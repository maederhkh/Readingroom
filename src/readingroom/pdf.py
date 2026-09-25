"""Read a PDF into clean text. The only module that talks to PyMuPDF."""
import pathlib

import pymupdf

from readingroom.clean import Line, body_size, clean_page
from readingroom.text import CleanText


def read_clean_text(path: pathlib.Path) -> CleanText:
    """Read every page, clean it, and join the pages into one text."""
    pages = read_lines(path)
    size = body_size(pages)
    return CleanText.from_pages([clean_page(lines, size) for lines in pages])


def read_lines(path: pathlib.Path) -> list[list[Line]]:
    """Every non-empty line of every page, with its position and font size."""
    with pymupdf.open(path) as doc:
        return [_page_lines(page) for page in doc]


def _page_lines(page: pymupdf.Page) -> list[Line]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):  # image blocks have no lines
            text = "".join(span["text"] for span in line["spans"])
            if text.strip():
                x, y = line["bbox"][0], line["bbox"][1]
                size = max(span["size"] for span in line["spans"])
                lines.append(Line(y=y, x=x, size=size, text=text))
    return lines
