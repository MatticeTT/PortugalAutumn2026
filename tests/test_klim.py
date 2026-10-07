"""Klimplekken: graad en slecht weer (pipeline/klim/weer.py)."""

from pipeline.klim.ophalen import plekken, soort
from pipeline.klim.weer import graad, graniet, label, per_uur, zandsteen


def test_soort():
    assert soort({"climbing": "boulder"}) == "boulderen"
    assert soort({"climbing:boulder": "yes"}) == "boulderen"
    assert soort({"climbing": "crag"}) == "muurklimmen"
    assert soort({}) == "muurklimmen"


def test_alleen_crags_areas_boulders():
    def el(i, **tags):
        return {"type": "node", "id": i, "lat": 38, "lon": -9, "tags": {"sport": "climbing", **tags}}
    e = [el(1, leisure="sports_centre", climbing="crag"), el(2, climbing="crag"), el(3, climbing="route_bottom"),
         el(4, climbing="route"), el(5, climbing="bolt"), el(6), el(7, climbing="boulder"),
         el(8, **{"climbing:boulder": "yes"}), el(9, climbing="area")]
    assert [p["id"] for p in plekken(e)] == ["node/2", "node/7", "node/8", "node/9"]


def test_area_met_crag_erin_valt_weg():
    vierkant = [{"lon": x, "lat": y} for x, y in [(-9, 38), (-8, 38), (-8, 39), (-9, 39), (-9, 38)]]
    area = {"type": "way", "id": 1, "center": {"lon": -8.5, "lat": 38.5}, "geometry": vierkant,
            "tags": {"sport": "climbing", "climbing": "area"}}
    crag = {"type": "node", "id": 2, "lon": -8.4, "lat": 38.4, "tags": {"sport": "climbing", "climbing": "crag"}}
    ver = {"type": "node", "id": 3, "lon": -7, "lat": 38.4, "tags": {"sport": "climbing", "climbing": "crag"}}
    assert [p["id"] for p in plekken([area, crag])] == ["node/2"]
    assert [p["id"] for p in plekken([area, ver])] == ["way/1", "node/3"]


def test_graad():
    assert graad("5a", "7b") == "5a–7b"
    assert graad("6a", "6a") == "6a"
    assert graad(None, "7b") == "7b"
    assert graad(None, None) == "?"
    assert label({"soort": "muurklimmen", "french:min": "5a", "font:min": "6A"}) == "5a"
    assert label({"soort": "boulderen", "font:min": "6A", "font:max": "7B"}) == "?"  # alleen de Franse graad
    assert label({"soort": "boulderen", "french:min": "5a"}) == "5a"


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


def test_ligging_uit_bounds():
    from pipeline.klim.ophalen import midden
    assert midden({"type": "way", "bounds": {"minlon": -9, "maxlon": -8, "minlat": 38, "maxlat": 39}}) == (-8.5, 38.5)
