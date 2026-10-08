"""Surfkaart rekenmodel v2 (eigenaar, 7 oktober 2026).

De code hieronder is de referentiecode uit het document "Surfkaart rekenmodel v2", letterlijk overgenomen.
Aanpassing van de rekenchat (antwoord c, 7 oktober 2026): vensterfactor krijgt een lijst vensters (0 tot 3)
en geeft het deel van de 45 graden rond de golfrichting dat binnen een venster valt.
Update van de eigenaar (8 oktober 2026): WAVE-grenzen 100 / 1000 / 3000 kJ, WIND-grenzen 5 / 15 / 25 kn.
bij twijfel geldt deze code. Niets eigens toegevoegd of weggelaten. De 27 testgevallen van het document
staan in tests/test_model.py. Alles wat de site extra nodig heeft (welke deining het krachtigst is, de
controles op de stranddata), staat in pipeline/rules/hulp.py, niet hier.
"""
# ruff: noqa
import math

MARGE = 1e-9   # twee getallen die minder verschillen gelden als gelijk (rekenafwijking)

def rond(x):
    """Afronden naar een geheel getal; precies ,5 gaat naar boven."""
    return math.floor(x + 0.5 + MARGE)

def lijn(x, punten):
    """Rechte lijnen tussen de punten; buiten het bereik de eerste of de laatste waarde."""
    if x <= punten[0][0]: return punten[0][1]
    if x >= punten[-1][0]: return punten[-1][1]
    for (x0, y0), (x1, y1) in zip(punten, punten[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

def hoek(a, b):
    """Kleinste hoek tussen twee kompasrichtingen, 0 tot 180."""
    x = abs(a - b) % 360
    return 360 - x if x > 180 else x

def vensterfactor(richting, vensters):
    """Deel van de 45 graden rond de golfrichting (22,5 links en
    rechts) dat binnen een venster valt."""
    start = richting - 22.5
    stukken = []
    for (van, tot) in vensters:
        s = (van - start) % 360
        L = (tot - van) % 360
        if L == 0 and tot != van: L = 360
        for a in (s, s - 360):
            lo, hi = max(0.0, a), min(45.0, a + L)
            if hi > lo: stukken.append((lo, hi))
    stukken.sort()
    totaal, einde = 0.0, 0.0
    for lo, hi in stukken:
        lo = max(lo, einde)
        if hi > lo:
            totaal += hi - lo
            einde = hi
    return totaal / 45.0

def bereken(kust, vensters, wind, vlaag, windrichting, deiningen,
            tij_pct=50, verval=2.4, golfdata_in_baai=False):
    # ---- hulpgetallen ----
    E, E_zee, som_e, som_et, h2 = 0.0, 0.0, 0.0, 0.0, 0.0
    for (H, periode, richting) in deiningen:
        theta = hoek(richting, kust)
        aandeel = math.cos(math.radians(theta)) if theta < 90 else 0.0
        if not golfdata_in_baai:
            aandeel *= vensterfactor(richting, vensters)
        e_zee = 1.96 * H * H * periode * periode      # kracht op zee: alleen hoogte en periode
        e = e_zee * aandeel                           # wat daarvan dit strand bereikt
        E_zee = max(E_zee, e_zee)
        E = max(E, e)
        som_e += e
        som_et += e * periode
        h2 += H * H * aandeel
    T = som_et / som_e if som_e > 0 else 0.0   # periode, gewogen met de energie per deining
    H_strand = math.sqrt(h2)
    phi = hoek(windrichting, kust)            # 0 = recht aanlandig, 180 = recht aflandig
    vlaagverschil = max(0.0, vlaag - wind)
    tijgewicht = min(1.0, 0.78 * verval / H_strand) if H_strand > 0 else 1.0
    golfslag = lijn(H_strand, [(0.1, 0), (0.5, 1)])

    # ---- gedeelde factoren ----
    f_grootte = lijn(E, [(0, 0), (200, 1), (1000, 1), (5000, 0)])
    f_vlagen  = lijn(vlaagverschil, [(5, 1), (15, .5), (25, 0)])
    tijcurve  = lijn(tij_pct, [(0, .5), (15, .75), (35, 1), (75, 1), (90, .75), (100, .5)])
    f_tij     = 1 - tijgewicht * (1 - tijcurve)

    # ---- golfsurfen ----
    van_zee  = lijn(wind, [(5, 1), (15, .5), (25, 0)])
    van_land = lijn(wind, [(15, 1), (25, .5), (35, 0)])
    s = max(0.0, min(1.0, (phi - 90) / 22.5))
    golfsurfen = {"grootte": f_grootte,
                  "periode": lijn(T, [(6, .7), (10, 1)]),
                  "wind": (1 - s) * van_zee + s * van_land,
                  "getij": f_tij}

    # ---- windsurfen op golven ----
    windsurfen_op_golven = {
        "windkracht": lijn(wind, [(12, 0), (15, .5), (18, 1), (25, 1), (35, 0)]),
        "vlagen": f_vlagen,
        "windrichting": lijn(phi, [(0, .5), (45, .8), (90, 1), (135, .8), (180, 0)]),
        "grootte": f_grootte,
        "getij": f_tij}

    # ---- windsurfen ----
    windsurfen = {
        "windkracht": lijn(wind, [(5, 0), (8, .5), (15, 1), (25, 1), (35, 0)]),
        "vlagen": f_vlagen,
        "windrichting": lijn(phi, [(0, .75), (45, 1), (90, 1), (135, .5), (180, 0)]),
        "vlak water": lijn(E, [(100, 1), (300, 0)]),
        "getij": 1 - tijgewicht * 0.25 * lijn(tij_pct, [(75, 0), (90, 1)]) * golfslag}

    # ---- stille waters ----
    stille_waters = {
        "windkracht": lijn(wind, [(5, 1), (12, 0)]),
        "vlagen": f_vlagen,
        "golfslag": lijn(H_strand, [(0.1, 1), (0.5, .5), (1.25, 0)]),
        "windrichting": 1 - (1 - lijn(phi, [(90, 1), (180, .5)])) * lijn(wind, [(0, 0), (5, 1)]),
        "getij": 1 - tijgewicht * 0.25 * lijn(tij_pct, [(15, 1), (35, 0)]) * golfslag}

    # ---- te wild: optellen, niet vermenigvuldigen ----
    winddeel = max(lijn(wind, [(15, 0), (25, .5), (35, 1)]),
                   lijn(vlaag, [(25, 0), (35, .5), (45, 1)]))
    golfdeel = lijn(E, [(300, 0), (1000, .5), (5000, 1)])

    def product(factoren):
        p = 1.0
        for f in factoren.values(): p *= f
        return 100 * p

    def level(e):
        return 1 if e < 100 else 2 if e < 1000 else 3 if e < 3000 else 4

    factoren = {"golfsurfen": golfsurfen, "windsurfen_op_golven": windsurfen_op_golven,
                "windsurfen": windsurfen, "stille_waters": stille_waters}
    ruw = {naam: product(f) for naam, f in factoren.items()}
    ruw["te_wild"] = 100 * min(1.0, winddeel + golfdeel)

    r = {
        # laag 1: WAVE = hoogte + periode
        "E_zee": rond(E_zee), "WAVE": level(E_zee),
        # laag 2: WIND = wind + vlagen
        "wind": wind, "vlaag": vlaag,
        "WIND": 4 if (wind > 25 or vlaag > 35) else 1 if wind < 5 else 2 if wind < 15 else 3,
        # laag 3: de extra's per strand
        "bereikt_pct": rond(100 * E / E_zee) if E_zee > 0 else 0,
        "E": rond(E), "WAVE_strand": level(E),
        "periode": round(T, 1), "H_strand": round(H_strand, 2),
        "windhoek": round(phi, 1), "tij_pct": tij_pct, "tijgewicht": round(tijgewicht, 2),
        # laag 4: scores en conclusie
        "ruw": ruw, "factoren": factoren, "te_wild_delen": {"winddeel": winddeel, "golfdeel": golfdeel},
    }
    for naam, waarde in ruw.items():
        r[naam] = rond(waarde)
    r["conclusie"] = conclusie(r)
    return r


VOLGORDE = ["golfsurfen", "windsurfen_op_golven", "windsurfen", "stille_waters"]
NAAM = {"golfsurfen": "golfsurfen", "windsurfen_op_golven": "windsurfen op golven",
        "windsurfen": "windsurfen", "stille_waters": "stille waters"}

def nota(uitkomst, factor, r):
    """De reden in gewone taal bij de zwakste factor van een uitkomst."""
    if factor == "grootte":    return "te weinig golf op dit strand" if r["E"] < 200 else "te grote golven"
    if factor == "periode":    return "korte, rommelige golven"
    if factor == "wind":       return "wind van zee of opzij" if r["windhoek"] < 101.25 else "te harde wind van land"
    if factor == "vlagen":     return "vlagerige wind"
    if factor == "vlak water": return "te veel golf"
    if factor == "golfslag":   return "te veel golfslag"
    if factor == "windkracht":
        if uitkomst == "stille_waters": return "te veel wind"
        ideaal_vanaf = 18 if uitkomst == "windsurfen_op_golven" else 15
        return "te weinig wind" if r["wind"] < ideaal_vanaf else "te veel wind"
    if factor == "windrichting":
        if uitkomst == "stille_waters": return "wind van land"
        return "wind recht van zee" if r["windhoek"] < 90 else "wind van land"
    if factor == "getij":
        if uitkomst == "windsurfen":    return "hoogwater met branding op het strand"
        if uitkomst == "stille_waters": return "laagwater met kans op muistromen"
        return "laagwater" if r["tij_pct"] < 50 else "hoogwater"

def conclusie(r):
    """Precies een van zes: ideaal (vier soorten), te wild, of andere met score en reden."""
    ruw, factoren = r["ruw"], r["factoren"]
    def zwakste(naam):                            # laagste factor; bij gelijke stand de eerste uit de tabel
        laagste = None
        for factor, waarde in factoren[naam].items():
            if laagste is None or waarde < factoren[naam][laagste] - MARGE:
                laagste = factor
        return laagste
    def zonder_zwakste(naam):                     # hoe dicht zit deze uitkomst erbij als haar zwakste factor wegvalt
        p = 1.0
        for factor, waarde in factoren[naam].items():
            if factor != zwakste(naam): p *= waarde
        return p
    # de beste uitkomst: hoogste score; bij gelijke stand de uitkomst die er het dichtst bij zit; daarna de volgorde
    beste = VOLGORDE[0]
    for naam in VOLGORDE[1:]:
        hoger = ruw[naam] > ruw[beste] + MARGE
        gelijk = abs(ruw[naam] - ruw[beste]) <= MARGE
        if hoger or (gelijk and zonder_zwakste(naam) > zonder_zwakste(beste) + MARGE):
            beste = naam
    score = rond(ruw[beste])
    if ruw["te_wild"] >= 50 - MARGE:
        if ruw[beste] >= 50 - MARGE:
            return "te wild; %s %d/100 alleen voor ervaren" % (NAAM[beste], score)
        return "te wild"
    if ruw[beste] >= 75 - MARGE:
        return "ideaal " + NAAM[beste]
    return "andere: %s %d/100, niet ideaal door %s" % (NAAM[beste], score, nota(beste, zwakste(beste), r))
