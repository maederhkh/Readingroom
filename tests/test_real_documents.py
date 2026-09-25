"""The cleaning, checked against the three real laws in documents/.

These read the actual PDFs (a few seconds each). documents/ is not in git, so they
skip themselves when a PDF is missing.
"""
import pathlib
import re

import pytest

from readingroom.pdf import read_clean_text

DOCUMENTS = pathlib.Path(__file__).parent.parent / "documents"

# file name, pages, recitals
LAWS = {
    "gdpr": ("GDPR.pdf", 88, 173),
    "ai_act": ("EU AI act.pdf", 144, 180),
    "dsa": ("Digital Services act.pdf", 102, 156),
}

# Page furniture in the three header/footer formats. Matched ANYWHERE in a line, because
# the parts of a header share a row and would be joined into one line if they survived:
# "4.5.2016 Official Journal of the European Union L 119/35". Matching only whole lines
# was tried first and missed exactly that - it passed with the cleaning switched off.
FURNITURE = [
    r"\bL \d+/\d+",                                # L 119/35, L 277/41 - GDPR, DSA
    # AI Act footer, "ELI: http://data.europa.eu/eli/reg/2024/1689/oj 41/144". The page
    # counter is what makes it furniture: Articles 102-110 cite "(OJ L, 2024/1689,
    # 12.7.2024, ELI: http://...)" in the body of the law.
    r"^ELI: http\S+\s+\d+/\d+\s*$",
    r"^OJ L, \d{1,2}\.\d{1,2}\.\d{4}\s*$",         # OJ L, 12.7.2024 - AI Act
    r"^EN\s*$",                                    # the language tag, all three
]
FURNITURE_LINE = re.compile("|".join(FURNITURE), re.MULTILINE)


@pytest.fixture(scope="module", params=LAWS)
def law(request):
    name, pages, recitals = LAWS[request.param]
    path = DOCUMENTS / name
    if not path.exists():
        pytest.skip(f"{name} is not in documents/")
    return read_clean_text(path), pages, recitals


def test_every_page_is_kept(law):
    doc, pages, _ = law
    assert doc.page_count == pages


def test_no_header_or_footer_line_survives(law):
    doc, _, _ = law
    assert FURNITURE_LINE.findall(doc.text) == []


def test_every_recital_survives(law):
    doc, _, recitals = law
    before_article_1 = doc.text[: re.search(r"^Article 1\s*$", doc.text, re.MULTILINE).start()]
    found = {int(n) for n in re.findall(r"^\((\d+)\)", before_article_1, re.MULTILINE)}
    assert set(range(1, recitals + 1)) <= found


def test_gdpr_article_5_point_d_runs_straight_into_point_e():
    # The example that started it: page 35's header and footnote used to sit here.
    path = DOCUMENTS / "GDPR.pdf"
    if not path.exists():
        pytest.skip("GDPR.pdf is not in documents/")
    text = read_clean_text(path).text
    d_ends = text.index("without delay\n(‘accuracy’);") + len("without delay\n(‘accuracy’);")
    assert text[d_ends:].startswith("\n(e)  kept in a form which permits identification")


def test_gdpr_signatures_survive():
    path = DOCUMENTS / "GDPR.pdf"
    if not path.exists():
        pytest.skip("GDPR.pdf is not in documents/")
    doc = read_clean_text(path)
    assert "M. SCHULZ" in doc.page_text(88)
    assert "J.A. HENNIS-PLASSCHAERT" in doc.page_text(88)
