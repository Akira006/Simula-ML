"""Validasi rubrik: JSON Schema + pemeriksaan semantik yang tidak bisa dinyatakan di skema.

    python -m reviewer.src.rubric reviewer/rubric/examples/*.rubric.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

RUBRIC_DIR = Path(__file__).resolve().parents[1] / "rubric"
SCHEMA = json.loads((RUBRIC_DIR / "rubric.schema.json").read_text(encoding="utf-8"))

# Deskripsi umum di client/src/constants/review.ts. Tidak boleh dipakai apa adanya di AI case.
GENERIC_LEVELS = {
    "bagian ini tidak ada atau tidak menjawab tugas.",
    "ada, tetapi banyak kekeliruan atau belum menjawab inti tugas.",
    "menjawab tugas, dengan beberapa kekurangan yang jelas.",
    "tepat dan rapi, hanya perlu sedikit penyempurnaan.",
    "melampaui harapan dan siap dipakai di lingkungan kerja.",
}


class RubricError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def rubric_problems(rubric: dict[str, Any]) -> list[str]:
    problems = [f"skema: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
                for e in Draft202012Validator(SCHEMA).iter_errors(rubric)]
    if problems:
        return problems  # pemeriksaan semantik mengandaikan bentuknya sudah benar

    criteria = rubric["criteria"]
    total = sum(c["weight"] for c in criteria)
    if total != 100:
        problems.append(f"total bobot harus 100, sekarang {total}")
    for attr in ("id", "name"):
        values = [c[attr] for c in criteria]
        dupes = {v for v in values if values.count(v) > 1}
        if dupes:
            problems.append(f"{attr} kriteria duplikat: {sorted(dupes)}")
    slot_ids = [s["id"] for s in rubric["slots"]]
    if len(slot_ids) != len(set(slot_ids)):
        problems.append("id slot duplikat")
    for c in criteria:
        missing = set(c["evidence_slots"]) - set(slot_ids)
        if missing:
            problems.append(f"{c['id']}: evidence_slots tidak dikenal: {sorted(missing)}")
        levels = [c["levels"][str(i)].strip() for i in range(1, 6)]
        if len({lv.lower() for lv in levels}) != 5:
            problems.append(f"{c['id']}: deskripsi level 1-5 harus berbeda satu sama lain")
        for i, lv in enumerate(levels, start=1):
            if lv.lower() in GENERIC_LEVELS:
                problems.append(f"{c['id']}: level {i} masih memakai deskripsi umum, tulis yang spesifik untuk kriteria ini")
    for s in rubric["slots"]:
        if "min_words" in s and "max_words" in s and s["min_words"] > s["max_words"]:
            problems.append(f"slot {s['id']}: min_words > max_words")
    used = {sid for c in criteria for sid in c["evidence_slots"]}
    unused = set(slot_ids) - used
    if unused:
        problems.append(f"slot tidak dipakai kriteria mana pun: {sorted(unused)}")
    return problems


def load_rubric(path: str | Path) -> dict[str, Any]:
    rubric = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = rubric_problems(rubric)
    if problems:
        raise RubricError(problems)
    return rubric


def main(paths: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    status = 0
    for path in paths:
        try:
            load_rubric(path)
            print(f"OK    {path}")
        except RubricError as err:
            status = 1
            print(f"GAGAL {path}")
            for p in err.problems:
                print(f"      - {p}")
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
