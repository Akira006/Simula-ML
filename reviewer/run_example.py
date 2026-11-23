"""Menilai satu submission contoh dengan Claude API sungguhan (memakai saldo API).

    python -m reviewer.run_example                       # submission contoh case API
    python -m reviewer.run_example --model claude-sonnet-5-5

API key dibaca dari ANTHROPIC_API_KEY atau dari ml/.env (spasi dan tanda kutip dibuang).
Key tidak pernah dicetak. Hasil lengkap (review + audit) disimpan ke reviewer/eval/runs/.
"""

from __future__ import annotations

import argparse
import json
import os
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
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

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

    print(f"Model: {config.model} | effort: {config.effort} | case: {args.case} | {len(rubric['criteria'])} kriteria\n")
    outcome = grade(job, AnthropicClient(), config, InMemoryStore(),
                    on_progress=lambda c, t: print(f"  kriteria selesai: {c}/{t}"))

    audit = outcome.audit
    print(f"\nStatus: {outcome.status}" + (f" ({outcome.failure_reason})" if outcome.failure_reason else ""))
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

    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f"{datetime.now():%Y%m%d-%H%M%S}-{config.model}-{args.case}.json"
    out.write_text(json.dumps({"status": outcome.status, "failure_reason": outcome.failure_reason,
                               "review": outcome.review, "audit": audit}, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"Hasil lengkap: {out.relative_to(ML)}")
    return 0 if outcome.status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
