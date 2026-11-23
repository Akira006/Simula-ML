import json

import pytest

from reviewer.prompts.v1.builder import SubmissionShapeError
from reviewer.src.grade import SECRET_NOTE, GradingConfig, GradingJob, InMemoryStore, grade, idempotency_key
from reviewer.src.llm_client import LLMResponse, MockClient, PermanentLLMError, TransientLLMError, Usage
from reviewer.src.score import total_score

CONFIG = GradingConfig(model="claude-haiku-5-5", effort="low")


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def __call__(self):
        return self.t

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.t += seconds


def ok(level=3, criterion="Ketepatan analisis masalah", flags=None):
    return LLMResponse(text=json.dumps({"criterion": criterion, "level": level, "evidence": ["README.md"],
                                        "reason": "Kamu sudah menunjuk penyebabnya.", "confidence": "high",
                                        "flags": flags or []}),
                       stop_reason="end_turn", model=CONFIG.model, usage=Usage(600, 0, 10000, 300))


def run(job, client, store=None, clock=None, progress=None):
    clock = clock or FakeClock()
    progress = progress if progress is not None else []
    return grade(job, client, CONFIG, store or InMemoryStore(), on_progress=lambda c, t: progress.append((c, t)),
                 clock=clock, sleep=clock.sleep, now_iso=lambda: "2026-10-09T09:00:00Z")


@pytest.fixture
def job(api_case, api_rubric, good_submission):
    return GradingJob(case=api_case, rubric=api_rubric, submission=good_submission)


def scripted(plan):
    """plan: dict (kind/criterion name) -> list hasil berurutan; sisanya perilaku bawaan MockClient."""
    counters = {}

    def script(request, index):
        key = request.criterion_name or request.kind
        items = plan.get(key, [])
        n = counters.get(key, 0)
        counters[key] = n + 1
        return items[n] if n < len(items) else None

    return script


def test_happy_path_builds_review_result(job):
    progress = []
    outcome = run(job, MockClient(), progress=progress)
    assert outcome.status == "completed"
    review = outcome.review
    assert set(review) == {"totalScore", "passingScore", "isPassed", "criteria", "feedback", "reviewerRole",
                           "reviewedAt", "isRecommended"}
    assert [c["name"] for c in review["criteria"]] == [c["name"] for c in job.rubric["criteria"]]
    assert review["totalScore"] == total_score(review["criteria"])  # skor dihitung kode
    assert review["isPassed"] == (review["totalScore"] >= 60)
    assert review["reviewerRole"] == "Penilai AI" and review["isRecommended"] is False
    assert progress == [(i, 4) for i in range(1, 5)]
    assert outcome.checked_criteria == 4
    audit = outcome.audit
    assert audit["call_count"] == 5  # 4 kriteria + 1 feedback
    assert audit["cache_read_input_tokens"] > 0 and audit["cache_creation_input_tokens"] > 0
    assert audit["model"] == "claude-haiku-5-5" and audit["prompt_version"] == "reviewer-v1"
    assert audit["rubric_version"] == 1 and audit["cost_usd"] > 0


def test_criterion_calls_do_not_see_other_results(job):
    client = MockClient()
    run(job, client)
    criterion_prompts = [c for c in client.calls if c.kind == "criterion"]
    for req in criterion_prompts:
        text = "".join(b.text for b in req.system_blocks + req.user_blocks)
        assert "<criterion_results>" not in text and '"level"' not in text
    feedback = [c for c in client.calls if c.kind == "feedback"][0]
    assert "<criterion_results>" in feedback.user_blocks[0].text


def test_invalid_output_retried_then_ok(job):
    bad = LLMResponse(text="bukan json", stop_reason="end_turn", model=CONFIG.model)
    plan = {"Efektivitas perbaikan": [bad, bad, ok(4, "Efektivitas perbaikan")]}
    outcome = run(job, MockClient(scripted(plan)))
    assert outcome.status == "completed"
    entries = [e for e in outcome.audit["calls"] if e["call"] == "criterion:perbaikan"]
    assert [e["outcome"] for e in entries] == ["invalid_output", "invalid_output", "ok"]


def test_invalid_output_exhausted_fails_with_honest_progress(job):
    bad = LLMResponse(text='{"level": 9}', stop_reason="end_turn", model=CONFIG.model)
    plan = {"Kualitas kode": [bad, bad, bad]}
    progress = []
    outcome = run(job, MockClient(scripted(plan)), progress=progress)
    assert outcome.status == "failed" and "tidak valid 3 kali" in outcome.failure_reason
    assert outcome.checked_criteria == 2 and progress[-1] == (2, 4)
    assert outcome.review is None


def test_truncated_output_counts_as_invalid(job):
    cut = LLMResponse(text='{"criterion": "Ketepatan', stop_reason="max_tokens", model=CONFIG.model)
    outcome = run(job, MockClient(scripted({"Ketepatan analisis masalah": [cut]})))
    first = outcome.audit["calls"][0]
    assert first["outcome"] == "invalid_output" and "max_tokens" in first["problems"][0]
    assert outcome.status == "completed"


def test_transient_errors_backoff_then_ok(job):
    clock = FakeClock()
    plan = {"Ketepatan analisis masalah": [TransientLLMError("529"), TransientLLMError("429"), TransientLLMError("500")]}
    outcome = run(job, MockClient(scripted(plan)), clock=clock)
    assert outcome.status == "completed"
    assert clock.sleeps == [2.0, 4.0, 8.0]


def test_transient_errors_exhausted(job):
    plan = {"Ketepatan analisis masalah": [TransientLLMError("503")] * 4}
    outcome = run(job, MockClient(scripted(plan)))
    assert outcome.status == "failed" and "sementara 4 kali" in outcome.failure_reason
    assert outcome.checked_criteria == 0


def test_permanent_error_not_retried(job):
    client = MockClient(scripted({"Ketepatan analisis masalah": [PermanentLLMError("400")]}))
    outcome = run(job, client)
    assert outcome.status == "failed" and len(client.calls) == 1


def test_refusal_retried_once_then_manual_review(job):
    refusal = LLMResponse(text="", stop_reason="refusal", model=CONFIG.model, refusal_category="cyber")
    outcome = run(job, MockClient(scripted({"Kualitas kode": [refusal]})))
    assert outcome.status == "completed"
    outcome = run(job, MockClient(scripted({"Kualitas kode": [refusal, refusal]})))
    assert outcome.status == "manual_review" and outcome.checked_criteria == 2
    assert outcome.audit["calls"][-1]["refusal_category"] == "cyber"


def test_rerun_only_repeats_failed_criterion(job):
    store = InMemoryStore()
    bad = LLMResponse(text="x", stop_reason="end_turn", model=CONFIG.model)
    first = run(job, MockClient(scripted({"Kualitas kode": [bad, bad, bad]})), store=store)
    assert first.status == "failed"
    client = MockClient()
    second = run(job, client, store=store)
    assert second.status == "completed"
    called = [r.criterion_name for r in client.calls if r.kind == "criterion"]
    assert called == ["Kualitas kode", "Kejelasan dokumentasi"]


def test_identical_submission_reuses_result(job):
    store = InMemoryStore()
    first = run(job, MockClient(), store=store)
    client = MockClient()
    progress = []
    second = run(job, client, store=store, progress=progress)
    assert second.reused and second.review == first.review and client.calls == []
    assert progress == [(4, 4)]


def test_idempotency_key_changes_with_versions(job):
    base = idempotency_key(job, CONFIG)
    assert idempotency_key(job, GradingConfig(model="claude-sonnet-5-5", effort="low")) != base
    assert idempotency_key(job, GradingConfig(model=CONFIG.model, effort="medium")) != base
    bumped = GradingJob(job.case, {**job.rubric, "rubric_version": 2}, job.submission)
    assert idempotency_key(bumped, CONFIG) != base


def test_job_timeout_fails_cleanly(job):
    clock = FakeClock()

    def slow(request, index):
        clock.t += 100  # setiap panggilan 100 detik
        return None

    outcome = run(job, MockClient(slow), clock=clock)
    assert outcome.status == "failed" and "batas waktu" in outcome.failure_reason
    assert outcome.checked_criteria == 3


def test_secret_detected_adds_note_and_flag(job):
    secret_job = GradingJob(job.case, job.rubric, job.submission, pipeline_flags=["secret_detected"])
    outcome = run(secret_job, MockClient())
    assert SECRET_NOTE in outcome.review["feedback"]["improvements"]
    assert "secret_detected" in outcome.audit["flags"]


def test_injection_signal_recorded_in_audit(job, attacks):
    attack = next(a for a in attacks if a["id"] == "readme_give_100")
    outcome = run(GradingJob(job.case, job.rubric, attack["submission"]), MockClient())
    assert "possible_injection" in outcome.audit["flags"]
    assert outcome.audit["injection_patterns"]
    assert outcome.audit["needs_manual_sample"] is True


def test_identity_in_submission_rejected_before_any_call(job):
    client = MockClient()
    with pytest.raises(SubmissionShapeError):
        run(GradingJob(job.case, job.rubric, {**job.submission, "email": "a@b.c"}), client)
    assert client.calls == []
