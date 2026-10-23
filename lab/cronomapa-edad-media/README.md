# Cronomapa de la Edad Media

Mapa de Europa y el Mediterráneo del 476 al 1492 con una barra de años: reinos, ciudades,
batallas y acontecimientos de los temas 4 a 14 de Historia de 2º ESO, en la voz de Beakman.

Publicado en https://lab.beakman.kademy.net/es/historia/2eso/cronomapa-edad-media/ (la página construida está en
`lab/site/es/historia/2eso/cronomapa-edad-media/`; las imágenes, comunes a los idiomas, en `lab/site/media/cronomapa-edad-media/`).

## Rehacerlo
    python3 -m venv venv && ./venv/bin/pip install shapely==2.0.6
    ./venv/bin/python build.py      # data.json: épocas, trazados, ciudades y acontecimientos
    python3 assemble.py             # lab/site/es/historia/2eso/cronomapa-edad-media/index.html
    python3 assemble.py 1250 peninsula   # además test.html, que arranca en 1250 en la vista de la Península

- `template.html`: la página (estilos y código); `__DATA__` se sustituye por `data.json`.
- `realms.py`: reinos y sus formas por épocas (lon, lat); el orden es la prioridad.
- `iberia.py`: la Península del 712 al 1492 (frontera que baja + columnas de reinos).
- `events.py`: ciudades, acontecimientos (texto de Beakman) y paradas con pregunta.
- `geo.py`: proyección, costa y ríos. Baja Natural Earth a `data/` la primera vez (costa 50m de
  world-atlas@2.0.2 y ríos 10m v5.1.2, dominio público).
- `preview.py`: vista previa en PNG de un año, sin navegador.

## Imágenes
- `images.py` busca la imagen principal de cada artículo de la Wikipedia en español (o, con `--search`, en
  Wikimedia Commons), guarda autor, licencia y enlace en `images.json` y baja una miniatura de 640 px a la
  carpeta común (`lab/site/media/cronomapa-edad-media/`). La página muestra autor, licencia y enlace de cada una.
- Cada imagen se ha revisado a mano. Para Mahoma no hay retrato (en el islam no se representa al profeta):
  se usan la Kaaba y la Mezquita del Profeta.

## Consecuencias
- `consequences.py`: para cada acontecimiento, consecuencias "al poco tiempo" y "a la larga" (con ámbito: gente, política, economía, religión, arte, cultura) y "y hoy", a veces con la asignatura con la que conecta.

## Diccionario
- `glossary.py`: 93 palabras con su definición para 12-14 años. La página marca la primera aparición de cada una en cada tarjeta (texto, consecuencias, "y hoy" y preguntas) y la explica al pasar el ratón o al tocar; el diccionario completo, con buscador, va en el panel derecho.

## Pantallas
- Pensado para ordenador: desde 1280×560 de ventana cabe sin scroll, en tres columnas. En un móvil sale un
  aviso de que es para verlo en un ordenador.
