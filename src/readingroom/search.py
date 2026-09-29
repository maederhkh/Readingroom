"""Keyword search over the articles on the shelf.

Each article is scored with BM25, the standard keyword-search formula. It encodes
three common-sense rules:

1. Rare words count more. "accuracy" is in few articles, "data" in nearly all, so
   matching "accuracy" says much more about what an article is about.
2. Repeating a word helps, but less each time. Twenty mentions are not worth twenty
   times one.
3. A long article does not win just by being long. Long articles mention everything
   somewhere; the score is adjusted for length.

Words in "double quotes" form a phrase: an article must contain those words in that
order. Phrases are matched on words, not raw characters, so "kept up to date" still
matches when the PDF's line break falls between "up" and "to".
"""
import math
import pathlib
import re
from collections import Counter
from dataclasses import dataclass

from readingroom import shelf

# The usual BM25 settings. K1: how quickly repeated mentions stop helping.
# B: how strongly long articles are held back (0 = not at all, 1 = fully).
K1 = 1.5
B = 0.75

WORD = re.compile(r"[a-z0-9]+")
SNIPPET_BEFORE, SNIPPET_AFTER = 150, 200  # characters shown around the matching words


def tokenize(text: str) -> list[str]:
    """Lowercase words: "Article 5(1)(d)" -> ["article", "5", "1", "d"]."""
    return WORD.findall(text.lower())


@dataclass(frozen=True)
class Passage:
    """One searchable piece of a law. For now, one whole article."""

    doc_id: str
    article: int
    title: str
    page_start: int
    page_end: int
    text: str

    @property
    def bookmark(self) -> str:
        return f"{self.doc_id}/article-{self.article}"


def load_passages(shelf_dir: pathlib.Path) -> list[Passage]:
    """Every article of every law on the shelf, ready to be searched."""
    passages = []
    for doc_id in shelf.list_documents(shelf_dir):
        text = shelf.load(shelf_dir, doc_id).text
        for a in shelf.load_articles(shelf_dir, doc_id):
            passages.append(Passage(doc_id=doc_id, article=a["number"], title=a["title"],
                                    page_start=a["page_start"], page_end=a["page_end"],
                                    text=text[a["start"]:a["end"]]))
    return passages


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float
    snippet: str  # the words in context, verbatim except that line breaks become spaces


class KeywordIndex:
    def __init__(self, passages: list[Passage]):
        self.passages = passages
        # For every passage: its words, and where each word sits in the text.
        self._words = [[(m.group(), m.start()) for m in WORD.finditer(p.text.lower())] for p in passages]
        self._counts = [Counter(word for word, _ in words) for words in self._words]
        self._average_length = sum(len(w) for w in self._words) / len(passages) if passages else 0
        # In how many passages each word appears at least once.
        self._passages_with = Counter(word for counts in self._counts for word in counts)

    def search(self, query: str, limit: int = 5, laws: list[str] | None = None) -> list[Hit]:
        words = list(dict.fromkeys(tokenize(query)))  # each query word once, in order
        phrases = [tokenize(p) for p in re.findall(r'"([^"]*)"', query) if tokenize(p)]
        if not words:
            return []
        hits = []
        for i, passage in enumerate(self.passages):
            if laws and passage.doc_id not in laws:
                continue
            if not all(self._phrase_at(i, phrase) is not None for phrase in phrases):
                continue
            score = sum(self._word_score(i, word) for word in words)
            if score > 0:
                hits.append(Hit(passage, score, self._snippet(i, words, phrases)))
        hits.sort(key=lambda h: (-h.score, h.passage.doc_id, h.passage.article))
        return hits[:limit]

    def _rarity(self, word: str) -> float:
        """High for words in few passages, near zero for words in almost all."""
        n, having = len(self.passages), self._passages_with[word]
        return math.log(1 + (n - having + 0.5) / (having + 0.5))

    def _word_score(self, i: int, word: str) -> float:
        mentions = self._counts[i][word]
        if not mentions:
            return 0.0
        length_factor = 1 - B + B * len(self._words[i]) / self._average_length
        return self._rarity(word) * mentions * (K1 + 1) / (mentions + K1 * length_factor)

    def _phrase_at(self, i: int, phrase: list[str]) -> int | None:
        """Where in the text the phrase begins, or None if it is not there."""
        words = self._words[i]
        for start in range(len(words) - len(phrase) + 1):
            if all(words[start + k][0] == phrase[k] for k in range(len(phrase))):
                return words[start][1]
        return None

    def _snippet(self, i: int, words: list[str], phrases: list[list[str]]) -> str:
        """A short passage around the first phrase, or else around the rarest matching word."""
        if phrases:
            centre = self._phrase_at(i, phrases[0])
        else:
            rarest = max((w for w in words if self._counts[i][w]), key=self._rarity)
            centre = next(pos for word, pos in self._words[i] if word == rarest)
        text = self.passages[i].text
        start, end = max(0, centre - SNIPPET_BEFORE), min(len(text), centre + SNIPPET_AFTER)
        if start > 0:  # begin and end on whole words
            start = next((k + 1 for k in range(start, centre) if text[k].isspace()), start)
        if end < len(text):
            end = next((k for k in range(end, centre, -1) if text[k].isspace()), end)
        snippet = text[start:end].replace("\n", " ")
        return ("…" if start > 0 else "") + snippet + ("…" if end < len(text) else "")
