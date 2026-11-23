"""Skor total AI Reviewer (AI-CONTEXT 6.4): dihitung kode, bukan LLM.

Replika persis client/src/lib/score.ts:

    getCriterionPoints = Math.round((level / 5) * weight * 10) / 10
    calculateTotalScore = Math.round(sum(getCriterionPoints))

Dua hal yang membuat replika naif keliru:
1. `round()` Python membulatkan setengah ke bilangan genap (60.5 -> 60), sedangkan Math.round JS
   membulatkan setengah ke atas (60.5 -> 61). Dipakai `js_round`.
2. Urutan operasi float harus sama: ((level / 5) * weight) * 10, lalu / 10, lalu dijumlah dari kiri.
Kecocokan diuji terhadap keluaran score.ts yang dijalankan dengan Node (tests/test_score.py).
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping

MAX_LEVEL = 5


def js_round(x: float) -> float:
    """Math.round JavaScript: bilangan bulat terdekat, setengah dibulatkan ke arah +tak hingga."""
    if math.isnan(x) or math.isinf(x):
        return x
    floor = math.floor(x)
    return float(floor + 1) if x - floor >= 0.5 else float(floor)


def criterion_points(level: int, weight: float) -> float:
    return js_round((level / MAX_LEVEL) * weight * 10) / 10


def total_score(criteria: Iterable[Mapping[str, float]]) -> int:
    total = 0
    for c in criteria:
        total = total + criterion_points(c["level"], c["weight"])
    return int(js_round(total))


def is_passed(score: int, passing_score: int) -> bool:
    return score >= passing_score
