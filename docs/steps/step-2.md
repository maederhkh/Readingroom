# Step 2 — The first tool: keyword search, connected to Claude Code

*Approved 29 Sep 2026.*

## What this step does

Claude Code gets its first tool, `keyword_search`, which looks through the articles on
the shelf for the words it is given. Then you watch Claude Code decide to use it.

## Built in two halves, with a stop after each

**Half 1 — the search itself**, plus a terminal command to try it without any agent.
**Half 2 — connect it to Claude Code** through a small MCP helper program.

## How keyword search scores an article (BM25)

Three common-sense rules, each guarded by a test that fails if the rule is broken:

1. **Rare words count more.** "accuracy" is in few articles, "data" in nearly all.
2. **Repeating a word helps, but less each time.**
3. **A long article does not win just by being long.**

Words in `"double quotes"` are a phrase: the article must contain them in that order.
Phrases are matched on words, not characters, so a PDF line break between "up" and "to"
does not stop `"kept up to date"` matching.

Each result carries: law, article, title, pages, a short verbatim passage where the
words appear (line breaks shown as spaces), and a bookmark name like `gdpr/article-5`.

## What we learned while building half 1

- **Keyword search counts words; it does not know which article is "the" one.** Only two
  GDPR articles contain the word "accuracy": Article 18 twice, Article 5 once. So
  Article 18 ranks first, although Article 5 is the accuracy principle. The first test
  expected Article 5 first — that was a hope, not something keyword search promises.
  The test now checks what it does promise: exactly those two articles.
- **It does not know that words are related.** "accurate", "inaccurate" and "accuracy"
  are different words to it.
- **It does not know meaning.** "keeping records correct" finds Article 30 (*Records* of
  processing activities) — the shared word is "records" — and misses Article 5 entirely.
  This is the gap meaning search (step 4) is for.
- **A test can pass while testing nothing, again.** The first rare-word test let the
  winning article match both query words, so it passed with rarity switched off.
  Rewritten so each article matches exactly one word; every scoring rule was then
  broken on purpose to confirm a test fails.

## Try it yourself

```bash
python -m readingroom search accuracy --law gdpr
python -m readingroom search "\"kept up to date\""
python -m readingroom search "automated decision-making profiling"
python -m readingroom search "keeping records correct" --law gdpr
```

## Deliberately left out

| Left out | When |
|---|---|
| Meaning search | step 4 |
| Recitals and annexes as searchable pieces | a later small step |
| Splitting long articles into smaller pieces | only if long articles cause problems |
| Telling Claude Code to rely only on the documents | skills, step 5 |

**Status: half 1 complete (29 Sep 2026).** 86 tests, all passing.
