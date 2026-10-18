# CLAUDE.md

Cuatro tutores Beakman (Historia, Matemáticas, Ciencias, Lengua) para 1º y 2º ESO, servidos como Gems de Google Gemini. Ver README.md.

## Comandos
- `python3 scripts/build.py`: genera `dist/<Asignatura>/` (tres ficheros por Gem más `gem.txt`).
- `python3 scripts/build.py --check`: valida sin escribir.
- Servidor MCP: `mcp/` (Python, `mcp` 2.x `MCPServer`). En local: `BEAKMAN_REPO_DIR=$PWD uvicorn beakman_mcp.server:app --app-dir mcp`. En producción lee el temario de GitHub (`main`) y lo refresca cada 5 min, así que un cambio de contenido no necesita imagen nueva. La imagen la publica `.github/workflows/mcp-image.yml` en `ghcr.io/icalvete/beakman-mcp`; se despliega en alala (`beakman.kademy.net`) desde el repo de kademy (`iac/roles/kademy_stack`).
- Web: `docs/` (GitHub Pages desde `main`, carpeta `/docs`). Vista previa: `python3 -m http.server -d docs`.

## Reglas que no se rompen
- **Los nombres de los ficheros de `dist/` no cambian nunca.** Cada Gem enlaza los ficheros de Drive por su ID. Un tema nuevo va en `<asignatura>/<curso>/` y acaba dentro del fichero del curso. Nunca crear un cuarto fichero por Gem.
- El Action sube con `rclone copy`, que sobrescribe manteniendo el ID (comprobado el 2026-10-18). No usar `sync` ni nada que borre y vuelva a crear.
- El remote `beakman` usa `scope=drive.file`: solo ve lo que crea su client_id. Si cambia el client_id, los ficheros viejos se quedan huérfanos y hay que volver a enlazarlos en los Gems.

## Contenido
- **Beakman no está loco.** Nunca describirlo como "loco", "chiflado" ni nada parecido, en ningún texto (instrucciones, temas, web, README). Es un científico curioso, entusiasta y apasionado por explicar. Lo pidió el usuario el 2026-10-18.
- Lo común a todas las asignaturas va en `beakman/base.md`; lo propio, en `<asignatura>/asignatura.md`. Nada se repite en los dos sitios.
- Formato de un tema: título, descripción breve, ideas clave, errores típicos, relación con otros temas.
- Para estudiantes de 12 a 14 años. Español de España.
- Ciencias de 2º tiene dos partes, `2eso/fisica_y_quimica/` y `2eso/biologia_y_geologia/` (cada una con `_titulo.txt`), porque según la comunidad toca una u otra. El Gem pregunta cuál da el estudiante. `build.py` trata cada subcarpeta de un curso como una parte.
