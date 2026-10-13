# Step 4 — Reading tools

## 4a — `read_article` (29 Sep 2026)

**What it does.** Given a bookmark from a search result (`gdpr/article-22`), it returns
the whole article word for word, with its title, chapter, section and pages.

**Why.** Search returns ~350-character excerpts. In both step-3 runs the model found
Article 22 but could only see its first sentence, so it spent its searches trying to
rebuild the article from fragments and could not give the exceptions in paragraph 2.
Search says *where* to look; `read_article` lets it *read*.

Every article fits in one reply: the median is ~1,700 characters, the longest (AI Act
Article 3, the definitions) 17,101 — about 4,000 tokens. No paging needed.

**What changed**

- `mcp_server.py` offers a second tool, `read_article`, to both chefs. Bad bookmarks are
  refused with a message the model can act on ("No gdpr/article-200. gdpr has Articles
  1–99."; "Bookmarks look like gdpr/article-22").
- `keyword_search`'s description now ends: the passage is an excerpt — to read the
  article in full, pass its bookmark to `read_article`. This is how the agent learns
  the two tools belong together.
- The loop counts **tool calls** (searches and reads together), not just searches: both
  cost money. Default limit 12; `--max-tool-calls` to change it.
- `ask` shows 🔎 for searches and 📖 for reads.

**Same question, before and after**

*"What does the GDPR say about automated decision-making?"*, `openai/gpt-5-mini`:

| | Before (search only) | After (search + read) |
|---|---|---|
| Tool calls | 10 searches (hit the limit) | 1 search, 4 reads |
| Rounds | 12 | 3 |
| Tokens | 45,412 | 11,082 |
| Cost | $0.0072 | $0.0048 |
| Article 22's exceptions | missing — "I cannot supply them" | all of 22(2), 22(3) and 22(4), quoted |

All 7 quotations in the new answer were checked against the clean GDPR text: every one
appears word for word.

Reading more is cheaper than searching blindly: one search plus reading whole articles
used a quarter of the tokens of ten searches for fragments.

*(4b below replaced the planned "read around a hit" tool.)*

**Status:** 131 tests, all passing.

## 4b — the invisible half gets bookmarks (13 Oct 2026)

**The problem.** Search only knew articles, which are about half of each law. The rest
was on the shelf but no bookmark pointed to it, so the agent could never find or read it:

| Law | Articles | Recitals | Annexes |
|---|---|---|---|
| GDPR | 55% | 45% (173) | — |
| AI Act | 52% | 40% (180) | 8% (13) |
| DSA | 52% | 47% (156) | — |

Example: GDPR Recital 71 contains "obtain an explanation of the decision reached" — a
phrase that appears nowhere in Article 22. Searching for it returned "No articles
contain these words". The AI Act's high-risk list is Annex III; Article 6 only refers to it.

**Why not a "read around a passage" tool.** It cannot reach text that search never
lands on, and for articles it is no longer needed — read_article returns the whole one.

**Built in half 1:** recitals and annexes are found and saved as bookmarks
(`recitals.json`, `annexes.json`), and `inspect` shows them:

```bash
python -m readingroom inspect gdpr --recital 71
python -m readingroom inspect eu-ai-act --annex III
```

Coverage by bookmarks: about 52% → over 99% of each law. The remaining ~0.6% is the
title, "Having regard to…" lines, chapter headings and signatures.

**Rules learned from the real text**

- Recitals sit between `Whereas:` and `HAVE ADOPTED THIS REGULATION:` (once per law),
  each starting with `(n)`. A new recital starts only on the *next* number, so a line
  that merely starts with a citation number cannot start a fake one.
- Annexes come after the closing sentence; `ANNEX III` alone on a line, title below.
- **Title rule extended.** Annex VIII and XII titles continue onto a line starting with a
  capital ("…in accordance with" / "Article 49"), which the small-letter rule missed. A
  title now also continues after a line ending on a word no title ends with (with, of,
  their…). Checked: it changes none of the 305 article, chapter and section titles.
  The bold-printing check was not usable here — Annex X's title is italic, not bold.
- The "annexes only after the closing sentence" rule is never needed in these three
  laws, so breaking it changed no real-document test. A dedicated test now guards it.

**Status of half 1:** 163 tests, all passing.

### Half 2 — the agent can find and read them

- **One list of parts.** `shelf.units_by_bookmark()` holds every article, recital and annex;
  search and reading both use it, so they cannot disagree about what exists.
- **Bookmarks** are `law/kind-number`: `gdpr/article-22` (unchanged), `gdpr/recital-71`,
  `eu-ai-act/annex-III`. Upper or lower case does not matter.
- **Search** covers all three kinds; each result says its kind and label ("Recital 71").
  The new `kind` input searches one kind only.
- **`read_article` became `read`**, for any bookmark. Refusals say what exists:
  "gdpr has Recitals 1–173", "gdpr has no annexes", "eu-ai-act has Annexes I, …, XIII".
- **`list_documents`** — new: each law's short name, official title, pages, and how many
  articles, recitals and annexes it has.
- The tool descriptions explain the three kinds: articles are the binding rules, recitals
  explain and help interpret them, annexes hold lists and details articles refer to.

### What we learned building half 2

- **Recitals crowded out the articles.** In one mixed list, word counting rewarded the
  recitals' plain sentences, which repeat key words: "prohibited AI practices" returned
  five recitals and no article; for "very large online platforms systemic risk", Article 34
  disappeared. Fixed by **grouping**: up to 5 best articles first, then up to 3 recitals,
  then up to 2 annexes, each ranked only against its own kind. Chosen by Peyman over
  "articles only unless asked" (which would leave Recital 71 hidden) and the mixed list.
- **Keyword search does not find AI Act Article 5 for "prohibited AI practices"**, its own
  title: it is a long article that says "prohibited" once, and the length rule holds it
  back. A limit of word counting — meaning search (step 5) is the cure.
- **The model typed `annex-iii`**, was refused, and spent a search finding `annex-III`.
  Bookmarks are now case-insensitive.
- **A Python trap, caught by the tests:** on a compiled pattern, `fullmatch(text, 2)` does
  not mean "ignore case" — the 2 is a start position. It silently read `gdpr` as `pr`.

### Real runs (13 Oct 2026, `openai/gpt-5-mini`)

| Question | What it did | Cost |
|---|---|---|
| Does the GDPR give a right to an explanation of automated decisions? | 1 search, read Articles 22 and 15 and **Recital 71**; quoted the recital and labelled it "recital language", separate from the binding articles | $0.0062 |
| Which AI systems count as high-risk under the AI Act? | 3 searches, read **Article 6** and **Annex III**; listed the eight Annex III areas and Article 6(3)'s exception, every point cited | $0.0079 |

**Claude Code:** the tool is now called `read`, not `read_article`, and there is a new
`list_documents`. Start a new Claude Code session to see them.

**Status: step 4 complete (13 Oct 2026).** 181 tests, all passing.
