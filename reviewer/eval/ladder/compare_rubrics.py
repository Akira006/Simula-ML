"""Membandingkan rubrik asli dan rubrik spesifik (putaran 2) pada 12 jawaban yang sama.

    python compare_rubrics.py
"""

import json
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent / "rancang-ulang-endpoint-ekspor-laporan"


def load(*names):
    by = defaultdict(list)
    for name in names:
        for row in json.loads((DATA / name).read_text(encoding="utf-8")):
            assert not row.get("error"), row
            by[row["submission"]].append(row)
    assert len(by) == 12 and all(len(v) == 3 for v in by.values())
    return by


def main() -> None:
    old = load("hasil-rubrik-asli.json", "hasil-rubrik-asli-batas-lulus.json")
    new = load("hasil-rubrik-spesifik-2.json")
    for label, by in (("ASLI", old), ("BARU", new)):
        same = [len({r["levels"][i] for r in v}) == 1 for v in by.values() for i in range(4)]
        spread = {k[:2]: max(r["score"] for r in v) - min(r["score"] for r in v) for k, v in by.items()}
        flips = [k[:2] for k, v in by.items() if len({r["score"] >= 60 for r in v}) > 1]
        print(f"{label}: level sama {sum(same)}/{len(same)} = {sum(same) / len(same):.1%} | selisih maks {max(spread.values())} "
              f"| selisih > 5: {[k for k, s in spread.items() if s > 5]} | lulus/gagal berubah: {flips}")
    for k in sorted(old):
        print(f"{k:36} asli {[r['score'] for r in old[k]]} {[r['levels'] for r in old[k]]} | baru {[r['score'] for r in new[k]]}")
    for k in sorted(old):
        for i in range(4):
            if k[:2] >= "09" and len({r["levels"][i] for r in old[k]}) > 1:
                for r in old[k]:
                    print(f"  goyah (asli) {k[:2]} K{i + 1} L{r['levels'][i]} | {r['reasons'][i]}")


if __name__ == "__main__":
    main()
