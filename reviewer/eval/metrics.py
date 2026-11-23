"""Metrik evaluasi AI Reviewer (AI-CONTEXT 10.2). Fungsi murni, diuji di tests/test_eval_metrics.py."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

LEVELS = (1, 2, 3, 4, 5)


def quadratic_weighted_kappa(a: Sequence[int], b: Sequence[int], levels: Sequence[int] = LEVELS) -> float:
    """QWK dua penilai pada skala ordinal. 1 = sepakat sempurna, 0 = setara kebetulan, < 0 = lebih buruk.

    Penyebut hanya 0 bila kedua penilai memberi satu nilai yang sama untuk semua item; hasilnya 1.0.
    Dua penilai yang konstan tetapi berbeda (misalnya selalu 3 vs selalu 4) menghasilkan 0.
    """
    if len(a) != len(b) or not a:
        raise ValueError("panjang data harus sama dan > 0")
    k = len(levels)
    index = {lv: i for i, lv in enumerate(levels)}
    observed = np.zeros((k, k))
    for x, y in zip(a, b):
        observed[index[x], index[y]] += 1
    weights = np.array([[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)])
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / observed.sum()
    denom = (weights * expected).sum()
    if denom == 0:
        return 1.0
    return float(1 - (weights * observed).sum() / denom)


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    def ranks(v):
        v = np.asarray(v, dtype=float)
        order = v.argsort(kind="stable")
        r = np.empty(len(v))
        r[order] = np.arange(len(v))
        for value in np.unique(v):  # rata-rata peringkat untuk nilai seri
            mask = v == value
            r[mask] = r[mask].mean()
        return r

    rx, ry = ranks(x), ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return math.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def permutation_p_value(x: Sequence[float], y: Sequence[float], n_perm: int = 5000, seed: int = 0) -> float:
    """p-value dua sisi untuk korelasi Spearman dengan uji permutasi (tanpa asumsi distribusi)."""
    observed = abs(spearman(x, y))
    if math.isnan(observed):
        return math.nan
    rng = np.random.default_rng(seed)
    y = np.asarray(y, dtype=float)
    hits = sum(abs(spearman(x, rng.permutation(y))) >= observed - 1e-12 for _ in range(n_perm))
    return (hits + 1) / (n_perm + 1)


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))
