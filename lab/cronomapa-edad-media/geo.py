"""Geografía del cronomapa: proyección, costa, ríos y utilidades de polígonos.

Todo se calcula aquí, una vez, y la página recibe trazados SVG ya proyectados.
"""
import json
import math
import os

from shapely.geometry import LineString, MultiPolygon, Polygon, box, shape
from shapely.ops import transform, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# Natural Earth (dominio público). No va en el repo: se baja la primera vez.
SOURCES = {
    "land-50m.json": "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-50m.json",
    "rivers-10m.geojson": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"
                          "ne_10m_rivers_lake_centerlines.geojson",
}


def _data(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        import urllib.request
        os.makedirs(DATA, exist_ok=True)
        urllib.request.urlretrieve(SOURCES[name], path)
    return path

# Cónica conforme de Lambert centrada en el Mediterráneo.
PHI1, PHI2, PHI0, LAM0 = map(math.radians, (32.0, 52.0, 40.0, 16.0))
_n = math.log(math.cos(PHI1) / math.cos(PHI2)) / math.log(
    math.tan(math.pi / 4 + PHI2 / 2) / math.tan(math.pi / 4 + PHI1 / 2)
)
_F = math.cos(PHI1) * math.tan(math.pi / 4 + PHI1 / 2) ** _n / _n
_rho0 = _F / math.tan(math.pi / 4 + PHI0 / 2) ** _n


def lcc(lon, lat):
    phi, lam = math.radians(lat), math.radians(lon)
    rho = _F / math.tan(math.pi / 4 + phi / 2) ** _n
    t = _n * (lam - LAM0)
    return rho * math.sin(t), _rho0 - rho * math.cos(t)


# Encuadre general: de Portugal a Bagdad y de Escocia a La Meca.
_FRAME_PTS = [(-10.5, 36.0), (-10.5, 52), (-5, 58.6), (20, 59), (48.5, 36), (46, 20.5), (36, 19.5), (-10, 30)]
_xs, _ys = zip(*(lcc(*p) for p in _FRAME_PTS))
X0, X1, Y0, Y1 = min(_xs), max(_xs), min(_ys), max(_ys)
WIDTH = 1000.0
SCALE = WIDTH / (X1 - X0)
HEIGHT = round((Y1 - Y0) * SCALE, 1)


def proj(lon, lat):
    """lon/lat a coordenadas de la página (y hacia abajo)."""
    x, y = lcc(lon, lat)
    return (x - X0) * SCALE, (Y1 - y) * SCALE


def proj_geom(g):
    return transform(lambda x, y, z=None: _vec_proj(x, y), g)


def _vec_proj(xs, ys):
    try:
        pts = [proj(x, y) for x, y in zip(xs, ys)]
        return [p[0] for p in pts], [p[1] for p in pts]
    except TypeError:
        return proj(xs, ys)


PAGE = box(-20, -20, WIDTH + 20, HEIGHT + 20)


def _decode_topo(path, obj):
    t = json.load(open(path))
    sx, sy = t["transform"]["scale"]
    tx, ty = t["transform"]["translate"]
    arcs = []
    for arc in t["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx):
        out = []
        for i in idx:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(a if not out else a[1:])
        return out

    polys = []
    for g in t["objects"][obj]["geometries"]:
        groups = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for rings in groups:
            rr = [ring(r) for r in rings]
            p = Polygon(rr[0], rr[1:]).buffer(0)
            if not p.is_empty:
                polys.append(p)
    return unary_union(polys)


_LAND_LL = None


def land_ll():
    """Tierra en lon/lat, recortada a la zona del mapa."""
    global _LAND_LL
    if _LAND_LL is None:
        land = _decode_topo(_data("land-50m.json"), "land")
        _LAND_LL = land.intersection(box(-30, 5, 70, 72)).buffer(0)
    return _LAND_LL


def page_geom(g_ll, tol=0.45):
    """Recorta a tierra, proyecta, recorta a la página y simplifica."""
    g = proj_geom(g_ll).buffer(0)
    g = g.intersection(PAGE)
    return g.simplify(tol, preserve_topology=True)


def to_path(g, nd=1):
    """Geometría (ya en página) a atributo d de SVG."""
    if g.is_empty:
        return ""
    fmt = "{:.%df}" % nd

    def ring(coords):
        pts = list(coords)
        if len(pts) < 4:
            return ""
        s = "M" + fmt.format(pts[0][0]) + " " + fmt.format(pts[0][1])
        prev = (round(pts[0][0], nd), round(pts[0][1], nd))
        for x, y in pts[1:-1]:
            c = (round(x, nd), round(y, nd))
            if c == prev:
                continue
            s += "L" + fmt.format(x) + " " + fmt.format(y)
            prev = c
        return s + "Z"

    parts = []
    geoms = g.geoms if hasattr(g, "geoms") else [g]
    for p in geoms:
        if p.geom_type != "Polygon" or p.area < 0.4:
            continue
        parts.append(ring(p.exterior.coords))
        for i in p.interiors:
            parts.append(ring(i.coords))
    return "".join(parts)


def line_path(g, nd=1):
    fmt = "{:.%df}" % nd
    geoms = g.geoms if hasattr(g, "geoms") else [g]
    out = []
    for l in geoms:
        if l.geom_type != "LineString" or l.length < 3:
            continue
        c = list(l.coords)
        out.append("M" + "L".join(fmt.format(x) + " " + fmt.format(y) for x, y in c))
    return "".join(out)


RIVERS = ["Duero", "Tajo", "Tejo", "Ebro", "Guadiana", "Guadalquivir", "Minho", "Rhine", "Rhône", "Danube",
          "Loire", "Seine", "Garonne", "Po", "Tevere", "Nile", "Euphrates", "Tigris", "Thames", "Jordan", "Elbe"]


def rivers_path():
    d = json.load(open(_data("rivers-10m.geojson")))
    lines = []
    for f in d["features"]:
        if (f["properties"].get("name") or "") in RIVERS:
            lines.append(shape(f["geometry"]))
    g = unary_union(lines)
    g = proj_geom(g).intersection(PAGE).simplify(0.5)
    return line_path(g)


def ll_poly(coords):
    """Polígono en lon/lat (lista de pares), arreglado si se cruza."""
    return Polygon(coords).buffer(0)


def ll_line(coords):
    return LineString(coords)


def label_point(g_page):
    """Punto donde poner la etiqueta: el más interior de la pieza mayor."""
    geoms = g_page.geoms if hasattr(g_page, "geoms") else [g_page]
    big = max(geoms, key=lambda p: p.area)
    try:
        from shapely import polylabel
        p = polylabel(big, tolerance=1.0)
    except Exception:
        p = big.representative_point()
    return round(p.x, 1), round(p.y, 1)


if __name__ == "__main__":
    print("frame", WIDTH, HEIGHT)
    land = page_geom(land_ll(), tol=0.35)
    d = to_path(land)
    print("land path chars", len(d))
    print("rivers chars", len(rivers_path()))
    for name, p in [("Toledo", (-4.02, 39.86)), ("Bagdad", (44.4, 33.3)), ("La Meca", (39.8, 21.4)), ("Londres", (-0.12, 51.5))]:
        print(name, [round(v) for v in proj(*p)])
