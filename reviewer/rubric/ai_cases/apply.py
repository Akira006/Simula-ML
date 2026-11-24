"""Menulis rubrik spesifik ke ai_cases.json di repo web (hanya description dan levelDescriptions).

    python apply.py <path ke server/scripts/seed/data/ai_cases.json>

Nama kriteria, bobot, urutan, dan isi case lain tidak berubah.
"""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubrics import RUBRICS  # noqa: E402

GENERIC_ENDINGS = (
    "atau isinya tidak relevan dengan kasus.",
    "dan belum memakai data dari kasus.",
    "namun masih ada celah yang jelas.",
    "dengan sedikit celah kecil.",
    "serta mempertimbangkan risiko dan alternatif.",
)


def check(cases: list[dict]) -> None:
    assert {c["slug"] for c in cases} == set(RUBRICS), "slug tidak cocok"
    for case in cases:
        rubric = RUBRICS[case["slug"]]
        assert [r["name"] for r in case["rubric"]] == list(rubric), (case["slug"], "nama kriteria tidak cocok")
        assert sum(r["weight"] for r in case["rubric"]) == 100, case["slug"]
        for name, (description, levels) in rubric.items():
            where = (case["slug"], name)
            assert description and len(levels) == 5 and len(set(levels)) == 5, where
            for text in [description, *levels]:
                assert text == text.strip() and text.endswith("."), (where, text)
                assert len(text) <= 420, (where, len(text))
                assert not text.endswith(GENERIC_ENDINGS), (where, text)


def main(path: str) -> None:
    target = Path(path)
    raw = target.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    cases = json.loads(raw)
    check(cases)
    before = copy.deepcopy(cases)
    for case in cases:
        for criterion in case["rubric"]:
            description, levels = RUBRICS[case["slug"]][criterion["name"]]
            criterion["description"] = description
            criterion["levelDescriptions"] = levels
    stripped = copy.deepcopy(cases)
    for old_case, new_case in zip(before, stripped):
        for old, new in zip(old_case["rubric"], new_case["rubric"]):
            for key in ("description", "levelDescriptions"):
                old.pop(key), new.pop(key)
    assert before == stripped, "bagian selain rubrik ikut berubah"
    text = json.dumps(cases, ensure_ascii=False, indent=2) + ("\n" if raw.endswith("\n") else "")
    target.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    print(f"{len(cases)} case, {sum(len(c['rubric']) for c in cases)} kriteria diperbarui")


if __name__ == "__main__":
    main(sys.argv[1])
