"""Scoreberekening per watersport - referentie-implementatie.

Eén rekenmethode voor 17 categorieën. Alle grenswaarden staan in PARAMS.
Windsnelheden in knopen, hoogtes in meter, periodes in seconden,
hoeken in graden ten opzichte van de kijkrichting van het strand
(wind: 0 = recht aanlandig, 90 = side-shore, 180 = recht aflandig;
 golf: 0 = recht op het strand).
"""
import math

G = 9.81
GO = 60            # startwaarde voor "ga"
LOW_SIDE = 0.80    # te klein wordt beoordeeld met 80% van de berekende brekende golf
SEC_MAX = 0.30     # bijkomende factoren trekken samen hooguit 30% af
REF_WEIGHT = 75.0  # kg


# ---------- bouwstenen ----------
def breaking_height(h0, t):
    """Komar & Gaughan (1973): brekende golfhoogte uit hoogte en periode."""
    if h0 <= 0 or t <= 0:
        return 0.0
    return 0.39 * G ** 0.2 * (t * h0 * h0) ** 0.4


def trap(x, a, b, c, d):
    """0 bij a en d, 1 tussen b en c, lineair ertussen. a/b None = geen ondergrens."""
    if a is not None and x <= a:
        return 0.0
    if d is not None and x >= d:
        return 0.0
    if b is not None and x < b:
        return (x - a) / (b - a)
    if c is not None and x > c:
        return (d - x) / (d - c)
    return 1.0


def golf_sub(hb, a, b, c, d):
    """Streng aan beide kanten: te klein met de voorzichtige schatting,
    te groot met de volle berekende hoogte."""
    return min(trap(LOW_SIDE * hb, a, b, None, None), trap(hb, None, None, c, d))


def upper(x, ideal, zero):
    """1 tot 'ideal', lineair naar 0 bij 'zero'."""
    return trap(x, None, None, ideal, zero)


def piecewise(x, pts):
    """Lineaire interpolatie door punten [(x, y), ...]."""
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 > x0 else y1
    return pts[-1][1]


def surf_wind(v, angle, anchors):
    """Windkwaliteit voor golfsurfen. anchors = {0:(ideaal,nul), 90:(..), 180:(..)}."""
    if angle <= 90:
        f = angle / 90.0
        lo, hi = anchors[0], anchors[90]
    else:
        f = (angle - 90) / 90.0
        lo, hi = anchors[90], anchors[180]
    ideal = lo[0] + f * (hi[0] - lo[0])
    zero = lo[1] + f * (hi[1] - lo[1])
    return upper(v, ideal, zero)


def combine(essentials, secondary):
    """Zwakste essentiële factor bepaalt de score; de andere halen er hooguit
    een kwart af. Bijkomende factoren halen er samen hooguit SEC_MAX af."""
    vals = list(essentials.values())
    lo = min(vals)
    rest = vals[:]
    rest.remove(lo)
    mean_rest = sum(rest) / len(rest) if rest else 1.0
    core = lo * (0.75 + 0.25 * mean_rest)
    known = [v for v in secondary.values() if v is not None]
    sec = sum(known) / len(known) if known else 1.0
    return 100.0 * core * (1 - SEC_MAX * (1 - sec))


# ---------- grenswaarden ----------
# golf: [onbruikbaar onder, ideaal van, ideaal tot, onbruikbaar boven]
SURF = {
    "golfsurfen_beginner":  dict(hb=[0.35, 0.6, 1.5, 2.0], t=[3, 5, 10, 16],
                                 wind={0: (8, 18), 90: (8, 20), 180: (10, 22)}, cur=(0.5, 1.5)),
    "golfsurfen_gemiddeld": dict(hb=[0.4, 1.0, 2.0, 3.25], t=[5, 7, 17, 22],
                                 wind={0: (4, 12), 90: (6, 16), 180: (10, 25)}, cur=(0.5, 2.0)),
    "golfsurfen_ervaren":   dict(hb=[0.8, 1.8, 4.0, 6.2], t=[6, 8, 18, 24],
                                 wind={0: (3, 10), 90: (5, 15), 180: (15, 30)}, cur=(0.5, 2.5)),
    "longboard_gemiddeld":  dict(hb=[0.3, 0.6, 1.3, 2.5], t=[5, 7, 16, 20],
                                 wind={0: (5, 12), 90: (6, 14), 180: (8, 18)}, cur=(0.5, 2.0)),
    "longboard_ervaren":    dict(hb=[0.4, 0.8, 1.3, 4.0], t=[6, 8, 18, 22],
                                 wind={0: (5, 10), 90: (6, 12), 180: (8, 16)}, cur=(0.5, 2.0)),
    "shortboard_gemiddeld": dict(hb=[0.6, 1.2, 2.0, 3.25], t=[5, 7, 17, 22],
                                 wind={0: (3, 10), 90: (5, 14), 180: (12, 28)}, cur=(0.5, 2.0)),
}
SURF["shortboard_ervaren"] = dict(hb=[0.9, 1.9, 4.0, 6.2], t=[7, 9, 20, 25],
                                  wind={0: (2, 8), 90: (5, 13), 180: (15, 30)}, cur=(0.5, 2.5))
SURF_PROFILES = {}

# vlak water. wind: trapezium; hoek: punten (hoek, score); vlaag: (ideaal tot, nul bij)
# water: golfhoogte aan het strand
FLAT = {
    "windsurfen_beginner": {"leren": dict(
        wind=[3, 5, 15, 20], angle=[(0, 0.6), (20, 1), (110, 1), (130, 0.3), (140, 0)],
        gust=(5, 12), water=[None, None, 0.3, 0.8])},
    "windsurfen_gemiddeld": {"planeren": dict(
        wind=[11, 15, 25, 32], angle=[(0, 0.5), (20, 1), (110, 1), (140, 0.4), (160, 0.1), (180, 0)],
        gust=(8, 16), water=[None, None, 0.5, 1.5])},
    "windsurfen_ervaren": {
        "slalom en speed": dict(
            wind=[11, 16, 30, 38], angle=[(0, 0.3), (40, 0.8), (70, 1), (140, 1), (165, 0.5), (180, 0.3)],
            gust=(6, 14), water=[None, None, 0.2, 0.8]),
        "springen en freestyle": dict(
            wind=[14, 18, 26, 32], angle=[(0, 0.5), (30, 0.9), (70, 1), (110, 1), (140, 0.5), (180, 0.2)],
            gust=(8, 16), water=[0.1, 0.3, 0.8, 1.5]),
        "storm": dict(
            wind=[26, 30, 40, 48], angle=[(0, 0.5), (20, 1), (110, 1), (140, 0.3), (180, 0.1)],
            gust=(10, 20), water=[None, None, 0.4, 1.2]),
    },
    "kitesurfen_beginner": {"leren": dict(
        wind=[11, 14, 22, 27], angle=[(0, 0.3), (20, 1), (110, 1), (120, 0)],
        gust=(5, 10), water=[None, None, 0.5, 1.0])},
    "kitesurfen_gemiddeld": {"vrij varen": dict(
        wind=[11, 15, 26, 32], angle=[(0, 0.4), (20, 1), (110, 1), (125, 0.3), (135, 0)],
        gust=(6, 12), water=[None, None, 0.8, 1.8])},
    "kitesurfen_ervaren": {
        "hoge sprongen": dict(
            wind=[24, 28, 39, 45], angle=[(0, 0.4), (20, 1), (110, 1), (130, 0.3), (140, 0)],
            gust=(8, 15), water=[0.2, 0.5, 1.5, 2.5]),
        "freestyle": dict(
            wind=[13, 16, 22, 28], angle=[(0, 0.4), (20, 0.9), (70, 1), (110, 1), (140, 0.5), (160, 0)],
            gust=(4, 9), water=[None, None, 0.15, 0.6]),
        "springen": dict(
            wind=[16, 20, 28, 34], angle=[(0, 0.4), (20, 1), (110, 1), (130, 0.3), (140, 0)],
            gust=(6, 12), water=[None, None, 0.8, 1.8]),
    },
}

# op golven: wind, hoek, vlaag, brekende golf, periode
WAVE = {
    "windsurfen_golven_gemiddeld": dict(
        wind=[14, 18, 30, 36], angle=[(0, 0.2), (30, 1), (110, 1), (130, 0.5), (150, 0)],
        gust=(8, 16), hb=[0.3, 0.7, 1.5, 2.3], t=[3, 5, 12, 18]),
    "windsurfen_golven_ervaren": dict(
        wind=[13, 18, 40, 48], angle=[(0, 0.1), (30, 1), (140, 1), (160, 0.5), (180, 0.2)],
        gust=(10, 20), hb=[0.6, 2.0, 4.7, 6.5], t=[6, 8, 18, 24]),
    "kitesurfen_golven_gemiddeld": dict(
        wind=[12, 16, 28, 34], angle=[(0, 0.3), (30, 1), (110, 1), (120, 0.3), (130, 0)],
        gust=(6, 12), hb=[0.3, 0.7, 1.5, 2.3], t=[3, 5, 12, 18]),
    "kitesurfen_golven_ervaren": dict(
        wind=[11, 15, 35, 42], angle=[(0, 0.1), (30, 1), (140, 1), (150, 0.3), (160, 0)],
        gust=(6, 13), hb=[0.6, 2.0, 3.9, 5.5], t=[5, 7, 17, 24]),
}

CATEGORIES = (list(SURF) + list(FLAT) + list(WAVE))


# ---------- bijkomende factoren ----------
def sec_wave_angle_surf(a):
    return piecewise(abs(a), [(0, 0.8), (10, 1), (30, 1), (60, 0.7), (90, 0.5)])


def sec_wave_angle_wave(a):
    return piecewise(abs(a), [(0, 1), (20, 1), (45, 0.5), (70, 0)])


def sec_clean(share):
    """Aandeel van het hoofdgolfsysteem in de totale golfenergie."""
    return None if share is None else piecewise(share, [(0.4, 0), (0.8, 1)])


def sec_current_wind(cur, rel):
    if cur is None:
        return None
    zero = 3.0 if rel != "mee" else 2.0
    return upper(cur, 1.0, zero)


def sec_rain(mm):
    return None if mm is None else piecewise(mm, [(0.5, 1), (3, 0.5), (8, 0.2)])


def eff_wind(v, cur, rel):
    if not cur:
        return v
    return v + cur if rel == "tegen" else v - cur if rel == "mee" else v


# ---------- score ----------
def score(category, c):
    """c = condities (dict). Geeft dict met score, profiel, deelscores, veto."""
    if c.get("onweer") or c.get("donker"):
        return dict(score=0.0, veto="onweer" if c.get("onweer") else "donker", profiel=None,
                    essentieel={}, bijkomend={})
    wratio = c.get("gewicht", REF_WEIGHT) / REF_WEIGHT
    f = wratio if category.startswith("kite") else math.sqrt(wratio)
    tide = c.get("getij_match")           # None als het beste getij niet bekend is
    cur = c.get("stroming")
    rel = c.get("stroming_tov_wind", "dwars")
    best = None

    def keep(res):
        nonlocal best
        if best is None or res["score"] > best["score"]:
            best = res

    if category in SURF or category in SURF_PROFILES:
        profs = {"": SURF[category]} if category in SURF else SURF_PROFILES[category]
        hb = c["hb"] if "hb" in c else breaking_height(c["golfhoogte"], c["periode"])
        for name, p in profs.items():
            w = surf_wind(c["wind"], c["windhoek"], p["wind"])
            if "wind_min_off" in p:   # kleine holle golf vraagt stevige aflandige wind
                lo, hi = p["wind_min_off"]
                off = piecewise(c["windhoek"], [(110, 0), (150, 1)])
                w = min(w, off * trap(c["wind"], lo, hi, None, None))
            ess = dict(golf=golf_sub(hb, *p["hb"]), wind=w, periode=trap(c["periode"], *p["t"]))
            sec = dict(golfrichting=sec_wave_angle_surf(c.get("golfhoek", 20)),
                       zuiverheid=sec_clean(c.get("aandeel_hoofdgolf")),
                       stroming=None if cur is None else upper(cur, *p["cur"]),
                       getij=tide)
            keep(dict(score=combine(ess, sec), profiel=name or None, essentieel=ess,
                      bijkomend=sec, veto=None, hb=hb))
    elif category in FLAT:
        v = eff_wind(c["wind"], cur, rel)
        gust = max(0.0, c.get("vlaag", c["wind"]) - c["wind"])
        for name, p in FLAT[category].items():
            a, b, cc, d = p["wind"]
            ess = dict(wind=trap(v, a * f, b * f, cc * f, d * f),
                       windrichting=piecewise(c["windhoek"], p["angle"]),
                       vlagen=upper(gust, *p["gust"]),
                       water=trap(c.get("golf_aan_strand", 0.0), *p["water"]))
            sec = dict(stroming=sec_current_wind(cur, rel), neerslag=sec_rain(c.get("neerslag")),
                       getij=tide)
            keep(dict(score=combine(ess, sec), profiel=name, essentieel=ess, bijkomend=sec, veto=None))
    else:
        p = WAVE[category]
        v = eff_wind(c["wind"], cur, rel)
        gust = max(0.0, c.get("vlaag", c["wind"]) - c["wind"])
        hb = c["hb"] if "hb" in c else breaking_height(c["golfhoogte"], c["periode"])
        a, b, cc, d = p["wind"]
        ess = dict(wind=trap(v, a * f, b * f, cc * f, d * f),
                   windrichting=piecewise(c["windhoek"], p["angle"]),
                   vlagen=upper(gust, *p["gust"]),
                   golf=golf_sub(hb, *p["hb"]), periode=trap(c["periode"], *p["t"]))
        sec = dict(golfrichting=sec_wave_angle_wave(c.get("golfhoek", 10)),
                   stroming=sec_current_wind(cur, rel), neerslag=sec_rain(c.get("neerslag")),
                   getij=tide)
        keep(dict(score=combine(ess, sec), profiel=None, essentieel=ess, bijkomend=sec,
                  veto=None, hb=hb))
    best["score"] = round(best["score"], 1)
    return best


# ---------- categorie 18: stille waters ----------
STIL = dict(wind=(8, 15), water=(0.3, 0.8), cur=(0.5, 1.5), off_wind=(5, 10))
STORM_WIND, STORM_GUST = 41, 48      # 9 Beaufort; achtergrond zwart


def is_storm(c):
    return c["wind"] >= STORM_WIND or c.get("vlaag", 0) >= STORM_GUST


def stille_waters(c):
    """Zwemmen, snorkelen, duiken, sup, e-foil: weinig wind, kleine golf, weinig stroming."""
    if c.get("onweer") or c.get("donker"):
        return dict(score=0.0, veto="onweer" if c.get("onweer") else "donker", essentieel={}, bijkomend={})
    w = upper(c["wind"], *STIL["wind"])
    if c.get("windhoek", 0) >= 120:          # aflandig: strenger, je drijft af
        w = min(w, upper(c["wind"], *STIL["off_wind"]))
    hb = c["hb"] if "hb" in c else breaking_height(c.get("golfhoogte", 0.0), c.get("periode", 0.0))
    ess = dict(wind=w, water=upper(max(c.get("golf_aan_strand", 0.0), hb), *STIL["water"]))
    cur = c.get("stroming")
    sec = dict(stroming=None if cur is None else upper(cur, *STIL["cur"]), neerslag=sec_rain(c.get("neerslag")))
    return dict(score=round(combine(ess, sec), 1), veto=None, essentieel=ess, bijkomend=sec)


def waarschuwingen(category, c):
    """Gevaren die de score niet veranderen maar die de app moet tonen."""
    out = []
    t = c.get("watertemperatuur")
    if t is not None and t < 8:
        out.append("water onder 8 graden: wedstrijden gaan dan niet door")
    elif t is not None and t < 15:
        out.append("water onder 15 graden: kans op koudeshock, wetsuit nodig")
    u = c.get("uur_tot_donker")
    if u is not None and u < 1:
        out.append("minder dan een uur tot donker")
    hoek = c.get("windhoek", 0)
    wind_cat = category in FLAT or category in WAVE
    if wind_cat and hoek >= 110:
        out.append("wind van land: je drijft naar zee bij pech")
    if category.startswith("kite") and hoek <= 20:
        out.append("recht aanlandige wind: blijf 80 m van de kust en van obstakels")
    if category.startswith("kite"):
        out.append("houd drie lijnlengtes vrij benedenwinds")
    if category in SURF and c.get("stroming") is not None and c["stroming"] >= 1.0:
        out.append("sterke stroming")
    return out


# ---------- algemene score: cirkel 0-4 met rand ----------
LEVEL = {"beginner": 0, "gemiddeld": 1, "ervaren": 2}
RAND = ["groen", "oranje", "rood"]
GOLF = [k for k in CATEGORIES if k.split("_")[0] in ("golfsurfen", "longboard", "shortboard")]
WIND = [k for k in CATEGORIES if k not in GOLF]


def cijfer(score100):
    return min(4, int(score100 // 20))


def te_veel(cats, c):
    """True als er te veel golf of te veel wind is voor elke categorie in de lijst.
    Golf: brekende golf boven de bovenkant van 'ideaal' van de hoogste categorie.
    Wind: wind boven de bovenkant van 'ideaal' van de hoogste categorie.
    Zo ziet de app het verschil tussen 'niets' en 'te gevaarlijk'."""
    if c.get("onweer") or c.get("donker"):
        return False
    surf = [k for k in cats if k in SURF]
    if surf:
        hb = c["hb"] if "hb" in c else breaking_height(c["golfhoogte"], c["periode"])
        return hb > max(SURF[k]["hb"][2] for k in surf)
    wratio = c.get("gewicht", REF_WEIGHT) / REF_WEIGHT
    grens = 0.0
    for k in cats:
        f = wratio if k.startswith("kite") else math.sqrt(wratio)
        profs = FLAT[k].values() if k in FLAT else [WAVE[k]]
        grens = max(grens, max(p["wind"][2] * f for p in profs))
    return c["wind"] > grens


def algemeen(groep, c, niveau=None):
    """groep = GOLF of WIND. niveau = None, 'beginner', 'gemiddeld' of 'ervaren'.
    Geeft cijfer 0-4, rand en de scores per categorie."""
    cats = [k for k in groep if niveau is None or k.endswith(niveau)]
    scores = {k: score(k, c)["score"] for k in cats}
    beste = max(scores, key=scores.get)
    n = cijfer(scores[beste])
    rand = None
    if n >= 3:
        laagste = min(LEVEL[k.rsplit("_", 1)[1]] for k, v in scores.items() if v >= GO)
        rand = RAND[laagste]
    return dict(cijfer=n, rand=rand, beste=beste, scores=scores,
                te_veel=n < 3 and te_veel(cats, c))


BETEKENIS = ["niets", "iets", "potentieel", "zekerheid", "ideaal"]


def strand_uur(c, niveau=None):
    """Alles wat de app voor één strand en één uur nodig heeft."""
    g, w = algemeen(GOLF, c, niveau), algemeen(WIND, c, niveau)
    st = stille_waters(c)
    return dict(golf=g, wind=w, stille_waters=dict(st, cijfer=cijfer(st["score"])),
                storm=is_storm(c), te_gevaarlijk=is_storm(c) or g["te_veel"] or w["te_veel"], onweer=bool(c.get("onweer")), donker=bool(c.get("donker")),
                waarschuwingen={k: waarschuwingen(k, c) for k in CATEGORIES})
