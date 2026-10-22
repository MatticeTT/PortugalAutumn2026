from spots.verwerken import osm_kandidaten, samenvoegen, vensters


def test_vensters_loopt_rond_noord():
    open_km = [0.0] * 72
    for i in list(range(66, 72)) + list(range(0, 4)):  # 330 .. 15 graden open
        open_km[i] = 300.0
    assert vensters(open_km) == [[330, 15]]
    assert vensters([300.0] * 72) == [[0, 360]]
    assert vensters([5.0] * 72) == []


def test_zaken_eruit_en_dubbels_samen():
    obj = [
        {"osm": "node/1", "lat": 39.0, "lon": -9.4, "tags": {"name": "Coxos", "surfing": "yes"}},
        {"osm": "way/2", "lat": 39.005, "lon": -9.42, "tags": {"name": "Praia dos Coxos", "natural": "beach"}},
        {"osm": "node/3", "lat": 39.0, "lon": -9.4, "tags": {"name": "Coxos Surf School", "sport": "surfing"}},
        {"osm": "node/4", "lat": 39.0, "lon": -9.4, "tags": {"name": "Surfshop", "shop": "sports"}},
        {"osm": "node/5", "lat": 39.0, "lon": -9.4, "tags": {"sport": "surfing"}},
    ]
    k, weg = osm_kandidaten(obj)
    assert [x["naam"] for x in k] == ["Coxos", "Praia dos Coxos"]
    s = samenvoegen(k)
    assert len(s) == 1 and s[0]["naam"] == "Coxos" and len(s[0]["bronnen"]) == 2
