"""De plankscore moet de testsets uit de overdracht exact volgen (verschil hoogstens 0,01)."""
import json
from pathlib import Path

import pytest

from score import referentie as R

MAP = Path(R.__file__).parent


@pytest.mark.parametrize("naam", ["testset_100.json", "testset_1000.json", "testset_getij_uur.json"])
def test_testset(naam):
    data = json.loads((MAP / naam).read_text())["situaties"]
    P = {k: {q: R.X(k, q) for q in R.KEYS} for k in R.PL}
    alfa = R.REGELS["score"]["alfa"]["waarde"]
    mx = 0.0
    for r in data:
        s = R.situatie(r)
        uit = R.score(R.kenmerken(s, R.bereken(s)), P, alfa)
        mx = max(mx, max(abs(uit[k][0] - r["regel"][k]) for k in R.PL))
    assert mx <= 0.01
