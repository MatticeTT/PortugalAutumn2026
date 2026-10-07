"""Klimgraden: uniform schrijven en omrekenen (eigenaar, 7 oktober 2026).

- Routes en sportklimgebieden: Franse schaal in kleine letters (6a+). Boulders: Font in hoofdletters (6A+).
  De twee worden nooit gemengd.
- "6a/6a+" of "6a-6c" wordt een bereik (laagste, hoogste).
- Andere schalen (UIAA, YDS, V) worden omgerekend met een vaste tabel en gemarkeerd als "omgerekend".

Omrekentabel: Wikipedia, "Grade (climbing)", Comparison tables (bronnen daar: RockFax Grade Tables 2021,
theCrag 2023), opgehaald op 7 oktober 2026. Alleen rijen waar de tabel één Franse of Font-graad geeft;
rijen zonder eenduidige waarde staan er niet in (dan: graad onbekend).
"""

from __future__ import annotations

import re

FRANS = re.compile(r"^[1-9][abc]?\+?$")
FONT = re.compile(r"^[1-9][ABC]?\+?$")

# Vrij klimmen: YDS en UIAA naar Frans.
YDS_FRANS = {
    "5.1": "2", "5.3": "3", "5.4": "4a", "5.5": "4b", "5.6": "4c", "5.7": "5a", "5.8": "5b", "5.9": "5c",
    "5.10a": "6a", "5.10b": "6a+", "5.10c": "6b", "5.10d": "6b+", "5.11a": "6c", "5.11b": "6c+",
    "5.11d": "7a", "5.12a": "7a+", "5.12b": "7b", "5.12c": "7b+", "5.12d": "7c", "5.13a": "7c+",
    "5.13b": "8a", "5.13c": "8a+", "5.13d": "8b", "5.14a": "8b+", "5.14b": "8c", "5.14c": "8c+",
    "5.14d": "9a", "5.15a": "9a+", "5.15b": "9b", "5.15c": "9b+", "5.15d": "9c",
}
UIAA_FRANS = {
    "I": "1", "II": "2", "III": "3", "IV": "4a", "V": "4c", "V+": "5a", "VI-": "5b", "VI": "5c",
    "VI+": "6a", "VII-": "6a+", "VII": "6b", "VII+": "6b+", "VIII-": "6c+", "VIII": "7a", "VIII+": "7a+",
    "IX-": "7b+", "IX": "7c", "IX+": "7c+", "X-": "8a", "X": "8b", "X+": "8b+", "XI-": "8c", "XI": "8c+",
    "XI+": "9a", "XII-": "9a+", "XII": "9b+", "XII+": "9c",
}
# Boulderen: V naar Font.
V_FONT = {
    "V0": "4", "V0+": "4+", "V1": "5", "V2": "5+", "V3": "6A", "V4": "6B", "V5": "6C", "V6": "7A",
    "V7": "7A+", "V8": "7B", "V9": "7C", "V10": "7C+", "V11": "8A", "V12": "8A+", "V13": "8B",
    "V14": "8B+", "V15": "8C", "V16": "8C+", "V17": "9A", "V18": "9A+",
}
ROMEINS = re.compile(r"^(XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)[+-]?$")


def _stukken(waarde: str | None) -> list[str]:
    """ "6a/6a+" en "6a-6c" -> ["6a", "6a+"]; spaties weg; "−" als min."""
    if not waarde:
        return []
    w = waarde.strip().replace(" ", "").replace("−", "-").replace("–", "/")
    # Een min-teken na een graad (UIAA "VI-") is geen scheiding; "6a-6c" wel.
    delen = re.split(r"/|;|(?<=[0-9abcABC+])-(?=[0-9])", w)
    return [d for d in delen if d]


def romeins(g: str) -> bool:
    return bool(ROMEINS.match(g))


def frans(waarde: str | None) -> tuple[list[str], bool] | None:
    """Franse graad(en) uit een veld voor routes: (graden, omgerekend) of None als het niet te lezen is.
    Een Romeins cijfer in het Franse veld (zo schrijven Portugese topo's de lage graden) blijft zoals in de
    bron: het is geen UIAA en wordt dus niet omgerekend."""
    uit = []
    for d in _stukken(waarde):
        if FRANS.match(d.lower()):
            uit.append(d.lower())
        elif ROMEINS.match(d.upper()):
            uit.append(d.upper())
        else:
            return None
    return (uit, False) if uit else None


def font(waarde: str | None) -> tuple[list[str], bool] | None:
    uit = []
    for d in _stukken(waarde):
        if FONT.match(d.upper()):
            uit.append(d.upper())
        else:
            return None
    return (uit, False) if uit else None


def uiaa(waarde: str | None):
    uit = []
    for d in _stukken(waarde):
        if d.upper() not in UIAA_FRANS:
            return None
        uit.append(UIAA_FRANS[d.upper()])
    return (uit, True) if uit else None


def yds(waarde: str | None):
    uit = []
    for d in _stukken(waarde):
        if d.lower() not in YDS_FRANS:
            return None
        uit.append(YDS_FRANS[d.lower()])
    return (uit, True) if uit else None


def vschaal(waarde: str | None):
    uit = []
    for d in _stukken(waarde):
        if d.upper() not in V_FONT:
            return None
        uit.append(V_FONT[d.upper()])
    return (uit, True) if uit else None


def rang(g: str) -> float:
    """Volgorde van een graad (Frans of Font): 6a < 6a+ < 6b ... ; voor filteren en min/max."""
    g = g.lower()
    n = int(g[0])
    letter = {"": 0, "a": 0, "b": 1, "c": 2}[g[1] if len(g) > 1 and g[1] in "abc" else ""]
    return n * 6 + letter * 2 + (1 if g.endswith("+") else 0)


def bereik(graden: list[str]) -> tuple[str, str]:
    """Laagste en hoogste. Met een Romeins cijfer erbij is de volgorde niet zeker: dan zoals gegeven."""
    if any(romeins(g) for g in graden):
        return graden[0], graden[-1]
    s = sorted(graden, key=rang)
    return s[0], s[-1]


def tekst(lo: str | None, hi: str | None) -> str:
    if lo and hi:
        return lo if lo == hi else f"{lo} – {hi}"
    return lo or hi or "graad onbekend"


def vscale_alias():
    """climbing:grade:hueco is in OpenStreetMap de V-schaal."""
    return vschaal
