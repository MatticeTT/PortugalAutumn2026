"""Invoer voor de score (pipeline/site/invoer.py)."""
import random

from pipeline.rules import score as S
from pipeline.site import invoer as I


def test_groep_gelijk_aan_algemeen():
    rnd = random.Random(3)
    for _ in range(1500):
        c = dict(wind=rnd.uniform(0, 45), windhoek=rnd.uniform(0, 180), golfhoogte=rnd.uniform(0, 5),
                 periode=rnd.uniform(2, 20), golfhoek=rnd.uniform(0, 90), golf_aan_strand=rnd.uniform(0, 3))
        c["vlaag"] = c["wind"] + rnd.uniform(0, 15)
        u = I.uur(c)
        for n in I.NIVEAUS:
            g, w = u[n]
            assert g == S.algemeen(S.GOLF, c, n)
            assert w == S.algemeen(S.WIND, c, n)
        assert u["stil"] == S.stille_waters(c)["score"]


def test_stroom_tov_wind():
    # wind uit het westen (270): waait naar het oosten. Stroom naar het westen = tegen de wind in.
    assert I.tov_wind(270, 270) == "tegen"
    assert I.tov_wind(90, 270) == "mee"
    assert I.tov_wind(0, 270) == "dwars"
    assert I.tov_wind(300, 270) == "tegen"


def test_hoofdgolf_en_aandeel():
    # kust 270 (kijkt naar het westen), venster 180-360; deining recht uit het westen en een kleine uit het zuiden
    c = I.condities(270, [(180, 360)], 38.7, -9.4, 29_000_000, 10, 12, 90, [(2.0, 12, 270), (0.5, 5, 225)],
                    None, None, 0.0, 1)
    assert c["periode"] == 12 and c["golfhoek"] == 0
    assert abs(c["golfhoogte"] - 2.0) < 1e-9
    assert 0.9 < c["aandeel_hoofdgolf"] < 1
    assert c["windhoek"] == 180  # wind uit het oosten: recht aflandig
    assert "stroming" not in c


def test_tekens():
    assert I.teken({"cijfer": 4, "rand": "rood", "te_veel": False}) == "R"
    assert I.teken({"cijfer": 3, "rand": "groen", "te_veel": False}) == "g"
    assert I.teken({"cijfer": 0, "rand": None, "te_veel": True}) == "a"
    assert I.teken({"cijfer": 2, "rand": None, "te_veel": False}) == "2"
    assert I.stil_teken(4, True) == "W" and I.stil_teken(2, False) == "2"
