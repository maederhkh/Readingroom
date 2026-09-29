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

**Still to come in step 4:** read the text around a hit (for recitals and anything outside
article boundaries), and list the documents.

**Status:** 131 tests, all passing.
