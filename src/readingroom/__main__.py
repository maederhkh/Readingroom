"""The commands.

    python -m readingroom ingest                  read documents/ and fill shelf/
    python -m readingroom inspect gdpr            one document: its details and articles
    python -m readingroom inspect gdpr --page 35
    python -m readingroom inspect gdpr --article 5
"""
import argparse
import hashlib
import pathlib
import sys

from readingroom import shelf
from readingroom.articles import find_articles
from readingroom.pdf import read_clean_text


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
        shelf.save_articles(shelf_dir, doc_id, articles, doc)
        print(f"{doc_id:24} {doc.page_count:4} pages  {len(doc.text):>9,} characters  "
              f"{len(articles):4} articles  <- {pdf.name}")
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
    d = shelf.details(shelf_dir, args.document)
    print(f"{args.document}: {d['pages']} pages, {d['characters']:,} characters, from {d['source']}")
    for a in shelf.load_articles(shelf_dir, args.document):
        print(f"  Article {a['number']:<4} {_pages(a):>10}   {a['title']}")
    return 0


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
    p.add_argument("--shelf", default="shelf")
    p.set_defaults(command=inspect)
    return parser


if __name__ == "__main__":
    sys.exit(main())
