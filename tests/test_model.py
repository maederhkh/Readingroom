"""The connection to the model - tested offline, on response objects built by hand."""
import pytest
from openai.types.chat import ChatCompletion

from readingroom.model import OpenRouterModel, Usage, reply_from


def completion(content=None, tool_calls=None, finish_reason="stop", cost=None):
    usage = {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
    if cost is not None:
        usage["cost"] = cost  # OpenRouter adds this field when asked to
    return ChatCompletion.model_validate({
        "id": "x", "object": "chat.completion", "created": 0, "model": "openai/gpt-5-mini",
        "choices": [{"index": 0, "finish_reason": finish_reason,
                     "message": {"role": "assistant", "content": content, "tool_calls": tool_calls}}],
        "usage": usage,
    })


def test_a_plain_answer():
    reply = reply_from(completion(content="Article 22 says..."))
    assert (reply.text, reply.tool_calls, reply.cut_off) == ("Article 22 says...", [], False)


def test_a_tool_request_keeps_the_arguments_exactly_as_written():
    reply = reply_from(completion(tool_calls=[{"id": "call-9", "type": "function", "function": {
        "name": "keyword_search", "arguments": '{"query": "profiling"}'}}], finish_reason="tool_calls"))
    [call] = reply.tool_calls
    assert (call.id, call.name, call.arguments) == ("call-9", "keyword_search", '{"query": "profiling"}')
    assert reply.text == ""


def test_hitting_the_length_limit_is_reported_as_cut_off():
    assert reply_from(completion(content="Article 22 says", finish_reason="length")).cut_off


def test_tokens_and_cost_are_read_from_the_response():
    reply = reply_from(completion(content="x", cost=0.0012))
    assert reply.usage == Usage(input_tokens=120, output_tokens=30, cost=0.0012)


def test_cost_is_unknown_rather_than_zero_when_not_reported():
    assert reply_from(completion(content="x")).usage.cost is None


def test_usage_adds_up_and_stays_unknown_only_if_every_part_is_unknown():
    assert Usage(1, 2, None) + Usage(3, 4, None) == Usage(4, 6, None)
    assert Usage(1, 2, 0.5) + Usage(3, 4, None) == Usage(4, 6, 0.5)


def test_a_missing_key_says_where_to_put_it(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match=r"\.env"):
        OpenRouterModel()


def test_the_model_can_be_chosen_in_the_environment(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("READINGROOM_MODEL", "anthropic/some-model")
    assert OpenRouterModel().model == "anthropic/some-model"
    assert OpenRouterModel("openai/other").model == "openai/other"   # an explicit choice wins
