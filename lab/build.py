"""Genera las páginas del laboratorio de Beakman a partir de catalog.yml y de los textos de i18n/<idioma>.yml.

Escribe en site/: la raíz (lleva al idioma del navegador), la portada de cada idioma, la página de cada asignatura
con recursos y el 404. Las páginas de cada recurso las genera su propio proyecto (p. ej. cronomapa-edad-media/).

    python3 lab/build.py
"""
import hashlib
import html
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
BASE = "https://lab.beakman.kademy.net"
FONTS = ("https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700"
         "&family=Nunito:ital,wght@0,400;0,600;0,700;0,800;1,400&display=swap")
LAPTOP = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v10H4zM2 19h20" fill="none" stroke="currentColor" '
          'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>')

e = html.escape
# Huella de lab.css en su URL: el servidor no manda reglas de caché y el navegador se quedaba con la versión vieja.
with open(os.path.join(SITE, "lab.css"), "rb") as _f:
    CSS_V = hashlib.md5(_f.read()).hexdigest()[:8]


def load(path):
    with open(os.path.join(HERE, path), encoding="utf-8") as f:
        return yaml.safe_load(f)


def write(rel, text):
    path = os.path.join(SITE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def page(t, lang, title, desc, up, path, body, langs):
    """Esqueleto común. `up` sube desde la página hasta site/; `path` es su ruta tras /<idioma>/."""
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}/{l}/{path}">\n' for l in langs)
    switch = "".join(f'<a class="lang" href="{up}{l}/{path}" hreflang="{l}" lang="{l}">{e(T[l]["nombre_idioma"])}</a>'
                     for l in langs if l != lang)
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}/{lang}/{path}">
{alts}<link rel="icon" href="{up}media/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{up}lab.css?v={CSS_V}">
</head>
<body>
<header class="wrap top">
  <a class="brand" href="{up}{lang}/"><span class="face"><img src="{up}media/beakman.jpg" alt="" width="52" height="52"></span>
    <span><b>{e(t["sitio"])}</b><small>lab.beakman.kademy.net</small></span></a>
  <nav><a href="{e(t["tutores_url"])}">{e(t["tutores"])}</a><a href="{e(t["mis_datos_url"])}">{e(t["mis_datos"])}</a>{switch}</nav>
</header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap"><span>{e(t["pie"])}</span>
  <a href="https://github.com/icalvete/beakman-mcp">{e(t["github"])}</a></div></footer>
</body>
</html>
"""


def count(t, n):
    return t["recurso_1"] if n == 1 else t["recurso_n"].format(n=n)


def resource_card(t, r, s, lang, up, prefix):
    """`s` es la asignatura del recurso: su nombre y su color van en la etiqueta."""
    tx = r[lang]
    pc = f'<span class="pc">{LAPTOP}{e(t["solo_pc"])}</span>' if r.get("solo_pc") else ""
    kind = f'<span class="kind">{e(t["tipos"][r["tipo"]])}</span>' if r.get("tipo") else ""
    return f"""  <a class="resource" href="{prefix}{r["curso"]}/{r["id"]}/" style="--subj: {s["color"]}">
    <img src="{up}media/{r["imagen"]}" alt="" width="800" height="423" loading="lazy">
    <div class="body">
      <div class="meta"><span class="subj">{e(s[lang]["nombre"])}</span>{kind}<span class="tag">{e(tx["temas"])}</span>{pc}</div>
      <h3>{e(tx["titulo"])}</h3>
      <p>{e(tx["descripcion"])}</p>
      <dl class="why">
        <dt>{e(t["objetivo"])}</dt><dd>{e(tx["objetivo"])}</dd>
        <dt>{e(t["metodo"])}</dt><dd>{e(tx["metodo"])}</dd>
      </dl>
    </div>
  </a>
"""


def summary_card(t, r, s, lang, up, prefix):
    """Tarjeta corta de un resumen: en su sección, aparte de los recursos."""
    tx = r[lang]
    return f"""  <a class="summary" href="{prefix}{r["curso"]}/{r["id"]}/" style="--subj: {s["color"]}">
    <img src="{up}media/{r["imagen"]}" alt="" width="800" height="423" loading="lazy">
    <div class="body">
      <div class="meta"><span class="subj">{e(s[lang]["nombre"])}</span><span class="tag">{e(t["cursos"][r["curso"]])} · {e(tx["temas"])}</span></div>
      <h3>{e(tx["titulo"])}</h3>
      <p>{e(tx["descripcion"])}</p>
    </div>
  </a>
"""


def build():
    cat = load("catalog.yml")
    langs = cat["idiomas"]
    subjects = {s["id"]: s for s in cat["asignaturas"]}
    for lang in langs:
        t = T[lang]
        res = [r for r in cat["recursos"] if lang in r]
        # Los resúmenes no son recursos: van en su propia sección, antes que ellos.
        is_summary = lambda r: r.get("tipo") == "resumen"
        slug = lambda r: subjects[r["asignatura"]][lang]["slug"] + "/"
        # Portada del idioma: asignaturas y todos los recursos.
        cards = []
        for s in cat["asignaturas"]:
            st, mine = s[lang], [r for r in res if r["asignatura"] == s["id"]]
            if mine:
                courses = sorted({r["curso"] for r in mine}, key=cat["cursos"].index)
                tag = f'{count(t, sum(not is_summary(r) for r in mine))} ·{" · ".join(t["cursos"][c] for c in courses)}'
                cards.append(f"""  <a class="subject {s["id"]}" href="{st["slug"]}/" style="--subj: {s["color"]}">
    <img src="../media/{s["foto"]}" alt="" loading="lazy">
    <div class="body"><h3>{e(st["nombre"])}</h3><p>{e(st["lema"])}</p><span class="tag">{e(tag)}</span></div>
  </a>
""")
            else:
                cards.append(f"""  <div class="subject soon {s["id"]}">
    <img src="../media/{s["foto"]}" alt="" loading="lazy">
    <div class="body"><h3>{e(st["nombre"])}</h3><p>{e(st["lema"])}</p><span class="tag soon">{e(t["proximamente"])}</span></div>
  </div>
""")
        every = "".join(resource_card(t, r, subjects[r["asignatura"]], lang, "../", slug(r)) for r in res if not is_summary(r))
        sums = [r for r in res if is_summary(r)]
        sums_html = (f'<section class="summaries"><h2>{e(t["resumenes"])}</h2><p class="hint">{e(t["resumenes_lead"])}</p>\n'
                     f'<div class="summary-list">\n'
                     f'{"".join(summary_card(t, r, subjects[r["asignatura"]], lang, "../", slug(r)) for r in sums)}</div></section>\n'
                     if sums else "")
        body = f"""<div class="hero"><h1>{e(t["portada_titulo"])}</h1><p class="lead">{e(t["portada_lead"])}</p></div>
<section><h2>{e(t["asignaturas"])}</h2>
<div class="subjects">
{"".join(cards)}</div></section>
{sums_html}<section><h2>{e(t["todos"])}</h2>
<div class="resources">
{every}</div></section>
<section><div class="tutors"><p>{e(t["tutores_texto"])}</p><a class="btn" href="{e(t["tutores_url"])}">{e(t["tutores"])}</a></div></section>"""
        write(f"{lang}/index.html", page(t, lang, t["sitio"], t["descripcion"], "../", "", body, langs))

        # Página de cada asignatura con recursos, por cursos.
        for s in cat["asignaturas"]:
            st, mine = s[lang], [r for r in res if r["asignatura"] == s["id"]]
            if not mine:
                continue
            # Los resúmenes van arriba, en su propia sección; debajo, el resto por cursos.
            summaries = [r for r in mine if is_summary(r)]
            parts = []
            if summaries:
                parts.append(f'<section class="summaries"><h2>{e(t["resumenes"])}</h2><p class="hint">{e(t["resumenes_lead"])}</p>\n'
                             f'<div class="summary-list">\n{"".join(summary_card(t, r, s, lang, "../../", "") for r in summaries)}</div></section>')
            courses = []
            for c in cat["cursos"]:
                rc = [r for r in mine if r["curso"] == c and not is_summary(r)]
                inner = (f'<div class="resources">\n{"".join(resource_card(t, r, s, lang, "../../", "") for r in rc)}</div>' if rc
                         else f'<p class="empty">{e(t["sin_recursos"].format(curso=t["cursos"][c]))}</p>')
                courses.append(f'<h3 class="course">{e(t["cursos"][c])}</h3>\n{inner}')
            parts.append(f'<section class="all-resources"><h2>{e(t["recursos"])}</h2>\n{chr(10).join(courses)}</section>')
            body = f"""<p class="crumb"><a href="../">← {e(t["volver"])}</a></p>
<div class="subject-head"><div class="polaroid"><img src="../../media/{s["foto"]}" alt=""></div>
  <div><h1>{e(st["nombre"])}</h1><p>{e(st["lema"])}</p></div></div>
{chr(10).join(parts)}"""
            write(f'{lang}/{st["slug"]}/index.html',
                  page(t, lang, f'{st["nombre"]} · {t["sitio"]}', st["lema"], "../../", f'{st["slug"]}/', body, langs))

    # Raíz: al idioma del navegador si está publicado; si no, al primero.
    default = langs[0]
    write("index.html", f"""<!doctype html>
<html lang="{default}">
<head>
<meta charset="utf-8">
<title>{e(T[default]["sitio"])}</title>
<meta http-equiv="refresh" content="0; url={default}/">
<link rel="canonical" href="{BASE}/{default}/">
<script>
(function () {{
  var langs = {langs!r}, want = (navigator.languages || [navigator.language || ""]).map(function (l) {{ return l.slice(0, 2); }});
  for (var i = 0; i < want.length; i++) if (langs.indexOf(want[i]) >= 0) {{ location.replace(want[i] + "/"); return; }}
  location.replace("{default}/");
}})();
</script>
</head>
<body><p><a href="{default}/">{e(T[default]["sitio"])}</a></p></body>
</html>
""")
    t = T[default]
    write("404.html", page(t, default, t["sitio"], t["descripcion"], "/", "", f"""<div class="hero"><h1>404</h1>
<p class="lead"><a href="/{default}/">← {e(t["volver"])}</a></p></div>""", langs))
    print("ok:", ", ".join(langs))


T = {l: load(f"i18n/{l}.yml") for l in load("catalog.yml")["idiomas"]}

if __name__ == "__main__":
    build()
