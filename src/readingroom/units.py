"""Find the recitals and annexes - the half of each law outside the articles.

Until this step, search could only find articles, so the recitals (40-47% of each
law) and the AI Act's annexes (8%) were on the shelf but invisible to the agent.

Recitals, learned from the GDPR (173), AI Act (180) and DSA (156):
- they sit between "Whereas:" and "HAVE ADOPTED THIS REGULATION:", once per law
- each starts with "(n)" at the start of a line, numbered 1, 2, 3... with no gaps
- a new recital starts only on the NEXT number in sequence, so a line that merely
  begins with a citation or footnote number like "(4)" cannot start a fake one

Annexes, learned from the AI Act (13; the GDPR and DSA have none):
- they come after the closing sentence, "This Regulation shall be binding in its entirety"
- "ANNEX III" alone on a line, its title on the next line (same title rule as articles)
- an annex runs to the next annex, or to the end of the text
"""
import re
from dataclasses import dataclass

from readingroom.articles import CLOSING, lines_with_positions, read_title

RECITALS_BEGIN = "Whereas:"
RECITALS_END = "HAVE ADOPTED THIS REGULATION:"
ANNEX = re.compile(r"ANNEX ([IVXLC]+)\s*")


@dataclass(frozen=True)
class Recital:
    number: int
    start: int  # position of its "(n)" in the clean text
    end: int    # position just after its last character


@dataclass(frozen=True)
class Annex:
    number: str  # Roman, as printed: "III"
    title: str
    start: int   # position of its "ANNEX III" heading
    end: int


def find_recitals(text: str) -> list[Recital]:
    lines = lines_with_positions(text)
    begin = next((i for i, (_, line) in enumerate(lines) if line.strip() == RECITALS_BEGIN), None)
    if begin is None:
        return []
    end = next((i for i, (_, line) in enumerate(lines) if line.startswith(RECITALS_END)), len(lines))
    region_end = lines[end][0] - 1 if end < len(lines) else len(text)

    starts = []  # (number, position)
    for position, line in lines[begin + 1:end]:
        found = re.match(r"\((\d+)\)", line)
        if found and int(found.group(1)) == len(starts) + 1:
            starts.append((len(starts) + 1, position))
    ends = [position - 1 for _, position in starts[1:]] + [region_end]
    return [Recital(number, start, stop) for (number, start), stop in zip(starts, ends)]


def find_annexes(text: str) -> list[Annex]:
    lines = lines_with_positions(text)
    closing = next((i for i, (_, line) in enumerate(lines) if line.startswith(CLOSING)), None)
    if closing is None:
        return []
    heads = [i for i in range(closing + 1, len(lines)) if ANNEX.fullmatch(lines[i][1])]
    annexes = []
    for k, i in enumerate(heads):
        end = lines[heads[k + 1]][0] - 1 if k + 1 < len(heads) else len(text)
        title, _ = read_title(lines, i + 1, heads[k + 1] if k + 1 < len(heads) else len(lines))
        annexes.append(Annex(ANNEX.fullmatch(lines[i][1]).group(1), title, lines[i][0], end))
    return annexes


def official_title(text: str) -> str | None:
    """The law's title: from the "REGULATION (EU) ..." line up to "(Text with EEA relevance)",
    joined into one line. None for a document that does not have one."""
    lines = text.split("\n")[:40]
    first = next((i for i, line in enumerate(lines) if line.startswith(("REGULATION (EU)", "DIRECTIVE (EU)"))), None)
    if first is None:
        return None
    last = next((i for i in range(first, len(lines)) if lines[i].startswith("(Text with EEA relevance)")), None)
    if last is None:
        return None
    return " ".join(line.strip() for line in lines[first:last])
