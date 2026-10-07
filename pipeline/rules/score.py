"""M5: WIND, WAVE en het label voor één strand en één uur (PLAN.md 2.4 tot 2.6).

Een pure functie: geen netwerk, geen bestanden behalve rules.yaml. Het getij is geen
invoer en verandert dus nooit een score (PLAN.md 2.7).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

RULES_FILE = Path(__file__).with_name("rules.yaml")
G = 9.81


@cache
def rules(path: Path = RULES_FILE) -> dict:
    return yaml.safe_load(path.read_text())


@dataclass
class Uur:
    wind_kn: float
    vlagen_kn: float
    windrichting: float                       # waar de wind vandaan komt, graden
    deelgolven: list[tuple[float, float, float]]  # (hoogte m, periode s, richting graden)
    golfhoogte_totaal: float | None = None    # Hs van het model; het deel dat de deelgolven missen telt als windgolf
    golfperiode_totaal: float | None = None
    golfrichting_totaal: float | None = None
    ipma_zeegang: str = "green"               # green, yellow, orange, red


@dataclass
class Strand:
    kijkrichting: float
    blootstelling: list[float] = field(default_factory=lambda: [1.0] * 36)  # f per 10 graden
    richting_onzeker: bool = False
    besloten_water: bool = False


@dataclass
class Score:
    wind: int
    wave: int
    label: str
    waarschuwing: str | None
    redenen: list[str]
    notas: list[str]
    wind_oorzaak: str | None      # "sterkte", "vlagen", "aflandig" of None
    windklasse: str | None
    hb: float
    hb_bereik: tuple[float, float]
    windsurf: str | None
    let_op: bool = False          # WIND 2 met aflandige wind: te licht om te kiten, verkeerde richting ("2!")


def fmt(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def angdiff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def wind_class(wind_from: float, facing: float) -> str:
    r = rules()["wind"]["richting"]
    a = angdiff(wind_from, facing)
    if a < r["aanlandig"]:
        return "aanlandig"
    if a < r["schuin_aan"]:
        return "schuin_aan"
    if a < r["zij"]:
        return "zij"
    if a < r["schuin_af"]:
        return "schuin_af"
    return "af"


KLASSE_TEKST = {"aanlandig": "aanlandig", "schuin_aan": "schuin aanlandig", "zij": "zijwind",
                "schuin_af": "schuin aflandig", "af": "aflandig"}


def exposure(f36: list[float], direction: float) -> float:
    """f voor een golfrichting, lineair tussen de waarden om de 10 graden."""
    x = (direction % 360) / 10
    i = int(math.floor(x)) % 36
    j = (i + 1) % 36
    t = x - math.floor(x)
    return f36[i] * (1 - t) + f36[j] * t


def parts_with_rest(u: Uur) -> list[tuple[float, float, float]]:
    """De deelgolven, plus het stuk dat ze samen tekortkomen tegenover de totale hoogte.

    Dat stuk telt als windgolf (OPEN.md punt 10, gekozen op 6 oktober 2026).
    """
    parts = [(h, t, d) for h, t, d in u.deelgolven if h and t]
    if u.golfhoogte_totaal and rules()["wave"].get("restdeel_als_windgolf"):
        rest = u.golfhoogte_totaal ** 2 - sum(h * h for h, _, _ in parts)
        if rest > 1e-6:
            ww = [p for p in u.deelgolven[2:3] if p[0] and p[1]]
            t = ww[0][1] if ww else (u.golfperiode_totaal or 0)
            d = ww[0][2] if ww else (u.golfrichting_totaal or 0)
            if t:
                parts.append((math.sqrt(rest), t, d))
    return parts


def breaking_height(parts, f36: list[float]) -> float:
    """Hb = k · 0,39 · g^0,2 · (som van f² · H² · T)^0,4 (Komar en Gaughan, PLAN.md 2.5)."""
    k = rules()["wave"]["k"]
    flux = sum(exposure(f36, d) ** 2 * h * h * t for h, t, d in parts)
    return k * 0.39 * G ** 0.2 * flux ** 0.4 if flux > 0 else 0.0


def kite_strength(w: float) -> int:
    r = rules()["wind"]
    th = r["kite"]
    s5 = r["voorzichtig"]["s5"] if r["voorzichtig"].get("aan") else th["s5"]
    if w >= s5:
        return 5
    if w >= th["s4"]:
        return 4
    if w >= th["s3"]:
        return 3
    if w >= th["s2"]:
        return 2
    return 1


def windsurf_text(w: float) -> str | None:
    for r in rules()["wind"]["windsurf_regels"]:
        if r["van"] <= round(w) <= r["tot"]:
            return r["tekst"]
    return None


def score(u: Uur, s: Strand, **_ignored) -> Score:
    R = rules()
    notas: list[str] = []

    # --- WIND ---------------------------------------------------------------
    w = u.wind_kn
    wind = kite_strength(w)
    cause = "sterkte" if wind == 5 else None
    vl = R["wind"]["vlagen"]
    gust_s5 = R["wind"]["voorzichtig"]["vlagen_s5"] if R["wind"]["voorzichtig"].get("aan") else vl["s5"]
    if u.vlagen_kn >= gust_s5 and wind < 5:
        wind, cause = 5, "vlagen"
    elif u.vlagen_kn > vl["min4"] and wind < 4:
        wind = 4
    if vl.get("nota_aan") and w > 0 and u.vlagen_kn > w * vl["nota_factor"]:
        notas.append("vlagerig")

    klasse = None if s.richting_onzeker else wind_class(u.windrichting, s.kijkrichting)
    let_op = False
    af = R["wind"]["aflandig"]
    if klasse is None:
        notas.append("richting niet beoordeeld")
    elif klasse in af["klassen"]:
        if w >= af["vanaf_kn"] and not s.besloten_water and wind < 5:
            wind, cause = af["score"], "aflandig"
        notas.append("aflandige wind: niet voor kite, windsurf of sup" if w >= af["vanaf_kn"]
                     else "aflandig: blijf dicht bij de kant")
        if s.besloten_water:
            notas.append("besloten water: aflandige wind telt niet als gevaar")
        let_op = wind == 2 and not s.besloten_water
    elif klasse == "aanlandig":
        notas.append("recht aanlandig, weinig ruimte, voor kite alleen met ervaring")
    else:
        notas.append("ideale richting")

    # --- WAVE ---------------------------------------------------------------
    parts = parts_with_rest(u)
    hb = breaking_height(parts, s.blootstelling)
    th = R["wave"]["hb"]
    s5 = R["wave"]["s5_alternatief"]["waarde"] if R["wave"]["s5_alternatief"].get("aan") else th["s5"]
    wave = 5 if hb >= s5 else 4 if hb >= th["s4"] else 3 if hb >= th["s3"] else 2 if hb >= th["s2"] else 1
    levels = ["green", "yellow", "orange", "red"]
    ipma = R["wave"]["ipma_zeegang"]
    ipma_hit = levels.index(u.ipma_zeegang) >= levels.index(ipma["vanaf"])
    if ipma_hit:
        wave = ipma["score"]
    main = max(parts, key=lambda p: p[0], default=None)
    period = main[1] if main else 0.0
    per = R["wave"]["periode"]
    if period and period < per["max2_onder_s"] and wave < 5:
        wave = min(wave, 2)
    if period >= per["nota_vanaf_s"]:
        notas.append("lange deining: lange pauzes tussen de sets, sterkere stroming")
    if wave == 4 and hb < R["wave"]["beginnersles_tot"]:
        notas.append("les voor beginners kan nog (grens Surfing England)")
    if klasse in ("schuin_af", "af"):
        notas.append("golven schoon (aflandige wind)")
    elif klasse in ("aanlandig", "schuin_aan") and w >= af["vanaf_kn"]:
        notas.append("golven rommelig (aanlandige wind)")

    # --- label (eerste regel die past, PLAN.md 2.6) ---------------------------
    sw = R["surf_wind"]
    warn = None
    if wave == 5:
        label = "Gevaarlijke zee"
    elif wind == 5 and cause in ("sterkte", "vlagen"):
        label = "Gevaarlijk: storm"
    elif wind == 5 and cause == "aflandig" and wave == 3 and w <= sw["beginner_max_kn"]:
        label, warn = "Surfdag voor beginners", "aflandige wind: niet voor kite, windsurf of sup"
    elif wind == 5 and cause == "aflandig" and wave == 4 and w <= sw["gevorderd_max_kn"]:
        label, warn = "Surfdag voor gevorderden", "aflandige wind: niet voor kite, windsurf of sup"
    elif wind == 5 and cause == "aflandig":
        label = "Aflandige wind: gevaarlijk voor kite, windsurf en sup"
    elif wind in (3, 4) and wave in (3, 4):
        label = "Winddag met golven (gevorderd)"
    elif wind == 4:
        label = "Winddag voor gevorderden"
    elif wind == 3:
        label = "Winddag voor beginners"
    elif wave == 4:
        label = "Surfdag voor gevorderden"
    elif wave == 3:
        label = "Surfdag voor beginners"
    else:
        label = "Stille dag (sup, kayak, wakeboard)"
        st = R["stil"]
        if w <= st["sup_goed_tot_kn"] and not let_op:
            notas.append("goed voor sup en kajak")
        elif w < R["wind"]["kite"]["s3"]:
            notas.append("randgeval voor sup")

    if let_op and warn is None:
        warn = "aflandige wind: niet voor kite, windsurf of sup"

    # --- redenen in woorden ---------------------------------------------------
    rw = f"WIND {wind}: {round(w)} kn"
    if klasse:
        rw += f", {KLASSE_TEKST[klasse]}"
    if cause == "vlagen":
        rw += f", vlagen {round(u.vlagen_kn)} kn"
    elif u.vlagen_kn > vl["min4"]:
        rw += f", vlagen {round(u.vlagen_kn)} kn"
    rv = f"WAVE {wave}: {fmt(hb)} m brekend"
    if period:
        rv += f", {round(period)} s"
    if ipma_hit:
        rv += f", IPMA-waarschuwing zeegang ({u.ipma_zeegang})"
    b = R["wave"]["bereik"]
    return Score(wind=wind, wave=wave, label=label, waarschuwing=warn, redenen=[rw, rv], notas=notas,
                 wind_oorzaak=cause, windklasse=klasse, hb=round(hb, 2),
                 hb_bereik=(round(hb * b["laag"], 1), round(hb * b["hoog"], 1)), windsurf=windsurf_text(w),
                 let_op=let_op)
