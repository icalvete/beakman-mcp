#!/usr/bin/env python3
"""Pruebas del conector MCP de Beakman, en local, en las dos versiones: abierta y con entrada.

Arranca el servidor con uvicorn en un puerto libre y una base de datos temporal, crea dos entradas de prueba
(una con nombre y curso, otra sin datos), les da un token como haría el OAuth y llama a las herramientas como
lo hace claude.ai. Datos inventados; nada sale de la máquina. El temario es el del propio repo.

Uso: python3 scripts/test_conector.py   (necesita las dependencias de mcp/requirements.txt)
El CI lo lanza antes de construir la imagen (.github/workflows/mcp-image.yml), después del contrato.
"""
import asyncio
import os
import socket
import subprocess
import sys
import tempfile
import time

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "mcp"))

ARRANQUE = "Si aún no has llamado a `empezar_clase`"
PIDE_CURSO = "y en qué curso está (1º o 2º de la ESO)"  # lo añade el servidor; «en qué curso» a secas sale en base.md
fallos: list[str] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    print(("  ok   " if ok else "  FALLA ") + nombre)
    if not ok:
        fallos.append(f"{nombre}: {detalle[:400]}")


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def llamar(url: str, token: str | None, herramienta: str, args: dict) -> str:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(headers=headers, timeout=30) as http:
        async with streamable_http_client(url, http_client=http) as st:
            async with ClientSession(st[0], st[1]) as s:
                await s.initialize()
                res = await s.call_tool(herramienta, args)
                return "\n".join(getattr(c, "text", "") for c in res.content)


async def herramientas(url: str, token: str | None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(headers=headers, timeout=30) as http:
        async with streamable_http_client(url, http_client=http) as st:
            async with ClientSession(st[0], st[1]) as s:
                await s.initialize()
                tools = {t.name: t for t in (await s.list_tools()).tools}
                prompts = (await s.list_prompts()).prompts
                return {"tools": tools, "prompts": prompts}


async def pruebas(abierto: str, con_entrada: str, con_datos: str, sin_datos: str) -> None:
    print("Versión abierta")
    t = await llamar(abierto, None, "empezar_clase", {})
    check("«Hola Beakman»: sin argumentos trae a Beakman y pregunta asignatura y curso",
          "INSTRUCCIONES DE BEAKMAN" in t and "qué asignatura" in t and PIDE_CURSO in t, t)
    t = await llamar(abierto, None, "empezar_clase", {"asignatura": "Historia"})
    check("solo la asignatura: pregunta el curso", "Quiere estudiar Historia" in t and "pregunta en qué curso está" in t, t)
    t = await llamar(abierto, None, "empezar_clase", {"asignatura": "Historia", "curso": "2º ESO"})
    check("asignatura y curso: trae los temas", "TEMAS DE 2º ESO" in t, t)
    t = await llamar(abierto, None, "empezar_clase", {"asignatura": "Ciencias", "curso": "2º ESO"})
    check("Ciencias de 2º: pide preguntar la parte", "varias partes" in t, t)
    t = await llamar(abierto, None, "leer_tema", {"asignatura": "Historia", "curso": "2º ESO", "tema": "3"})
    check("leer_tema recuerda arrancar con empezar_clase", ARRANQUE in t, t)
    t = await llamar(abierto, None, "buscar_en_temario", {"consulta": "feudalismo"})
    check("buscar_en_temario encuentra y recuerda arrancar", "Historia" in t and ARRANQUE in t, t)
    lista = await herramientas(abierto, None)
    check("sin prompts", not lista["prompts"], str(lista["prompts"]))

    print("Versión con entrada")
    async with httpx2.AsyncClient(timeout=10) as http:
        r = await http.post(con_entrada, json={})
    check("sin token: 401 con resource_metadata",
          r.status_code == 401 and "resource_metadata" in r.headers.get("www-authenticate", ""), str(r.status_code))
    lista = await herramientas(con_entrada, con_datos)
    lectura = ["empezar_clase", "mapa_del_curso", "leer_tema", "buscar_en_temario", "que_sabes_de_mi"]
    check("las de lectura llevan readOnlyHint",
          all(lista["tools"][n].annotations and lista["tools"][n].annotations.read_only_hint for n in lectura))
    check("olvidame lleva destructiveHint",
          bool(lista["tools"]["olvidame"].annotations and lista["tools"]["olvidame"].annotations.destructive_hint))
    t = await llamar(con_entrada, con_datos, "empezar_clase", {})
    check("con datos, «Hola Beakman»: Beakman, saluda por el nombre y no pregunta el curso",
          "INSTRUCCIONES DE BEAKMAN" in t and "Lucía" in t and "Salúdale por su nombre" in t
          and PIDE_CURSO not in t, t)
    t = await llamar(con_entrada, con_datos, "empezar_clase", {"asignatura": "Historia"})
    check("con datos y asignatura: usa el curso guardado", "TEMAS DE 2º ESO" in t, t)
    t = await llamar(con_entrada, con_datos, "que_sabes_de_mi", {})
    check("que_sabes_de_mi: sus datos y recuerda arrancar", "Lucía" in t and ARRANQUE in t, t)
    t = await llamar(con_entrada, sin_datos, "empezar_clase", {})
    check("sin datos, «Hola Beakman»: Beakman, no pide el nombre y pregunta el curso",
          "INSTRUCCIONES DE BEAKMAN" in t and "no se lo pidas" in t and PIDE_CURSO in t, t)
    t = await llamar(con_entrada, sin_datos, "olvidame", {})
    check("olvidame sin confirmar: pide confirmación", "seguro" in t, t)
    # A mano: el cliente de mcp vuelve a pedir la lista de herramientas tras la llamada, y el token ya no vale.
    async with httpx2.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {sin_datos}",
                                                       "Accept": "application/json, text/event-stream"}) as http:
        r = await http.post(con_entrada, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                               "params": {"name": "olvidame", "arguments": {"confirmado": True}}})
    check("olvidame confirmado: lo borra", r.status_code == 200 and "lo he borrado todo" in r.text, r.text)
    async with httpx2.AsyncClient(timeout=10, headers={"Authorization": f"Bearer {sin_datos}"}) as http:
        r = await http.post(con_entrada, json={})
    check("olvidame confirmado: su token ya no vale (401)", r.status_code == 401, str(r.status_code))


def main() -> int:
    tmp = tempfile.mkdtemp()
    db, puerto = os.path.join(tmp, "pruebas.sqlite"), puerto_libre()
    entrada_url = f"http://127.0.0.1:{puerto}"
    env = {**os.environ, "BEAKMAN_REPO_DIR": REPO, "BEAKMAN_ENTRADA_URL": entrada_url, "BEAKMAN_DB": db,
           "BEAKMAN_ALLOWED_HOSTS": f"localhost:{puerto}", "BEAKMAN_SITE_DIR": tmp, "BEAKMAN_LAB_DIR": tmp}
    for var in ("BEAKMAN_ADMIN_HASH", "BEAKMAN_ADMIN_CORREOS"):
        env.pop(var, None)

    from beakman_mcp.entrada import Entrada  # crea la base con su esquema
    entrada = Entrada(entrada_url, db)
    con_datos = entrada.db.guardar_persona({"correo": "lucia@ejemplo.com", "nombre": "Lucía", "curso": "2eso",
                                            "comunidad": "Aragón"})
    sin_datos = entrada.db.nueva_persona()
    tok_datos = entrada._emitir("prueba-local", con_datos, [], None).access_token
    tok_sin = entrada._emitir("prueba-local", sin_datos, [], None).access_token

    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "beakman_mcp.server:app", "--app-dir",
                            os.path.join(REPO, "mcp"), "--port", str(puerto), "--log-level", "warning"], env=env)
    try:
        for _ in range(60):
            try:
                if httpx2.get(f"http://localhost:{puerto}/up", timeout=1).status_code == 200:
                    break
            except httpx2.HTTPError:
                time.sleep(0.25)
        else:
            print("El servidor no arranca.")
            return 1
        asyncio.run(pruebas(f"http://localhost:{puerto}/mcp", f"{entrada_url}/mcp", tok_datos, tok_sin))
    finally:
        srv.terminate()
        srv.wait(timeout=10)
    if fallos:
        print(f"\n{len(fallos)} pruebas fallan:\n- " + "\n- ".join(fallos))
        return 1
    print("\nTodas las pruebas pasan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
