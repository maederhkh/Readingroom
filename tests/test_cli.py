"""The two commands: `ingest` builds the shelf, `inspect` shows what is on it."""
import pymupdf
import pytest

from readingroom.__main__ import main


@pytest.fixture
def documents(tmp_path):
    """A one-page PDF: a header in the top strip, and one line of body text."""
    folder = tmp_path / "documents"
    folder.mkdir()
    pdf = pymupdf.open()
    page = pdf.new_page(width=595, height=842)          # A4, in points
    page.insert_text((40, 50), "L 1/1  Official Journal of the European Union", fontsize=9.6)
    page.insert_text((70, 200), "Article 1", fontsize=9.6)
    page.insert_text((70, 215), "Subject-matter and objectives", fontsize=9.6)
    pdf.save(folder / "Tiny Law.pdf")
    pdf.close()
    return folder


def test_ingest_puts_each_pdf_on_the_shelf(documents, tmp_path):
    shelf = tmp_path / "shelf"
    assert main(["ingest", "--documents", str(documents), "--shelf", str(shelf)]) == 0
    text = (shelf / "tiny-law" / "text.txt").read_text(encoding="utf-8")
    assert text == "Article 1\nSubject-matter and objectives"


def test_inspect_shows_one_page(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    assert main(["inspect", "tiny-law", "--page", "1", "--shelf", str(shelf)]) == 0
    assert "Subject-matter and objectives" in capsys.readouterr().out


def test_inspect_without_a_page_summarises_the_document(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    main(["inspect", "tiny-law", "--shelf", str(shelf)])
    out = capsys.readouterr().out
    assert "Tiny Law.pdf" in out
    assert "1 pages" in out


def test_inspect_an_unknown_document_says_what_is_on_the_shelf(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    assert main(["inspect", "gdpr", "--shelf", str(shelf)]) == 1
    assert "tiny-law" in capsys.readouterr().err
