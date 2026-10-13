"""Recitals and annexes in the three real laws in documents/. Skips when a PDF is missing."""
import pathlib
import re
from functools import cache

import pytest

from readingroom.articles import find_articles
from readingroom.pdf import read_clean_text
from readingroom.units import find_annexes, find_recitals

DOCUMENTS = pathlib.Path(__file__).parent.parent / "documents"
RECITAL_COUNT = {"GDPR.pdf": 173, "EU AI act.pdf": 180, "Digital Services act.pdf": 156}


@cache
def load(name):
    if not (DOCUMENTS / name).exists():
        pytest.skip(f"{name} is not in documents/")
    return read_clean_text(DOCUMENTS / name).text


@pytest.mark.parametrize("name", RECITAL_COUNT)
def test_exactly_the_right_recitals_are_found(name):
    assert [r.number for r in find_recitals(load(name))] == list(range(1, RECITAL_COUNT[name] + 1))


@pytest.mark.parametrize("name", RECITAL_COUNT)
def test_every_recital_starts_with_its_own_number_and_stays_in_the_preamble(name):
    text = load(name)
    first_article = find_articles(text)[0].start
    for r in find_recitals(text):
        assert text[r.start:r.end].startswith(f"({r.number}) ")
        assert r.end < first_article
        assert "HAVE ADOPTED THIS REGULATION" not in text[r.start:r.end]


def test_gdpr_recital_71_holds_the_right_to_an_explanation():
    # The phrase that search could not find before this step.
    text = load("GDPR.pdf")
    r71 = find_recitals(text)[70]
    assert "obtain an explanation of the decision reached" in re.sub(r"\s+", " ", text[r71.start:r71.end])


@pytest.mark.parametrize("name", ["GDPR.pdf", "Digital Services act.pdf"])
def test_laws_without_annexes_have_none(name):
    assert find_annexes(load(name)) == []


def test_the_ai_act_has_its_13_annexes_in_order():
    numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]
    assert [a.number for a in find_annexes(load("EU AI act.pdf"))] == numerals


def test_ai_act_annex_iii_is_the_high_risk_list():
    text = load("EU AI act.pdf")
    annex = find_annexes(text)[2]
    assert annex.title == "High-risk AI systems referred to in Article 6(2)"
    assert "High-risk AI systems pursuant to Article 6(2) are the AI systems listed" in text[annex.start:annex.end]


def test_ai_act_annex_titles_that_wrap_are_complete():
    annexes = {a.number: a.title for a in find_annexes(load("EU AI act.pdf"))}
    assert annexes["VIII"].endswith("in accordance with Article 49")
    assert annexes["XII"].endswith("integrate the model into their AI system")
    assert annexes["X"] == "Union legislative acts on large-scale IT systems in the area of Freedom, Security and Justice"


def test_articles_recitals_and_annexes_never_overlap():
    text = load("EU AI act.pdf")
    spans = sorted([(u.start, u.end) for u in find_recitals(text) + find_articles(text) + find_annexes(text)])
    for (_, end), (start, _) in zip(spans, spans[1:]):
        assert end < start
