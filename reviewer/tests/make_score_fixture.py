"""Membuat fixtures/score_ts_reference.json: kasus skor + hasil score.ts asli yang dijalankan Node.

    python -m reviewer.tests.make_score_fixture <path ke client/src/lib/score.ts>

Fixture disimpan supaya test_score.py tetap bisa membandingkan tanpa Node dan tanpa folder client.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "score_ts_reference.json"


def build_cases() -> dict:
    points = [{"level": lv, "weight": w} for lv in range(1, 6) for w in range(0, 101)]
    points += [{"level": lv, "weight": w} for lv in range(1, 6)
               for w in (0.1, 2.5, 7.5, 12.5, 16.7, 33.3, 33.33, 37.5, 62.5, 0.25, 0.75, 1.25)]
    rng = random.Random(20261009)
    totals = [
        # Contoh AI-CONTEXT 6.4 (harus 76) dan kasus .5 (Math.round ke atas, round() Python ke genap).
        [{"level": 4, "weight": 30}, {"level": 3, "weight": 35}, {"level": 4, "weight": 20}, {"level": 5, "weight": 15}],
        [{"level": 3, "weight": 25}, {"level": 3, "weight": 25}, {"level": 3, "weight": 25}, {"level": 4, "weight": 25}],
        [{"level": 1, "weight": 25}, {"level": 2, "weight": 25}, {"level": 3, "weight": 25}, {"level": 4, "weight": 25}],
        [{"level": 3, "weight": 12.5}, {"level": 3, "weight": 87.5}],
        [{"level": 2, "weight": 12.5}, {"level": 5, "weight": 87.5}],
        [{"level": 3, "weight": 33.3}, {"level": 3, "weight": 33.3}, {"level": 4, "weight": 33.4}],
    ]
    for _ in range(600):
        n = rng.randint(2, 6)
        cuts = sorted(rng.sample(range(1, 100), n - 1))
        weights = [b - a for a, b in zip([0] + cuts, cuts + [100])]
        totals.append([{"level": rng.randint(1, 5), "weight": w} for w in weights])
    return {"points": points, "totals": totals}


def main(score_ts: str) -> None:
    cases = build_cases()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(cases, fh)
        cases_path = fh.name
    out = subprocess.run(["node", str(HERE / "score_crosscheck.mjs"), score_ts, cases_path],
                         capture_output=True, text=True, check=True)
    result = json.loads(out.stdout)
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_text(json.dumps({
        "generated_by": f"Node {result['node']} menjalankan client/src/lib/score.ts dari Simula-main.zip",
        "cases": cases,
        "expected_points": result["points"],
        "expected_totals": result["totals"],
    }, indent=1), encoding="utf-8")
    print(f"{len(cases['points'])} kasus poin dan {len(cases['totals'])} kasus total ditulis ke {FIXTURE}")


if __name__ == "__main__":
    main(sys.argv[1])
