"""Finding the articles in a law's clean text.

The excerpts are stitched together from real lines of the clean GDPR and AI Act texts,
each line copied verbatim; only the order of the pieces is arranged for the test.
"""
from readingroom.articles import find_articles

GDPR_EXCERPT = "\n".join([
    "HAVE ADOPTED THIS REGULATION:",
    "CHAPTER I",
    "General provisions",
    "Article 1",
    "Subject-matter and objectives",
    "1. This Regulation lays down rules relating to the protection of natural persons with regard to the processing of",
    "Article 11",
    "Processing which does not require identification",
    "2. Where, in cases referred to in paragraph 1 of this Article, the controller is able to demonstrate that it is not in a",
    "those articles, provides additional information enabling his or her identification.",
    "CHAPTER III",
    "Rights of the data subject",
    "Section 1",
    "Transparency and modalities",
    "Article 12",
    "Transparent information, communication and modalities for the exercise of the rights of the data",
    "subject",
    "1. The controller shall take appropriate measures to provide any information referred to in Articles 13 and 14 and",
    "This Regulation shall be binding in its entirety and directly applicable in all Member States.",
    "Done at Brussels, 13 June 2024.",
])

AI_ACT_ENDING = "\n".join([
    "Article 1",
    "Subject matter`",   # the stray backtick is in the official PDF
    "1. The purpose of this Regulation is to improve the functioning of the internal market and promote the uptake of",
    "Article 113",
    "Entry into force and application",
    "It shall apply from 2 August 2026.",
    "(c) Article 6(1) and the corresponding obligations in this Regulation shall apply from 2 August 2027.",
    "This Regulation shall be binding in its entirety and directly applicable in all Member States.",
    "Done at Brussels, 13 June 2024.",
    "R. METSOLA M. MICHEL",
    "ANNEX VIII",
    "Information to be submitted upon the registration of high-risk AI systems in accordance with",
    "Article 49",
    "Section A — Information to be submitted by providers of high-risk AI systems in accordance with Article 49(1)",
])


def by_number(text):
    return {a.number: a for a in find_articles(text)}


def test_articles_are_found_in_order():
    assert [a.number for a in find_articles(GDPR_EXCERPT)] == [1, 11, 12]


def test_title_is_the_line_after_the_heading():
    assert by_number(GDPR_EXCERPT)[11].title == "Processing which does not require identification"


def test_a_title_continues_onto_lines_that_start_with_a_small_letter():
    assert by_number(GDPR_EXCERPT)[12].title == (
        "Transparent information, communication and modalities for the exercise of the rights of the data subject"
    )


def test_each_article_knows_its_chapter():
    articles = by_number(GDPR_EXCERPT)
    assert articles[1].chapter == "CHAPTER I — General provisions"
    assert articles[11].chapter == "CHAPTER I — General provisions"
    assert articles[12].chapter == "CHAPTER III — Rights of the data subject"


def test_each_article_knows_its_section_if_it_has_one():
    articles = by_number(GDPR_EXCERPT)
    assert articles[11].section is None
    assert articles[12].section == "Section 1 — Transparency and modalities"


def test_an_article_runs_from_its_heading_to_the_next_heading():
    a = by_number(GDPR_EXCERPT)[11]
    text = GDPR_EXCERPT[a.start:a.end]
    assert text.startswith("Article 11\nProcessing which does not require identification\n")
    assert text.endswith("enabling his or her identification.")  # CHAPTER III is not included


def test_the_last_article_stops_at_the_closing_sentence():
    a = by_number(GDPR_EXCERPT)[12]
    assert GDPR_EXCERPT[a.start:a.end].endswith("referred to in Articles 13 and 14 and")


def test_nothing_after_the_closing_sentence_is_an_article():
    # Annex VIII's title wraps so that "Article 49" lands alone on a line.
    assert [a.number for a in find_articles(AI_ACT_ENDING)] == [1, 113]


def test_text_with_no_articles_has_none():
    assert find_articles("Whereas:\n(1) The protection of natural persons") == []
