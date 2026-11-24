"""Membandingkan hasil tes jawaban berjenjang dengan harapan (harapan.json).

    python analyze.py rancang-ulang-endpoint-ekspor-laporan/hasil-rubrik-asli.json
"""

import json
import sys
from collections import defaultdict
from statistics import median
from pathlib import Path


def main(path: str) -> None:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    by = defaultdict(list)
    for r in rows:
        by[r["submission"]].append(r)
    assert len(rows) == 24 and not [r for r in rows if r.get("error")], [r.get("error") for r in rows]
    score = {k[:2]: median(r["score"] for r in v) for k, v in by.items()}
    level = {k[:2]: [median(r["levels"][i] for r in v) for i in range(4)] for k, v in by.items()}
    same = total = 0
    worst = 0
    for k, v in sorted(by.items()):
        scores = [r["score"] for r in v]
        worst = max(worst, max(scores) - min(scores))
        for i in range(4):
            total += 1
            same += len({r["levels"][i] for r in v}) == 1
        print(f"{k:32} skor {scores} median {median(scores)} | level {[r['levels'] for r in v]}")
    others = [i for i in (0, 1, 3)]
    checks = [
        ("01, 02, 03 median < 60", all(score[k] < 60 for k in ("01", "02", "03"))),
        ("03 >= 01 dan 03 >= 02", score["03"] >= score["01"] and score["03"] >= score["02"]),
        ("04 di antara 03 dan 05", score["03"] < score["04"] < score["05"]),
        ("05 tertinggi dan >= 80", score["05"] == max(score.values()) and score["05"] >= 80),
        ("05 - 04 >= 15", score["05"] - score["04"] >= 15),
        ("06 kriteria 3 median <= 2", level["06"][2] <= 2),
        ("06 kriteria lain berselisih <= 1", all(abs(level["06"][i] - level["05"][i]) <= 1 for i in others)),
        ("07 <= 04 - 5", score["07"] <= score["04"] - 5),
        ("08 <= 04 dan tiap kriteria <= 04", score["08"] <= score["04"] and all(a <= b for a, b in zip(level["08"], level["04"]))),
        (f"level sama di 3 run >= 90% ({same}/{total} = {same / total:.0%})", same / total >= 0.9),
        (f"selisih skor antar-run <= 5 (terbesar {worst})", worst <= 5),
    ]
    for name, ok in checks:
        print("LOLOS " if ok else "GAGAL ", name)


if __name__ == "__main__":
    main(sys.argv[1])
