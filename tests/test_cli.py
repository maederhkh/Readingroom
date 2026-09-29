"""The commands: `ingest` builds the shelf, `inspect` shows it, `search` searches it.

The `documents` fixture (a one-page PDF) lives in conftest.py.
"""
from readingroom.__main__ import main


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


def test_ingest_reports_how_many_articles_it_found(documents, tmp_path, capsys):
    main(["ingest", "--documents", str(documents), "--shelf", str(tmp_path / "shelf")])
    assert "1 articles" in capsys.readouterr().out


def test_inspect_lists_the_articles(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    main(["inspect", "tiny-law", "--shelf", str(shelf)])
    out = capsys.readouterr().out
    assert "Article 1" in out
    assert "Subject-matter and objectives" in out


def test_inspect_shows_one_article(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    assert main(["inspect", "tiny-law", "--article", "1", "--shelf", str(shelf)]) == 0
    assert "Article 1\nSubject-matter and objectives" in capsys.readouterr().out


def test_inspect_an_article_that_does_not_exist(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    assert main(["inspect", "tiny-law", "--article", "7", "--shelf", str(shelf)]) == 1
    assert "no Article 7" in capsys.readouterr().err


def test_search_prints_the_matching_article_with_its_bookmark(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    assert main(["search", "objectives", "--shelf", str(shelf)]) == 0
    out = capsys.readouterr().out
    assert "tiny-law · Article 1 · Subject-matter and objectives" in out
    assert "tiny-law/article-1" in out


def test_search_with_no_match_says_so(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    assert main(["search", "zebra", "--shelf", str(shelf)]) == 0
    assert "No articles contain these words." in capsys.readouterr().out


def test_inspect_an_unknown_document_says_what_is_on_the_shelf(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    assert main(["inspect", "gdpr", "--shelf", str(shelf)]) == 1
    assert "tiny-law" in capsys.readouterr().err
