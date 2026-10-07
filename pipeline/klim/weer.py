"""Klimplekken: graad op de kaart en slecht weer per uur (eigenaar, 7 oktober 2026). De surfberekening
staat hier los van.

Rode rand als een van deze twee geldt:
- het regent in dat uur (neerslag boven 0 mm);
- de rotssoort is zandsteen (sandstone) en het heeft in de 24 uur ervoor geregend.
Nota's (maken de rand niet rood): "klam, minder grip" bij luchtvochtigheid boven 70%;
"rots kan nog nat zijn" als het in de 24 uur ervoor geregend heeft en de rotssoort geen graniet is.
"""

from __future__ import annotations

GEEN, REGEN, ZANDSTEEN_NAT = "0", "1", "2"


def graad(lo: str | None, hi: str | None) -> str:
    """Laagste en hoogste graad, bv. "5a–7b"; één bekend: die; geen: "?" (niets verzinnen)."""
    if lo and hi:
        return lo if lo == hi else f"{lo}–{hi}"
    return lo or hi or "?"


def label(plek: dict) -> str:
    """Muurklimmen: de Franse graad; boulderen: de Font-graad."""
    s = "french" if plek["soort"] == "muurklimmen" else "font"
    return graad(plek.get(f"{s}:min"), plek.get(f"{s}:max"))


def rotsen(plek: dict) -> list[str]:
    """climbing:rock kan meerdere waarden hebben, gescheiden door ";"."""
    return [x.strip().lower() for x in (plek.get("rots") or "").split(";") if x.strip()]


def zandsteen(plek: dict) -> bool:
    return "sandstone" in rotsen(plek)


def graniet(plek: dict) -> bool:
    """Alleen graniet als de rotssoort graniet is; onbekend of gemengd telt als geen graniet."""
    return rotsen(plek) == ["granite"]


def per_uur(plek: dict, neerslag: list[float | None], i: int) -> dict:
    """Het weer-oordeel voor uur i. `neerslag` loopt minstens 24 uur vóór i (anders: wat er is)."""
    nu = neerslag[i]
    if nu is None:
        return {"rood": "-", "regen24": None, "sinds": None}
    voor = [x for x in neerslag[max(0, i - 24):i] if x is not None]
    regen24 = any(x > 0 for x in voor)
    # Uren sinds de laatste regen: 0 als het nu regent; None als er in de hele reeks ervoor geen regen viel.
    sinds = None
    for k in range(i, -1, -1):
        if neerslag[k] is not None and neerslag[k] > 0:
            sinds = i - k
            break
    if nu > 0:
        rood = REGEN
    elif zandsteen(plek) and regen24:
        rood = ZANDSTEEN_NAT
    else:
        rood = GEEN
    return {"rood": rood, "regen24": regen24, "sinds": sinds}
