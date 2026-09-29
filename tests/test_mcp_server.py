"""The MCP helper program that hands readingroom's tools to Claude Code.

read_article has its own file, tests/test_read_article.py.
"""
import sys

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from readingroom.__main__ import main
from readingroom.mcp_server import build_server, keyword_search_result, tool_description
from readingroom.search import KeywordIndex, Passage

GDPR_5 = Passage(doc_id="gdpr", article=5, title="Principles relating to processing of personal data",
                 page_start=35, page_end=36,
                 text="Article 5\nPrinciples relating to processing of personal data\n"
                      "(d)  accurate and, where necessary, kept up to date (‘accuracy’);")
DSA_12 = Passage(doc_id="digital-services-act", article=12, title="Points of contact for recipients of the service",
                 page_start=48, page_end=48, text="Article 12\nPoints of contact\nkept up to date")
INDEX = KeywordIndex([GDPR_5, DSA_12])
LAWS = ["digital-services-act", "gdpr"]


def call_over_connection(shelf, arguments, tool="keyword_search"):
    """Start the helper program as its own process and call a tool, as Claude Code does."""
    server = StdioServerParameters(command=sys.executable, args=["-m", "readingroom.mcp_server"],
                                   env={"READINGROOM_SHELF": str(shelf)})

    async def ask():
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool, arguments)

    return anyio.run(ask)


def test_a_result_carries_everything_needed_to_cite_and_reopen_it():
    [result] = keyword_search_result(INDEX, LAWS, "accuracy")["results"]
    assert result == {
        "bookmark": "gdpr/article-5",
        "law": "gdpr",
        "article": 5,
        "title": "Principles relating to processing of personal data",
        "pages": "35–36",
        "passage": "Article 5 Principles relating to processing of personal data "
                   "(d)  accurate and, where necessary, kept up to date (‘accuracy’);",
        "score": result["score"],
    }


def test_the_query_is_echoed_back():
    assert keyword_search_result(INDEX, LAWS, "accuracy")["query"] == "accuracy"


def test_no_match_says_so_and_suggests_what_to_try():
    answer = keyword_search_result(INDEX, LAWS, "zebra")
    assert answer["results"] == []
    assert answer["note"].startswith("No articles contain these words.")


def test_search_can_be_limited_to_one_law():
    answer = keyword_search_result(INDEX, LAWS, '"kept up to date"', law="gdpr")
    assert [r["bookmark"] for r in answer["results"]] == ["gdpr/article-5"]


def test_an_unknown_law_is_refused_with_the_laws_that_exist():
    with pytest.raises(ValueError, match="No law called 'ai-act'.*digital-services-act, gdpr"):
        keyword_search_result(INDEX, LAWS, "accuracy", law="ai-act")


def test_limit_must_be_between_1_and_20():
    with pytest.raises(ValueError):
        keyword_search_result(INDEX, LAWS, "accuracy", limit=0)
    with pytest.raises(ValueError):
        keyword_search_result(INDEX, LAWS, "accuracy", limit=21)


def test_the_description_names_the_laws_and_says_what_the_tool_cannot_do():
    text = tool_description(LAWS)
    assert "digital-services-act, gdpr" in text
    assert "not meaning" in text               # an honest limit, so the agent searches again
    assert '"double quotes"' in text           # how to ask for a phrase
    assert "read_article" in text              # where to go for the whole article
    assert "recitals" in text                  # what is not searched


def test_the_server_offers_search_and_reading(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    tools = anyio.run(build_server(shelf).list_tools)
    assert [t.name for t in tools] == ["keyword_search", "read_article"]


def test_a_refused_request_tells_claude_code_why(documents, tmp_path):
    # The MCP library hides the message of an ordinary exception ("Error executing
    # tool keyword_search") - the agent would know it failed but not how to fix it.
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    answer = call_over_connection(shelf, {"query": "x", "law": "gdpr"})
    assert answer.is_error
    assert "No law called 'gdpr' on the shelf. Laws available: tiny-law." in answer.content[0].text


def test_every_input_is_explained_to_claude_code(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    tool = anyio.run(build_server(shelf).list_tools)[0]
    for name, field in tool.input_schema["properties"].items():  # keyword_search
        assert field.get("description"), f"'{name}' has no description"
    assert "tiny-law" in tool.input_schema["properties"]["law"]["description"]


def test_claude_code_can_call_the_tool_over_a_real_connection(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    answer = call_over_connection(shelf, {"query": "objectives"})
    assert not answer.is_error
    assert answer.structured_content["results"][0]["bookmark"] == "tiny-law/article-1"
