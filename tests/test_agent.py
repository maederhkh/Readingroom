"""The research loop - readingroom's own chef.

The model is a FakeModel that follows a script, so no test calls a real model or
spends money. The tools are real: the same MCP helper program Claude Code uses,
serving the one-page test law from conftest.py.
"""
import copy
import json

import pytest

from readingroom.__main__ import main
from readingroom.agent import INSTRUCTIONS, research
from readingroom.mcp_server import build_server
from readingroom.model import Reply, ToolCall, Usage


class FakeModel:
    """Replies from a script, in order; the last reply repeats. Records every request."""

    model = "fake/scripted-model"  # the name the `ask` command prints

    def __init__(self, *replies: Reply):
        self.replies = list(replies)
        self.requests = []  # (messages, tools) as the loop sent them

    def respond(self, messages, tools):
        self.requests.append((copy.deepcopy(messages), tools))
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def asks_to_read(bookmark, call_id="read-1"):
    return Reply(text="", tool_calls=[ToolCall(id=call_id, name="read",
                                               arguments=json.dumps({"bookmark": bookmark}))],
                 cut_off=False, usage=Usage(input_tokens=100, output_tokens=10))


def asks_to_search(query, call_id="call-1", **arguments):
    return Reply(text="", tool_calls=[ToolCall(id=call_id, name="keyword_search",
                                               arguments=json.dumps({"query": query, **arguments}))],
                 cut_off=False, usage=Usage(input_tokens=100, output_tokens=10))


def answers(text, cut_off=False):
    return Reply(text=text, tool_calls=[], cut_off=cut_off, usage=Usage(input_tokens=200, output_tokens=50))


def tool_messages(model, request=-1):
    messages, _ = model.requests[request]
    return [m for m in messages if m["role"] == "tool"]


@pytest.fixture
def server(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    return build_server(shelf)


def test_the_model_gets_the_instructions_and_the_question(server):
    model = FakeModel(answers("It says nothing."))
    research("What is the subject-matter?", model, server)
    messages, _ = model.requests[0]
    assert messages == [{"role": "system", "content": INSTRUCTIONS},
                        {"role": "user", "content": "What is the subject-matter?"}]


def test_the_model_sees_the_same_tool_claude_code_sees(server):
    import anyio
    mcp_tools = anyio.run(server.list_tools)
    model = FakeModel(answers("done"))
    research("q", model, server)
    _, tools = model.requests[0]
    assert tools == [{"type": "function", "function": {
        "name": t.name, "description": t.description, "parameters": t.input_schema}} for t in mcp_tools]


def test_an_answer_without_searching_ends_the_loop(server):
    result = research("q", FakeModel(answers("An answer.")), server)
    assert result.answer == "An answer."
    assert result.steps == []
    assert result.rounds == 1


def test_a_requested_search_is_run_and_its_results_handed_back(server):
    model = FakeModel(asks_to_search("objectives"), answers("Article 1 sets out the objectives."))
    result = research("q", model, server)
    [tool_message] = tool_messages(model)
    assert tool_message["tool_call_id"] == "call-1"
    assert json.loads(tool_message["content"])["results"][0]["bookmark"] == "tiny-law/article-1"
    assert result.answer == "Article 1 sets out the objectives."
    assert result.rounds == 2


def test_the_models_own_request_is_kept_in_the_conversation(server):
    # The model must see its earlier tool call, or the tool result makes no sense to it.
    model = FakeModel(asks_to_search("objectives"), answers("done"))
    research("q", model, server)
    messages, _ = model.requests[1]
    [assistant] = [m for m in messages if m["role"] == "assistant"]
    assert assistant["tool_calls"][0]["id"] == "call-1"
    assert assistant["tool_calls"][0]["function"]["name"] == "keyword_search"


def test_each_step_is_reported_as_it_happens(server):
    seen = []
    research("q", FakeModel(asks_to_search("objectives"), answers("done")), server, on_step=seen.append)
    [step] = seen
    assert (step.tool, step.arguments["query"]) == ("keyword_search", "objectives")
    assert step.result["results"][0]["bookmark"] == "tiny-law/article-1"


def test_a_requested_article_is_read_and_handed_back_whole(server):
    model = FakeModel(asks_to_read("tiny-law/article-1"), answers("done"))
    result = research("q", model, server)
    [tool_message] = tool_messages(model)
    assert json.loads(tool_message["content"])["text"] == "Article 1\nSubject-matter and objectives"
    assert [s.tool for s in result.steps] == ["read"]


def test_a_refused_search_is_handed_back_so_the_model_can_correct_itself(server):
    model = FakeModel(asks_to_search("objectives", law="gdpr"), answers("done"))
    result = research("q", model, server)
    [tool_message] = tool_messages(model)
    assert "No law called 'gdpr' on the shelf. Laws available: tiny-law." in tool_message["content"]
    assert result.steps[0].error is not None


def test_arguments_that_are_not_valid_json_are_handed_back_as_an_error(server):
    broken = Reply(text="", tool_calls=[ToolCall(id="c", name="keyword_search", arguments="{query: oops")],
                   cut_off=False, usage=Usage())
    model = FakeModel(broken, answers("done"))
    research("q", model, server)
    assert "not valid JSON" in tool_messages(model)[0]["content"]


def test_the_tool_call_limit_stops_a_model_that_never_finishes(server):
    # Reading counts towards the limit as well as searching: both cost money.
    model = FakeModel(asks_to_search("objectives"), asks_to_read("tiny-law/article-1"),
                      asks_to_search("objectives"), answers("What I found so far."))
    result = research("q", model, server, max_tool_calls=2)
    assert [s.tool for s in result.steps] == ["keyword_search", "read"]
    assert result.hit_limit
    assert "Tool-call limit of 2 reached" in tool_messages(model)[-1]["content"]
    last_messages, last_tools = model.requests[-1]
    assert last_tools is None                      # the final request offers no tools
    # ...and says so plainly, in its own message. A note tucked inside the last tool
    # result was not enough: in the first real run gpt-5-mini wrote more search
    # requests as plain text instead of answering.
    assert last_messages[-1]["role"] == "user"
    assert "no tool calls left" in last_messages[-1]["content"]
    assert result.answer == "What I found so far."


def test_a_cut_off_answer_is_reported_as_cut_off(server):
    result = research("q", FakeModel(answers("Article 1 says", cut_off=True)), server)
    assert result.cut_off


def test_usage_is_added_up_across_rounds(server):
    result = research("q", FakeModel(asks_to_search("objectives"), answers("done")), server)
    assert (result.usage.input_tokens, result.usage.output_tokens) == (300, 60)
