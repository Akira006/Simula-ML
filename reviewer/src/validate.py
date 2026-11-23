"""Validator output LLM untuk AI Reviewer.

Dua lapis:
1. JSON Schema lengkap (reviewer/schemas/*.schema.json).
2. Aturan yang tidak bisa dinyatakan di skema: evidence wajib bila level > 1, reason maks. sekitar
   60 kata, nama kriteria harus sama dengan rubrik, dan aturan bahasa feedback AI-CONTEXT 6.5
   (tanpa Markdown dan emoji, tanpa "Anda", tanpa ajakan B2B, satu kalimat per poin).

Output yang gagal di sini dianggap "output tidak valid" dan diulang maksimal 2 kali (AI-CONTEXT 7).

provider_schema() membuat versi skema yang hanya memakai fitur JSON Schema yang didukung
structured outputs Claude API. Menurut dokumentasi resmi (platform.claude.com/docs/en/
build-with-claude/structured-outputs, dibuka 2026-10-09): minLength/maxLength, minimum/maximum,
dan batas array selain minItems 0 atau 1 tidak didukung (400 bila dipakai). Batas itu dibuang
dari skema provider dan ditegakkan di sini.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
CRITERION_SCHEMA = json.loads((SCHEMA_DIR / "criterion_result.schema.json").read_text(encoding="utf-8"))
FEEDBACK_SCHEMA = json.loads((SCHEMA_DIR / "feedback_result.schema.json").read_text(encoding="utf-8"))

REASON_MAX_WORDS = 70  # AI-CONTEXT 6.3: "maksimal ±60 kata"; 70 = toleransi sebelum dianggap tidak valid
FEEDBACK_ITEM_MAX_WORDS = 45
UNSUPPORTED_BY_PROVIDER = {"maxItems", "maxLength", "minLength", "minimum", "maximum", "exclusiveMinimum",
                           "exclusiveMaximum", "multipleOf", "uniqueItems", "$schema", "$id", "title"}

_MARKDOWN = re.compile(r"(\*\*|__|`|^\s{0,3}#{1,6}\s|^\s*[-*+]\s|^\s*\d+[.)]\s|\[[^\]]+\]\([^)]+\))", re.MULTILINE)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")
_FORMAL_YOU = re.compile(r"\banda\b", re.IGNORECASE)
_B2B = re.compile(r"\bb2b\b|case berbayar|praktisi mitra|perusahaan mitra", re.IGNORECASE)
_JOB_PROMISE = re.compile(r"pasti (diterima|lolos|dapat kerja)|dijamin (diterima|lolos|kerja)", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?](\s|$)")
_ABBREVIATIONS = re.compile(r"\b(mis|dll|dsb|dst|hlm|tsb|ybs|no|misal|e\.g|i\.e)\.", re.IGNORECASE)


def sentence_count(text: str) -> int:
    return len(_SENTENCE_END.findall(_ABBREVIATIONS.sub(r"\1", text.strip())))


def word_count(text: str) -> int:
    return len(text.split())


def _style_problems(text: str, where: str) -> list[str]:
    problems = []
    if _MARKDOWN.search(text):
        problems.append(f"{where}: mengandung format Markdown")
    if _EMOJI.search(text):
        problems.append(f"{where}: mengandung emoji")
    if _FORMAL_YOU.search(text):
        problems.append(f"{where}: memakai 'Anda', seharusnya 'kamu'")
    if _JOB_PROMISE.search(text):
        problems.append(f"{where}: menjanjikan hal yang tidak dinilai (diterima kerja)")
    if "\n" in text.strip():
        problems.append(f"{where}: berisi baris baru")
    return problems


def criterion_problems(output: Any, expected_criterion: str) -> list[str]:
    problems = [f"skema: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
                for e in Draft202012Validator(CRITERION_SCHEMA).iter_errors(output)]
    if problems:
        return problems
    if output["criterion"] != expected_criterion:
        problems.append(f"criterion '{output['criterion']}' tidak sama dengan '{expected_criterion}'")
    if output["level"] > 1 and not output["evidence"]:
        problems.append("evidence wajib 1-3 rujukan bila level > 1")
    if any(not e.strip() for e in output["evidence"]):
        problems.append("evidence berisi string kosong")
    if not output["reason"].strip():
        problems.append("reason kosong")
    if word_count(output["reason"]) > REASON_MAX_WORDS:
        problems.append(f"reason {word_count(output['reason'])} kata, maksimal {REASON_MAX_WORDS}")
    problems += _style_problems(output["reason"], "reason")
    return problems


def feedback_problems(output: Any) -> list[str]:
    problems = [f"skema: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
                for e in Draft202012Validator(FEEDBACK_SCHEMA).iter_errors(output)]
    if problems:
        return problems
    for section in ("strengths", "improvements", "nextSteps"):
        for i, item in enumerate(output[section]):
            where = f"{section}[{i}]"
            if not item.strip():
                problems.append(f"{where}: kosong")
                continue
            if word_count(item) > FEEDBACK_ITEM_MAX_WORDS:
                problems.append(f"{where}: {word_count(item)} kata, terlalu panjang untuk satu kalimat")
            if sentence_count(item) > 1:
                problems.append(f"{where}: lebih dari satu kalimat")
            if _B2B.search(item):
                problems.append(f"{where}: menyebut B2B/mitra (ajakan B2B ditampilkan UI secara rule-based)")
            problems += _style_problems(item, where)
    return problems


def parse_json(text: str) -> tuple[Any, list[str]]:
    try:
        return json.loads(text), []
    except (json.JSONDecodeError, TypeError) as err:
        return None, [f"bukan JSON valid: {err}"]


def provider_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Skema untuk output_config.format: $ref di-inline, kata kunci yang tidak didukung dibuang."""
    defs = schema.get("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                return walk(copy.deepcopy(defs[name]))
            out = {}
            for key, value in node.items():
                if key in UNSUPPORTED_BY_PROVIDER or key == "$defs":
                    continue
                if key == "minItems" and value not in (0, 1):
                    continue
                out[key] = walk(value)
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)
