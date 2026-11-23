"""Klien LLM untuk AI Reviewer: satu interface, dua implementasi.

- MockClient: deterministik, tanpa jaringan, untuk tes dan pengembangan. Bisa diberi skenario
  (output tidak valid, error 5xx/429, refusal) untuk menguji retry di grade.py.
- AnthropicClient: Claude API lewat SDK resmi `anthropic`. Aktif HANYA bila ANTHROPIC_API_KEY ada.

Parameter API diambil dari dokumentasi resmi yang dibuka 2026-10-09 (bukan dari ingatan):
- Structured outputs: `output_config={"format": {"type": "json_schema", "schema": ...}}`
  (platform.claude.com/docs/en/build-with-claude/structured-outputs). `effort` juga di dalam
  `output_config`.
- Prompt caching: `cache_control={"type": "ephemeral"}` pada blok teks, maks. 4 breakpoint, TTL
  default 5 menit, minimum 512 token untuk Haiku 5.5 / Sonnet 5.5 / Opus 5.5. Usage:
  input_tokens (setelah breakpoint terakhir), cache_creation_input_tokens, cache_read_input_tokens
  (platform.claude.com/docs/en/build-with-claude/prompt-caching).
- Refusal: HTTP 200 dengan `stop_reason == "refusal"` dan `stop_details.category`.
- Versi SDK yang dikunci: anthropic==1.12.1 (requirements.txt). Klien ini BELUM pernah dijalankan
  terhadap API sungguhan karena tidak ada API key di lingkungan pengembangan.

Sengaja TIDAK memakai parameter `fallbacks` (fallback otomatis ke model lain saat refusal):
penilaian harus memakai satu model yang dikunci dan tercatat (AI-CONTEXT 9). Refusal ditangani
grade.py sesuai tabel AI-CONTEXT 7 (ulangi sekali, lalu tinjau manual).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from ..prompts.v1.builder import PromptRequest


class TransientLLMError(Exception):
    """Timeout, error 5xx, 429, atau gangguan koneksi: boleh diulang dengan jeda."""


class PermanentLLMError(Exception):
    """Error 4xx selain 429 (permintaan salah, kunci salah): jangan diulang."""


@dataclass
class Usage:
    input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 0

    def total_input(self) -> int:
        return self.input_tokens + self.cache_creation_input_tokens + self.cache_read_input_tokens


@dataclass
class LLMResponse:
    text: str
    stop_reason: str  # "end_turn" | "max_tokens" | "refusal" | lainnya
    model: str
    usage: Usage = field(default_factory=Usage)
    latency_ms: int = 0
    refusal_category: str | None = None


@dataclass
class CallSettings:
    model: str
    effort: str
    max_tokens: int
    timeout_seconds: float = 90.0


class LLMClient(Protocol):
    def complete(self, request: PromptRequest, settings: CallSettings) -> LLMResponse: ...


def approx_tokens(text: str) -> int:
    """Perkiraan kasar untuk MockClient saja (~4 karakter per token). Bukan untuk penagihan."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# MockClient
# ---------------------------------------------------------------------------

Script = Callable[[PromptRequest, int], "LLMResponse | Exception | None"]


class MockClient:
    """Klien palsu yang deterministik.

    Tanpa skenario: mengembalikan output valid. Level ditentukan dari hash (kriteria + submission),
    sehingga input sama selalu menghasilkan level sama. Usage meniru caching: prefix yang sama
    dengan panggilan sebelumnya dihitung sebagai cache read.

    `script(request, call_index)` boleh mengembalikan LLMResponse, Exception (akan di-raise),
    atau None (pakai perilaku bawaan).
    """

    def __init__(self, script: Script | None = None, model_name: str | None = None):
        self.script = script
        self.model_name = model_name
        self.calls: list[PromptRequest] = []
        self._seen_prefixes: set[str] = set()

    def complete(self, request: PromptRequest, settings: CallSettings) -> LLMResponse:
        index = len(self.calls)
        self.calls.append(request)
        if self.script:
            outcome = self.script(request, index)
            if isinstance(outcome, Exception):
                raise outcome
            if outcome is not None:
                return outcome
        return LLMResponse(
            text=json.dumps(self._default_output(request), ensure_ascii=False),
            stop_reason="end_turn",
            model=self.model_name or settings.model,
            usage=self._usage(request),
            latency_ms=1,
        )

    def _usage(self, request: PromptRequest) -> Usage:
        cached = sum(approx_tokens(b.text) for b in request.system_blocks) + sum(
            approx_tokens(b.text) for b in request.user_blocks if b.cache)
        uncached = sum(approx_tokens(b.text) for b in request.user_blocks if not b.cache)
        has_breakpoint = any(b.cache for b in request.system_blocks + request.user_blocks)
        if not has_breakpoint:
            return Usage(input_tokens=cached + uncached, output_tokens=150)
        key = request.prefix_hash()
        if key in self._seen_prefixes:
            return Usage(input_tokens=uncached, cache_read_input_tokens=cached, output_tokens=150)
        self._seen_prefixes.add(key)
        return Usage(input_tokens=uncached, cache_creation_input_tokens=cached, output_tokens=150)

    @staticmethod
    def _default_output(request: PromptRequest) -> dict[str, Any]:
        if request.kind == "feedback":
            return {
                "strengths": ["Kamu menjelaskan bagian utama solusi dengan runtut."],
                "improvements": ["Tambahkan pengukuran sebelum dan sesudah supaya klaim perbaikanmu bisa diperiksa."],
                "nextSteps": ["Latih cara membaca query plan dengan contoh query sederhana."],
            }
        submission = next(b.text for b in request.user_blocks if b.cache)
        digest = hashlib.sha256(f"{request.criterion_name}|{submission}".encode("utf-8")).digest()
        level = digest[0] % 5 + 1
        return {
            "criterion": request.criterion_name,
            "level": level,
            "evidence": [] if level == 1 else ["Penjelasan solusi: bagian yang relevan dengan kriteria ini"],
            "reason": "Kamu sudah menyinggung bagian yang dinilai, tetapi buktinya belum lengkap.",
            "confidence": "medium",
            "flags": ["possible_injection"] if request.signals.get("injection_patterns") else [],
        }


# ---------------------------------------------------------------------------
# AnthropicClient
# ---------------------------------------------------------------------------


class AnthropicClient:
    """Claude API. Hanya bisa dibuat bila ANTHROPIC_API_KEY tersedia.

    Retry bawaan SDK dimatikan (max_retries=0) supaya jumlah percobaan dikendalikan grade.py
    persis sesuai tabel AI-CONTEXT 7 dan tercatat di log.
    """

    def __init__(self, sdk_client: Any | None = None):
        if sdk_client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY tidak diset. Pakai MockClient untuk pengembangan dan tes.")
            import anthropic  # impor di sini: paket tidak wajib untuk tes

            sdk_client = anthropic.Anthropic(max_retries=0)
        self._client = sdk_client

    @staticmethod
    def build_params(request: PromptRequest, settings: CallSettings) -> dict[str, Any]:
        def blocks(items):
            out = []
            for b in items:
                block: dict[str, Any] = {"type": "text", "text": b.text}
                if b.cache:
                    block["cache_control"] = {"type": "ephemeral"}
                out.append(block)
            return out

        return {
            "model": settings.model,
            "max_tokens": settings.max_tokens,
            "system": blocks(request.system_blocks),
            "messages": [{"role": "user", "content": blocks(request.user_blocks)}],
            "output_config": {
                "effort": settings.effort,
                "format": {"type": "json_schema", "schema": request.output_schema},
            },
        }

    def complete(self, request: PromptRequest, settings: CallSettings) -> LLMResponse:
        try:
            import anthropic as sdk
        except ImportError:  # hanya terjadi bila sdk_client palsu dipakai di tes tanpa paket anthropic
            sdk = None

        params = self.build_params(request, settings)
        started = time.monotonic()
        try:
            response = self._client.with_options(timeout=settings.timeout_seconds).messages.create(**params)
        except Exception as err:
            if sdk is None:
                raise
            if isinstance(err, sdk.RateLimitError):
                raise TransientLLMError(f"429: {err}") from err
            if isinstance(err, sdk.APIStatusError):
                if err.status_code >= 500:
                    raise TransientLLMError(f"{err.status_code}: {err}") from err
                raise PermanentLLMError(f"{err.status_code}: {err}") from err
            if isinstance(err, sdk.APIConnectionError):  # termasuk APITimeoutError
                raise TransientLLMError(f"koneksi/timeout: {err}") from err
            raise
        latency = int((time.monotonic() - started) * 1000)

        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        usage = response.usage
        details = getattr(response, "stop_details", None)
        return LLMResponse(
            text=text,
            stop_reason=response.stop_reason,
            model=response.model,
            usage=Usage(
                input_tokens=usage.input_tokens or 0,
                cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
                cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                output_tokens=usage.output_tokens or 0,
            ),
            latency_ms=latency,
            refusal_category=getattr(details, "category", None) if response.stop_reason == "refusal" else None,
        )


def make_client() -> LLMClient:
    """AnthropicClient bila ANTHROPIC_API_KEY ada, selain itu MockClient."""
    return AnthropicClient() if os.environ.get("ANTHROPIC_API_KEY") else MockClient()
