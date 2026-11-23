import json
from types import SimpleNamespace

import pytest

from reviewer.prompts.v1.builder import build_criterion_request, build_feedback_request
from reviewer.src.llm_client import AnthropicClient, CallSettings, MockClient, make_client

SETTINGS = CallSettings(model="claude-haiku-5-5", effort="low", max_tokens=8000, timeout_seconds=90)


def test_mock_is_deterministic_and_simulates_cache(api_case, api_rubric, good_submission):
    reqs = [build_criterion_request(api_case, api_rubric, c["id"], good_submission) for c in api_rubric["criteria"]]
    a, b = MockClient(), MockClient()
    out_a = [a.complete(r, SETTINGS) for r in reqs]
    out_b = [b.complete(r, SETTINGS) for r in reqs]
    assert [o.text for o in out_a] == [o.text for o in out_b]
    assert out_a[0].usage.cache_creation_input_tokens > 0 and out_a[0].usage.cache_read_input_tokens == 0
    assert all(o.usage.cache_read_input_tokens == out_a[0].usage.cache_creation_input_tokens for o in out_a[1:])


def test_anthropic_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        AnthropicClient()
    assert isinstance(make_client(), MockClient)


def test_anthropic_params_shape(api_case, api_rubric, good_submission):
    req = build_criterion_request(api_case, api_rubric, "analisis", good_submission)
    params = AnthropicClient.build_params(req, SETTINGS)
    assert params["model"] == "claude-haiku-5-5"
    assert params["output_config"]["effort"] == "low"
    assert params["output_config"]["format"]["type"] == "json_schema"
    assert [("cache_control" in b) for b in params["system"]] == [False, True]
    assert [("cache_control" in b) for b in params["messages"][0]["content"]] == [True, False]
    assert params["system"][1]["cache_control"] == {"type": "ephemeral"}
    assert "thinking" not in params and "fallbacks" not in params and "temperature" not in params
    breakpoints = sum("cache_control" in b for b in params["system"] + params["messages"][0]["content"])
    assert breakpoints <= 4


def test_feedback_params_have_no_cache(api_case, api_rubric):
    results = [{"criterion": c["name"], "level": 3, "evidence": ["x"], "reason": "y.", "confidence": "high", "flags": []}
               for c in api_rubric["criteria"]]
    params = AnthropicClient.build_params(build_feedback_request(api_case, api_rubric, results, []), SETTINGS)
    assert not any("cache_control" in b for b in params["system"] + params["messages"][0]["content"])


class _FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


class _FakeSDK:
    def __init__(self, response):
        self.messages = _FakeMessages(response)
        self.timeout = None

    def with_options(self, timeout):
        self.timeout = timeout
        return self


def test_anthropic_response_parsing_with_fake_sdk(api_case, api_rubric, good_submission):
    payload = {"criterion": "Ketepatan analisis masalah", "level": 4, "evidence": ["README.md"], "reason": "Jelas.",
               "confidence": "high", "flags": []}
    response = SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=json.dumps(payload))],
        stop_reason="end_turn", model="claude-haiku-5-5", stop_details=None,
        usage=SimpleNamespace(input_tokens=600, cache_creation_input_tokens=0, cache_read_input_tokens=12000,
                              output_tokens=250))
    fake = _FakeSDK(response)
    client = AnthropicClient(sdk_client=fake)
    req = build_criterion_request(api_case, api_rubric, "analisis", good_submission)
    out = client.complete(req, SETTINGS)
    assert json.loads(out.text) == payload
    assert out.usage.cache_read_input_tokens == 12000 and out.usage.output_tokens == 250
    assert fake.timeout == 90
