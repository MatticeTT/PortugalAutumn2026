"""Draait tests.py van de rekenchat letterlijk tegen pipeline/rules/score.py. Alles moet slagen."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rekenchat_tests_alles_ok():
    r = subprocess.run([sys.executable, "tests.py"], cwd=ROOT / "tests" / "rekenchat_score", capture_output=True,
                       text=True, env={"PYTHONPATH": str(ROOT)})
    assert r.returncode == 0, r.stderr
    assert r.stdout.rstrip().endswith("ALLES OK"), r.stdout[-3000:]


def test_zelfde_als_referentie():
    """De app-versie (grenswaarden uit json) geeft exact dezelfde scores als de referentiecode."""
    import importlib.util
    import random

    spec = importlib.util.spec_from_file_location("ref", ROOT / "docs" / "rekenchat" / "score_referentie.py")
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    from pipeline.rules import score as app
    assert app.CATEGORIES == ref.CATEGORIES
    rnd = random.Random(1)
    for _ in range(4000):
        c = dict(wind=rnd.uniform(0, 50), windhoek=rnd.uniform(0, 180), golfhoogte=rnd.uniform(0, 7),
                 periode=rnd.uniform(1, 22), golfhoek=rnd.uniform(0, 90), golf_aan_strand=rnd.uniform(0, 3))
        c["vlaag"] = c["wind"] + rnd.uniform(0, 20)
        if rnd.random() < .5:
            c["stroming"], c["stroming_tov_wind"] = rnd.uniform(0, 3), rnd.choice(["tegen", "mee", "dwars"])
        if rnd.random() < .3:
            c["aandeel_hoofdgolf"] = rnd.random()
        if rnd.random() < .3:
            c["neerslag"] = rnd.uniform(0, 10)
        if rnd.random() < .2:
            c["gewicht"] = rnd.uniform(50, 110)
        niveau = rnd.choice([None, "beginner", "gemiddeld", "ervaren"])
        a, b = app.strand_uur(c, niveau), ref.strand_uur(c, niveau)
        assert a == b
