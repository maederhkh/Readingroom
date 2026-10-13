"""The helper program that hands readingroom's tools to Claude Code, over MCP.

Claude Code starts this program itself (see .mcp.json in the project folder) and talks
to it through its standard input and output. The program loads the shelf once, then
answers tool calls until Claude Code closes it.

    python -m readingroom.mcp_server          uses ./shelf, or $READINGROOM_SHELF

Three tools:
    keyword_search   find the articles, recitals and annexes that contain some words
    read             open one of them in full, by its bookmark
    list_documents   what is on the shelf
"""
import os
import pathlib
import re
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from readingroom import shelf
from readingroom.search import GROUPED_ANNEXES, GROUPED_RECITALS, KeywordIndex, load_passages
from readingroom.units import official_title

# The project folder: src/readingroom/mcp_server.py -> three levels up.
PROJECT = pathlib.Path(__file__).resolve().parents[2]
MAX_LIMIT = 20

# What each kind of bookmark is - told to the agent in the tool descriptions, so it can
# tell a binding rule from an explanation of one.
KINDS_EXPLAINED = """Each law has three kinds of part:
- articles: the binding rules (gdpr/article-22)
- recitals: the numbered "Whereas" paragraphs before the articles. They explain why the
  law was made and how to read the articles; they are not rules themselves (gdpr/recital-71)
- annexes: lists and technical details that articles refer to (eu-ai-act/annex-III)"""


def tool_description(laws: list[str]) -> str:
    """What Claude Code reads to decide when, and how, to use keyword_search."""
    return f"""Search the laws in this reading room for exact words.
Laws available: {", ".join(laws)}.

{KINDS_EXPLAINED}

Without `kind`, results come grouped: up to `limit` articles first, then up to
{GROUPED_RECITALS} recitals, then up to {GROUPED_ANNEXES} annexes - each ranked against its own kind, so the
binding rules are never pushed out by explanations. With `kind`, only that kind, up to `limit`.

Within a kind, results are ranked by keyword matching: a part containing the rarer query words,
more often, ranks higher. It matches words, not meaning - "accurate" does not match
"accuracy", and a question in your own words will miss text that uses different ones.
If the results are missing or weak, search again with other words: the law's own
terms, synonyms, or fewer words.

Put a phrase in "double quotes" to require those words in that order, for example
"kept up to date" or "Article 22".

Each result gives the law, kind, label (e.g. "Recital 71"), title, pages, a short
verbatim passage where the words appear, and a bookmark. The passage is only an excerpt:
to read the whole article, recital or annex, pass its bookmark to read."""


def read_description(laws: list[str]) -> str:
    return f"""Read one whole article, recital or annex, word for word, by its bookmark -
for example gdpr/article-22, gdpr/recital-71 or eu-ai-act/annex-III.
Bookmarks come from keyword_search results. Laws available: {", ".join(laws)}.

{KINDS_EXPLAINED}

Returns the full text with its label, title, chapter, section and pages. Use it when a
search excerpt looks relevant: the excerpt is only a fragment, and the rest - later
paragraphs, conditions, exceptions - can change what it means."""


LIST_DESCRIPTION = """List the laws on the shelf: each law's short name (used in bookmarks
and in the `law` input of keyword_search), its official title, its page count, and how many
articles, recitals and annexes it has."""

BOOKMARK = re.compile(r"(?P<law>[a-z0-9-]+)/(?P<kind>article|recital|annex)-(?P<number>\d+|[IVXLC]+)",
                      re.IGNORECASE)
PLURAL = {"article": "Articles", "recital": "Recitals", "annex": "Annexes"}


def read_result(library: dict[str, dict], laws: list[str], bookmark: str) -> dict[str, Any]:
    """The tool's answer, as plain data. Raises ValueError for a request it cannot serve."""
    shape = BOOKMARK.fullmatch(bookmark.strip())
    if not shape:
        raise ValueError(f"'{bookmark}' is not a bookmark. Bookmarks look like gdpr/article-22, "
                         "gdpr/recital-71 or eu-ai-act/annex-III, as given in keyword_search results.")
    # Case does not matter: the model once asked for "annex-iii" and lost a round to it.
    law, kind = shape["law"].lower(), shape["kind"].lower()
    bookmark = f"{law}/{kind}-{shape['number'].upper()}"
    if law not in laws:
        raise ValueError(f"No law called '{law}' on the shelf. Laws available: {', '.join(laws)}.")
    if bookmark not in library:
        numbers = [u["number"] for u in library.values() if u["law"] == law and u["kind"] == kind]
        if not numbers:
            raise ValueError(f"{law} has no {PLURAL[kind].lower()}.")
        if kind == "annex":
            raise ValueError(f"No {bookmark}. {law} has Annexes {', '.join(numbers)}.")
        raise ValueError(f"No {bookmark}. {law} has {PLURAL[kind]} {min(numbers)}–{max(numbers)}.")
    u = library[bookmark]
    return {"bookmark": bookmark, "law": law, "kind": kind, "label": u["label"], "title": u["title"],
            "chapter": u["chapter"], "section": u["section"],
            "pages": _pages(u["page_start"], u["page_end"]), "text": u["text"]}


def keyword_search_result(index: KeywordIndex, laws: list[str], query: str, law: str | None = None,
                          kind: str | None = None, limit: int = 5) -> dict[str, Any]:
    """The tool's answer, as plain data. Raises ValueError for a request it cannot serve."""
    if law is not None and law not in laws:
        raise ValueError(f"No law called '{law}' on the shelf. Laws available: {', '.join(laws)}.")
    if kind is not None and kind not in shelf.KINDS:
        raise ValueError(f"No kind called '{kind}'. Kinds: {', '.join(shelf.KINDS)}.")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}, not {limit}.")
    laws_wanted = [law] if law else None
    hits = (index.search(query, limit=limit, laws=laws_wanted, kinds=[kind]) if kind
            else index.search_grouped(query, limit=limit, laws=laws_wanted))
    answer: dict[str, Any] = {"query": query, "results": [_result(hit) for hit in hits]}
    if not hits:
        answer["note"] = ("Nothing contains these words. Try the law's own terms, "
                          "synonyms, or fewer words.")
    return answer


def list_documents_result(shelf_dir: pathlib.Path) -> dict[str, Any]:
    documents = []
    for doc_id in shelf.list_documents(shelf_dir):
        d = shelf.details(shelf_dir, doc_id)
        documents.append({
            "law": doc_id,
            "title": official_title(shelf.load(shelf_dir, doc_id).text) or d["source"],
            "pages": d["pages"],
            "articles": len(shelf.load_articles(shelf_dir, doc_id)),
            "recitals": len(shelf.load_units(shelf_dir, doc_id, "recitals")),
            "annexes": len(shelf.load_units(shelf_dir, doc_id, "annexes")),
        })
    return {"documents": documents}


def build_server(shelf_dir: pathlib.Path) -> MCPServer:
    laws = shelf.list_documents(shelf_dir)
    library = shelf.units_by_bookmark(shelf_dir)    # loaded once, at startup
    index = KeywordIndex(load_passages(shelf_dir))  # built once, at startup
    documents = list_documents_result(shelf_dir)
    # WARNING, not the library's default INFO: INFO switches on a log line for every
    # HTTP request the program makes, which buries the output of `ask`.
    server = MCPServer(name="readingroom", log_level="WARNING")

    # Each input carries its own explanation; Claude Code sees these next to the name.
    Query = Annotated[str, Field(description='Words to find. Put a phrase in "double quotes".')]
    Law = Annotated[str | None, Field(description=(
        f"Only search this law: one of {', '.join(laws)}. Leave out to search all of them."))]
    Kind = Annotated[str | None, Field(description=(
        f"Only search this kind of part: one of {', '.join(shelf.KINDS)}. Leave out to search all three."))]
    Limit = Annotated[int, Field(description=(
        f"How many articles to return (or results of the chosen kind), 1 to {MAX_LIMIT}."))]

    @server.tool(description=tool_description(laws))
    def keyword_search(query: Query, law: Law = None, kind: Kind = None, limit: Limit = 5) -> dict[str, Any]:
        try:
            return keyword_search_result(index, laws, query, law, kind, limit)
        except ValueError as refusal:
            # ToolError passes the message on to Claude Code; any other exception is
            # treated as a crash and reaches it only as "Error executing tool".
            raise ToolError(str(refusal)) from refusal

    Bookmark = Annotated[str, Field(description=(
        "The bookmark, e.g. gdpr/article-22, gdpr/recital-71 or eu-ai-act/annex-III."))]

    @server.tool(description=read_description(laws))
    def read(bookmark: Bookmark) -> dict[str, Any]:
        try:
            return read_result(library, laws, bookmark)
        except ValueError as refusal:
            raise ToolError(str(refusal)) from refusal

    @server.tool(description=LIST_DESCRIPTION)
    def list_documents() -> dict[str, Any]:
        return documents

    return server


def _result(hit) -> dict[str, Any]:
    p = hit.passage
    return {"bookmark": p.bookmark, "law": p.doc_id, "kind": p.kind, "label": p.label, "title": p.title,
            "pages": _pages(p.page_start, p.page_end), "passage": hit.snippet, "score": round(hit.score, 2)}


def _pages(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}–{end}"


def main() -> None:
    shelf_dir = pathlib.Path(os.environ.get("READINGROOM_SHELF", PROJECT / "shelf"))
    build_server(shelf_dir).run("stdio")


if __name__ == "__main__":
    main()
