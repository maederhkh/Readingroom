"""The shelf on disk: one folder per document.

    shelf/gdpr/text.txt        the clean text - open it and read it
    shelf/gdpr/pages.json      where each page begins, and which PDF it came from
    shelf/gdpr/articles.json   one bookmark per article: title, chapter, pages, position
"""
import json
import pathlib
import re
from dataclasses import asdict

from readingroom.articles import Article
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


def save_articles(shelf: pathlib.Path, doc_id: str, articles: list[Article], doc: CleanText) -> None:
    records = []
    for article in articles:
        record = asdict(article)
        # Pages are looked up now so a reader of articles.json never has to.
        record["page_start"] = doc.page_at(article.start)
        record["page_end"] = doc.page_at(article.end - 1)
        records.append(record)
    text = json.dumps(records, indent=2, ensure_ascii=False)
    (shelf / doc_id).mkdir(parents=True, exist_ok=True)
    (shelf / doc_id / "articles.json").write_text(text, encoding="utf-8")


def save_units(shelf: pathlib.Path, doc_id: str, kind: str, units: list, doc: CleanText) -> None:
    """Save recitals or annexes as bookmarks: shelf/<doc>/recitals.json or annexes.json."""
    records = []
    for unit in units:
        record = asdict(unit)
        record["page_start"] = doc.page_at(unit.start)
        record["page_end"] = doc.page_at(unit.end - 1)
        records.append(record)
    (shelf / doc_id).mkdir(parents=True, exist_ok=True)
    text = json.dumps(records, indent=2, ensure_ascii=False)
    (shelf / doc_id / f"{kind}.json").write_text(text, encoding="utf-8")


def load_units(shelf: pathlib.Path, doc_id: str, kind: str) -> list[dict]:
    """Recitals or annexes; empty for a law that has none, or a shelf built before they existed."""
    path = shelf / doc_id / f"{kind}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def load_articles(shelf: pathlib.Path, doc_id: str) -> list[dict]:
    return json.loads((shelf / doc_id / "articles.json").read_text(encoding="utf-8"))


KINDS = ("article", "recital", "annex")
LABEL = {"article": "Article", "recital": "Recital", "annex": "Annex"}


def units_by_bookmark(shelf: pathlib.Path) -> dict[str, dict]:
    """Every article, recital and annex on the shelf, by bookmark ("gdpr/recital-71"),
    with its full text cut from the one clean copy of its law. Search and reading both
    use this list, so they can never disagree about what exists."""
    library = {}
    for doc_id in list_documents(shelf):
        text = load(shelf, doc_id).text
        found = {"article": load_articles(shelf, doc_id),
                 "recital": load_units(shelf, doc_id, "recitals"),
                 "annex": load_units(shelf, doc_id, "annexes")}
        for kind in KINDS:
            for u in found[kind]:
                library[f"{doc_id}/{kind}-{u['number']}"] = {
                    "law": doc_id, "kind": kind, "number": u["number"],
                    "label": f"{LABEL[kind]} {u['number']}",
                    "title": u.get("title"), "chapter": u.get("chapter"), "section": u.get("section"),
                    "page_start": u["page_start"], "page_end": u["page_end"],
                    "text": text[u["start"]:u["end"]],
                }
    return library


def details(shelf: pathlib.Path, doc_id: str) -> dict:
    return json.loads((shelf / doc_id / "pages.json").read_text(encoding="utf-8"))


def list_documents(shelf: pathlib.Path) -> list[str]:
    if not shelf.exists():
        return []
    return sorted(p.name for p in shelf.iterdir() if (p / "pages.json").exists())
