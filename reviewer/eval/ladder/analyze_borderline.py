"""Memeriksa harapan-batas-lulus.json (12 jawaban). Pelengkap analyze.py."""

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median


def main(path: str) -> None:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    assert len(rows) == 36 and not [r for r in rows if r.get("error")]
    by = defaultdict(list)
    for r in rows:
        by[r["submission"][:2]].append(r)
    score = {k: median(r["score"] for r in v) for k, v in by.items()}
    level = {k: [median(r["levels"][i] for r in v) for i in range(4)] for k, v in by.items()}
    cells = [len({r["levels"][i] for r in v}) == 1 for v in by.values() for i in range(4)]
    spread = {k: max(r["score"] for r in v) - min(r["score"] for r in v) for k, v in by.items()}
    flips = [k for k, v in by.items() if len({r["score"] >= 60 for r in v}) > 1]
    for k in sorted(by):
        print(k, [r["score"] for r in by[k]], [r["levels"] for r in by[k]])
    checks = [
        ("09 K1 >= 4 dan K3 <= 2", level["09"][0] >= 4 and level["09"][2] <= 2),
        ("10 K1 <= 2 dan K2 >= 4", level["10"][0] <= 2 and level["10"][1] >= 4),
        ("11 skor 55-68 dan > 12", 55 <= score["11"] <= 68 and score["11"] > score["12"]),
        ("12 < 60 dan hanya K3 berbeda dari 11", score["12"] < 60 and [i for i in range(4) if level["11"][i] != level["12"][i]] == [2]),
        (f"level sama >= 90% ({sum(cells)}/{len(cells)} = {sum(cells) / len(cells):.0%})", sum(cells) / len(cells) >= 0.9),
        (f"selisih skor <= 5 (terbesar {max(spread.values())}: {[k for k, s in spread.items() if s > 5]})", max(spread.values()) <= 5),
        (f"tidak ada lulus/gagal berubah ({flips})", not flips),
    ]
    for name, ok in checks:
        print("LOLOS " if ok else "GAGAL ", name)


if __name__ == "__main__":
    main(sys.argv[1])
