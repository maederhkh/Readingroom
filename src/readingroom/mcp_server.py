"""The helper program that hands readingroom's tools to Claude Code, over MCP.

Claude Code starts this program itself (see .mcp.json in the project folder) and talks
to it through its standard input and output. The program loads the shelf once, then
answers tool calls until Claude Code closes it.

    python -m readingroom.mcp_server          uses ./shelf, or $READINGROOM_SHELF

For now there is one tool: keyword_search.
"""
import os
import pathlib
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from readingroom import shelf
from readingroom.search import KeywordIndex, load_passages

# The project folder: src/readingroom/mcp_server.py -> three levels up.
PROJECT = pathlib.Path(__file__).resolve().parents[2]
MAX_LIMIT = 20


def tool_description(laws: list[str]) -> str:
    """What Claude Code reads to decide when, and how, to use keyword_search."""
    return f"""Search the articles of the laws in this reading room for exact words.
Laws available: {", ".join(laws)}.

Articles are ranked by keyword matching: an article containing the rarer query words,
more often, ranks higher. It matches words, not meaning - "accurate" does not match
"accuracy", and a question in your own words will miss text that uses different ones.
If the results are missing or weak, search again with other words: the law's own
terms, synonyms, or fewer words.

Put a phrase in "double quotes" to require those words in that order, for example
"kept up to date" or "Article 22".

Only articles are searched, not recitals or annexes.

Each result gives the law, article number, title, pages, a short verbatim passage
where the words appear, and a bookmark such as gdpr/article-5. The passage is an
excerpt from the article, not the whole article."""


def keyword_search_result(index: KeywordIndex, laws: list[str], query: str,
                          law: str | None = None, limit: int = 5) -> dict[str, Any]:
    """The tool's answer, as plain data. Raises ValueError for a request it cannot serve."""
    if law is not None and law not in laws:
        raise ValueError(f"No law called '{law}' on the shelf. Laws available: {', '.join(laws)}.")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}, not {limit}.")
    hits = index.search(query, limit=limit, laws=[law] if law else None)
    answer: dict[str, Any] = {"query": query, "results": [_result(hit) for hit in hits]}
    if not hits:
        answer["note"] = ("No articles contain these words. Try the law's own terms, "
                          "synonyms, or fewer words.")
    return answer


def build_server(shelf_dir: pathlib.Path) -> MCPServer:
    laws = shelf.list_documents(shelf_dir)
    index = KeywordIndex(load_passages(shelf_dir))  # built once, at startup
    # WARNING, not the library's default INFO: INFO switches on a log line for every
    # HTTP request the program makes, which buries the output of `ask`.
    server = MCPServer(name="readingroom", log_level="WARNING")

    # Each input carries its own explanation; Claude Code sees these next to the name.
    Query = Annotated[str, Field(description='Words to find. Put a phrase in "double quotes".')]
    Law = Annotated[str | None, Field(description=(
        f"Only search this law: one of {', '.join(laws)}. Leave out to search all of them."))]
    Limit = Annotated[int, Field(description=f"How many articles to return, 1 to {MAX_LIMIT}.")]

    @server.tool(description=tool_description(laws))
    def keyword_search(query: Query, law: Law = None, limit: Limit = 5) -> dict[str, Any]:
        try:
            return keyword_search_result(index, laws, query, law, limit)
        except ValueError as refusal:
            # ToolError passes the message on to Claude Code; any other exception is
            # treated as a crash and reaches it only as "Error executing tool".
            raise ToolError(str(refusal)) from refusal

    return server


def _result(hit) -> dict[str, Any]:
    p = hit.passage
    pages = str(p.page_start) if p.page_start == p.page_end else f"{p.page_start}–{p.page_end}"
    return {"bookmark": p.bookmark, "law": p.doc_id, "article": p.article, "title": p.title,
            "pages": pages, "passage": hit.snippet, "score": round(hit.score, 2)}


def main() -> None:
    shelf_dir = pathlib.Path(os.environ.get("READINGROOM_SHELF", PROJECT / "shelf"))
    build_server(shelf_dir).run("stdio")


if __name__ == "__main__":
    main()
