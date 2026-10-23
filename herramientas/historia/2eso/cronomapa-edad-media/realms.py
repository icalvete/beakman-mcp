"""Reinos e imperios del cronomapa, con sus formas por épocas (lon, lat).

Las formas son esquemáticas y generosas hacia el mar: la costa real las recorta.
Fuente: temario de Historia de 2º ESO de Beakman (temas 4 a 14). Donde el
temario no da una fecha que el mapa necesita, va la histórica y se marca con
`# fuera del temario`.
"""

# ---------------------------------------------------------------- piezas base
IBERIA_MASK = [(-10.5, 44.6), (-1.75, 44.6), (-1.75, 43.38), (-1.4, 43.25), (-0.7, 42.88), (0.0, 42.72),
               (0.7, 42.86), (1.45, 42.6), (1.75, 42.5), (2.5, 42.43), (3.2, 42.45), (3.6, 42.4), (5.0, 42.0),
               (5.0, 37.4), (1.0, 37.3), (-2.0, 36.45), (-4.8, 35.95), (-6.6, 35.95), (-6.6, 35.6), (-10.5, 35.6)]

SEPTIMANIA = [(1.7, 42.5), (3.3, 42.5), (4.9, 43.4), (4.6, 44.3), (3.2, 44.2), (1.9, 43.7), (1.3, 43.1), (1.45, 42.6)]
AQUITANIA_VISI = [(-1.75, 43.38), (-2.5, 47.3), (1.5, 47.6), (3.0, 47.0), (4.5, 46.0), (6.5, 44.5), (7.6, 43.8),
                  (6.0, 42.8), (3.3, 42.5), (1.75, 42.5), (0.7, 42.86), (0.0, 42.72), (-0.7, 42.88), (-1.4, 43.25)]
SUEVO = [(-10.5, 41.0), (-10.5, 44.6), (-5.8, 44.6), (-5.8, 42.4), (-6.3, 41.6), (-7.0, 41.0), (-8.5, 40.6)]
SPANIA = [(-6.6, 35.95), (-6.25, 36.8), (-5.6, 37.15), (-4.2, 37.3), (-2.5, 37.55), (-1.0, 38.0), (-0.45, 38.45),
          (0.6, 38.6), (0.6, 36.0), (-4.8, 35.95)]

FRANKS_481 = [(-1.6, 49.7), (1.5, 51.0), (4.0, 51.6), (7.0, 52.0), (8.5, 51.0), (8.0, 49.5), (6.0, 48.5),
              (4.5, 47.5), (3.0, 47.0), (1.5, 47.6), (-1.6, 47.35)]
FRANKS_507 = FRANKS_481[:-1] + [(-1.75, 47.3), (-1.4, 46.0), (-1.75, 43.38), (-1.4, 43.25), (-0.7, 42.88),
                                (0.0, 42.72), (1.3, 43.1), (1.9, 43.7), (3.2, 44.2), (4.0, 45.8), (4.6, 47.0)]
FRANKS_534 = [(-1.6, 49.7), (1.5, 51.0), (4.0, 51.8), (7.0, 53.3), (9.5, 53.6), (11.5, 53.0), (13.0, 51.0),
              (13.5, 48.5), (12.8, 47.3), (10.5, 46.8), (7.8, 45.9), (7.0, 44.2), (7.6, 43.75), (6.5, 43.1),
              (4.9, 43.4), (3.3, 42.5), (1.75, 42.5), (0.7, 42.86), (0.0, 42.72), (-0.7, 42.88), (-1.4, 43.25),
              (-1.75, 43.38), (-1.4, 46.0), (-1.75, 47.3), (-1.6, 47.35)]
CAROLINGIAN = [(-5.2, 48.6), (-1.5, 49.8), (1.5, 51.0), (4.0, 51.8), (7.0, 53.5), (9.0, 54.8), (11.0, 54.2),
               (12.0, 53.6), (13.5, 52.0), (14.5, 50.5), (14.0, 48.8), (16.2, 48.2), (15.8, 46.5), (13.7, 45.6),
               (12.6, 44.9), (10.5, 46.8), (7.8, 45.9), (7.0, 44.2), (7.6, 43.75), (6.5, 43.1), (4.0, 43.4),
               (3.2, 42.45), (1.75, 42.5), (0.7, 42.86), (0.0, 42.72), (-0.7, 42.88), (-1.4, 43.25), (-1.75, 43.38),
               (-2.0, 47.3), (-4.8, 47.8)]
ITALY_N_CAROLINGIAN = [(6.95, 44.2), (6.9, 45.1), (7.0, 46.0), (8.5, 46.4), (10.5, 46.8), (12.5, 46.6), (13.7, 45.75),
                       (13.5, 45.2), (12.6, 44.9), (13.6, 43.4), (13.9, 42.6), (13.6, 41.9), (12.6, 41.4),
                       (11.8, 41.9), (10.0, 42.6), (9.6, 43.6), (7.5, 43.6), (7.55, 43.8)]
FRANCE = [(-5.2, 48.6), (-1.5, 49.8), (1.6, 51.1), (2.6, 51.15), (3.4, 50.6), (4.4, 49.8), (4.9, 48.4),
          (4.9, 47.0), (4.8, 45.5), (4.7, 43.6), (4.3, 43.4), (3.3, 42.5), (1.75, 42.5), (0.7, 42.86), (0.0, 42.72),
          (-0.7, 42.88), (-1.4, 43.25), (-1.75, 43.38), (-2.0, 47.3), (-4.8, 47.8)]
GERMANY = [(2.6, 51.15), (4.0, 51.8), (7.0, 53.5), (9.0, 54.8), (11.0, 54.2), (13.0, 54.2), (14.3, 53.5),
           (14.8, 51.0), (16.8, 50.2), (18.0, 49.6), (17.0, 48.6), (16.9, 47.8), (16.0, 46.6), (13.7, 45.75),
           (12.5, 46.6), (10.5, 46.8), (8.5, 46.4), (7.0, 46.0), (6.9, 45.1), (6.95, 44.2), (7.55, 43.8),
           (6.5, 43.1), (4.3, 43.4), (4.7, 43.6), (4.8, 45.5), (4.9, 47.0), (4.9, 48.4), (4.4, 49.8), (3.4, 50.6)]
ITALY_N = [(6.95, 44.2), (6.9, 45.1), (7.0, 46.0), (8.5, 46.4), (10.5, 46.8), (12.5, 46.6), (13.7, 45.75),
           (13.5, 45.2), (12.6, 44.9), (13.6, 43.4), (13.9, 42.6), (13.6, 41.9), (12.6, 41.4), (11.8, 41.9),
           (10.0, 42.6), (9.6, 43.6), (7.5, 43.6), (7.55, 43.8)]
ITALY = [(7.5, 43.6), (7.55, 43.8), (6.95, 44.2), (6.9, 45.1), (7.0, 46.0), (8.5, 46.4), (10.5, 46.8), (12.5, 46.6),
         (13.7, 45.75), (13.5, 45.2), (13.0, 44.0), (15.5, 42.3), (18.0, 41.0), (18.8, 40.0), (18.8, 37.0),
         (15.62, 37.0), (15.62, 38.05), (15.62, 38.3), (14.8, 38.7), (11.3, 39.0), (10.3, 40.0), (10.0, 42.6),
         (9.6, 43.6)]
SICILY = [(11.9, 36.4), (15.35, 36.4), (15.62, 38.05), (15.62, 38.3), (15.0, 38.6), (12.0, 38.4)]
SOUTH_ITALY = [(12.9, 41.0), (13.3, 41.4), (13.8, 42.0), (14.2, 42.9), (15.5, 43.0), (18.0, 41.0), (18.8, 40.0),
               (18.8, 37.0), (15.62, 37.0), (15.62, 38.05), (15.62, 38.3), (14.8, 38.7), (12.5, 40.2)]
SARD_CORS = [(8.0, 38.7), (10.2, 38.7), (10.0, 41.3), (9.9, 43.2), (8.3, 43.2), (8.0, 41.0)]
SARDINIA = [(8.0, 38.7), (10.2, 38.7), (10.0, 41.28), (8.0, 41.28)]
PAPAL = [(12.2, 41.5), (11.7, 42.2), (11.5, 42.9), (12.2, 43.6), (11.9, 44.25), (12.4, 44.6), (13.0, 43.9),
         (13.6, 43.4), (13.9, 42.6), (13.6, 41.9), (13.0, 41.4), (12.6, 41.4)]
BYZ_CORRIDOR = [(12.0, 44.6), (12.6, 44.9), (13.0, 43.6), (12.8, 42.8), (12.6, 41.8), (12.1, 41.6), (11.8, 42.3),
                (12.2, 43.4), (11.9, 44.2)]
CALABRIA = [(15.62, 37.8), (15.62, 38.3), (16.0, 39.7), (16.8, 39.9), (17.3, 39.0), (16.4, 37.8)]
APULIA = [(16.6, 40.9), (18.8, 40.9), (18.8, 39.7), (17.6, 39.9), (16.9, 40.4)]

ENGLAND = [(-5.7, 49.9), (-3.6, 50.2), (1.4, 50.8), (2.0, 51.4), (1.9, 52.9), (0.3, 53.6), (-0.5, 54.6),
           (-1.6, 55.7), (-2.1, 55.8), (-3.0, 55.1), (-3.5, 54.5), (-3.0, 53.6), (-2.9, 53.0), (-3.0, 52.0),
           (-2.7, 51.6), (-4.0, 51.2), (-4.5, 50.9), (-5.7, 50.5)]
WALES = [(-2.9, 53.4), (-3.0, 52.0), (-2.7, 51.6), (-5.6, 51.5), (-5.0, 52.2), (-4.5, 53.6)]
ANGEVIN = [(-1.9, 49.75), (1.6, 50.1), (1.8, 49.0), (1.0, 48.2), (0.6, 47.2), (1.5, 46.6), (2.5, 45.5),
           (2.0, 44.2), (0.0, 42.72), (-0.7, 42.88), (-1.4, 43.25), (-1.75, 43.38), (-1.3, 44.5), (-1.6, 46.5),
           (-2.2, 47.3), (-1.5, 47.6), (-1.5, 48.6)]
GUYENNE = [(-1.75, 43.38), (-1.4, 43.25), (-1.2, 45.6), (0.5, 45.2), (0.6, 44.3), (-0.4, 43.5)]
BRETIGNY = [(-1.75, 43.38), (-1.4, 43.25), (-0.7, 42.88), (0.0, 42.72), (1.5, 43.4), (2.2, 44.6), (1.8, 45.6),
            (0.8, 46.6), (-1.0, 46.5), (-1.6, 46.4)]
LANCASTER_N = [(-1.9, 49.75), (1.6, 50.1), (2.6, 51.0), (4.0, 50.0), (3.8, 48.4), (2.8, 47.8), (1.5, 47.6),
               (0.0, 47.6), (-1.0, 48.6), (-1.6, 48.6)]
NORMANDY = [(-1.9, 49.75), (1.6, 50.1), (1.8, 49.0), (1.0, 48.4), (-1.0, 48.5), (-1.6, 48.6)]
CALAIS = [(1.55, 50.75), (2.15, 50.75), (2.15, 51.1), (1.55, 51.1)]

MAGHREB_W = [(-12, 29.5), (-12, 35.5), (-6.6, 35.5), (-6.6, 35.9), (-4.8, 35.9), (-2.0, 36.4), (1.0, 36.9), (1.0, 33.0),
             (-3.0, 31.0), (-8.0, 29.0)]
MAGHREB_C = [(1.0, 33.0), (1.0, 36.9), (8.5, 37.4), (8.5, 33.6), (5.0, 33.4)]
IFRIQIYA = [(8.5, 33.6), (8.5, 37.4), (11.5, 37.55), (11.5, 34.2), (15.0, 33.2), (19.0, 31.5), (19.0, 29.8),
            (15.5, 30.6), (12.5, 31.6), (10.0, 32.6)]
CYRENAICA = [(19.0, 29.8), (19.0, 31.5), (22.0, 33.5), (25.0, 32.5), (25.0, 30.6), (22.0, 30.2)]
EGYPT = [(25.0, 30.6), (25.0, 32.5), (29.0, 32.0), (32.5, 31.8), (34.25, 31.32), (34.9, 29.5), (33.6, 27.8),
         (33.4, 26.0), (33.3, 24.0), (32.5, 23.6), (32.3, 25.6), (31.0, 27.4), (30.6, 28.8), (29.4, 29.4), (28.0, 30.5)]
SYRIA = [(34.0, 31.4), (34.25, 31.32), (34.9, 29.5), (36.0, 29.2), (38.0, 29.5), (39.0, 32.0), (40.6, 34.5),
         (40.0, 37.2), (38.5, 37.2), (36.2, 36.9), (35.9, 36.0), (35.6, 35.4), (35.3, 34.5), (34.6, 33.0)]
IRAQ = [(40.0, 37.2), (42.5, 37.5), (45.5, 36.5), (46.5, 34.5), (48.6, 31.0), (48.0, 29.5), (46.5, 29.0),
        (44.0, 29.2), (41.0, 31.5), (39.0, 32.0), (40.6, 34.5)]
ARABIA = [(34.9, 29.5), (36.0, 29.2), (38.0, 29.5), (39.0, 32.0), (41.0, 31.5), (44.0, 29.2), (46.5, 29.0),
          (48.0, 29.5), (50.0, 28.0), (52.0, 24.0), (56.0, 24.0), (56.0, 15.0), (42.0, 12.0), (38.0, 18.0),
          (34.9, 27.5)]
HEJAZ = [(36.0, 27.5), (40.5, 27.5), (42.0, 22.0), (41.5, 19.5), (39.0, 19.5), (37.5, 23.5)]

ANATOLIA = [(26.0, 40.05), (26.6, 40.35), (29.02, 40.98), (29.08, 41.25), (29.1, 41.6), (33.0, 42.2), (37.0, 41.6),
            (41.6, 41.6), (43.5, 40.5), (44.5, 39.5), (44.0, 37.5), (42.5, 37.5), (40.0, 37.2), (38.5, 37.2),
            (36.2, 36.9), (35.9, 36.0), (34.8, 35.9), (33.0, 35.9), (30.0, 36.1), (28.0, 36.4), (26.4, 38.0),
            (26.0, 39.0)]
ANATOLIA_W = [(26.0, 40.05), (26.6, 40.35), (29.02, 40.98), (29.08, 41.25), (29.1, 41.6), (31.5, 41.4),
              (31.0, 39.5), (30.5, 37.0), (30.0, 36.1), (28.0, 36.4), (26.4, 38.0), (26.0, 39.0)]
ANATOLIA_NW = [(26.0, 40.05), (26.6, 40.35), (29.02, 40.98), (29.08, 41.25), (30.5, 41.2), (31.0, 40.3),
               (29.6, 39.6), (27.6, 39.5), (26.6, 39.6)]
ANTIOCH = [(35.9, 36.0), (36.2, 36.9), (37.2, 37.1), (37.4, 36.0), (36.4, 35.4), (35.6, 35.4)]
CYPRUS = [(32.1, 34.4), (34.8, 34.4), (34.8, 35.8), (32.1, 35.8)]
CRETE = [(23.3, 34.7), (26.5, 34.7), (26.5, 35.8), (23.3, 35.8)]
BALKANS_S = [(18.8, 40.0), (19.4, 42.2), (21.0, 42.4), (23.0, 42.2), (26.0, 42.0), (28.0, 42.2), (29.08, 41.25),
             (29.02, 40.98), (26.6, 40.35), (26.0, 40.05), (25.8, 39.0), (26.3, 38.0), (27.9, 36.4),
             (28.5, 35.0), (22.0, 35.0), (20.5, 36.5)]
BALKANS_N = [(19.4, 42.2), (18.5, 42.5), (16.0, 43.5), (15.0, 45.3), (19.0, 45.0), (22.5, 44.7), (24.0, 43.7),
             (26.0, 44.1), (28.6, 44.3), (28.0, 42.2), (26.0, 42.0), (23.0, 42.2), (21.0, 42.4)]
BULGARIA = [(22.5, 44.7), (24.0, 43.7), (26.0, 44.1), (28.6, 44.3), (28.0, 42.2), (26.0, 42.0), (23.0, 42.2),
            (22.4, 42.8)]
THRACE = [(26.0, 40.05), (25.5, 40.8), (24.0, 41.0), (24.0, 41.6), (26.0, 42.0), (28.0, 42.2), (29.08, 41.25),
          (29.02, 40.98), (26.6, 40.35)]
MACEDONIA = [(22.0, 40.0), (24.0, 40.3), (24.0, 41.6), (22.0, 41.6)]
CONSTANTINOPLE = [(28.45, 40.9), (28.45, 41.3), (29.08, 41.25), (29.02, 40.98)]
MOREA = [(21.0, 36.3), (23.6, 36.3), (23.3, 37.95), (21.2, 38.3)]
EPIRUS = [(19.3, 39.1), (21.3, 38.9), (21.4, 40.5), (19.6, 41.0)]
OTTOMAN_1400 = ANATOLIA_W[:5] + [(33.5, 41.8), (36.0, 41.4), (36.0, 38.5), (33.0, 37.0), (30.0, 36.1),
                                 (28.0, 36.4), (26.4, 38.0), (26.0, 39.0)]
OTTOMAN_BALKANS_1400 = [(26.0, 40.05), (25.5, 40.8), (22.0, 40.3), (20.5, 41.0), (21.0, 42.4), (22.5, 44.7),
                        (24.0, 43.7), (26.0, 44.1), (28.6, 44.3), (28.0, 42.2), (29.08, 41.25), (29.02, 40.98),
                        (26.6, 40.35)]
OTTOMAN_BALKANS_1453 = [(18.8, 40.0), (19.4, 42.2), (18.5, 42.5), (18.0, 44.0), (19.0, 45.0), (22.5, 44.7),
                        (24.0, 43.7), (26.0, 44.1), (28.6, 44.3), (28.0, 42.2), (29.08, 41.25), (29.02, 40.98),
                        (26.6, 40.35), (26.0, 40.05), (25.8, 39.0), (24.0, 37.8), (22.0, 35.0), (20.5, 36.5)]
CRUSADERS_1099 = [(34.0, 31.2), (35.6, 31.0), (35.8, 32.8), (36.4, 34.2), (36.9, 35.8), (38.2, 36.5), (39.2, 37.4),
                  (38.3, 37.9), (36.6, 37.2), (36.0, 36.9), (35.6, 35.4), (35.2, 34.3), (34.4, 32.8)]
CRUSADERS_1187 = [(34.9, 32.7), (35.4, 32.7), (36.2, 34.3), (36.6, 35.8), (36.4, 36.8), (35.9, 36.6), (35.6, 35.4),
                  (35.2, 34.3), (34.6, 32.9)]
GRANADA = [(-5.6, 35.97), (-5.4, 36.6), (-4.9, 37.15), (-4.3, 37.35), (-3.6, 37.55), (-2.8, 37.6), (-2.0, 37.5),
           (-1.65, 37.15), (-1.7, 36.0)]

# ------------------------------------------------------------------- reinos
# Cada reino: id, nombre por defecto, paleta, y periodos (desde, hasta, formas, nombre opcional).
# "hasta" no incluido. Las formas son listas de polígonos.
# El orden de REALMS es la prioridad: si dos se pisan, gana el primero.

REALMS = [
    # La Península después del 711 la genera iberia.py; esto es lo de antes.
    {"id": "suevos", "name": "Reino suevo", "pal": "suevo", "tema": 4,
     "periods": [(476, 585, [SUEVO])]},
    {"id": "bizancio", "name": "Imperio bizantino", "pal": "bizancio", "tema": 5,
     "periods": [
         (476, 534, [BALKANS_S, BALKANS_N, ANATOLIA, SYRIA, EGYPT, CYRENAICA, CYPRUS, CRETE]),
         (534, 554, [BALKANS_S, BALKANS_N, ANATOLIA, SYRIA, EGYPT, CYRENAICA, CYPRUS, CRETE, IFRIQIYA, SARD_CORS]),
         (554, 568, [BALKANS_S, BALKANS_N, ANATOLIA, SYRIA, EGYPT, CYRENAICA, CYPRUS, CRETE, IFRIQIYA, SARD_CORS,
                     ITALY, SICILY, SPANIA]),
         (568, 625, [BALKANS_S, BALKANS_N, ANATOLIA, SYRIA, EGYPT, CYRENAICA, CYPRUS, CRETE, IFRIQIYA, SARD_CORS,
                     SICILY, BYZ_CORRIDOR, CALABRIA, APULIA, SPANIA]),
         (625, 636, [BALKANS_S, BALKANS_N, ANATOLIA, SYRIA, EGYPT, CYRENAICA, CYPRUS, CRETE, IFRIQIYA, SARD_CORS,
                     SICILY, BYZ_CORRIDOR, CALABRIA, APULIA]),
         (636, 642, [BALKANS_S, BALKANS_N, ANATOLIA, EGYPT, CYRENAICA, CYPRUS, CRETE, IFRIQIYA, SARD_CORS,
                     SICILY, BYZ_CORRIDOR, CALABRIA, APULIA]),
         (642, 681, [BALKANS_S, BALKANS_N, ANATOLIA, CYPRUS, CRETE, IFRIQIYA, SARD_CORS, SICILY, BYZ_CORRIDOR,
                     CALABRIA, APULIA]),
         (681, 698, [BALKANS_S, ANATOLIA, CYPRUS, CRETE, IFRIQIYA, SARD_CORS, SICILY, BYZ_CORRIDOR, CALABRIA, APULIA]),
         (698, 751, [BALKANS_S, ANATOLIA, CYPRUS, CRETE, SICILY, BYZ_CORRIDOR, CALABRIA, APULIA]),
         (751, 827, [BALKANS_S, ANATOLIA, CYPRUS, CRETE, SICILY, CALABRIA, APULIA]),
         (827, 902, [BALKANS_S, ANATOLIA, CYPRUS, SICILY, CALABRIA, APULIA]),  # fuera del temario: Creta árabe
         (902, 969, [BALKANS_S, ANATOLIA, CYPRUS, CALABRIA, APULIA]),
         (969, 1018, [BALKANS_S, ANATOLIA, CYPRUS, CRETE, CALABRIA, APULIA, ANTIOCH]),
         (1018, 1071, [BALKANS_S, BALKANS_N, ANATOLIA, CYPRUS, CRETE, CALABRIA, APULIA, ANTIOCH]),
         (1071, 1185, [BALKANS_S, BALKANS_N, ANATOLIA_W, CYPRUS, CRETE]),
         (1185, 1204, [BALKANS_S, BALKANS_N, ANATOLIA_W, CRETE]),
         (1204, 1261, [ANATOLIA_W, EPIRUS], "Imperio bizantino (en Nicea)"),
         (1261, 1330, [THRACE, MACEDONIA, MOREA, ANATOLIA_NW]),
         (1330, 1354, [THRACE, MACEDONIA, MOREA]),
         (1354, 1453, [CONSTANTINOPLE, MOREA]),
     ]},
    {"id": "latino", "name": "Imperio latino (cruzados)", "pal": "latino", "tema": 5,
     "periods": [(1204, 1261, [THRACE])]},
    {"id": "cruzados", "name": "Estados cruzados", "pal": "cruzados", "tema": 5,
     "periods": [(1099, 1187, [CRUSADERS_1099]), (1187, 1291, [CRUSADERS_1187])]},
    {"id": "otomanos", "name": "Imperio otomano", "pal": "otomano", "tema": 5,
     "periods": [(1300, 1354, [ANATOLIA_NW]),
                 (1354, 1400, [ANATOLIA_W, THRACE]),
                 (1400, 1453, [OTTOMAN_1400, OTTOMAN_BALKANS_1400]),
                 (1453, 1493, [ANATOLIA, OTTOMAN_BALKANS_1453])]},
    {"id": "selyucidas", "name": "Turcos selyúcidas", "pal": "selyucida", "tema": 5,
     "periods": [(1071, 1300, [ANATOLIA])]},
    {"id": "bulgaros", "name": "Búlgaros", "pal": "bulgaro", "tema": 5,
     "periods": [(681, 1018, [BULGARIA]), (1185, 1396, [BULGARIA])]},
    {"id": "papa", "name": "Estados Pontificios", "pal": "papa", "tema": 8,
     "periods": [(756, 1493, [PAPAL])]},  # fuera del temario: fecha de 756
    {"id": "sicilia_mus", "name": "Sicilia musulmana", "pal": "magreb", "tema": 6,
     "periods": [(902, 1071, [SICILY])]},
    {"id": "normandos", "name": "Reino normando de Sicilia", "pal": "normando", "tema": 8,
     "periods": [(1071, 1282, [SICILY, SOUTH_ITALY])]},  # fuera del temario
    {"id": "napoles", "name": "Reino de Nápoles", "pal": "normando", "tema": 8,
     "periods": [(1282, 1442, [SOUTH_ITALY])]},  # fuera del temario
    # Corona de Aragón fuera de la Península (la parte peninsular la añade iberia.py con el mismo id).
    {"id": "aragon", "name": "Corona de Aragón", "pal": "aragon", "tema": 10,
     "periods": [(1282, 1323, [SICILY]), (1323, 1442, [SICILY, SARDINIA]),
                 (1442, 1493, [SICILY, SARDINIA, SOUTH_ITALY])]},  # fuera del temario: fechas
    {"id": "inglaterra", "name": "Reino de Inglaterra", "pal": "inglaterra", "tema": 12,
     "periods": [(927, 1154, [ENGLAND]),
                 (1154, 1204, [ENGLAND, ANGEVIN]),
                 (1204, 1284, [ENGLAND, GUYENNE]),
                 (1284, 1360, [ENGLAND, WALES, GUYENNE]),
                 (1360, 1369, [ENGLAND, WALES, BRETIGNY, CALAIS]),
                 (1369, 1420, [ENGLAND, WALES, GUYENNE, CALAIS]),
                 (1420, 1435, [ENGLAND, WALES, GUYENNE, LANCASTER_N]),
                 (1435, 1450, [ENGLAND, WALES, GUYENNE, NORMANDY]),
                 (1450, 1453, [ENGLAND, WALES, GUYENNE, CALAIS]),
                 (1453, 1493, [ENGLAND, WALES, CALAIS])]},
    {"id": "anglosajones", "name": "Anglos y sajones", "pal": "inglaterra", "tema": 4,
     "periods": [(476, 927, [ENGLAND])]},
    {"id": "vandalos", "name": "Reino vándalo", "pal": "vandalo", "tema": 4,
     "periods": [(476, 534, [IFRIQIYA, SARD_CORS])]},
    {"id": "odoacro", "name": "Reino de Odoacro", "pal": "ostrogodo", "tema": 4,
     "periods": [(476, 493, [ITALY, SICILY])]},
    {"id": "ostrogodos", "name": "Reino ostrogodo", "pal": "ostrogodo", "tema": 4,
     "periods": [(493, 554, [ITALY, SICILY])]},
    {"id": "lombardos", "name": "Reino lombardo", "pal": "lombardo", "tema": 8,
     "periods": [(568, 774, [ITALY_N, SOUTH_ITALY])]},  # fuera del temario
    {"id": "visigodos", "name": "Reino visigodo", "pal": "visigodo", "tema": 4,
     "periods": [(476, 507, [IBERIA_MASK, AQUITANIA_VISI], "Reino visigodo de Tolosa"),
                 (507, 711, [IBERIA_MASK, SEPTIMANIA], "Reino visigodo de Toledo")]},
    {"id": "francos", "name": "Reino franco", "pal": "franco", "tema": 4,
     "periods": [(481, 507, [FRANKS_481]), (507, 534, [FRANKS_507]), (534, 768, [FRANKS_534])]},
    {"id": "carolingio", "name": "Imperio carolingio", "pal": "franco", "tema": 8,
     "periods": [(768, 774, [CAROLINGIAN], "Reino franco de Carlomagno"),
                 (774, 800, [CAROLINGIAN, ITALY_N_CAROLINGIAN], "Reino franco de Carlomagno"),
                 (800, 843, [CAROLINGIAN, ITALY_N_CAROLINGIAN], "Imperio de Carlomagno")]},
    {"id": "francia", "name": "Reino de Francia", "pal": "franco", "tema": 8,
     "periods": [(843, 987, [FRANCE], "Francia occidental"), (987, 1493, [FRANCE])]},
    {"id": "italia", "name": "Reino de Italia", "pal": "lombardo", "tema": 8,
     "periods": [(843, 962, [ITALY_N])]},  # fuera del temario
    {"id": "germania", "name": "Sacro Imperio", "pal": "germania", "tema": 8,
     "periods": [(843, 962, [GERMANY], "Francia oriental"), (962, 1493, [GERMANY, ITALY_N])]},  # fuera del temario
    # Islam
    {"id": "mahoma", "name": "Comunidad de Mahoma", "pal": "islam", "tema": 6,
     "periods": [(622, 632, [HEJAZ])]},
    {"id": "califato", "name": "Califato", "pal": "islam", "tema": 6,
     "periods": [(632, 636, [ARABIA]), (636, 642, [ARABIA, SYRIA, IRAQ]), (642, 661, [ARABIA, SYRIA, IRAQ, EGYPT, CYRENAICA])]},
    {"id": "omeyas", "name": "Califato omeya", "pal": "omeya", "tema": 6,
     "periods": [(661, 670, [ARABIA, SYRIA, IRAQ, EGYPT, CYRENAICA]),
                 (670, 698, [ARABIA, SYRIA, IRAQ, EGYPT, CYRENAICA, IFRIQIYA]),
                 (698, 720, [ARABIA, SYRIA, IRAQ, EGYPT, CYRENAICA, IFRIQIYA, MAGHREB_C, MAGHREB_W]),
                 (720, 750, [ARABIA, SYRIA, IRAQ, EGYPT, CYRENAICA, IFRIQIYA, MAGHREB_C, MAGHREB_W, SEPTIMANIA])]},
    {"id": "abasies", "name": "Califato abasí", "pal": "abasi", "tema": 6,
     "periods": [(750, 788, [ARABIA, SYRIA, IRAQ, EGYPT, CYRENAICA, IFRIQIYA, MAGHREB_C, MAGHREB_W]),
                 (788, 909, [ARABIA, SYRIA, IRAQ, EGYPT, CYRENAICA, IFRIQIYA, MAGHREB_C]),
                 (909, 1258, [IRAQ])]},
    {"id": "oriente", "name": "Reinos musulmanes de Oriente", "pal": "oriente", "tema": 6,
     "periods": [(909, 1258, [SYRIA, EGYPT, CYRENAICA, ARABIA]),
                 (1258, 1493, [SYRIA, EGYPT, CYRENAICA, ARABIA, IRAQ])]},
    {"id": "almoravides", "name": "Almorávides", "pal": "almoravide", "tema": 7,
     "periods": [(1056, 1147, [MAGHREB_W])]},
    {"id": "almohades", "name": "Almohades", "pal": "almohade", "tema": 7,
     "periods": [(1147, 1269, [MAGHREB_W, MAGHREB_C, IFRIQIYA])]},
    {"id": "magreb", "name": "Reinos musulmanes del Magreb", "pal": "magreb", "tema": 6,
     "periods": [(788, 909, [MAGHREB_W]), (909, 1056, [MAGHREB_W, MAGHREB_C, IFRIQIYA]),
                 (1056, 1147, [MAGHREB_C, IFRIQIYA]), (1269, 1493, [MAGHREB_W, MAGHREB_C, IFRIQIYA])]},
]
