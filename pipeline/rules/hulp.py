"""Wat de site naast het rekenmodel nodig heeft. Geen eigen rekenregels: alles gebruikt de functies
van pipeline/rules/model.py.

- krachtigste: welke deining op zee de grootste E_zee heeft (die toont het WAVE-vlak).
- aandeel: het aandeel van een deining uit een richting, zoals model.bereken het rekent.
- controle: de controles op de stranddata uit het document (deel "Controles op de stranddata").
"""

from __future__ import annotations

import math

from pipeline.rules.model import hoek, vensterfactor

KOMPAS = ["N", "NNO", "NO", "ONO", "O", "OZO", "ZO", "ZZO", "Z", "ZZW", "ZW", "WZW", "W", "WNW", "NW", "NNW"]


def krachtigste(deiningen: list[tuple[float, float, float]]) -> int | None:
    """Index van de deining met de grootste 1,96 × hoogte² × periode² (E_zee), of None zonder deining."""
    best, idx = 0.0, None
    for k, (h, t, _r) in enumerate(deiningen):
        e = 1.96 * h * h * t * t
        if e > best:
            best, idx = e, k
    return idx


def aandeel(richting: float, kust: float, vensters: list, golfdata_in_baai: bool = False) -> float:
    """Zelfde berekening als in model.bereken: cos θ (0 vanaf 90°) × vensterfactor."""
    theta = hoek(richting, kust)
    a = math.cos(math.radians(theta)) if theta < 90 else 0.0
    if not golfdata_in_baai:
        a *= vensterfactor(richting, vensters)
    return a


def binnen(richting: float, vensters: list) -> bool:
    return any(((richting - van) % 360) <= ((tot - van) % 360) for van, tot in vensters)


def controle(kust: float, vensters: list[list[float]]) -> dict:
    """De controles op één strand (het model rekent altijd; dit is wat nagekeken moet worden).

    Volgens het document kan een kaap een aanlandige richting echt afschermen: dit zijn geen zekere fouten.
    """
    uit: dict = {"blokkerend": [], "nakijken": []}
    v = [tuple(x) for x in vensters]
    if not v:
        uit["nakijken"].append("geen swell-venster: deining van zee bereikt dit strand niet")
    elif not binnen(kust, v):
        uit["nakijken"].append("kustrichting ligt buiten het venster")
    # Een deining uit een richting waarvan de wind recht of schuin aanlandig heet (φ < 67,5°)
    # moet een aandeel boven 0 hebben.
    if v:
        nul = [r for r in range(360) if hoek(r, kust) < 67.5 and aandeel(r, kust, v) <= 0]
        if nul:
            uit["nakijken"].append(f"aandeel 0 bij aanlandige richtingen: {_reeksen(nul)}")
    uit["aandeel16"] = [round(aandeel(k * 22.5, kust, v), 2) for k in range(16)]
    return uit


def _reeksen(graden: list[int]) -> str:
    """[100, 101, 102, 200] -> "100–102°, 200°"."""
    out, start = [], graden[0]
    for a, b in zip(graden, graden[1:] + [None], strict=True):
        if b != a + 1:
            out.append(f"{start}°" if start == a else f"{start}–{a}°")
            start = b
    return ", ".join(out)
