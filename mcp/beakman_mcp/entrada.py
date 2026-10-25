"""La entrada al laboratorio: OAuth propio para el conector de Beakman, de momento solo en el nombre de prueba.

Al conectar el conector, Claude abre /entrada. Un adulto escribe un nombre para el saludo, un correo, el curso y
la comunidad autónoma, y marca la casilla de consentimiento. Le llega un correo de Beakman; al confirmarlo, la
ventana de Claude sigue sola y Claude recibe su token. Cada llamada al conector lleva ese token, y por él sabemos
de quién es, sin que nadie vuelva a escribir nada.

La parte de OAuth (metadatos, registro de clientes, /authorize, /token con PKCE, /revoke) la pone la librería
`mcp`; aquí va dónde se guarda cada cosa (SQLite), la página y el correo.

Datos: el contacto (correo, nombre, consentimiento) y el progreso (curso, curso escolar, comunidad) van en tablas
separadas, unidas solo por un identificador aleatorio de persona. «Olvídame» borra todo lo de esa persona.
Los tokens se guardan como hash, nunca en claro.
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import secrets
import smtplib
import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

import httpx
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .content import normalize

log = logging.getLogger("beakman.entrada")

CURSOS = {"1eso": "1º ESO", "2eso": "2º ESO", "3eso": "3º ESO", "4eso": "4º ESO"}
COMUNIDADES = [
    "Andalucía", "Aragón", "Principado de Asturias", "Illes Balears", "Canarias", "Cantabria", "Castilla-La Mancha",
    "Castilla y León", "Cataluña", "Comunitat Valenciana", "Extremadura", "Galicia", "Comunidad de Madrid",
    "Región de Murcia", "Comunidad Foral de Navarra", "País Vasco", "La Rioja", "Ceuta", "Melilla",
]
CONSENTIMIENTO = (
    "Soy el padre, la madre o el tutor (o tengo 14 años o más). Acepto que Beakman guarde este nombre, este correo, "
    "el curso y la comunidad autónoma para dar las clases y para escribirnos: resúmenes de los temas, recordatorios "
    "y avisos del laboratorio. Me puedo dar de baja cuando quiera diciéndole a Beakman «olvídame»."
)

SOLICITUD_TTL = 30 * 60          # la ventana de entrada caduca a la media hora
CODIGO_TTL = 5 * 60              # el código que canjea Claude, a los 5 minutos
ACCESS_TTL = 7 * 24 * 3600       # Claude renueva el token solo con el de refresco
REFRESH_TTL = 365 * 24 * 3600


def curso_escolar(ahora: datetime | None = None) -> str:
    """'2026-27' entre el 1 de septiembre de 2026 y el 31 de agosto de 2027."""
    d = ahora or datetime.now(timezone.utc)
    y = d.year if d.month >= 9 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def _hoy() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _normaliza_correo(correo: str) -> str:
    return correo.strip().lower()


def _curso_valido(curso: str) -> str:
    """'2º ESO', '2eso', 'segundo' -> '2eso'."""
    c = normalize(curso or "")
    for key, palabra in zip(CURSOS, ("primero", "segundo", "tercero", "cuarto")):
        if c.startswith((key[0], palabra)):
            return key
    raise ValueError("Curso no válido: tiene que ser 1º, 2º, 3º o 4º de la ESO.")


def _comunidad_valida(comunidad: str) -> str:
    """Admite el nombre sin tildes o en parte ('andalucia', 'madrid')."""
    want = normalize(comunidad or "")
    for c in COMUNIDADES:
        if want and (normalize(c) == want or want in normalize(c)):
            return c
    raise ValueError("Comunidad autónoma no válida. Opciones: " + ", ".join(COMUNIDADES))


# ---- almacén ----------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS personas (id TEXT PRIMARY KEY, creada TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contactos (
  persona_id TEXT PRIMARY KEY REFERENCES personas(id) ON DELETE CASCADE,
  correo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL,
  consentimiento TEXT NOT NULL, consentimiento_fecha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS progreso (
  persona_id TEXT PRIMARY KEY REFERENCES personas(id) ON DELETE CASCADE,
  curso TEXT, curso_escolar TEXT, comunidad TEXT, actualizado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clientes (client_id TEXT PRIMARY KEY, info TEXT NOT NULL, creado TEXT NOT NULL);
-- tipo: entrar (la ventana de Claude), presentarse (dar nombre y correo a una entrada sin datos) o borrar.
CREATE TABLE IF NOT EXISTS solicitudes (
  id TEXT PRIMARY KEY, tipo TEXT NOT NULL DEFAULT 'entrar', client_id TEXT, params TEXT, persona_id TEXT,
  creada REAL NOT NULL, datos TEXT, confirmacion TEXT, redirect TEXT);
-- enlaces de «preséntate» que da Beakman desde el chat, de un solo uso
CREATE TABLE IF NOT EXISTS enlaces (hash TEXT PRIMARY KEY, persona_id TEXT NOT NULL, caduca REAL NOT NULL);
CREATE TABLE IF NOT EXISTS codigos (code TEXT PRIMARY KEY, datos TEXT NOT NULL, caduca REAL NOT NULL);
CREATE TABLE IF NOT EXISTS tokens (
  hash TEXT PRIMARY KEY, tipo TEXT NOT NULL, client_id TEXT NOT NULL, persona_id TEXT NOT NULL,
  scopes TEXT NOT NULL, resource TEXT, caduca INTEGER NOT NULL);
"""


class Almacen:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA journal_mode = WAL")
        if self.db.execute("PRAGMA user_version").fetchone()[0] < 2:
            # Versión 2 (entrada sin datos): progreso admite huecos y solicitudes tiene tipo. La 1 solo existió en
            # la prueba, sin datos de nadie, así que estas dos tablas se rehacen.
            self.db.executescript("DROP TABLE IF EXISTS progreso; DROP TABLE IF EXISTS solicitudes;")
        self.db.executescript(SCHEMA)
        self.db.execute("PRAGMA user_version = 2")
        self.lock = threading.Lock()

    def q(self, sql: str, *args):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def one(self, sql: str, *args):
        rows = self.q(sql, *args)
        return rows[0] if rows else None

    def limpiar(self):
        now = time.time()
        self.q("DELETE FROM solicitudes WHERE creada < ?", now - SOLICITUD_TTL)
        self.q("DELETE FROM codigos WHERE caduca < ?", now)
        self.q("DELETE FROM tokens WHERE caduca < ?", int(now))
        self.q("DELETE FROM enlaces WHERE caduca < ?", now)
        # Entradas sin datos que ya no usa nadie (se desconectó el conector y caducaron sus tokens).
        self.q("DELETE FROM personas WHERE id NOT IN (SELECT persona_id FROM contactos) "
               "AND id NOT IN (SELECT persona_id FROM tokens) "
               "AND id NOT IN (SELECT json_extract(datos, '$.subject') FROM codigos)")

    # personas
    def persona_por_correo(self, correo: str) -> str | None:
        row = self.one("SELECT persona_id FROM contactos WHERE correo = ?", correo)
        return row["persona_id"] if row else None

    def nueva_persona(self) -> str:
        pid = secrets.token_hex(16)
        self.q("INSERT INTO personas (id, creada) VALUES (?, ?)", pid, _hoy())
        return pid

    def guardar_progreso(self, pid: str, curso: str | None = None, comunidad: str | None = None):
        """Solo cambia lo que llega; el curso siempre con su curso escolar."""
        self.q("INSERT INTO progreso (persona_id, actualizado) VALUES (?, ?) ON CONFLICT(persona_id) DO NOTHING",
               pid, _hoy())
        if curso:
            self.q("UPDATE progreso SET curso = ?, curso_escolar = ?, actualizado = ? WHERE persona_id = ?",
                   curso, curso_escolar(), _hoy(), pid)
        if comunidad:
            self.q("UPDATE progreso SET comunidad = ?, actualizado = ? WHERE persona_id = ?", comunidad, _hoy(), pid)

    def guardar_contacto(self, pid: str, correo: str, nombre: str):
        otra = self.persona_por_correo(correo)
        if otra and otra != pid:
            raise ValueError("Ese correo ya está en otra entrada del laboratorio.")
        self.q("INSERT INTO contactos VALUES (?, ?, ?, ?, ?) ON CONFLICT(persona_id) DO UPDATE SET "
               "correo = excluded.correo, nombre = excluded.nombre, consentimiento = excluded.consentimiento, "
               "consentimiento_fecha = excluded.consentimiento_fecha",
               pid, correo, nombre, CONSENTIMIENTO, _hoy())

    def guardar_persona(self, datos: dict) -> str:
        """Entrada con datos: crea la persona, o la reutiliza si ese correo ya entró antes (conserva su progreso)."""
        pid = self.persona_por_correo(datos["correo"]) or self.nueva_persona()
        self.guardar_contacto(pid, datos["correo"], datos["nombre"])
        self.guardar_progreso(pid, datos["curso"], datos["comunidad"])
        return pid

    def ficha(self, pid: str) -> dict | None:
        """Lo que se sabe de la persona. `correo` y `nombre` faltan si entró sin datos."""
        if not self.one("SELECT id FROM personas WHERE id = ?", pid):
            return None
        c = self.one("SELECT correo, nombre, consentimiento_fecha FROM contactos WHERE persona_id = ?", pid)
        p = self.one("SELECT curso, curso_escolar, comunidad FROM progreso WHERE persona_id = ?", pid)
        return {"correo": None, "nombre": None, "curso": None, "curso_escolar": None, "comunidad": None,
                **(dict(c) if c else {}), **(dict(p) if p else {})}

    def quitar_contacto(self, pid: str):
        """Borra nombre y correo; la entrada sigue, sin datos."""
        self.q("DELETE FROM contactos WHERE persona_id = ?", pid)

    def enlace_presentarse(self, pid: str) -> str:
        token = secrets.token_urlsafe(24)
        self.q("INSERT INTO enlaces VALUES (?, ?, ?)", _hash(token), pid, time.time() + SOLICITUD_TTL)
        return token

    def olvidar(self, pid: str):
        self.q("DELETE FROM tokens WHERE persona_id = ?", pid)
        self.q("DELETE FROM personas WHERE id = ?", pid)  # contactos y progreso caen en cascada


# ---- límites y avisos ---------------------------------------------------------

class Limites:
    """Ventana deslizante en memoria: basta con un solo proceso."""

    def __init__(self):
        self.hits: dict[str, deque] = defaultdict(deque)

    def permite(self, clave: str, maximo: int, ventana: int) -> bool:
        now, q = time.time(), self.hits[clave]
        while q and q[0] < now - ventana:
            q.popleft()
        if len(q) >= maximo:
            return False
        q.append(now)
        return True


async def turnstile_ok(secret: str, token: str, ip: str | None) -> bool:
    if not secret:
        log.warning("Turnstile sin clave: no se comprueba (solo vale en local)")
        return True
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                                  data={"secret": secret, "response": token, "remoteip": ip or ""})
        return bool(r.json().get("success"))
    except Exception:  # noqa: BLE001 — si Cloudflare no responde, no se entra
        log.exception("Turnstile no responde")
        return False


# ---- el proveedor OAuth ---------------------------------------------------------

class Entrada:
    """Proveedor OAuth de la librería `mcp` y las páginas de la entrada."""

    def __init__(self, base_url: str, db_path: str):
        self.base = base_url.rstrip("/")
        self.db = Almacen(db_path)
        self.limites = Limites()
        self.turnstile_site = os.environ.get("TURNSTILE_SITE_KEY", "")
        self.turnstile_secret = os.environ.get("TURNSTILE_SECRET_KEY", "")
        self.permitidos = {_normaliza_correo(c) for c in os.environ.get("BEAKMAN_PRUEBA_CORREOS", "").split(",")
                           if c.strip()}
        self.smtp = {k: os.environ.get(f"BEAKMAN_SMTP_{k.upper()}", "") for k in ("host", "port", "user", "password")}

    # clientes (registro dinámico: Claude se da de alta solo)
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        row = self.db.one("SELECT info FROM clientes WHERE client_id = ?", client_id)
        return OAuthClientInformationFull.model_validate_json(row["info"]) if row else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self.db.q("INSERT OR REPLACE INTO clientes VALUES (?, ?, ?)", client_info.client_id,
                  client_info.model_dump_json(), datetime.now(timezone.utc).isoformat(timespec="seconds"))

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """No decide nada todavía: apunta la petición y manda la ventana a nuestra página."""
        self.db.limpiar()
        sid = secrets.token_urlsafe(24)
        self.db.q("INSERT INTO solicitudes (id, client_id, params, creada) VALUES (?, ?, ?, ?)",
                  sid, client.client_id, params.model_dump_json(), time.time())
        return f"{self.base}/entrada?s={sid}"

    # códigos de un solo uso
    async def load_authorization_code(self, client, authorization_code: str) -> AuthorizationCode | None:
        row = self.db.one("SELECT datos FROM codigos WHERE code = ?", authorization_code)
        if not row:
            return None
        code = AuthorizationCode.model_validate_json(row["datos"])
        return code if code.client_id == client.client_id else None

    async def exchange_authorization_code(self, client, authorization_code: AuthorizationCode) -> OAuthToken:
        self.db.q("DELETE FROM codigos WHERE code = ?", authorization_code.code)
        return self._emitir(client.client_id, authorization_code.subject, authorization_code.scopes,
                            authorization_code.resource)

    # tokens
    def _emitir(self, client_id: str, pid: str | None, scopes: list[str], resource: str | None) -> OAuthToken:
        if not pid:
            raise TokenError("invalid_grant", "código sin persona")
        access, refresh, now = secrets.token_urlsafe(32), secrets.token_urlsafe(32), int(time.time())
        for tok, tipo, ttl in ((access, "access", ACCESS_TTL), (refresh, "refresh", REFRESH_TTL)):
            self.db.q("INSERT INTO tokens VALUES (?, ?, ?, ?, ?, ?, ?)", _hash(tok), tipo, client_id, pid,
                      " ".join(scopes), resource, now + ttl)
        return OAuthToken(access_token=access, expires_in=ACCESS_TTL, refresh_token=refresh,
                          scope=" ".join(scopes) or None)

    def _token(self, token: str, tipo: str):
        row = self.db.one("SELECT * FROM tokens WHERE hash = ? AND tipo = ?", _hash(token), tipo)
        if not row or row["caduca"] < time.time():
            return None
        return row

    async def load_refresh_token(self, client, refresh_token: str) -> RefreshToken | None:
        row = self._token(refresh_token, "refresh")
        if not row or row["client_id"] != client.client_id:
            return None
        return RefreshToken(token=refresh_token, client_id=row["client_id"], scopes=row["scopes"].split(),
                            expires_at=row["caduca"], resource=row["resource"], subject=row["persona_id"])

    async def exchange_refresh_token(self, client, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        self.db.q("DELETE FROM tokens WHERE hash = ?", _hash(refresh_token.token))  # se rota
        return self._emitir(client.client_id, refresh_token.subject, scopes or refresh_token.scopes,
                            refresh_token.resource)

    async def load_access_token(self, token: str) -> AccessToken | None:
        row = self._token(token, "access")
        if not row:
            return None
        return AccessToken(token=token, client_id=row["client_id"], scopes=row["scopes"].split(),
                           expires_at=row["caduca"], resource=row["resource"], subject=row["persona_id"])

    async def revoke_token(self, token) -> None:
        self.db.q("DELETE FROM tokens WHERE hash = ?", _hash(token.token))

    # ---- páginas ----------------------------------------------------------------

    def _solicitud(self, sid: str):
        row = self.db.one("SELECT * FROM solicitudes WHERE id = ?", sid or "")
        if not row or row["creada"] < time.time() - SOLICITUD_TTL:
            return None
        return row

    def _ip(self, request: Request) -> str:
        return request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0]

    def _enlace(self, token: str) -> str | None:
        row = self.db.one("SELECT persona_id FROM enlaces WHERE hash = ? AND caduca > ?", _hash(token or ""), time.time())
        return row["persona_id"] if row else None

    def _codigo(self, sol, pid: str) -> str:
        """El código de un solo uso para Claude, y la dirección de vuelta a su ventana."""
        params = AuthorizationParams.model_validate_json(sol["params"])
        code = AuthorizationCode(
            code=secrets.token_urlsafe(32), scopes=params.scopes or [], expires_at=time.time() + CODIGO_TTL,
            client_id=sol["client_id"], code_challenge=params.code_challenge, redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly, resource=params.resource,
            subject=pid)
        self.db.q("INSERT INTO codigos VALUES (?, ?, ?)", code.code, code.model_dump_json(), code.expires_at)
        redirect = construct_redirect_uri(str(params.redirect_uri), code=code.code, state=params.state)
        self.db.q("UPDATE solicitudes SET redirect = ? WHERE id = ?", redirect, sol["id"])
        return redirect

    async def pagina(self, request: Request) -> Response:
        """La ventana que abre Claude al conectar: con datos o sin datos."""
        sid = request.query_params.get("s", "")
        if not self._solicitud(sid):
            return _html("La entrada ha caducado", CADUCADA, 400)
        return _html("Antes de empezar, preséntate", _formulario("s", sid, self.turnstile_site))

    async def presentarse(self, request: Request) -> Response:
        """El enlace que da Beakman desde el chat a una entrada sin datos."""
        e = request.query_params.get("e", "")
        if not self._enlace(e):
            return _html("El enlace ha caducado", "<p>Pídele a Beakman otro: «quiero presentarme».</p>", 400)
        return _html("Preséntate", _formulario("e", e, self.turnstile_site, anonima=False))

    async def enviar(self, request: Request) -> Response:
        form = await request.form()
        sid, e = str(form.get("s", "")), str(form.get("e", ""))
        sol = self._solicitud(sid) if sid else None
        pid_enlace = self._enlace(e) if e else None
        if not sol and not pid_enlace:
            return _html("La entrada ha caducado", CADUCADA, 400)
        oculto = ("s", sid) if sol else ("e", e)
        ip = self._ip(request)
        sin_datos = sol is not None and form.get("modo") == "sin-datos"

        errores, datos = [], {}
        if not sin_datos:
            datos["nombre"] = " ".join(str(form.get("nombre", "")).split())[:40]
            if not datos["nombre"]:
                errores.append("Falta un nombre para el saludo.")
            datos["correo"] = _normaliza_correo(str(form.get("correo", "")))[:120]
            if "@" not in datos["correo"] or "." not in datos["correo"].split("@")[-1]:
                errores.append("El correo no parece válido.")
            if form.get("acepto") != "si":
                errores.append("Hace falta marcar la casilla de consentimiento.")
        for campo, valida in (("curso", _curso_valido), ("comunidad", _comunidad_valida)):
            try:
                datos[campo] = valida(str(form.get(campo, "")))
            except ValueError as exc:
                datos[campo] = None
                if not sin_datos:  # sin datos, el curso y la comunidad son opcionales
                    errores.append(str(exc))
        if not errores and not await turnstile_ok(self.turnstile_secret, str(form.get("cf-turnstile-response", "")), ip):
            errores.append("No he podido comprobar que no eres un robot. Inténtalo otra vez.")
        # Lista cerrada: vacía no entra nadie; "*" abre la entrada a cualquiera. Sin datos no se manda ningún correo.
        if not errores and not sin_datos and "*" not in self.permitidos and datos["correo"] not in self.permitidos:
            errores.append("Esta entrada es de prueba y solo admite unos correos concretos.")
        if not errores and not self.limites.permite(f"ip:{ip}", 10, 3600):
            errores.append("Demasiados intentos. Espera un rato y vuelve a probar.")
        if not errores and not sin_datos and not self.limites.permite(f"correo:{datos['correo']}", 3, 3600):
            errores.append("Demasiados intentos con ese correo. Espera un rato y vuelve a probar.")
        if errores:
            return _html("Antes de empezar, preséntate",
                         _formulario(*oculto, self.turnstile_site, errores, form, anonima=sol is not None), 400)

        if sin_datos:
            # Entrada sin datos: ni correo ni confirmación. Claude recibe su token al momento.
            pid = self.db.nueva_persona()
            self.db.guardar_progreso(pid, datos["curso"], datos["comunidad"])
            return RedirectResponse(self._codigo(sol, pid), status_code=303)

        confirmacion = secrets.token_urlsafe(24)
        enlace = f"{self.base}/entrada/confirmar?t={confirmacion}"
        if sol:
            self.db.q("UPDATE solicitudes SET datos = ?, confirmacion = ? WHERE id = ?",
                      json.dumps(datos), _hash(confirmacion), sid)
            self._correo(datos["correo"], datos["nombre"], "Confirma tu entrada al laboratorio de Beakman",
                         "Confirma tu entrada", "Para entrar en el laboratorio, pulsa el botón. La ventana de Claude "
                         "se conectará sola.", "Confirmar mi entrada", enlace)
            return _html("Mira tu correo", _esperando(sid, datos["correo"]))
        self.db.q("INSERT INTO solicitudes (id, tipo, persona_id, creada, datos, confirmacion) VALUES (?, ?, ?, ?, ?, ?)",
                  secrets.token_urlsafe(24), "presentarse", pid_enlace, time.time(), json.dumps(datos),
                  _hash(confirmacion))
        self.db.q("DELETE FROM enlaces WHERE hash = ?", _hash(e))
        self._correo(datos["correo"], datos["nombre"], "Confirma tus datos en el laboratorio de Beakman",
                     "Confirma tus datos", "Pulsa el botón y Beakman ya sabrá cómo saludarte y a quién escribir.",
                     "Confirmar mis datos", enlace)
        return _html("Mira tu correo", f"<p class='lead'>Te he mandado un correo a <b>{html.escape(datos['correo'])}"
                                       "</b>. Pulsa el botón que trae y listo.</p>")

    async def estado(self, request: Request) -> Response:
        sol = self._solicitud(request.query_params.get("s", ""))
        if not sol:
            return JSONResponse({"estado": "caducada"}, status_code=404)
        return JSONResponse({"estado": "confirmada", "redirect": sol["redirect"]} if sol["redirect"]
                            else {"estado": "esperando"})

    async def confirmar(self, request: Request) -> Response:
        t = request.query_params.get("t", "")
        sol = self.db.one("SELECT * FROM solicitudes WHERE confirmacion = ?", _hash(t)) if t else None
        if not sol or sol["creada"] < time.time() - SOLICITUD_TTL:
            return _html("El enlace ha caducado", CADUCADA, 400)
        datos = json.loads(sol["datos"])
        if sol["tipo"] == "borrar":
            pid = self.db.persona_por_correo(datos["correo"])
            if pid:
                self.db.olvidar(pid)
            self.db.q("DELETE FROM solicitudes WHERE id = ?", sol["id"])
            return _html("Borrado", "<p class='lead'>He borrado todo lo que el laboratorio guardaba de ese correo. "
                                    "Si Beakman sigue conectado en Claude, ya no sabe quién eres.</p>")
        if sol["tipo"] == "presentarse":
            try:
                self.db.guardar_contacto(sol["persona_id"], datos["correo"], datos["nombre"])
            except ValueError as exc:
                return _html("No ha podido ser", f"<p>{html.escape(str(exc))} Para usar ese correo, en Claude ve a "
                                                 "Ajustes → Conectores, desconecta Beakman y vuelve a conectarlo.</p>",
                             400)
            self.db.guardar_progreso(sol["persona_id"], datos.get("curso"), datos.get("comunidad"))
            self.db.q("DELETE FROM solicitudes WHERE id = ?", sol["id"])
            return _html("¡Hecho!", f"<p class='lead'>Encantado, {html.escape(datos['nombre'])}. Vuelve a Claude: "
                                    "Beakman ya sabe cómo saludarte.</p>")
        if not sol["redirect"]:
            self._codigo(sol, self.db.guardar_persona(datos))
        return _html("¡Hecho!", "<p class='lead'>Ya estás dentro del laboratorio. Vuelve a la ventana de Claude: "
                                "se conecta sola en unos segundos.</p><p>Puedes cerrar esta pestaña.</p>")

    async def borrar_pagina(self, request: Request) -> Response:
        return _html("Borrar mis datos", _form_borrar(self.turnstile_site))

    async def borrar(self, request: Request) -> Response:
        """Borrar desde fuera del chat: llega un enlace al correo y, al pulsarlo, se borra todo."""
        form = await request.form()
        correo = _normaliza_correo(str(form.get("correo", "")))[:120]
        ip = self._ip(request)
        if "@" not in correo:
            return _html("Borrar mis datos", _form_borrar(self.turnstile_site, "El correo no parece válido."), 400)
        if not await turnstile_ok(self.turnstile_secret, str(form.get("cf-turnstile-response", "")), ip):
            return _html("Borrar mis datos", _form_borrar(self.turnstile_site, "No he podido comprobar que no eres "
                                                          "un robot. Inténtalo otra vez."), 400)
        # La respuesta es la misma esté o no el correo: así no se puede averiguar quién usa el laboratorio.
        if (self.db.persona_por_correo(correo) and self.limites.permite(f"ip:{ip}", 10, 3600)
                and self.limites.permite(f"correo:{correo}", 3, 3600)):
            confirmacion = secrets.token_urlsafe(24)
            self.db.q("INSERT INTO solicitudes (id, tipo, creada, datos, confirmacion) VALUES (?, ?, ?, ?, ?)",
                      secrets.token_urlsafe(24), "borrar", time.time(), json.dumps({"correo": correo}),
                      _hash(confirmacion))
            self._correo(correo, None, "Borrar tus datos del laboratorio de Beakman", "Borrar tus datos",
                         "Has pedido borrar todo lo que el laboratorio guarda de este correo. Pulsa el botón para "
                         "hacerlo; no se puede deshacer.", "Borrar mis datos",
                         f"{self.base}/entrada/confirmar?t={confirmacion}")
        return _html("Mira tu correo", "<p class='lead'>Si ese correo está en el laboratorio, te llega un enlace para "
                                       "borrarlo todo. Caduca en media hora.</p>")

    # ---- correo -------------------------------------------------------------------

    def _correo(self, correo: str, nombre: str | None, asunto: str, titulo: str, intro: str, boton: str, enlace: str):
        hola = f"¡Hola, {nombre}!" if nombre else "¡Hola!"
        texto = (f"{hola}\n\n{intro}\n{enlace}\n\nEl enlace caduca en media hora. Si no has sido tú, no hagas nada.\n\n"
                 "Un abrazo con la bata puesta,\nBeakman")
        cuerpo = (MAIL_HTML.replace("{hola}", html.escape(hola)).replace("{titulo}", html.escape(titulo))
                  .replace("{intro}", html.escape(intro)).replace("{boton}", html.escape(boton))
                  .replace("{enlace}", html.escape(enlace)))
        if not self.smtp["password"]:
            log.warning("SMTP sin contraseña: no se envía. Enlace: %s", enlace)
            return
        msg = EmailMessage()
        msg["From"] = formataddr(("Beakman", os.environ.get("BEAKMAN_MAIL_FROM", "beakman@kademy.net")))
        msg["To"] = correo
        msg["Subject"] = asunto
        msg["Message-ID"] = make_msgid(domain="kademy.net")
        msg.set_content(texto)
        msg.add_alternative(cuerpo, subtype="html")
        with smtplib.SMTP(self.smtp["host"] or "smtp.zoho.eu", int(self.smtp["port"] or 587), timeout=20) as s:
            s.starttls()
            s.login(self.smtp["user"] or "root@kademy.net", self.smtp["password"])
            s.send_message(msg)
        log.info("correo enviado: %s", asunto)


# ---- HTML ---------------------------------------------------------------------------

PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo} · El laboratorio de Beakman</title>
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@400;700;800&display=swap">
<style>
:root { --lime: #A6D41E; --lime-soft: #EEF6D6; --ink: #1F3A0B; --text: #1F2A17; --muted: #4E5A45; --card: #F4F6EC;
  --line: #DCE6C6; --note: #F8EFCB; --note-line: #E8D27A; }
* { box-sizing: border-box; }
html { background: #fff; }
body { margin: 0; min-height: 100vh; color: var(--text); font: 17px/1.6 "Nunito", system-ui, sans-serif; border-top: 6px solid var(--lime);
  background-color: #fff; background-image: linear-gradient(rgba(127,168,15,.10) 1px, transparent 1px),
  linear-gradient(90deg, rgba(127,168,15,.10) 1px, transparent 1px); background-size: 28px 28px; }
.wrap { max-width: 560px; margin: 0 auto; padding: 22px 16px 40px; }
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.brand img { width: 56px; height: 56px; border-radius: 50%; border: 3px solid var(--lime); object-fit: cover; }
.brand b { font: 600 1.15rem/1.1 "Fredoka", sans-serif; color: var(--ink); display: block; }
.brand small { color: var(--muted); }
h1 { font: 600 1.9rem/1.15 "Fredoka", sans-serif; color: var(--ink); margin: 0 0 6px; }
.lead { color: var(--muted); margin: 0 0 18px; }
.card { background: var(--card); border: 2px solid var(--ink); border-radius: 18px; box-shadow: 4px 4px 0 var(--lime); padding: 18px 20px; }
label { display: block; font-weight: 800; color: var(--ink); margin: 12px 0 4px; }
input[type=text], input[type=email], select { width: 100%; font: 400 1rem "Nunito", sans-serif; padding: 9px 12px;
  border: 2px solid var(--line); border-radius: 12px; background: #fff; color: var(--text); }
input:focus, select:focus { outline: none; border-color: var(--ink); }
.hint { font-size: .88rem; color: var(--muted); margin: 3px 0 0; }
.check { display: flex; gap: 10px; align-items: flex-start; font-weight: 400; font-size: .92rem; color: var(--text);
  background: #fff; border: 1.5px solid var(--line); border-radius: 12px; padding: 10px 12px; margin-top: 16px; }
.check input { margin-top: 4px; width: 18px; height: 18px; flex: none; }
.alt { margin-top: 22px; padding-top: 16px; border-top: 1.5px dashed var(--line); }
.alt p { font-size: .92rem; color: var(--muted); margin: 4px 0 0; }
.btn.ghost { background: #fff; }
a { color: var(--ink); text-decoration-color: var(--lime); text-decoration-thickness: 2px; }
.btn { display: inline-flex; margin-top: 18px; background: var(--lime); color: var(--ink); font: 800 1rem "Nunito", sans-serif;
  border: 2px solid var(--ink); border-radius: 999px; padding: 10px 20px; box-shadow: 3px 3px 0 var(--ink); cursor: pointer; }
.errores { background: #FBE5E1; border: 1.5px solid #E7A89F; border-radius: 12px; padding: 10px 14px; margin-bottom: 12px; color: #7A2A20; }
.errores p { margin: 0; }
.note { background: var(--note); border: 1.5px solid var(--note-line); border-radius: 12px; padding: 12px 14px; font-size: .92rem; margin-top: 18px; }
.spin { display: inline-block; width: 16px; height: 16px; border: 3px solid var(--line); border-top-color: var(--ink);
  border-radius: 50%; animation: s 1s linear infinite; vertical-align: -3px; margin-right: 8px; }
@keyframes s { to { transform: rotate(360deg); } }
</style>
{head}
</head>
<body><main class="wrap">
<div class="brand"><img src="https://lab.beakman.kademy.net/media/beakman.jpg" alt="">
  <span><b>El laboratorio de Beakman</b><small>La entrada</small></span></div>
{cuerpo}
</main></body>
</html>
"""

MAIL_HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="color-scheme" content="light"></head>
<body style="margin:0;padding:0;background:#F4F6EC;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F4F6EC;"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:560px;background:#FFFFFF;border:2px solid #1F3A0B;border-radius:18px;font-family:Nunito,'Segoe UI',Arial,sans-serif;color:#1F2A17;">
<tr><td style="background:#A6D41E;height:8px;line-height:8px;font-size:0;border-radius:16px 16px 0 0;">&nbsp;</td></tr>
<tr><td style="padding:22px 26px 6px;"><table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
<td style="vertical-align:middle;padding-right:14px;"><img src="https://lab.beakman.kademy.net/media/beakman.jpg" width="60" height="60" alt="Beakman" style="display:block;width:60px;height:60px;border-radius:50%;border:3px solid #A6D41E;object-fit:cover;"></td>
<td style="vertical-align:middle;"><div style="font-size:13px;font-weight:700;color:#4F6B0A;">El laboratorio de Beakman</div>
<div style="font-size:22px;line-height:1.2;font-weight:800;color:#1F3A0B;">{titulo}</div></td></tr></table></td></tr>
<tr><td style="padding:12px 26px 0;font-size:16px;line-height:1.6;">
<p style="margin:0 0 14px;">{hola}</p>
<p style="margin:0 0 18px;">{intro}</p>
<p style="margin:0 0 22px;"><a href="{enlace}" style="display:inline-block;background:#A6D41E;color:#1F3A0B;font-weight:800;text-decoration:none;border:2px solid #1F3A0B;border-radius:999px;padding:10px 20px;">{boton}</a></p>
<p style="margin:0 0 14px;color:#4E5A45;font-size:14px;">El enlace caduca en media hora. Si no has sido tú, no hagas nada: sin confirmar no cambia nada.</p>
<p style="margin:0 0 4px;">Un abrazo con la bata puesta,</p>
<p style="margin:0 0 20px;font-size:20px;font-weight:800;color:#1F3A0B;">Beakman</p></td></tr>
</table></td></tr></table></body></html>
"""


def _html(titulo: str, cuerpo: str, status: int = 200, head: str = "") -> HTMLResponse:
    page = PAGE.replace("{titulo}", html.escape(titulo)).replace("{head}", head).replace("{cuerpo}", cuerpo)
    return HTMLResponse(page, status_code=status, headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY"})


CADUCADA = "<p>Vuelve a Claude y pulsa otra vez <b>Conectar</b>.</p>"
CAMBIAR = ("<p class='note'>¿Quieres cambiar de opción más adelante? En Claude, ve a Ajustes → Conectores, desconecta "
           "Beakman y vuelve a conectarlo: esta página saldrá otra vez. También puedes pedírselo a Beakman en el chat "
           "(«quiero presentarme», «olvídame»). Y si ya diste tus datos y quieres borrarlos sin entrar en Claude: "
           "<a href='/entrada/borrar'>borrar mis datos</a>.</p>")


def _turnstile(site_key: str) -> str:
    return (f'<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>'
            f'<div class="cf-turnstile" data-sitekey="{html.escape(site_key)}" data-language="es" style="margin-top:14px">'
            f'</div>' if site_key else "")


def _formulario(oculto: str, valor: str, site_key: str, errores: list[str] | None = None, form=None,
                anonima: bool = True) -> str:
    """El formulario de la entrada. `oculto` es "s" (la ventana de Claude) o "e" (el enlace «preséntate»).
    Con `anonima`, además el botón «Entrar sin datos»."""
    v = (lambda k: html.escape(str(form.get(k, "")))) if form else (lambda k: "")
    cursos = "".join(f'<option value="{k}"{" selected" if v("curso") == k else ""}>{n}</option>' for k, n in CURSOS.items())
    comunidades = "".join(f'<option{" selected" if v("comunidad") == html.escape(c) else ""}>{html.escape(c)}</option>'
                          for c in COMUNIDADES)
    err = ("<div class='errores'>" + "".join(f"<p>{html.escape(e)}</p>" for e in errores) + "</div>") if errores else ""
    sin_datos = """<div class="alt"><b>¿Prefieres no dar datos?</b>
<p>Entra sin datos: Beakman no sabrá tu nombre ni podrá escribiros. El curso y la comunidad, si los eliges arriba, sí
se guardan (no dicen quién eres). Podrás presentarte cuando quieras.</p>
<button class="btn ghost" type="submit" name="modo" value="sin-datos" formnovalidate>Entrar sin datos</button></div>""" \
        if anonima else ""
    return f"""<h1>¡Hola! Antes de empezar, preséntate</h1>
<p class="lead">Lo rellena un adulto. Solo necesito un nombre para saludar y un correo para comunicarme con vosotros.</p>
{err}<form class="card" method="post" action="/entrada">
<input type="hidden" name="{oculto}" value="{html.escape(valor)}">
<label for="nombre">Nombre para el saludo</label>
<input type="text" id="nombre" name="nombre" maxlength="40" required autocomplete="given-name" value="{v('nombre')}">
<p class="hint">El nombre de pila o un mote. No hace falta el apellido.</p>
<label for="correo">Correo de un adulto</label>
<input type="email" id="correo" name="correo" maxlength="120" required autocomplete="email" value="{v('correo')}">
<label for="curso">Curso</label>
<select id="curso" name="curso" required><option value="">Elige…</option>{cursos}</select>
<label for="comunidad">Comunidad autónoma</label>
<select id="comunidad" name="comunidad" required><option value="">Elige…</option>{comunidades}</select>
<p class="hint">Cada comunidad da el temario a su manera: así Beakman sigue el tuyo.</p>
<label class="check"><input type="checkbox" name="acepto" value="si" required><span>{html.escape(CONSENTIMIENTO)}</span></label>
{_turnstile(site_key)}
<button class="btn" type="submit" name="modo" value="datos">Entrar al laboratorio</button>
{sin_datos}
</form>
<p class="note">Qué guardamos: lo que ves en este formulario y nada más. No guardamos apellidos, edad, colegio ni lo que
escribís en Claude. Para verlo, pregúntale a Beakman «¿qué sabes de mí?»; para borrarlo todo, «olvídame».</p>
{CAMBIAR if anonima else ""}"""


def _form_borrar(site_key: str, error: str = "") -> str:
    err = f"<div class='errores'><p>{html.escape(error)}</p></div>" if error else ""
    return f"""<h1>Borrar mis datos</h1>
<p class="lead">Escribe el correo que diste al entrar. Te llegará un enlace; al pulsarlo, se borra todo lo que el
laboratorio guarda de ese correo.</p>
{err}<form class="card" method="post" action="/entrada/borrar">
<label for="correo">Correo</label>
<input type="email" id="correo" name="correo" maxlength="120" required autocomplete="email">
{_turnstile(site_key)}
<button class="btn" type="submit">Mandarme el enlace</button>
</form>"""


def _esperando(sid: str, correo: str) -> str:
    return f"""<h1>Mira tu correo</h1>
<p class="lead">Te he mandado un correo a <b>{html.escape(correo)}</b>. Pulsa el botón que trae y esta ventana seguirá sola.</p>
<div class="card"><span class="spin"></span><span id="msg">Esperando la confirmación…</span></div>
<p class="note">¿No llega? Mira en la carpeta de correo no deseado. El enlace caduca en media hora.</p>
<script>
(function () {{
  var msg = document.getElementById("msg");
  function mira() {{
    fetch("/entrada/estado?s={html.escape(sid)}", {{cache: "no-store"}}).then(function (r) {{ return r.json(); }}).then(function (d) {{
      if (d.estado === "confirmada") {{ msg.textContent = "¡Confirmado! Volviendo a Claude…"; location.replace(d.redirect); }}
      else if (d.estado === "caducada") {{ msg.textContent = "La entrada ha caducado. Vuelve a Claude y pulsa otra vez Conectar."; }}
      else setTimeout(mira, 2000);
    }}).catch(function () {{ setTimeout(mira, 4000); }});
  }}
  setTimeout(mira, 2000);
}})();
</script>"""
