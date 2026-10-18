# CLAUDE.md

Cuatro tutores Beakman (Historia, Matemáticas, Ciencias, Lengua) para 1º y 2º ESO, servidos como Gems de Google Gemini. Ver README.md.

## Comandos
- `python3 scripts/build.py`: genera `dist/<Asignatura>/` (tres ficheros por Gem más `gem.txt`).
- `python3 scripts/build.py --check`: valida sin escribir.
- Web: `docs/` (GitHub Pages desde `main`, carpeta `/docs`). Vista previa: `python3 -m http.server -d docs`.

## Reglas que no se rompen
- **Los nombres de los ficheros de `dist/` no cambian nunca.** Cada Gem enlaza los ficheros de Drive por su ID. Un tema nuevo va en `<asignatura>/<curso>/` y acaba dentro del fichero del curso. Nunca crear un cuarto fichero por Gem.
- El Action sube con `rclone copy`, que sobrescribe manteniendo el ID (comprobado el 2026-10-18). No usar `sync` ni nada que borre y vuelva a crear.
- El remote `beakman` usa `scope=drive.file`: solo ve lo que crea su client_id. Si cambia el client_id, los ficheros viejos se quedan huérfanos y hay que volver a enlazarlos en los Gems.

## Contenido
- Lo común a todas las asignaturas va en `beakman/base.md`; lo propio, en `<asignatura>/asignatura.md`. Nada se repite en los dos sitios.
- Formato de un tema: título, descripción breve, ideas clave, errores típicos, relación con otros temas.
- Para estudiantes de 12 a 14 años. Español de España.
- En Ciencias, 2º ESO puede ser Física y Química según la comunidad autónoma.
