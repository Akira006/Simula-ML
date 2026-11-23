"""Mesin simulasi numpy harus memberi top-3 yang sama persis dengan implementasi referensi."""

import copy

import numpy as np
import pytest

from quiz.simulation.engine import Engine, answers_to_dicts, persona_answers, uniform_answers
from quiz.src.config import load_config
from quiz.src.scoring import score_quiz

DIVERSITY = {"type": "max_per_cluster", "max": 2, "override_gap_points": 2}


def _variants():
    v1 = load_config("quiz.v1.json")
    v2 = load_config("quiz.v2.json")
    v2_div = copy.deepcopy(v2)
    v2_div["scoring"]["diversity"] = DIVERSITY
    v2_field_order = copy.deepcopy(v2)
    v2_field_order["scoring"]["tie_break"] = ["field_order"]
    return {"v1": v1, "v2": v2, "v2_div": v2_div, "v2_field_order": v2_field_order}


@pytest.mark.parametrize("name", ["v1", "v2", "v2_div", "v2_field_order"])
def test_engine_matches_reference(name):
    config = _variants()[name]
    engine = Engine(config)
    rng = np.random.default_rng(7)
    batches = [uniform_answers(engine, 400, rng)]
    for target in range(engine.F):
        major = next((i for i, e in enumerate(config["major_mapping"]) if engine.keys[target] in e["points"]), None)
        batches.append(persona_answers(engine, target, 30, rng, major_entry=major))
    for ans in batches:
        result = engine.rank(ans)
        for r, answers in enumerate(answers_to_dicts(engine, ans)):
            ref = score_quiz(config, answers, "2026-10-09T00:00:00Z")
            expected = [s["fieldKey"] for s in ref["suggestions"]]
            got = [engine.keys[i] for i in result["top"][r] if i >= 0]
            assert got == expected, (name, answers, got, expected)
