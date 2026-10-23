# El laboratorio de Beakman

Recursos para estudiar con las manos (mapas, juegos, experimentos), por asignatura y curso.
Se publica en https://lab.beakman.kademy.net.

## Cómo está hecho
- `site/`: lo que se publica, tal cual. Lo sirve el contenedor del servidor MCP cuando el Host es
  `lab.beakman.kademy.net` (ver `mcp/beakman_mcp/server.py`).
  - `site/<idioma>/`: portada; `site/<idioma>/<asignatura>/`: página de la asignatura;
    `site/<idioma>/<asignatura>/<curso>/<recurso>/`: cada recurso.
  - `site/media/`: imágenes comunes a todos los idiomas. `site/lab.css`: estilos (la piel de la web de Beakman).
  - `site/index.html` lleva al idioma del navegador si está publicado; si no, al primero de `idiomas`.
- `catalog.yml`: idiomas publicados, asignaturas y recursos, con sus textos por idioma.
- `i18n/<idioma>.yml`: los textos fijos de las páginas (botones, rótulos, avisos).
- `build.py`: genera la raíz, las portadas, las páginas de asignatura y el 404. `python3 lab/build.py` (necesita PyYAML).
- `<recurso>/`: el código de cada recurso, que genera su propia página en `site/` (ver su README).

## Añadir un recurso
1. Su código en `lab/<id>/` y su página en `site/<idioma>/<asignatura>/<curso>/<id>/index.html`.
2. Una miniatura de 800×423 en `site/media/<id>.jpg`.
3. Su entrada en `catalog.yml` y `python3 lab/build.py`.

Al subir a `main`, el Action construye la imagen; se despliega con un tag de kademy.

## Otro idioma
1. `i18n/<idioma>.yml` con las mismas claves que `es.yml`.
2. En `catalog.yml`, los textos de cada asignatura y recurso en ese idioma, y el idioma en `idiomas`.
3. La página de cada recurso en `site/<idioma>/…` (el recurso tiene que estar traducido).
