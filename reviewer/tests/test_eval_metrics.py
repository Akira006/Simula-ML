"""Uji kode metrik dengan kasus yang jawabannya diketahui. Data di sini SINTETIS, BUKAN LABEL MANUSIA."""

import random
from pathlib import Path

import pytest

from reviewer.eval.harness import SYNTHETIC_LABEL, evaluate, load_rubrics, read_jsonl, render
from reviewer.eval.metrics import permutation_p_value, quadratic_weighted_kappa, spearman

ROOT = Path(__file__).resolve().parents[1]
RUBRICS = load_rubrics(ROOT / "rubric" / "examples")


def qwk_bruteforce(a, b, k=5):
    """Implementasi independen dari definisi (loop eksplisit), sebagai pembanding."""
    n = len(a)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[x - 1][y - 1] += 1
    ha = [sum(obs[i]) for i in range(k)]
    hb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * obs[i][j]
            den += w * ha[i] * hb[j] / n
    return 1 - num / den


def test_qwk_known_values():
    assert quadratic_weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == pytest.approx(1.0)
    assert quadratic_weighted_kappa([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == pytest.approx(-1.0)
    assert quadratic_weighted_kappa([3, 3, 3], [3, 3, 3]) == 1.0
    # Dua penilai konstan tetapi berbeda: kesepakatan tidak lebih baik dari kebetulan -> 0.
    assert quadratic_weighted_kappa([3, 3, 3], [4, 4, 4]) == pytest.approx(0.0)
    assert qwk_bruteforce([3, 3, 3], [4, 4, 4]) == pytest.approx(0.0)


def test_qwk_matches_bruteforce_on_random_data():
    rng = random.Random(1)
    for _ in range(50):
        a = [rng.randint(1, 5) for _ in range(30)]
        b = [min(5, max(1, x + rng.choice([-1, 0, 0, 1]))) for x in a]
        assert quadratic_weighted_kappa(a, b) == pytest.approx(qwk_bruteforce(a, b))


def test_qwk_matches_sklearn_if_available():
    metrics = pytest.importorskip("sklearn.metrics")
    rng = random.Random(2)
    a = [rng.randint(1, 5) for _ in range(40)]
    b = [min(5, max(1, x + rng.choice([-2, -1, 0, 1]))) for x in a]
    assert quadratic_weighted_kappa(a, b) == pytest.approx(metrics.cohen_kappa_score(a, b, weights="quadratic"))


def test_spearman_and_permutation():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert permutation_p_value(list(range(20)), list(range(20)), n_perm=500) < 0.01


def _dataset(ai_levels_by_sid):
    """4 submission rubrik API dengan label manusia tetap; AI diatur per tes."""
    human_levels = {"s1": 1, "s2": 2, "s3": 4, "s4": 5}
    crit = [c["id"] for c in RUBRICS["optimasi-api-endpoint-produk"]["criteria"]]
    subs = [{"submission_id": s, "rubric_id": "optimasi-api-endpoint-produk", "length_chars": 1000 * i,
             "clear_verdict": {"s1": "fail", "s4": "pass"}.get(s)} for i, s in enumerate(human_levels, start=1)]
    human = [{"submission_id": s, "rater_id": r, "levels": {c: lv for c in crit}}
             for s, lv in human_levels.items() for r in ("a", "b")]
    ai = [{"submission_id": s, "run": run, "levels": {c: lv for c in crit}, "calls": 5, "format_errors": 0, "flags": []}
          for s, lv in ai_levels_by_sid.items() for run in (1, 2, 3)]
    return subs, human, ai


def test_harness_perfect_agreement():
    subs, human, ai = _dataset({"s1": 1, "s2": 2, "s3": 4, "s4": 5})
    r = evaluate(RUBRICS, subs, human, ai)
    assert all(v["ai_vs_human"] == pytest.approx(1.0) for v in r["qwk"].values())
    assert r["pass_agreement"] == 1.0 and r["fatal_errors"] == []
    assert r["stability"] == {"level_agreement": 1.0, "max_total_diff": 0, "submissions": 4}
    assert r["format_error_rate"] == 0.0
    assert r["synthetic"] is False


def test_harness_detects_fatal_error_and_disagreement():
    subs, human, ai = _dataset({"s1": 4, "s2": 2, "s3": 4, "s4": 5})  # s1 jelas gagal, AI meluluskan
    r = evaluate(RUBRICS, subs, human, ai)
    assert r["fatal_errors"] == ["s1"]
    assert r["pass_agreement"] == pytest.approx(0.75)
    assert r["gates"]["fatal_errors"] is False and r["gates"]["pass_agreement"] is False


def test_harness_detects_instability_and_injection_inflation():
    subs, human, ai = _dataset({"s1": 1, "s2": 2, "s3": 4, "s4": 5})
    ai[0]["levels"] = {k: 2 for k in ai[0]["levels"]}  # run 1 s1 berbeda dari run 2-3
    subs.append({"submission_id": "s2-inj", "rubric_id": "optimasi-api-endpoint-produk", "length_chars": 2000,
                 "injection_of": "s2", "exclude_from_agreement": True})
    ai += [{"submission_id": "s2-inj", "run": n, "levels": {k: 5 for k in ai[0]["levels"]}, "calls": 5,
            "format_errors": 0, "flags": []} for n in (1, 2, 3)]
    r = evaluate(RUBRICS, subs, human, ai)
    assert r["stability"]["level_agreement"] < 1.0 and r["stability"]["max_total_diff"] == 20
    assert r["injection"]["robustness"] == 0.0
    assert r["injection"]["cases"][0] == {"submission_id": "s2-inj", "not_inflated": False, "flagged": False}


def test_synthetic_fixture_is_labelled_and_never_releasable():
    fx = ROOT / "eval" / "fixtures"
    subs = read_jsonl(fx / "synthetic_submissions.jsonl")
    human = read_jsonl(fx / "synthetic_human_labels.jsonl")
    ai = read_jsonl(fx / "synthetic_ai_runs.jsonl")
    assert all(row["label_source"] == SYNTHETIC_LABEL for row in subs + human + ai)
    report = evaluate(RUBRICS, subs, human, ai)
    text = render(report)
    assert report["synthetic"] is True
    assert SYNTHETIC_LABEL in text and "BOLEH RILIS: TIDAK" in text
    assert report["injection"]["robustness"] == 1.0 and report["injection"]["cases"][0]["flagged"]
