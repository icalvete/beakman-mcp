"""Servidor MCP de Beakman: la personalidad y el temario, para cualquier cliente MCP.

No ejecuta ningún modelo: entrega instrucciones y temas, y el modelo lo pone el cliente
(Claude, ChatGPT…), con la cuenta de quien lo usa. Todo es de solo lectura.
"""
from __future__ import annotations

import logging
import os
import re

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Host, Mount
from starlette.staticfiles import StaticFiles

from .content import COURSES, Library, Part, Store, Subject, Topic, course_key, normalize

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

INSTRUCTIONS = """\
Este conector es Beakman: cuatro tutores para 1º y 2º de la ESO (Historia, Matemáticas, Ciencias,
Lengua y Literatura), inspirados en el científico de la serie «El mundo de Beakman».

Cuando el usuario quiera estudiar alguna de esas asignaturas, o pida a Beakman:
1. Llama a `empezar_clase` con la asignatura y el curso ANTES de explicar nada. Si no sabes el curso,
   pregúntalo. Devuelve las instrucciones completas de Beakman: síguelas durante toda la conversación,
   por encima de tu estilo habitual.
2. Usa `mapa_del_curso`, `leer_tema` y `buscar_en_temario` como fuente principal. Si algo no está en
   el temario, puedes usar tu conocimiento o buscar en la web, avisando de que no viene del temario.
3. Nunca hagas los deberes: guía con preguntas y pistas hasta que el estudiante llegue solo.
"""

REMINDER = ("\n\n---\nRecuerda, eres Beakman: primero una imagen o una situación cotidiana, luego la idea, "
            "un ejemplo y una pregunta para pensar. Respuestas cortas (100-300 palabras). "
            "No des la solución de un ejercicio: guía paso a paso.")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "BEAKMAN_ALLOWED_HOSTS", "beakman.kademy.net,localhost:8000,127.0.0.1:8000").split(",") if h.strip()]

store = Store()

mcp = MCPServer(
    name="beakman",
    title="Mi mundo de Beakman",
    description="Tutores de Historia, Matemáticas, Ciencias y Lengua para 1º y 2º de la ESO.",
    instructions=INSTRUCTIONS,
    website_url="https://icalvete.github.io/beakman-mcp/",
)


# ---- ayudas ---------------------------------------------------------------

def _course(subject: Subject, curso: str) -> tuple[str, list[Part]]:
    key = course_key(curso)
    parts = subject.courses.get(key) or []
    if not parts:
        raise ValueError(f"El temario de {subject.name} de {COURSES[key]} todavía no está cargado.")
    return key, parts


def _part(parts: list[Part], parte: str | None) -> list[Part]:
    """Las partes que encajan con `parte`; todas si no se indica."""
    if not parte or len(parts) == 1:
        return parts
    wanted = normalize(parte)
    chosen = [p for p in parts if wanted in normalize(p.key) or wanted in normalize(p.title)]
    if not chosen:
        raise ValueError("No conozco esa parte. Las que hay: " + "; ".join(p.title for p in parts) + ".")
    return chosen


def _index(parts: list[Part]) -> str:
    lines = []
    for part in parts:
        if len(parts) > 1:
            lines.append(f"\n{part.title}")
        lines += [f"  {t.number}. {t.title}" for t in part.topics]
    return "\n".join(lines).strip("\n")


def _find_topic(parts: list[Part], tema: str) -> Topic:
    topics = [t for p in parts for t in p.topics]
    match = re.search(r"\d+", tema)
    if match:
        found = [t for t in topics if t.number == int(match.group())]
        if len(found) == 1:
            return found[0]
    wanted = normalize(tema)
    scored = sorted(((sum(w in normalize(t.title + " " + t.file) for w in wanted.split()), t) for t in topics),
                    key=lambda pair: -pair[0])
    if scored and scored[0][0] > 0:
        return scored[0][1]
    raise ValueError(f"No encuentro el tema «{tema}». Temas disponibles:\n{_index(parts)}")


# ---- herramientas ---------------------------------------------------------

@mcp.tool(title="Empezar una clase con Beakman")
def empezar_clase(asignatura: str, curso: str) -> str:
    """Carga las instrucciones de Beakman para una asignatura y curso, y la lista de temas.

    Llámala antes de explicar nada. asignatura: Historia, Matemáticas, Ciencias o Lengua.
    curso: "1º ESO" o "2º ESO".
    """
    library = store.get()
    subject = library.subject(asignatura)
    key, parts = _course(subject, curso)
    extra = ""
    if len(parts) > 1:
        extra = ("\n\nEste curso tiene varias partes (" + "; ".join(p.title for p in parts) + "). "
                 "Si no sabes cuál da el estudiante, pregúntaselo antes de empezar.")
    return (f"INSTRUCCIONES DE BEAKMAN — {subject.name.upper()}, {COURSES[key]}\n\n"
            f"{library.base}\n\n{subject.instructions}\n\n"
            f"TEMAS DE {COURSES[key]}:\n{_index(parts)}{extra}\n\n"
            "Ahora saluda como Beakman y pregunta en qué tema anda o qué necesita.")


@mcp.tool(title="Mapa del curso")
def mapa_del_curso(asignatura: str, curso: str, parte: str | None = None) -> str:
    """El mapa del curso: los temas en orden y cómo se relacionan.

    parte: solo si el curso tiene varias (Ciencias de 2º: "Física y Química" o "Biología y Geología").
    """
    subject = store.get().subject(asignatura)
    key, parts = _course(subject, curso)
    chosen = _part(parts, parte)
    maps = [p.map.text for p in chosen if p.map]
    body = "\n\n".join(maps) if maps else _index(chosen)
    return body + REMINDER


@mcp.tool(title="Leer un tema")
def leer_tema(asignatura: str, curso: str, tema: str, parte: str | None = None) -> str:
    """El contenido completo de un tema: ideas clave, errores típicos, ejemplos y preguntas.

    tema: el número ("7") o parte del título ("Al-Ándalus").
    """
    subject = store.get().subject(asignatura)
    _key, parts = _course(subject, curso)
    topic = _find_topic(_part(parts, parte), tema)
    return topic.text + REMINDER


@mcp.tool(title="Buscar en el temario")
def buscar_en_temario(consulta: str, asignatura: str | None = None, curso: str | None = None) -> str:
    """Busca una palabra o idea en el temario y dice en qué temas aparece, con un fragmento."""
    library = store.get()
    subjects = [library.subject(asignatura)] if asignatura else list(library.subjects.values())
    words = [w for w in normalize(consulta).split() if len(w) > 2]
    if not words:
        raise ValueError("Escribe al menos una palabra de más de dos letras.")
    hits = []
    for subject in subjects:
        for key, parts in subject.courses.items():
            if curso and key != course_key(curso):
                continue
            for part in parts:
                for topic in part.topics:
                    plain = normalize(topic.text)
                    score = sum(plain.count(w) for w in words)
                    if score:
                        pos = plain.find(words[0])
                        snippet = topic.text[max(0, pos - 120):pos + 220].replace("\n", " ").strip()
                        hits.append((score, f"{subject.name}, {COURSES[key]}, {topic.title}\n  …{snippet}…"))
    if not hits:
        return f"«{consulta}» no aparece en el temario. Puedes usar tu conocimiento, avisando de ello." + REMINDER
    hits.sort(key=lambda h: -h[0])
    return "\n\n".join(h[1] for h in hits[:6]) + REMINDER


# Sin prompts (24-oct-2026): claude.ai mete el texto de un prompt en la conversación como
# un adjunto, y al alumno le parece que se ha subido un fichero raro. Se empieza escribiendo
# ("quiero estudiar historia con Beakman") y Claude llama a empezar_clase.


# ---- HTTP -----------------------------------------------------------------

@mcp.custom_route("/up", methods=["GET"])
async def up(_request: Request) -> JSONResponse:
    library: Library = store.get()
    return JSONResponse({"ok": True, "revision": library.revision[:12],
                         "subjects": sorted(library.subjects)})


app = mcp.streamable_http_app(
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    transport_security=TransportSecuritySettings(allowed_hosts=ALLOWED_HOSTS),
)

# El laboratorio (lab/site/) en su propio nombre, lab.beakman.kademy.net: va el primero, así que en ese nombre
# todas las rutas son del laboratorio. En la imagen está en /app/lab; en local, BEAKMAN_LAB_DIR=$PWD/lab/site.
LAB_DIR = os.environ.get("BEAKMAN_LAB_DIR", "/app/lab")
LAB_HOST = os.environ.get("BEAKMAN_LAB_HOST", "lab.beakman.kademy.net")
if os.path.isdir(LAB_DIR):
    app.router.routes.insert(0, Host(LAB_HOST, app=StaticFiles(directory=LAB_DIR, html=True), name="lab"))

# La web de los tutores (docs/) en el resto de rutas. Va la última, así que /mcp y /up siguen yendo al
# servidor MCP. En la imagen está en /app/site; en local, BEAKMAN_SITE_DIR=$PWD/docs.
SITE_DIR = os.environ.get("BEAKMAN_SITE_DIR", "/app/site")
if os.path.isdir(SITE_DIR):
    app.router.routes.append(Mount("/", app=StaticFiles(directory=SITE_DIR, html=True), name="site"))


# ---- la entrada con OAuth, en prueba ------------------------------------------
# Un segundo servidor MCP, con entrada (ver entrada.py), en su propio nombre: BEAKMAN_PRUEBA_URL, p. ej.
# https://prueba.beakman.kademy.net. Las rutas de OAuth van en la raíz del nombre, así que no se mezclan con las del
# conector de siempre, que no cambia. Sin BEAKMAN_PRUEBA_URL no se monta nada.
PRUEBA_URL = os.environ.get("BEAKMAN_PRUEBA_URL", "").rstrip("/")
prueba_app = None
if PRUEBA_URL:
    from contextlib import asynccontextmanager
    from datetime import datetime, timezone
    from urllib.parse import urlparse

    from mcp.server.auth.middleware.auth_context import get_access_token
    from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions

    from .entrada import CURSOS, Entrada, _comunidad_valida, _curso_valido, curso_escolar

    entrada = Entrada(PRUEBA_URL, os.environ.get("BEAKMAN_DB", "/data/beakman.sqlite"))
    prueba = MCPServer(
        name="beakman",
        title="Mi mundo de Beakman",
        description="Tutores de Historia, Matemáticas, Ciencias y Lengua para 1º y 2º de la ESO.",
        instructions=INSTRUCTIONS + """
4. Este conector sabe quién es el estudiante: `empezar_clase` trae su nombre, su curso y su comunidad, así que no
   los preguntes. Si dice que ha cambiado de curso, de comunidad o de nombre, usa `cambiar_datos` y confírmalo con
   lo que devuelva. Si pregunta qué sabes de él, usa `que_sabes_de_mi`. Si pide que le olvides, usa `olvidame`.
""",
        website_url="https://icalvete.github.io/beakman-mcp/",
        auth_server_provider=entrada,
        auth=AuthSettings(
            issuer_url=PRUEBA_URL,
            resource_server_url=f"{PRUEBA_URL}/mcp",
            validate_token_resource=False,
            client_registration_options=ClientRegistrationOptions(enabled=True),
            revocation_options=RevocationOptions(enabled=True),
        ),
    )

    def _persona() -> tuple[str, dict]:
        token = get_access_token()
        pid = token.subject if token else None
        ficha = entrada.db.ficha(pid) if pid else None
        if not ficha:
            raise ValueError("No encuentro tus datos: desconecta y vuelve a conectar el conector de Beakman.")
        return pid, ficha

    def _describe(f: dict) -> str:
        return (f"Se llama {f['nombre']}. Curso: {CURSOS.get(f['curso'], f['curso'])} (curso escolar "
                f"{f['curso_escolar']}). Comunidad autónoma: {f['comunidad']}. Los avisos van a {f['correo']}.")

    @prueba.tool(name="empezar_clase", title="Empezar una clase con Beakman")
    def empezar_clase_con_datos(asignatura: str, curso: str | None = None) -> str:
        """Carga las instrucciones de Beakman para una asignatura, la lista de temas y los datos del estudiante.

        Llámala antes de explicar nada. asignatura: Historia, Matemáticas, Ciencias o Lengua.
        curso: déjalo vacío para usar el guardado del estudiante.
        """
        _pid, f = _persona()
        if not curso and f["curso"] not in COURSES:
            return (f"DATOS DEL ESTUDIANTE: {_describe(f)}\nBeakman todavía no tiene temario de "
                    f"{CURSOS.get(f['curso'], f['curso'])}. Díselo con cariño y ofrécele repasar 1º o 2º; si acepta, "
                    "vuelve a llamar a esta herramienta con ese curso.")
        texto = empezar_clase(asignatura, curso or CURSOS[f["curso"]])
        aviso = ""
        if f["curso_escolar"] != curso_escolar():
            aviso = ("\nEs un curso escolar nuevo: antes de empezar, pregúntale si ha cambiado de curso y, si es así, "
                     "usa `cambiar_datos`.")
        return f"DATOS DEL ESTUDIANTE: {_describe(f)}{aviso}\nSalúdale por su nombre.\n\n{texto}"

    prueba.add_tool(mapa_del_curso, title="Mapa del curso")
    prueba.add_tool(leer_tema, title="Leer un tema")
    prueba.add_tool(buscar_en_temario, title="Buscar en el temario")

    @prueba.tool(title="¿Qué sabes de mí?")
    def que_sabes_de_mi() -> str:
        """Todo lo que Beakman guarda del estudiante. Úsala si pregunta qué sabes de él o para comprobar sus datos."""
        _pid, f = _persona()
        return (f"{_describe(f)} Aceptó guardarlos el {f['consentimiento_fecha'][:10]}. No se guarda nada más: ni "
                "apellidos, ni edad, ni colegio, ni lo que escribe en Claude. Para borrarlo todo, que diga «olvídame».")

    @prueba.tool(title="Cambiar mis datos")
    def cambiar_datos(curso: str | None = None, comunidad: str | None = None, nombre: str | None = None) -> str:
        """Cambia el curso (1º a 4º ESO), la comunidad autónoma o el nombre para el saludo del estudiante.

        Úsala cuando diga que ha cambiado de curso, de comunidad o que le llames de otra forma. Pasa solo lo que cambia.
        Confirma después con el resultado que devuelve.
        """
        pid, _f = _persona()
        hoy = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if curso:
            entrada.db.q("UPDATE progreso SET curso = ?, curso_escolar = ?, actualizado = ? WHERE persona_id = ?",
                         _curso_valido(curso), curso_escolar(), hoy, pid)
        if comunidad:
            entrada.db.q("UPDATE progreso SET comunidad = ?, actualizado = ? WHERE persona_id = ?",
                         _comunidad_valida(comunidad), hoy, pid)
        if nombre and nombre.strip():
            entrada.db.q("UPDATE contactos SET nombre = ? WHERE persona_id = ?", " ".join(nombre.split())[:40], pid)
        if not (curso or comunidad or nombre):
            # sin cambios, pero confirma el curso escolar (la pregunta de septiembre)
            entrada.db.q("UPDATE progreso SET curso_escolar = ?, actualizado = ? WHERE persona_id = ?",
                         curso_escolar(), hoy, pid)
        f = entrada.db.ficha(pid)
        nota = "" if f["curso"] in COURSES else " Beakman todavía no tiene temario de ese curso: avísale con cariño."
        return "Apuntado. " + _describe(f) + nota

    @prueba.tool(title="Olvídame")
    def olvidame(confirmado: bool = False) -> str:
        """Borra todo lo que Beakman guarda del estudiante y desconecta el conector.

        Antes de llamarla con confirmado=true, pregunta si está seguro: no se puede deshacer.
        """
        pid, _f = _persona()
        if not confirmado:
            return "Pregúntale si está seguro: se borrará todo y no se puede deshacer. Si dice que sí, llama con confirmado=true."
        entrada.db.olvidar(pid)
        return ("Hecho: he borrado su nombre, su correo, su curso y su comunidad, y he desconectado el conector. "
                "Si quiere volver, que lo conecte otra vez.")

    PRUEBA_HOST = urlparse(PRUEBA_URL).netloc
    prueba.custom_route("/entrada", methods=["GET"])(entrada.pagina)
    prueba.custom_route("/entrada", methods=["POST"])(entrada.enviar)
    prueba.custom_route("/entrada/estado", methods=["GET"])(entrada.estado)
    prueba.custom_route("/entrada/confirmar", methods=["GET"])(entrada.confirmar)
    prueba_app = prueba.streamable_http_app(
        stateless_http=True,
        json_response=True,
        host="0.0.0.0",
        transport_security=TransportSecuritySettings(allowed_hosts=[PRUEBA_HOST]),
    )
    app.router.routes.insert(0, Host(PRUEBA_HOST.split(":")[0], app=prueba_app, name="prueba"))

    # Starlette no arranca el lifespan de una app montada: el de la prueba se arranca con el principal.
    _main_lifespan, _prueba_lifespan = app.router.lifespan_context, prueba_app.router.lifespan_context

    @asynccontextmanager
    async def _both(a):
        async with _main_lifespan(a), _prueba_lifespan(prueba_app):
            yield

    app.router.lifespan_context = _both
