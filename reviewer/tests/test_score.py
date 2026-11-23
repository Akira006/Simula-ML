"""score.py harus identik dengan client/src/lib/score.ts.

Pembanding utama: fixtures/score_ts_reference.json, berisi keluaran score.ts ASLI yang dijalankan
dengan Node (lihat make_score_fixture.py). Bila env SIMULA_SCORE_TS menunjuk ke score.ts dan Node
tersedia, tes juga menjalankan score.ts secara langsung.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from reviewer.src.score import criterion_points, is_passed, js_round, total_score

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / "fixtures" / "score_ts_reference.json").read_text(encoding="utf-8"))


def test_points_identical_to_score_ts():
    got = [criterion_points(c["level"], c["weight"]) for c in FIXTURE["cases"]["points"]]
    mismatches = [(c, g, e) for c, g, e in zip(FIXTURE["cases"]["points"], got, FIXTURE["expected_points"]) if g != e]
    assert not mismatches, mismatches[:5]


def test_totals_identical_to_score_ts():
    got = [total_score(c) for c in FIXTURE["cases"]["totals"]]
    mismatches = [(c, g, e) for c, g, e in zip(FIXTURE["cases"]["totals"], got, FIXTURE["expected_totals"]) if g != e]
    assert not mismatches, mismatches[:5]


def test_ai_context_example_is_76_and_passes():
    criteria = [{"level": 4, "weight": 30}, {"level": 3, "weight": 35}, {"level": 4, "weight": 20}, {"level": 5, "weight": 15}]
    assert [criterion_points(c["level"], c["weight"]) for c in criteria] == [24.0, 21.0, 16.0, 15.0]
    assert total_score(criteria) == 76
    assert is_passed(76, 60) and not is_passed(59, 60) and is_passed(60, 60)


def test_python_round_would_disagree_with_js():
    # 3/5*12.5 + 3/5*87.5 = 7.5 + 52.5 = 60.0; 2/5*12.5 + 5/5*87.5 = 5 + 87.5 = 92.5 -> JS 93, round() 92
    criteria = [{"level": 2, "weight": 12.5}, {"level": 5, "weight": 87.5}]
    assert total_score(criteria) == 93
    assert round(5.0 + 87.5) == 92  # alasan js_round dipakai
    assert js_round(0.49999999999999994) == 0.0 and js_round(-2.5) == -2.0 and js_round(2.5) == 3.0


@pytest.mark.skipif(not os.environ.get("SIMULA_SCORE_TS") or not shutil.which("node"),
                    reason="set SIMULA_SCORE_TS=<path client/src/lib/score.ts> untuk menjalankan score.ts langsung")
def test_live_against_score_ts():
    cases = FIXTURE["cases"]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(cases, fh)
    out = subprocess.run(["node", str(HERE / "score_crosscheck.mjs"), os.environ["SIMULA_SCORE_TS"], fh.name],
                         capture_output=True, text=True, check=True)
    result = json.loads(out.stdout)
    assert result["points"] == [criterion_points(c["level"], c["weight"]) for c in cases["points"]]
    assert result["totals"] == [total_score(c) for c in cases["totals"]]
