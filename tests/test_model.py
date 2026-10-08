"""De testgevallen uit "Surfkaart rekenmodel v2", exact zoals in het document, met de update van 8 oktober 2026
(WAVE 2 in plaats van 3 bij test 6, 7, 8, 9, 10, 13, 17, 20, 21, 23 en 24; nieuwe tests 32 en 33).
Ook test 1, 16, 26 en 27 krijgen WAVE 3 in plaats van 4: dat volgt uit de nieuwe grenzen (E_zee 1859, 2070, 1073 en
1245 kJ, tussen 1000 en 3000), maar stond niet in de update. Gemeld aan de eigenaar; scores en conclusies blijven gelijk.

Meia Praia: kust 142°, venster 100–200°, verval 2,4 m, golfdata_in_baai nee.
Per geval: nr, wind, vlaag, windrichting, deiningen (hoogte, periode, richting), tij_pct,
WAVE, bereikt %, E, golfsurfen, windsurfen op golven, windsurfen, stille waters, te wild, conclusie.
"""
# ruff: noqa: E501

import pytest

from pipeline.rules.model import bereken, vensterfactor

GEVALLEN = [
    (1, 12.0, 17.0, 230.0, [(2.2, 14.0, 292.5)], 50, 3, 0, 0, 0, 0, 79, 0, 0, 'ideaal windsurfen'),
    (2, 10.0, 13.0, 232.0, [], 50, 1, 0, 0, 0, 0, 64, 29, 0, 'andere: windsurfen 64/100, niet ideaal door te weinig wind'),
    (3, 8.0, 11.0, 142.0, [], 50, 1, 0, 0, 0, 0, 38, 57, 0, 'andere: stille waters 57/100, niet ideaal door te veel wind'),
    (4, 18.0, 22.0, 322.0, [], 50, 1, 0, 0, 0, 0, 0, 0, 15, 'andere: windsurfen 0/100, niet ideaal door wind van land'),
    (5, 8.0, 11.0, 322.0, [], 50, 1, 0, 0, 0, 0, 0, 29, 0, 'andere: stille waters 29/100, niet ideaal door wind van land'),
    (6, 3.0, 5.0, 322.0, [(1.2, 11.0, 160.0)], 50, 2, 95, 325, 100, 0, 0, 4, 2, 'ideaal golfsurfen'),
    (7, 18.0, 22.0, 322.0, [(1.2, 11.0, 160.0)], 50, 2, 95, 325, 85, 0, 0, 0, 17, 'ideaal golfsurfen'),
    (8, 18.0, 22.0, 152.0, [(1.2, 11.0, 160.0)], 50, 2, 95, 325, 35, 57, 0, 0, 17, 'andere: windsurfen op golven 57/100, niet ideaal door wind recht van zee'),
    (9, 20.0, 26.0, 230.0, [(1.5, 9.0, 190.0), (1.0, 5.0, 230.0)], 50, 2, 48, 173, 20, 81, 61, 0, 25, 'ideaal windsurfen op golven'),
    (10, 16.0, 20.0, 232.0, [(1.3, 12.0, 150.0)], 50, 2, 99, 472, 45, 67, 0, 0, 17, 'andere: windsurfen op golven 67/100, niet ideaal door te weinig wind'),
    (11, 3.0, 5.0, 322.0, [(0.8, 10.0, 142.0)], 50, 2, 100, 125, 63, 0, 0, 21, 0, 'andere: golfsurfen 63/100, niet ideaal door te weinig golf op dit strand'),
    (12, 3.0, 5.0, 322.0, [(0.8, 10.0, 142.0)], 95, 2, 100, 125, 39, 0, 0, 21, 0, 'andere: golfsurfen 39/100, niet ideaal door hoogwater'),
    (13, 3.0, 5.0, 322.0, [(1.2, 11.0, 160.0)], 5, 2, 95, 325, 58, 0, 0, 3, 2, 'andere: golfsurfen 58/100, niet ideaal door laagwater'),
    (14, 3.0, 5.0, 230.0, [(0.4, 7.0, 150.0)], 50, 1, 99, 15, 6, 0, 0, 63, 0, 'andere: stille waters 63/100, niet ideaal door te veel golfslag'),
    (15, 3.0, 5.0, 230.0, [(0.7, 8.0, 142.0)], 50, 1, 100, 61, 26, 0, 0, 37, 0, 'andere: stille waters 37/100, niet ideaal door te veel golfslag'),
    (16, 10.0, 14.0, 322.0, [(2.5, 13.0, 170.0)], 50, 3, 88, 1828, 79, 0, 0, 0, 60, 'te wild; golfsurfen 79/100 alleen voor ervaren'),
    (17, 20.0, 26.0, 230.0, [(1.6, 12.0, 150.0)], 50, 2, 99, 716, 25, 94, 0, 0, 55, 'te wild; windsurfen op golven 94/100 alleen voor ervaren'),
    (18, 28.0, 36.0, 230.0, [(1.0, 6.0, 150.0)], 50, 1, 99, 70, 0, 21, 60, 0, 65, 'te wild; windsurfen 60/100 alleen voor ervaren'),
    (19, 20.0, 36.0, 230.0, [], 50, 1, 0, 0, 0, 0, 45, 0, 55, 'te wild'),
    (20, 10.0, 12.0, 232.0, [(1.2, 12.0, 205.0)], 50, 2, 18, 72, 27, 0, 64, 14, 0, 'andere: windsurfen 64/100, niet ideaal door te weinig wind'),
    (21, 10.0, 12.0, 232.0, [(1.2, 12.0, 195.0)], 50, 2, 37, 149, 56, 0, 48, 10, 0, 'andere: golfsurfen 56/100, niet ideaal door te weinig golf op dit strand'),
    (22, 4.0, 6.0, 322.0, [(0.3, 6.0, 150.0)], 5, 1, 99, 6, 1, 0, 0, 40, 0, 'andere: stille waters 40/100, niet ideaal door wind van land'),
    (23, 9.0, 11.0, 187.0, [(1.2, 12.0, 177.0)], 50, 2, 82, 333, 80, 0, 0, 5, 2, 'ideaal golfsurfen'),
    (24, 13.0, 14.0, 187.0, [(1.2, 12.0, 177.0)], 50, 2, 82, 333, 60, 13, 0, 0, 2, 'andere: golfsurfen 60/100, niet ideaal door wind van zee of opzij'),
    (25, 9.0, 11.0, 187.0, [(1.2, 6.0, 177.0)], 50, 2, 82, 83, 23, 0, 57, 5, 0, 'andere: windsurfen 57/100, niet ideaal door te weinig wind'),
    (26, 7.0, 14.0, 232.0, [(1.8, 13.0, 292.5)], 10, 3, 0, 0, 0, 0, 30, 64, 0, 'andere: stille waters 64/100, niet ideaal door te veel wind'),
    (27, 13.0, 14.0, 187.0, [(1.8, 14.0, 160.0)], 10, 3, 95, 1184, 38, 8, 0, 0, 52, 'te wild'),
]


@pytest.mark.parametrize("g", GEVALLEN, ids=[f"geval {g[0]}" for g in GEVALLEN])
def test_geval(g):
    nr, wind, vlaag, richting, deiningen, tij, WAVE, bereikt, E, G, WG, W, S, TW, conclusie = g
    r = bereken(142, [(100, 200)], wind, vlaag, richting, deiningen, tij_pct=tij, verval=2.4)
    assert (r["WAVE"], r["bereikt_pct"], r["E"]) == (WAVE, bereikt, E)
    assert (r["golfsurfen"], r["windsurfen_op_golven"], r["windsurfen"], r["stille_waters"], r["te_wild"]) == \
        (G, WG, W, S, TW)
    assert r["conclusie"] == conclusie


# Controle van de rekenchat bij de nieuwe vensterfactor (vensters 85–160, 165–170, 180–200).
REBOLINHOS = [(85, 160), (165, 170), (180, 200)]


@pytest.mark.parametrize("richting,factor", [(120, 1.00), (150, 0.83), (165, 0.67), (190, 0.50), (210, 0.28), (60, 0.00)])
def test_vensterfactor_meerdere_vensters(richting, factor):
    assert round(vensterfactor(richting, REBOLINHOS), 2) == factor


def test_vensterfactor_geen_venster():
    assert vensterfactor(150, []) == 0.0


# Nieuwe tests van 8 oktober 2026: kust 165°, wind 3/5 kn uit 345°, deining 1,2 m 11 s uit 165°, tij 50.
@pytest.mark.parametrize("vensters,WAVE,bereikt,E,score,conclusie", [
    ([(85, 160), (165, 170), (180, 200)], 2, 67, 228, ("golfsurfen", 100), "ideaal golfsurfen"),
    ([], None, 0, 0, ("stille_waters", 70), "andere: stille waters 70/100, niet ideaal door wind van land"),
], ids=["test 32", "test 33"])
def test_32_33(vensters, WAVE, bereikt, E, score, conclusie):
    r = bereken(165, vensters, 3, 5, 345, [(1.2, 11, 165)], tij_pct=50, verval=2.4)
    if WAVE is not None:
        assert r["WAVE"] == WAVE
    assert (r["bereikt_pct"], r["E"], r[score[0]], r["conclusie"]) == (bereikt, E, score[1], conclusie)
