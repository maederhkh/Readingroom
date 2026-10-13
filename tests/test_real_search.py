"""Keyword search on the three real laws: PDF -> shelf -> search. Skips without documents/."""
import pathlib

import pytest

from readingroom.__main__ import main
from readingroom.search import KeywordIndex, load_passages, tokenize

DOCUMENTS = pathlib.Path(__file__).parent.parent / "documents"


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    if not all((DOCUMENTS / n).exists() for n in ("GDPR.pdf", "EU AI act.pdf", "Digital Services act.pdf")):
        pytest.skip("the three laws are not all in documents/")
    shelf = tmp_path_factory.mktemp("shelf")
    main(["ingest", "--documents", str(DOCUMENTS), "--shelf", str(shelf)])
    return KeywordIndex(load_passages(shelf))


def test_every_article_recital_and_annex_of_every_law_is_searchable(index):
    kinds = [p.kind for p in index.passages]
    assert kinds.count("article") == 99 + 113 + 93
    assert kinds.count("recital") == 173 + 180 + 156
    assert kinds.count("annex") == 13


def test_the_phrase_that_was_invisible_is_found_in_recital_71(index):
    # Before recitals were searchable this returned nothing at all.
    [hit] = index.search('"explanation of the decision"', laws=["gdpr"])
    assert hit.passage.bookmark == "gdpr/recital-71"


def test_accuracy_in_the_gdpr_finds_exactly_the_two_articles_using_the_word(index):
    # Article 18 says "accuracy" twice, Article 5 once - so keyword search ranks 18 first,
    # even though Article 5 is THE accuracy principle. Counting words cannot know that.
    # (An earlier version of this test expected Article 5 first; that was a hope, not
    # something keyword search promises.)
    hits = index.search("accuracy", laws=["gdpr"], limit=50)
    assert [h.passage.bookmark for h in hits] == ["gdpr/article-18", "gdpr/article-5"]
    assert all("accuracy" in h.snippet for h in hits)


def test_accuracy_robustness_cybersecurity_finds_ai_act_article_15_first(index):
    top = index.search("accuracy robustness cybersecurity")[0]
    assert top.passage.bookmark == "eu-ai-act/article-15"


def test_every_phrase_hit_really_contains_the_phrase(index):
    hits = index.search('"kept up to date"', limit=50)
    assert "gdpr/article-5" in [h.passage.bookmark for h in hits]
    for hit in hits:
        assert " kept up to date " in " " + " ".join(tokenize(hit.passage.text)) + " "


def test_nonsense_finds_nothing(index):
    assert index.search("zebra xylophone") == []
