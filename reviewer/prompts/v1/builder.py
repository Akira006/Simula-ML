"""Perakit prompt AI Reviewer v1.

Urutan bagian dari yang paling stabil ke yang paling berubah, supaya prefix bisa di-cache:

    system  (sama untuk semua case)                      -> parameter `system`, blok 1
    case    (sama untuk semua peserta di case ini)       -> parameter `system`, blok 2, BREAKPOINT CACHE
    submission (sama untuk semua kriteria peserta ini)   -> pesan user, blok 1, BREAKPOINT CACHE
    criterion (berubah di setiap panggilan)              -> pesan user, blok 2, tidak di-cache

AI-CONTEXT 6.2 menaruh rubrik sebelum submission. Di sini kriteria ditaruh PALING AKHIR karena
itulah satu-satunya bagian yang berubah antar panggilan. Bila kriteria ada sebelum submission,
setiap panggilan mengubah prefix sebelum submission, sehingga submission (bagian terbesar,
sampai ~60 ribu token) tidak bisa dibaca dari cache. Lihat ml/docs/PROPOSED-CHANGES.md.

Keamanan:
- Hanya field yang diizinkan (slots, note) yang boleh masuk ke prompt. Identitas peserta ditolak.
- Teks peserta di-escape: tanda "<" pada teks yang mirip tag blok kita diganti "&lt;", sehingga
  peserta tidak bisa menutup <submission> dan menyisipkan "instruksi sistem".
- Karakter tak terlihat (zero-width, kontrol bidi) dibuang dan dihitung.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Any

from ...src.validate import CRITERION_SCHEMA, FEEDBACK_SCHEMA, provider_schema

PROMPT_VERSION = "reviewer-v1"
PROMPT_DIR = Path(__file__).resolve().parent

RESERVED_TAGS = (
    "submission", "slot", "note", "case", "criterion", "criterion_results", "result", "rubric_overview",
    "levels", "level", "system", "instructions", "notes", "case_summary", "context", "tasks", "evidence",
    "reason", "title", "field", "name", "weight", "look_for", "not_assessed_here", "what_is_assessed",
    "evidence_slots", "deliverable_slots", "materials_summary",
)
_TAG_LIKE = re.compile(r"<(\s*/?\s*(?:" + "|".join(RESERVED_TAGS) + r")\b)", re.IGNORECASE)
_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿]")
ALLOWED_SUBMISSION_KEYS = {"slots", "note"}
ALLOWED_SLOT_KEYS = {"id", "title", "kind", "content"}

# Pola kasar untuk sinyal injection SEBELUM LLM. Bukan pengganti instruksi sistem; hanya mencatat flag.
INJECTION_PATTERNS = [
    r"abaikan\s+(semua\s+|seluruh\s+)?(instruksi|perintah|rubrik|aturan)",
    r"ignore\s+(all\s+|any\s+|the\s+|previous\s+|above\s+)*(instructions|rubric|rules)",
    r"(beri|berikan|kasih)\s+(saya\s+|aku\s+)?(nilai|skor|level)\s+(100|5|sempurna|maksimal|tertinggi)",
    r"(give|assign)\s+(me\s+)?(a\s+)?(score|grade|level)\s+(of\s+)?(100|5|full|maximum|perfect)",
    r"(kamu|anda)\s+sekarang\s+(adalah|menjadi)",
    r"you\s+are\s+now\b",
    r"(catatan|pesan|note|message)\s+(untuk|kepada|for|to)\s+(penilai|reviewer|grader)\s*(ai|llm)?",
    r"system\s*prompt|prompt\s+sistem",
    r"\bto\s+the\s+ai\b|\buntuk\s+ai\b",
]
_INJECTION = re.compile("|".join(f"(?:{p})" for p in INJECTION_PATTERNS), re.IGNORECASE)


class SubmissionShapeError(ValueError):
    """Submission berisi field yang tidak boleh masuk ke prompt (misalnya identitas peserta)."""


@dataclass(frozen=True)
class Block:
    text: str
    cache: bool = False


@dataclass
class PromptRequest:
    kind: str  # "criterion" | "feedback"
    system_blocks: list[Block]
    user_blocks: list[Block]
    output_schema: dict[str, Any]
    criterion_name: str | None = None
    prompt_version: str = PROMPT_VERSION
    signals: dict[str, Any] = field(default_factory=dict)

    def prefix_hash(self) -> str:
        """Hash bagian yang di-cache (untuk log dan MockClient)."""
        cached = [b.text for b in self.system_blocks] + [b.text for b in self.user_blocks if b.cache]
        return hashlib.sha256("\x00".join(cached).encode("utf-8")).hexdigest()[:16]


def _template(name: str) -> Template:
    return Template((PROMPT_DIR / name).read_text(encoding="utf-8"))


def escape_data(text: str) -> tuple[str, int]:
    """Netralkan teks peserta. Mengembalikan (teks, jumlah karakter tak terlihat yang dibuang)."""
    cleaned, removed = _INVISIBLE.subn("", text)
    return _TAG_LIKE.sub(r"&lt;\1", cleaned), removed


def _esc(text: str) -> str:
    return escape_data(text)[0]


def _attr(text: str) -> str:
    return html.escape(_INVISIBLE.sub("", text), quote=True)


def injection_signals(text: str) -> list[str]:
    return sorted({m.group(0).strip().lower() for m in _INJECTION.finditer(_INVISIBLE.sub("", text))})


def system_text() -> str:
    return (PROMPT_DIR / "system.md").read_text(encoding="utf-8").strip()


def build_case_block(case: dict[str, Any], rubric: dict[str, Any]) -> str:
    slots = "\n".join(f"- {s['title']} ({s['kind']}): {s.get('description', '')}".rstrip(": ") for s in rubric["slots"])
    criteria = "\n".join(f"- {c['name']} (bobot {c['weight']}): {c['description']}" for c in rubric["criteria"])
    tasks = "\n".join(f"{i}. {t['title']}: {t['description']}" for i, t in enumerate(case["tasks"], start=1))
    return _template("case.md").substitute(
        title=_esc(case["title"]),
        field_label=_esc(case["field_label"]),
        context=_esc("\n".join(case["context"])),
        tasks=_esc(tasks),
        materials=_esc("\n".join(f"- {m}" for m in case.get("materials_summary", [])) or "-"),
        slots=_esc(slots),
        criteria_count=len(rubric["criteria"]),
        criteria=_esc(criteria),
    ).strip()


def build_submission_block(submission: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    extra = set(submission) - ALLOWED_SUBMISSION_KEYS
    if extra:
        raise SubmissionShapeError(f"Field tidak boleh masuk prompt: {sorted(extra)}")
    parts = ["<submission>"]
    removed_total = 0
    raw_text = []
    for slot in submission["slots"]:
        extra = set(slot) - ALLOWED_SLOT_KEYS
        if extra:
            raise SubmissionShapeError(f"Field slot tidak boleh masuk prompt: {sorted(extra)}")
        content, removed = escape_data(slot["content"])
        removed_total += removed
        raw_text.append(slot["content"])
        parts.append(f'<slot id="{_attr(slot["id"])}" name="{_attr(slot["title"])}" kind="{_attr(slot["kind"])}">')
        parts.append(content)
        parts.append("</slot>")
    note = (submission.get("note") or "").strip()
    if note:
        content, removed = escape_data(note)
        removed_total += removed
        raw_text.append(note)
        parts += ["<note>", content, "</note>"]
    parts.append("</submission>")
    signals = {
        "hidden_chars_removed": removed_total,
        "injection_patterns": injection_signals("\n".join(raw_text)),
    }
    return "\n".join(parts), signals


def build_criterion_block(criterion: dict[str, Any], rubric: dict[str, Any]) -> str:
    slot_titles = {s["id"]: s["title"] for s in rubric["slots"]}
    bullets = lambda items: "\n".join(f"- {x}" for x in items) or "-"  # noqa: E731
    return _template("criterion.md").substitute(
        name=_esc(criterion["name"]),
        weight=criterion["weight"],
        description=_esc(criterion["description"]),
        evidence_slots=_esc(", ".join(slot_titles[s] for s in criterion["evidence_slots"])),
        look_for=_esc(bullets(criterion.get("look_for", []))),
        out_of_scope=_esc(bullets(criterion.get("out_of_scope", []))),
        **{f"level_{i}": _esc(criterion["levels"][str(i)]) for i in range(1, 6)},
    ).strip()


def build_criterion_request(case: dict[str, Any], rubric: dict[str, Any], criterion_id: str,
                            submission: dict[str, Any]) -> PromptRequest:
    criterion = next(c for c in rubric["criteria"] if c["id"] == criterion_id)
    submission_block, signals = build_submission_block(submission)
    return PromptRequest(
        kind="criterion",
        system_blocks=[Block(system_text()), Block(build_case_block(case, rubric), cache=True)],
        user_blocks=[Block(submission_block, cache=True), Block(build_criterion_block(criterion, rubric))],
        output_schema=provider_schema(CRITERION_SCHEMA),
        criterion_name=criterion["name"],
        signals=signals,
    )


def build_feedback_request(case: dict[str, Any], rubric: dict[str, Any], results: list[dict[str, Any]],
                           notes: list[str]) -> PromptRequest:
    """Panggilan feedback TIDAK menyertakan submission utuh, hanya hasil per kriteria + bukti.

    Alasannya: skema output feedback berbeda dari skema kriteria, dan mengganti output_config.format
    membatalkan prompt cache (dokumentasi structured outputs), sehingga submission akan dibayar
    penuh lagi. Bukti per kriteria sudah merujuk bagian submission yang relevan.
    """
    weights = {c["name"]: c["weight"] for c in rubric["criteria"]}
    lines = []
    for r in results:
        evidence = "\n".join(f"- {_esc(e)}" for e in r["evidence"]) or "-"
        lines.append(
            f'<result criterion="{_attr(r["criterion"])}" weight="{weights[r["criterion"]]}" level="{r["level"]}">\n'
            f"<reason>{_esc(r['reason'])}</reason>\n<evidence>\n{evidence}\n</evidence>\n</result>"
        )
    text = _template("feedback.md").substitute(
        title=_esc(case["title"]),
        field_label=_esc(case["field_label"]),
        context=_esc("\n".join(case["context"])),
        results="\n".join(lines),
        notes=_esc("\n".join(f"- {n}" for n in notes) or "-"),
    ).strip()
    return PromptRequest(
        kind="feedback",
        system_blocks=[Block((PROMPT_DIR / "feedback_system.md").read_text(encoding="utf-8").strip())],
        user_blocks=[Block(text)],
        output_schema=provider_schema(FEEDBACK_SCHEMA),
    )


def submission_hash(submission: dict[str, Any]) -> str:
    """Hash isi submission yang sudah diolah (untuk hasil ulang submission identik, AI-CONTEXT 6.1)."""
    canonical = json.dumps({"slots": submission["slots"], "note": (submission.get("note") or "").strip()},
                           sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
