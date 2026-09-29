"""Saving clean text to the shelf and reading it back."""
import pathlib

from readingroom import shelf
from readingroom.text import CleanText


def test_document_id_comes_from_the_file_name():
    assert shelf.document_id(pathlib.Path("documents/GDPR.pdf")) == "gdpr"
    assert shelf.document_id(pathlib.Path("documents/EU AI act.pdf")) == "eu-ai-act"
    assert shelf.document_id(pathlib.Path("Digital Services act.pdf")) == "digital-services-act"


def test_saved_text_comes_back_identical(tmp_path):
    doc = CleanText.from_pages(["Article 5\nPrinciples", "(e)  kept in a form"])
    shelf.save(tmp_path, "gdpr", doc, source_name="GDPR.pdf", source_sha256="abc")
    assert shelf.load(tmp_path, "gdpr") == doc


def test_saved_file_keeps_single_character_line_breaks(tmp_path):
    # On Windows a plain write turns "\n" into "\r\n", which would shift every
    # character position after the first line break - and every bookmark with it.
    doc = CleanText.from_pages(["line one\nline two", "page two"])
    shelf.save(tmp_path, "doc", doc, source_name="x.pdf", source_sha256="abc")
    raw = (tmp_path / "doc" / "text.txt").read_bytes()
    assert b"\r" not in raw
    assert len(raw.decode("utf-8")) == len(doc.text)


def test_shelf_lists_the_documents_it_holds(tmp_path):
    doc = CleanText.from_pages(["x"])
    shelf.save(tmp_path, "gdpr", doc, source_name="GDPR.pdf", source_sha256="a")
    shelf.save(tmp_path, "dsa", doc, source_name="DSA.pdf", source_sha256="b")
    assert shelf.list_documents(tmp_path) == ["dsa", "gdpr"]


def test_article_bookmarks_are_saved_with_their_pages(tmp_path):
    from readingroom.articles import Article
    doc = CleanText.from_pages(["Article 1\nScope\nText on page one", "more text on page two"])
    article = Article(number=1, title="Scope", chapter="CHAPTER I — General", section=None,
                      start=0, end=len(doc.text))
    shelf.save_articles(tmp_path, "law", [article], doc)
    [saved] = shelf.load_articles(tmp_path, "law")
    assert saved == {
        "number": 1, "title": "Scope", "chapter": "CHAPTER I — General", "section": None,
        "page_start": 1, "page_end": 2, "start": 0, "end": len(doc.text),
    }


def test_details_record_where_the_text_came_from(tmp_path):
    doc = CleanText.from_pages(["one", "two"])
    shelf.save(tmp_path, "gdpr", doc, source_name="GDPR.pdf", source_sha256="abc123")
    details = shelf.details(tmp_path, "gdpr")
    assert details["source"] == "GDPR.pdf"
    assert details["source_sha256"] == "abc123"
    assert details["pages"] == 2
    assert details["characters"] == len("one\ntwo")
