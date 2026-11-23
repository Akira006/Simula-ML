"""Skoring kuis minat: implementasi referensi (fungsi murni, deterministik, tanpa I/O).

Implementasi TypeScript/Go nanti wajib menghasilkan keluaran identik untuk semua kasus di
test_vectors/vectors.json. Karena itu semua perbandingan memakai pecahan eksak (Fraction),
bukan float, dan pembulatan persen didefinisikan dengan aritmetika bilangan bulat.

Kenapa normalisasi memakai poin MAKSIMUM YANG DAPAT DICAPAI tiap bidang, bukan skor tertinggi
pengguna (draf v1, AI-CONTEXT 14.4):
- Membagi semua bidang dengan skor tertinggi si pengguna hanya mengubah skala, bukan urutan.
  Bidang yang punya lebih banyak peluang dapat poin tetap unggul, jadi bias tidak hilang.
- Membagi tiap bidang dengan maksimumnya sendiri berarti "berapa persen dari poin yang mungkin
  untuk bidang ini sudah kamu dapat". Bidang dengan peluang poin kecil (misalnya Legal di v1)
  tidak lagi kalah hanya karena jumlah opsinya sedikit.
- Di v2 strukturnya sudah dibuat simetris (maksimum semua bidang sama), sehingga normalisasi ini
  menjadi jaring pengaman bila bobot diubah nanti, dan membuat angka persen bermakna.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from .config import field_keys

MAX_MAJOR_LENGTH = 100  # sama dengan batas zod di client/src/app/onboarding/_schema.ts
MAJOR_REASON = "punya jurusan yang berdekatan dengan bidang ini"


class QuizAnswerError(ValueError):
    """Jawaban kuis tidak valid. `problems` berisi daftar masalah per soal."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


# ---------------------------------------------------------------------------
# Utilitas yang juga dipakai analisis dan simulasi
# ---------------------------------------------------------------------------


def normalize_major(text: str) -> str:
    return " ".join(text.lower().split())


def match_major(config: dict[str, Any], major: str | None) -> list[dict[str, Any]]:
    """Entri major_mapping yang cocok (substring kata kunci pada teks yang dinormalisasi)."""
    if not major:
        return []
    norm = normalize_major(major)
    if not norm:
        return []
    return [entry for entry in config.get("major_mapping", []) if any(k in norm for k in entry["keywords"])]


def _major_question(config: dict[str, Any]) -> dict[str, Any] | None:
    return next((q for q in config["questions"] if q["type"] == "major"), None)


def max_points(config: dict[str, Any], include_major: bool) -> dict[str, int]:
    """Poin maksimum yang dapat dicapai tiap bidang, dihitung langsung dari konfigurasi."""
    keys = field_keys(config)
    totals = dict.fromkeys(keys, 0)
    for question in config["questions"]:
        qtype = question["type"]
        if qtype == "single":
            for key in keys:
                totals[key] += max(opt["points"].get(key, 0) for opt in question["options"])
        elif qtype == "multi":
            exclusive = set(question.get("exclusive_option_ids", []))
            cap = question.get("per_field_cap")
            for key in keys:
                raw = sum(o["points"].get(key, 0) for o in question["options"] if o["id"] not in exclusive)
                totals[key] += raw if cap is None else min(cap, raw)
        elif qtype == "major" and include_major:
            cap = question.get("per_field_cap")
            for key in keys:
                best = max((e["points"].get(key, 0) for e in config.get("major_mapping", [])), default=0)
                totals[key] += best if cap is None else min(cap, best)
    return totals


def round_half_up_percent(value: Fraction) -> int:
    """round(100 * value) dengan setengah dibulatkan ke atas, memakai bilangan bulat saja."""
    num, den = value.numerator * 100, value.denominator
    return (2 * num + den) // (2 * den)


# ---------------------------------------------------------------------------
# Validasi jawaban
# ---------------------------------------------------------------------------


def validate_answers(config: dict[str, Any], answers: Any) -> None:
    if not isinstance(answers, dict):
        raise QuizAnswerError(["Jawaban harus berupa objek {idSoal: jawaban}."])
    problems: list[str] = []
    questions = {q["id"]: q for q in config["questions"]}
    for key in answers:
        if key not in questions:
            problems.append(f"{key}: soal tidak dikenal.")
    for qid, question in questions.items():
        qtype = question["type"]
        value = answers.get(qid)
        if qtype == "single":
            if value is None:
                problems.append(f"{qid}: wajib dijawab.")
            elif not isinstance(value, str) or value not in {o["id"] for o in question["options"]}:
                problems.append(f"{qid}: opsi tidak dikenal: {value!r}.")
        elif qtype == "multi":
            if value is None or (isinstance(value, list) and not value):
                problems.append(f"{qid}: pilih minimal satu opsi (atau 'Belum ada').")
                continue
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                problems.append(f"{qid}: jawaban harus daftar id opsi.")
                continue
            valid_ids = {o["id"] for o in question["options"]}
            unknown = [v for v in value if v not in valid_ids]
            if unknown:
                problems.append(f"{qid}: opsi tidak dikenal: {unknown}.")
            if len(set(value)) != len(value):
                problems.append(f"{qid}: opsi tidak boleh dipilih dua kali.")
            exclusive = set(question.get("exclusive_option_ids", []))
            if exclusive & set(value) and len(value) > 1:
                problems.append(f"{qid}: 'Belum ada' tidak boleh digabung dengan opsi lain.")
        elif qtype == "scale":
            if isinstance(value, bool) or not isinstance(value, int) or not question["min"] <= value <= question["max"]:
                problems.append(f"{qid}: harus bilangan bulat {question['min']}-{question['max']}.")
        elif qtype == "major":
            if value is not None and not isinstance(value, str):
                problems.append(f"{qid}: jurusan harus teks atau kosong.")
            elif isinstance(value, str) and len(value.strip()) > MAX_MAJOR_LENGTH:
                problems.append(f"{qid}: jurusan maksimal {MAX_MAJOR_LENGTH} karakter.")
    if problems:
        raise QuizAnswerError(problems)


# ---------------------------------------------------------------------------
# Skoring
# ---------------------------------------------------------------------------


def _answer_rotation_offset(config: dict[str, Any], answers: dict[str, Any]) -> int:
    """Pergeseran urutan tie-break dari jawaban: deterministik, tidak memihak bidang tertentu.

    offset = jumlah (posisi soal, mulai 1) x (indeks opsi terpilih, mulai 1) untuk soal single
    dan multi, modulo jumlah bidang. Soal scale dan major tidak ikut.
    """
    total = 0
    for position, question in enumerate(config["questions"], start=1):
        if question["type"] not in ("single", "multi"):
            continue
        selected = answers[question["id"]]
        selected = [selected] if isinstance(selected, str) else selected
        index_of = {o["id"]: i for i, o in enumerate(question["options"], start=1)}
        total += sum(position * index_of[oid] for oid in selected)
    return total % len(config["fields"])


def score_quiz(config: dict[str, Any], answers: dict[str, Any], answered_at: str) -> dict[str, Any]:
    """Hitung saran bidang dari jawaban. `answered_at` diberikan pemanggil (fungsi ini tanpa jam)."""
    if not isinstance(answered_at, str) or not answered_at:
        raise QuizAnswerError(["answered_at wajib berupa string ISO."])
    validate_answers(config, answers)

    keys = field_keys(config)
    labels = {f["key"]: f["label"] for f in config["fields"]}
    scoring = config["scoring"]

    points = dict.fromkeys(keys, 0)
    strong = dict.fromkeys(keys, 0)
    contributions: dict[str, list[tuple[int, int, str]]] = {k: [] for k in keys}  # (poin, posisi, alasan)
    confidence = None
    matched_majors: list[dict[str, Any]] = []

    for position, question in enumerate(config["questions"], start=1):
        qtype = question["type"]
        value = answers.get(question["id"])
        if qtype == "single":
            option = next(o for o in question["options"] if o["id"] == value)
            for key, pts in option["points"].items():
                if pts:
                    points[key] += pts
                    strong[key] += pts >= 2
                    contributions[key].append((pts, position, option["reason"]))
        elif qtype == "multi":
            cap = question.get("per_field_cap")
            raw = dict.fromkeys(keys, 0)
            for option in (o for o in question["options"] if o["id"] in value):
                for key, pts in option["points"].items():
                    if pts:
                        raw[key] += pts
                        contributions[key].append((pts if cap is None else min(cap, pts), position, option["reason"]))
            for key in keys:
                points[key] += raw[key] if cap is None else min(cap, raw[key])
        elif qtype == "scale":
            confidence = value
        elif qtype == "major":
            matched_majors = match_major(config, value)
            cap = question.get("per_field_cap")
            for key in keys:
                best = max((e["points"].get(key, 0) for e in matched_majors), default=0)
                best = best if cap is None else min(cap, best)
                if best:
                    points[key] += best
                    contributions[key].append((best, position, MAJOR_REASON))

    if scoring["normalization"] == "max_achievable":
        maxima = max_points(config, include_major=bool(matched_majors))
        scores = {k: Fraction(points[k], maxima[k]) if maxima[k] else Fraction(0) for k in keys}
        ref = max(maxima.values())
    else:  # user_max: draf v1, bidang tertinggi = 100%
        maxima = None
        top_points = max(points.values())
        scores = {k: Fraction(points[k], top_points) if top_points else Fraction(0) for k in keys}
        ref = top_points

    offset = _answer_rotation_offset(config, answers)
    index = {k: i for i, k in enumerate(keys)}

    def sort_key(key: str) -> tuple:
        parts: list[Any] = [-scores[key]]
        for rule in scoring["tie_break"]:
            if rule == "strong_count":
                parts.append(-strong[key])
            elif rule == "answer_rotation":
                parts.append((index[key] - offset) % len(keys))
            elif rule == "field_order":
                parts.append(index[key])
        parts.append(index[key])  # urutan total terakhir, agar hasil selalu deterministik
        return tuple(parts)

    order = sorted((k for k in keys if points[k] > 0), key=sort_key)
    top = _apply_diversity(config, order, scores, ref)

    margin = scoring["tie_margin_points"]
    tied = [k for k in top if (scores[top[0]] - scores[k]) * ref <= margin] if top else []
    tie_like = len(tied) >= 2

    suggestions = []
    for key in top:
        reasons = _pick_reasons(contributions[key], scoring["max_reasons"])
        suggestions.append(
            {
                "fieldKey": key,
                "label": labels[key],
                "percent": round_half_up_percent(scores[key]),
                "reasons": reasons,
                "reasonText": _render_reason(reasons),
            }
        )

    return {
        "quiz": {
            "version": config["version"],
            "answeredAt": answered_at,
            "fieldScores": {k: round_half_up_percent(scores[k]) for k in keys},
            "confidence": confidence,
        },
        "suggestions": suggestions,
        "tieLike": tie_like,
        "tiedFieldKeys": tied if tie_like else [],
        "meta": {
            "rawPoints": points,
            "maxPoints": maxima,
            "matchedMajorIds": [e["id"] for e in matched_majors],
            "rotationOffset": offset,
        },
    }


def _apply_diversity(config: dict[str, Any], order: list[str], scores: dict[str, Fraction], ref: int) -> list[str]:
    """Ambil top-N; bila aturan klaster aktif, batasi jumlah bidang sekelompok kecuali selisihnya besar."""
    top_n = config["scoring"]["top_n"]
    rule = config["scoring"]["diversity"]
    if rule["type"] == "none":
        return order[:top_n]
    if rule["type"] != "max_per_cluster":
        raise ValueError(f"diversity.type tidak dikenal: {rule['type']}")

    cluster_of = {f: c["id"] for c in config.get("clusters", []) for f in c["fields"]}
    limit, gap_points = rule["max"], rule["override_gap_points"]
    selected: list[str] = []
    remaining = list(order)

    def violates(key: str) -> bool:
        cluster = cluster_of.get(key)
        return cluster is not None and sum(cluster_of.get(s) == cluster for s in selected) >= limit

    while remaining and len(selected) < top_n:
        candidate = remaining.pop(0)
        if violates(candidate):
            alternative = next((r for r in remaining if not violates(r)), None)
            if alternative is not None and (scores[candidate] - scores[alternative]) * ref < gap_points:
                continue  # selisih kecil: beri tempat ke bidang dari klaster lain
        selected.append(candidate)
    return selected


def _pick_reasons(items: list[tuple[int, int, str]], limit: int) -> list[str]:
    reasons: list[str] = []
    for _, _, reason in sorted(items, key=lambda item: (-item[0], item[1])):
        if reason and reason not in reasons:
            reasons.append(reason)
        if len(reasons) == limit:
            break
    return reasons


def _render_reason(reasons: list[str]) -> str:
    if not reasons:
        return ""
    if len(reasons) == 1:
        return f"Kamu {reasons[0]}."
    return "Kamu " + ", ".join(reasons[:-1]) + f", dan {reasons[-1]}." if len(reasons) > 2 else f"Kamu {reasons[0]} dan {reasons[1]}."
