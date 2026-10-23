"""Busca en Wikipedia (es) la imagen principal de cada artículo, su licencia y su autor, y baja una miniatura.

Salida: las miniaturas, en la carpeta común a los idiomas (lab/site/media/cronomapa-edad-media/<clave>.jpg),
y images.json {clave: {src, alt, credit, license, link, title}}.
"""
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

UA = "BeakmanCronomapa/1.0 (+https://github.com/icalvete/beakman-mcp)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../site/media/cronomapa-edad-media")

# clave -> (artículo de es.wikipedia, texto alternativo)
WANT = {
    # personajes
    "romulo": ("Rómulo Augústulo", "Moneda de Rómulo Augústulo, último emperador de Occidente"),
    "clodoveo": ("Clodoveo I", "Clodoveo, rey de los francos"),
    "justiniano": ("Justiniano I", "Justiniano en el mosaico de San Vital de Rávena"),
    "leovigildo": ("Leovigildo", "Leovigildo, rey visigodo"),
    "recaredo": ("Recaredo I", "La conversión de Recaredo"),
    "pelayo": ("Don Pelayo", "Pelayo, primer rey de Asturias"),
    "abderraman1": ("Abderramán I", "Abderramán I, emir de Córdoba"),
    "carlomagno": ("Carlomagno", "Carlomagno, emperador"),
    "abderraman3": ("Abderramán III", "Abderramán III, califa de Córdoba"),
    "alfonso6": ("Alfonso VI de León", "Alfonso VI, rey de Castilla y León"),
    "alfonso1ar": ("Alfonso I de Aragón", "Alfonso I el Batallador, rey de Aragón"),
    "petronila": ("Petronila de Aragón", "Petronila de Aragón y Ramón Berenguer IV"),
    "alfonso1pt": ("Alfonso I de Portugal", "Alfonso Enríquez, primer rey de Portugal"),
    "jaime1": ("Jaime I de Aragón", "Jaime I el Conquistador"),
    "fernando3": ("Fernando III de Castilla", "Fernando III el Santo"),
    "alfonso10": ("Alfonso X de Castilla", "Alfonso X el Sabio"),
    "osman": ("Osmán I", "Osmán I, fundador del Imperio otomano"),
    "enrique2": ("Enrique II de Castilla", "Enrique de Trastámara"),
    "juana": ("Juana de Arco", "Juana de Arco"),
    "gutenberg": ("Johannes Gutenberg", "Johannes Gutenberg"),
    "mehmed2": ("Mehmed II", "El sultán Mehmed II"),
    "reyescatolicos": ("Reyes Católicos", "Isabel I de Castilla y Fernando II de Aragón"),
    "colon": ("Cristóbal Colón", "Cristóbal Colón"),
    # monumentos y lugares
    "santasofia": ("Santa Sofía", "Santa Sofía, en Estambul"),
    "sanvital": ("Basílica de San Vital", "La basílica de San Vital de Rávena"),
    "spania": ("Provincia de Spania", "La provincia bizantina de Spania"),
    "kaaba": ("Kaaba", "La Kaaba, en La Meca"),
    "mezquitaprofeta": ("Mezquita del Profeta", "La Mezquita del Profeta, en Medina"),
    "omeyasdamasco": ("Mezquita de los Omeyas", "La Mezquita de los Omeyas, en Damasco"),
    "guadalete": ("Batalla de Guadalete", "La batalla de Guadalete"),
    "abasies": ("Califato abasí", "El califato abasí"),
    "casasabiduria": ("Casa de la Sabiduría", "Sabios en una biblioteca abasí"),
    "mezquitacordoba": ("Mezquita-catedral de Córdoba", "Los arcos de la Mezquita de Córdoba"),
    "marcahispanica": ("Marca Hispánica", "La Marca Hispánica"),
    "catedralsantiago": ("Catedral de Santiago de Compostela", "La catedral de Santiago de Compostela"),
    "cluny": ("Abadía de Cluny", "La abadía de Cluny"),
    "medinaazahara": ("Medina Azahara", "Restos de Medina Azahara"),
    "taifas": ("Reinos de taifas", "Los reinos de taifas"),
    "cisma": ("Cisma de Oriente y Occidente", "El Cisma de Oriente"),
    "bolonia": ("Universidad de Bolonia", "La Universidad de Bolonia"),
    "jerusalen1099": ("Sitio de Jerusalén (1099)", "La toma de Jerusalén por los cruzados"),
    "saintdenis": ("Basílica de Saint-Denis", "La basílica de Saint-Denis"),
    "sanisidoro": ("Real Colegiata de San Isidoro", "San Isidoro de León, donde se reunieron las Cortes"),
    "portico": ("Pórtico de la Gloria", "El Pórtico de la Gloria"),
    "navas": ("Batalla de las Navas de Tolosa", "La batalla de las Navas de Tolosa"),
    "salamanca_u": ("Universidad de Salamanca", "La Universidad de Salamanca"),
    "valencia1238": ("Conquista de Valencia", "La conquista de Valencia"),
    "alhambra": ("Alhambra", "La Alhambra de Granada"),
    "giralda": ("Giralda", "La Giralda de Sevilla"),
    "catedralleon": ("Catedral de León", "La catedral de León"),
    "cienanos": ("Guerra de los Cien Años", "Una batalla de la Guerra de los Cien Años"),
    "peste": ("Peste negra", "Entierro de víctimas de la peste negra"),
    "jacquerie": ("Jacquerie", "La Jacquerie"),
    "palaciopapas": ("Palacio de los Papas", "El Palacio de los Papas de Aviñón"),
    "revuelta1381": ("Revuelta campesina de 1381", "La revuelta campesina de 1381 en Inglaterra"),
    "pogromo1391": ("Pogromo de 1391", "Los ataques contra las juderías de 1391"),
    "santamariafiore": ("Catedral de Santa María del Fiore", "La cúpula de Brunelleschi en Florencia"),
    "caidaconstantinopla": ("Caída de Constantinopla", "La caída de Constantinopla"),
    "inquisicion": ("Inquisición española", "La Inquisición española"),
    "tomagranada": ("Toma de Granada", "La rendición de Granada"),
    "rodrigo": ("Rodrigo (rey)", "Don Rodrigo, último rey visigodo"),
    # ciudades
    "c_roma": ("Roma", "Roma"), "c_constantinopla": ("Constantinopla", "Constantinopla"),
    "c_ravena": ("Rávena", "Rávena"), "c_toledo": ("Toledo", "Toledo"), "c_cordoba": ("Córdoba (España)", "Córdoba"),
    "c_sevilla": ("Sevilla", "Sevilla"), "c_granada": ("Granada", "Granada"), "c_valencia": ("Valencia", "Valencia"),
    "c_zaragoza": ("Zaragoza", "Zaragoza"), "c_barcelona": ("Barcelona", "Barcelona"), "c_lisboa": ("Lisboa", "Lisboa"),
    "c_leon": ("León (España)", "León"), "c_oviedo": ("Oviedo", "Oviedo"), "c_burgos": ("Burgos", "Burgos"),
    "c_santiago": ("Santiago de Compostela", "Santiago de Compostela"), "c_salamanca": ("Salamanca", "Salamanca"),
    "c_pamplona": ("Pamplona", "Pamplona"), "c_damasco": ("Damasco", "Damasco"), "c_bagdad": ("Bagdad", "Bagdad"),
    "c_meca": ("La Meca", "La Meca"), "c_medina": ("Medina", "Medina"), "c_jerusalen": ("Jerusalén", "Jerusalén"),
    "c_alejandria": ("Alejandría", "Alejandría"), "c_cairo": ("El Cairo", "El Cairo"), "c_cartago": ("Cartago", "Cartago"),
    "c_kairuan": ("Cairuán", "Cairuán"), "c_aquisgran": ("Aquisgrán", "Aquisgrán"), "c_paris": ("París", "París"),
    "c_venecia": ("Venecia", "Venecia"), "c_genova": ("Génova", "Génova"), "c_florencia": ("Florencia", "Florencia"),
    "c_londres": ("Londres", "Londres"), "c_tolosa": ("Toulouse", "Tolosa"),
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def api(base, **params):
    params.update({"format": "json", "formatversion": "2"})
    return json.loads(get(base + "?" + urllib.parse.urlencode(params)))


def strip(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


SEARCH = {
    # clave: (búsqueda en Commons, texto alternativo)
    "clodoveo": ("Master of Saint Giles Baptism of Clovis", "El bautismo de Clodoveo"),
    "abderraman3": ("Baixeras Abderraman III embajada", "Abderramán III recibe a un embajador"),
    "abasies": ("Samarra Malwiya minaret", "El alminar en espiral de Samarra, de época abasí"),
    "bolonia": ("Archiginnasio Bologna courtyard", "El Archiginnasio de Bolonia"),
    "salamanca_u": ("Fachada Universidad de Salamanca plateresca", "La fachada de la Universidad de Salamanca"),
    "inquisicion": ("Berruguete Auto de fe Santo Domingo", "Un auto de fe, pintado por Pedro Berruguete"),
    "cienanos": ("Battle of Crecy Froissart", "La batalla de Crécy, en una crónica de la época"),
    "alhambra": ("Court of the Lions Alhambra fountain", "El Patio de los Leones de la Alhambra"),
    "sanvital": ("Basilica of San Vitale Ravenna", "Mosaicos de San Vital de Rávena"),
    "sanisidoro": ("Panteón de los Reyes San Isidoro León", "El panteón de San Isidoro de León"),
    "jacquerie": ("Jacquerie Meaux miniature Froissart", "La Jacquerie en una miniatura de la época"),
    "palaciopapas": ("Palais des Papes Avignon", "El Palacio de los Papas de Aviñón"),
    "revuelta1381": ("Peasants Revolt 1381 Froissart Wat Tyler", "La revuelta campesina de 1381"),
    "pogromo1391": ("Judería Sevilla Santa Cruz barrio", "El antiguo barrio judío de Sevilla"),
    "rodrigo": ("Rodrigo rey visigodo Madrazo", "Don Rodrigo, último rey visigodo"),
    "c_constantinopla": ("Walls of Constantinople", "Las murallas de Constantinopla"),
    "c_toledo": ("View of Toledo El Greco Metropolitan", "Vista de Toledo, de El Greco"),
    "c_cordoba": ("Puente romano Córdoba Mezquita", "El puente romano y la Mezquita de Córdoba"),
    "c_sevilla": ("Torre del Oro Sevilla", "La Torre del Oro de Sevilla"),
    "c_granada": ("Alhambra Mirador de San Nicolás", "La Alhambra desde el Albaicín"),
    "c_valencia": ("Torres de Serranos Valencia", "Las Torres de Serranos de Valencia"),
    "c_zaragoza": ("Aljafería Zaragoza", "La Aljafería de Zaragoza"),
    "c_barcelona": ("Santa Maria del Mar Barcelona façana", "Santa María del Mar, en Barcelona"),
    "c_lisboa": ("Castelo de São Jorge Lisboa", "El castillo de San Jorge de Lisboa"),
    "c_leon": ("Basílica San Isidoro León fachada", "San Isidoro de León"),
    "c_oviedo": ("Santa María del Naranco", "Santa María del Naranco, en Oviedo"),
    "c_burgos": ("Catedral de Burgos fachada", "La catedral de Burgos"),
    "c_santiago": ("Plaza del Obradoiro catedral Santiago", "La plaza del Obradoiro de Santiago"),
    "c_salamanca": ("Puente romano Salamanca catedral", "El puente romano y la catedral de Salamanca"),
    "c_pamplona": ("Catedral de Pamplona claustro gótico", "El claustro de la catedral de Pamplona"),
    "c_damasco": ("Damascus Straight Street old city", "La ciudad vieja de Damasco"),
    "c_bagdad": ("Mustansiriya Madrasah Baghdad", "La madrasa Mustansiriya de Bagdad, de época abasí"),
    "c_meca": ("Kaaba Masjid al-Haram", "La Kaaba, en La Meca"),
    "c_jerusalen": ("Dome of the Rock Jerusalem", "La Cúpula de la Roca, en Jerusalén"),
    "c_alejandria": ("Citadel of Qaitbay Alexandria", "La ciudadela de Qaitbay, en Alejandría"),
    "c_cairo": ("Mosque of Ibn Tulun courtyard", "La mezquita de Ibn Tulun, en El Cairo"),
    "c_aquisgran": ("Aachen Cathedral Palatine Chapel octagon", "La capilla de Carlomagno en Aquisgrán"),
    "c_paris": ("Notre-Dame de Paris façade", "Notre-Dame de París"),
    "c_venecia": ("Basilica di San Marco facade Venice", "La basílica de San Marcos de Venecia"),
    "c_genova": ("Porta Soprana Genova", "La Porta Soprana de Génova"),
    "c_londres": ("Tower of London White Tower", "La Torre Blanca de Londres"),
}


def commons_search(query):
    r = api("https://commons.wikimedia.org/w/api.php", action="query", list="search", srsearch=query + " filetype:bitmap",
            srnamespace=6, srlimit=8)
    return [x["title"][5:] for x in r["query"]["search"]]


def fetch_file(key, fname, alt, article):
    ii = api("https://commons.wikimedia.org/w/api.php", action="query", titles="File:" + fname,
             prop="imageinfo", iiprop="url|extmetadata|mime|size", iiurlwidth=640)
    info = ii["query"]["pages"][0]["imageinfo"][0]
    if info.get("mime") not in ("image/jpeg", "image/png") or info.get("width", 0) < 500:
        return None
    md = info.get("extmetadata", {})
    lic = strip(md.get("LicenseShortName", {}).get("value", ""))
    if not lic:
        return None
    artist = strip(md.get("Artist", {}).get("value", "")) or "Autor desconocido"
    if len(artist) > 80:
        artist = artist[:77] + "…"
    raw = get(info.get("thumburl") or info["url"])
    tmp = os.path.join(OUT, key + ".src")
    open(tmp, "wb").write(raw)
    subprocess.run(["convert", tmp + "[0]", "-auto-orient", "-resize", "640x480>", "-strip", "-quality", "78",
                    "-background", "white", "-flatten", os.path.join(OUT, key + ".jpg")], check=True)
    os.remove(tmp)
    return {"src": f"img/{key}.jpg", "alt": alt, "credit": artist, "license": lic,
            "link": info.get("descriptionurl"), "file": fname, "article": article}


def search_main(keys, skip=0):
    meta = json.load(open("images.json"))
    for key in keys:
        q, alt = SEARCH[key]
        try:
            cands = commons_search(q)[skip:]
            got = None
            for fname in cands:
                got = fetch_file(key, fname, alt, q)
                if got:
                    break
            if got:
                meta[key] = got
                print(f"{key}: {got['file']} · {got['license']} · {got['credit'][:40]}")
            else:
                print(f"{key}: nada válido para «{q}»")
        except Exception as e:  # noqa: BLE001
            print(f"{key}: ERROR {e}")
        time.sleep(0.3)
    json.dump(meta, open("images.json", "w"), ensure_ascii=False, indent=1)


def main(keys):
    os.makedirs(OUT, exist_ok=True)
    meta = json.load(open("images.json")) if os.path.exists("images.json") else {}
    for key in keys:
        title, alt = WANT[key]
        try:
            q = api("https://es.wikipedia.org/w/api.php", action="query", titles=title, redirects=1,
                    prop="pageimages", piprop="name")
            page = q["query"]["pages"][0]
            fname = page.get("pageimage")
            if not fname:
                print(f"{key}: sin imagen en «{title}»")
                continue
            ii = api("https://commons.wikimedia.org/w/api.php", action="query", titles="File:" + fname,
                     prop="imageinfo", iiprop="url|extmetadata|mime", iiurlwidth=640)
            info = ii["query"]["pages"][0]["imageinfo"][0]
            md = info.get("extmetadata", {})
            lic = strip(md.get("LicenseShortName", {}).get("value", ""))
            artist = strip(md.get("Artist", {}).get("value", "")) or "Autor desconocido"
            if len(artist) > 80:
                artist = artist[:77] + "…"
            thumb = info.get("thumburl") or info["url"]
            raw = get(thumb)
            tmp = os.path.join(OUT, key + ".src")
            open(tmp, "wb").write(raw)
            dst = os.path.join(OUT, key + ".jpg")
            subprocess.run(["convert", tmp + "[0]", "-auto-orient", "-resize", "640x480>", "-strip",
                            "-quality", "78", "-background", "white", "-flatten", dst], check=True)
            os.remove(tmp)
            meta[key] = {"src": f"img/{key}.jpg", "alt": alt, "credit": artist, "license": lic,
                         "link": info.get("descriptionurl"), "file": fname, "article": page["title"]}
            print(f"{key}: {fname} · {lic} · {artist[:40]}")
        except Exception as e:  # noqa: BLE001
            print(f"{key}: ERROR {e}")
        time.sleep(0.3)
    json.dump(meta, open("images.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--search"]:
        args = sys.argv[2:]
        skip = 0
        if args and args[0].startswith("--skip="):
            skip = int(args[0].split("=")[1]); args = args[1:]
        search_main(args or list(SEARCH), skip)
    else:
        main(sys.argv[1:] or list(WANT))
