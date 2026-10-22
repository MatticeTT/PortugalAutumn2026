"""Referentie-implementatie van de plankscore (surf-app), in één bestand.
Leest regels.json (alle getallen) en een testset; rekent strand en score opnieuw uit.
Gebruik: python3 referentie.py testset_100.json   (of testset_1000.json)
Dit is de specificatie: een eigen implementatie moet dezelfde scores geven (max verschil 0,01).
Versie 2026-10-22d: zie LEESMIJ (wat veranderde).
"""
import math, json, sys, os

G = 9.81
HIER = os.path.dirname(os.path.abspath(__file__))
REGELS = json.load(open(os.path.join(HIER, "regels.json")))
PL = list(REGELS["planken"])
KEYS = ["a", "b", "c", "d", "hol", "holw", "kp", "kw", "ko", "kr", "ks"]


def X(k, veld):
    return REGELS["planken"][k][veld]["waarde"]


def vorm_uit_tekst(t):
    """Spotvorm (tekst of klasse) -> Iribarren-equivalent; klassen staan in regels.json > spot_vorm."""
    t = (t or "").lower()
    sv = REGELS["spot_vorm"]
    if t in sv and isinstance(sv[t], (int, float)):
        return sv[t]
    if "niet extreem hol" in t: return sv["steil_niet_extreem"]
    if "ondiep" in t: return sv["ondiep"]
    if "extreem" in t or "zeer zwaar" in t: return sv["extreem"]
    if "zwaar" in t: return sv["zwaar"]
    if "vol" in t or "dik" in t: return sv["vol"]
    if "zacht" in t: return sv["zacht"]
    if "hol" in t: return sv["hol"]
    return sv["wall"]


def hb_kg(H, T, hoek):
    if hoek is None or abs(hoek) >= 90 or H <= 0:
        return 0.0
    H0 = H * math.sqrt(math.cos(math.radians(hoek)))
    return 0.39 * G ** 0.2 * (T * H0 ** 2) ** 0.4




def piekperiode(tm01):
    """De regel verwacht de PIEKperiode Tp per systeem (wat surfers en surfrapporten bedoelen).
    Golfmodellen (Copernicus IBI en NW-shelf: VTM01_WW, VTM01_SW1, VTM01_SW2) geven per systeem
    een gemiddelde periode Tm01. Omrekenen met de JONSWAP-verhouding uit regels.json."""
    return tm01 / REGELS["fysica"]["periode"]["tm01_gedeeld_door_tp"]["waarde"]


def getij_stand(h, laag, hoog):
    """Waterstand h tegenover laag- en hoogwater van die getijcyclus (zelfde nulpunt), als getal 0..1."""
    if hoog - laag < 0.05: return 0.5
    return min(1.0, max(0.0, (h - laag) / (hoog - laag)))


def getij_bakje(h, laag, hoog):
    """ALLEEN voor tekst en voor de vlaggen 'ondiep bij laagwater' / 'vol bij hoogwater':
    onderste derde = laag, middelste derde = half, bovenste derde = hoog. De tijfactor rekent met getij_stand()."""
    if hoog - laag < 0.05: return "half"
    x = (h - laag) / (hoog - laag)
    G = REGELS["tijvenster"]["bakjes"]
    return "laag" if x < G["laag_tot"]["waarde"] else ("hoog" if x > G["hoog_vanaf"]["waarde"] else "half")


def bereken(s):
    sy = {n: dict(H=H, T=T, hoek=a, Hb=hb_kg(H, T, a)) for n, H, T, a in s["sys"]}
    beslis = max(sy, key=lambda n: sy[n]["Hb"]) if sy else None
    b = sy[beslis] if beslis else dict(H=0, T=0, hoek=0, Hb=0)
    Hb, T = b["Hb"], b["T"]
    c = math.sqrt(G * Hb / 0.78) if Hb > 0 else 0
    tanb = s["spot"].get("tanb")
    xi = tanb * T / math.sqrt(2 * math.pi * Hb / G) if (tanb and Hb > 0) else None
    kn, rel, stoot = s["wind"]
    loodrecht = kn * math.cos(math.radians(rel))  # + = offshore
    r = loodrecht * 0.5144 / c if c else 0
    deining = [v["Hb"] for n, v in sy.items() if n.startswith("deining")]
    ww = sy.get("windzee", {}).get("Hb", 0)
    M = None if ww == 0 else ((ww / max(deining)) if deining and max(deining) > 0 else float("inf"))
    kruis = sy["deining2"]["Hb"] / sy["deining1"]["Hb"] if ("deining2" in sy and sy["deining1"]["Hb"] > 0) else None
    V = 0
    is_point = "point" in s["spot"].get("vorm", "").lower()
    if Hb > 0 and abs(b["hoek"]) < 90 and s["spot"].get("tanb") is not None and "point" not in s["spot"].get("vorm", "").lower():  # Komar: alleen zandstranden. Op een point is de schuine deining net wat hem laat werken; de stroom langs de point zit in 'stroom' (spotkennis of model)
        c0 = G * T / (2 * math.pi)
        tb = math.asin(min(1, math.sin(math.radians(abs(b["hoek"]))) * c / c0))
        V = 1.17 * math.sqrt(G * Hb) * math.sin(tb) * math.cos(tb)
    elif Hb > 0 and is_point:
        # Point: de golf pelt langs de wall onder een vrij vaste hoek (bepaald door de bodem, niet door de deining).
        # Komar met die vaste breekhoek; minder als de deining bijna recht op de point staat (dan pelt hij niet).
        PS = REGELS["richting"]["point"]
        ab = math.radians(PS["breekhoek_stroming"]["waarde"])
        V = 1.17 * math.sqrt(G * Hb) * math.sin(ab) * math.cos(ab) * smooth(abs(b["hoek"]) / PS["vanaf"]["waarde"])
    Vt = V * s.get("langs_factor", 1.0) + s.get("stroom", 0.0)
    # op een point rijd je met de stroming mee en peddel je terug via de geul: in de score telt ze maar deels
    Vs = Vt if not is_point else V * s.get("langs_factor", 1.0) * REGELS["richting"]["point"]["stroming_gewicht"]["waarde"] + s.get("stroom", 0.0)
    P = 0.49 * b["H"] ** 2 * T
    return dict(hoek=b["hoek"], Hb=Hb, T=T, xi=xi, r=r, M=M, kruis=kruis, V=V, Vt=Vt, Vs=Vs, P=P, beslis=beslis, kn=kn, rel=rel, stoot=stoot, ww=ww)




def smooth(t):
    t = min(1.0, max(0.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)




def trap(x, a, b, c, d):
    """1 tussen b en c; daarbuiten een geleidelijke afname (geen klif). Breedte van de flank = (b-a)/2 en (d-c)/2."""
    if x < b:
        return 1.0 / (1.0 + ((b - x) / ((b - a) / 2)) ** 2)
    if x <= c:
        return 1.0
    return 1.0 / (1.0 + ((x - c) / ((d - c) / 2)) ** 2)




def kenmerken(s, x):
    """x = uitkomst van bereken(s) uit bouw100."""
    kn, rel, st = s["wind"]
    c = math.cos(math.radians(rel))
    on = max(0.0, -c) * kn
    off = max(0.0, c) * kn
    zij = abs(math.sin(math.radians(rel))) * kn
    tanb = s["spot"].get("tanb")
    xi = x["xi"] if x["xi"] is not None else vorm_uit_tekst(s["spot"].get("vorm", ""))
    fl = set(s.get("flags", []))
    if "point" in s["spot"].get("vorm", "").lower() or s.get("groep") == "Point break":
        fl.add("point")
    M = x["M"]
    if M == float("inf"):  # alleen windzee: rommelig als de wind nog op zee staat, anders vooral kort en zwak
        M = 1.2 if on >= 6 else 0.35
    M = 0.0 if M is None else min(M, 1.5)
    kr = x["kruis"] or 0.0
    rif = tanb is None and "point" not in fl  # rif en big-wave rif: geen helling, geen point
    return dict(vorm_txt=(s["spot"].get("vorm") or "").lower(), hoek=abs(x["hoek"]), hoek_signed=x["hoek"], rel=rel, venster=s["spot"].get("deining_venster"), zand=bool(tanb) and "point" not in fl,
                Hb=x["Hb"], T=x["T"], xi=xi, steil=bool(tanb and xi >= 1.0), steil_strand=bool(tanb and tanb >= 0.07 and xi < 1.0), P=x["P"], on=on, off=off, zij=zij,
                kn=kn, stoot=st or kn, open=s.get("open", False), M=M, kruis=kr, Vt=x["Vt"], Vs=x["Vs"], flags=fl, rif=rif,
                getij=s.get("getij"), stand=s.get("getij_stand"), werkt_bij_tij=s["spot"].get("werkt_bij_tij"), bereik=s.get("getij_bereik_m"))




def chop_richting(rel):
    """Deel van de wind dat chop maakt, volgens de richting (0 = offshore, 90 = zij, 180 = onshore).
    Wind van het land heeft geen stuk water vlak bij de kust om chop op te bouwen."""
    W = REGELS["fysica"]["wind_richting"]
    zij, nul = W["zij"]["waarde"], W["geen_chop_tot_graden"]["waarde"]
    rel = abs(rel) % 360
    if rel > 180: rel = 360 - rel
    if rel >= 90: return zij + (1.0 - zij) * smooth((rel - 90) / 90)
    return zij * smooth((rel - nul) / (90 - nul))


def richtingfactoren(f):
    """Deiningsrichting per spottype. Point: schuine deining nodig om rond de kaap te buigen.
    Zandbank: geen richtingsfactor (dichtklappen hangt vooral af van de vorm van de bank: vaste vlag 'closeout').
    Spotveld deining_venster [min, max] (graden t.o.v. loodrecht): buiten het venster schaduw."""
    RI = REGELS["richting"]; a = f["hoek"]; F = {}
    v = f.get("venster")
    if v:
        lo, hi = min(v), max(v); x = f["hoek_signed"]
        d = max(lo - x, x - hi, 0.0)
        if d > 0: F["deiningsrichting"] = 1.0 / (1.0 + (d / RI["venster_breedte"]["waarde"]) ** 2)
    elif "point" in f["flags"]:
        P = RI["point"]; b, c, w = P["vanaf"]["waarde"], P["tot"]["waarde"], P["breedte"]["waarde"]; lo = P["recht"]["waarde"]
        if f["hoek_signed"] < 0:  # van de baaikant: de point ligt in zijn eigen schaduw
            F["deiningsrichting"] = lo / (1.0 + (a / RI["venster_breedte"]["waarde"]) ** 2)
        elif a < b: F["deiningsrichting"] = lo + (1 - lo) * smooth(a / b)
        elif a > c: F["deiningsrichting"] = 1.0 / (1.0 + ((a - c) / w) ** 2)
    return F


def expert_label(f):
    """Apart label naast de score (verandert de score niet): golven die alleen voor ervaren surfers zijn."""
    E = REGELS["expert_label"]; red = []
    if f["Hb"] >= E["groot_m"]["waarde"]: red.append("grote golven")
    if not f.get("zand") and f["xi"] >= E["hol_xi"]["waarde"] and f["Hb"] >= E["hol_m"]["waarde"]: red.append("holle golf over rif of rotsen")
    if f["steil"] and f["Hb"] >= E["shorebreak_m"]["waarde"]: red.append("zware shorebreak")
    if "ondiep" in f.get("vorm_txt", "") and f["Hb"] >= E["ondiep_m"]["waarde"]: red.append("ondiep rif of rotsen")
    if f["Vt"] >= E["stroming_ms"]["waarde"]: red.append("sterke stroming")
    return red


TIJ = ["laag", "half", "hoog"]


def tijfactor(f):
    """Tijvenster met de waterstand zelf (geen bakjes, dus geen sprong van uur tot uur).
    stand = (waterstand - laagwater) / (hoogwater - laagwater) van die cyclus, 0..1.
    Elk woord uit het spotveld 'werkt bij tij' is een stuk van die stand (regels.json > tijvenster > stukken).
    dh = meter water dat de stand nu buiten het venster ligt; tegenover de breekdiepte (Hb / 0,78)."""
    w = f.get("werkt_bij_tij")
    if not w or f["flags"] & {"vol", "ondiep"}: return None
    x = f.get("stand")
    if x is None:
        if f.get("getij") not in TIJ: return None
        x = REGELS["tijvenster"]["stand_uit_woord"][f["getij"]]
    TV = REGELS["tijvenster"]
    buiten = min(max(TV["stukken"][t][0] - x, x - TV["stukken"][t][1], 0.0) for t in w)
    if buiten <= 0: return 1.0
    bereik = f.get("bereik") or TV["standaard_bereik_m"]["waarde"]
    dh = buiten * bereik
    hb = max(f["Hb"], 0.3) / TV["breekverhouding"]["waarde"]
    return 1.0 / (1.0 + (dh / hb / TV["r0"]["waarde"]) ** 2)


def factoren(f, p, k):
    """Alle factoren voor plank k, als dict naam -> waarde 0..1."""
    H = f["Hb"]
    F = {}
    F["hoogte"] = trap(H, p["a"], p["b"], p["c"], p["d"])
    xi = f["xi"]
    # te hol
    v = 1.0 if xi <= p["hol"] else 1.0 / (1.0 + ((xi - p["hol"]) / p["holw"]) ** 2)
    # te zacht (alleen planken die steilte nodig hebben)
    zm = X(k, "zacht_min")
    if xi < zm:
        v *= max(0.25, (xi / zm) ** 1.3)
    if f["steil"] or xi > 2.0:
        v *= REGELS["planken"][k].get("shorebreak", {"waarde": 0.15})["waarde"]
    F["vorm"] = v
    if f.get("steil_strand"):  # steil strand, golf klapt over maar stort niet in: zware, korte tubes
        F["steil strand"] = X(k, "steil_strand")
    F["kracht"] = 1.0 / (1.0 + (p["kp"] / max(f["P"], 0.05)) ** 2)
    T = f["T"]
    T0 = X(k, "periode_T0")  # grote planken hebben lange, krachtige deining nodig
    F["periode"] = 1.0 if T >= T0 else 1.0 / (1.0 + ((T0 - T) / 3.0) ** 2)
    if "point" in f["flags"]:  # lange wall: lengte en trim winnen, korte brede plank minder
        F["point"] = X(k, "point")
    # heel vlak: breekt ver uit en meerdere keren, lange peddel, golf verliest kracht
    F["breed"] = 1.0 if xi >= 0.16 else 0.55 + 0.45 * smooth((xi - 0.06) / 0.10)
    # Wind die chop maakt (onshore + 0,8 x zijwind), gewogen naar golfhoogte.
    # Kleine golf: verwaait sneller (gewicht > 1). Grote golf op een strand of point: wat minder last,
    # maar nooit minder dan de ondergrens. Rif en big wave: geen korting; onshore maakt de drop
    # onvoorspelbaar en weegt zwaarder naarmate de golf groter is.
    W = REGELS["fysica"]["wind_gewicht"]
    g = math.sqrt(W["ref_m"] / max(H, 0.3))
    if f.get("rif"):
        RF = W["rif_factor"]
        zwaar = 1.0 if f["xi"] >= RF["vorm_vanaf_xi"] else smooth((H - RF["vanaf_m"]) / (RF["vol_vanaf_m"] - RF["vanaf_m"]))
        g = max(1.0, g) * (1.0 + (RF["waarde"] - 1.0) * zwaar)
    else:
        g = max(W["ondergrens"], g)
    C = f["kn"] * chop_richting(f["rel"]) * g
    F["wind"] = 1.0 / (1.0 + (C / p["kw"]) ** 3)
    # offshore te sterk tegenover de golfsnelheid c = wortel(g*diepte bij breken)
    c = math.sqrt(9.81 * max(H, 0.2) / 0.78)
    r_off = f["off"] * 0.5144 / c
    F["offshore"] = 1.0 if r_off <= 1.2 else 1.0 / (1.0 + ((r_off - 1.2) / (p["ko"] / 7.0)) ** 2)
    F["inpeddelen"] = 1.0 if f["off"] <= 18 else 1.0 / (1.0 + ((f["off"] - 18) / X(k, "inpeddel_breedte")) ** 2)
    # Windstoten: geleidelijk (geen klif). Volle straf vanaf 'tot_kn' verschil tussen stoot en wind.
    ST = REGELS["fysica"]["windstoten"]
    d = f["stoot"] - f["kn"]
    F["stoten"] = 1.0 - (1.0 - ST["factor"]) * smooth((d - ST["vanaf_kn"]) / (ST["tot_kn"] - ST["vanaf_kn"]))
    RI = REGELS["richting"]
    kd = RI["zand"]["kruis_vanaf"]["waarde"] if f.get("zand") else 0.3
    R = f["M"] + 1.0 * max(f["kruis"] - kd, 0.0)
    for naam, v in richtingfactoren(f).items():
        F[naam] = v
    F["rommel"] = 1.0 / (1.0 + (R / p["kr"]) ** 2)
    dv = max(f["Vs"] - 0.25, 0.0)
    F["stroming"] = max(0.3, 1.0 / (1.0 + (dv / p["ks"]) ** 2))
    if "terugslag" in f["flags"]:
        F["terugslag"] = X(k, "terugslag")
    if "vol" in f["flags"]:
        F["vol"] = X(k, "vol")
    # Tijvenster uit spotkennis: werkt de spot bij dit tij? De vlaggen 'vol' en 'ondiep' gaan voor.
    tv = tijfactor(f)
    if tv is not None:
        F["tij"] = tv
    return F




def score(f, P, alfa):
    """Geeft per plank (score, factoren, harde grens of None)."""
    uit = {}
    fl = f["flags"]
    for k in PL:
        F = factoren(f, P[k], k)
        prod = 1.0
        for v in F.values():
            prod *= v
        s = 1 + 4 * prod ** alfa
        grens = None
        if fl & {"bliksem", "donker", "riool", "zwemzone", "ondiep", "uitstroom"} or f["kn"] >= 30:
            s, grens = 1.0, "veiligheid"
        elif f["Hb"] < 0.05:
            s, grens = 1.0, "geen golf"
        else:
            diep = f.get("steil_strand")  # steil strand met overklappende golf: diep water dicht bij de kust (Puerto-type)
            gmax = REGELS["planken"][k].get("open_strand_gun_max")
            if f.get("open") and not diep and gmax and s > gmax["waarde"]:
                s, grens = gmax["waarde"], "open strand gun"
            if f.get("open") and f["Hb"] > 2.5 and f["xi"] < 0.3:
                cap = 2.0
                if s > cap:
                    s, grens = cap, "open strand schuim"
            if f.get("open") and not diep and f["Hb"] > 3.0:
                cap = X(k, "open_strand_max")
                if s > cap:
                    s, grens = cap, "open strand"
            if "closeout" in fl:
                cap = X(k, "closeout_max")
                if s > cap:
                    s, grens = cap, "close-out"
            if "mist" in fl and s > 2.0:
                s, grens = 2.0, "mist"
            if "pier" in fl:
                cap = X(k, "pier_max")
                if s > cap:
                    s, grens = cap, "pier"
            if s > 4.4 and f["Hb"] < X(k, "klein_onder") and not ("point" in fl and f["T"] >= 13):
                s, grens = 4.4, "klein"
            tw = REGELS["planken"][k].get("tow_in_boven_m")
            if tw and f["Hb"] > tw["waarde"] and s > X(k, "tow_in_max"):
                s, grens = X(k, "tow_in_max"), "tow-in"
        uit[k] = (round(s, 2), F, grens)
    return uit




def rnd(x):
    return int(math.floor(x + 0.5))




def situatie(r):
    """Testset-rij -> dict zoals bereken() en kenmerken() die verwachten."""
    w = r["ruw"]
    return dict(spot=w["spot"], sys=[tuple(t) for t in w["systemen"]], wind=tuple(w["wind"]), stroom=w["stroom"],
                langs_factor=w["langs_factor"], flags=w["vlaggen"], open=w["open"], groep=r.get("groep", ""),
                getij=w.get("getij"), getij_stand=w.get("getij_stand"), getij_bereik_m=w.get("getij_bereik_m"))


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))["situaties"]
    P = {k: {q: X(k, q) for q in KEYS} for k in PL}
    alfa = REGELS["score"]["alfa"]["waarde"]
    mx, n, lab = 0.0, 0, 0
    for r in data:
        s = situatie(r)
        f = kenmerken(s, bereken(s))
        uit = score(f, P, alfa)
        for k in PL:
            d = abs(uit[k][0] - r["regel"][k]); mx = max(mx, d); n += 1
        if "expert" in r and expert_label(f) != r["expert"]: lab += 1
    print(f"{len(data)} situaties, {n} scores, grootste verschil met verwacht: {mx:.3f}; expertlabel anders: {lab}")
