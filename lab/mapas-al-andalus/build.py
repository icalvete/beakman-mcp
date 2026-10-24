"""Los mapas de al-Ándalus: recorta del cronomapa la Península en seis momentos y escribe la página.

Lee ../cronomapa-edad-media/data.json (hay que haberlo construido antes) y template.html, y escribe
../site/es/historia/2eso/mapas-al-andalus/index.html con los datos dentro.

    python3 lab/mapas-al-andalus/build.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "../cronomapa-edad-media/data.json")
OUT = os.path.join(HERE, "../site/es/historia/2eso/mapas-al-andalus/index.html")

# Un año por etapa (el que mejor la representa en el cronomapa).
YEARS = [720, 800, 1000, 1050, 1150, 1450]
# Colores claros de los reinos, los mismos que el cronomapa.
PAL = {"andalus": "#2f8a58", "leon": "#8c4ea9", "castilla": "#c23b2e", "navarra": "#c4567f", "aragon": "#e2a636",
       "cataluna": "#e9bd4f", "portugal": "#2c7ca8", "franco": "#4d6cae", "almoravide": "#7a983a", "almohade": "#557f2b",
       "magreb": "#7ea887", "visigodo": "#c0893b", "bizancio": "#7b4c9c", "normando": "#6b8fc0", "omeya": "#379566",
       "papa": "#e6cf7c", "suevo": "#8ea567"}
CITIES = {"cordoba", "toledo", "sevilla", "granada", "zaragoza", "valencia", "leon", "oviedo", "barcelona", "lisboa",
          "burgos", "pamplona", "santiago"}

d = json.load(open(SRC, encoding="utf-8"))
x0, y0, w, h = d["views"]["peninsula"]
pad = 6
box = [x0 - pad, y0 - pad, w + 2 * pad, h + 2 * pad]


def inside(x, y):
    return box[0] <= x <= box[0] + box[2] and box[1] <= y <= box[1] + box[3]


steps = []
for year in YEARS:
    ep = next(e for e in d["epochs"] if e["from"] <= year < e["to"])
    pieces = []
    for p in ep["pieces"]:
        pieces.append({"id": p["id"], "name": p["name"], "c": PAL.get(p["pal"], "#9aa38f"), "p": p["p"],
                       "lx": p["lx"], "ly": p["ly"], "a": p.get("a", 0),
                       "show": inside(p["lx"], p["ly"]) and p["id"] not in ("francia", "francos", "carolingio")})
    cities = [{"n": c["name"], "x": c["x"], "y": c["y"]} for c in d["cities"]
              if c["id"] in CITIES and c["from"] <= year < c.get("to", 9999)]
    steps.append({"year": year, "pieces": pieces, "cities": cities})

used = {p["p"] for s in steps for p in s["pieces"]}
data = {"box": box, "land": d["land"], "rivers": d["rivers"], "paths": {k: v for k, v in d["paths"].items() if k in used},
        "steps": steps}
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
page = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(page)
print(f"index.html {len(page) / 1024:.0f} KB, {len(steps)} mapas")
