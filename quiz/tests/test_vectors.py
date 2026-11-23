"""Implementasi referensi harus tetap cocok dengan test vector yang sudah dibagikan ke tim TS/Go."""

import hashlib
import json
from pathlib import Path

import pytest

from quiz.src.config import CONFIG_DIR, load_config
from quiz.src.scoring import QuizAnswerError, score_quiz

VECTORS = json.loads((Path(__file__).resolve().parents[1] / "test_vectors" / "vectors.json").read_text(encoding="utf-8"))


def test_vectors_match_current_config_file():
    name = Path(VECTORS["configFile"]).name
    digest = hashlib.sha256((CONFIG_DIR / name).read_bytes()).hexdigest()
    assert digest == VECTORS["configSha256"], (
        "quiz.v2.json berubah setelah test vector dibuat. Naikkan version bila skor berubah, "
        "lalu jalankan: python -m quiz.test_vectors.generate"
    )


@pytest.mark.parametrize("case", VECTORS["cases"], ids=[c["name"] for c in VECTORS["cases"]])
def test_vector(case):
    config = load_config(Path(VECTORS["configFile"]).name)
    if "expectedError" in case:
        with pytest.raises(QuizAnswerError) as err:
            score_quiz(config, case["answers"], case["answeredAt"])
        assert sorted({p.split(":")[0] for p in err.value.problems}) == case["expectedError"]["questionIds"]
    else:
        assert score_quiz(config, case["answers"], case["answeredAt"]) == case["expected"]
