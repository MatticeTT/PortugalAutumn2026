"""Klimplekken: graad en slecht weer (pipeline/klim/weer.py)."""

from pipeline.klim.ophalen import plekken, soort
from pipeline.klim.weer import graad, graniet, label, per_uur, zandsteen


def test_soort():
    assert soort({"climbing": "boulder"}) == "boulderen"
    assert soort({"climbing:boulder": "yes"}) == "boulderen"
    assert soort({"climbing": "crag"}) == "muurklimmen"
    assert soort({}) == "muurklimmen"


def test_geen_klimhallen():
    e = [{"type": "node", "id": 1, "lat": 38, "lon": -9, "tags": {"sport": "climbing", "leisure": "sports_centre"}},
         {"type": "way", "id": 2, "center": {"lat": 38, "lon": -9}, "tags": {"sport": "climbing", "climbing": "crag"}}]
    assert [p["id"] for p in plekken(e)] == ["way/2"]


def test_graad():
    assert graad("5a", "7b") == "5a–7b"
    assert graad("6a", "6a") == "6a"
    assert graad(None, "7b") == "7b"
    assert graad(None, None) == "?"
    assert label({"soort": "muurklimmen", "french:min": "5a", "font:min": "6A"}) == "5a"
    assert label({"soort": "boulderen", "french:min": "5a", "font:min": "6A", "font:max": "7B"}) == "6A–7B"
    assert label({"soort": "boulderen", "french:min": "5a"}) == "?"


def test_rotssoort():
    assert zandsteen({"rots": "sandstone"}) and zandsteen({"rots": "limestone;sandstone"})
    assert graniet({"rots": "granite"}) and not graniet({"rots": "granite;limestone"}) and not graniet({})


def test_rood():
    kalk, zand = {"rots": "limestone"}, {"rots": "sandstone"}
    reeks = [0.0] * 30 + [0.4] + [0.0] * 30
    assert per_uur(kalk, reeks, 30)["rood"] == "1"          # het regent
    assert per_uur(kalk, reeks, 40)["rood"] == "0"          # kalksteen: geen rode rand na regen
    assert per_uur(zand, reeks, 40)["rood"] == "2"          # zandsteen, geregend in de 24 uur ervoor
    assert per_uur(zand, reeks, 54)["rood"] == "2"          # 24 uur na de regen: nog binnen
    assert per_uur(zand, reeks, 55)["rood"] == "0"          # 25 uur na de regen: niet meer
    assert per_uur(zand, reeks, 40)["sinds"] == 10
    assert per_uur(zand, reeks, 20)["sinds"] is None
