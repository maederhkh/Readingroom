"""Finding the recitals and annexes - the half of each law outside the articles.

The excerpts are stitched together from real lines of the clean GDPR and AI Act texts,
each line copied verbatim.
"""
from readingroom.units import find_annexes, find_recitals

PREAMBLE = "\n".join([
    "Acting in accordance with the ordinary legislative procedure (3),",
    "Whereas:",
    "(1) The protection of natural persons in relation to the processing of personal data is a",
    "Article 8(1) of the Charter of Fundamental Rights of the European Union (the ‘Charter’) and",
    "(2) The principles of, and rules on the protection of natural persons with regard to the",
    "(3) Directive 95/46/EC of the European Parliament and of the Council (4) seeks to harmonise",
    "Directive 2002/58/EC should be reviewed in particular in order to ensure consistency with",
    "HAVE ADOPTED THIS REGULATION:",
    "CHAPTER I",
    "General provisions",
    "Article 1",
])

ENDING = "\n".join([
    "This Regulation shall be binding in its entirety and directly applicable in all Member States.",
    "Done at Brussels, 13 June 2024.",
    "R. METSOLA M. MICHEL",
    "ANNEX III",
    "High-risk AI systems referred to in Article 6(2)",
    "High-risk AI systems pursuant to Article 6(2) are the AI systems listed in any of the following areas:",
    "ANNEX VIII",
    "Information to be submitted upon the registration of high-risk AI systems in accordance with",
    "Article 49",
    "Section A — Information to be submitted by providers of high-risk AI systems in accordance with Article 49(1)",
])


def test_recitals_are_found_in_order():
    assert [r.number for r in find_recitals(PREAMBLE)] == [1, 2, 3]


def test_a_recital_runs_from_its_number_to_the_next_recital():
    first = find_recitals(PREAMBLE)[0]
    assert PREAMBLE[first.start:first.end] == (
        "(1) The protection of natural persons in relation to the processing of personal data is a\n"
        "Article 8(1) of the Charter of Fundamental Rights of the European Union (the ‘Charter’) and")


def test_the_last_recital_stops_before_the_enacting_formula():
    last = find_recitals(PREAMBLE)[-1]
    assert PREAMBLE[last.start:last.end].endswith("in order to ensure consistency with")


def test_a_line_starting_with_a_number_out_of_sequence_is_not_a_new_recital():
    # "(4)" here would be a footnote reference or citation; the next recital is (2).
    text = "Whereas:\n(1) First recital\n(4) a line that merely starts with a number\n(2) Second\nHAVE ADOPTED THIS REGULATION:"
    recitals = find_recitals(text)
    assert [r.number for r in recitals] == [1, 2]
    assert text[recitals[0].start:recitals[0].end] == "(1) First recital\n(4) a line that merely starts with a number"


def test_text_without_recitals_has_none():
    assert find_recitals("Article 1\nSubject-matter") == []


def test_annexes_are_found_after_the_closing_sentence():
    assert [a.number for a in find_annexes(ENDING)] == ["III", "VIII"]


def test_an_annex_title_is_the_line_after_its_heading():
    assert find_annexes(ENDING)[0].title == "High-risk AI systems referred to in Article 6(2)"


def test_an_annex_title_continues_after_a_line_ending_mid_phrase():
    # The second line starts with a capital, so the small-letter rule alone would stop
    # at "...in accordance with". Checked against the PDF's bold printing.
    assert find_annexes(ENDING)[1].title == (
        "Information to be submitted upon the registration of high-risk AI systems "
        "in accordance with Article 49")


def test_an_annex_runs_from_its_heading_to_the_next_annex():
    annex = find_annexes(ENDING)[0]
    text = ENDING[annex.start:annex.end]
    assert text.startswith("ANNEX III\nHigh-risk AI systems referred to in Article 6(2)\n")
    assert text.endswith("listed in any of the following areas:")


def test_the_last_annex_runs_to_the_end_of_the_text():
    assert ENDING[find_annexes(ENDING)[-1].start:].startswith("ANNEX VIII")
    assert find_annexes(ENDING)[-1].end == len(ENDING)


def test_an_annex_heading_before_the_closing_sentence_is_not_an_annex():
    # Never happens in the three laws (cross-references are written "Annex II"), so the
    # real-document tests cannot guard this rule - this one does.
    text = "Article 6\nas set out in\nANNEX II\nof this Regulation.\n" + ENDING
    assert [a.number for a in find_annexes(text)] == ["III", "VIII"]


def test_a_law_without_annexes_has_none():
    assert find_annexes("This Regulation shall be binding in its entirety and directly applicable "
                        "in all Member States.\nDone at Strasbourg") == []
