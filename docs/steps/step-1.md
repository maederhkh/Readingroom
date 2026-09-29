# Step 1 — Stock the pantry shelf

*Approved 25 Sep 2026. Build order B: thin thread first — see the table at the bottom.*

## What this step does

Reads the PDFs in `documents/` and turns each one into **clean text, cut into articles**,
where every article remembers its number, title, chapter and pages.

No search, no Claude Code, no cost. Those start in step 2.

## Built in two halves, with a stop after each

**Half 1 — clean text.** Take the text out page by page, remove page headers, footers
and footnotes, and remember which page every character came from.

**Half 2 — find the articles.** Spot `Article 5` lines, take the title from the next line,
note the chapter, stop once the annexes begin (so AI Act Annex VIII's `Article 49`
heading is not mistaken for an article).

## What we learned by looking before writing any code

- All three PDFs contain real text. No OCR.
- **Page headers and footers sit in fixed strips** at the top (y < 70) and bottom
  (y > 805) of every A4 page (842 points tall). One rule — "ignore those strips" —
  removes exactly the furniture on all 334 pages, in all three formats, and no body text.
- **Footnotes are in smaller print** than the body (8.5 vs 9.6 points) and sit below the
  last line of body text. But small print alone is not enough:
  - AI Act recital numbers like `(165)` are also 8.5 — they are kept because body text
    follows them.
  - The GDPR's signatures (`M. SCHULZ`) are also small print at the bottom — they are
    kept because a footnote block must **start with a footnote number** like `(7)`.
- Checked: every recital survives cleaning — GDPR 173, AI Act 180, DSA 156.
- *"Official Journal of the European Union"* legitimately appears inside articles
  ("shall enter into force on the twentieth day following ... publication in the Official
  Journal of the European Union"). So the test is that the **header lines** are gone,
  not that the phrase is.

## What we learned while building half 1

- **The body font size must be decided for the whole document, not per page.** On GDPR
  page 35 the footnote has more characters than the three lines of Article 5 above it,
  so a per-page count picked the footnote's font as "body" and kept the footnote. A test
  caught it.
- **A test can pass while checking nothing.** The first furniture test looked for header
  parts alone on a line. With cleaning switched off, the parts share a row and are
  joined into one line (`4.5.2016 Official Journal of the European Union L 119/35`), so
  the test still passed. Each real-document test was then checked by breaking the
  cleaning on purpose and confirming it fails.
- **`ELI: http://...` appears in the law itself.** AI Act Articles 102-110 cite the AI
  Act as "(OJ L, 2024/1689, 12.7.2024, ELI: http://...)". The footer differs by having
  a page counter (`41/144`) on the same row.
- **On Windows a plain text save writes `\r\n`**, which would shift every character
  position after the first line break. The shelf writes `\n` only, and a test checks it.

## What we learned while building half 2

- **Titles can run onto a second line, and the second line starts with a small letter**
  ("...the rights of the data" / "subject"). This simple text rule was checked against
  the PDFs' bold printing: they agree on all 306 headings. The same rule handles
  chapter and section titles (three DSA section titles wrap).
- **The AI Act's annexes come after the closing sentence** ("This Regulation shall be
  binding in its entirety"), which appears exactly once per law. Stopping there keeps
  out the fake `Article 49` - which turned out to be the second line of Annex VIII's
  title, "...in accordance with" / "Article 49".
- **`CHAPTER I` sits above `Article 1`**, so chapter headings are read from the top even
  though articles are only counted from `Article 1`. A test caught the first version
  missing it.
- **Official typos are kept as printed**: AI Act Article 1's title is ``Subject matter` ``
  (stray backtick) and Article 111's title ends "already placed on the marked".
- Every real-document test was checked by breaking each rule on purpose (closing
  sentence, title continuation, chapter headings) and confirming tests fail.

## How to check it yourself

```bash
python -m readingroom ingest
python -m readingroom inspect gdpr              # details + every article with its pages
python -m readingroom inspect gdpr --page 35
python -m readingroom inspect gdpr --article 5
```

## What counts as working

- GDPR Article 5 point (d) is followed directly by point (e) — no header or footnote
  wedged between them.
- No header or footer line survives on any page.
- Every recital survives: 173 / 180 / 156.
- The GDPR signatures survive.
- GDPR has 99 articles, AI Act 113, DSA 93 — exactly, numbered 1..N with none missing.
- Every article knows its title, chapter, section and pages; GDPR Article 5 is
  "Principles relating to processing of personal data", Chapter II, pages 35–36.

**Status: step 1 complete (29 Sep 2026).** 65 tests, all passing.

## Deliberately left out of step 1

| Left out | When |
|---|---|
| Recitals and annexes as separate pieces | a later small step |
| Splitting very long articles | step 2 |
| Any search | step 2 |

## The build order (option B, "thin thread first")

1. Clean text and articles — **this step**
2. One keyword-search tool, connected to Claude Code straight away
3. Reading tools — open an article, read the text around a hit
4. Meaning search, then combined search
5. Skills
