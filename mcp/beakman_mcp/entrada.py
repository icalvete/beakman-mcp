"""La entrada al laboratorio: OAuth propio para el conector de Beakman.

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


def _buzon(correo: str) -> str:
    """El buzón real, para los límites: sin +sufijo, y en Gmail sin puntos («a.b+x@gmail.com» = «ab@gmail.com»)."""
    local, _, dominio = correo.partition("@")
    local = local.split("+", 1)[0]
    if dominio in ("gmail.com", "googlemail.com"):
        local, dominio = local.replace(".", ""), "gmail.com"
    return f"{local}@{dominio}"


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
-- «Mis datos»: enlaces mágicos (un solo uso, 15 min) y sesiones (1 hora), siempre como hash
CREATE TABLE IF NOT EXISTS accesos (hash TEXT PRIMARY KEY, persona_id TEXT NOT NULL, caduca REAL NOT NULL);
-- Contadores de uso: cuántas veces pasa algo cada día, nada más. Sin persona, sin IP, sin correo.
CREATE TABLE IF NOT EXISTS contadores (dia TEXT NOT NULL, clave TEXT NOT NULL, n INTEGER NOT NULL,
  PRIMARY KEY (dia, clave));
-- Administración (/admin): enlaces y sesiones aparte de los de «Mis datos», siempre como hash
CREATE TABLE IF NOT EXISTS admin_accesos (hash TEXT PRIMARY KEY, correo TEXT NOT NULL, caduca REAL NOT NULL);
CREATE TABLE IF NOT EXISTS admin_sesiones (hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, caduca REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sesiones (
  hash TEXT PRIMARY KEY, persona_id TEXT NOT NULL, csrf TEXT NOT NULL, caduca REAL NOT NULL);
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
        self.q("DELETE FROM accesos WHERE caduca < ?", now)
        self.q("DELETE FROM sesiones WHERE caduca < ?", now)
        self.q("DELETE FROM admin_accesos WHERE caduca < ?", now)
        self.q("DELETE FROM admin_sesiones WHERE caduca < ?", now)
        # Entradas sin datos que ya no usa nadie (se desconectó el conector y caducaron sus tokens).
        self.q("DELETE FROM personas WHERE id NOT IN (SELECT persona_id FROM contactos) "
               "AND id NOT IN (SELECT persona_id FROM tokens) "
               "AND id NOT IN (SELECT json_extract(datos, '$.subject') FROM codigos)")

    # personas
    def persona_por_correo(self, correo: str) -> str | None:
        row = self.one("SELECT persona_id FROM contactos WHERE correo = ?", correo)
        return row["persona_id"] if row else None

    def contar(self, clave: str):
        """Suma 1 al contador de hoy (UTC). Es lo único que se apunta del uso: ni quién ni desde dónde."""
        self.q("INSERT INTO contadores VALUES (?, ?, 1) ON CONFLICT(dia, clave) DO UPDATE SET n = n + 1",
               datetime.now(timezone.utc).date().isoformat(), clave)

    def cifras(self, semanas: int = 12) -> dict:
        """Totales por semana ISO de las últimas `semanas`, y las entradas que existen ahora."""
        from datetime import date
        por_semana: dict[str, dict[str, int]] = {}
        for row in self.q("SELECT dia, clave, n FROM contadores ORDER BY dia DESC"):
            a, s, _ = date.fromisoformat(row["dia"]).isocalendar()
            por_semana.setdefault(f"{a}-S{s:02d}", {}).setdefault(row["clave"], 0)
            por_semana[f"{a}-S{s:02d}"][row["clave"]] += row["n"]
        total = self.one("SELECT COUNT(*) AS n FROM personas")["n"]
        con = self.one("SELECT COUNT(*) AS n FROM contactos")["n"]
        return {"semanas": dict(list(sorted(por_semana.items(), reverse=True))[:semanas]),
                "entradas": {"con_datos": con, "sin_datos": total - con}}

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
        self.contar("sin_correo")

    def enlace_presentarse(self, pid: str) -> str:
        token = secrets.token_urlsafe(24)
        self.q("INSERT INTO enlaces VALUES (?, ?, ?)", _hash(token), pid, time.time() + SOLICITUD_TTL)
        return token

    def olvidar(self, pid: str):
        self.contar("borrado")
        self.q("DELETE FROM tokens WHERE persona_id = ?", pid)
        self.q("DELETE FROM sesiones WHERE persona_id = ?", pid)
        self.q("DELETE FROM accesos WHERE persona_id = ?", pid)
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
        # Administración: correos de los administradores y la huella scrypt de su contraseña (scripts/admin_password.py).
        # Si falta cualquiera de los dos, /admin no existe.
        self.admins = {_buzon(_normaliza_correo(c)) for c in os.environ.get("BEAKMAN_ADMIN_CORREOS", "").split(",")
                       if c.strip()}
        self.admin_hash = os.environ.get("BEAKMAN_ADMIN_HASH", "")
        self.permitidos = {_normaliza_correo(c) for c in os.environ.get("BEAKMAN_ENTRADA_CORREOS", "").split(",")
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
            errores.append("Ahora mismo la entrada solo admite unos correos concretos.")
        if not errores and not self.limites.permite(f"ip:{ip}", 10, 3600):
            errores.append("Demasiados intentos. Espera un rato y vuelve a probar.")
        if not errores and not sin_datos and not self.limites.permite(f"correo:{_buzon(datos['correo'])}", 3, 3600):
            errores.append("Demasiados intentos con ese correo. Espera un rato y vuelve a probar.")
        if errores:
            return _html("Antes de empezar, preséntate",
                         _formulario(*oculto, self.turnstile_site, errores, form, anonima=sol is not None), 400)

        if sin_datos:
            # Entrada sin datos: ni correo ni confirmación. Claude recibe su token al momento.
            pid = self.db.nueva_persona()
            self.db.contar("entrada_sin_datos")
            self.db.guardar_progreso(pid, datos["curso"], datos["comunidad"])
            return RedirectResponse(self._codigo(sol, pid), status_code=303)

        confirmacion = secrets.token_urlsafe(24)
        enlace = f"{self.base}/entrada/confirmar?t={confirmacion}"
        if sol:
            self.db.q("UPDATE solicitudes SET datos = ?, confirmacion = ? WHERE id = ?",
                      json.dumps(datos), _hash(confirmacion), sid)
            self._correo(datos["correo"], None, "Confirma tu entrada al laboratorio de Beakman",
                         "Confirma tu entrada", "Para entrar en el laboratorio, pulsa el botón. La ventana de Claude "
                         "se conectará sola.", "Confirmar mi entrada", enlace)
            return _html("Mira tu correo", _esperando(sid, datos["correo"]))
        self.db.q("INSERT INTO solicitudes (id, tipo, persona_id, creada, datos, confirmacion) VALUES (?, ?, ?, ?, ?, ?)",
                  secrets.token_urlsafe(24), "presentarse", pid_enlace, time.time(), json.dumps(datos),
                  _hash(confirmacion))
        self.db.q("DELETE FROM enlaces WHERE hash = ?", _hash(e))
        self._correo(datos["correo"], None, "Confirma tus datos en el laboratorio de Beakman",
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
            return _html("Este enlace ya no sirve", ENLACE_USADO, 400)
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
            self.db.contar("presentado")
            return _html("¡Hecho!", f"<p class='lead'>Encantado, {html.escape(datos['nombre'])}. Vuelve a Claude: "
                                    "Beakman ya sabe cómo saludarte.</p>")
        if not sol["redirect"]:
            self._codigo(sol, self.db.guardar_persona(datos))
            self.db.contar("entrada_con_datos")
        return _html("¡Hecho!", "<p class='lead'>Ya estás dentro del laboratorio. Vuelve a la ventana de Claude: "
                                "se conecta sola en unos segundos.</p><p>Puedes cerrar esta pestaña.</p>")

    # ---- «Mis datos»: entrar con un enlace mágico ------------------------------------------
    # Solo para quien ya tiene entrada con datos: aquí no se crea nada. El enlace solo se manda a correos que ya
    # están, y la respuesta es la misma estén o no, para que nadie pueda averiguar quién usa el laboratorio.

    COOKIE = "beakman_sesion"
    SESION_TTL = 3600
    ACCESO_TTL = 15 * 60

    def _sesion(self, request: Request):
        token = request.cookies.get(self.COOKIE, "")
        row = self.db.one("SELECT * FROM sesiones WHERE hash = ? AND caduca > ?", _hash(token), time.time()) \
            if token else None
        return row if row and self.db.ficha(row["persona_id"]) else None

    def _con_cookie(self, resp: Response, token: str | None) -> Response:
        resp.set_cookie(self.COOKIE, token or "", max_age=self.SESION_TTL if token else 0, path="/cuenta",
                        httponly=True, secure=self.base.startswith("https://"), samesite="lax")
        return resp

    async def cuenta(self, request: Request) -> Response:
        ses = self._sesion(request)
        if not ses:
            return _html("Mis datos", _form_cuenta(self.turnstile_site))
        aviso = request.query_params.get("ok", "")
        return _html("Mis datos", _panel(self.db.ficha(ses["persona_id"]), ses["csrf"], AVISOS.get(aviso, "")))

    async def pedir_enlace(self, request: Request) -> Response:
        form = await request.form()
        correo = _normaliza_correo(str(form.get("correo", "")))[:120]
        ip = self._ip(request)
        if "@" not in correo or "." not in correo.split("@")[-1]:
            return _html("Mis datos", _form_cuenta(self.turnstile_site, "El correo no parece válido."), 400)
        if not await turnstile_ok(self.turnstile_secret, str(form.get("cf-turnstile-response", "")), ip):
            return _html("Mis datos", _form_cuenta(self.turnstile_site, "No he podido comprobar que no eres un robot. "
                                                   "Inténtalo otra vez."), 400)
        if not self.limites.permite(f"cuenta-ip:{ip}", 5, 3600):
            return _html("Mis datos", _form_cuenta(self.turnstile_site, "Demasiados intentos. Espera un rato."), 429)
        pid = self.db.persona_por_correo(correo)
        if pid and self.limites.permite(f"cuenta-correo:{_buzon(correo)}", 3, 3600):
            self.db.limpiar()
            token = secrets.token_urlsafe(32)
            self.db.q("INSERT INTO accesos VALUES (?, ?, ?)", _hash(token), pid, time.time() + self.ACCESO_TTL)
            self.db.contar("mis_datos_enlace")
            nombre = self.db.ficha(pid)["nombre"]
            self._correo(correo, nombre, "Tu enlace para entrar en «Mis datos»", "Entra en «Mis datos»",
                         "Pulsa el botón para ver, cambiar o borrar lo que el laboratorio guarda de ti. Sirve una "
                         "sola vez y caduca en 15 minutos.", "Entrar en mis datos",
                         f"{self.base}/cuenta/entrar?t={token}", caduca="15 minutos")
        return _html("Mira tu correo", "<p class='lead'>Si ese correo tiene entrada en el laboratorio, te llega un "
                                       "enlace para entrar. Sirve una vez y caduca en 15 minutos.</p>" + AYUDA)

    async def entrar(self, request: Request) -> Response:
        t = request.query_params.get("t", "")
        row = self.db.one("SELECT * FROM accesos WHERE hash = ? AND caduca > ?", _hash(t), time.time()) if t else None
        if not row:
            return _html("Este enlace ya no sirve", "<p class='lead'>Este enlace ya se ha usado o ha caducado.</p>"
                         "<p><a href='/cuenta'>Pide otro en «Mis datos»</a>.</p>", 400)
        self.db.q("DELETE FROM accesos WHERE hash = ?", _hash(t))  # un solo uso
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(16)
        self.db.q("INSERT INTO sesiones VALUES (?, ?, ?, ?)", _hash(token), row["persona_id"], csrf,
                  time.time() + self.SESION_TTL)
        return self._con_cookie(RedirectResponse("/cuenta", status_code=303), token)

    async def cambiar(self, request: Request) -> Response:
        """Los botones del panel. Cada uno lleva el token anti-falsificación de la sesión."""
        ses = self._sesion(request)
        form = await request.form()
        if not ses or not secrets.compare_digest(str(form.get("csrf", "")), ses["csrf"]):
            return RedirectResponse("/cuenta", status_code=303)
        pid, accion, f = ses["persona_id"], str(form.get("accion", "")), self.db.ficha(ses["persona_id"])
        error = ""
        if accion == "datos":
            try:
                curso = _curso_valido(str(form.get("curso", ""))) if form.get("curso") else None
                comunidad = _comunidad_valida(str(form.get("comunidad", ""))) if form.get("comunidad") else None
                self.db.guardar_progreso(pid, curso, comunidad)
                nombre = " ".join(str(form.get("nombre", "")).split())[:40]
                if nombre and f["correo"]:
                    self.db.q("UPDATE contactos SET nombre = ? WHERE persona_id = ?", nombre, pid)
                return RedirectResponse("/cuenta?ok=datos", status_code=303)
            except ValueError as exc:
                error = str(exc)
        elif accion == "correo":
            nuevo = _normaliza_correo(str(form.get("correo", "")))[:120]
            if "@" not in nuevo or "." not in nuevo.split("@")[-1]:
                error = "El correo nuevo no parece válido."
            elif nuevo == f["correo"]:
                error = "Ese ya es tu correo."
            elif self.db.persona_por_correo(nuevo):
                error = "Ese correo ya está en otra entrada del laboratorio."
            elif not self.limites.permite(f"cuenta-cambio:{pid}", 3, 3600):
                error = "Demasiados cambios seguidos. Espera un rato."
            else:
                confirmacion = secrets.token_urlsafe(24)
                datos = {"correo": nuevo, "nombre": f["nombre"], "curso": f["curso"], "comunidad": f["comunidad"]}
                self.db.q("INSERT INTO solicitudes (id, tipo, persona_id, creada, datos, confirmacion) "
                          "VALUES (?, ?, ?, ?, ?, ?)", secrets.token_urlsafe(24), "presentarse", pid, time.time(),
                          json.dumps(datos), _hash(confirmacion))
                self._correo(nuevo, None, "Confirma tu correo nuevo en el laboratorio de Beakman",
                             "Confirma tu correo nuevo", "Has pedido que el laboratorio use este correo. Pulsa el "
                             "botón para confirmarlo; hasta entonces seguimos con el de antes.", "Confirmar este correo",
                             f"{self.base}/entrada/confirmar?t={confirmacion}")
                return RedirectResponse("/cuenta?ok=correo", status_code=303)
        elif accion == "sin-correos":
            self.db.quitar_contacto(pid)
            self.db.q("DELETE FROM sesiones WHERE persona_id = ?", pid)
            return self._con_cookie(_html("Hecho", "<p class='lead'>He borrado tu nombre y tu correo. Beakman sigue "
                                          "funcionando en Claude, sin datos, y no te escribiré más.</p>" + AYUDA), None)
        elif accion == "borrar":
            if form.get("seguro") != "si":
                error = "Marca la casilla para confirmar que quieres borrarlo todo."
            else:
                self.db.olvidar(pid)
                return self._con_cookie(_html("Borrado", "<p class='lead'>He borrado todo lo que el laboratorio "
                                              "guardaba de ti. Si Beakman sigue conectado en Claude, ya no sabe quién "
                                              "eres.</p>" + AYUDA), None)
        elif accion == "salir":
            self.db.q("DELETE FROM sesiones WHERE hash = ?", _hash(request.cookies.get(self.COOKIE, "")))
            return self._con_cookie(RedirectResponse("/cuenta", status_code=303), None)
        return _html("Mis datos", _panel(self.db.ficha(pid), ses["csrf"], error=error), 400 if error else 200)

    # ---- administración: /admin ----------------------------------------------------------
    # Dos llaves: correo + contraseña (huella scrypt en BEAKMAN_ADMIN_HASH) y, después, un enlace a ese correo. Sin la
    # contraseña no sale ningún correo. Sesión de 1 hora, cookie solo para /admin y SameSite=Lax (con Strict, el
    # navegador no la manda al volver desde el enlace del correo, que viene de otra web, y se entra en bucle).

    ADMIN_COOKIE = "beakman_admin"

    def _admin_activo(self) -> bool:
        return bool(self.admins and self.admin_hash)

    def _admin_sesion(self, request: Request):
        t = request.cookies.get(self.ADMIN_COOKIE, "")
        return self.db.one("SELECT * FROM admin_sesiones WHERE hash = ? AND caduca > ?", _hash(t), time.time()) \
            if t else None

    def _admin_cookie(self, resp: Response, token: str | None) -> Response:
        resp.set_cookie(self.ADMIN_COOKIE, token or "", max_age=self.SESION_TTL if token else 0, path="/admin",
                        httponly=True, secure=self.base.startswith("https://"), samesite="lax")
        return resp

    async def admin(self, request: Request) -> Response:
        if not self._admin_activo():
            return Response("Not Found", status_code=404)
        ses = self._admin_sesion(request)
        if not ses:
            return _html("Administración", _form_admin(self.turnstile_site))
        vista = request.query_params.get("v", "cifras")
        cuerpo = (self._vista_entradas(request.query_params.get("q", ""), ses["csrf"],
                                       request.query_params.get("ok", ""))
                  if vista == "entradas" else self._vista_cifras())
        return _html("Administración", _admin_menu(vista, ses["csrf"]) + cuerpo)

    async def admin_pedir(self, request: Request) -> Response:
        if not self._admin_activo():
            return Response("Not Found", status_code=404)
        form = await request.form()
        ip = self._ip(request)
        if not self.limites.permite(f"admin-ip:{ip}", 5, 3600):
            return _html("Administración", _form_admin(self.turnstile_site, "Demasiados intentos. Espera un rato."), 429)
        if not await turnstile_ok(self.turnstile_secret, str(form.get("cf-turnstile-response", "")), ip):
            return _html("Administración", _form_admin(self.turnstile_site, "No he podido comprobar que no eres un "
                                                       "robot."), 400)
        correo = _normaliza_correo(str(form.get("correo", "")))
        bien = _buzon(correo) in self.admins and verificar_clave(str(form.get("clave", "")), self.admin_hash)
        if not bien:
            log.warning("administración: intento de entrada fallido")
            return _html("Administración", _form_admin(self.turnstile_site, "Correo o contraseña incorrectos."), 400)
        token = secrets.token_urlsafe(32)
        self.db.q("INSERT INTO admin_accesos VALUES (?, ?, ?)", _hash(token), correo, time.time() + self.ACCESO_TTL)
        self._correo(correo, None, "Tu enlace de administración de Beakman", "Entrar en la administración",
                     "Pulsa el botón para terminar de entrar. Sirve una vez y caduca en 15 minutos. Si no has sido tú, "
                     "alguien conoce tu contraseña: cámbiala.", "Entrar", f"{self.base}/admin/entrar?t={token}",
                     caduca="15 minutos")
        return _html("Mira tu correo", "<p class='lead'>Contraseña correcta. Te he mandado un enlace para terminar de "
                                       "entrar: sirve una vez y caduca en 15 minutos.</p>")

    async def admin_entrar(self, request: Request) -> Response:
        if not self._admin_activo():
            return Response("Not Found", status_code=404)
        t = request.query_params.get("t", "")
        row = self.db.one("SELECT * FROM admin_accesos WHERE hash = ? AND caduca > ?", _hash(t), time.time()) \
            if t else None
        if not row:
            return _html("Este enlace ya no sirve", "<p class='lead'>Este enlace ya se ha usado o ha caducado.</p>"
                         "<p><a href='/admin'>Vuelve a entrar</a>.</p>", 400)
        self.db.q("DELETE FROM admin_accesos WHERE hash = ?", _hash(t))
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(16)
        self.db.q("INSERT INTO admin_sesiones VALUES (?, ?, ?)", _hash(token), csrf, time.time() + self.SESION_TTL)
        log.info("administración: sesión abierta")
        return self._admin_cookie(RedirectResponse("/admin", status_code=303), token)

    async def admin_accion(self, request: Request) -> Response:
        if not self._admin_activo():
            return Response("Not Found", status_code=404)
        ses = self._admin_sesion(request)
        form = await request.form()
        if not ses or not secrets.compare_digest(str(form.get("csrf", "")), ses["csrf"]):
            return RedirectResponse("/admin", status_code=303)
        accion, pid = str(form.get("accion", "")), str(form.get("pid", ""))
        if accion == "salir":
            self.db.q("DELETE FROM admin_sesiones WHERE hash = ?", _hash(request.cookies.get(self.ADMIN_COOKIE, "")))
            return self._admin_cookie(RedirectResponse("/admin", status_code=303), None)
        if accion == "correo":
            nuevo = _normaliza_correo(str(form.get("correo", "")))[:120]
            otra = self.db.persona_por_correo(nuevo)
            if "@" not in nuevo or (otra and otra != pid) or not self.db.ficha(pid):
                return RedirectResponse("/admin?v=entradas&ok=error", status_code=303)
            self.db.q("UPDATE contactos SET correo = ? WHERE persona_id = ?", nuevo, pid)
            log.info("administración: correo cambiado en una entrada")
            return RedirectResponse("/admin?v=entradas&ok=correo", status_code=303)
        if accion == "borrar" and form.get("seguro") == "si" and self.db.ficha(pid):
            self.db.olvidar(pid)
            log.info("administración: entrada borrada")
            return RedirectResponse("/admin?v=entradas&ok=borrada", status_code=303)
        return RedirectResponse("/admin?v=entradas&ok=error", status_code=303)

    def _vista_cifras(self) -> str:
        """Cuánto se usa Beakman: contadores por semana, sin nada de nadie."""
        c = self.db.cifras()
        cols = [("entrada_con_datos", "Con datos"), ("entrada_sin_datos", "Sin datos"), ("clases", "Clases"),
                ("presentado", "Correo"), ("sin_correo", "Sin correo"), ("borrado", "Borran")]
        filas = ""
        for semana, v in c["semanas"].items():
            v = dict(v, clases=sum(n for k, n in v.items() if k.startswith("clase:")))
            filas += f"<tr><td>{semana[5:]} · {semana[:4]}</td>" + "".join(f"<td>{v.get(k, 0)}</td>" for k, _ in cols) + "</tr>"
        asign = {}
        for v in c["semanas"].values():
            for k, n in v.items():
                if k.startswith("clase:"):
                    asign[k[6:]] = asign.get(k[6:], 0) + n
        por_asig = " · ".join(f"{html.escape(k)}: {n}" for k, n in sorted(asign.items(), key=lambda x: -x[1])) or "—"
        cab = "".join(f"<th>{t}</th>" for _, t in cols)
        return f"""<h1>Cifras</h1>
<p class="lead">Ahora mismo hay <b>{c['entradas']['con_datos']}</b> entradas con datos y <b>{c['entradas']['sin_datos']}</b>
sin datos. Debajo, lo que ha pasado cada semana.</p>
<div class="card" style="overflow-x:auto"><table class="cifras"><tr><th>Semana</th>{cab}</tr>{filas or
'<tr><td colspan="7">Aún no hay nada que contar.</td></tr>'}</table></div>
<p class="hint" style="margin-top:12px"><b>Con datos / Sin datos:</b> entradas nuevas. <b>Correo:</b> se presentan o
cambian de correo. <b>Sin correo:</b> borran nombre y correo. <b>Borran:</b> lo borran todo.<br>
Clases por asignatura, en estas semanas: {por_asig}.</p>"""

    def _entradas_sin_datos(self) -> str:
        """Las entradas sin datos: no tienen nada personal, solo cuándo se crearon, el curso y la comunidad elegidos y
        si siguen conectadas (con un token vivo). Y las solicitudes con correo que nadie ha confirmado todavía."""
        filas = self.db.q(
            "SELECT p.creada, pr.curso, pr.comunidad, "
            "EXISTS (SELECT 1 FROM tokens t WHERE t.persona_id = p.id AND t.caduca > ?) AS conectada "
            "FROM personas p LEFT JOIN progreso pr ON pr.persona_id = p.id "
            "WHERE p.id NOT IN (SELECT persona_id FROM contactos) ORDER BY p.creada DESC LIMIT 200", int(time.time()))
        pend = self.db.one("SELECT COUNT(*) AS n FROM solicitudes WHERE datos IS NOT NULL AND redirect IS NULL "
                           "AND tipo = 'entrar'")["n"]
        tabla = "".join(
            f"<tr><td>{html.escape(f['creada'][:16].replace('T', ' '))}</td>"
            f"<td>{html.escape(CURSOS.get(f['curso'] or '', '—'))}</td><td>{html.escape(f['comunidad'] or '—')}</td>"
            f"<td>{'sí' if f['conectada'] else 'no'}</td></tr>" for f in filas)
        return f"""<h2 style="margin-top:22px">Sin datos</h2>
<p class="hint">Sin nombre ni correo: solo cuándo se creó (UTC), lo que eligió y si sigue conectada. Para darle datos,
que diga en Claude «quiero presentarme». Solicitudes con correo sin confirmar ahora mismo: <b>{pend}</b> (caducan a la
media hora).</p>
<div class="card" style="overflow-x:auto"><table class="cifras"><tr><th>Creada</th><th>Curso</th><th>Comunidad</th>
<th>Conectada</th></tr>{tabla or '<tr><td colspan="4">Ninguna.</td></tr>'}</table></div>"""

    def _vista_entradas(self, q: str, csrf: str, ok: str) -> str:
        """Las entradas con datos, para dar soporte (cambiar un correo, borrar a petición de la familia)."""
        q = q.strip().lower()[:80]
        filas = self.db.q("SELECT c.persona_id, c.nombre, c.correo, c.consentimiento_fecha, p.curso, p.comunidad "
                          "FROM contactos c LEFT JOIN progreso p ON p.persona_id = c.persona_id "
                          "WHERE ? = '' OR lower(c.correo) LIKE ? OR lower(c.nombre) LIKE ? "
                          "ORDER BY c.consentimiento_fecha DESC LIMIT 200", q, f"%{q}%", f"%{q}%")
        sin = self.db.one("SELECT COUNT(*) AS n FROM personas WHERE id NOT IN (SELECT persona_id FROM contactos)")["n"]
        oculto = f'<input type="hidden" name="csrf" value="{html.escape(csrf)}">'
        avisos = {"correo": "Correo cambiado.", "borrada": "Entrada borrada.",
                  "error": "No se ha podido: revisa el correo (¿ya lo usa otra entrada?)."}
        msg = f"<div class='{'errores' if ok == 'error' else 'ok'}'><p>{avisos[ok]}</p></div>" if ok in avisos else ""
        cuerpo = ""
        for f in filas:
            pid = html.escape(f["persona_id"])
            cuerpo += f"""<div class="card" style="margin-bottom:12px">
<b>{html.escape(f['nombre'])}</b> · {html.escape(f['correo'])}<br>
<span class="hint">{html.escape(CURSOS.get(f['curso'] or '', '') or 'sin curso')} · {html.escape(f['comunidad'] or 'sin comunidad')} ·
desde el {html.escape((f['consentimiento_fecha'] or '')[:10])}</span>
<form method="post" action="/admin/accion" style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">{oculto}
<input type="hidden" name="accion" value="correo"><input type="hidden" name="pid" value="{pid}">
<input type="email" name="correo" placeholder="Correo nuevo" required style="flex:1;min-width:180px">
<button class="btn ghost" type="submit" style="margin-top:0">Cambiar correo</button></form>
<form method="post" action="/admin/accion" style="display:flex;gap:8px;margin-top:8px;align-items:center;flex-wrap:wrap">{oculto}
<input type="hidden" name="accion" value="borrar"><input type="hidden" name="pid" value="{pid}">
<label class="check" style="margin:0"><input type="checkbox" name="seguro" value="si" required><span>Borrar todo</span></label>
<button class="btn ghost" type="submit" style="margin-top:0">Borrar</button></form>
</div>"""
        return f"""<h1>Entradas</h1>
<p class="lead"><b>{len(filas)}</b> con datos{' que coinciden' if q else ''} y <b>{sin}</b> sin datos (de esas no hay nada
que enseñar). Cambiar el correo aquí no pide confirmación: hazlo solo si te lo pide la familia.</p>
<form method="get" action="/admin" style="display:flex;gap:8px;margin-bottom:14px"><input type="hidden" name="v" value="entradas">
<input type="text" name="q" value="{html.escape(q)}" placeholder="Buscar por nombre o correo" style="flex:1">
<button class="btn ghost" type="submit" style="margin-top:0">Buscar</button></form>
{msg}{cuerpo or '<p>No hay ninguna.</p>'}
{self._entradas_sin_datos()}"""

    async def borrar_pagina(self, request: Request) -> Response:
        """La página vieja de borrar: ahora se borra desde «Mis datos»."""
        return RedirectResponse("/cuenta", status_code=303)

    # ---- correo -------------------------------------------------------------------

    def _correo(self, correo: str, nombre: str | None, asunto: str, titulo: str, intro: str, boton: str, enlace: str,
                caduca: str = "media hora"):
        """Correo de Beakman, con textos fijos. `nombre` solo para direcciones ya confirmadas: a una sin confirmar no
        va nada escrito por quien rellenó el formulario, para que nadie pueda usarnos para mandar su texto a otros."""
        # Tope para todo el servidor, además de los límites por IP y por correo: nunca correos a lo loco.
        if not self.limites.permite("correos-servidor", 60, 3600):
            log.error("tope de correos del servidor alcanzado: no se envía «%s»", asunto)
            return
        hola = f"¡Hola, {nombre}!" if nombre else "¡Hola!"
        texto = (f"{hola}\n\n{intro}\n{enlace}\n\nEl enlace caduca en {caduca}. Si no has sido tú, no hagas nada.\n\n"
                 "Un abrazo con la bata puesta,\nBeakman")
        cuerpo = (MAIL_HTML.replace("{hola}", html.escape(hola)).replace("{titulo}", html.escape(titulo))
                  .replace("{intro}", html.escape(intro)).replace("{boton}", html.escape(boton))
                  .replace("{enlace}", html.escape(enlace)).replace("{caduca}", html.escape(caduca)))
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
<link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/img/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
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
.why { background: var(--lime-soft); border: 1.5px solid var(--lime); border-radius: 14px; padding: 12px 16px; margin: 0 0 16px; font-size: .93rem; }
.why ul { margin: 6px 0 0; padding-left: 20px; }
.why li { margin-bottom: 5px; }
.alt { margin-top: 22px; padding-top: 16px; border-top: 1.5px dashed var(--line); }
.alt p { font-size: .92rem; color: var(--muted); margin: 4px 0 0; }
.btn.ghost { background: #fff; }
a { color: var(--ink); text-decoration-color: var(--lime); text-decoration-thickness: 2px; }
.btn { display: inline-flex; margin-top: 18px; background: var(--lime); color: var(--ink); font: 800 1rem "Nunito", sans-serif;
  border: 2px solid var(--ink); border-radius: 999px; padding: 10px 20px; box-shadow: 3px 3px 0 var(--ink); cursor: pointer; }
.ok { background: var(--lime-soft); border: 1.5px solid var(--lime); border-radius: 12px; padding: 10px 14px; margin-bottom: 12px; color: var(--ink); }
.ok p { margin: 0; }
h2 { font: 600 1.2rem/1.2 "Fredoka", sans-serif; color: var(--ink); margin: 6px 0 6px; }
.card h2:not(:first-child) { margin-top: 16px; }
.card ol, .card ul { margin: 0; padding-left: 20px; font-size: .95rem; }
.card li { margin-bottom: 6px; }
.cifras { border-collapse: collapse; width: 100%; font-size: .84rem; }
.cifras th, .cifras td { white-space: nowrap; padding: 5px 5px; border-bottom: 1px solid var(--line); text-align: right; }
.cifras th:first-child, .cifras td:first-child { text-align: left; }
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
<p style="margin:0 0 14px;color:#4E5A45;font-size:14px;">El enlace caduca en {caduca}. Si no has sido tú, no hagas nada: sin confirmar no cambia nada.</p>
<p style="margin:0 0 4px;">Un abrazo con la bata puesta,</p>
<p style="margin:0 0 20px;font-size:20px;font-weight:800;color:#1F3A0B;">Beakman</p></td></tr>
</table></td></tr></table></body></html>
"""


def _html(titulo: str, cuerpo: str, status: int = 200, head: str = "") -> HTMLResponse:
    page = PAGE.replace("{titulo}", html.escape(titulo)).replace("{head}", head).replace("{cuerpo}", cuerpo)
    return HTMLResponse(page, status_code=status, headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY"})


CADUCADA = "<p>Vuelve a Claude y pulsa otra vez <b>Conectar</b>.</p>"
# Los enlaces de los correos son de un solo uso y caducan a la media hora: pulsarlo otra vez no es un error.
ENLACE_USADO = ("<p class='lead'>Este enlace ya se ha usado o ha caducado.</p><p>Si ya estás conectado en Claude, no "
                "tienes que hacer nada. Si no, vuelve a Claude y pulsa <b>Conectar</b>.</p>")
CAMBIAR = ("<p class='note'>¿Quieres cambiar de opción más adelante? En Claude, ve a Ajustes → Conectores, desconecta "
           "Beakman y vuelve a conectarlo: esta página saldrá otra vez. También puedes pedírselo a Beakman en el chat "
           "(«quiero presentarme», «olvídame»). Y si ya diste tus datos y quieres borrarlos sin entrar en Claude: "
           "<a href='/cuenta'>Mis datos</a>.</p>")


def huella_clave(clave: str) -> str:
    """Huella scrypt de una contraseña: «scrypt:n:r:p:sal:huella» (sal y huella en hex)."""
    sal = secrets.token_bytes(16)
    n, r, p = 2 ** 15, 8, 1
    h = hashlib.scrypt(clave.encode(), salt=sal, n=n, r=r, p=p, maxmem=64 * 1024 * 1024)
    return f"scrypt:{n}:{r}:{p}:{sal.hex()}:{h.hex()}"


def verificar_clave(clave: str, huella: str) -> bool:
    try:
        _, n, r, p, sal, h = huella.split(":")
        calc = hashlib.scrypt(clave.encode(), salt=bytes.fromhex(sal), n=int(n), r=int(r), p=int(p),
                              maxmem=64 * 1024 * 1024)
        return secrets.compare_digest(calc.hex(), h)
    except (ValueError, TypeError):
        return False


def _form_admin(site_key: str, error: str = "") -> str:
    err = f"<div class='errores'><p>{html.escape(error)}</p></div>" if error else ""
    return f"""<h1>Administración</h1>
<p class="lead">Correo y contraseña. Después te llega un enlace al correo para terminar de entrar.</p>
{err}<form class="card" method="post" action="/admin">
<label for="correo">Correo</label>
<input type="email" id="correo" name="correo" maxlength="120" required autocomplete="username">
<label for="clave">Contraseña</label>
<input type="password" id="clave" name="clave" maxlength="200" required autocomplete="current-password"
  style="width:100%;font:400 1rem Nunito,sans-serif;padding:9px 12px;border:2px solid var(--line);border-radius:12px">
{_turnstile(site_key)}
<button class="btn" type="submit">Entrar</button>
</form>"""


def _admin_menu(vista: str, csrf: str) -> str:
    def a(v, t):
        estilo = "font-weight:800;text-decoration-thickness:3px" if v == vista else ""
        return f'<a href="/admin?v={v}" style="{estilo}">{t}</a>'
    return f"""<nav style="display:flex;gap:16px;align-items:center;margin-bottom:14px">{a("cifras", "Cifras")}{a("entradas", "Entradas")}
<form method="post" action="/admin/accion" style="margin-left:auto"><input type="hidden" name="csrf" value="{html.escape(csrf)}">
<input type="hidden" name="accion" value="salir"><button class="btn ghost" type="submit" style="margin-top:0">Salir</button></form></nav>"""


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
<p>Entra sin datos: Beakman no sabrá tu nombre ni podrá escribiros, no podrás usar «Mis datos» y, si vuelves a
conectar, empezarás de cero. El curso y la comunidad, si los eliges arriba, sí se guardan (no dicen quién eres). Podrás
presentarte cuando quieras.</p>
<button class="btn ghost" type="submit" name="modo" value="sin-datos" formnovalidate>Entrar sin datos</button></div>""" \
        if anonima else ""
    return f"""<h1>¡Hola! Antes de empezar, preséntate</h1>
<p class="lead">Lo rellena un adulto. Solo necesito un nombre para saludar y un correo para comunicarme con vosotros.</p>
{POR_QUE_CORREO}
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


# Por qué merece la pena dar el correo. Solo lo que es verdad hoy (ver guardar_persona y «Mis datos»).
POR_QUE_CORREO = """<div class="why"><b>¿Para qué el correo?</b>
<ul>
<li><b>Te reconozco en cualquier sitio.</b> Si cambias de ordenador o vuelves a conectar Beakman, entras con el mismo
correo y sigo sabiendo tu nombre y tu curso. Sin correo, cada conexión nueva empieza de cero.</li>
<li><b>Tus datos, siempre a mano.</b> Con el correo entras en «Mis datos» para verlos, cambiarlos o borrarlos, sin pasar
por Claude. Sin correo, solo puedes hacerlo desde el chat.</li>
<li><b>Puedo escribiros.</b> Resúmenes de los temas, recordatorios de repaso y novedades del laboratorio, siempre al
correo de un adulto y con baja en cualquier momento.</li>
</ul></div>"""
CONECTAR = """<h2>¿Aún no tienes Beakman en Claude?</h2>
<ol>
<li>En claude.ai, ve a <b>Ajustes → Conectores → Agregar conector personalizado</b>.</li>
<li>Nombre: <b>beakman</b>. Dirección: <b>https://beakman.kademy.net/mcp</b>. Deja lo que Claude marca solo («Iniciar
sesión ahora» y «Registrar automáticamente») y pulsa <b>Agregar</b>, y luego <b>Conectar</b>.</li>
<li>Se abre mi página: entra <b>con datos</b> (nombre, correo, curso y comunidad) o <b>sin datos</b>.</li>
<li>En un chat nuevo: «Quiero estudiar historia con Beakman».</li>
</ol>"""
CAMBIOS = """<h2>¿Quieres cambiar de opción?</h2>
<ul>
<li><b>Entraste sin datos y ahora quieres darlos:</b> en Claude, dile a Beakman «quiero presentarme» y te da un enlace.
O en <b>Ajustes → Conectores → beakman</b>, pulsa Desconectar y Conectar, y elige «Entrar al laboratorio».</li>
<li><b>Quieres dejar de dar datos:</b> aquí mismo, «No quiero más correos» (sigues usando Beakman, sin datos) o
«Borrar todo». También en el chat: «no quiero más correos» u «olvídame».</li>
<li><b>Desconectar no borra:</b> quitar el conector en Claude no borra tus datos. Para borrarlos, usa esta página o
«olvídame».</li>
</ul>"""
AYUDA = f"<div class='card' style='margin-top:18px'>{CONECTAR}{CAMBIOS}</div>"
AVISOS = {"datos": "Guardado.", "correo": "Te he mandado un correo a tu dirección nueva: confírmalo desde allí. "
                                            "Hasta entonces seguimos con la de antes."}


def _form_cuenta(site_key: str, error: str = "") -> str:
    err = f"<div class='errores'><p>{html.escape(error)}</p></div>" if error else ""
    return f"""<h1>Mis datos</h1>
<p class="lead">Escribe el correo con el que entraste en el laboratorio. Te llega un enlace para ver, cambiar o borrar
lo que guardo de ti. Sin contraseñas.</p>
{err}<form class="card" method="post" action="/cuenta">
<label for="correo">Correo</label>
<input type="email" id="correo" name="correo" maxlength="120" required autocomplete="email">
{_turnstile(site_key)}
<button class="btn" type="submit">Mándame el enlace</button>
</form>
<p class="note">Solo sirve si entraste <b>con datos</b>. Si entraste sin datos, no tengo ningún correo tuyo: gestiónalo
desde el chat, o preséntate («quiero presentarme») para poder usar esta página. Pedir el enlace no guarda nada.</p>
{AYUDA}"""


def _panel(f: dict, csrf: str, aviso: str = "", error: str = "") -> str:
    def opt(valor, texto, actual):
        return f'<option value="{html.escape(valor)}"{" selected" if valor == actual else ""}>{html.escape(texto)}</option>'
    cursos = "".join(opt(k, n, f["curso"] or "") for k, n in CURSOS.items())
    comunidades = "".join(opt(c, c, f["comunidad"] or "") for c in COMUNIDADES)
    oculto = f'<input type="hidden" name="csrf" value="{html.escape(csrf)}">'
    msg = (f"<div class='ok'><p>{html.escape(aviso)}</p></div>" if aviso else "") + \
          (f"<div class='errores'><p>{html.escape(error)}</p></div>" if error else "")
    escolar = f" (curso {html.escape(f['curso_escolar'])})" if f["curso_escolar"] else ""
    return f"""<h1>Mis datos</h1>
<p class="lead">Esto es todo lo que el laboratorio guarda de ti. Nada más: ni apellidos, ni edad, ni colegio, ni lo que
escribes en Claude.</p>
{msg}<form class="card" method="post" action="/cuenta/cambiar">{oculto}<input type="hidden" name="accion" value="datos">
<label for="nombre">Nombre para el saludo</label>
<input type="text" id="nombre" name="nombre" maxlength="40" value="{html.escape(f['nombre'] or '')}">
<label for="curso">Curso{escolar}</label>
<select id="curso" name="curso"><option value="">Sin indicar</option>{cursos}</select>
<label for="comunidad">Comunidad autónoma</label>
<select id="comunidad" name="comunidad"><option value="">Sin indicar</option>{comunidades}</select>
<p class="hint">Aceptaste guardarlos el {html.escape((f['consentimiento_fecha'] or '')[:10])}.</p>
<button class="btn" type="submit">Guardar cambios</button>
</form>
<form class="card" method="post" action="/cuenta/cambiar" style="margin-top:16px">{oculto}<input type="hidden" name="accion" value="correo">
<label for="correo">Correo</label>
<p class="hint" style="margin:0 0 6px">Ahora: <b>{html.escape(f['correo'] or '')}</b>. Para cambiarlo, escribe el nuevo y
confírmalo desde allí.</p>
<input type="email" id="correo" name="correo" maxlength="120" required autocomplete="email">
<button class="btn ghost" type="submit">Cambiar el correo</button>
</form>
<form class="card" method="post" action="/cuenta/cambiar" style="margin-top:16px">{oculto}<input type="hidden" name="accion" value="sin-correos">
<b>No quiero más correos</b>
<p class="hint">Borra tu nombre y tu correo. Beakman sigue funcionando en Claude, sin datos.</p>
<button class="btn ghost" type="submit">Borrar nombre y correo</button>
</form>
<form class="card" method="post" action="/cuenta/cambiar" style="margin-top:16px">{oculto}<input type="hidden" name="accion" value="borrar">
<b>Borrar todo</b>
<p class="hint">Borra todo lo que el laboratorio guarda de ti y desconecta Beakman en Claude. No se puede deshacer.</p>
<label class="check"><input type="checkbox" name="seguro" value="si"><span>Sí, quiero borrarlo todo.</span></label>
<button class="btn ghost" type="submit">Borrarlo todo</button>
</form>
<form method="post" action="/cuenta/cambiar" style="margin-top:16px">{oculto}<input type="hidden" name="accion" value="salir">
<button class="btn ghost" type="submit">Salir</button>
</form>
{AYUDA}"""


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
