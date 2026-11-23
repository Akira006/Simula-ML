"""Orkestrator satu job penilaian AI Reviewer (AI-CONTEXT 6.1, 7, 8).

Alur: per kriteria BERURUTAN sesuai rubrik -> validasi -> simpan -> naikkan checkedCriteria
-> panggilan feedback -> skor dihitung kode (score.py) -> IReviewResult + catatan audit.

Kebijakan retry per panggilan (tabel AI-CONTEXT 7):
- output tidak valid (bukan JSON, gagal skema/aturan, atau terpotong max_tokens): ulangi maks. 2 kali;
- error 5xx/429/timeout/koneksi: ulangi maks. 3 kali dengan jeda bertahap (2, 4, 8 detik);
- refusal: ulangi 1 kali; bila tetap ditolak -> status manual_review;
- error 4xx lain: langsung gagal (tidak ada gunanya diulang).
Hanya kriteria yang gagal yang diulang. Hasil kriteria yang sudah valid disimpan per kriteria,
jadi job yang dijalankan ulang (setelah crash atau gagal sementara) melanjutkan dari situ.

Idempoten: kunci = hash(submission yang sudah diolah + rubric_id + rubric_version + prompt_version
+ model + effort). Job yang sama tidak menilai ulang, dan submission identik memakai hasil lama
(mencegah "mengocok ulang" skor, AI-CONTEXT 6.1 langkah 3).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from ..cost.cost_model import call_cost
from ..prompts.v1.builder import (
    PROMPT_VERSION,
    PromptRequest,
    build_criterion_request,
    build_feedback_request,
    build_submission_block,
    submission_hash,
)
from .llm_client import CallSettings, LLMClient, PermanentLLMError, TransientLLMError
from .score import is_passed, total_score
from .validate import criterion_problems, feedback_problems, parse_json

AI_REVIEWER_ROLE = "Penilai AI"  # sama dengan AI_REVIEWER_ROLE di client/src/mocks/data/reviewResults.ts
SECRET_NOTE = "Jangan menyertakan kunci rahasia seperti API key atau kata sandi di repositori, karena berkas itu kami saring dan tidak ikut dinilai."
PIPELINE_NOTES = {
    "secret_detected": SECRET_NOTE,
    "unreadable_part": "Sebagian isi submission tidak bisa dibaca dan tidak ikut dinilai. Sebutkan bagian itu di improvements bila relevan.",
}


@dataclass
class GradingConfig:
    model: str
    effort: str
    max_tokens_criterion: int = 8000
    max_tokens_feedback: int = 8000
    request_timeout_seconds: float = 90.0
    job_timeout_seconds: float = 300.0
    max_invalid_retries: int = 2
    max_transient_retries: int = 3
    max_refusal_retries: int = 1
    backoff_base_seconds: float = 2.0

    @classmethod
    def from_models_json(cls, path) -> "GradingConfig":
        data = json.loads(open(path, encoding="utf-8").read())
        return cls(model=data["active_model"], effort=data["effort"],
                   max_tokens_criterion=data["max_tokens"]["criterion"],
                   max_tokens_feedback=data["max_tokens"]["feedback"],
                   request_timeout_seconds=data["request_timeout_seconds"],
                   job_timeout_seconds=data["job_timeout_seconds"])


@dataclass
class GradingJob:
    case: dict[str, Any]
    rubric: dict[str, Any]
    submission: dict[str, Any]  # {"slots": [...], "note": str|None} hasil pipeline input, TANPA identitas
    pipeline_flags: list[str] = field(default_factory=list)


@dataclass
class GradingOutcome:
    status: str  # "completed" | "failed" | "manual_review"
    idempotency_key: str
    checked_criteria: int
    review: dict[str, Any] | None
    audit: dict[str, Any]
    failure_reason: str | None = None
    reused: bool = False


class ResultStore(Protocol):
    def get_result(self, key: str) -> GradingOutcome | None: ...
    def save_result(self, key: str, outcome: GradingOutcome) -> None: ...
    def get_criterion(self, key: str, criterion_id: str) -> dict[str, Any] | None: ...
    def save_criterion(self, key: str, criterion_id: str, result: dict[str, Any]) -> None: ...


class InMemoryStore:
    def __init__(self):
        self.results: dict[str, GradingOutcome] = {}
        self.criteria: dict[tuple[str, str], dict[str, Any]] = {}

    def get_result(self, key):
        return self.results.get(key)

    def save_result(self, key, outcome):
        self.results[key] = outcome

    def get_criterion(self, key, criterion_id):
        return self.criteria.get((key, criterion_id))

    def save_criterion(self, key, criterion_id, result):
        self.criteria[(key, criterion_id)] = result


class _JobTimeout(Exception):
    pass


def idempotency_key(job: GradingJob, config: GradingConfig) -> str:
    payload = {
        "submission": submission_hash(job.submission),
        "rubric_id": job.rubric["rubric_id"],
        "rubric_version": job.rubric["rubric_version"],
        "prompt_version": PROMPT_VERSION,
        "model": config.model,
        "effort": config.effort,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class _Caller:
    client: LLMClient
    config: GradingConfig
    deadline: float
    clock: Callable[[], float]
    sleep: Callable[[float], None]
    log: list[dict[str, Any]]

    def call(self, request: PromptRequest, validate: Callable[[Any], list[str]], max_tokens: int,
             label: str) -> tuple[str, Any]:
        """Mengembalikan ("ok", output) | ("failed", alasan) | ("manual_review", alasan)."""
        invalid = transient = refusal = 0
        settings = CallSettings(self.config.model, self.config.effort, max_tokens, self.config.request_timeout_seconds)
        while True:
            if self.clock() >= self.deadline:
                raise _JobTimeout(label)
            entry: dict[str, Any] = {"call": label, "model": self.config.model, "prompt_version": PROMPT_VERSION,
                                     "attempt": invalid + transient + refusal + 1}
            self.log.append(entry)
            try:
                response = self.client.complete(request, settings)
            except TransientLLMError as err:
                transient += 1
                entry.update(outcome="transient_error", error=str(err)[:300])
                if transient > self.config.max_transient_retries:
                    return "failed", f"{label}: error sementara {transient} kali"
                self.sleep(self.config.backoff_base_seconds * 2 ** (transient - 1))
                continue
            except PermanentLLMError as err:
                entry.update(outcome="permanent_error", error=str(err)[:300])
                return "failed", f"{label}: error permanen dari provider"

            u = response.usage
            entry.update(
                model=response.model, stop_reason=response.stop_reason, latency_ms=response.latency_ms,
                input_tokens=u.input_tokens, cache_creation_input_tokens=u.cache_creation_input_tokens,
                cache_read_input_tokens=u.cache_read_input_tokens, output_tokens=u.output_tokens,
                cost_usd=_safe_cost(self.config.model, u),
            )
            if response.stop_reason == "refusal":
                refusal += 1
                entry.update(outcome="refusal", refusal_category=response.refusal_category)
                if refusal > self.config.max_refusal_retries:
                    return "manual_review", f"{label}: model menolak menilai {refusal} kali"
                continue
            problems = ["output terpotong (max_tokens)"] if response.stop_reason == "max_tokens" else []
            output = None
            if not problems:
                output, problems = parse_json(response.text)
            if not problems:
                problems = validate(output)
            if problems:
                invalid += 1
                entry.update(outcome="invalid_output", problems=problems[:5])
                if invalid > self.config.max_invalid_retries:
                    return "failed", f"{label}: output tidak valid {invalid} kali"
                continue
            entry["outcome"] = "ok"
            return "ok", output


def _safe_cost(model: str, usage) -> float | None:
    try:
        return round(call_cost(model, usage.input_tokens, usage.output_tokens,
                               usage.cache_creation_input_tokens, usage.cache_read_input_tokens), 8)
    except KeyError:
        return None  # model tidak ada di pricing.json


def grade(job: GradingJob, client: LLMClient, config: GradingConfig, store: ResultStore,
          on_progress: Callable[[int, int], None] = lambda checked, total: None,
          clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
          now_iso: Callable[[], str] = _now_iso) -> GradingOutcome:
    key = idempotency_key(job, config)
    criteria = job.rubric["criteria"]
    previous = store.get_result(key)
    if previous is not None and previous.status == "completed":
        on_progress(len(criteria), len(criteria))
        return GradingOutcome(**{**previous.__dict__, "reused": True})

    _, signals = build_submission_block(job.submission)  # menolak field terlarang sebelum ada panggilan API
    started = clock()
    caller = _Caller(client, config, started + config.job_timeout_seconds, clock, sleep, log=[])
    results: list[dict[str, Any]] = []

    def finish(status: str, reason: str | None, review: dict[str, Any] | None) -> GradingOutcome:
        outcome = GradingOutcome(status=status, idempotency_key=key, checked_criteria=len(results), review=review,
                                 audit=_audit(job, config, caller.log, results, signals, clock() - started),
                                 failure_reason=reason)
        if status == "completed":
            store.save_result(key, outcome)
        return outcome

    try:
        for criterion in criteria:
            saved = store.get_criterion(key, criterion["id"])
            if saved is None:
                request = build_criterion_request(job.case, job.rubric, criterion["id"], job.submission)
                status, value = caller.call(request, lambda o, n=criterion["name"]: criterion_problems(o, n),
                                            config.max_tokens_criterion, f"criterion:{criterion['id']}")
                if status != "ok":
                    return finish(status, value, None)
                saved = value
                store.save_criterion(key, criterion["id"], saved)
            results.append(saved)
            on_progress(len(results), len(criteria))  # jujur: hanya setelah hasil kriteria valid tersimpan

        notes = [PIPELINE_NOTES[f] for f in job.pipeline_flags if f in PIPELINE_NOTES]
        request = build_feedback_request(job.case, job.rubric, results, notes)
        status, feedback = caller.call(request, feedback_problems, config.max_tokens_feedback, "feedback")
        if status != "ok":
            return finish(status, feedback, None)
    except _JobTimeout as err:
        return finish("failed", f"batas waktu job {config.job_timeout_seconds:.0f} detik habis saat {err}", None)

    if "secret_detected" in job.pipeline_flags:
        feedback = _ensure_secret_note(feedback)
    scored = [{"name": c["name"], "weight": c["weight"], "level": r["level"], "reason": r["reason"]}
              for c, r in zip(criteria, results)]
    score = total_score(scored)
    review = {
        "totalScore": score,
        "passingScore": job.rubric["passing_score"],
        "isPassed": is_passed(score, job.rubric["passing_score"]),
        "criteria": scored,
        "feedback": feedback,
        "reviewerRole": AI_REVIEWER_ROLE,
        "reviewedAt": now_iso(),
        "isRecommended": False,  # rekomendasi interview hanya untuk B2B
    }
    return finish("completed", None, review)


def _ensure_secret_note(feedback: dict[str, list[str]]) -> dict[str, list[str]]:
    """AI-CONTEXT 5.3: peserta diberi catatan bila berkas rahasia disaring. Ditegakkan oleh kode."""
    if any("rahasia" in item.lower() for item in feedback["improvements"]):
        return feedback
    improvements = list(feedback["improvements"])
    if len(improvements) >= 3:
        improvements[-1] = SECRET_NOTE
    else:
        improvements.append(SECRET_NOTE)
    return {**feedback, "improvements": improvements}


def _audit(job: GradingJob, config: GradingConfig, log: list[dict[str, Any]], results: list[dict[str, Any]],
           signals: dict[str, Any], duration_s: float) -> dict[str, Any]:
    flags = set(job.pipeline_flags)
    for r in results:
        flags.update(r["flags"])
    if signals.get("injection_patterns"):
        flags.add("possible_injection")
    total = lambda k: sum(e.get(k) or 0 for e in log)  # noqa: E731
    costs = [e.get("cost_usd") for e in log if "cost_usd" in e]
    confidences = [r["confidence"] for r in results]
    return {
        "model": config.model,
        "effort": config.effort,
        "prompt_version": PROMPT_VERSION,
        "rubric_id": job.rubric["rubric_id"],
        "rubric_version": job.rubric["rubric_version"],
        "submission_hash": submission_hash(job.submission),
        "calls": log,
        "call_count": len(log),
        "input_tokens": total("input_tokens"),
        "cache_creation_input_tokens": total("cache_creation_input_tokens"),
        "cache_read_input_tokens": total("cache_read_input_tokens"),
        "output_tokens": total("output_tokens"),
        "cost_usd": round(sum(c for c in costs if c is not None), 8) if costs else 0.0,
        "duration_ms": int(duration_s * 1000),
        "flags": sorted(flags),
        "confidences": confidences,
        "criterion_results": results,  # evidence, confidence, flags: untuk audit internal, tidak dikirim ke peserta
        "injection_patterns": signals.get("injection_patterns", []),
        "hidden_chars_removed": signals.get("hidden_chars_removed", 0),
        "needs_manual_sample": "low" in confidences or bool(flags),
    }
