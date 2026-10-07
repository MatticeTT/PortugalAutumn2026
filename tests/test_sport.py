"""Sportscore: de 41 testgevallen en de voorbeelden uit het document van de eigenaar."""

import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline.sport.score import Invoer, bereken, sporten, strandfactor, tij_op

CASES = list(csv.DictReader((Path(__file__).parent / "fixtures" / "sport" / "cases.csv").open()))
TIJ = {"op": "opkomend", "af": "afgaand", "laag": "laag", "hoog": "hoog", "": None}


def invoer_van(r: dict) -> Invoer:
    luwte = (float(r["LUWTE_van"]), float(r["LUWTE_tot"])) if r["LUWTE_van"] and r["LUWTE_tot"] else None
    return Invoer(N=r["N"], K=r["K"] or None, H=r["H"], T=r["T"], GR=r["GR"], V=r["V"], G=r["G"], WR=r["WR"],
                  TIJ=TIJ[r["TIJ"]], BESTTIJ=r["BESTTIJ"] or None, DROOG=r["DROOG"] == "ja", LUWTE=luwte)


def test_41_gevallen():
    assert len(CASES) == 41


@pytest.mark.parametrize("r", CASES, ids=[f"{r['nr']} {r['omschrijving'][:30]}" for r in CASES])
def test_geval(r):
    uit = bereken(invoer_van(r))
    namen = list(sporten()["sporten"])
    if uit is None:
        assert all(r[s] == "" for s in namen)
        return
    assert {s: uit.cijfers[s] for s in namen} == {s: int(r[s]) for s in namen}
    assert uit.GOLF == pytest.approx(float(r["GOLF"]), abs=0.002)
    assert uit.RUW == pytest.approx(float(r["RUW"]), abs=0.002)
    assert uit.W == pytest.approx(float(r["W"]), abs=0.006)  # de tabel rondt W af op 2 decimalen
    assert uit.a == pytest.approx(float(r["a"]), abs=0.05)


def test_voorbeeld_shortboard():
    zee = dict(N=270, H=1.5, T=11, GR=270, WR=270)
    assert bereken(Invoer(V=18, G=22, **zee)).cijfers["short"] == 2
    assert bereken(Invoer(V=5, G=7, **zee)).cijfers["short"] == 3
    assert bereken(Invoer(V=22, G=26, **zee)).cijfers["short"] == 1
    assert bereken(Invoer(V=18, G=22, **zee)).redenen["short"] == 7


def test_voorbeeld_kitesurf():
    uit = bereken(Invoer(N=270, H=1.5, T=8, GR=315, V=20, G=26, WR=340))
    assert uit.cijfers["kite"] == 4 and uit.redenen["kite"] == 5
    assert bereken(Invoer(N=270, H=0, T=8, GR=315, V=20, G=26, WR=340)).cijfers["kite"] == 3


def test_redenen():
    # Wind van land bij kitesurf: 5, ongunstige windrichting.
    uit = bereken(Invoer(N=270, H=0.5, T=8, GR=270, V=12, G=14, WR=90))
    assert uit.cijfers["kite"] == 5 and uit.redenen["kite"] == 3
    # Droogvallen bij laag water gaat voor alles, behalve kiten op land.
    uit = bereken(Invoer(N=270, H=0.5, T=8, GR=270, V=12, G=14, WR=90, TIJ="laag", DROOG=True))
    assert uit.cijfers["sup"] == 1 and uit.redenen["sup"] == 1
    assert uit.redenen["landkite"] != 1
    # Kiten op land bij hoog water.
    uit = bereken(Invoer(N=270, H=0.5, T=8, GR=270, V=12, G=14, WR=0, TIJ="hoog"))
    assert uit.cijfers["landkite"] == 1 and uit.redenen["landkite"] == 2
    # Korte periode bij shortboard.
    uit = bereken(Invoer(N=270, H=2.5, T=5, GR=270, V=2, G=3, WR=90))
    assert uit.redenen["short"] == 8 and uit.cijfers["short"] == 2


def test_geen_reden_als_niets_verschoof():
    # Te weinig wind voor kitesurf en wind van land: de 1 komt van de wind, niet van de richting.
    uit = bereken(Invoer(N=270, H=0.5, T=8, GR=270, V=4, G=5, WR=90))
    assert uit.cijfers["kite"] == 1 and uit.redenen["kite"] == 0


def test_tij():
    ex = [[0, 50, 0], [370, 350, 1], [745, 60, 0]]
    assert tij_op(ex, 30) == "laag"
    assert tij_op(ex, 200) == "opkomend"
    assert tij_op(ex, 420) == "hoog"
    assert tij_op(ex, 600) == "afgaand"
    assert tij_op(ex, 2000) is None


def test_strandfactor():
    assert strandfactor([0.9] * 36, [])[0] == 1.0
    assert strandfactor([0.65] * 36, [])[0] == 0.6
    assert strandfactor([0.4] * 36, [])[0] == 0.3
    assert strandfactor([0.2] * 36, [])[0] == 0.1
    assert strandfactor([0.0] * 36, [])[0] == 0.0
    assert strandfactor([0.0] * 36, ["punt voor de kust ligt op land"])[0] == 1.0


TIJ_WEB = {"opkomend": "op", "afgaand": "af"}


@pytest.mark.skipif(shutil.which("node") is None, reason="geen node")
def test_fiche_rekent_hetzelfde():
    """De fiche (web/src/sportscore.ts) geeft voor de 41 gevallen dezelfde cijfers als Python."""
    namen = list(sporten()["sporten"])
    invoer = []
    for r in CASES:
        i = invoer_van(r)
        invoer.append({"N": _f(i.N), "K": _f(i.K), "H": _f(i.H), "T": _f(i.T), "GR": _f(i.GR), "V": _f(i.V),
                       "G": _f(i.G), "WR": _f(i.WR), "TIJ": TIJ_WEB.get(i.TIJ, i.TIJ), "BESTTIJ": i.BESTTIJ,
                       "DROOG": i.DROOG, "LUWTE": list(i.LUWTE) if i.LUWTE else None})
    cfg = [{"id": s, **c} for s, c in sporten()["sporten"].items()]
    cli = Path(__file__).parents[1] / "web" / "tests" / "sportscore_cli.mjs"
    out = subprocess.run(["node", str(cli)], input=json.dumps({"sporten": cfg, "invoer": invoer}),
                         capture_output=True, text=True, check=True)
    for r, web in zip(CASES, json.loads(out.stdout), strict=True):
        py = bereken(invoer_van(r))
        assert (web is None) == (py is None), r["nr"]
        if py:
            assert {s: web[s] for s in namen} == py.cijfers, r["nr"]


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None
