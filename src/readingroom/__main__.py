"""The commands.

    python -m readingroom ingest               read documents/ and fill shelf/
    python -m readingroom inspect gdpr         what the shelf holds for one document
    python -m readingroom inspect gdpr --page 35
"""
import argparse
import hashlib
import pathlib
import sys

from readingroom import shelf
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
        print(f"{doc_id:24} {doc.page_count:4} pages  {len(doc.text):>9,} characters  <- {pdf.name}")
    return 0


def inspect(args) -> int:
    shelf_dir = pathlib.Path(args.shelf)
    held = shelf.list_documents(shelf_dir)
    if args.document not in held:
        print(f"'{args.document}' is not on the shelf. It holds: {', '.join(held) or 'nothing'}",
              file=sys.stderr)
        return 1
    if args.page is None:
        d = shelf.details(shelf_dir, args.document)
        print(f"{args.document}: {d['pages']} pages, {d['characters']:,} characters, from {d['source']}")
        return 0
    doc = shelf.load(shelf_dir, args.document)
    try:
        print(doc.page_text(args.page))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m readingroom")
    commands = parser.add_subparsers(required=True)

    p = commands.add_parser("ingest", help="read the PDFs and fill the shelf")
    p.add_argument("--documents", default="documents")
    p.add_argument("--shelf", default="shelf")
    p.set_defaults(command=ingest)

    p = commands.add_parser("inspect", help="show what the shelf holds")
    p.add_argument("document", help="e.g. gdpr")
    p.add_argument("--page", type=int, help="show this page's clean text")
    p.add_argument("--shelf", default="shelf")
    p.set_defaults(command=inspect)
    return parser


if __name__ == "__main__":
    sys.exit(main())
