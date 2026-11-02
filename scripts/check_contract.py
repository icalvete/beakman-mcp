#!/usr/bin/env python3
"""Comprueba que el servidor MCP no rompe a los conectores ya añadidos en claude.ai.

claude.ai guarda cómo era el conector al añadirlo: si pedía entrar y qué herramientas tenía. Si eso
cambia, el conector se rompe y a veces no se puede ni borrar (pasó en oct-2026). Este script compara
el servidor con mcp/contract.json, en sus dos versiones (abierta y con entrada):
  - la versión con entrada sigue pidiendo entrar;
  - ninguna herramienta del contrato desaparece;
  - ningún argumento del contrato desaparece;
  - ningún argumento pasa a ser obligatorio si no lo era.
Una herramienta nueva o un argumento opcional nuevo sí valen: se avisa y se añaden con --update.

Uso: python3 scripts/check_contract.py [--update]   (necesita las dependencias de mcp/requirements.txt)
El CI lo lanza antes de construir la imagen (.github/workflows/mcp-image.yml).
"""
import asyncio
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT = os.path.join(REPO, "mcp", "contract.json")


async def current() -> dict:
    tmp = tempfile.mkdtemp()
    os.environ.update(BEAKMAN_REPO_DIR=REPO, BEAKMAN_ENTRADA_URL="https://contrato.invalid",
                      BEAKMAN_DB=os.path.join(tmp, "contrato.sqlite"), BEAKMAN_SITE_DIR=tmp, BEAKMAN_LAB_DIR=tmp)
    sys.path.insert(0, os.path.join(REPO, "mcp"))
    from beakman_mcp import server

    out = {}
    for name, srv in (("abierto", server.mcp), ("con_entrada", server.servidor)):
        tools = {}
        for t in await srv.list_tools():
            schema = t.input_schema or {}
            tools[t.name] = {"args": sorted(schema.get("properties", {})), "required": sorted(schema.get("required", []))}
        out[name] = {"auth": srv.settings.auth is not None, "tools": dict(sorted(tools.items()))}
    return out


def compare(old: dict, new: dict) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    for variant, want in old.items():
        have = new.get(variant)
        if have is None:
            errors.append(f"{variant}: ha desaparecido")
            continue
        if want["auth"] != have["auth"]:
            errors.append(f"{variant}: la autenticación ha cambiado ({want['auth']} → {have['auth']})")
        for tool, spec in want["tools"].items():
            got = have["tools"].get(tool)
            if got is None:
                errors.append(f"{variant}: falta la herramienta {tool}")
                continue
            for arg in sorted(set(spec["args"]) - set(got["args"])):
                errors.append(f"{variant}: {tool} ya no tiene el argumento {arg}")
            for arg in sorted(set(got["required"]) - set(spec["required"])):
                errors.append(f"{variant}: {tool} exige ahora {arg}")
            for arg in sorted(set(got["args"]) - set(spec["args"])):
                notes.append(f"{variant}: {tool} tiene un argumento nuevo, {arg}")
        for tool in sorted(set(have["tools"]) - set(want["tools"])):
            notes.append(f"{variant}: herramienta nueva, {tool}")
    return errors, notes


def main() -> int:
    new = asyncio.run(current())
    if "--update" in sys.argv:
        with open(CONTRACT, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Escrito {os.path.relpath(CONTRACT, REPO)}.")
        return 0
    with open(CONTRACT, encoding="utf-8") as f:
        old = json.load(f)
    errors, notes = compare(old, new)
    for n in notes:
        print(f"aviso: {n} (añádelo con --update)")
    for e in errors:
        print(f"ROTO: {e}")
    if errors:
        print("\nEsto rompería los conectores ya añadidos en claude.ai. Si hace falta, va en una URL nueva (/mcp/v2).")
        return 1
    print("Contrato OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
