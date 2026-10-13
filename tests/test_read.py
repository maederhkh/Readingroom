"""read and list_documents: open any part of a law by its bookmark, and see what is on the shelf."""
import pathlib

import pytest

from readingroom.__main__ import main
from readingroom.mcp_server import list_documents_result, read_description, read_result
from readingroom.shelf import units_by_bookmark
from tests.test_mcp_server import call_over_connection


def unit(law, kind, number, title=None, chapter=None, section=None, pages=(1, 1), text="..."):
    label = {"article": "Article", "recital": "Recital", "annex": "Annex"}[kind]
    return {"law": law, "kind": kind, "number": number, "label": f"{label} {number}", "title": title,
            "chapter": chapter, "section": section, "page_start": pages[0], "page_end": pages[1], "text": text}


LIBRARY = {
    "gdpr/article-1": unit("gdpr", "article", 1, "Subject-matter and objectives", pages=(32, 32)),
    "gdpr/article-22": unit("gdpr", "article", 22, "Automated individual decision-making, including profiling",
                            "CHAPTER III — Rights of the data subject",
                            "Section 4 — Right to object and automated individual decision-making",
                            pages=(46, 46), text="Article 22\n...\n2. Paragraph 1 shall not apply if the decision:"),
    "gdpr/article-99": unit("gdpr", "article", 99, "Entry into force and application", pages=(87, 88)),
    "gdpr/recital-1": unit("gdpr", "recital", 1, pages=(1, 1)),
    "gdpr/recital-71": unit("gdpr", "recital", 71, pages=(14, 14),
                            text="(71) ... to obtain an explanation of the decision reached ..."),
    "eu-ai-act/annex-I": unit("eu-ai-act", "annex", "I", "List of Union harmonisation legislation"),
    "eu-ai-act/annex-III": unit("eu-ai-act", "annex", "III", "High-risk AI systems referred to in Article 6(2)",
                                pages=(127, 129)),
}
LAWS = ["eu-ai-act", "gdpr"]


def test_an_article_comes_back_whole_with_where_it_sits():
    assert read_result(LIBRARY, LAWS, "gdpr/article-22") == {
        "bookmark": "gdpr/article-22",
        "law": "gdpr",
        "kind": "article",
        "label": "Article 22",
        "title": "Automated individual decision-making, including profiling",
        "chapter": "CHAPTER III — Rights of the data subject",
        "section": "Section 4 — Right to object and automated individual decision-making",
        "pages": "46",
        "text": "Article 22\n...\n2. Paragraph 1 shall not apply if the decision:",
    }


def test_a_recital_can_be_read():
    result = read_result(LIBRARY, LAWS, "gdpr/recital-71")
    assert (result["kind"], result["label"], result["pages"]) == ("recital", "Recital 71", "14")
    assert "explanation of the decision reached" in result["text"]


def test_an_annex_can_be_read():
    result = read_result(LIBRARY, LAWS, "eu-ai-act/annex-III")
    assert (result["label"], result["title"], result["pages"]) == (
        "Annex III", "High-risk AI systems referred to in Article 6(2)", "127–129")


def test_a_bookmark_in_the_wrong_shape_is_refused_with_examples():
    with pytest.raises(ValueError, match="gdpr/article-22.*gdpr/recital-71.*eu-ai-act/annex-III"):
        read_result(LIBRARY, LAWS, "GDPR Article 22")


def test_an_unknown_law_is_refused_with_the_laws_that_exist():
    with pytest.raises(ValueError, match="No law called 'dsa'.*Laws available: eu-ai-act, gdpr"):
        read_result(LIBRARY, LAWS, "dsa/article-5")


def test_a_number_that_does_not_exist_is_refused_with_the_range_that_does():
    with pytest.raises(ValueError, match="No gdpr/article-200. gdpr has Articles 1–99."):
        read_result(LIBRARY, LAWS, "gdpr/article-200")
    with pytest.raises(ValueError, match="No gdpr/recital-200. gdpr has Recitals 1–71."):
        read_result(LIBRARY, LAWS, "gdpr/recital-200")


def test_an_annex_in_a_law_without_annexes_says_so():
    with pytest.raises(ValueError, match="gdpr has no annexes."):
        read_result(LIBRARY, LAWS, "gdpr/annex-I")


def test_a_missing_annex_lists_the_annexes_that_exist():
    with pytest.raises(ValueError, match="No eu-ai-act/annex-II. eu-ai-act has Annexes I, III."):
        read_result(LIBRARY, LAWS, "eu-ai-act/annex-II")


def test_the_description_says_where_bookmarks_come_from_and_what_each_kind_is():
    text = read_description(LAWS)
    assert "keyword_search" in text
    assert "gdpr/article-22" in text and "gdpr/recital-71" in text and "eu-ai-act/annex-III" in text


def test_list_documents_shows_each_law_with_its_parts(full_documents, documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(full_documents), "--shelf", str(shelf)])
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    assert list_documents_result(shelf) == {"documents": [
        {"law": "full-law", "title": "Full Law.pdf", "pages": 1, "articles": 1, "recitals": 2, "annexes": 1},
        {"law": "tiny-law", "title": "Tiny Law.pdf", "pages": 1, "articles": 1, "recitals": 0, "annexes": 0},
    ]}


def test_the_library_holds_every_kind_from_the_shelf(full_documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(full_documents), "--shelf", str(shelf)])
    library = units_by_bookmark(shelf)
    assert list(library) == ["full-law/article-1", "full-law/recital-1", "full-law/recital-2", "full-law/annex-I"]
    assert library["full-law/recital-2"]["text"] == "(2) The second recital explains how."
    assert library["full-law/annex-I"]["title"] == "List of things"


def test_claude_code_can_read_a_recital_over_a_real_connection(full_documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(full_documents), "--shelf", str(shelf)])
    answer = call_over_connection(shelf, {"bookmark": "full-law/recital-1"}, tool="read")
    assert not answer.is_error
    assert answer.structured_content["text"] == "(1) The first recital explains why."


def test_a_bad_bookmark_tells_claude_code_why(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    answer = call_over_connection(shelf, {"bookmark": "tiny-law/article-7"}, tool="read")
    assert answer.is_error
    assert "No tiny-law/article-7. tiny-law has Articles 1–1." in answer.content[0].text


def test_claude_code_can_list_the_documents_over_a_real_connection(documents, tmp_path):
    shelf = tmp_path / "shelf"
    main(["ingest", "--documents", str(documents), "--shelf", str(shelf)])
    answer = call_over_connection(shelf, {}, tool="list_documents")
    assert answer.structured_content["documents"][0]["law"] == "tiny-law"


REAL = pathlib.Path(__file__).parent.parent / "documents"


@pytest.mark.skipif(not all((REAL / n).exists() for n in ("GDPR.pdf", "EU AI act.pdf", "Digital Services act.pdf")),
                    reason="the three laws are not all in documents/")
def test_the_real_shelf(tmp_path):
    main(["ingest", "--documents", str(REAL), "--shelf", str(tmp_path)])
    library = units_by_bookmark(tmp_path)
    laws = ["digital-services-act", "eu-ai-act", "gdpr"]
    # The case that motivated read_article: the search excerpt shows only paragraph 1.
    assert "Paragraph 1 shall not apply if the decision" in read_result(library, laws, "gdpr/article-22")["text"]
    # The case that motivated recitals: a phrase found nowhere in the articles.
    assert "explanation of the decision" in read_result(library, laws, "gdpr/recital-71")["text"]
    assert read_result(library, laws, "eu-ai-act/annex-III")["pages"] == "127–129"
    listed = {d["law"]: d for d in list_documents_result(tmp_path)["documents"]}
    assert listed["gdpr"]["title"].startswith("REGULATION (EU) 2016/679 OF THE EUROPEAN PARLIAMENT")
    assert listed["gdpr"]["title"].endswith("(General Data Protection Regulation)")
    assert listed["eu-ai-act"]["title"].endswith("(Artificial Intelligence Act)")
    assert (listed["eu-ai-act"]["articles"], listed["eu-ai-act"]["recitals"], listed["eu-ai-act"]["annexes"]) == (113, 180, 13)


def test_upper_and_lower_case_do_not_matter_in_a_bookmark():
    # In the first real run the model asked for "eu-ai-act/annex-iii", was refused, and
    # spent an extra search finding the spelling "annex-III".
    assert read_result(LIBRARY, LAWS, "eu-ai-act/annex-iii")["bookmark"] == "eu-ai-act/annex-III"
    assert read_result(LIBRARY, LAWS, "GDPR/Recital-71")["bookmark"] == "gdpr/recital-71"
