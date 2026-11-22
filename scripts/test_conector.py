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


NAVEGADOR = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"}
PRUEBA_FQ = "/es/ciencias/2eso/ponte-a-prueba-fq-tema-2/"


def contadores(db: str) -> dict[str, int]:
    import sqlite3
    with sqlite3.connect(db) as c:
        return {k: n for k, n in c.execute("SELECT clave, SUM(n) FROM contadores GROUP BY clave")}


def pruebas_metricas(base: str, db: str) -> None:
    print("Cifras de uso")
    lab = {**NAVEGADOR, "Host": "lab.beakman.kademy.net"}
    get = lambda ruta, h=lab: httpx2.get(base + ruta, headers=h, timeout=10)  # noqa: E731
    post = lambda q: httpx2.post(f"{base}/_cuenta?{q}", headers=lab, timeout=10)  # noqa: E731
    antes = contadores(db)
    get(PRUEBA_FQ); get(PRUEBA_FQ + "index.html"); get("/lab.css"); get("/no-existe/")
    get(PRUEBA_FQ, {"User-Agent": "Googlebot/2.1", "Host": "lab.beakman.kademy.net"})
    get("/empieza.html", NAVEGADOR); get("/site.css", NAVEGADOR)
    r_ok, r_mal, r_otra = post(f"p={PRUEBA_FQ}&k=calcula"), post(f"p={PRUEBA_FQ}&k=inventada"), post("p=/es/&k=calcula")
    post(f"p={PRUEBA_FQ}&k=completa")
    d = {k: n - antes.get(k, 0) for k, n in contadores(db).items() if n != antes.get(k, 0)}
    check("una página del lab suma una visita por petición (con o sin index.html)", d.get(f"visita:lab:{PRUEBA_FQ}") == 2, str(d))
    check("el CSS, un 404 y un robot no cuentan", not any(".css" in k or "no-existe" in k for k in d), str(d))
    check("una página de la web suma", d.get("visita:web:/empieza.html") == 1, str(d))
    check("un «Ponte a prueba» cuenta la sección y las 12 completas",
          r_ok.status_code == 204 and d.get(f"prueba:{PRUEBA_FQ}:calcula") == 1
          and d.get(f"prueba:{PRUEBA_FQ}:completa") == 1, str(d))
    check("una sección o una página que no existen se rechazan (400) y no cuentan",
          r_mal.status_code == 400 and r_otra.status_code == 400 and not any("inventada" in k for k in d), str(d))
    check("cuenta.js se sirve y las dos pruebas lo cargan", get("/cuenta.js").status_code == 200
          and "cuenta.js" in get(PRUEBA_FQ).text and "cuenta.js" in get("/es/historia/2eso/ponte-a-prueba-tema-1/").text)


def pruebas_cifras(entrada, db: str) -> None:
    from beakman_mcp import metricas
    metricas.cargar(os.path.join(REPO, "lab", "site"), os.path.join(REPO, "docs"))
    t = contadores(db)
    check("el conector cuenta las llamadas por herramienta",
          t.get("herramienta:empezar_clase", 0) >= 3 and t.get("herramienta:que_sabes_de_mi") == 1, str(t))
    texto = entrada._vista_cifras("7")
    check("Cifras: frase de resumen y bloques",
          "se han abierto" in texto and all(b in texto for b in ("Laboratorio", "Ponte a prueba", "Beakman en Claude",
                                                                    "Web", "Entradas", "Semana a semana")), texto[:300])
    check("Cifras: los recursos y las secciones salen con su título",
          "Ponte a prueba: propiedades y estados de la materia" in texto and "3 · Calcula la densidad" in texto
          and "Empezar una clase" in texto, texto[:300])


def main() -> int:
    tmp = tempfile.mkdtemp()
    db, puerto = os.path.join(tmp, "pruebas.sqlite"), puerto_libre()
    entrada_url = f"http://127.0.0.1:{puerto}"
    env = {**os.environ, "BEAKMAN_REPO_DIR": REPO, "BEAKMAN_ENTRADA_URL": entrada_url, "BEAKMAN_DB": db,
           "BEAKMAN_ALLOWED_HOSTS": f"localhost:{puerto},127.0.0.1:{puerto}",
           "BEAKMAN_SITE_DIR": os.path.join(REPO, "docs"), "BEAKMAN_LAB_DIR": os.path.join(REPO, "lab", "site")}
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
        pruebas_metricas(entrada_url, db)
        pruebas_cifras(entrada, db)
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
