"""The research loop: readingroom's own chef.

    ask the model  ->  it asks for a search  ->  run it  ->  hand back the results
         ^                                                          |
         +----------------------------------------------------------+
    ... until the model answers instead of asking for another search.

The tools come from the same MCP helper program Claude Code uses (mcp_server.py),
called from inside this program - so both chefs see the same tool, the same
description and the same error messages.
"""
import json
from collections.abc import Callable
from dataclasses import dataclass, field

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from readingroom.model import Reply, Usage

# Minimal on purpose: the full research method is a later step. This only sets the
# ground rules, so what the model does beyond them is visible.
INSTRUCTIONS = """You answer questions using only the laws in this reading room, which you \
can search with the keyword_search tool.
- Base every statement on text the tool returned. Do not rely on your own knowledge of these laws.
- After each statement, cite the bookmark and pages it comes from, e.g. [gdpr/article-5, pp. 35–36].
- If the tool results do not contain the answer, say so plainly instead of guessing."""

MAX_SEARCHES = 10
FINAL_ANSWER_NOW = ("You have no searches left. Write your final answer now, using only the "
                    "search results above, with a citation after each statement. If they are "
                    "not enough to answer fully, say what is missing.")


@dataclass(frozen=True)
class Search:
    query: str
    law: str | None
    result_count: int
    top: str | None           # bookmark of the best result
    error: str | None = None  # why the search was refused, if it was


@dataclass
class Research:
    answer: str
    searches: list[Search] = field(default_factory=list)
    rounds: int = 0          # how many times the model was asked
    usage: Usage = Usage()
    hit_limit: bool = False  # stopped because it reached the search limit
    cut_off: bool = False    # the final answer hit the length limit


def research(question: str, model, server: MCPServer, max_searches: int = MAX_SEARCHES,
             on_search: Callable[[Search], None] = lambda s: None) -> Research:
    tools = [_as_model_tool(t) for t in anyio.run(server.list_tools)]
    messages = [{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": question}]
    result = Research(answer="")

    while True:
        reply: Reply = model.respond(messages, None if result.hit_limit else tools)
        result.rounds += 1
        result.usage += reply.usage
        if not reply.tool_calls or result.hit_limit:  # an answer - or the last word after the limit
            result.answer, result.cut_off = reply.text, reply.cut_off
            return result

        messages.append(_remember_request(reply))  # the model must see its own request
        for call in reply.tool_calls:
            done = len([s for s in result.searches if s.error is None])
            if done >= max_searches:
                result.hit_limit = True
                content = {"error": f"Search limit of {max_searches} reached. "
                                    "Answer now with what you have found."}
            else:
                search, content = _run(server, call)
                result.searches.append(search)
                on_search(search)
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(content, ensure_ascii=False)})
        if result.hit_limit:
            # Said plainly, in a message of its own. When this lived only inside the last
            # tool result, gpt-5-mini wrote more search requests as text instead of answering.
            messages.append({"role": "user", "content": FINAL_ANSWER_NOW})


def _run(server: MCPServer, call) -> tuple[Search, dict]:
    """Carry out one tool call. Problems go back to the model as an error it can act on."""
    try:
        arguments = json.loads(call.arguments)
    except json.JSONDecodeError:
        error = f"The arguments were not valid JSON: {call.arguments}"
        return Search(query="?", law=None, result_count=0, top=None, error=error), {"error": error}
    query, law = str(arguments.get("query", "")), arguments.get("law")
    try:
        answer = anyio.run(server.call_tool, call.name, arguments).structured_content
    except ToolError as refusal:
        return Search(query, law, 0, None, error=str(refusal)), {"error": str(refusal)}
    results = answer["results"]
    return Search(query, law, len(results), results[0]["bookmark"] if results else None), answer


def _as_model_tool(tool) -> dict:
    """An MCP tool, in the shape the model's API expects."""
    return {"type": "function", "function": {
        "name": tool.name, "description": tool.description, "parameters": tool.input_schema}}


def _remember_request(reply: Reply) -> dict:
    return {"role": "assistant", "content": reply.text or None, "tool_calls": [
        {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
        for c in reply.tool_calls]}
