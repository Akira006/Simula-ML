"""Memuat dan memvalidasi konfigurasi kuis minat (quiz.v*.json).

Validasi di sini menjaga invarian yang diandalkan fungsi skoring: id unik, fieldKey dikenal,
bobot bilangan bulat >= 0, dan opsi eksklusif Q4 tidak memberi poin.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

SCORING_TYPES = ("single", "multi", "major")
VALID_NORMALIZATION = ("max_achievable", "user_max")
VALID_TIE_BREAK = ("field_order", "strong_count", "answer_rotation")


class QuizConfigError(ValueError):
    """Konfigurasi kuis tidak valid."""


def load_config(name_or_path: str | Path = "quiz.v2.json") -> dict[str, Any]:
    path = Path(name_or_path)
    if not path.is_absolute() and not path.exists():
        path = CONFIG_DIR / path
    with path.open(encoding="utf-8") as fh:
        config = json.load(fh)
    validate_config(config)
    return config


def field_keys(config: dict[str, Any]) -> list[str]:
    return [field["key"] for field in config["fields"]]


def validate_config(config: dict[str, Any]) -> None:
    keys = field_keys(config)
    if len(keys) != len(set(keys)):
        raise QuizConfigError("fieldKey duplikat di 'fields'.")
    known = set(keys)

    scoring = config["scoring"]
    if scoring["normalization"] not in VALID_NORMALIZATION:
        raise QuizConfigError(f"normalization tidak dikenal: {scoring['normalization']}")
    for rule in scoring["tie_break"]:
        if rule not in VALID_TIE_BREAK:
            raise QuizConfigError(f"tie_break tidak dikenal: {rule}")
    if not isinstance(scoring["tie_margin_points"], int) or scoring["tie_margin_points"] < 0:
        raise QuizConfigError("tie_margin_points harus bilangan bulat >= 0.")

    question_ids: set[str] = set()
    option_ids: set[str] = set()
    for question in config["questions"]:
        qid = question["id"]
        if qid in question_ids:
            raise QuizConfigError(f"id soal duplikat: {qid}")
        question_ids.add(qid)
        qtype = question["type"]
        if qtype not in (*SCORING_TYPES, "scale"):
            raise QuizConfigError(f"{qid}: tipe soal tidak dikenal: {qtype}")
        if qtype in ("single", "multi"):
            if len(question["options"]) < 2:
                raise QuizConfigError(f"{qid}: minimal 2 opsi.")
            exclusive = set(question.get("exclusive_option_ids", []))
            for option in question["options"]:
                oid = option["id"]
                if oid in option_ids:
                    raise QuizConfigError(f"id opsi duplikat: {oid}")
                option_ids.add(oid)
                _validate_points(option["points"], known, f"{qid}/{oid}")
                if oid in exclusive and option["points"]:
                    raise QuizConfigError(f"{qid}/{oid}: opsi eksklusif tidak boleh memberi poin.")
                if option["points"] and not option.get("reason"):
                    raise QuizConfigError(f"{qid}/{oid}: opsi berpoin wajib punya 'reason'.")
            cap = question.get("per_field_cap")
            if qtype == "multi" and cap is not None and (not isinstance(cap, int) or cap < 1):
                raise QuizConfigError(f"{qid}: per_field_cap harus null atau bilangan bulat >= 1.")
    if sum(1 for q in config["questions"] if q["type"] == "major") > 1:
        raise QuizConfigError("Maksimal satu soal bertipe 'major'.")

    for cluster in config.get("clusters", []):
        unknown = set(cluster["fields"]) - known
        if unknown:
            raise QuizConfigError(f"Klaster {cluster['id']} berisi fieldKey tidak dikenal: {unknown}")
    for entry in config.get("major_mapping", []):
        _validate_points(entry["points"], known, f"major_mapping/{entry['id']}")
        if not entry["keywords"]:
            raise QuizConfigError(f"major_mapping/{entry['id']}: keywords kosong.")


def _validate_points(points: dict[str, Any], known: set[str], where: str) -> None:
    for key, value in points.items():
        if key not in known:
            raise QuizConfigError(f"{where}: fieldKey tidak dikenal: {key}")
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise QuizConfigError(f"{where}: bobot harus bilangan bulat >= 0 (dapat {value!r}).")
