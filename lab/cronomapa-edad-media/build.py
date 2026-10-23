"""Genera data.json para el cronomapa: épocas, trazados, ciudades y acontecimientos."""
import os
import hashlib
import json
import sys

from shapely.geometry import Polygon
from shapely.ops import unary_union

import consequences as CQ
import glossary as GL
import events as EV
import geo
import iberia
from realms import REALMS

# Las imágenes son comunes a los idiomas: viven en lab/site/media/, a cuatro niveles de la página.
MEDIA = "../../../../media/cronomapa-edad-media/"

START, END = 476, 1493   # END no incluido: el último año es 1492


def realm_geom(periods_cache, realm, y):
    for i, per in enumerate(realm["periods"]):
        a, b, shapes = per[0], per[1], per[2]
        if a <= y < b:
            key = (realm["id"], i)
            if key not in periods_cache:
                g = unary_union([Polygon(s).buffer(0) for s in shapes])
                periods_cache[key] = g.intersection(geo.land_ll()).buffer(0)
            name = per[3] if len(per) > 3 else realm["name"]
            return periods_cache[key], name
    return None, None


def years_of_change():
    ys = {START, END}
    for r in REALMS:
        for per in r["periods"]:
            ys.add(per[0])
            ys.add(per[1])
    ys |= set(iberia.CHANGE_YEARS)
    return sorted(y for y in ys if START <= y <= END)


def main():
    land = geo.page_geom(geo.land_ll(), tol=0.22)
    out = {"w": geo.WIDTH, "h": geo.HEIGHT, "land": geo.to_path(land), "rivers": geo.rivers_path()}

    # Encuadre de la Península (en coordenadas de página).
    xs, ys = zip(*(geo.proj(*p) for p in [(-10.2, 35.7), (-10.2, 44.2), (4.6, 44.2), (4.6, 35.7), (-2.8, 44.3)]))
    out["views"] = {
        "mundo": [0, 0, geo.WIDTH, geo.HEIGHT],
        "peninsula": [round(min(xs) - 6, 1), round(min(ys) - 6, 1), round(max(xs) - min(xs) + 12, 1),
                      round(max(ys) - min(ys) + 12, 1)],
    }

    pal_of = {r["id"]: r["pal"] for r in REALMS}
    tema_of = {r["id"]: r["tema"] for r in REALMS}
    pal_of.update({"andalus": "andalus", "leon": "leon", "castilla": "castilla", "navarra": "navarra",
                   "aragon": "aragon", "cataluna": "cataluna", "portugal": "portugal"})
    tema_of.update({"andalus": 7, "leon": 10, "castilla": 10, "navarra": 10, "aragon": 10, "cataluna": 10,
                    "portugal": 10})

    paths = {}       # hash -> path
    cache = {}
    epochs = []
    years = years_of_change()
    for a, b in zip(years, years[1:]):
        y = a
        layers = []   # (id, name, geom lon/lat)
        for rid, (g, name) in iberia.state(y).items():
            layers.append((rid, name, g))
        for r in REALMS:
            g, name = realm_geom(cache, r, y)
            if g is None:
                continue
            layers.append((r["id"], name, g))
        # Prioridad: primero la Península, luego el orden de REALMS. Mismo id = mismo reino (se unen).
        taken = None
        merged = {}
        order = []
        for rid, name, g in layers:
            if taken is not None:
                g = g.difference(taken).buffer(0)
            if g.is_empty:
                continue
            taken = g if taken is None else unary_union([taken, g])
            if rid in merged:
                merged[rid] = (unary_union([merged[rid][0], g]), merged[rid][1])
            else:
                merged[rid] = (g, name)
                order.append(rid)
        pieces = []
        for rid in order:
            g, name = merged[rid]
            tol = 0.18 if rid in pal_of and pal_of[rid] in ("andalus", "leon", "castilla", "navarra", "aragon",
                                                             "cataluna", "portugal", "visigodo", "suevo") else 0.4
            pg = geo.page_geom(g, tol=tol)
            if pg.is_empty or pg.area < 2:
                continue
            d = geo.to_path(pg)
            if not d:
                continue
            h = hashlib.sha1(d.encode()).hexdigest()[:10]
            paths[h] = d
            lx, ly = geo.label_point(pg)
            pieces.append({"id": rid, "name": name, "pal": pal_of[rid], "tema": tema_of[rid], "p": h,
                           "lx": lx, "ly": ly, "a": round(pg.area)})
        epochs.append({"from": a, "to": b, "pieces": pieces})
        print(f"{a}-{b}: {len(pieces)} reinos", file=sys.stderr)

    out["paths"] = paths
    out["epochs"] = epochs

    out["cities"] = []
    for cid, name, lon, lat, a, b, note in EV.CITIES:
        x, y = geo.proj(lon, lat)
        out["cities"].append({"id": cid, "name": name, "x": round(x, 1), "y": round(y, 1), "from": a, "to": b})

    out["events"] = []
    for eid, kind, title, lon, lat, year, until, tema, text, extra in EV.EVENTS:
        x, y = geo.proj(lon, lat)
        out["events"].append({"id": eid, "kind": kind, "title": title, "x": round(x, 1), "y": round(y, 1),
                              "year": year, "until": until, "tema": tema, "text": text,
                              "aprox": bool(extra.get("aprox")), "fuera": extra.get("fuera")})
    imgs = json.load(open("images.json"))
    used = set()
    for ev in out["events"]:
        ev["img"] = [k for k in EV.EVENT_IMAGES.get(ev["id"], []) if k in imgs]
        used.update(ev["img"])
    for c in out["cities"]:
        k = EV.CITY_IMAGES.get(c["id"], "c_" + c["id"])
        if k in imgs:
            c["img"] = k
            used.add(k)
    out["images"] = {k: {f: imgs[k][f] for f in ("src", "alt", "credit", "license", "link")} for k in sorted(used)}
    for im in out["images"].values():
        im["src"] = MEDIA + os.path.basename(im["src"])
    missing = [e["id"] for e in out["events"] if not e["img"]]
    print("sin imagen:", missing, "| ciudades sin imagen:", [c["id"] for c in out["cities"] if "img" not in c],
          file=sys.stderr)
    for ev in out["events"]:
        c = CQ.C.get(ev["id"])
        if c:
            ev["cons"] = {"corto": c["corto"], "largo": c["largo"], "hoy": c.get("hoy")}
    print("sin consecuencias:", [e["id"] for e in out["events"] if "cons" not in e], file=sys.stderr)
    out["glossary"] = [{"id": i, "t": t, "f": f, "cs": cs, "d": d} for i, t, f, cs, d in GL.G]
    out["stops"] = [{"year": y, "q": q, "a": a} for y, q, a in EV.STOPS]
    out["eras"] = [{"from": a, "to": b, "name": n} for a, b, n in EV.ERAS]

    s = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    open("data.json", "w").write(s)
    print(f"data.json: {len(s) / 1024:.0f} KB, {len(epochs)} épocas, {len(paths)} trazados", file=sys.stderr)


if __name__ == "__main__":
    main()
