"""Membangkitkan test_vectors/vectors.json dari implementasi referensi.

Tujuan: implementasi TypeScript (frontend) atau Go (backend) nanti menjalankan setiap kasus dan
harus menghasilkan objek `expected` yang IDENTIK (termasuk urutan saran, persen, alasan, dan
tieLike). Jalankan ulang hanya bila quiz.v2.json berubah, dan naikkan `version` di config.

    python -m quiz.test_vectors.generate      (dari folder ml/)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ..simulation.engine import Engine, answers_to_dicts, persona_answers, uniform_answers
from ..src.config import CONFIG_DIR, load_config
from ..src.scoring import QuizAnswerError, score_quiz

OUT = Path(__file__).resolve().parent / "vectors.json"
AT = "2026-10-09T08:00:00Z"
CONFIG_NAME = "quiz.v2.json"


def base(**overrides):
    answers = {"q1": "q1_a", "q2": "q2_a", "q3": "q3_c", "q4": ["q4_none"], "q5": "q5_c", "q6": "q6_b", "q7": 3}
    answers.update(overrides)
    return answers


def handpicked(config):
    q4 = next(q for q in config["questions"] if q["id"] == "q4")
    all_tools = [o["id"] for o in q4["options"] if o["id"] != "q4_none"]
    return [
        ("seri Back-End dan Data, dipecah strong_count", base()),
        ("seri Data dan Marketing, dipecah rotasi jawaban", base(q3="q3_e", q5="q5_e")),
        ("seri UI/UX dan Marketing, dipecah rotasi jawaban", base(q1="q1_c", q3="q3_e", q5="q5_e")),
        ("aturan klaster: tech ketiga diganti (selisih 1 poin)", base(q1="q1_b", q3="q3_c", q5="q5_a", q6="q6_c")),
        ("aturan klaster: tech ketiga dipertahankan (selisih 3 poin)",
         base(q1="q1_b", q2="q2_b", q3="q3_c", q4=["q4_api", "q4_web"], q5="q5_a", q6="q6_a")),
        ("Q4 semua dicentang", base(q4=all_tools)),
        ("Q4 satu tools", base(q4=["q4_law"])),
        ("Q8 kosong string", {**base(), "q8": ""}),
        ("Q8 hanya spasi", {**base(), "q8": "   "}),
        ("Q8 tidak dikenali", {**base(), "q8": "Sastra Jepang"}),
        ("Q8 akuntansi (huruf campur, spasi)", {**base(), "q8": "  AKUNTANSI  "}),
        ("Q8 cocok dua entri", {**base(), "q8": "Manajemen Informatika"}),
        ("Q8 DKV tidak ikut entri komunikasi", {**base(), "q8": "Desain Komunikasi Visual"}),
        ("Q8 hukum", {**base(), "q8": "Ilmu Hukum"}),
        ("Q7 = 1", base(q7=1)),
        ("Q7 = 5", base(q7=5)),
    ]


def persona_ideals(config):
    """Jawaban 'ideal' untuk tiap bidang: opsi berbobot tertinggi di setiap soal, tools bidang itu."""
    cases = []
    for field in config["fields"]:
        key = field["key"]
        answers = {"q7": 4}
        for q in config["questions"]:
            if q["type"] == "single":
                answers[q["id"]] = max(q["options"], key=lambda o: o["points"].get(key, 0))["id"]
            elif q["type"] == "multi":
                answers[q["id"]] = [o["id"] for o in q["options"] if o["points"].get(key, 0) > 0] or ["q4_none"]
        cases.append((f"jawaban ideal persona {field['label']}", answers))
    return cases


def random_cases(config, n):
    engine = Engine(config)
    rng = np.random.default_rng(42)
    rows = answers_to_dicts(engine, uniform_answers(engine, n, rng), confidence=2)
    rows += answers_to_dicts(engine, persona_answers(engine, 6, 3, rng, eps=0.4, major_entry=4), confidence=5)
    return [(f"acak #{i + 1}", r) for i, r in enumerate(rows)]


def invalid_cases():
    return [
        ("tidak valid: kosong", {}),
        ("tidak valid: opsi tidak dikenal", base(q1="q1_z")),
        ("tidak valid: Belum ada digabung", base(q4=["q4_none", "q4_api"])),
        ("tidak valid: Q7 di luar 1-5", base(q7=0)),
    ]


def main() -> None:
    config = load_config(CONFIG_NAME)
    digest = hashlib.sha256((CONFIG_DIR / CONFIG_NAME).read_bytes()).hexdigest()
    cases = []
    for name, answers in handpicked(config) + persona_ideals(config) + random_cases(config, 10):
        result = score_quiz(config, answers, AT)
        cases.append({"name": name, "answers": answers, "answeredAt": AT, "expected": result})
    for name, answers in invalid_cases():
        try:
            score_quiz(config, answers, AT)
        except QuizAnswerError as err:
            cases.append({"name": name, "answers": answers, "answeredAt": AT,
                          "expectedError": {"questionIds": sorted({p.split(":")[0] for p in err.problems})}})
        else:
            raise AssertionError(f"{name} seharusnya tidak valid")
    payload = {
        "description": "Test vector kuis minat. Implementasi lain wajib menghasilkan `expected` identik "
                       "(urutan saran, persen, alasan, tieLike, meta) atau menolak kasus `expectedError` "
                       "dengan masalah pada soal yang sama.",
        "configFile": f"ml/quiz/config/{CONFIG_NAME}",
        "configVersion": config["version"],
        "configSha256": digest,
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(cases)} kasus ditulis ke {OUT}")


if __name__ == "__main__":
    main()
