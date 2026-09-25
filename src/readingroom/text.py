"""One document's clean text, stored once, and which page every character came from.

This is the "one clean copy of the book". Everything found in it later is a bookmark:
a start and end position in this text. The page of any position is looked up here.
"""
from bisect import bisect_right
from dataclasses import dataclass


@dataclass(frozen=True)
class CleanText:
    text: str
    page_starts: tuple[int, ...]  # page_starts[i] is where page i + 1 begins in text

    @classmethod
    def from_pages(cls, pages: list[str]) -> "CleanText":
        """Join the pages with a newline, remembering where each one begins."""
        starts, position = [], 0
        for page in pages:
            starts.append(position)
            position += len(page) + 1  # + 1 for the joining newline
        return cls(text="\n".join(pages), page_starts=tuple(starts))

    @property
    def page_count(self) -> int:
        return len(self.page_starts)

    def page_text(self, page: int) -> str:
        """The text of one page, counting pages from 1 as the PDF does."""
        if not 1 <= page <= self.page_count:
            raise ValueError(f"page {page} is outside 1..{self.page_count}")
        start = self.page_starts[page - 1]
        end = self.page_starts[page] - 1 if page < self.page_count else len(self.text)
        return self.text[start:end]

    def page_at(self, position: int) -> int:
        """The page, counting from 1, that the character at this position is on."""
        if not 0 <= position < len(self.text):
            raise ValueError(f"position {position} is outside 0..{len(self.text) - 1}")
        return bisect_right(self.page_starts, position)
