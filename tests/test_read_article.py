"""read_article: open a whole article by the bookmark a search result gave you."""
import pathlib

import pytest

from readingroom.__main__ import main
from readingroom.mcp_server import read_article_description, read_article_result
from readingroom.shelf import articles_by_bookmark
from tests.test_mcp_server import call_over_connection

LIBRARY = {
    "gdpr/article-22": {"law": "gdpr", "article": 22,
                        "title": "Automated individual decision-making, including profiling",
                        "chapter": "CHAPTER III — Rights of the data subject",
                        "section": "Section 4 — Right to object and automated individual decision-making",
                        "page_start": 46, "page_end": 46,
                        "text": "Article 22\nAutomated individual decision-making, including profiling\n"
                                "1. The data subject shall have the right not to be subject to a decision...\n"
                                "2. Paragraph 1 shall not apply if the decision:"},
    "gdpr/article-99": {"law": "gdpr", "article": 99, "title": "Entry into force and application",
                        "chapter": "CHAPTER XI — Final provisions", "section": None,
                        "page_start": 87, "page_end": 88, "text": "Article 99\n..."},
    "gdpr/article-1": {"law": "gdpr", "article": 1, "title": "Subject-matter and objectives",
                       "chapter": "CHAPTER I — General provisions", "section": None,
                       "page_start": 32, "page_end": 32, "text": "Article 1\n..."},
}
LAWS = ["gdpr"]


def test_the_whole_article_comes_back_with_where_it_sits():
    assert read_article_result(LIBRARY, LAWS, "gdpr/article-22") == {
        "bookmark": "gdpr/article-22",
        "law": "gdpr",
        "article": 22,
        "title": "Automated individual decision-making, including profiling",
        "chapter": "CHAPTER III — Rights of the data subject",
        "section": "Section 4 — Right to object and automated individual decision-making",
        "pages": "46",
        "text": LIBRARY["gdpr/article-22"]["text"],
    }


def test_pages_spanning_two_pages_are_shown_as_a_range():
    assert read_article_result(LIBRARY, LAWS, "gdpr/article-99")["pages"] == "87–88"


def test_a_bookmark_in_the_wrong_shape_is_refused_with_an_example():
    with pytest.raises(ValueError, match="gdpr/article-22"):
        read_article_result(LIBRARY, LAWS, "GDPR Article 22")


def test_an_unknown_law_is_refused_with_the_laws_that_exist():
    with pytest.raises(ValueError, match="No law called 'dsa'.*Laws available: gdpr"):
        read_article_result(LIBRARY, LAWS, "dsa/article-5")


def test_an_article_that_does_not_exist_is_refused_with_the_range_that_does():
    with pytest.raises(ValueError, match="No gdpr/article-200. gdpr has Articles 1–99."):
        read_article_result(LIBRARY, LAWS, "gdpr/article-200")


def test_the_description_says_where_bookmarks_come_from():
    text = read_article_description(LAWS)
    assert "keyword_search" in text
    assert "gdpr/article-22" in text


def test_the_library_is_loaded_from_the_shelf(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    library = articles_by_bookmark(shelf)
    assert list(library) == ["tiny-law/article-1"]
    assert library["tiny-law/article-1"]["text"] == "Article 1\nSubject-matter and objectives"


def test_claude_code_can_read_an_article_over_a_real_connection(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    answer = call_over_connection(shelf, {"bookmark": "tiny-law/article-1"}, tool="read_article")
    assert not answer.is_error
    assert answer.structured_content["text"] == "Article 1\nSubject-matter and objectives"


def test_a_bad_bookmark_tells_claude_code_why(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    answer = call_over_connection(shelf, {"bookmark": "tiny-law/article-7"}, tool="read_article")
    assert answer.is_error
    assert "No tiny-law/article-7. tiny-law has Articles 1–1." in answer.content[0].text


@pytest.mark.skipif(not (pathlib.Path(__file__).parent.parent / "documents" / "GDPR.pdf").exists(),
                    reason="GDPR.pdf is not in documents/")
def test_gdpr_article_22_comes_back_with_its_exceptions(tmp_path):
    # The case that motivated the tool: the search excerpt shows only paragraph 1.
    docs = pathlib.Path(__file__).parent.parent / "documents"
    main(["ingest", "--documents", str(docs), "--shelf", str(tmp_path)])
    article = read_article_result(articles_by_bookmark(tmp_path), ["gdpr"], "gdpr/article-22")
    assert "Paragraph 1 shall not apply if the decision" in article["text"]
    assert article["pages"] == "46"
