"""A1: analisis struktural konfigurasi kuis, dihitung langsung dari JSON (tanpa simulasi).

Menjawab: berapa poin maksimum tiap bidang, berapa opsi yang memberi poin ke tiap bidang,
berapa poin harapan bila menjawab acak seragam, dan opsi mana yang memberi poin ke banyak
bidang sekaligus.

Jalankan:  python -m quiz.src.analyze            (dari folder ml/)
"""

from __future__ import annotations

import sys
from fractions import Fraction
from typing import Any

from .config import field_keys, load_config
from .scoring import max_points


def option_counts(config: dict[str, Any]) -> dict[str, int]:
    """Jumlah opsi (di soal single dan multi) yang memberi poin > 0 ke tiap bidang."""
    counts = dict.fromkeys(field_keys(config), 0)
    for question in config["questions"]:
        if question["type"] in ("single", "multi"):
            for option in question["options"]:
                for key, pts in option["points"].items():
                    counts[key] += pts > 0
    return counts


def expected_points_uniform(config: dict[str, Any]) -> dict[str, Fraction]:
    """Poin harapan per bidang bila tiap soal single dijawab acak seragam dan tiap opsi Q4
    (selain 'Belum ada') dicentang dengan peluang 1/2. Batas Q4 diperhitungkan secara eksak
    dengan enumerasi semua subset (jumlah opsi Q4 kecil)."""
    keys = field_keys(config)
    expected = dict.fromkeys(keys, Fraction(0))
    for question in config["questions"]:
        if question["type"] == "single":
            n = len(question["options"])
            for key in keys:
                expected[key] += Fraction(sum(o["points"].get(key, 0) for o in question["options"]), n)
        elif question["type"] == "multi":
            exclusive = set(question.get("exclusive_option_ids", []))
            options = [o for o in question["options"] if o["id"] not in exclusive]
            cap = question.get("per_field_cap")
            m = len(options)
            for key in keys:
                total = Fraction(0)
                for mask in range(2**m):
                    raw = sum(options[i]["points"].get(key, 0) for i in range(m) if mask >> i & 1)
                    total += raw if cap is None else min(cap, raw)
                expected[key] += total / 2**m
    return expected


def multi_field_options(config: dict[str, Any], min_fields: int = 3) -> list[tuple[str, str, dict[str, int]]]:
    rows = []
    for question in config["questions"]:
        if question["type"] in ("single", "multi"):
            for option in question["options"]:
                if sum(1 for v in option["points"].values() if v > 0) >= min_fields:
                    rows.append((question["id"], option["text"], option["points"]))
    return rows


def dominated_pairs(config: dict[str, Any]) -> list[tuple[str, str]]:
    """Pasangan (f, g): di SETIAP opsi soal single/multi dan setiap entri jurusan, poin f <= poin g.

    Artinya untuk jawaban apa pun poin mentah f tidak pernah melebihi g. Dengan normalisasi
    'user_max' (v1) atau tie-break urutan bidang, f tidak akan pernah berada di atas g.
    """
    keys = field_keys(config)
    vectors = []
    for question in config["questions"]:
        if question["type"] in ("single", "multi"):
            vectors += [o["points"] for o in question["options"]]
    vectors += [e["points"] for e in config.get("major_mapping", [])]
    pairs = []
    for f in keys:
        if not any(v.get(f, 0) for v in vectors):
            continue
        for g in keys:
            if f != g and all(v.get(f, 0) <= v.get(g, 0) for v in vectors):
                pairs.append((f, g))
    return pairs


def report(config_name: str) -> str:
    config = load_config(config_name)
    keys = field_keys(config)
    labels = {f["key"]: f["label"] for f in config["fields"]}
    max_no_major = max_points(config, include_major=False)
    max_with_major = max_points(config, include_major=True)
    counts = option_counts(config)
    expected = expected_points_uniform(config)
    lines = [
        f"### {config_name} (versi {config['version']})",
        "",
        "| Bidang | Poin maks. Q1-Q6 | Poin maks. + Q8 | Opsi yang memberi poin | Poin harapan (acak) | Harapan / maks. |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in sorted(keys, key=lambda k: (-max_no_major[k], keys.index(k))):
        ratio = expected[key] / max_no_major[key] if max_no_major[key] else Fraction(0)
        lines.append(
            f"| {labels[key]} (`{key}`) | {max_no_major[key]} | {max_with_major[key]} | {counts[key]} "
            f"| {float(expected[key]):.2f} | {float(ratio):.3f} |"
        )
    spread = max(max_no_major.values()) - min(max_no_major.values())
    lines += ["", f"Selisih poin maksimum tertinggi dan terendah (tanpa Q8): **{spread}**.", ""]
    rows = multi_field_options(config)
    if rows:
        lines.append("Opsi yang memberi poin ke 3 bidang atau lebih sekaligus:")
        lines.append("")
        for qid, text, pts in rows:
            lines.append(f"- {qid} \"{text}\": " + ", ".join(f"{k} +{v}" for k, v in pts.items()))
    else:
        lines.append("Tidak ada opsi yang memberi poin ke 3 bidang atau lebih sekaligus.")
    lines.append("")
    pairs = dominated_pairs(config)
    if pairs:
        lines.append("Pasangan terdominasi (poin mentah bidang pertama TIDAK PERNAH melebihi bidang kedua, "
                     "untuk jawaban apa pun):")
        lines.append("")
        lines += [f"- {labels[f]} <= {labels[g]}" for f, g in pairs]
    else:
        lines.append("Tidak ada pasangan bidang yang terdominasi.")
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    names = argv or ["quiz.v1.json", "quiz.v2.json"]
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n\n".join(report(name) for name in names))


if __name__ == "__main__":
    main(sys.argv[1:])
