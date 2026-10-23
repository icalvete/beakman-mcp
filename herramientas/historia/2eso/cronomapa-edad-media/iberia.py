"""La Península del 712 al 1492: Al-Ándalus y los reinos cristianos.

Método: la Península se parte por una línea de frontera (de oeste a este) que
baja con los siglos. Lo de arriba se reparte entre columnas separadas por
líneas fijas (Portugal | León | Castilla | Navarra | Aragón | Cataluña), y cada
columna pertenece a un reino según la época. Fuente: temas 7 y 10 de 2º ESO.
"""
from shapely.geometry import Polygon, box
from shapely.ops import split, unary_union

from geo import land_ll, ll_line
from realms import GRANADA, IBERIA_MASK

# Frontera cristiano-musulmana (de oeste a este, de mar a mar).
F718 = [(-11.5, 43.05), (-7.2, 43.0), (-6.0, 42.95), (-4.8, 42.95), (-4.0, 43.1), (-3.4, 43.45), (-3.3, 44.8)]
F801 = [(-11.5, 42.6), (-8.6, 42.2), (-7.0, 42.4), (-5.5, 42.6), (-4.5, 42.7), (-3.5, 42.9), (-2.5, 42.85),
        (-1.8, 42.7), (-1.0, 42.5), (0.2, 42.3), (1.0, 41.9), (1.8, 41.45), (2.4, 41.3), (5.5, 41.3)]
F910 = [(-11.5, 41.2), (-8.6, 41.15), (-7.5, 41.1), (-6.2, 41.4), (-5.3, 41.5), (-4.0, 41.6), (-3.2, 41.45),
        (-2.6, 41.6), (-2.0, 42.0), (-1.6, 42.15), (-1.0, 42.25), (0.0, 42.1), (0.8, 41.85), (1.4, 41.4),
        (1.9, 41.2), (5.5, 41.2)]
F1085 = [(-11.5, 40.2), (-8.6, 40.2), (-7.0, 40.1), (-6.0, 40.2), (-5.0, 40.1), (-4.0, 39.6), (-3.0, 39.9),
         (-2.4, 40.5), (-1.9, 41.2), (-1.4, 41.8), (-0.8, 42.15), (0.2, 41.95), (0.9, 41.6), (1.5, 41.3), (5.5, 41.25)]
F1118 = [(-11.5, 40.2), (-8.6, 40.2), (-7.0, 40.1), (-6.0, 40.2), (-5.0, 40.1), (-4.0, 39.6), (-3.0, 39.9),
         (-2.0, 40.7), (-1.2, 41.0), (-0.3, 41.1), (0.6, 41.3), (1.2, 41.15), (5.5, 41.1)]
F1147 = [(-11.5, 38.8), (-9.0, 38.75), (-8.2, 39.0), (-7.4, 39.4), (-6.4, 39.5), (-5.2, 39.6), (-4.2, 39.5),
         (-3.0, 39.6), (-2.0, 40.0), (-1.2, 40.1), (-0.4, 40.5), (0.4, 40.6), (5.5, 40.6)]
F1212 = [(-11.5, 38.2), (-8.6, 38.2), (-7.6, 38.3), (-6.4, 38.4), (-5.0, 38.35), (-3.6, 38.3), (-2.6, 38.6),
         (-1.6, 39.2), (-0.6, 39.7), (-0.2, 39.9), (0.5, 40.3), (5.5, 40.3)]
F1236 = [(-11.5, 37.4), (-8.9, 37.5), (-7.6, 37.6), (-6.3, 37.75), (-5.0, 37.7), (-4.0, 37.6), (-3.0, 38.3),
         (-2.6, 38.6), (-1.6, 39.2), (-0.6, 39.7), (-0.2, 39.9), (0.5, 40.3), (5.5, 40.3)]
F1238 = [(-11.5, 37.4), (-8.9, 37.5), (-7.6, 37.6), (-6.3, 37.75), (-5.0, 37.7), (-4.0, 37.6), (-3.0, 37.7),
         (-1.7, 37.75), (-0.6, 37.5), (1.0, 37.3), (5.5, 37.3)]

FRONTIERS = [
    (712, 718, None),
    (718, 801, F718),
    (801, 910, F801),
    (910, 1085, F910),
    (1085, 1118, F1085),
    (1118, 1147, F1118),
    (1147, 1212, F1147),
    (1212, 1236, F1212),
    (1236, 1238, F1236),
    (1238, 1248, F1238),
    (1248, 1493, "granada"),
]

# Líneas entre reinos cristianos (de norte a sur, de lado a lado del rectángulo).
DIVIDERS = [
    [(-11.5, 41.9), (-8.1, 41.95), (-7.5, 41.85), (-6.6, 41.95), (-6.4, 41.6), (-6.9, 41.0), (-6.9, 40.3),
     (-7.0, 39.6), (-7.4, 38.9), (-7.1, 38.2), (-7.5, 37.5), (-7.4, 34.5)],                       # Portugal | León
    [(-4.3, 46.5), (-4.25, 43.2), (-4.6, 42.3), (-4.9, 41.5), (-5.1, 40.6), (-5.2, 40.0), (-5.4, 39.3),
     (-5.5, 38.6), (-6.0, 38.0), (-6.4, 37.3), (-6.6, 34.5)],                                      # León | Castilla
    [(-2.3, 46.5), (-2.4, 43.3), (-2.6, 42.6), (-2.2, 42.0), (-1.9, 41.6), (-1.6, 41.0), (-1.5, 40.3),
     (-1.3, 39.5), (-1.0, 38.6), (-0.9, 38.0), (-0.8, 34.5)],                                      # Castilla | Navarra y Aragón
    [(-0.85, 46.5), (-0.8, 42.8), (-1.0, 42.4), (-1.4, 42.05), (-1.9, 41.6), (-2.6, 40.8)],        # Navarra | Aragón
    [(0.75, 46.5), (0.7, 42.7), (0.6, 42.0), (0.35, 41.3), (0.9, 40.8), (5.5, 40.6)],             # Aragón | Cataluña
]
COLUMN_SEEDS = {"pt": (-8.3, 40.5), "leon": (-6.0, 42.8), "cast": (-3.7, 42.3), "nav": (-1.6, 42.8),
                "arag": (-0.3, 42.4), "cat": (1.9, 41.9), "sur": (-1.5, 41.2)}


def column_owner(col, y):
    """Qué reino (id, nombre) tiene cada columna en el año y."""
    if col in ("pt", "leon", "cast"):
        if col == "pt" and y >= 1139:
            return "portugal", "Reino de Portugal"
        if y < 910:
            return "leon", "Reino de Asturias"
        if col == "cast" and 931 <= y < 1037:
            return "castilla", "Condado de Castilla" if y < 1035 else "Reino de Castilla"
        if 1037 <= y < 1157:
            return "castilla", "Castilla y León"
        if 1157 <= y < 1230:
            return ("leon", "Reino de León") if col != "cast" else ("castilla", "Reino de Castilla")
        if y >= 1230:
            return "castilla", "Corona de Castilla"
        return "leon", "Reino de León"
    if col == "nav":
        return "navarra", "Reino de Navarra" if y >= 824 else "Pamplona"
    if col in ("arag", "sur"):
        if y < 922:
            return "aragon", "Condado de Aragón"
        if y < 1035:
            return "navarra", "Reino de Navarra"
        if y < 1137:
            return "aragon", "Reino de Aragón"
        return "aragon", "Corona de Aragón"
    if col == "cat":
        if y < 1137:
            return "cataluna", "Condados catalanes"
        return "aragon", "Corona de Aragón"
    raise KeyError(col)


def andalus_label(y):
    if y < 756:
        return "Al-Ándalus (emirato dependiente)"
    if y < 929:
        return "Emirato de Córdoba"
    if y < 1031:
        return "Califato de Córdoba"
    if y < 1090:
        return "Reinos de taifas"
    if y < 1147:
        return "Al-Ándalus almorávide"
    if y < 1238:
        return "Al-Ándalus almohade"
    if y < 1248:
        return "Últimos reinos de Al-Ándalus"
    return "Reino nazarí de Granada"


# Años en los que cambia algo de la Península (para cortar épocas).
CHANGE_YEARS = sorted({f[0] for f in FRONTIERS} | {f[1] for f in FRONTIERS} |
                      {756, 824, 922, 929, 931, 1031, 1035, 1037, 1090, 1137, 1139, 1157, 1229, 1230})

_IBERIA = None
_COLUMNS = None


def iberia():
    global _IBERIA
    if _IBERIA is None:
        _IBERIA = land_ll().intersection(Polygon(IBERIA_MASK)).buffer(0)
    return _IBERIA


def _split_all(geom, lines):
    parts = [geom]
    for ln in lines:
        nxt = []
        for p in parts:
            try:
                nxt.extend(split(p, ll_line(ln)).geoms)
            except Exception:
                nxt.append(p)
        parts = nxt
    return parts


def columns():
    global _COLUMNS
    if _COLUMNS is None:
        rect = box(-11.2, 34.8, 5.2, 46.2)
        parts = _split_all(rect, DIVIDERS)
        cols = {}
        from shapely.geometry import Point
        for name, (x, y) in COLUMN_SEEDS.items():
            for p in parts:
                if p.contains(Point(x, y)):
                    cols[name] = p
        _COLUMNS = cols
    return _COLUMNS


def frontier_at(y):
    for a, b, f in FRONTIERS:
        if a <= y < b:
            return f
    return None


def state(y):
    """Reinos de la Península en el año y: {id: (geom lon/lat, nombre)}."""
    if y < 712:
        return {}
    ib = iberia()
    f = frontier_at(y)
    out = {}
    if f is None:
        return {"andalus": (ib, andalus_label(y))}
    if f == "granada":
        south = ib.intersection(Polygon(GRANADA)).buffer(0)
        north = ib.difference(south).buffer(0)
    else:
        north_poly = Polygon(f + [(5.5, 46.5), (-11.5, 46.5)]).buffer(0)
        north = ib.intersection(north_poly).buffer(0)
        south = ib.difference(north_poly).buffer(0)
    # Islas conquistadas antes de que la frontera llegue a su altura (tema 10: Mallorca, 1229).
    islands = []
    if 1229 <= y < 1238:
        islands.append(box(2.2, 39.2, 3.6, 40.0))
    if 1235 <= y < 1238:
        islands.append(box(1.1, 38.6, 1.7, 39.15))
    moved = None
    for isl in islands:
        piece = south.intersection(isl)
        if not piece.is_empty:
            south = south.difference(isl).buffer(0)
            moved = piece if moved is None else unary_union([moved, piece])
    if moved is not None:
        north = unary_union([north, moved])
    out["andalus"] = (south, andalus_label(y))
    for col, cpoly in columns().items():
        piece = north.intersection(cpoly)
        if piece.is_empty or piece.area < 1e-4:
            continue
        rid, name = column_owner(col, y)
        if rid in out:
            out[rid] = (unary_union([out[rid][0], piece]), out[rid][1])
        else:
            out[rid] = (piece, name)
    return out
