"""El temario de Beakman, leído del repositorio.

Lee la misma estructura que scripts/build.py: beakman/base.md, <asignatura>/asignatura.md y
<asignatura>/<curso>/[<parte>/]NN_*.txt. Del repositorio solo se leen datos, nunca código.

Fuentes:
  - BEAKMAN_REPO_DIR=<ruta>: una copia local (desarrollo y pruebas).
  - Si no, GitHub: comprueba el último commit de la rama cada REFRESH_SECONDS y, si ha
    cambiado, descarga el tarball y lo vuelve a cargar. Un push llega solo, sin redesplegar.
"""
from __future__ import annotations

import io
import logging
import os
import tarfile
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import PurePosixPath

import httpx

log = logging.getLogger("beakman.content")

SUBJECTS = ["historia", "matematicas", "ciencias", "lengua"]
COURSES = {"1eso": "1º ESO", "2eso": "2º ESO"}
SUBJECT_ALIASES = {
    "mates": "matematicas", "mate": "matematicas",
    "fisica y quimica": "ciencias", "fisica": "ciencias", "quimica": "ciencias",
    "biologia y geologia": "ciencias", "biologia": "ciencias", "geologia": "ciencias",
    "ciencias naturales": "ciencias",
    "lengua y literatura": "lengua", "lengua castellana": "lengua", "literatura": "lengua",
    "geografia e historia": "historia",
}
REPO = os.environ.get("BEAKMAN_GITHUB_REPO", "icalvete/beakman-gems")
BRANCH = os.environ.get("BEAKMAN_GITHUB_BRANCH", "main")
REFRESH_SECONDS = int(os.environ.get("BEAKMAN_REFRESH_SECONDS", "300"))


def normalize(text: str) -> str:
    """'Matemáticas' -> 'matematicas'; para comparar sin tildes ni mayúsculas."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().replace("_", " ").split())


@dataclass
class Topic:
    file: str        # nombre del fichero, p. ej. "07_Al_Andalus.txt"
    number: int      # 7
    title: str       # primera línea, p. ej. "TEMA 7 – AL-ÁNDALUS"
    text: str


@dataclass
class Part:
    key: str         # carpeta, p. ej. "fisica_y_quimica"; "" si el curso no tiene partes
    title: str
    map: Topic | None = None
    topics: list[Topic] = field(default_factory=list)


@dataclass
class Subject:
    key: str
    name: str
    gem_name: str
    description: str
    instructions: str                                        # cuerpo de asignatura.md
    courses: dict[str, list[Part]] = field(default_factory=dict)


@dataclass
class Library:
    base: str
    subjects: dict[str, Subject]
    revision: str

    def subject(self, name: str) -> Subject:
        wanted = normalize(name)
        key = SUBJECT_ALIASES.get(wanted, wanted)
        for subject in self.subjects.values():
            if key in (subject.key, normalize(subject.name)):
                return subject
        raise ValueError(f"No conozco la asignatura «{name}». Las que hay: "
                         + ", ".join(s.name for s in self.subjects.values()) + ".")


def course_key(curso: str) -> str:
    wanted = normalize(curso).replace("o eso", "eso").replace(" ", "")
    if wanted.startswith(("1", "primero")):
        return "1eso"
    if wanted.startswith(("2", "segundo")):
        return "2eso"
    raise ValueError(f"No conozco el curso «{curso}». Los que hay: 1º ESO y 2º ESO.")


def _topic(name: str, text: str) -> Topic:
    digits = name.split("_", 1)[0]
    number = int(digits) if digits.isdigit() else -1
    title = next((line.strip() for line in text.splitlines() if line.strip()), name)
    return Topic(file=name, number=number, title=title, text=text.strip())


def _parts(files: dict[str, str], prefix: str) -> list[Part]:
    """Las partes de un curso a partir de {ruta: texto}, con ruta relativa al curso."""
    groups: dict[str, dict[str, str]] = {}
    for path, text in files.items():
        if not path.startswith(prefix) or not path.endswith(".txt"):
            continue
        rel = PurePosixPath(path[len(prefix):])
        key = rel.parts[0] if len(rel.parts) == 2 else ""
        if len(rel.parts) > 2:
            continue
        groups.setdefault(key, {})[rel.name] = text
    parts = []
    for key in sorted(groups):
        entries = groups[key]
        title = entries.pop("_titulo.txt", "").strip().splitlines()
        part = Part(key=key, title=title[0] if title else key.replace("_", " ").upper())
        for name in sorted(entries):
            if name.startswith("_"):
                continue
            topic = _topic(name, entries[name])
            if topic.number == 0:
                part.map = topic
            else:
                part.topics.append(topic)
        if part.map or part.topics:
            parts.append(part)
    return parts


def build_library(files: dict[str, str], revision: str) -> Library:
    """Monta la biblioteca a partir de {ruta relativa al repo: texto}."""
    subjects = {}
    for key in SUBJECTS:
        raw = files.get(f"{key}/asignatura.md")
        if raw is None or not raw.startswith("---\n"):
            continue
        header, body = raw[4:].split("\n---\n", 1)
        meta = dict(line.split(": ", 1) for line in header.splitlines() if ": " in line)
        subject = Subject(key=key, name=meta.get("nombre", key), gem_name=meta.get("gem", ""),
                          description=meta.get("descripcion", ""), instructions=body.strip())
        for course in COURSES:
            subject.courses[course] = _parts(files, f"{key}/{course}/")
        subjects[key] = subject
    return Library(base=files.get("beakman/base.md", "").strip(), subjects=subjects, revision=revision)


def load_dir(root: str) -> Library:
    files = {}
    for dirpath, _dirs, names in os.walk(root):
        if "/." in dirpath or "/dist" in dirpath or "/docs" in dirpath or "/mcp" in dirpath:
            continue
        for name in names:
            if name.endswith((".md", ".txt")):
                full = os.path.join(dirpath, name)
                with open(full, encoding="utf-8") as fh:
                    files[os.path.relpath(full, root)] = fh.read()
    return build_library(files, revision="local")


def load_tarball(data: bytes, revision: str) -> Library:
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith((".md", ".txt")):
                continue
            rel = member.name.split("/", 1)[1] if "/" in member.name else member.name
            if rel.startswith(("docs/", "mcp/", ".")):
                continue
            files[rel] = tar.extractfile(member).read().decode("utf-8")
    return build_library(files, revision=revision)


class Store:
    """La biblioteca vigente. Se refresca desde GitHub como mucho cada REFRESH_SECONDS."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._library: Library | None = None
        self._checked = 0.0
        self._local = os.environ.get("BEAKMAN_REPO_DIR")

    def get(self) -> Library:
        if self._local:
            if self._library is None:
                self._library = load_dir(self._local)
            return self._library
        if self._library is None or time.monotonic() - self._checked > REFRESH_SECONDS:
            with self._lock:
                if self._library is None or time.monotonic() - self._checked > REFRESH_SECONDS:
                    self._refresh()
        if self._library is None:
            raise RuntimeError("No he podido cargar el temario desde GitHub.")
        return self._library

    def _refresh(self) -> None:
        self._checked = time.monotonic()
        try:
            with httpx.Client(timeout=20, follow_redirects=True,
                              headers={"User-Agent": "beakman-mcp"}) as client:
                sha = client.get(f"https://api.github.com/repos/{REPO}/commits/{BRANCH}",
                                 headers={"Accept": "application/vnd.github.sha"}).raise_for_status().text.strip()
                if self._library and self._library.revision == sha:
                    return
                tar = client.get(f"https://codeload.github.com/{REPO}/tar.gz/{sha}").raise_for_status()
                self._library = load_tarball(tar.content, revision=sha)
                log.info("Temario cargado: %s", sha[:7])
        except Exception:  # sin red o GitHub caído: seguimos con lo que había
            log.exception("No he podido refrescar el temario; sigo con la versión %s",
                          self._library.revision[:7] if self._library else "ninguna")
