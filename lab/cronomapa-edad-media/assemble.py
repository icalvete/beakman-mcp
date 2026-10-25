"""Mete data.json en la plantilla y escribe la página publicada (lab/site/es/historia/2eso/cronomapa-edad-media/index.html).

Con argumentos (año, vista, tema) escribe además test.html aquí, que arranca en ese año: sirve para probar en local.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "../site/es/historia/2eso/cronomapa-edad-media")

HEAD = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Mapa de la Edad Media con una barra de años: qué reinos, ciudades y acontecimientos
coincidieron en el tiempo. Historia de 2º de la ESO, con Beakman.">
<link rel="icon" href="../../../../media/favicon.svg" type="image/svg+xml">
<link rel="icon" href="../../../../media/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="../../../../media/apple-touch-icon.png">
{boot}</head>
<body>
"""

tpl = open(os.path.join(HERE, "template.html")).read()
data = open(os.path.join(HERE, "data.json")).read().replace("</", "<\\/")
page = tpl.replace("__DATA__", data)
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "index.html"), "w").write(HEAD.format(boot="") + page + "\n</body>\n</html>\n")
print(f"index.html {len(page) / 1024:.0f} KB")

if len(sys.argv) > 1:
    year, view = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "mundo")
    boot = ("<script>try{localStorage.setItem('cronomapa',JSON.stringify({year:%s,view:'%s'}))}catch(e){}</script>\n"
            % (year, view))
    open(os.path.join(OUT, "test.html"), "w").write(HEAD.format(boot=boot) + page + "\n</body>\n</html>\n")
