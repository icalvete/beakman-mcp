"""Cuánto se usa Beakman fuera de Claude: visitas a las páginas del laboratorio y de la web, y los «Ponte a prueba».

Solo se suma 1 a un contador por día y clave (ver Db.contar): ni quién, ni desde dónde, ni cookies, ni IP.
- Visitas: al servir una página HTML (GET, 200 o 304) que no pide un robot. Las imágenes, el CSS y el JS no cuentan.
- «Ponte a prueba»: la propia página (lab/site/cuenta.js) avisa con un POST a /_cuenta cuando se empieza una sección o
  se marcan las 12 preguntas. Solo valen claves de una lista cerrada, sacada de las páginas que hay.
Sin base de datos (sin entrada), no cuenta nada.
"""
from __future__ import annotations

import html
import logging
import os
import re
from collections.abc import Callable

from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger(__name__)

# Lo que se llama para contar; lo pone server.py cuando hay base de datos.
_contar: Callable[[str], None] | None = None

ROBOTS = re.compile(r"bot|crawl|spider|slurp|preview|fetch|scan|monitor|curl|wget|python|httpx|go-http|java/|"
                    r"headless|lighthouse|facebookexternalhit|whatsapp|telegram", re.I)
_TITULO = re.compile(r"<title>(.*?)</title>", re.S | re.I)
_SECCION = re.compile(r'<section class="block" id="([a-z0-9-]+)">\s*<h2>(.*?)</h2>', re.S)
_ETIQUETAS = re.compile(r"<[^>]+>")
COMPLETA = "completa"


def configurar(contar: Callable[[str], None] | None) -> None:
    global _contar
    _contar = contar


def contar(clave: str) -> None:
    if _contar is None:
        return
    try:
        _contar(clave)
    except Exception:  # contar nunca puede tumbar una página
        log.exception("métricas: no se ha podido contar")


def ruta_de_pagina(path: str) -> str | None:
    """La ruta con la que se cuenta una página, o None si no es una página (css, img…)."""
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    if path.endswith("/") or path.endswith(".html"):
        return path
    return None


def es_robot(user_agent: str) -> bool:
    return not user_agent or bool(ROBOTS.search(user_agent))


class ContarVisitas:
    """Envuelve una app ASGI de ficheros estáticos y cuenta `visita:<sitio>:<ruta>` por cada página servida."""

    def __init__(self, app, sitio: str):
        self.app, self.sitio = app, sitio

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "GET":
            return await self.app(scope, receive, send)
        ruta = ruta_de_pagina(scope["path"])
        ua = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"user-agent"), "")
        if ruta is None or es_robot(ua):
            return await self.app(scope, receive, send)

        async def enviar(msg):
            if msg["type"] == "http.response.start" and msg["status"] in (200, 304):
                contar(f"visita:{self.sitio}:{ruta}")
            await send(msg)

        return await self.app(scope, receive, enviar)


def _limpio(texto: str) -> str:
    texto = html.unescape(_ETIQUETAS.sub("", texto))
    return " ".join(texto.split())


def _paginas(directorio: str):
    """(ruta, html) de cada página de un directorio servido."""
    if not directorio or not os.path.isdir(directorio):
        return
    for raiz, _dirs, ficheros in os.walk(directorio):
        for f in ficheros:
            if not f.endswith(".html") or f == "404.html" or f.startswith("_"):
                continue
            rel = "/" + os.path.relpath(os.path.join(raiz, f), directorio).replace(os.sep, "/")
            try:
                with open(os.path.join(raiz, f), encoding="utf-8") as fh:
                    yield ruta_de_pagina(rel), fh.read()
            except OSError:
                continue


class Catalogo:
    """Los títulos de las páginas y las secciones de los «Ponte a prueba», leídos de los HTML que se sirven."""

    def __init__(self, lab_dir: str | None, site_dir: str | None):
        self.titulos: dict[str, dict[str, str]] = {"lab": {}, "web": {}}
        self.pruebas: dict[str, list[tuple[str, str]]] = {}  # ruta → [(id de sección, título)]
        for sitio, directorio in (("lab", lab_dir), ("web", site_dir)):
            for ruta, texto in _paginas(directorio):
                m = _TITULO.search(texto)
                titulo = _limpio(m.group(1)).split(" · ")[0] if m else ruta
                self.titulos[sitio][ruta] = titulo
                if sitio == "lab" and "/ponte-a-prueba" in ruta:
                    self.pruebas[ruta] = [(i, _limpio(t)) for i, t in _SECCION.findall(texto)]

    def clave_prueba(self, ruta: str, que: str) -> str | None:
        """La clave de «Ponte a prueba» si `ruta` y `que` existen; si no, None."""
        secciones = self.pruebas.get(ruta)
        if secciones is None:
            return None
        if que == COMPLETA or que in {i for i, _ in secciones}:
            return f"prueba:{ruta}:{que}"
        return None


catalogo = Catalogo(None, None)


def cargar(lab_dir: str | None, site_dir: str | None) -> None:
    global catalogo
    catalogo = Catalogo(lab_dir, site_dir)


async def cuenta(request: Request) -> Response:
    """POST /_cuenta?p=<ruta>&k=<sección|completa> desde un «Ponte a prueba». Responde 204 siempre que la clave exista."""
    if es_robot(request.headers.get("user-agent", "")):
        return Response(status_code=204)
    clave = catalogo.clave_prueba(request.query_params.get("p", "")[:200], request.query_params.get("k", "")[:40])
    if not clave:
        return Response(status_code=400)
    contar(clave)
    return Response(status_code=204)


# Los nombres de las herramientas del conector, como los ve quien lo usa.
HERRAMIENTAS = {
    "empezar_clase": "Empezar una clase", "mapa_del_curso": "Mapa del curso", "leer_tema": "Leer un tema",
    "buscar_en_temario": "Buscar en el temario", "que_sabes_de_mi": "¿Qué sabes de mí?",
    "cambiar_datos": "Cambiar mis datos", "presentarme": "Presentarme", "no_escribirme": "No escribirme",
    "olvidame": "Olvídame",
}
