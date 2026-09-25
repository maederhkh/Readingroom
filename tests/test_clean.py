"""The page-cleaning rules.

Every Line below is copied verbatim from the real PDFs (position, font size, text),
captured with PyMuPDF on 25 Sep 2026. y is the distance from the top of an A4 page,
which is 842 points tall.
"""
from readingroom.clean import Line, body_size, clean_page as _clean_page

# The body font size of all three laws, as body_size() finds it for the whole document.
BODY = 9.6


def clean_page(lines):
    return _clean_page(lines, body_size=BODY)


# --- GDPR page 35: the end of Article 5(1)(d), then the header strip and a footnote.
GDPR_P35 = [
    Line(y=50.3, x=41.6, size=9.6, text="4.5.2016 "),
    Line(y=50.3, x=517.5, size=9.6, text="L 119/35 "),
    Line(y=50.3, x=223.4, size=9.6, text="Official Journal of the European Union "),
    Line(y=51.4, x=119.8, size=8.5, text="EN     "),
    Line(y=732.9, x=67.4, size=9.6, text="(d)  accurate and, where necessary, kept up to date; every reasonable step must be taken to ensure that personal data that "),
    Line(y=743.4, x=82.1, size=9.6, text="are inaccurate, having regard to the purposes for which they are processed, are erased or rectified without delay "),
    Line(y=754.0, x=82.1, size=9.6, text="(‘accuracy’); "),
    Line(y=777.4, x=67.4, size=8.5, text="(1) Directive (EU) 2015/1535 of the European Parliament and of the Council of 9 September 2015 laying down a procedure for the "),
    Line(y=786.8, x=78.6, size=8.5, text="provision of information in the field of technical regulations and of rules on Information Society services (OJ L 241, 17.9.2015, p. 1). "),
]

# --- AI Act page 41: a recital number in small print, on the same row as its text,
# plus the 2024-format header and footer.
AI_ACT_P41 = [
    Line(y=44.3, x=535.1, size=15.9, text="EN"),
    Line(y=50.7, x=41.8, size=9.6, text="OJ L, 12.7.2024"),
    Line(y=716.6, x=67.4, size=8.5, text="(165)"),
    Line(y=715.8, x=93.7, size=9.6, text="The development of AI systems other than high-risk AI systems in accordance with the requirements of this "),
    Line(y=726.3, x=93.7, size=9.6, text="Regulation may lead to a larger uptake of ethical and trustworthy AI in the Union. Providers of AI systems that are "),
    Line(y=813.1, x=41.8, size=9.6, text="ELI: http://data.europa.eu/eli/reg/2024/1689/oj"),
    Line(y=813.1, x=525.2, size=9.6, text="41/144"),
]

# --- DSA page 41: a point letter and its text on the same row.
DSA_P41 = [
    Line(y=754.9, x=83.7, size=9.6, text="Union law on consumer protection and product safety, including Regulations (EU) 2017/2394 and (EU) 2019/1020 "),
    Line(y=754.9, x=68.0, size=9.6, text="(f)"),
    Line(y=765.6, x=83.7, size=9.6, text="and Directives 2001/95/EC and 2013/11/EU;"),
]

# --- GDPR page 88: the signatures, in small print at the bottom of the text.
GDPR_P88 = [
    Line(y=143.9, x=158.4, size=9.6, text="For the European Parliament "),
    Line(y=143.9, x=360.6, size=9.6, text="For the Council "),
    Line(y=158.7, x=185.0, size=9.6, text="The President "),
    Line(y=158.7, x=364.1, size=9.6, text="The President "),
    Line(y=173.5, x=187.7, size=8.5, text="M. SCHULZ  "),
    Line(y=173.5, x=338.9, size=8.5, text="J.A. HENNIS-PLASSCHAERT   "),
]


def test_header_strip_is_removed():
    text = clean_page(GDPR_P35)
    assert "L 119/35" not in text
    assert "4.5.2016" not in text
    assert "Official Journal" not in text


def test_footer_strip_is_removed():
    text = clean_page(AI_ACT_P41)
    assert "ELI:" not in text
    assert "41/144" not in text
    assert "OJ L, 12.7.2024" not in text


def test_footnote_below_the_body_text_is_removed():
    text = clean_page(GDPR_P35)
    assert "2015/1535" not in text
    assert text.endswith("(‘accuracy’);")


def test_body_text_survives_cleaning():
    text = clean_page(GDPR_P35)
    assert text.startswith("(d)  accurate and, where necessary, kept up to date;")


def test_small_print_recital_number_is_kept_with_its_text():
    # Small print alone does not make a footnote: (165) is followed by body text.
    text = clean_page(AI_ACT_P41)
    assert text.startswith("(165) The development of AI systems")


def test_lines_on_one_row_are_joined_left_to_right():
    text = clean_page(DSA_P41)
    assert text.splitlines()[0].startswith("(f) Union law on consumer protection")


def test_small_print_signatures_are_not_mistaken_for_footnotes():
    # A footnote block must start with a footnote number like "(1)".
    text = clean_page(GDPR_P88)
    assert "M. SCHULZ" in text
    assert "J.A. HENNIS-PLASSCHAERT" in text


def test_page_with_no_text_cleans_to_empty_string():
    assert clean_page([]) == ""


def test_body_size_is_decided_by_the_whole_document_not_one_page():
    # On GDPR page 35 alone the footnote has more characters than the body text,
    # so a per-page count would pick the footnote's 8.5 as the body size.
    # Across the document the body text wins.
    assert body_size([GDPR_P35, AI_ACT_P41, DSA_P41]) == 9.6
