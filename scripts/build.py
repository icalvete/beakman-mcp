#!/usr/bin/env python3
"""Genera los ficheros que lee cada Gem.

Por asignatura salen siempre los mismos tres ficheros en dist/<Asignatura>/:
  Beakman_<Asignatura>_00_Instrucciones.txt  base común + lo propio de la asignatura
  Beakman_<Asignatura>_01_Curso_1ESO.txt     los temas de <asignatura>/1eso/, en orden
  Beakman_<Asignatura>_02_Curso_2ESO.txt     los temas de <asignatura>/2eso/, en orden

Los nombres no cambian nunca: el Gem enlaza cada fichero de Drive por su ID, y un
fichero nuevo habría que enlazarlo a mano. Un tema nuevo va dentro del de su curso.
También escribe dist/<Asignatura>/gem.txt con lo que se pega al crear el Gem (no se sube).

Uso: python3 scripts/build.py [--check]   (--check: falla si algo no cuadra, sin escribir)
"""
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SUBJECTS = ["historia", "matematicas", "ciencias", "lengua"]
COURSES = [("1eso", "01_Curso_1ESO", "1º ESO"), ("2eso", "02_Curso_2ESO", "2º ESO")]
SEPARATOR = "\n\n" + "=" * 72 + "\n\n"


def slug(text):
    """'Matemáticas' -> 'Matematicas'."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(ch for ch in plain if ch.isalnum())


def read_subject(name):
    """Devuelve (metadatos, cuerpo) de <asignatura>/asignatura.md."""
    text = (ROOT / name / "asignatura.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{name}/asignatura.md: falta la cabecera ---")
    header, body = text[4:].split("\n---\n", 1)
    meta = dict(line.split(": ", 1) for line in header.splitlines() if line.strip())
    for key in ("nombre", "gem", "descripcion"):
        if key not in meta:
            raise ValueError(f"{name}/asignatura.md: falta '{key}' en la cabecera")
    return meta, body.strip()


def course_text(name, folder, label, title):
    topics = sorted((ROOT / name / folder).glob("*.txt"))
    head = f"TEMARIO DE {title.upper()} – {label}\n"
    if not topics:
        return head + (
            "\nEN PREPARACIÓN. Este temario todavía no está cargado.\n"
            "Si el estudiante pregunta por este curso, díselo con naturalidad y ayúdale "
            "con conocimientos generales del curso, avisando de que no vienen de tu temario.\n"
        )
    parts = [head]
    for topic in topics:
        parts.append(f"[Fichero de origen: {topic.name}]\n\n" + topic.read_text(encoding="utf-8").strip())
    return SEPARATOR.join(parts) + "\n"


def build():
    base = (ROOT / "beakman" / "base.md").read_text(encoding="utf-8").strip()
    stub = (ROOT / "beakman" / "gem_stub.txt").read_text(encoding="utf-8")
    out = {}
    for name in SUBJECTS:
        meta, body = read_subject(name)
        s = slug(meta["nombre"])
        files = {
            f"Beakman_{s}_00_Instrucciones.txt": base + SEPARATOR + body + "\n",
        }
        for folder, suffix, label in COURSES:
            files[f"Beakman_{s}_{suffix}.txt"] = course_text(name, folder, label, meta["nombre"])
        gem = (
            f"NOMBRE:\n{meta['gem']}\n\nDESCRIPCIÓN:\n{meta['descripcion']}\n\n"
            f"INSTRUCCIONES:\n{stub.format(nombre=meta['nombre'], slug=s)}\n"
            f"CONOCIMIENTO (desde Google Drive, carpeta Beakman/{s}):\n"
            + "".join(f"- {f}\n" for f in files)
        )
        out[s] = (files, gem)
    return out


def main():
    check = "--check" in sys.argv
    result = build()
    for s, (files, gem) in result.items():
        target = DIST / s
        if not check:
            target.mkdir(parents=True, exist_ok=True)
            for old in target.glob("*.txt"):
                if old.name not in files and old.name != "gem.txt":
                    old.unlink()
            for fname, content in files.items():
                (target / fname).write_text(content, encoding="utf-8")
            (target / "gem.txt").write_text(gem, encoding="utf-8")
        sizes = ", ".join(f"{f.split('_', 2)[2]} {len(c.encode()) // 1024} KB" for f, c in files.items())
        print(f"{s}: {sizes}")
    print("OK (solo comprobación)" if check else f"Escrito en {DIST.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
