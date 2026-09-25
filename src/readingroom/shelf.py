"""The shelf on disk: one folder per document.

    shelf/gdpr/text.txt      the clean text - open it and read it
    shelf/gdpr/pages.json    where each page begins, and which PDF it came from
"""
import json
import pathlib
import re

from readingroom.text import CleanText


def document_id(pdf: pathlib.Path) -> str:
    """A short, stable name for a document: "EU AI act.pdf" -> "eu-ai-act"."""
    return re.sub(r"[^a-z0-9]+", "-", pdf.stem.lower()).strip("-")


def save(shelf: pathlib.Path, doc_id: str, doc: CleanText, source_name: str, source_sha256: str) -> None:
    folder = shelf / doc_id
    folder.mkdir(parents=True, exist_ok=True)
    # newline="\n" stops Windows writing "\r\n", which would shift every position.
    (folder / "text.txt").write_text(doc.text, encoding="utf-8", newline="\n")
    details = {
        "source": source_name,
        "source_sha256": source_sha256,
        "pages": doc.page_count,
        "characters": len(doc.text),
        "page_starts": list(doc.page_starts),
    }
    (folder / "pages.json").write_text(json.dumps(details, indent=2), encoding="utf-8")


def load(shelf: pathlib.Path, doc_id: str) -> CleanText:
    # newline="" reads the text exactly as written, without translating line breaks.
    with open(shelf / doc_id / "text.txt", encoding="utf-8", newline="") as f:
        text = f.read()
    return CleanText(text=text, page_starts=tuple(details(shelf, doc_id)["page_starts"]))


def details(shelf: pathlib.Path, doc_id: str) -> dict:
    return json.loads((shelf / doc_id / "pages.json").read_text(encoding="utf-8"))


def list_documents(shelf: pathlib.Path) -> list[str]:
    if not shelf.exists():
        return []
    return sorted(p.name for p in shelf.iterdir() if (p / "pages.json").exists())
