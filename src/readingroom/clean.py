"""Clean one PDF page: remove the page furniture, keep the law.

Three rules, each learned by looking at every page of the GDPR, AI Act and DSA:

1. Page headers and footers sit in fixed strips at the top and bottom of the page.
2. Lines that share a row are put back together, left to right.
3. Footnotes are the small-print rows below the last row of body text, and the block
   starts with a footnote number like "(1)". Small print alone is not enough: AI Act
   recital numbers and the GDPR's signatures are small print too.

The body text's font size is decided once per document, by body_size(), and passed in.
Deciding it per page fails: on a page where footnotes outweigh the body text, the
footnotes' font would win.
"""
import re
from collections import Counter
from dataclasses import dataclass

# An A4 page is 842 points tall. On all 334 pages checked, headers sit above 70 and
# footers below 805, and no body text does.
TOP_STRIP = 70
BOTTOM_STRIP = 805

# Lines less than this far apart vertically are on the same row. Rows of text are
# about 10.5 points apart; "(165)" and its sentence differ by 0.8.
ROW_TOLERANCE = 2.0

FOOTNOTE_NUMBER = re.compile(r"\(\d+\)")


@dataclass(frozen=True)
class Line:
    """One line of text as the PDF places it on the page."""

    y: float     # distance from the top of the page, in points
    x: float     # distance from the left edge, in points
    size: float  # font size, in points
    text: str


Row = list[Line]


def body_size(pages: list[list[Line]]) -> float:
    """The font size carrying the most characters in the whole document."""
    chars = Counter()
    for lines in pages:
        for line in _inside_strips(lines):
            chars[line.size] += len(line.text)
    return chars.most_common(1)[0][0]


def clean_page(lines: list[Line], body_size: float) -> str:
    """Return the page's text with headers, footers and footnotes removed."""
    rows = _drop_footnotes(_group_rows(_inside_strips(lines)), body_size)
    return "\n".join(" ".join(line.text.strip() for line in row) for row in rows)


def _inside_strips(lines: list[Line]) -> list[Line]:
    return [line for line in lines if TOP_STRIP <= line.y <= BOTTOM_STRIP]


def _group_rows(lines: list[Line]) -> list[Row]:
    """Group lines into rows, top to bottom, each row read left to right."""
    rows: list[Row] = []
    for line in sorted(lines, key=lambda line: line.y):
        if rows and line.y - rows[-1][0].y <= ROW_TOLERANCE:
            rows[-1].append(line)
        else:
            rows.append([line])
    return [sorted(row, key=lambda line: line.x) for row in rows]


def _drop_footnotes(rows: list[Row], body_size: float) -> list[Row]:
    """Remove the footnote block, if there is one, from the bottom of the page."""
    is_body = [any(abs(line.size - body_size) < 0.3 for line in row) for row in rows]
    if True not in is_body:
        return rows
    last_body = len(is_body) - 1 - is_body[::-1].index(True)
    tail = rows[last_body + 1:]
    if tail and FOOTNOTE_NUMBER.match(tail[0][0].text.strip()):
        return rows[:last_body + 1]
    return rows
