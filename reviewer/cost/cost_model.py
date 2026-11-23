"""Model biaya AI Reviewer (B5).

Harga HANYA dari pricing.json (disalin dari halaman pricing resmi, lihat source_url dan retrieved).
Jalankan dari folder ml/:

    python -m reviewer.cost.cost_model          # menulis reviewer/cost/results.md

Pola yang dimodelkan (AI-CONTEXT 6.1): N panggilan kriteria BERURUTAN + 1 panggilan feedback.
Asumsi lengkap ada di ASSUMPTIONS dan ditulis ke results.md.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PRICING = json.loads((HERE / "pricing.json").read_text(encoding="utf-8"))
MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]
MTOK = 1_000_000


def _tier(model: str, prompt_tokens: int) -> dict[str, Any]:
    for tier in PRICING["models"][model]["tiers"]:
        if tier["max_prompt_tokens"] is None or prompt_tokens <= tier["max_prompt_tokens"]:
            return tier
    raise ValueError("tier tidak ditemukan")


def call_cost(model: str, input_tokens: int, output_tokens: int, cache_write_tokens: int = 0,
              cache_read_tokens: int = 0, ttl: str = "5m") -> float:
    """Biaya satu request. Tier Haiku ditentukan dari SEMUA token input (termasuk cache)."""
    prompt = input_tokens + cache_write_tokens + cache_read_tokens
    t = _tier(model, prompt)
    return (input_tokens * t["input"] + cache_write_tokens * t[f"cache_write_{ttl}"]
            + cache_read_tokens * t["cache_read"] + output_tokens * t["output"]) / MTOK


@dataclass
class Scenario:
    name: str
    prefix_tokens: int  # system + case + submission: bagian yang sama di semua panggilan kriteria


ASSUMPTIONS = {
    "criteria": 5,
    "criterion_block_tokens": 600,  # blok <criterion> + instruksi akhir, tidak di-cache
    "feedback_input_tokens": 3_000,  # system feedback + ringkasan case + hasil 5 kriteria (tanpa submission)
    "output_profiles": {
        "hemat": {"criterion": 300, "feedback": 400,
                  "note": "JSON saja, thinking minimal. Total 1.900 token, dekat asumsi AI-CONTEXT (1.500)."},
        "dengan_thinking": {"criterion": 1_200, "feedback": 1_000,
                            "note": "Thinking adaptif aktif di ketiga model dan ditagih sebagai output. Angka ini tebakan; ukur di golden set."},
    },
    "aicontext_output_tokens": 1_500,
    "retry_rate": 0.0,
}

SCENARIOS = [Scenario("Isian teks saja", 10_000), Scenario("Dokumen atau kode zip", 40_000),
             Scenario("Mendekati batas 5.5", 60_000)]


def aicontext_single_call(model: str, scenario: Scenario) -> float:
    """Cara AI-CONTEXT bagian 12 menghitung: satu panggilan, tanpa cache, output 1.500 token."""
    return call_cost(model, scenario.prefix_tokens, ASSUMPTIONS["aicontext_output_tokens"])


def assessment_cost(model: str, scenario: Scenario, cached: bool, profile: str) -> dict[str, float]:
    """Biaya satu penilaian: N panggilan kriteria berurutan + 1 feedback.

    Dengan cache: panggilan ke-1 menulis prefix (1,25x), panggilan ke-2..N membaca prefix dari cache.
    Panggilan dianggap berurutan dan selisih waktunya < 5 menit (TTL default), sesuai desain antrean.
    Feedback tidak memakai cache: skemanya berbeda (mengganti output_config.format membatalkan cache)
    dan inputnya kecil.
    """
    n = ASSUMPTIONS["criteria"]
    r = ASSUMPTIONS["criterion_block_tokens"]
    out = ASSUMPTIONS["output_profiles"][profile]
    p = scenario.prefix_tokens
    if cached:
        first = call_cost(model, r, out["criterion"], cache_write_tokens=p)
        rest = (n - 1) * call_cost(model, r, out["criterion"], cache_read_tokens=p)
        criteria = first + rest
    else:
        criteria = n * call_cost(model, p + r, out["criterion"])
    feedback = call_cost(model, ASSUMPTIONS["feedback_input_tokens"], out["feedback"])
    total = (criteria + feedback) * (1 + ASSUMPTIONS["retry_rate"])
    return {"criteria": criteria, "feedback": feedback, "total": total}


def usd(x: float) -> str:
    if x >= 100:
        return f"${x:,.0f}"
    if x >= 1:
        return f"${x:,.2f}"
    return f"${x:.4f}"


def report() -> str:
    lines = [
        "# Hasil model biaya AI Reviewer (dibuat otomatis)",
        "",
        f"Harga: {PRICING['source_url']} (diambil {PRICING['retrieved']}). Per 1 juta token, USD.",
        "",
        "| Model | Input | Cache write 5m | Cache read | Output |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for m in MODELS:
        for t in PRICING["models"][m]["tiers"]:
            suffix = "" if len(PRICING["models"][m]["tiers"]) == 1 else (
                f" (prompt <= {t['max_prompt_tokens']:,})" if t["max_prompt_tokens"] else " (prompt > 100.000)")
            lines.append(f"| {PRICING['models'][m]['label']}{suffix} | ${t['input']} | ${t['cache_write_5m']} "
                         f"| ${t['cache_read']} | ${t['output']} |")
    lines += ["", "## Asumsi", "", "```json", json.dumps(ASSUMPTIONS, indent=2, ensure_ascii=False), "```", ""]

    lines += ["## 1. Per penilaian", ""]
    for profile in ASSUMPTIONS["output_profiles"]:
        lines += [f"### Profil output: {profile}", "",
                  "| Skenario | Model | AI-CONTEXT 12 (1 panggilan) | 6 panggilan tanpa cache | 6 panggilan dengan cache "
                  "| Dengan cache / AI-CONTEXT | Tanpa cache / dengan cache |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
        for s in SCENARIOS:
            for m in MODELS:
                single = aicontext_single_call(m, s)
                nocache = assessment_cost(m, s, False, profile)["total"]
                cache = assessment_cost(m, s, True, profile)["total"]
                lines.append(f"| {s.name} ({s.prefix_tokens // 1000} rb) | {PRICING['models'][m]['label']} | {usd(single)} "
                             f"| {usd(nocache)} | {usd(cache)} | {cache / single:.2f}x | {nocache / cache:.2f}x |")
        lines.append("")

    lines += ["## 2. Rincian satu penilaian (dengan cache, profil hemat, 60 ribu token)", "",
              "| Model | Panggilan 1 (tulis cache) | Panggilan 2-5 (baca cache) | Feedback | Total |",
              "| --- | ---: | ---: | ---: | ---: |"]
    s = SCENARIOS[2]
    out = ASSUMPTIONS["output_profiles"]["hemat"]
    r = ASSUMPTIONS["criterion_block_tokens"]
    for m in MODELS:
        first = call_cost(m, r, out["criterion"], cache_write_tokens=s.prefix_tokens)
        rest = 4 * call_cost(m, r, out["criterion"], cache_read_tokens=s.prefix_tokens)
        fb = call_cost(m, ASSUMPTIONS["feedback_input_tokens"], out["feedback"])
        lines.append(f"| {PRICING['models'][m]['label']} | {usd(first)} | {usd(rest)} | {usd(fb)} | {usd(first + rest + fb)} |")

    lines += ["", "## 3. Bulanan (dengan cache)", ""]
    for profile in ASSUMPTIONS["output_profiles"]:
        lines += [f"### Profil output: {profile}", "",
                  "| Skenario | Model | 1.000 penilaian | 10.000 penilaian | Rumus AI-CONTEXT 12 per skenario, tanpa retry (1.000 / 10.000) |",
                  "| --- | --- | ---: | ---: | --- |"]
        for s in SCENARIOS:
            for m in MODELS:
                c = assessment_cost(m, s, True, profile)["total"]
                a = aicontext_single_call(m, s)
                lines.append(f"| {s.name} | {PRICING['models'][m]['label']} | {usd(1000 * c)} | {usd(10000 * c)} "
                             f"| {usd(1000 * a)} / {usd(10000 * a)} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    text = report()
    (HERE / "results.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
