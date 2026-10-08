from pipeline.site.inpakken import VELDEN, ontpak, pak


def test_heen_en_terug():
    reeksen = {"wind": [0, 12.3, None, 35.7], "E_zee": [0, 4096, 70000, None], "H": [0.0, 1.23, 4.5, None],
               "windrichting": [0, 359, None, 180], "verval": [0.12, 6.62, None, 0],
               "stroom_pct": [-59, 0, 107, None], "stroom": [0.0, 2.3, None, 0.1]}
    for veld, xs in reeksen.items():
        opties = VELDEN[veld]
        assert ontpak(pak(xs, *opties), *opties) == xs


def test_conclusies_heen_en_terug():
    import copy

    from pipeline.site.inpakken import conclusies_inpakken, conclusies_uitpakken
    d = {"scores": [[10, 20, 25, 30, 0], [10, 20, 26, 30, 0], None, [80, 0, 0, 0, 60]],
         "conclusie": ["andere: windsurfen 25/100, niet ideaal door te weinig wind",
                       "andere: windsurfen 26/100, niet ideaal door te weinig wind", None,
                       "te wild; golfsurfen 80/100 alleen voor ervaren"]}
    orig = copy.deepcopy(d)
    p = conclusies_inpakken(d)
    assert len(p["conclusies"]) == 2  # de twee windsurfteksten delen één sjabloon
    assert conclusies_uitpakken(p)["conclusie"] == orig["conclusie"]
    assert p["scores"] == orig["scores"]
