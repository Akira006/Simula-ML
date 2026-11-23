import json
from pathlib import Path

import pytest

from reviewer.src.validate import (
    CRITERION_SCHEMA,
    FEEDBACK_SCHEMA,
    UNSUPPORTED_BY_PROVIDER,
    criterion_problems,
    feedback_problems,
    parse_json,
    provider_schema,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "outputs"
CRITERION = "Ketepatan analisis masalah"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(p.name for p in FIX.glob("criterion_valid_*.json")))
def test_valid_criterion_outputs(name):
    assert criterion_problems(load(name), CRITERION) == []


@pytest.mark.parametrize("name", sorted(p.name for p in FIX.glob("criterion_invalid_*.json")))
def test_invalid_criterion_outputs(name):
    case = load(name)
    problems = criterion_problems(case["output"], CRITERION)
    assert problems, name
    assert any(case["expect"] in p for p in problems), problems


@pytest.mark.parametrize("name", sorted(p.name for p in FIX.glob("feedback_valid_*.json")))
def test_valid_feedback_outputs(name):
    assert feedback_problems(load(name)) == []


@pytest.mark.parametrize("name", sorted(p.name for p in FIX.glob("feedback_invalid_*.json")))
def test_invalid_feedback_outputs(name):
    case = load(name)
    problems = feedback_problems(case["output"])
    assert any(case["expect"] in p for p in problems), problems


def test_parse_json_rejects_non_json():
    value, problems = parse_json("Berikut hasilnya: {level: 4}")
    assert value is None and problems


def test_abbreviation_is_not_a_sentence_end():
    out = load("feedback_valid_1.json")
    out["nextSteps"][0] = "Pelajari cara membaca query plan, mis. dengan EXPLAIN ANALYZE di PostgreSQL."
    assert feedback_problems(out) == []


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v)


@pytest.mark.parametrize("schema", [CRITERION_SCHEMA, FEEDBACK_SCHEMA])
def test_provider_schema_uses_only_supported_keywords(schema):
    ps = provider_schema(schema)
    keys = set(_keys(ps))
    assert not keys & UNSUPPORTED_BY_PROVIDER
    assert "$ref" not in keys and "$defs" not in keys
    assert ps["additionalProperties"] is False


def test_provider_schema_keeps_level_enum_and_flags_enum():
    ps = provider_schema(CRITERION_SCHEMA)
    assert ps["properties"]["level"]["enum"] == [1, 2, 3, 4, 5]
    assert "possible_injection" in ps["properties"]["flags"]["items"]["enum"]
    fb = provider_schema(FEEDBACK_SCHEMA)
    assert fb["properties"]["strengths"]["minItems"] == 1 and "maxItems" not in fb["properties"]["strengths"]
