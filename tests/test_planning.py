"""Planning op de score van de rekenchat: blokken van minstens 3 uur met 60 of meer, per categorie."""
import json
from datetime import UTC, datetime, timedelta

from pipeline.site import planning


def test_blokken_per_categorie(tmp_path):
    t0 = datetime(2026, 10, 10, 0, tzinfo=UTC)
    axis = [(t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(48)]
    reeks = bytearray([255]) * 48
    for i, v in zip(range(10, 15), [70, 80, 90, 65, 40], strict=True):  # 10-13 UTC: 4 uur 60+
        reeks[i] = v
    kort = bytearray([255]) * 48
    kort[11], kort[12] = 90, 90  # maar 2 uur: geen blok
    planning.SCORES.clear()
    planning.SCORES["s1"] = {"naam": "Proef", "lat": 37.1, "lon": -8.6, "land": "pt",
                             "scores": {"golfsurfen_beginner": reeks, "stil": kort}}
    planning.RIJ.clear()
    planning.RIJ["s1"] = {"min": 15}
    uit = planning.maak(axis, tmp_path, {}, [])
    dag = next(d for d in uit["dagen"] if d["dag"] == "2026-10-10")
    bl = dag["kandidaten"]["golfsurfen_beginner"]
    assert len(bl) == 1 and bl[0]["van"] == "11:00" and bl[0]["tot"] == "15:00"  # Lissabon = UTC+1
    assert bl[0]["score"] == 76.2 and bl[0]["rij"] == 15
    assert "stil" not in dag["kandidaten"]
    assert json.loads((tmp_path / "planning.json").read_text())["dagen"]
