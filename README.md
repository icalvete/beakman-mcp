# Mi mundo de Beakman

<p align="center">
  <img src="historia/logo.jpeg" alt="Beakman, Historia" height="140">
  <img src="matematicas/logo.jpeg" alt="Beakman, Matemáticas" height="140">
  <img src="ciencias/logo.png" alt="Beakman, Ciencias" height="140">
  <img src="lengua/logo.webp" alt="Beakman, Lengua" height="140">
</p>

<p align="center"><strong>Cuatro tutores de IA para 1º y 2º de la ESO que no hacen los deberes: ayudan a entenderlos.</strong><br>
Historia, Matemáticas, Ciencias y Lengua. Gratis, en Google Gemini.</p>

<p align="center"><a href="https://icalvete.github.io/beakman-gems/">Web</a> · <a href="https://icalvete.github.io/beakman-gems/guia/usarlo.html">Cómo se usa</a> · <a href="https://icalvete.github.io/beakman-gems/guia/montar-el-tuyo.html">Monta el tuyo</a></p>

## Por qué

Con un chat de IA cualquiera, un estudiante pega el ejercicio, copia la solución y no aprende nada. Lo peor es la costumbre de no pensar.

Beakman está instruido para lo contrario:

- **Guía, no resuelve.** Pregunta qué has probado, da una pista y espera a que lo intentes.
- **Entender antes que memorizar.** Primero una imagen mental o una situación cotidiana, luego la idea y al final los nombres, las fechas o las fórmulas.
- **El error es parte de aprender.** Nunca dice que algo es «fácil». Si no lo entiendes, cambia de ejemplo.
- **Sigue el temario de clase** y dice cuándo algo no está en él o no está seguro.
- **Abierto.** [Sus instrucciones](beakman/base.md) y todo el temario están aquí. Cualquier familia o profe puede leer qué se le pide.

Es un homenaje a Beakman, el científico apasionado de *El mundo de Beakman* (1992-1998), que enseñó a una generación que la ciencia podía ser una aventura.

## Cómo se usa

No hay que montar nada. Abre el enlace de la asignatura en la [web](https://icalvete.github.io/beakman-gems/#asignaturas), entra con tu cuenta de Google y dile tu curso y qué necesitas. Si no sabes por dónde empezar, escribe «Ayuda».

La [guía de uso](https://icalvete.github.io/beakman-gems/guia/usarlo.html) tiene ideas para estudiantes, familias y profesorado.

## Cómo funciona

Todo el contenido vive en este repositorio, y nadie copia nada a mano en Gemini:

1. Editas un tema o las instrucciones y haces push a `main`.
2. El Action [sync-drive.yml](.github/workflows/sync-drive.yml) ejecuta [scripts/build.py](scripts/build.py), que junta las piezas en tres ficheros por asignatura.
3. El Action los sobrescribe en Google Drive con rclone. Cada fichero conserva su ID.
4. Cada Gem tiene esos tres ficheros enlazados desde Drive y recibe los cambios sin tocarlo.

Lo único manual es crear cada Gem la primera vez, porque Gemini no tiene API para eso.

```
beakman/base.md              personalidad y método, comunes a las cuatro asignaturas
beakman/gem_stub.txt         texto fijo de la caja de instrucciones del Gem
<asignatura>/asignatura.md   lo propio de cada asignatura (cabecera con nombre y descripción del Gem)
<asignatura>/1eso/*.txt      temas de 1º, en orden por nombre
<asignatura>/2eso/*.txt      temas de 2º (en borrador; Ciencias tiene dos partes:
                             fisica_y_quimica/ y biologia_y_geologia/)
<asignatura>/logo.*          la imagen de Beakman de esa asignatura
scripts/build.py             genera dist/<Asignatura>/ con los ficheros de cada Gem
docs/                        la web (GitHub Pages)
```

Cada Gem recibe siempre los mismos tres ficheros: `Beakman_<Asignatura>_00_Instrucciones.txt`, `..._01_Curso_1ESO.txt` y `..._02_Curso_2ESO.txt`. Un tema nuevo va dentro del fichero de su curso, porque un fichero nuevo habría que enlazarlo a mano en el Gem.

Para probar en local: `python3 scripts/build.py`. En `dist/<Asignatura>/gem.txt` queda lo que va en el formulario del Gem.

## Monta el tuyo

Si eres profe o quieres tu propio temario, la [guía para montarlo](https://icalvete.github.io/beakman-gems/guia/montar-el-tuyo.html) explica cada paso: fork, GitHub Pages, tu app de Google, rclone, el secreto `RCLONE_CONF` y la creación de los Gems. Unos 30 minutos.

## Contribuir

¿Un error en un tema o una mejora? Abre una [incidencia](https://github.com/icalvete/beakman-gems/issues) o un pull request. Antes, lee [CLAUDE.md](CLAUDE.md): tiene las reglas del contenido.

## Aviso

Beakman es una herramienta de apoyo y no sustituye al profesorado. Es una IA y puede equivocarse. Recomendamos supervisión adulta con menores. Se ofrece tal cual, sin garantías.

No tiene ninguna relación con los autores de *El mundo de Beakman* ni con Google. Las imágenes pertenecen a sus dueños y se usan solo como homenaje.

## Licencia

Contenido bajo [CC BY-SA 4.0](LICENSE).

Sustituye a los GPTs de [beakman_history](https://github.com/icalvete/beakman_history), [beakman_math](https://github.com/icalvete/beakman_math), [beakman_science](https://github.com/icalvete/beakman_science) y [beakman_language](https://github.com/icalvete/beakman_language). OpenAI retira los GPTs el 11 de diciembre de 2026.
