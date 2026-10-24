# Cómo es una página de recurso del laboratorio

Guía para escribir un recurso nuevo en `lab/site/es/<asignatura>/<curso>/<id>/index.html`.

## Reglas
- Una sola página HTML, autónoma: los datos van dentro (en un `<script type="application/json">` o en el JS), sin
  librerías externas salvo las letras de Google Fonts. Nada de cookies ni analítica.
- Estilos: `lab.css` (la piel de Beakman) y `recursos.css` (piezas comunes: `.block`, `.b`, `.chip`, `.ok`, `.ko`,
  `.answer`, `.model`, `.mark`, `.beak`, `.note`, `.tabs`). Estilos propios del recurso, en un `<style>` dentro de la página.
- Rutas relativas: desde `es/historia/2eso/<id>/` hasta `site/` hay cuatro niveles (`../../../../`).
  Imágenes comunes en `../../../../media/`; las del cronomapa en `../../../../media/cronomapa-edad-media/<clave>.jpg`
  (autor, licencia y enlace en `lab/cronomapa-edad-media/images.json`: si usas una, muestra su crédito).
- Público: 12-14 años (2º ESO). Español de España. Tutea. Frases cortas. Voz de Beakman: curioso, cercano, nunca
  "fácil", "obvio" ni "todo el mundo lo sabe"; nunca describirlo como loco. Valora el intento, no ridiculiza el error.
- Pensado para ordenador (desde 1280 px se ve entero). En móvil basta con que no se rompa; incluye el aviso
  `.phone-note`.
- Solo claro (sin modo oscuro), como la web de Beakman.
- Lo que la persona marca (respuestas, aciertos) puede guardarse en `localStorage`, siempre en `try/catch`, y la
  página tiene que funcionar sin él.
- Datos históricos: solo hechos aceptados. Si una fecha es aproximada, dilo ("hacia el 865").
- Libro de referencia de la probadora: Vicens Vives, Geografía e Historia 2º ESO, Comunidad de Madrid, Tema 1
  "La huella andalusí". No copiar texto del libro: se puede citar el título de un apartado; las explicaciones son nuestras.

## Esqueleto
Ver `lab/_modelo.html`. Copiarlo a `lab/site/es/<asignatura>/<curso>/<id>/index.html` y rellenar (las rutas relativas ya cuentan con esa profundidad).

## Catálogo
Cada recurso necesita su entrada en `lab/catalog.yml` (título, temas, descripción, objetivo, método) y una miniatura
de 800×423 en `lab/site/media/<id>.jpg`. Después, `python3 lab/build.py`.
