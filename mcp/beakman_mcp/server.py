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
from starlette.routing import Mount
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


# ---- prompts: un arranque por asignatura ----------------------------------
# Sin argumentos: claude.ai pinta cada argumento como un formulario (aunque sea opcional),
# y eso confunde. El curso lo pregunta Beakman en el chat.

def _starter(nombre: str):
    def starter() -> str:
        return (f"Quiero estudiar {nombre} con Beakman. Pregúntame en qué curso estoy y qué quiero "
                f"repasar, y luego llama a empezar_clase con la asignatura «{nombre}» y sigue sus "
                f"instrucciones.")
    return starter


for _key, _name in [("historia", "Historia"), ("matematicas", "Matemáticas"),
                    ("ciencias", "Ciencias"), ("lengua", "Lengua")]:
    mcp.prompt(name=f"beakman_{_key}", title=f"Beakman de {_name}",
               description=f"Empieza una clase de {_name} con Beakman.")(_starter(_name))


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

# La web (docs/: portada, guías y herramientas) en el resto de rutas. Va la última, así que /mcp y /up
# siguen yendo al servidor MCP. En la imagen está en /app/site; en local, BEAKMAN_SITE_DIR=$PWD/docs.
SITE_DIR = os.environ.get("BEAKMAN_SITE_DIR", "/app/site")
if os.path.isdir(SITE_DIR):
    app.router.routes.append(Mount("/", app=StaticFiles(directory=SITE_DIR, html=True), name="site"))
