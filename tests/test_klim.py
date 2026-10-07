"""Klimplekken: graad en slecht weer (pipeline/klim/weer.py)."""

from pipeline.klim.weer import graad, graniet, label, per_uur, zandsteen


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



def test_graden_uniform_en_bereik():
    from pipeline.klim.graden import bereik, font, frans, tekst
    assert frans("6A+") == (["6a+"], False)
    assert frans("6a/6a+") == (["6a", "6a+"], False)
    assert frans("6a - 6c") == (["6a", "6c"], False)
    assert frans("III") == (["III"], False)        # Romeins cijfer in het Franse veld: zoals in de bron
    assert frans("onbekend") is None
    assert font("6a+") == (["6A+"], False)
    assert bereik(["7b", "5c", "6a+"]) == ("5c", "7b")
    assert tekst("5c", "7b") == "5c – 7b" and tekst(None, None) == "graad onbekend"


def test_omrekenen():
    from pipeline.klim.graden import uiaa, vschaal, yds
    assert uiaa("VI+") == (["6a"], True)
    assert uiaa("VII-") == (["6a+"], True)
    assert yds("5.10a") == (["6a"], True)
    assert vschaal("V4") == (["6B"], True)
    assert yds("5.11c") is None                     # geen eenduidige waarde in de tabel
