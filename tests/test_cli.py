"""The commands: `ingest` builds the shelf, `inspect` shows it, `search` searches it.

The `documents` fixture (a one-page PDF) lives in conftest.py.
"""
import pytest

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


@pytest.fixture
def fake_model(monkeypatch):
    """Put a scripted model in place of OpenRouter, so `ask` never reaches the network."""
    from tests.test_agent import FakeModel
    import readingroom.__main__ as cli

    def install(*replies):
        model = FakeModel(*replies)
        monkeypatch.setattr(cli, "OpenRouterModel", lambda name=None: model)
        monkeypatch.setattr(cli, "_load_env", lambda: None)
        return model
    return install


def test_ask_shows_each_search_then_the_answer_then_the_cost(documents, tmp_path, capsys, fake_model):
    from tests.test_agent import answers, asks_to_search
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    fake_model(asks_to_search("objectives"), answers("Article 1 sets out the objectives [tiny-law/article-1, p. 1]."))
    capsys.readouterr()
    assert main(["ask", "What are the objectives?", "--shelf", str(shelf)]) == 0
    out = capsys.readouterr().out
    assert "search: objectives" in out and "tiny-law/article-1" in out
    assert "Article 1 sets out the objectives" in out
    assert "1 search · 2 rounds · 360 tokens" in out


def test_ask_warns_when_the_answer_was_cut_off(documents, tmp_path, capsys, fake_model):
    from tests.test_agent import answers
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    fake_model(answers("Article 1 says", cut_off=True))
    capsys.readouterr()
    main(["ask", "q", "--shelf", str(shelf)])
    assert "cut off" in capsys.readouterr().out


def test_ask_without_a_key_says_where_to_put_it(documents, tmp_path, capsys, monkeypatch):
    import readingroom.__main__ as cli
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    monkeypatch.setattr(cli, "_load_env", lambda: None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    capsys.readouterr()
    assert main(["ask", "q", "--shelf", str(shelf)]) == 1
    assert ".env" in capsys.readouterr().err


def test_inspect_an_unknown_document_says_what_is_on_the_shelf(documents, tmp_path, capsys):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    capsys.readouterr()
    assert main(["inspect", "gdpr", "--shelf", str(shelf)]) == 1
    assert "tiny-law" in capsys.readouterr().err
