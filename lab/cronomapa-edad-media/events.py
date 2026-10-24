"""Ciudades, batallas, obras y acontecimientos del cronomapa (temas 4 a 14 de 2º ESO).

tipo: ciudad | batalla | hecho | arte | cultura
"aprox": la fecha es aproximada ("hacia"). "fuera": dato que no trae el temario.
Los textos van en la voz de Beakman: tú, frases cortas, sin "fácil" ni "obvio".
"""

CITIES = [
    # id, nombre, lon, lat, desde, hasta, nota corta
    ("roma", "Roma", 12.48, 41.9, 476, 1493, "La ciudad de los papas"),
    ("constantinopla", "Constantinopla", 28.97, 41.01, 476, 1453, "Capital de Bizancio"),
    ("estambul", "Estambul", 28.97, 41.01, 1453, 1493, "Capital otomana"),
    ("ravena", "Rávena", 12.2, 44.42, 476, 1493, ""),
    ("toledo", "Toledo", -4.02, 39.86, 476, 1493, ""),
    ("madrid", "Madrid", -3.71, 40.42, 865, 1493, "Mayrit, fortaleza de Córdoba"),
    ("cordoba", "Córdoba", -4.78, 37.88, 476, 1493, ""),
    ("sevilla", "Sevilla", -5.99, 37.39, 476, 1493, ""),
    ("granada", "Granada", -3.6, 37.18, 476, 1493, ""),
    ("valencia", "Valencia", -0.38, 39.47, 476, 1493, ""),
    ("zaragoza", "Zaragoza", -0.89, 41.65, 476, 1493, ""),
    ("barcelona", "Barcelona", 2.17, 41.39, 476, 1493, ""),
    ("lisboa", "Lisboa", -9.14, 38.72, 476, 1493, ""),
    ("leon", "León", -5.57, 42.6, 910, 1493, ""),
    ("oviedo", "Oviedo", -5.85, 43.36, 791, 1493, ""),
    ("burgos", "Burgos", -3.7, 42.34, 884, 1493, ""),
    ("santiago", "Santiago", -8.54, 42.88, 830, 1493, ""),
    ("salamanca", "Salamanca", -5.66, 40.96, 476, 1493, ""),
    ("pamplona", "Pamplona", -1.64, 42.81, 476, 1493, ""),
    ("damasco", "Damasco", 36.29, 33.51, 476, 1493, ""),
    ("bagdad", "Bagdad", 44.36, 33.31, 762, 1493, ""),
    ("meca", "La Meca", 39.83, 21.42, 476, 1493, ""),
    ("medina", "Medina", 39.61, 24.47, 476, 1493, ""),
    ("jerusalen", "Jerusalén", 35.23, 31.78, 476, 1493, ""),
    ("alejandria", "Alejandría", 29.92, 31.2, 476, 1493, ""),
    ("cairo", "El Cairo", 31.24, 30.04, 969, 1493, ""),
    ("cartago", "Cartago", 10.32, 36.85, 476, 698, ""),
    ("kairuan", "Cairuán", 10.1, 35.68, 670, 1493, ""),
    ("aquisgran", "Aquisgrán", 6.08, 50.78, 794, 1493, ""),
    ("paris", "París", 2.35, 48.86, 476, 1493, ""),
    ("venecia", "Venecia", 12.33, 45.44, 476, 1493, ""),
    ("genova", "Génova", 8.93, 44.41, 476, 1493, ""),
    ("florencia", "Florencia", 11.25, 43.77, 476, 1493, ""),
    ("londres", "Londres", -0.13, 51.5, 476, 1493, ""),
    ("tolosa", "Tolosa", 1.44, 43.6, 476, 1493, ""),
]

# id, tipo, título, lon, lat, año, hasta (o None), tema, texto, extra
EVENTS = [
    ("e476", "hecho", "Fin del Imperio romano de Occidente", 12.2, 44.42, 476, None, 4,
     "Odoacro, un jefe germano, quita la corona al último emperador de Occidente, Rómulo Augústulo. "
     "Aquí acaba la Edad Antigua y empieza la Edad Media. Ojo: en Oriente el Imperio sigue en pie.", {}),
    ("e507", "batalla", "Los francos vencen a los visigodos", 0.16, 46.64, 507, None, 4,
     "Clodoveo y sus francos derrotan a los visigodos en Vouillé. Los visigodos pierden casi toda la Galia "
     "y se quedan con Hispania. Su capital acabará siendo Toledo.", {"fuera": "lugar de la batalla"}),
    ("e527", "hecho", "Justiniano, emperador", 28.97, 41.01, 527, 565, 5,
     "Justiniano quiere reconstruir el viejo Imperio romano. Conquista Italia, el norte de África y un trozo "
     "del sur de Hispania. Mira cómo crece el morado bizantino.", {}),
    ("e537", "arte", "Santa Sofía", 28.98, 41.0, 537, None, 5,
     "Justiniano termina en Constantinopla una iglesia con una cúpula enorme que parece flotar, llena de "
     "mosaicos dorados. Fue iglesia durante casi mil años.", {"fuera": "año 537"}),
    ("e547", "arte", "San Vital de Rávena", 12.2, 44.42, 547, None, 5,
     "Una iglesia bizantina en Italia, con mosaicos de Justiniano y su esposa Teodora. "
     "Es la prueba de que Bizancio llegó a mandar en Rávena.", {"fuera": "año 547"}),
    ("e554", "hecho", "Bizancio en el sur de Hispania", -0.98, 37.6, 554, 624, 5,
     "Los bizantinos se quedan con la costa del sureste, alrededor de Cartagena. Durante setenta años, "
     "en la Península conviven visigodos, suevos y bizantinos.", {"fuera": "fechas exactas"}),
    ("e570", "hecho", "Nace Mahoma", 39.83, 21.42, 570, None, 6,
     "En La Meca, una ciudad de comerciantes en medio del desierto, nace Mahoma. Mientras, en Europa mandan "
     "francos, visigodos y Bizancio. Nadie podía imaginar lo que iba a pasar.", {"aprox": True}),
    ("e585", "hecho", "Leovigildo conquista el reino suevo", -8.43, 41.55, 585, None, 4,
     "El rey visigodo Leovigildo se queda con el reino suevo del noroeste. Casi toda la Península tiene "
     "ya un solo rey.", {}),
    ("e589", "hecho", "Recaredo se hace católico", -4.02, 39.86, 589, None, 4,
     "En el III Concilio de Toledo, el rey Recaredo se convierte al catolicismo. Así godos e "
     "hispanorromanos comparten religión.", {}),
    ("e622", "hecho", "La Hégira", 39.61, 24.47, 622, None, 6,
     "Mahoma tiene que huir de La Meca a Medina. Ese viaje es el año 1 del calendario musulmán. "
     "Fíjate en la manchita verde que aparece en Arabia: es el comienzo.", {}),
    ("e632", "hecho", "Muere Mahoma", 39.61, 24.47, 632, None, 6,
     "Cuando muere, gran parte de Arabia ya es musulmana. Le suceden los califas. Mueve la barra despacio "
     "y mira qué rápido crece el verde.", {}),
    ("e661", "hecho", "Los omeyas, en Damasco", 36.29, 33.51, 661, None, 6,
     "Empieza la dinastía de los omeyas, con capital en Damasco. Con ellos el islam llegará hasta la "
     "Península Ibérica.", {}),
    ("e711", "batalla", "Batalla de Guadalete", -5.9, 36.6, 711, None, 7,
     "Tariq cruza el estrecho (Gibraltar viene de «monte de Tariq») y vence al rey visigodo Rodrigo. "
     "En pocos años, casi toda la Península es Al-Ándalus.", {}),
    ("e722", "batalla", "Covadonga", -5.05, 43.31, 722, None, 10,
     "Según la tradición, Pelayo vence a los musulmanes en las montañas de Asturias. Nace un pequeño reino "
     "cristiano en el norte: mira el hilo de color pegado al Cantábrico.", {}),
    ("e732", "batalla", "Batalla de Poitiers", 0.34, 46.58, 732, None, 8,
     "Carlos Martel, jefe de los francos, frena cerca de Poitiers a un ejército musulmán que venía de Al-Ándalus. "
     "Los musulmanes ya no avanzarán al norte de los Pirineos.", {}),
    ("e750", "hecho", "Los abasíes toman el poder", 44.36, 33.31, 750, None, 6,
     "Una nueva dinastía, la abasí, sustituye a los omeyas. En el 762 fundarán Bagdad, que será un gran "
     "centro de sabiduría.", {}),
    ("e756", "hecho", "Abderramán I, emir de Córdoba", -4.78, 37.88, 756, None, 7,
     "Un omeya que ha escapado de los abasíes llega a Al-Ándalus y se hace independiente. "
     "Córdoba ya no obedece a nadie de fuera.", {}),
    ("e762", "cultura", "Fundación de Bagdad", 44.36, 33.31, 762, None, 6,
     "Los abasíes fundan Bagdad. Allí, en la Casa de la Sabiduría, traducen libros griegos, persas e indios. "
     "De allí nos llegan los números que usas y el cero.", {}),
    ("e785", "arte", "Mezquita de Córdoba", -4.78, 37.88, 785, None, 7,
     "Empieza la mezquita, con su bosque de columnas y arcos rojos y blancos. Se ampliará varias veces "
     "durante dos siglos.", {"fuera": "año 785"}),
    ("e800", "hecho", "Carlomagno, emperador", 12.48, 41.9, 800, None, 8,
     "El papa corona en Roma a Carlomagno, rey de los francos. Mira el mapa: a la vez hay un emperador "
     "en Occidente, otro en Constantinopla y un califa en Bagdad.", {}),
    ("e801", "hecho", "La Marca Hispánica", 2.17, 41.39, 801, None, 10,
     "Los francos toman Barcelona y crean una zona de frontera en el noreste: la Marca Hispánica. "
     "De ahí saldrán los condados catalanes.", {"fuera": "año 801"}),
    ("e830", "cultura", "El Camino de Santiago", -8.54, 42.88, 830, None, 10,
     "Se encuentra en Galicia el que se cree sepulcro del apóstol Santiago. Empieza una ruta de "
     "peregrinos que unirá la Península con el resto de Europa.", {"aprox": True, "fuera": "fecha"}),
    ("e843", "hecho", "Tratado de Verdún", 5.38, 49.16, 843, None, 8,
     "Los nietos de Carlomagno, Lotario, Luis y Carlos, se reparten el imperio. El gran imperio cristiano "
     "ha durado muy poco: cada trozo irá por su lado.", {}),
    ("e865", "hecho", "Nace Mayrit", -3.71, 40.42, 865, None, 7,
     "El emir Muhammad I manda levantar una fortaleza junto al río Manzanares para vigilar el camino de Toledo "
     "frente a los cristianos del norte. Se llama Mayrit: es el origen de Madrid.", {"aprox": True}),
    ("e950", "cultura", "Norias, acequias y cultivos nuevos", -0.37, 39.47, 950, None, 7,
     "En Al-Ándalus se extiende el regadío: norias que suben el agua, acequias que la reparten y cultivos nuevos "
     "como el arroz, la berenjena, la naranja amarga o el azafrán. Por eso Al-Ándalus es tan rico.", {"aprox": True}),
    ("e910", "cultura", "Monasterio de Cluny", 4.66, 46.43, 910, None, 8,
     "Se funda Cluny, un monasterio que dirigirá cientos de monasterios por Europa. Sus monjes copian "
     "libros antiguos en el scriptorium.", {"fuera": "año 910"}),
    ("e929", "hecho", "Abderramán III, califa", -4.78, 37.88, 929, None, 7,
     "Abderramán III se proclama califa. Es el gran momento de Al-Ándalus: Córdoba es una de las ciudades "
     "más grandes de Europa.", {}),
    ("e936", "arte", "Medina Azahara", -4.87, 37.89, 936, None, 7,
     "Abderramán III manda construir junto a Córdoba una ciudad-palacio para su corte.", {"fuera": "año 936"}),
    ("e1031", "hecho", "Fin del califato: los taifas", -4.78, 37.88, 1031, None, 7,
     "El califato se rompe en pequeños reinos, los taifas. Son ricos pero débiles, y pagan tributos "
     "(parias) a los reyes cristianos.", {}),
    ("e1054", "hecho", "Cisma de Oriente", 28.97, 41.01, 1054, None, 5,
     "Las Iglesias de Roma y Constantinopla se separan para siempre: de ahí vienen la Iglesia católica "
     "y la ortodoxa.", {}),
    ("e1085", "hecho", "Alfonso VI conquista Toledo", -4.02, 39.86, 1085, None, 10,
     "El rey de Castilla y León aprovecha la debilidad de los taifas y toma Toledo. Fíjate cómo la "
     "frontera salta del Duero al Tajo.", {}),
    ("e1088", "cultura", "Universidad de Bolonia", 11.34, 44.49, 1088, None, 9,
     "Nace en Bolonia una de las primeras universidades. Se estudia derecho, medicina y teología.",
     {"fuera": "año 1088"}),
    ("e1099", "batalla", "Los cruzados toman Jerusalén", 35.23, 31.78, 1099, None, 5,
     "Ejércitos cristianos de Europa llegan a Oriente y crean los Estados cruzados en la costa. "
     "Durante dos siglos, cruzados y musulmanes serán vecinos.", {"fuera": "fecha y cruzadas"}),
    ("e1118", "hecho", "Alfonso I conquista Zaragoza", -0.89, 41.65, 1118, None, 10,
     "El rey de Aragón, el Batallador, toma Zaragoza. El valle del Ebro pasa a ser cristiano.", {}),
    ("e1137", "hecho", "Nace la Corona de Aragón", -0.89, 41.65, 1137, None, 10,
     "Se unen el reino de Aragón y los condados catalanes. Mira cómo dos colores pasan a ser uno.", {}),
    ("e1143", "hecho", "Portugal, reino independiente", -8.43, 41.55, 1143, None, 10,
     "Portugal se separa de León y se convierte en reino propio. Ya existe la frontera que verás en "
     "los mapas de hoy.", {"fuera": "año 1143"}),
    ("e1144", "arte", "Nace el gótico", 2.36, 48.94, 1144, None, 11,
     "En la abadía de Saint-Denis, cerca de París, aparecen el arco apuntado y las grandes vidrieras. "
     "Las iglesias se vuelven altas y luminosas.", {"fuera": "año 1144"}),
    ("e1188", "hecho", "Cortes de León", -5.57, 42.6, 1188, None, 9,
     "Por primera vez se reúnen con el rey representantes de las ciudades, además de nobles y clero.", {}),
    ("e1188b", "arte", "Pórtico de la Gloria", -8.54, 42.88, 1188, None, 11,
     "El maestro Mateo termina en Santiago un pórtico de esculturas que ya anuncia el gótico.",
     {"fuera": "año 1188"}),
    ("e1212", "batalla", "Las Navas de Tolosa", -3.55, 38.28, 1212, None, 10,
     "Los reyes cristianos vencen a los almohades. A partir de aquí, el avance hacia el sur es enorme. "
     "Mueve la barra hasta 1250 y verás la diferencia.", {}),
    ("e1218", "cultura", "Universidad de Salamanca", -5.66, 40.96, 1218, None, 9,
     "Se funda la universidad más antigua de España que sigue abierta.", {"fuera": "año 1218"}),
    ("e1229", "batalla", "Jaime I conquista Mallorca", 2.65, 39.57, 1229, None, 10,
     "El rey de Aragón cruza el mar y conquista Mallorca. La Corona de Aragón empieza a mirar al "
     "Mediterráneo.", {}),
    ("e1230", "hecho", "Castilla y León, unidos para siempre", -4.72, 41.65, 1230, None, 10,
     "Fernando III une definitivamente Castilla y León: nace la Corona de Castilla.", {}),
    ("e1236", "batalla", "Fernando III conquista Córdoba", -4.78, 37.88, 1236, None, 10,
     "La antigua capital del califato pasa a la Corona de Castilla.", {}),
    ("e1238", "batalla", "Jaime I conquista Valencia", -0.38, 39.47, 1238, None, 10,
     "La ciudad de Valencia se rinde y nace el reino de Valencia, dentro de la Corona de Aragón.", {}),
    ("e1238b", "hecho", "Nace el reino nazarí de Granada", -3.6, 37.18, 1238, None, 7,
     "Será el último reino musulmán de la Península. Durará más de 250 años.", {}),
    ("e1248", "batalla", "Fernando III conquista Sevilla", -5.99, 37.39, 1248, None, 10,
     "Con Sevilla, de Al-Ándalus solo queda el reino de Granada. Mira lo pequeño que se ha quedado el verde.", {}),
    ("e1252", "cultura", "Alfonso X el Sabio", -4.02, 39.86, 1252, 1284, 10,
     "Este rey de Castilla impulsa la Escuela de Traductores de Toledo y el castellano escrito. "
     "Cristianos, musulmanes y judíos trabajan juntos traduciendo libros.", {"fuera": "fechas del reinado"}),
    ("e1255", "arte", "Catedral de León", -5.57, 42.6, 1255, None, 11,
     "Una de las grandes catedrales góticas: casi todo son vidrieras.", {"aprox": True, "fuera": "fecha"}),
    ("e1300", "hecho", "Nacen los otomanos", 30.18, 40.02, 1300, None, 5,
     "En el noroeste de Anatolia aparece un pequeño grupo de turcos: los otomanos. "
     "Sigue su color hasta 1453.", {"aprox": True, "fuera": "fecha"}),
    ("e1337", "batalla", "Empieza la Guerra de los Cien Años", 2.35, 48.86, 1337, 1453, 12,
     "Francia e Inglaterra se pelean por tierras francesas durante más de un siglo, con treguas. "
     "Mira cómo cambia el rojo inglés dentro de Francia.", {}),
    ("e1347", "hecho", "La peste negra", 15.55, 38.19, 1347, 1351, 12,
     "Llega a Europa por los puertos del Mediterráneo y en cuatro años mata a entre un tercio y la mitad "
     "de la población. Nadie sabe qué la causa.", {"fuera": "puerto de Mesina"}),
    ("e1358", "hecho", "La Jacquerie", 2.6, 49.3, 1358, None, 12,
     "Los campesinos franceses se rebelan contra los señores, que intentan cobrarles más.", {}),
    ("e1369", "hecho", "Enrique de Trastámara, rey", -3.7, 42.34, 1369, None, 12,
     "Tras una guerra civil contra su hermanastro Pedro I, Enrique se convierte en rey de Castilla.", {}),
    ("e1378", "hecho", "Cisma de Occidente", 4.81, 43.95, 1378, 1417, 12,
     "Hay a la vez dos papas, uno en Roma y otro en Aviñón (y en algún momento tres). "
     "Mucha gente pierde la confianza en la Iglesia.", {}),
    ("e1381", "hecho", "Revuelta campesina en Inglaterra", -0.13, 51.5, 1381, None, 12,
     "Miles de campesinos marchan sobre Londres para pedir menos impuestos y más libertad.", {}),
    ("e1391", "hecho", "Ataques a las juderías", -5.99, 37.39, 1391, None, 12,
     "En muchas ciudades de Castilla y Aragón se atacan los barrios judíos.", {}),
    ("e1429", "batalla", "Juana de Arco", 1.91, 47.9, 1429, None, 12,
     "Una joven campesina anima al ejército francés a liberar Orleans. La guerra empieza a girar "
     "a favor de Francia.", {"fuera": "Orleans"}),
    ("e1436", "arte", "La cúpula de Florencia", 11.26, 43.77, 1436, None, 13,
     "Brunelleschi termina la cúpula de la catedral de Florencia. En Italia empieza el Renacimiento "
     "mientras en la Península aún existe Al-Ándalus.", {"fuera": "año 1436"}),
    ("e1450", "cultura", "La imprenta de Gutenberg", 8.27, 50.0, 1450, None, 13,
     "En Maguncia, Gutenberg inventa la imprenta de tipos móviles. Los libros se vuelven más baratos "
     "y las ideas viajan más rápido.", {"aprox": True}),
    ("e1453", "batalla", "Cae Constantinopla", 28.97, 41.01, 1453, None, 5,
     "El sultán Mehmed II conquista Constantinopla. El Imperio bizantino, que nació en el 395, desaparece. "
     "Algunos historiadores ponen aquí el fin de la Edad Media.", {}),
    ("e1469", "hecho", "Se casan Isabel y Fernando", -4.72, 41.65, 1469, None, 14,
     "Isabel de Castilla y Fernando de Aragón se casan en Valladolid. Cada reino seguirá con sus leyes, "
     "pero tendrán los mismos reyes.", {"fuera": "Valladolid"}),
    ("e1478", "hecho", "La Inquisición", -5.99, 37.39, 1478, None, 14,
     "Los Reyes Católicos crean la Inquisición para vigilar a los conversos.", {}),
    ("e1492", "batalla", "Conquista de Granada", -3.6, 37.18, 1492, None, 14,
     "El 2 de enero de 1492, Granada se rinde. Termina Al-Ándalus, después de casi ocho siglos.", {}),
    ("e1492b", "hecho", "Colón sale hacia el oeste", -6.89, 37.23, 1492, None, 14,
     "En agosto sale de Palos y el 12 de octubre llega a una isla de las Bahamas. El mapa se queda "
     "pequeño: empieza la Edad Moderna.", {"fuera": "puerto de Palos"}),
]

# Paradas: Beakman se detiene y pregunta. pista = lo que se ve al pedir ayuda.
STOPS = [
    (500, "Hace 25 años mandaba aquí un solo imperio. Cuenta: ¿cuántos reinos germánicos ves ahora en su lugar?",
     "Francos, visigodos, suevos, ostrogodos, vándalos y anglos y sajones. Seis reinos donde antes había un emperador. "
     "Y en Oriente, el Imperio bizantino sigue entero."),
    (712, "Un año después de Guadalete. ¿Quién manda en casi toda la Península? ¿Y quién manda a la vez en Constantinopla?",
     "En la Península, Al-Ándalus, que es parte del califato omeya de Damasco. En Constantinopla sigue el Imperio "
     "bizantino. Dos mundos distintos existiendo al mismo tiempo."),
    (750, "Este año cambia algo en el mundo islámico. Mira el color de Oriente: ¿qué dinastía manda ahora?",
     "Los abasíes sustituyen a los omeyas. Pronto fundarán Bagdad. Fíjate en que Al-Ándalus no se va con ellos: "
     "en el 756 se hará independiente."),
    (800, "Carlomagno acaba de ser coronado emperador. ¿Qué otros dos grandes poderes existen a la vez a su alrededor?",
     "El Imperio bizantino, con su emperador en Constantinopla, y el califato abasí, con su califa en Bagdad. "
     "Y en la Península, el emirato de Córdoba y el pequeño reino de Asturias."),
    (1000, "Córdoba está en su mejor momento. ¿Qué reinos cristianos hay en el norte de la Península en este mismo año?",
     "De oeste a este: el reino de León, el condado de Castilla, el reino de Navarra (que ahora incluye Aragón) y "
     "los condados catalanes. La frontera con Al-Ándalus va más o menos por el Duero."),
    (1100, "Busca en el mapa tres sitios donde cristianos y musulmanes son vecinos de frontera.",
     "La Península (reinos cristianos y Al-Ándalus almorávide), Oriente (Estados cruzados y reinos musulmanes) y "
     "Anatolia (bizantinos y turcos selyúcidas)."),
    (1250, "Compara con el año 1000. ¿Qué queda de Al-Ándalus? ¿Qué reinos cristianos se han repartido el resto?",
     "Solo queda el reino nazarí de Granada. El resto es de Portugal, la Corona de Castilla y la Corona de Aragón "
     "(y Navarra, al norte, sin frontera con los musulmanes)."),
    (1348, "Llega la peste negra. ¿Qué dos reinos están, además, en plena guerra?",
     "Francia e Inglaterra, en la Guerra de los Cien Años. Peste, hambre y guerra a la vez: por eso se habla de la "
     "crisis del siglo XIV."),
    (1453, "Cae Constantinopla. ¿Quién la conquista? Calcula: ¿cuántos años había resistido desde el 476?",
     "La conquistan los turcos otomanos de Mehmed II. Desde el 476 son 977 años: casi mil. Mira qué poco quedaba "
     "ya del morado bizantino."),
    (1492, "Último año del mapa. ¿Qué tres cosas de tu tema pasan en 1492?",
     "Los Reyes Católicos conquistan Granada, se expulsa a los judíos que no se convierten y Colón llega a América. "
     "Y Nebrija publica la primera gramática del castellano."),
]

ERAS = [(476, 1000, "Alta Edad Media"), (1000, 1300, "Plena Edad Media"), (1300, 1492, "Baja Edad Media")]

# Imágenes de cada acontecimiento (claves de images.json): personaje, monumento o lugar que menciona.
EVENT_IMAGES = {
    "e732": ["poitiers"], "e843": ["lotario"], "e865": ["mayrit"], "e950": ["noria"],
    "e476": ["romulo"], "e507": ["clodoveo"], "e527": ["justiniano"], "e537": ["santasofia"], "e547": ["sanvital"],
    "e554": ["spania"], "e570": ["kaaba"], "e585": ["leovigildo"], "e589": ["recaredo"], "e622": ["mezquitaprofeta"],
    "e632": ["mezquitaprofeta"], "e661": ["omeyasdamasco"], "e711": ["guadalete", "rodrigo"], "e722": ["pelayo"],
    "e750": ["abasies"], "e756": ["abderraman1"], "e762": ["casasabiduria"], "e785": ["mezquitacordoba"],
    "e800": ["carlomagno"], "e801": ["marcahispanica"], "e830": ["catedralsantiago"], "e910": ["cluny"],
    "e929": ["abderraman3"], "e936": ["medinaazahara"], "e1031": ["taifas"], "e1054": ["cisma"],
    "e1085": ["alfonso6", "c_toledo"], "e1088": ["bolonia"], "e1099": ["jerusalen1099"],
    "e1118": ["alfonso1ar", "c_zaragoza"], "e1137": ["petronila"], "e1143": ["alfonso1pt"], "e1144": ["saintdenis"],
    "e1188": ["sanisidoro"], "e1188b": ["portico"], "e1212": ["navas"], "e1218": ["salamanca_u"], "e1229": ["jaime1"],
    "e1230": ["fernando3"], "e1236": ["c_cordoba"], "e1238": ["valencia1238"], "e1238b": ["alhambra"],
    "e1248": ["giralda", "fernando3"], "e1252": ["alfonso10"], "e1255": ["catedralleon"], "e1300": ["osman"],
    "e1337": ["cienanos"], "e1347": ["peste"], "e1358": ["jacquerie"], "e1369": ["enrique2"], "e1378": ["palaciopapas"],
    "e1381": ["revuelta1381"], "e1391": ["pogromo1391"], "e1429": ["juana"], "e1436": ["santamariafiore"],
    "e1450": ["gutenberg"], "e1453": ["caidaconstantinopla", "mehmed2"], "e1469": ["reyescatolicos"],
    "e1478": ["inquisicion"], "e1492": ["tomagranada"], "e1492b": ["colon"],
}
CITY_IMAGES = {"estambul": "santasofia", "madrid": "mayrit"}   # el resto: "c_" + id
