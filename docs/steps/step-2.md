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

## Half 2 — connecting it to Claude Code

`src/readingroom/mcp_server.py` is a small helper program. Claude Code starts it
itself, because `.mcp.json` in the project folder says so, and talks to it through its
standard input and output. It loads the shelf and builds the search index once, then
answers `keyword_search` calls.

What Claude Code sees:

- the tool's **name**, `keyword_search`
- its **description** — what it searches, how it ranks, what it cannot do (words not
  meaning; articles only), how to write a phrase, and what a result contains
- an **explanation of each input** — `query`, `law` (lists the laws on the shelf), `limit`

What it gets back: structured results (bookmark, law, article, title, pages, verbatim
passage, score), or an empty list with a note suggesting what to try instead.

## What we learned while building half 2

- **The MCP library changed under us.** Version 2 renamed `FastMCP` to `MCPServer`
  and renamed fields (`isError` → `is_error`). Checking the installed library instead
  of writing from memory caught it before any code was written against the old names.
- **An ordinary error's message is hidden from the agent.** A refusal like "No law
  called 'ai-act' — laws available: …" reached Claude Code only as "Error executing
  tool keyword_search": it would know it failed, but not how to fix the call. The
  library's `ToolError` is the way to say "expected failure, pass my message on".
- **Test what the agent sees, over the real connection.** Called directly in Python,
  the same refusal is thrown as an exception; over the connection it arrives as an
  error result the agent can read. The tests start the helper program as its own
  process and talk to it exactly as Claude Code does.
- **A project cannot start programs on your computer without your approval.** Claude
  Code lists the server as "pending approval" until you allow it once.

## Try it in Claude Code

1. Start a **new** Claude Code session in the `readingroom` folder.
2. Approve the `readingroom` MCP server when asked.
3. Ask, for example: *"Using the readingroom keyword_search tool, what does the GDPR
   say about automated decision-making?"*

Watch which searches it runs, whether it searches again, and what it cites.

**Status: step 2 complete (29 Sep 2026).** 97 tests, all passing.
