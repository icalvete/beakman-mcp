# Mi mundo de Beakman

<p align="center">
  <img src="historia/logo.jpeg" alt="Beakman, Historia" height="140">
  <img src="matematicas/logo.jpeg" alt="Beakman, Matemáticas" height="140">
  <img src="ciencias/logo.png" alt="Beakman, Ciencias" height="140">
  <img src="lengua/logo.webp" alt="Beakman, Lengua" height="140">
</p>

Cuatro tutores de IA para 1º y 2º de la ESO: **Historia, Matemáticas, Ciencias y Lengua y Literatura**. Funcionan como Gems de Google Gemini, que son gratis.

Están inspirados en Beakman, el profesor loco de "El mundo de Beakman". Explican con imágenes mentales, preguntan antes de dar respuestas y tratan el error como parte del aprendizaje. Lo que buscan es que se entienda, no que se memorice.

Documentación: **https://icalvete.github.io/beakman-gems/**

## Cómo funciona

Todo el contenido vive en este repo. Nadie copia nada a mano en Gemini:

1. Editas un tema o las instrucciones y haces push a `main`.
2. El Action [sync-drive.yml](.github/workflows/sync-drive.yml) ejecuta [scripts/build.py](scripts/build.py), que genera tres ficheros por asignatura.
3. El Action los sube a Google Drive con rclone, sobrescribiéndolos. Cada fichero mantiene su ID.
4. Cada Gem tiene esos tres ficheros enlazados desde Drive. Gemini usa siempre su versión más reciente.

Lo único manual es crear cada Gem la primera vez, porque Google no tiene API para crearlos.

## Estructura

```
beakman/base.md          personalidad y método de Beakman, comunes a todas las asignaturas
beakman/gem_stub.txt     texto fijo de la caja de instrucciones del Gem
<asignatura>/asignatura.md   lo propio de cada asignatura (cabecera con nombre y descripción del Gem)
<asignatura>/1eso/*.txt      temas de 1º, en orden por nombre
<asignatura>/2eso/*.txt      temas de 2º (en preparación)
<asignatura>/logo.*          la imagen de Beakman de esa asignatura
scripts/build.py         genera dist/<Asignatura>/ con los ficheros de cada Gem
docs/                    la web de documentación (GitHub Pages)
```

Cada Gem recibe siempre los mismos tres ficheros:

- `Beakman_<Asignatura>_00_Instrucciones.txt`: la base común más lo propio de la asignatura.
- `Beakman_<Asignatura>_01_Curso_1ESO.txt`: todos los temas de 1º.
- `Beakman_<Asignatura>_02_Curso_2ESO.txt`: todos los temas de 2º.

Un tema nuevo va dentro del fichero de su curso. Un fichero nuevo habría que enlazarlo a mano en el Gem.

## Probar en local

```
python3 scripts/build.py     # genera dist/
```

`dist/<Asignatura>/gem.txt` tiene el nombre, la descripción, las instrucciones y los ficheros que hay que poner al crear el Gem.

## Montar el tuyo

Los pasos están en la [guía para montarlo](https://icalvete.github.io/beakman-gems/guia/montar-el-tuyo.html): client_id propio de Google, rclone, el secreto `RCLONE_CONF` y la creación de los Gems.

## Aviso

Es una herramienta de apoyo y no sustituye al profesorado. Puede equivocarse. Recomendamos supervisión adulta con menores. Se ofrece tal cual, sin garantías.

Es un homenaje a "El mundo de Beakman" (Beakman's World, 1992-1998) sin ninguna relación con sus autores ni con Google. Las imágenes pertenecen a sus dueños.

## Licencia

Contenido bajo [CC BY-SA 4.0](LICENSE).

Sustituye a los GPTs de [beakman_history](https://github.com/icalvete/beakman_history), [beakman_math](https://github.com/icalvete/beakman_math), [beakman_science](https://github.com/icalvete/beakman_science) y [beakman_language](https://github.com/icalvete/beakman_language). OpenAI retira los GPTs el 11 de diciembre de 2026.
