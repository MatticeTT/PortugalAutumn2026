"""De 36 tests uit "Surfkaart rekenmodel v3 – eindversie" (test 35 heeft vier delen: a tot d).
Per test: levels WAVE, WAVE strand en WIND, E op het strand, de vijf scores en de conclusie moeten exact kloppen.
"""
# ruff: noqa: E501

import pytest

from pipeline.rules.model import bereken

# nr, kust, vensters, verval, wind, vlaag, windrichting, deiningen, tij %, (stroom kn, stroom naar),
# [WAVE, WAVE strand, WIND, E, golfsurfen, windsurfen op golven, windsurfen, stille waters, te wild], conclusie
GEVALLEN = [
    ('1', 142, [(100, 200)], 2.4, 12.0, 17.0, 230.0, [(2.2, 14.0, 292.5)], 50, (0.0, 0.0), [2, 0, 1, 0, 0, 0, 100, 0, 0], 'ideaal windsurfen'),
    ('2', 142, [(100, 200)], 2.4, 10.0, 13.0, 232.0, [], 50, (0.0, 0.0), [0, 0, 1, 0, 0, 0, 100, 29, 0], 'ideaal windsurfen'),
    ('3', 142, [(100, 200)], 2.4, 8.0, 11.0, 142.0, [], 50, (0.0, 0.0), [0, 0, 1, 0, 0, 0, 75, 57, 0], 'ideaal windsurfen'),
    ('4', 142, [(100, 200)], 2.4, 18.0, 22.0, 322.0, [], 50, (0.0, 0.0), [0, 0, 2, 0, 0, 0, 0, 0, 15], 'andere: windsurfen 0/100, niet ideaal door wind van land'),
    ('5', 142, [(100, 200)], 2.4, 8.0, 11.0, 322.0, [], 50, (0.0, 0.0), [0, 0, 1, 0, 0, 0, 0, 29, 0], 'andere: stille waters 29/100, niet ideaal door wind van land'),
    ('6', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(1.2, 11.0, 160.0)], 50, (0.0, 0.0), [1, 1, 0, 325, 100, 0, 0, 4, 0], 'ideaal golfsurfen'),
    ('7', 142, [(100, 200)], 2.4, 18.0, 22.0, 322.0, [(1.2, 11.0, 160.0)], 50, (0.0, 0.0), [1, 1, 2, 325, 85, 0, 0, 0, 15], 'ideaal golfsurfen'),
    ('8', 142, [(100, 200)], 2.4, 18.0, 22.0, 152.0, [(1.2, 11.0, 160.0)], 50, (0.0, 0.0), [1, 1, 2, 325, 35, 57, 0, 0, 15], 'andere: windsurfen op golven 57/100, niet ideaal door wind recht van zee'),
    ('9', 142, [(100, 200)], 2.4, 20.0, 26.0, 230.0, [(1.5, 9.0, 190.0), (1.0, 5.0, 230.0)], 50, (0.0, 0.0), [1, 1, 2, 173, 23, 81, 30, 0, 25], 'ideaal windsurfen op golven (ervaring nodig)'),
    ('10', 142, [(100, 200)], 2.4, 16.0, 20.0, 232.0, [(1.3, 12.0, 150.0)], 50, (0.0, 0.0), [1, 1, 2, 472, 45, 67, 0, 0, 5], 'andere: windsurfen op golven 67/100, niet ideaal door te weinig wind'),
    ('11', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(0.8, 10.0, 142.0)], 50, (0.0, 0.0), [1, 1, 0, 125, 88, 0, 0, 21, 0], 'ideaal golfsurfen'),
    ('12', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(0.8, 10.0, 142.0)], 95, (0.0, 0.0), [1, 1, 0, 125, 55, 0, 0, 21, 0], 'andere: golfsurfen 55/100, niet ideaal door hoogwater'),
    ('13', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(1.2, 11.0, 160.0)], 5, (0.0, 0.0), [1, 1, 0, 325, 58, 0, 0, 3, 0], 'andere: golfsurfen 58/100, niet ideaal door laagwater'),
    ('14', 142, [(100, 200)], 2.4, 3.0, 5.0, 230.0, [(0.4, 7.0, 150.0)], 50, (0.0, 0.0), [0, 0, 0, 15, 9, 0, 0, 63, 0], 'andere: stille waters 63/100, niet ideaal door te veel golfslag'),
    ('15', 142, [(100, 200)], 2.4, 3.0, 5.0, 230.0, [(0.7, 8.0, 142.0)], 50, (0.0, 0.0), [0, 0, 0, 61, 39, 0, 0, 37, 0], 'andere: golfsurfen 39/100, niet ideaal door te weinig golf op dit strand'),
    ('16', 142, [(100, 200)], 2.4, 10.0, 14.0, 322.0, [(2.5, 13.0, 170.0)], 50, (0.0, 0.0), [2, 2, 1, 1828, 79, 0, 0, 0, 21], 'andere: golfsurfen 79/100, niet ideaal door sterke golven, ervaring nodig'),
    ('17', 142, [(100, 200)], 2.4, 20.0, 26.0, 230.0, [(1.6, 12.0, 150.0)], 50, (0.0, 0.0), [1, 1, 2, 716, 25, 94, 0, 0, 25], 'ideaal windsurfen op golven (ervaring nodig)'),
    ('18', 142, [(100, 200)], 2.4, 28.0, 36.0, 230.0, [(1.0, 6.0, 150.0)], 50, (0.0, 0.0), [0, 0, 3, 70, 0, 21, 0, 0, 65], 'te wild'),
    ('19', 142, [(100, 200)], 2.4, 20.0, 36.0, 230.0, [], 50, (0.0, 0.0), [0, 0, 3, 0, 0, 0, 23, 0, 55], 'te wild'),
    ('20', 142, [(100, 200)], 2.4, 10.0, 12.0, 232.0, [(1.2, 12.0, 205.0)], 50, (0.0, 0.0), [1, 0, 1, 72, 40, 0, 100, 14, 0], 'ideaal windsurfen'),
    ('21', 142, [(100, 200)], 2.4, 10.0, 12.0, 232.0, [(1.2, 12.0, 195.0)], 50, (0.0, 0.0), [1, 1, 1, 149, 75, 0, 75, 10, 0], 'ideaal windsurfen'),
    ('22', 142, [(100, 200)], 2.4, 4.0, 6.0, 322.0, [(0.3, 6.0, 150.0)], 5, (0.0, 0.0), [0, 0, 0, 6, 2, 0, 0, 40, 0], 'andere: stille waters 40/100, niet ideaal door wind van land'),
    ('23', 142, [(100, 200)], 2.4, 9.0, 11.0, 187.0, [(1.2, 12.0, 177.0)], 50, (0.0, 0.0), [1, 1, 1, 333, 80, 0, 0, 5, 0], 'ideaal golfsurfen'),
    ('24', 142, [(100, 200)], 2.4, 13.0, 14.0, 187.0, [(1.2, 12.0, 177.0)], 50, (0.0, 0.0), [1, 1, 1, 333, 60, 13, 0, 0, 0], 'andere: golfsurfen 60/100, niet ideaal door wind van zee of opzij'),
    ('25', 142, [(100, 200)], 2.4, 9.0, 11.0, 187.0, [(1.2, 6.0, 177.0)], 50, (0.0, 0.0), [1, 0, 1, 83, 35, 0, 100, 5, 0], 'ideaal windsurfen'),
    ('26', 142, [(100, 200)], 2.4, 7.0, 14.0, 232.0, [(1.8, 13.0, 292.5)], 10, (0.0, 0.0), [2, 0, 1, 0, 0, 0, 90, 64, 0], 'ideaal windsurfen'),
    ('27', 142, [(100, 200)], 2.4, 13.0, 14.0, 187.0, [(1.8, 14.0, 160.0)], 10, (0.0, 0.0), [2, 2, 1, 1184, 38, 8, 0, 0, 5], 'andere: golfsurfen 38/100, niet ideaal door wind van zee of opzij'),
    ('28', 142, [(100, 200)], 2.4, 13.0, 15.0, 152.0, [(1.8, 14.0, 150.0)], 31, (0.0, 0.0), [2, 2, 1, 1233, 54, 8, 0, 0, 6], 'andere: golfsurfen 54/100, niet ideaal door wind van zee of opzij'),
    ('29', 142, [(100, 200)], 2.4, 13.0, 14.0, 152.0, [(1.8, 13.0, 150.0)], 11, (0.0, 0.0), [2, 2, 1, 1063, 40, 6, 0, 0, 2], 'andere: golfsurfen 40/100, niet ideaal door wind van zee of opzij'),
    ('30', 142, [(100, 200)], 2.4, 10.0, 14.0, 322.0, [(3.5, 14.0, 150.0)], 50, (0.0, 0.0), [3, 3, 1, 4660, 8, 0, 0, 0, 92], 'te wild'),
    ('31', 142, [(100, 200)], 2.4, 22.0, 28.0, 230.0, [(2.4, 13.0, 150.0)], 50, (0.0, 0.0), [2, 2, 2, 1889, 12, 73, 0, 0, 57], 'te wild; windsurfen op golven 73/100 alleen voor ervaren'),
    ('32', 165, [(85, 160), (165, 170), (180, 200)], 2.4, 3.0, 5.0, 345.0, [(1.2, 11.0, 165.0)], 50, (0.0, 0.0), [1, 1, 0, 228, 100, 0, 0, 13, 0], 'ideaal golfsurfen'),
    ('33', 165, [], 2.4, 3.0, 5.0, 345.0, [(1.2, 11.0, 165.0)], 50, (0.0, 0.0), [1, 0, 0, 0, 0, 0, 0, 70, 0], 'andere: stille waters 70/100, niet ideaal door wind van land'),
    ('34', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(2.0, 7.0, 160.0)], 50, (0.0, 0.0), [1, 1, 0, 365, 78, 0, 0, 0, 0], 'andere: golfsurfen 78/100, niet ideaal door korte, rommelige golven'),
    ('35a', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(0.8, 10.0, 142.0)], 50, (0.0, 0.0), [1, 1, 0, 125, 88, 0, 0, 21, 0], 'ideaal golfsurfen'),
    ('35b', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(0.8, 10.0, 142.0)], 50, (2.0, 142.0), [1, 1, 0, 169, 100, 0, 0, 15, 0], 'ideaal golfsurfen'),
    ('35c', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(0.8, 10.0, 142.0)], 50, (2.0, 322.0), [1, 0, 0, 99, 74, 0, 0, 25, 0], 'andere: golfsurfen 74/100, niet ideaal door te weinig golf op dit strand'),
    ('35d', 142, [(100, 200)], 2.4, 3.0, 5.0, 322.0, [(0.8, 10.0, 142.0)], 50, (2.0, 52.0), [1, 1, 0, 125, 88, 0, 0, 21, 0], 'ideaal golfsurfen'),
    ('36', 340, [(275, 30)], 4.15, 11.1, 15.2, 273.0, [(0.98, 7.25, 346.0), (0.58, 4.25, 283.0)], 42, (0.92, 77.0), [0, 0, 1, 98, 40, 0, 100, 2, 0], 'ideaal windsurfen'),
]


@pytest.mark.parametrize("g", GEVALLEN, ids=[f"test {g[0]}" for g in GEVALLEN])
def test_v3(g):
    nr, kust, vensters, verval, wind, vlaag, richting, deiningen, tij, (kn, naar), verwacht, conclusie = g
    r = bereken(kust, vensters, wind, vlaag, richting, deiningen, tij_pct=tij, verval=verval, stroom_kn=kn, stroom_naar=naar)
    kreeg = [r[k] for k in ("WAVE", "WAVE_strand", "WIND", "E", "golfsurfen", "windsurfen_op_golven", "windsurfen", "stille_waters", "te_wild")]
    assert (kreeg, r["conclusie"]) == (verwacht, conclusie)
