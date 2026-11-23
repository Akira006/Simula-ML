import copy
import json
from fractions import Fraction
from pathlib import Path

import pytest

from quiz.src.analyze import dominated_pairs, multi_field_options
from quiz.src.config import QuizConfigError, load_config, validate_config
from quiz.src.scoring import QuizAnswerError, max_points, round_half_up_percent, score_quiz

AT = "2026-10-09T08:00:00Z"
# Disalin dari client/src/constants/fields.ts (FIELD_OPTIONS[].key). Bila client berubah, tes ini gagal.
CLIENT_FIELD_KEYS = [
    "backend", "frontend", "mobile", "data", "uiux", "product",
    "marketing", "finance", "accounting", "hr", "supply-chain", "legal",
]
FORBIDDEN_TERMS = ["psikotes", "tes kepribadian", "tes bakat", "psikologis", "kepribadian"]


@pytest.fixture(scope="module")
def v2():
    return load_config("quiz.v2.json")


@pytest.fixture(scope="module")
def v1():
    return load_config("quiz.v1.json")


def base_answers(**overrides):
    answers = {"q1": "q1_a", "q2": "q2_a", "q3": "q3_c", "q4": ["q4_none"], "q5": "q5_c", "q6": "q6_b", "q7": 3}
    answers.update(overrides)
    return answers


# --------------------------------------------------------------------------- kontrak & konfigurasi


def test_field_keys_match_client(v1, v2):
    assert [f["key"] for f in v2["fields"]] == CLIENT_FIELD_KEYS
    assert [f["key"] for f in v1["fields"]] == CLIENT_FIELD_KEYS


def test_no_psychological_test_terms(v2):
    text = json.dumps(v2, ensure_ascii=False).lower()
    for term in FORBIDDEN_TERMS:
        assert term not in text, term


def test_v1_max_points_match_reported_draft(v1):
    # Angka di prompt tim (Q1-Q6, Q4 semua relevan dicentang). Dihitung, bukan disalin.
    assert max_points(v1, include_major=False) == {
        "data": 12, "marketing": 11, "backend": 10, "uiux": 10, "accounting": 10, "finance": 8,
        "frontend": 7, "mobile": 6, "supply-chain": 6, "product": 5, "hr": 5, "legal": 5,
    }


def test_v1_structural_problems(v1):
    assert ("mobile", "backend") in dominated_pairs(v1)
    assert any(set(p) == {"backend", "frontend", "mobile"} for _, _, p in multi_field_options(v1))


def test_v2_is_structurally_symmetric(v2):
    assert set(max_points(v2, include_major=False).values()) == {8}
    assert set(max_points(v2, include_major=True).values()) == {9}
    assert multi_field_options(v2) == []
    assert dominated_pairs(v2) == []
    for q in v2["questions"]:
        if q["type"] == "single":
            seen = [k for o in q["options"] for k in o["points"]]
            assert sorted(seen) == sorted(CLIENT_FIELD_KEYS), f"{q['id']}: tiap bidang tepat sekali"


def test_v2_pair_repeats_documented_in_changelog(v2):
    from collections import Counter

    pairs = Counter()
    for q in v2["questions"]:
        if q["type"] == "single":
            for o in q["options"]:
                pairs[frozenset(o["points"])] += 1
    repeated = {tuple(sorted(p)) for p, n in pairs.items() if n > 1}
    assert repeated == {("accounting", "finance"), ("backend", "mobile"), ("frontend", "mobile")}


def test_config_validation_rejects_bad_configs(v2):
    bad = copy.deepcopy(v2)
    bad["questions"][0]["options"][0]["points"] = {"back_end": 2}
    with pytest.raises(QuizConfigError):
        validate_config(bad)
    bad = copy.deepcopy(v2)
    bad["questions"][0]["options"][0]["points"] = {"backend": -1}
    with pytest.raises(QuizConfigError):
        validate_config(bad)
    bad = copy.deepcopy(v2)
    q4 = next(q for q in bad["questions"] if q["id"] == "q4")
    q4["options"][-1]["points"] = {"legal": 1}
    with pytest.raises(QuizConfigError):
        validate_config(bad)


# --------------------------------------------------------------------------- validasi jawaban


@pytest.mark.parametrize(
    "answers, needle",
    [
        ({**base_answers(), "q9": "x"}, "q9"),
        (base_answers(q1="q1_z"), "q1"),
        (base_answers(q4="q4_api"), "q4"),
        (base_answers(q4=["q4_api", "q4_none"]), "Belum ada"),
        (base_answers(q4=["q4_api", "q4_api"]), "dua kali"),
        (base_answers(q4=[]), "q4"),
        (base_answers(q7=6), "q7"),
        (base_answers(q7=True), "q7"),
        (base_answers(q7="3"), "q7"),
        ({**base_answers(), "q8": 123}, "q8"),
        ({**base_answers(), "q8": "x" * 101}, "q8"),
    ],
)
def test_invalid_answers(v2, answers, needle):
    with pytest.raises(QuizAnswerError) as err:
        score_quiz(v2, answers, AT)
    assert needle in str(err.value)


def test_empty_answers_list_all_missing_required(v2):
    with pytest.raises(QuizAnswerError) as err:
        score_quiz(v2, {}, AT)
    missing = {p.split(":")[0] for p in err.value.problems}
    assert missing == {"q1", "q2", "q3", "q4", "q5", "q6", "q7"}  # q8 opsional


def test_non_dict_and_missing_timestamp(v2):
    with pytest.raises(QuizAnswerError):
        score_quiz(v2, ["q1_a"], AT)
    with pytest.raises(QuizAnswerError):
        score_quiz(v2, base_answers(), "")


# --------------------------------------------------------------------------- Q8 jurusan


@pytest.mark.parametrize("major", [None, "", "   ", "Sastra Jepang"])
def test_q8_empty_or_unmatched_is_ignored(v2, major):
    plain = score_quiz(v2, base_answers(), AT)
    answers = base_answers()
    if major is not None:
        answers["q8"] = major
    result = score_quiz(v2, answers, AT)
    assert result["quiz"] == plain["quiz"]
    assert result["suggestions"] == plain["suggestions"]
    assert set(result["meta"]["maxPoints"].values()) == {8}


def test_q8_matched_major_adds_small_points(v2):
    plain = score_quiz(v2, base_answers(), AT)
    result = score_quiz(v2, {**base_answers(), "q8": "  Akuntansi  "}, AT)
    assert result["meta"]["matchedMajorIds"] == ["akuntansi"]
    assert set(result["meta"]["maxPoints"].values()) == {9}
    for key, pts in result["meta"]["rawPoints"].items():
        assert pts - plain["meta"]["rawPoints"][key] == (1 if key in ("accounting", "finance") else 0)


def test_q8_multiple_matches_capped_at_one(v2):
    result = score_quiz(v2, {**base_answers(), "q8": "Manajemen Informatika"}, AT)
    assert result["meta"]["matchedMajorIds"] == ["informatika", "manajemen"]
    plain = score_quiz(v2, base_answers(), AT)
    deltas = {k: v - plain["meta"]["rawPoints"][k] for k, v in result["meta"]["rawPoints"].items()}
    assert max(deltas.values()) == 1
    assert deltas["product"] == 1 and deltas["backend"] == 1 and deltas["legal"] == 0


def test_dkv_does_not_match_communication_major(v2):
    result = score_quiz(v2, {**base_answers(), "q8": "Desain Komunikasi Visual"}, AT)
    assert result["meta"]["matchedMajorIds"] == ["desain"]


# --------------------------------------------------------------------------- Q4


def test_q4_check_all_is_neutral(v2):
    q4 = next(q for q in v2["questions"] if q["id"] == "q4")
    all_tools = [o["id"] for o in q4["options"] if o["id"] != "q4_none"]
    none = score_quiz(v2, base_answers(q4=["q4_none"]), AT)
    every = score_quiz(v2, base_answers(q4=all_tools), AT)
    for key in every["meta"]["rawPoints"]:
        assert every["meta"]["rawPoints"][key] - none["meta"]["rawPoints"][key] == 1


def test_q4_cap_limits_points_per_field(v2):
    cfg = copy.deepcopy(v2)
    q4 = next(q for q in cfg["questions"] if q["id"] == "q4")
    q4["options"][0]["points"] = {"backend": 3}  # tanpa batas, centang semua = +3 untuk Back-End
    validate_config(cfg)
    result = score_quiz(cfg, base_answers(q4=["q4_api"]), AT)
    plain = score_quiz(cfg, base_answers(q4=["q4_none"]), AT)
    assert result["meta"]["rawPoints"]["backend"] - plain["meta"]["rawPoints"]["backend"] == 1
    assert max_points(cfg, False)["backend"] == 8


# --------------------------------------------------------------------------- ranking, seri, klaster


def test_tie_detected_and_broken_by_strong_count(v2):
    # Back-End 4 (dua jawaban +2) dan Data 4 (satu jawaban +2): seri, strong_count memenangkan Back-End.
    result = score_quiz(v2, base_answers(), AT)
    assert result["meta"]["rawPoints"]["backend"] == 4 and result["meta"]["rawPoints"]["data"] == 4
    assert result["tieLike"] is True
    assert result["tiedFieldKeys"] == ["backend", "data"]
    assert [s["fieldKey"] for s in result["suggestions"]][:2] == ["backend", "data"]
    assert result["suggestions"][0]["percent"] == result["suggestions"][1]["percent"] == 50


def test_tie_with_equal_strength_uses_answer_rotation(v2):
    answers = base_answers(q3="q3_e", q5="q5_e", q6="q6_b")  # Data 3 dan Marketing 3, sama-sama satu +2
    result = score_quiz(v2, answers, AT)
    pts = result["meta"]["rawPoints"]
    assert pts["data"] == pts["marketing"] == 3
    offset = result["meta"]["rotationOffset"]
    keys = CLIENT_FIELD_KEYS
    rot = {k: (keys.index(k) - offset) % 12 for k in ("data", "marketing")}
    expected_first = min(rot, key=rot.get)
    assert result["suggestions"][0]["fieldKey"] == expected_first
    assert result["tieLike"] is True


def test_rotation_does_not_always_favor_the_same_field(v2):
    winners = set()
    for q7 in (1,):
        for q6 in ("q6_b", "q6_e"):
            for q1 in ("q1_a", "q1_c"):
                answers = base_answers(q1=q1, q3="q3_e", q5="q5_e", q6=q6, q7=q7)
                result = score_quiz(v2, answers, AT)
                if result["tieLike"]:
                    winners.add(result["suggestions"][0]["fieldKey"])
    assert len(winners) >= 2


def test_cluster_rule_replaces_third_tech_field_when_gap_small(v2):
    answers = base_answers(q1="q1_b", q2="q2_a", q3="q3_c", q5="q5_a", q6="q6_c")
    result = score_quiz(v2, answers, AT)
    pts = result["meta"]["rawPoints"]
    assert (pts["frontend"], pts["backend"], pts["mobile"], pts["data"]) == (5, 3, 3, 2)
    assert [s["fieldKey"] for s in result["suggestions"]] == ["frontend", "backend", "data"]
    no_rule = copy.deepcopy(v2)
    no_rule["scoring"]["diversity"] = {"type": "none"}
    assert [s["fieldKey"] for s in score_quiz(no_rule, answers, AT)["suggestions"]] == ["frontend", "backend", "mobile"]


def test_cluster_rule_keeps_third_tech_field_when_gap_large(v2):
    answers = base_answers(q1="q1_b", q2="q2_b", q3="q3_c", q4=["q4_api", "q4_web"], q5="q5_a", q6="q6_a")
    result = score_quiz(v2, answers, AT)
    pts = result["meta"]["rawPoints"]
    assert (pts["backend"], pts["frontend"], pts["mobile"], pts["accounting"]) == (6, 5, 4, 1)
    assert [s["fieldKey"] for s in result["suggestions"]] == ["backend", "frontend", "mobile"]


def test_only_fields_with_points_are_suggested(v2):
    result = score_quiz(v2, base_answers(), AT)
    for s in result["suggestions"]:
        assert result["meta"]["rawPoints"][s["fieldKey"]] > 0


# --------------------------------------------------------------------------- keluaran


def test_output_contract(v2):
    result = score_quiz(v2, {**base_answers(q7=4), "q8": "Teknik Informatika"}, AT)
    quiz = result["quiz"]
    assert set(quiz) == {"version", "answeredAt", "fieldScores", "confidence"}
    assert quiz["version"] == v2["version"] and quiz["answeredAt"] == AT and quiz["confidence"] == 4
    assert list(quiz["fieldScores"]) == CLIENT_FIELD_KEYS
    assert all(isinstance(v, int) and 0 <= v <= 100 for v in quiz["fieldScores"].values())
    assert 1 <= len(result["suggestions"]) <= 3
    for s in result["suggestions"]:
        assert s["percent"] == quiz["fieldScores"][s["fieldKey"]]
        assert s["reasonText"].startswith("Kamu ") and s["reasonText"].endswith(".")
        assert 1 <= len(s["reasons"]) <= 2


def test_percent_is_points_over_max_achievable(v2):
    result = score_quiz(v2, base_answers(), AT)
    for key, pts in result["meta"]["rawPoints"].items():
        assert result["quiz"]["fieldScores"][key] == round_half_up_percent(Fraction(pts, 8))


def test_reasons_come_from_strongest_answers(v2):
    result = score_quiz(v2, base_answers(), AT)
    top = result["suggestions"][0]
    assert top["fieldKey"] == "backend"
    assert top["reasons"] == [
        "sering menulis logika program dan menyiapkan database di tugas kelompok",
        "ingin mengecek kecepatan dan error aplikasi",
    ]


@pytest.mark.parametrize("value, expected", [(Fraction(1, 8), 13), (Fraction(5, 8), 63), (Fraction(2, 3), 67),
                                             (Fraction(1, 9), 11), (Fraction(0), 0), (Fraction(1), 100)])
def test_round_half_up_percent(value, expected):
    assert round_half_up_percent(value) == expected


def test_deterministic(v2):
    answers = {**base_answers(q4=["q4_api", "q4_figma"]), "q8": "Ilmu Hukum"}
    first = score_quiz(v2, answers, AT)
    for _ in range(5):
        assert score_quiz(v2, copy.deepcopy(answers), AT) == first


def test_v1_user_max_normalization(v1):
    answers = {"q1": "q1_a", "q2": "q2_a", "q3": "q3_c", "q4": ["q4_code"], "q5": "q5_a", "q6": "q6_a", "q7": 3}
    result = score_quiz(v1, answers, AT)
    top = result["suggestions"][0]
    assert top["fieldKey"] == "backend" and top["percent"] == 100  # bidang tertinggi = 100%
    assert result["meta"]["maxPoints"] is None


def test_vectors_file_exists_and_is_large_enough():
    data = json.loads((Path(__file__).resolve().parents[1] / "test_vectors" / "vectors.json").read_text(encoding="utf-8"))
    assert len(data["cases"]) >= 30
