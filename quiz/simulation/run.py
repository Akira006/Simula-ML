"""A5: simulasi bias struktural kuis minat (v1 draf vs v2).

PENTING: semua jawaban di sini SINTETIS. Simulasi hanya memeriksa bias struktural (apakah ada
bidang yang diuntungkan oleh susunan opsi dan bobot), BUKAN bukti bahwa kuis cocok untuk
mahasiswa sungguhan.

Jalankan dari folder ml/:
    python -m quiz.simulation.run              # lengkap, termasuk sensitivitas (~1 menit)
    python -m quiz.simulation.run --quick      # tanpa sensitivitas
Keluaran: quiz/simulation/results/summary.json dan results/tables.md
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from ..src.config import load_config
from .engine import Engine, persona_answers, uniform_answers

RESULTS = Path(__file__).resolve().parent / "results"

SEED = 20261009
N_UNIFORM = 20_000
N_PERSONA = 2_000
EPS = 0.2  # peluang persona menjawab acak di tiap soal
TOOL_NOISE = 0.15  # peluang persona mencentang tools yang tidak terkait bidangnya
BAND = (0.15, 0.35)  # pita toleransi masuk top-3 untuk jawaban acak (pilihan penulis, lihat REPORT)
TARGET_TOP3, TARGET_TOP1 = 0.90, 0.60
DIVERSITY = {"type": "max_per_cluster", "max": 2, "override_gap_points": 2}
TECH = ["backend", "frontend", "mobile"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (centre - half, centre + half)


def variants() -> dict[str, dict[str, Any]]:
    v1 = load_config("quiz.v1.json")
    v2 = load_config("quiz.v2.json")
    v1_norm = copy.deepcopy(v1)
    v1_norm["scoring"]["normalization"] = "max_achievable"  # menguji normalisasi saja, tanpa merombak struktur
    out = {
        "v1_max_norm": {"config": v1_norm, "tie_break": ["random"], "diversity": None,
                        "label": "v1 struktur draf + normalisasi poin maks. (tie acak)"},
        "v1": {"config": v1, "tie_break": None, "diversity": None, "label": "v1 draf (tie-break urutan bidang)"},
        "v1_random_tie": {"config": v1, "tie_break": ["random"], "diversity": None,
                          "label": "v1 draf (tie-break acak)"},
        "v2_no_rule": {"config": v2, "tie_break": None, "diversity": {"type": "none"},
                       "label": "v2 (a) tanpa aturan klaster"},
        "v2_field_order": {"config": v2, "tie_break": ["field_order"], "diversity": {"type": "none"},
                           "label": "v2 (a) dengan tie-break urutan bidang"},
        "v2": {"config": v2, "tie_break": None, "diversity": DIVERSITY,
               "label": "v2 final: (b) maks. 2 bidang per klaster kecuali selisih >= 2 poin"},
    }
    assert v2["scoring"]["diversity"] == DIVERSITY, "quiz.v2.json harus memakai aturan klaster yang dievaluasi"
    return out


def summarize(engine: Engine, result: dict[str, np.ndarray]) -> dict[str, Any]:
    top = result["top"]
    n = top.shape[0]
    per_field = {}
    for f, key in enumerate(engine.keys):
        in3 = int((top == f).any(axis=1).sum())
        t1 = int((top[:, 0] == f).sum())
        lo, hi = wilson(in3, n)
        per_field[key] = {"top1": t1 / n, "top3": in3 / n, "top3_ci": [lo, hi]}
    tech_idx = [engine.keys.index(k) for k in TECH]
    all_tech = np.all(np.isin(top, tech_idx), axis=1).mean()
    gap = result["gap_points"]
    return {
        "n": n,
        "per_field": per_field,
        "all_tech_top3": float(all_tech),
        "tie_rate_exact": float((gap == 0).mean()),
        "tie_rate_le1": float((gap <= 1).mean()),
    }


def run_uniform(name: str, spec: dict[str, Any], rng_seed: int) -> dict[str, Any]:
    engine = Engine(spec["config"])
    rng = np.random.default_rng(rng_seed)
    ans = uniform_answers(engine, N_UNIFORM, rng)
    res = engine.rank(ans, tie_break=spec["tie_break"], rng=np.random.default_rng(rng_seed + 1),
                      diversity=spec["diversity"])
    out = summarize(engine, res)
    out["out_of_band"] = [k for k, v in out["per_field"].items() if not BAND[0] <= v["top3"] <= BAND[1]]
    return out


def run_personas(spec: dict[str, Any], rng_seed: int, eps: float = EPS, with_major: bool = False,
                 n: int = N_PERSONA) -> dict[str, Any]:
    engine = Engine(spec["config"])
    out = {}
    for f, key in enumerate(engine.keys):
        rng = np.random.default_rng(rng_seed + f)
        major = None
        if with_major:
            major = next((i for i, e in enumerate(spec["config"]["major_mapping"]) if key in e["points"]), None)
        ans = persona_answers(engine, f, n, rng, eps=eps, tool_noise=TOOL_NOISE, major_entry=major)
        res = engine.rank(ans, tie_break=spec["tie_break"], rng=np.random.default_rng(rng_seed + 100 + f),
                          diversity=spec["diversity"])
        top = res["top"]
        tech_idx = [engine.keys.index(k) for k in TECH]
        out[key] = {
            "top1": float((top[:, 0] == f).mean()),
            "top3": float((top == f).any(axis=1).mean()),
            "all_tech_top3": float(np.all(np.isin(top, tech_idx), axis=1).mean()),
            "tie_exact": float((res["gap_points"] == 0).mean()),
            "tie_le1": float((res["gap_points"] <= 1).mean()),
        }
    return out


def perturbations(config: dict[str, Any]):
    """Setiap bobot yang ada (> 0) di soal single/multi diubah +1 dan -1."""
    for qi, q in enumerate(config["questions"]):
        if q["type"] not in ("single", "multi"):
            continue
        for oi, opt in enumerate(q["options"]):
            for key, pts in opt["points"].items():
                for delta in (+1, -1):
                    if pts + delta < 0:
                        continue
                    cfg = copy.deepcopy(config)
                    new_points = cfg["questions"][qi]["options"][oi]["points"]
                    if pts + delta == 0:
                        del new_points[key]
                    else:
                        new_points[key] = pts + delta
                    yield f"{opt['id']}:{key}{'+' if delta > 0 else '-'}1 ({pts}->{pts + delta})", cfg


def sensitivity(spec: dict[str, Any], n_uniform: int = N_UNIFORM, n_persona: int = 500) -> dict[str, Any]:
    base_engine = Engine(spec["config"])
    rng = np.random.default_rng(SEED + 7)
    uni = uniform_answers(base_engine, n_uniform, rng)  # bilangan acak bersama untuk semua perturbasi
    personas = [persona_answers(base_engine, f, n_persona, np.random.default_rng(SEED + 50 + f), eps=EPS,
                                tool_noise=TOOL_NOISE) for f in range(base_engine.F)]

    def evaluate(config):
        engine = Engine(config)
        res = engine.rank(uni, tie_break=spec["tie_break"], rng=np.random.default_rng(1), diversity={"type": "none"})
        top = res["top"]
        rates = np.array([(top == f).any(axis=1).mean() for f in range(engine.F)])
        p_top1 = []
        for f, ans in enumerate(personas):
            r = engine.rank(ans, tie_break=spec["tie_break"], rng=np.random.default_rng(2), diversity={"type": "none"})
            p_top1.append((r["top"][:, 0] == f).mean())
        return rates, np.array(p_top1)

    base_rates, base_p1 = evaluate(spec["config"])
    rows = []
    for label, cfg in perturbations(spec["config"]):
        rates, p1 = evaluate(cfg)
        dev = np.abs(rates - 0.25)
        rows.append({
            "change": label,
            "max_dev_top3": float(dev.max()),
            "field_max_dev": base_engine.keys[int(dev.argmax())],
            "max_shift_top3": float(np.abs(rates - base_rates).max()),
            "field_max_shift": base_engine.keys[int(np.abs(rates - base_rates).argmax())],
            "min_persona_top1": float(p1.min()),
            "field_min_persona_top1": base_engine.keys[int(p1.argmin())],
        })
    rows.sort(key=lambda r: -r["max_shift_top3"])
    return {
        "baseline_max_dev_top3": float(np.abs(base_rates - 0.25).max()),
        "baseline_min_persona_top1": float(base_p1.min()),
        "n_changes": len(rows),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Tabel markdown
# ---------------------------------------------------------------------------


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def tables(summary: dict[str, Any]) -> str:
    labels = {f["key"]: f["label"] for f in load_config("quiz.v2.json")["fields"]}
    keys = list(labels)
    uni = summary["uniform"]
    lines = ["## 1. Jawaban acak seragam", "",
             f"N = {N_UNIFORM:,} responden per varian, seed {SEED}. Pita toleransi masuk top-3: "
             f"{pct(BAND[0])}-{pct(BAND[1])} (nilai seimbang = 25%).", "",
             "| Bidang | v1 top-3 | v1 top-1 | v1 (tie acak) top-3 | v2 final top-3 | v2 final top-1 | v2 top-3 (CI 95%) |",
             "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for k in keys:
        a, b, c = uni["v1"]["per_field"][k], uni["v1_random_tie"]["per_field"][k], uni["v2"]["per_field"][k]
        flag1 = " ⚠" if not BAND[0] <= a["top3"] <= BAND[1] else ""
        flag2 = " ⚠" if not BAND[0] <= c["top3"] <= BAND[1] else ""
        lines.append(f"| {labels[k]} | {pct(a['top3'])}{flag1} | {pct(a['top1'])} | {pct(b['top3'])} "
                     f"| {pct(c['top3'])}{flag2} | {pct(c['top1'])} | {pct(c['top3_ci'][0])}-{pct(c['top3_ci'][1])} |")
    lines += ["", "⚠ = di luar pita toleransi.", "",
              "| Varian | Bidang di luar pita | Selisih maks. dari 25% | Top-3 berisi 3 bidang tech | Top-1 seri persis |",
              "| --- | --- | ---: | ---: | ---: |"]
    for name, spec in variants().items():
        u = uni[name]
        dev = max(abs(v["top3"] - 0.25) for v in u["per_field"].values())
        oob = ", ".join(labels[k] for k in u["out_of_band"]) or "tidak ada"
        lines.append(f"| {spec['label']} | {oob} | {100 * dev:.1f} poin persen | {pct(u['all_tech_top3'])} "
                     f"| {pct(u['tie_rate_exact'])} |")
    lines += ["", "Pembanding: bila top-3 diambil acak dari 12 bidang, peluang ketiganya tech = 1/220 = 0.45%.", ""]

    per = summary["personas"]
    lines += ["## 2. Persona sintetis", "",
              f"N = {N_PERSONA:,} per bidang. Persona memilih opsi berbobot tertinggi untuk bidangnya dengan peluang "
              f"{1 - EPS:.0%}, sisanya acak; tools tidak terkait dicentang dengan peluang {TOOL_NOISE:.0%}. "
              f"Target: top-3 >= {TARGET_TOP3:.0%}, top-1 >= {TARGET_TOP1:.0%}.", "",
              "| Persona | v1 top-1 | v1 top-3 | v2 final top-1 | v2 final top-3 | v2 (a) top-3 | v2 + jurusan top-1 "
              "| v2 seri persis | v2 selisih <= 1 poin |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for k in keys:
        a, c = per["v1"][k], per["v2"][k]
        m, d = per["v2_with_major"][k], per["v2_no_rule"][k]
        w = lambda v, t: " ⚠" if v < t else ""  # noqa: E731
        lines.append(f"| {labels[k]} | {pct(a['top1'])}{w(a['top1'], TARGET_TOP1)} | {pct(a['top3'])}{w(a['top3'], TARGET_TOP3)} "
                     f"| {pct(c['top1'])}{w(c['top1'], TARGET_TOP1)} | {pct(c['top3'])}{w(c['top3'], TARGET_TOP3)} "
                     f"| {pct(d['top3'])} | {pct(m['top1'])} | {pct(c['tie_exact'])} | {pct(c['tie_le1'])} |")
    lines += ["", "⚠ = di bawah target (top-1 < 60% atau top-3 < 90%).", "",
              "v1 struktur draf + normalisasi poin maks. (tanpa merombak soal), persona: "
              f"top-1 terendah {pct(min(v['top1'] for v in per['v1_max_norm'].values()))}, "
              f"top-3 terendah {pct(min(v['top3'] for v in per['v1_max_norm'].values()))}.", ""]
    lines += ["Persona tech yang top-3-nya berisi 3 bidang tech:", "",
              "| Persona | v1 | v2 (a) tanpa aturan | v2 final (b) |", "| --- | ---: | ---: | ---: |"]
    for k in TECH:
        lines.append(f"| {labels[k]} | {pct(per['v1'][k]['all_tech_top3'])} | {pct(per['v2_no_rule'][k]['all_tech_top3'])} "
                     f"| {pct(per['v2'][k]['all_tech_top3'])} |")
    lines += ["", "Ketahanan terhadap noise (nilai terendah di antara 12 persona):", "",
              "| eps | v1 min top-1 | v1 min top-3 | v2 min top-1 | v2 min top-3 |", "| ---: | ---: | ---: | ---: | ---: |"]
    for eps, row in summary["eps_sweep"].items():
        lines.append(f"| {eps} | {pct(row['v1']['min_top1'])} | {pct(row['v1']['min_top3'])} "
                     f"| {pct(row['v2']['min_top1'])} | {pct(row['v2']['min_top3'])} |")

    if "sensitivity" in summary:
        lines += ["", "## 3. Sensitivitas bobot (+/-1)", ""]
        for name in ("v2", "v1"):
            s = summary["sensitivity"][name]
            lines += [f"### {name}: {s['n_changes']} perubahan diuji",
                      "", f"Baseline: selisih maks. top-3 dari 25% = {100 * s['baseline_max_dev_top3']:.1f} poin persen; "
                      f"top-1 persona terendah = {pct(s['baseline_min_persona_top1'])}.", "",
                      "| Perubahan | Pergeseran top-3 terbesar | Bidang | Selisih maks. dari 25% | Top-1 persona terendah |",
                      "| --- | ---: | --- | ---: | --- |"]
            for r in s["rows"][:10]:
                lines.append(f"| `{r['change']}` | {100 * r['max_shift_top3']:.1f} pp | {labels[r['field_max_shift']]} "
                             f"| {100 * r['max_dev_top3']:.1f} pp | {pct(r['min_persona_top1'])} ({labels[r['field_min_persona_top1']]}) |")
            worst = min(s["rows"], key=lambda r: r["min_persona_top1"])
            lines += ["", f"Perubahan yang paling menurunkan top-1 persona: `{worst['change']}` -> "
                          f"{pct(worst['min_persona_top1'])} ({labels[worst['field_min_persona_top1']]}).", ""]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="lewati analisis sensitivitas")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    started = time.time()
    specs = variants()
    summary: dict[str, Any] = {
        "note": "SINTETIS: jawaban acak dan persona buatan. Hanya menguji bias struktural.",
        "params": {"seed": SEED, "n_uniform": N_UNIFORM, "n_persona": N_PERSONA, "eps": EPS,
                   "tool_noise": TOOL_NOISE, "band": BAND, "targets": [TARGET_TOP3, TARGET_TOP1]},
        "uniform": {name: run_uniform(name, spec, SEED) for name, spec in specs.items()},
        "personas": {name: run_personas(spec, SEED + 1000) for name, spec in specs.items()},
    }
    summary["personas"]["v2_with_major"] = run_personas(specs["v2"], SEED + 1000, with_major=True)
    summary["eps_sweep"] = {}
    for eps in (0.1, 0.2, 0.3, 0.4):
        row = {}
        for name in ("v1", "v2"):
            per = run_personas(specs[name], SEED + 2000, eps=eps)
            row[name] = {"min_top1": min(v["top1"] for v in per.values()),
                         "min_top3": min(v["top3"] for v in per.values())}
        summary["eps_sweep"][str(eps)] = row
    if not args.quick:
        summary["sensitivity"] = {"v2": sensitivity(specs["v2"]), "v1": sensitivity(specs["v1"])}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "tables.md").write_text(tables(summary), encoding="utf-8")
    print(tables(summary))
    print(f"Selesai dalam {time.time() - started:.1f} detik.")


if __name__ == "__main__":
    main(sys.argv[1:])
