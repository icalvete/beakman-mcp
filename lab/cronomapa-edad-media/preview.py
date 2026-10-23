"""Vista previa en PNG de varias épocas, para revisar fronteras."""
import json
import sys

import cairosvg

d = json.load(open("data.json"))
COL = {"suevo": "#8fa86a", "bizancio": "#7d4f9e", "latino": "#c98aa8", "cruzados": "#d98c6a", "otomano": "#a3333d",
       "selyucida": "#3e9b9b", "bulgaro": "#9a8a5a", "papa": "#e8d58a", "magreb": "#7fa98a", "normando": "#6f93c2",
       "aragon": "#e0a83a", "inglaterra": "#c4553b", "vandalo": "#b27b4f", "ostrogodo": "#d4a35a",
       "lombardo": "#c9a58f", "visigodo": "#c08a3e", "franco": "#4f6fb0", "germania": "#5d5d6e", "islam": "#2f8f5b",
       "omeya": "#3b9a6b", "abasi": "#245e4f", "oriente": "#5f8f70", "almoravide": "#7c9a3c", "almohade": "#5d8a2f",
       "andalus": "#2e8b57", "leon": "#8a4fa8", "castilla": "#c0392b", "navarra": "#c2577f", "cataluna": "#e6b84a",
       "portugal": "#2f7fa8"}


def svg(year, view="mundo"):
    ep = next(e for e in d["epochs"] if e["from"] <= year < e["to"])
    vb = d["views"][view]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(map(str, vb))}" width="1400" '
             f'height="{round(1400 * vb[3] / vb[2])}"><rect x="-50" y="-50" width="2000" height="2000" fill="#cfdde6"/>',
             f'<path d="{d["land"]}" fill="#efe6d2" stroke="#7a6a50" stroke-width="0.4"/>']
    for p in ep["pieces"]:
        parts.append(f'<path d="{d["paths"][p["p"]]}" fill="{COL[p["pal"]]}" fill-opacity="0.75" stroke="#222" '
                     f'stroke-width="0.3"/>')
    parts.append(f'<path d="{d["rivers"]}" fill="none" stroke="#5b8bb0" stroke-width="0.4"/>')
    fs = 7 if view == "mundo" else 2.2
    for p in ep["pieces"]:
        parts.append(f'<text x="{p["lx"]}" y="{p["ly"]}" font-size="{fs}" text-anchor="middle" '
                     f'font-family="sans-serif">{p["name"]}</text>')
    parts.append(f'<text x="{vb[0] + 5}" y="{vb[1] + vb[3] * 0.06}" font-size="{fs * 3}">{year}</text></svg>')
    return "".join(parts)


for arg in sys.argv[1:]:
    y, _, view = arg.partition(":")
    cairosvg.svg2png(bytestring=svg(int(y), view or "mundo").encode(), write_to=f"prev-{y}-{view or 'mundo'}.png")
    print("ok", arg)
