"""The articles found in the three real laws in documents/. Skips when a PDF is missing."""
import pathlib
import re
from functools import cache

import pytest

from readingroom.articles import find_articles
from readingroom.pdf import read_clean_text

DOCUMENTS = pathlib.Path(__file__).parent.parent / "documents"
ARTICLE_COUNT = {"GDPR.pdf": 99, "EU AI act.pdf": 113, "Digital Services act.pdf": 93}
HEADING_LINE = re.compile(r"^(?:CHAPTER [IVXLC]+|SECTION \d+|Section \d+)\s*$", re.MULTILINE)


@cache
def load(name):
    path = DOCUMENTS / name
    if not path.exists():
        pytest.skip(f"{name} is not in documents/")
    doc = read_clean_text(path)
    return doc, {a.number: a for a in find_articles(doc.text)}


@pytest.mark.parametrize("name", ARTICLE_COUNT)
def test_exactly_the_right_articles_are_found(name):
    _, articles = load(name)
    assert sorted(articles) == list(range(1, ARTICLE_COUNT[name] + 1))


@pytest.mark.parametrize("name", ARTICLE_COUNT)
def test_every_article_text_starts_with_its_own_heading(name):
    doc, articles = load(name)
    for n, a in articles.items():
        assert doc.text[a.start:a.end].startswith(f"Article {n}\n{a.title.split()[0]}")


@pytest.mark.parametrize("name", ARTICLE_COUNT)
def test_no_article_swallows_a_chapter_heading_or_the_closing_sentence(name):
    doc, articles = load(name)
    for a in articles.values():
        text = doc.text[a.start:a.end]
        assert HEADING_LINE.search(text) is None, a.number
        assert "This Regulation shall be binding in its entirety" not in text, a.number


def test_gdpr_article_5():
    doc, articles = load("GDPR.pdf")
    a = articles[5]
    assert a.title == "Principles relating to processing of personal data"
    assert a.chapter == "CHAPTER II — Principles"
    assert a.section is None
    assert (doc.page_at(a.start), doc.page_at(a.end - 1)) == (35, 36)
    assert "(‘accuracy’);\n(e)" in doc.text[a.start:a.end]


def test_gdpr_article_12_two_line_title():
    _, articles = load("GDPR.pdf")
    assert articles[12].title == (
        "Transparent information, communication and modalities for the exercise of the rights of the data subject"
    )


def test_a_new_chapter_clears_the_section():
    # Chapter IV has sections; Chapter V, which starts at Article 44, has none.
    _, articles = load("GDPR.pdf")
    assert articles[43].section is not None
    assert articles[44].chapter.startswith("CHAPTER V —")
    assert articles[44].section is None


def test_ai_act_titles_are_kept_exactly_as_printed():
    _, articles = load("EU AI act.pdf")
    assert articles[1].title == "Subject matter`"        # stray backtick, official PDF
    assert articles[111].title.endswith("already placed on the marked")  # official typo


def test_ai_act_last_article_stops_before_the_annexes():
    doc, articles = load("EU AI act.pdf")
    assert "ANNEX" not in doc.text[articles[113].start:articles[113].end]


def test_dsa_two_line_section_title():
    _, articles = load("Digital Services act.pdf")
    assert articles[33].section.endswith("to manage systemic risks")
