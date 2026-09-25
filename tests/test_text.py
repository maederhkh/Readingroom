"""One document's clean text, and which page every character came from."""
import pytest

from readingroom.text import CleanText

PAGES = ["page one", "page two is longer", "three"]


def test_pages_are_joined_by_a_newline():
    doc = CleanText.from_pages(PAGES)
    assert doc.text == "page one\npage two is longer\nthree"


def test_page_count():
    assert CleanText.from_pages(PAGES).page_count == 3


def test_page_text_returns_exactly_that_page():
    doc = CleanText.from_pages(PAGES)
    assert doc.page_text(1) == "page one"
    assert doc.page_text(2) == "page two is longer"
    assert doc.page_text(3) == "three"


def test_page_at_maps_a_character_position_to_its_page():
    doc = CleanText.from_pages(PAGES)
    assert doc.page_at(0) == 1                            # "p" of "page one"
    assert doc.page_at(doc.text.index("two")) == 2
    assert doc.page_at(len(doc.text) - 1) == 3           # the final "e"


def test_the_newline_between_pages_belongs_to_the_earlier_page():
    doc = CleanText.from_pages(PAGES)
    assert doc.page_at(len("page one")) == 1


def test_page_numbers_outside_the_document_are_refused():
    doc = CleanText.from_pages(PAGES)
    with pytest.raises(ValueError):
        doc.page_text(0)
    with pytest.raises(ValueError):
        doc.page_text(4)


def test_character_positions_outside_the_document_are_refused():
    doc = CleanText.from_pages(PAGES)
    with pytest.raises(ValueError):
        doc.page_at(len(doc.text))
    with pytest.raises(ValueError):
        doc.page_at(-1)
