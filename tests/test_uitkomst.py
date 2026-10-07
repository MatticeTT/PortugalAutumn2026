"""De testgevallen van de rekenchat (7 oktober 2026), exact zoals opgegeven.

Meia Praia: kustrichting 142°, swell-venster 100–200°, verval 2,4 m, tij 50% tenzij vermeld.
"""

import pytest

from pipeline.rules.uitkomst import (
    GEEN,
    GOLFSURF,
    STIL,
    TE_WILD,
    WINDGOLF,
    WINDSURF,
    Deining,
    Strand,
    Uur,
    bereken,
    getoond,
)

MEIA = Strand(kust=142, venster=[[100, 200]])


def uur(wind, vlaag=None, uit=0, golven=(), tij=50):
    return Uur(wind=wind, vlaag=wind if vlaag is None else vlaag, windrichting=uit,
               deiningen=[Deining(*g) for g in golven], tij=tij, verval=2.4)


GOLF_WNW = [(2.2, 14, 292.5)]
GOLF_160 = [(1.2, 11, 160)]

GEVALLEN = [
    # (omschrijving, uur, verwachte uitkomst)
    ("1 wind 12 uit 230, golf uit WNW", uur(12, 17, 230, GOLF_WNW), WINDSURF),
    ("2 wind 8 aanlandig, golf uit WNW", uur(8, 11, 142, GOLF_WNW), WINDSURF),
    ("3 wind 8 aflandig, golf uit WNW", uur(8, 11, 322, GOLF_WNW), STIL),
    # Oorspronkelijk "te wild"; die regel is geschrapt (eigenaar, 7 okt): valt alles af, dan niets.
    ("4 wind 18 aflandig, golf uit WNW", uur(18, 22, 322, GOLF_WNW), GEEN),
    ("5 wind 3, 1,2 m 11 s uit 160", uur(3, 3, 0, GOLF_160), GOLFSURF),
    ("6 zelfde golf, wind 18 aflandig", uur(18, 22, 322, GOLF_160), GOLFSURF),
    ("7 zelfde golf, wind 18 aanlandig", uur(18, 22, 142, GOLF_160), WINDGOLF),
    ("8 wind 20 uit 230, 1,5 m 9 s uit 190", uur(20, 26, 230, [(1.5, 9, 190)]), WINDGOLF),
    ("9 wind 13 uit 230, 1,1 m 10 s uit 142", uur(13, 17, 230, [(1.1, 10, 142)]), GOLFSURF),
    ("10 zelfde, tij 10%", uur(13, 17, 230, [(1.1, 10, 142)], tij=10), WINDSURF),
    ("11 wind 3, 0,8 m 10 s uit 142", uur(3, 3, 0, [(0.8, 10, 142)]), GOLFSURF),
    ("12 zelfde, tij 95%", uur(3, 3, 0, [(0.8, 10, 142)], tij=95), STIL),
    ("13 wind 3, 0,7 m 8 s uit 142", uur(3, 3, 0, [(0.7, 8, 142)]), STIL),
    ("14 wind 10, 2,5 m 13 s uit 170", uur(10, 10, 322, [(2.5, 13, 170)]), TE_WILD),
    ("15 wind 28, vlaag 36", uur(28, 36, 225, [(1, 6, 150)]), TE_WILD),
]


@pytest.mark.parametrize("naam,u,verwacht", GEVALLEN, ids=[g[0] for g in GEVALLEN])
def test_geval(naam, u, verwacht):
    assert bereken(u, MEIA).uitkomst == verwacht


def test_strafpunten_uit_de_voorbeelden():
    assert bereken(uur(12, 17, 230, GOLF_WNW), MEIA).punten[WINDSURF] == 0
    r = bereken(uur(8, 11, 142, GOLF_WNW), MEIA)
    assert r.punten[WINDSURF] == 1 and r.punten[STIL] == 1
    assert bereken(uur(8, 11, 322, GOLF_WNW), MEIA).punten[STIL] == 2
    r = bereken(uur(13, 17, 230, [(1.1, 10, 142)], tij=10), MEIA)
    assert (r.punten[GOLFSURF], r.punten[WINDGOLF], r.punten[WINDSURF]) == (2, 2, 1)


def test_energie_uit_de_voorbeelden():
    assert bereken(uur(3, 3, 0, GOLF_160), MEIA).E == pytest.approx(325, abs=1)
    assert bereken(uur(20, 26, 230, [(1.5, 9, 190)]), MEIA).E == pytest.approx(239, abs=1)
    assert bereken(uur(3, 3, 0, [(0.8, 10, 142)]), MEIA).E == pytest.approx(125, abs=1)
    assert bereken(uur(3, 3, 0, [(0.7, 8, 142)]), MEIA).E == pytest.approx(61, abs=1)


@pytest.mark.parametrize("wind,vlaag,wild",
                         [(25.0, 25.0, False), (25.1, 25.1, True), (20, 35.0, False), (20, 35.1, True)])
def test_grenzen_te_wild(wind, vlaag, wild):
    assert (bereken(uur(wind, vlaag, 230), MEIA).uitkomst == TE_WILD) == wild


def test_grens_E_1000_is_te_wild():
    # 1,96 × H² × T² = 1000 bij H·T = √(1000/1,96), recht binnen
    ht = (1000 / 1.96) ** 0.5
    assert bereken(uur(3, 3, 0, [(1.0, ht + 1e-9, 142)]), MEIA).uitkomst == TE_WILD


def test_grens_wind_15_van_zee_laat_golfsurfen_afvallen():
    assert bereken(uur(15.0, 15.0, 142, GOLF_160), MEIA).punten[GOLFSURF] is None
    assert bereken(uur(14.9, 14.9, 142, GOLF_160), MEIA).punten[GOLFSURF] is not None


def test_grens_wind_12_geen_strafpunt_bij_windsurfen():
    assert bereken(uur(12.0, 12.0, 230), MEIA).punten[WINDSURF] == 0


def test_levels():
    r = bereken(uur(12, 17, 230, GOLF_160), MEIA)
    assert (r.wave, r.wind) == (3, 3)
    assert bereken(uur(4.9, 4.9, 230), MEIA).wind == 1
    assert bereken(uur(22, 36, 230), MEIA).wind == 4


def test_getoond_alleen_bij_0_of_1_strafpunt():
    assert getoond(bereken(uur(3, 3, 0, GOLF_160), MEIA)) == GOLFSURF          # 0 strafpunten
    assert getoond(bereken(uur(8, 11, 322, GOLF_WNW), MEIA)) is None           # stil met 2 strafpunten
    assert getoond(bereken(uur(28, 36, 225), MEIA)) == TE_WILD                 # te wild altijd


def test_alles_valt_af_is_niets():
    r = bereken(uur(18, 22, 322, GOLF_WNW), MEIA)
    assert r.uitkomst == GEEN and getoond(r) is None
