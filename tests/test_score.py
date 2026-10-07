"""M5: de acceptatietests uit PLAN.md (M5, 'Klaar als')."""

import pytest

from pipeline.rules.score import Strand, Uur, breaking_height, score

WEST = Strand(kijkrichting=270)  # open strand dat naar het westen kijkt


def uur(w=5.0, g=None, d=270.0, h=0.0, t=10.0, gd=270.0, ipma="green"):
    """Eén deelgolf; d = windrichting (270 = recht uit zee voor WEST)."""
    return Uur(wind_kn=w, vlagen_kn=g if g is not None else w, windrichting=d,
               deelgolven=[(h, t, gd)] if h else [], ipma_zeegang=ipma)


def hb_for(target, t=12.0):
    """Golfhoogte op zee die op een open strand precies Hb = target geeft."""
    # Hb = 0,39 · g^0,2 · (T · H²)^0,4  →  H = sqrt((Hb / (0,39 · g^0,2))^2,5 / T)
    return ((target / (0.39 * 9.81 ** 0.2)) ** 2.5 / t) ** 0.5


# --- rekenvoorbeelden ----------------------------------------------------------

@pytest.mark.parametrize("h,t,hb", [(1.0, 12, 1.66), (2.0, 12, 2.90), (0.5, 6, 0.72)])
def test_rekenvoorbeelden(h, t, hb):
    assert breaking_height([(h, t, 270)], [1.0] * 36) == pytest.approx(hb, abs=0.005)


def test_blootstelling_halveert_niet_maar_verkleint():
    f = [0.5] * 36
    assert breaking_height([(1.0, 12, 270)], f) == pytest.approx(0.95, abs=0.01)  # PLAN.md 2.5: f = 0,5 geeft 0,95 m


# --- grenzen WIND (PLAN.md 2.4) --------------------------------------------------

@pytest.mark.parametrize("w,s", [(7.9, 1), (8.0, 2), (11.9, 2), (12.0, 3), (21.9, 3), (22.0, 4), (33.9, 4), (34.0, 5)])
def test_windgrenzen(w, s):
    assert score(uur(w=w, d=225), WEST).wind == s  # schuin aanlandig: richting verandert niets


@pytest.mark.parametrize("g,s", [(30.0, 3), (30.1, 4), (37.9, 4), (38.0, 5)])
def test_vlagen(g, s):
    assert score(uur(w=15, g=g, d=225), WEST).wind == s


def test_vlagen_tegen_aflandig_oorzaak():
    r = score(uur(w=15, g=40, d=225), WEST)
    assert r.wind == 5 and r.wind_oorzaak == "vlagen" and r.label == "Gevaarlijk: storm"


# --- richting -------------------------------------------------------------------

@pytest.mark.parametrize("d,klasse", [
    (270, "aanlandig"), (292.4, "aanlandig"), (292.6, "schuin_aan"), (337.4, "schuin_aan"), (337.6, "zij"),
    (22.4, "zij"), (22.6, "schuin_af"), (67.4, "schuin_af"), (67.6, "af"), (90, "af"),
])
def test_windklassen(d, klasse):
    assert score(uur(w=5, d=d), WEST).windklasse == klasse


@pytest.mark.parametrize("d", [45.0, 90.0, 135.0])  # schuin aflandig en aflandig
def test_aflandig_vanaf_12_kn_altijd_5(d):
    assert score(uur(w=12.0, d=d), WEST).wind == 5
    assert score(uur(w=12.0, d=d), Strand(kijkrichting=270, besloten_water=True)).wind == 3


@pytest.mark.parametrize("d", [45.0, 90.0, 135.0])
def test_aflandig_onder_12_kn_is_2_met_uitroepteken(d):
    # Te licht om te kiten; voor golfsurf net goed (eigenaar, 7 okt 2026).
    r = score(uur(w=8.0, d=d), WEST)
    assert r.wind == 2 and r.let_op and r.waarschuwing.startswith("aflandige wind")
    assert score(uur(w=7.9, d=d), WEST).wind == 1
    assert not score(uur(w=11.9, d=225), WEST).let_op  # aanlandig: geen uitroepteken


def test_richting_onzeker_geen_oordeel():
    r = score(uur(w=15, d=90), Strand(kijkrichting=270, richting_onzeker=True))
    assert r.wind == 3 and "richting niet beoordeeld" in r.notas


# --- grenzen WAVE (PLAN.md 2.5) --------------------------------------------------

@pytest.mark.parametrize("target,s", [
    (0.29, 1), (0.30, 2), (0.49, 2), (0.50, 3), (0.99, 3), (1.00, 4), (2.99, 4), (3.00, 5),
])
def test_golfgrenzen(target, s):
    h = hb_for(target + 1e-6)
    assert score(uur(h=h, t=12), WEST).wave == s


def test_onder_halve_meter_nooit_3_of_hoger():
    for target in (0.1, 0.3, 0.49):
        for t in (6, 10, 16):
            assert score(uur(h=hb_for(target, t), t=t), WEST).wave <= 2


@pytest.mark.parametrize("level", ["yellow", "orange", "red"])
def test_ipma_zeegang_altijd_5(level):
    assert score(uur(h=0.2, t=8, ipma=level), WEST).wave == 5


def test_korte_periode_hoogstens_2_tenzij_5():
    assert score(uur(h=1.5, t=5), WEST).wave == 2
    assert score(uur(h=hb_for(3.2, 5.9), t=5.9), WEST).wave == 5


def test_lange_periode_nota():
    assert any("lange deining" in n for n in score(uur(h=1, t=15), WEST).notas)


# --- label: alle elf regels --------------------------------------------------------

@pytest.mark.parametrize("u,label", [
    (uur(w=5, h=hb_for(3.5), t=12), "Gevaarlijke zee"),                                       # 1
    (uur(w=35, d=225), "Gevaarlijk: storm"),                                                  # 2
    (uur(w=10, d=90, h=hb_for(0.8), t=12), "Surfdag voor beginners"),                         # 3
    (uur(w=18, d=90, h=hb_for(1.8), t=12), "Surfdag voor gevorderden"),                       # 4
    (uur(w=25, d=90, h=hb_for(1.8), t=12), "Aflandige wind: gevaarlijk voor kite, windsurf en sup"),  # 5
    (uur(w=15, d=225, h=hb_for(1.5), t=12), "Winddag met golven (gevorderd)"),                # 6
    (uur(w=25, d=225), "Winddag voor gevorderden"),                                           # 7
    (uur(w=15, d=225), "Winddag voor beginners"),                                             # 8
    (uur(w=5, d=225, h=hb_for(1.8), t=12), "Surfdag voor gevorderden"),                       # 9
    (uur(w=5, d=225, h=hb_for(0.8), t=12), "Surfdag voor beginners"),                         # 10
    (uur(w=5, d=225), "Stille dag (sup, kayak, wakeboard)"),                                  # 11
])
def test_labels(u, label):
    assert score(u, WEST).label == label


def test_label_3_en_4_dragen_een_waarschuwing():
    assert score(uur(w=10, d=90, h=hb_for(0.8), t=12), WEST).waarschuwing.startswith("aflandige wind")
    assert score(uur(w=18, d=90, h=hb_for(1.8), t=12), WEST).waarschuwing.startswith("aflandige wind")


# --- getij en redenen ----------------------------------------------------------------

def test_getij_verandert_geen_score():
    u = uur(w=14, d=225, h=1.2, t=11)
    base = score(u, WEST)
    for getij in ({"fase": "laag"}, {"fase": "hoog"}, {"hoogte_m": 3.6}):
        r = score(u, WEST, getij=getij)
        assert (r.wind, r.wave, r.label) == (base.wind, base.wave, base.label)


def test_reden_in_woorden():
    r = score(uur(w=16, d=225, h=1.0, t=12), WEST)
    assert r.redenen[0] == "WIND 3: 16 kn, schuin aanlandig"
    assert r.redenen[1] == "WAVE 4: 1,7 m brekend, 12 s"


def test_restdeel_telt_als_windgolf():
    u = Uur(wind_kn=5, vlagen_kn=5, windrichting=225, deelgolven=[(0.8, 10, 270), (0, 0, 0), (0.2, 4, 270)],
            golfhoogte_totaal=1.0, golfperiode_totaal=9)
    with_rest = score(u, WEST).hb
    u.golfhoogte_totaal = None
    assert with_rest > score(u, WEST).hb
