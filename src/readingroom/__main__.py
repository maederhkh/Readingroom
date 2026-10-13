"""The commands.

    python -m readingroom ingest                  read documents/ and fill shelf/
    python -m readingroom inspect gdpr            one document: its details and articles
    python -m readingroom inspect gdpr --page 35
    python -m readingroom inspect gdpr --article 5
    python -m readingroom inspect gdpr --recital 71
    python -m readingroom inspect eu-ai-act --annex III
    python -m readingroom search accuracy --law gdpr
    python -m readingroom search "\\"kept up to date\\""
    python -m readingroom ask "What does the GDPR say about automated decision-making?"
"""
import argparse
import hashlib
import pathlib
import sys

from readingroom import shelf
from readingroom.agent import MAX_TOOL_CALLS, research
from readingroom.articles import find_articles
from readingroom.mcp_server import PROJECT, build_server
from readingroom.model import OpenRouterModel
from readingroom.pdf import read_clean_text
from readingroom.search import KeywordIndex, load_passages
from readingroom.units import find_annexes, find_recitals


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.command(args)


def ingest(args) -> int:
    documents, shelf_dir = pathlib.Path(args.documents), pathlib.Path(args.shelf)
    pdfs = sorted(documents.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs in {documents}", file=sys.stderr)
        return 1
    for pdf in pdfs:
        doc = read_clean_text(pdf)
        doc_id = shelf.document_id(pdf)
        sha256 = hashlib.sha256(pdf.read_bytes()).hexdigest()
        shelf.save(shelf_dir, doc_id, doc, source_name=pdf.name, source_sha256=sha256)
        articles = find_articles(doc.text)
        recitals = find_recitals(doc.text)
        annexes = find_annexes(doc.text)
        shelf.save_articles(shelf_dir, doc_id, articles, doc)
        shelf.save_units(shelf_dir, doc_id, "recitals", recitals, doc)
        shelf.save_units(shelf_dir, doc_id, "annexes", annexes, doc)
        print(f"{doc_id:24} {doc.page_count:4} pages  {len(doc.text):>9,} characters  "
              f"{len(articles):4} articles {len(recitals):4} recitals {len(annexes):3} annexes  <- {pdf.name}")
    return 0


def inspect(args) -> int:
    shelf_dir = pathlib.Path(args.shelf)
    held = shelf.list_documents(shelf_dir)
    if args.document not in held:
        print(f"'{args.document}' is not on the shelf. It holds: {', '.join(held) or 'nothing'}",
              file=sys.stderr)
        return 1
    if args.page is not None:
        return _show_page(shelf_dir, args.document, args.page)
    if args.article is not None:
        return _show_article(shelf_dir, args.document, args.article)
    if args.recital is not None:
        return _show_unit(shelf_dir, args.document, "recitals", args.recital)
    if args.annex is not None:
        return _show_unit(shelf_dir, args.document, "annexes", args.annex.upper())
    d = shelf.details(shelf_dir, args.document)
    articles = shelf.load_articles(shelf_dir, args.document)
    recitals = shelf.load_units(shelf_dir, args.document, "recitals")
    annexes = shelf.load_units(shelf_dir, args.document, "annexes")
    print(f"{args.document}: {d['pages']} pages, {d['characters']:,} characters, from {d['source']}")
    print(f"  {len(articles)} articles, {len(recitals)} recitals, {len(annexes)} annexes")
    if recitals:
        print(f"  Recitals 1–{len(recitals)}  {_pages({'page_start': recitals[0]['page_start'], 'page_end': recitals[-1]['page_end']}):>10}")
    for a in articles:
        print(f"  Article {a['number']:<4} {_pages(a):>10}   {a['title']}")
    for a in annexes:
        print(f"  Annex {a['number']:<6} {_pages(a):>10}   {a['title']}")
    return 0


def search(args) -> int:
    index = KeywordIndex(load_passages(pathlib.Path(args.shelf)))
    hits = (index.search(args.query, limit=args.limit, laws=args.law, kinds=args.kind) if args.kind
            else index.search_grouped(args.query, limit=args.limit, laws=args.law))
    if not hits:
        print("Nothing contains these words.")
        return 0
    for rank, hit in enumerate(hits, start=1):
        p = hit.passage
        pages = _pages({"page_start": p.page_start, "page_end": p.page_end})
        title = f" · {p.title}" if p.title else ""
        print(f"{rank}. {p.doc_id} · {p.label}{title} · {pages}   (score {hit.score:.2f})")
        print(f"   {hit.snippet}")
        print(f"   bookmark: {p.bookmark}\n")
    return 0


def ask(args) -> int:
    _load_env()
    try:
        model = OpenRouterModel(args.model)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    server = build_server(pathlib.Path(args.shelf))

    print(f"  [{model.model}]")
    result = research(args.question, model, server, max_tool_calls=args.max_tool_calls, on_step=_show_step)
    print("\n  Answer\n")
    print(result.answer)
    if result.cut_off:
        print("\n  ⚠ The answer was cut off at the length limit - it is incomplete.")
    if result.hit_limit:
        print(f"\n  ⚠ Stopped at the limit of {args.max_tool_calls} tool calls; answered with what it had found.")
    searches = sum(s.tool == "keyword_search" for s in result.steps)
    reads = sum(s.tool == "read" for s in result.steps)
    u = result.usage
    cost = f" · ${u.cost:.4f}" if u.cost is not None else ""
    print(f"\n  {searches} search{'es' if searches != 1 else ''} · {reads} read{'s' if reads != 1 else ''} · "
          f"{result.rounds} rounds · {u.input_tokens + u.output_tokens:,} tokens{cost}")
    return 0


def _show_step(step) -> None:
    """One line per tool call, printed as it happens. Queries are shown as the model wrote them."""
    if step.tool == "keyword_search":
        filters = "".join(f" {k}={step.arguments[k]}" for k in ("law", "kind") if step.arguments.get(k))
        head = f"  🔎 search: {step.arguments.get('query', '?')}{filters}"
        if step.error is None:
            results = step.result["results"]
            top = f" (top: {results[0]['bookmark']})" if results else ""
            print(f"{head}  → {len(results)} results{top}")
            return
    elif step.tool == "read":
        head = f"  📖 read: {step.arguments.get('bookmark', '?')}"
        if step.error is None:
            r = step.result
            pages = f"pp. {r['pages']}" if "–" in r["pages"] else f"p. {r['pages']}"
            title = f" — {r['title']}" if r["title"] else ""
            print(f"{head}  → {r['label']}{title} ({pages})")
            return
    elif step.tool == "list_documents":
        if step.error is None:
            print(f"  📚 list documents  → {', '.join(d['law'] for d in step.result['documents'])}")
            return
        head = "  📚 list documents"
    else:
        head = f"  ? {step.tool}"
    print(f"{head}  → refused: {step.error}")


def _load_env() -> None:
    """Read OPENROUTER_API_KEY (and optionally READINGROOM_MODEL) from readingroom/.env."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT / ".env")


def _show_page(shelf_dir: pathlib.Path, doc_id: str, page: int) -> int:
    doc = shelf.load(shelf_dir, doc_id)
    try:
        print(doc.page_text(page))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


def _show_article(shelf_dir: pathlib.Path, doc_id: str, number: int) -> int:
    found = [a for a in shelf.load_articles(shelf_dir, doc_id) if a["number"] == number]
    if not found:
        print(f"{doc_id} has no Article {number}", file=sys.stderr)
        return 1
    a = found[0]
    where = " · ".join(part for part in (a["chapter"], a["section"], _pages(a)) if part)
    print(f"[{doc_id} · {where} · characters {a['start']:,}–{a['end']:,}]\n")
    print(shelf.load(shelf_dir, doc_id).text[a["start"]:a["end"]])
    return 0


def _show_unit(shelf_dir: pathlib.Path, doc_id: str, kind: str, number) -> int:
    """Show one recital or annex, with its bookmark on top."""
    name = "Recital" if kind == "recitals" else "Annex"
    found = [u for u in shelf.load_units(shelf_dir, doc_id, kind) if u["number"] == number]
    if not found:
        print(f"{doc_id} has no {name} {number}", file=sys.stderr)
        return 1
    u = found[0]
    label = f"{name} {number}" + (f" — {u['title']}" if "title" in u else "")
    print(f"[{doc_id} · {label} · {_pages(u)} · characters {u['start']:,}–{u['end']:,}]\n")
    print(shelf.load(shelf_dir, doc_id).text[u["start"]:u["end"]])
    return 0


def _pages(article: dict) -> str:
    if article["page_start"] == article["page_end"]:
        return f"p. {article['page_start']}"
    return f"pp. {article['page_start']}–{article['page_end']}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m readingroom")
    commands = parser.add_subparsers(required=True)

    p = commands.add_parser("ingest", help="read the PDFs and fill the shelf")
    p.add_argument("--documents", default="documents")
    p.add_argument("--shelf", default="shelf")
    p.set_defaults(command=ingest)

    p = commands.add_parser("inspect", help="show what the shelf holds")
    p.add_argument("document", help="e.g. gdpr")
    shown = p.add_mutually_exclusive_group()
    shown.add_argument("--page", type=int, help="show this page's clean text")
    shown.add_argument("--article", type=int, help="show this article's text")
    shown.add_argument("--recital", type=int, help="show this recital's text")
    shown.add_argument("--annex", help="show this annex's text, e.g. III")
    p.add_argument("--shelf", default="shelf")
    p.set_defaults(command=inspect)

    p = commands.add_parser("search", help="keyword search over articles, recitals and annexes")
    p.add_argument("query", help='words to find; put a phrase in "double quotes"')
    p.add_argument("--law", action="append", help="only this law, e.g. gdpr (repeatable)")
    p.add_argument("--kind", action="append", choices=["article", "recital", "annex"],
                   help="only this kind of part (repeatable)")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--shelf", default="shelf")
    p.set_defaults(command=search)

    p = commands.add_parser("ask", help="research a question and answer it from the shelf")
    p.add_argument("question")
    p.add_argument("--model", help="an OpenRouter model name; default from .env or openai/gpt-5-mini")
    p.add_argument("--max-tool-calls", type=int, default=MAX_TOOL_CALLS,
                   help="searches and reads together")
    p.add_argument("--shelf", default="shelf")
    p.set_defaults(command=ask)
    return parser


if __name__ == "__main__":
    sys.exit(main())
