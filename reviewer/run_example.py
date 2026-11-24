"""Menilai satu submission contoh dengan Claude API sungguhan (memakai saldo API).

    python -m reviewer.run_example                       # submission contoh case API
    python -m reviewer.run_example --model claude-sonnet-5-5
    python -m reviewer.run_example --repeat 5            # ukur waktu dan stabilitas (5x biaya)

API key dibaca dari ANTHROPIC_API_KEY atau dari ml/.env (spasi dan tanda kutip dibuang).
Key tidak pernah dicetak. Hasil lengkap (review + audit) disimpan ke reviewer/eval/runs/.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from .src.grade import GradingConfig, GradingJob, InMemoryStore, grade
from .src.llm_client import AnthropicClient

ROOT = Path(__file__).resolve().parent
ML = ROOT.parent
EXAMPLES = ROOT / "rubric" / "examples"
RUNS = ROOT / "eval" / "runs"
IDR_PER_USD = 18_000  # kurs asumsi untuk tampilan saja


def load_env_key() -> None:
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        os.environ["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"].strip()
        return
    env = ML / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "ANTHROPIC_API_KEY":
                os.environ["ANTHROPIC_API_KEY"] = value.strip().strip('"').strip("'")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="optimasi-api-endpoint-produk")
    parser.add_argument("--model", help="ganti model dari config/models.json")
    parser.add_argument("--effort", help="ganti effort dari config/models.json")
    parser.add_argument("--repeat", type=int, default=1,
                        help="ulangi penilaian N kali untuk mengukur waktu dan stabilitas (default 1)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if args.repeat < 1:
        print("--repeat minimal 1.")
        return 1

    load_env_key()
    if not os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-"):
        print("ANTHROPIC_API_KEY tidak ditemukan atau formatnya salah. Isi ml/.env dulu.")
        return 1

    config = GradingConfig.from_models_json(ROOT / "config" / "models.json")
    if args.model:
        config = replace(config, model=args.model)
    if args.effort:
        config = replace(config, effort=args.effort)

    case = json.loads((EXAMPLES / f"{args.case}.case.json").read_text(encoding="utf-8"))
    rubric = json.loads((EXAMPLES / f"{args.case}.rubric.json").read_text(encoding="utf-8"))
    submission = json.loads((EXAMPLES / f"{args.case}.submission.json").read_text(encoding="utf-8"))["submission"]
    job = GradingJob(case=case, rubric=rubric, submission=submission)

    print(f"Model: {config.model} | effort: {config.effort} | case: {args.case} | "
          f"{len(rubric['criteria'])} kriteria | {args.repeat} kali\n")
    client = AnthropicClient()
    outcomes = []
    for i in range(1, args.repeat + 1):
        if args.repeat > 1:
            print(f"=== Run {i}/{args.repeat} ===")
        # Penyimpanan baru tiap run: tanpa ini run ke-2 dst. memakai ulang hasil run pertama
        # (fitur hasil ulang submission identik) dan tidak memanggil API sama sekali.
        outcome = grade(job, client, config, InMemoryStore(),
                        on_progress=lambda c, t: print(f"  kriteria selesai: {c}/{t}"))
        outcomes.append(outcome)
        print_outcome(outcome, detailed=(i == 1))
        save_outcome(outcome, config.model, args.case, i)
    if args.repeat > 1:
        print_summary(outcomes, rubric)
    return 0 if all(o.status == "completed" for o in outcomes) else 2


def save_outcome(outcome, model: str, case_slug: str, index: int) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f"{datetime.now():%Y%m%d-%H%M%S}-{model}-{case_slug}-run{index}.json"
    out.write_text(json.dumps({"status": outcome.status, "failure_reason": outcome.failure_reason,
                               "review": outcome.review, "audit": outcome.audit}, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"Hasil lengkap: {out.relative_to(ML)}\n")


def print_outcome(outcome, detailed: bool) -> None:
    audit = outcome.audit
    print(f"\nStatus: {outcome.status}" + (f" ({outcome.failure_reason})" if outcome.failure_reason else ""))
    if outcome.review and not detailed:
        r = outcome.review
        levels = ", ".join(str(c["level"]) for c in r["criteria"])
        print(f"Skor {r['totalScore']} | level [{levels}] | durasi {audit['duration_ms'] / 1000:.1f} detik "
              f"| biaya Rp{audit['cost_usd'] * IDR_PER_USD:,.2f}")
        return
    if outcome.review:
        r = outcome.review
        print(f"Skor total: {r['totalScore']} / ambang {r['passingScore']} -> {'LULUS' if r['isPassed'] else 'BELUM LULUS'}\n")
        for c, raw in zip(r["criteria"], audit["criterion_results"]):
            print(f"[{c['name']}] bobot {c['weight']}, level {c['level']}, confidence {raw['confidence']}")
            print(f"  alasan : {c['reason']}")
            print(f"  bukti  : {'; '.join(raw['evidence'])}")
        for section in ("strengths", "improvements", "nextSteps"):
            print(f"\n{section}:")
            for item in r["feedback"][section]:
                print(f"  - {item}")

    print("\nRincian panggilan:")
    print(f"  {'panggilan':<24}{'hasil':<16}{'input':>7}{'cache tulis':>12}{'cache baca':>11}{'output':>8}{'detik':>7}")
    for e in audit["calls"]:
        print(f"  {e['call']:<24}{e.get('outcome', '-'):<16}{e.get('input_tokens', 0):>7}"
              f"{e.get('cache_creation_input_tokens', 0):>12}{e.get('cache_read_input_tokens', 0):>11}"
              f"{e.get('output_tokens', 0):>8}{e.get('latency_ms', 0) / 1000:>7.1f}")
    cost = audit["cost_usd"]
    print(f"\nTotal token: input {audit['input_tokens']}, cache tulis {audit['cache_creation_input_tokens']}, "
          f"cache baca {audit['cache_read_input_tokens']}, output {audit['output_tokens']}")
    print(f"Biaya: ${cost:.6f} ≈ Rp{cost * IDR_PER_USD:,.2f} | durasi {audit['duration_ms'] / 1000:.1f} detik | flags {audit['flags']}")


def _pct(values: list[float], q: float) -> float:
    """Persentil dengan interpolasi linier (sama dengan numpy default)."""
    s = sorted(values)
    k = (len(s) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def print_summary(outcomes, rubric) -> None:
    done = [o for o in outcomes if o.status == "completed"]
    print("=" * 72)
    print(f"RINGKASAN {len(outcomes)} RUN ({len(done)} selesai, {len(outcomes) - len(done)} gagal)")
    if not done:
        return
    totals = [o.audit["duration_ms"] / 1000 for o in done]
    print(f"\nWaktu total per penilaian: median {statistics.median(totals):.1f} detik, "
          f"p95 {_pct(totals, 0.95):.1f} detik, tercepat {min(totals):.1f}, terlama {max(totals):.1f}")
    print("Target AI-CONTEXT 8: median < 60 detik, p95 < 180 detik"
          f" -> {'TERPENUHI' if statistics.median(totals) < 60 and _pct(totals, 0.95) < 180 else 'BELUM'}")
    if len(done) < 20:
        print(f"Catatan: dengan {len(done)} run, p95 praktis sama dengan run terlama; belum mewakili.")

    by_call: dict[str, list[float]] = {}
    for o in done:
        for e in o.audit["calls"]:
            if e.get("outcome") == "ok":
                by_call.setdefault(e["call"], []).append(e["latency_ms"] / 1000)
    print(f"\n  {'panggilan':<24}{'rata2':>8}{'median':>8}{'terlama':>9}  (detik)")
    for call, lat in by_call.items():
        print(f"  {call:<24}{statistics.mean(lat):>8.1f}{statistics.median(lat):>8.1f}{max(lat):>9.1f}")
    retries = sum(1 for o in done for e in o.audit["calls"] if e.get("outcome") != "ok")
    print(f"  percobaan ulang (retry) total: {retries}")

    print("\nStabilitas level antar-run (AI-CONTEXT 10.2: sama di >= 90% kriteria, selisih skor <= 5):")
    same = 0
    for idx, c in enumerate(rubric["criteria"]):
        levels = [o.review["criteria"][idx]["level"] for o in done]
        same += len(set(levels)) == 1
        print(f"  {c['name']:<30} level per run: {levels}")
    scores = [o.review["totalScore"] for o in done]
    agree = same / len(rubric["criteria"])
    print(f"  kriteria dengan level sama di semua run: {same}/{len(rubric['criteria'])} ({agree:.0%})")
    print(f"  skor per run: {scores} -> selisih maks. {max(scores) - min(scores)} poin"
          f" -> {'TERPENUHI' if agree >= 0.9 and max(scores) - min(scores) <= 5 else 'BELUM'}")

    costs = [o.audit["cost_usd"] for o in outcomes]
    print(f"\nBiaya total: ${sum(costs):.6f} ≈ Rp{sum(costs) * IDR_PER_USD:,.2f} "
          f"(rata-rata Rp{statistics.mean(costs) * IDR_PER_USD:,.2f} per penilaian)")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
