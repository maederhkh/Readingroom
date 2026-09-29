"""Find the articles in a law's clean text.

Rules, each learned by reading the clean GDPR, AI Act and DSA:

1. An article heading is a line holding only "Article N". Its title is the next line.
2. A title continues onto following lines that start with a small letter
   ("...the rights of the data" / "subject"). Checked against the PDFs' bold printing:
   the two agree on every one of the 306 headings. Chapter and section titles follow the
   same rule.
3. "CHAPTER II" and "SECTION 1" / "Section 1" headings work the same way. An article
   belongs to the chapter and section above it; a new chapter clears the section.
4. Articles start at "Article 1" (everything before is the preamble and recitals) -
   but chapter and section headings are read from the top, because "CHAPTER I" sits
   just above "Article 1". Articles end at the closing sentence "This Regulation shall be binding in its entirety". The
   AI Act's annexes come after it, and Annex VIII's title wraps so that "Article 49"
   lands alone on a line - stopping at the closing sentence keeps it out.

An article runs from its heading to the next heading (article, chapter or section) or
to the closing sentence. It is a bookmark: a start and end position in the clean text.
"""
import re
from dataclasses import dataclass

ARTICLE = re.compile(r"Article (\d+)\s*")
CHAPTER = re.compile(r"CHAPTER [IVXLC]+\s*")
SECTION = re.compile(r"(?:SECTION|Section) \d+\s*")
CLOSING = "This Regulation shall be binding in its entirety"


@dataclass(frozen=True)
class Article:
    number: int
    title: str
    chapter: str | None  # e.g. "CHAPTER II — Principles"
    section: str | None  # e.g. "Section 1 — Transparency and modalities"
    start: int           # position of the "Article N" heading in the clean text
    end: int             # position just after the article's last character


def find_articles(text: str) -> list[Article]:
    lines = _lines_with_positions(text)
    first = next((i for i, (_, line) in enumerate(lines) if line.strip() == "Article 1"), None)
    if first is None:
        return []
    closing = next((i for i, (_, line) in enumerate(lines) if line.startswith(CLOSING)), len(lines))
    region_end = lines[closing][0] - 1 if closing < len(lines) else len(text)

    articles: list[Article] = []
    chapter = section = None
    open_article = None  # (number, title, chapter, section, start) until its end is known

    def close(end: int) -> None:
        if open_article:
            articles.append(Article(*open_article, end=end))

    i = 0
    while i < closing:
        position, line = lines[i]
        is_article = ARTICLE.fullmatch(line) and i >= first
        if CHAPTER.fullmatch(line) or SECTION.fullmatch(line) or is_article:
            close(position - 1)  # - 1: the newline before a heading is not the article's
            open_article = None
            title, i = _title(lines, i + 1, closing)
            label = f"{line.strip()} — {title}"
            if CHAPTER.fullmatch(line):
                chapter, section = label, None
            elif SECTION.fullmatch(line):
                section = label
            else:
                number = int(ARTICLE.fullmatch(line).group(1))
                open_article = (number, title, chapter, section, position)
        else:
            i += 1
    close(region_end)
    return articles


def _title(lines: list[tuple[int, str]], i: int, stop: int) -> tuple[str, int]:
    """The title starting at line i, and the index of the line after it."""
    parts = [lines[i][1].strip()]
    i += 1
    while i < stop and re.match(r"[a-z]", lines[i][1]):
        parts.append(lines[i][1].strip())
        i += 1
    return " ".join(parts), i


def _lines_with_positions(text: str) -> list[tuple[int, str]]:
    """Every line of the text, with the position where it begins."""
    result, position = [], 0
    for line in text.split("\n"):
        result.append((position, line))
        position += len(line) + 1
    return result
