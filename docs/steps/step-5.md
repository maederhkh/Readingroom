# Step 5 — Meaning search and combined search

*Design agreed in conversation, 14 Oct 2026. Nothing below is built yet.*

## Why

Keyword search matches words, not meaning. It has missed, in real runs and checks:

| Question / search | What it should find | What happened |
|---|---|---|
| "keeping records correct" | GDPR Article 5 (accuracy) | found Article 30 "*Records* of processing" |
| "prohibited AI practices" | AI Act Article 5, whose title this is | not in the results — long article, word said once |
| "accurate" | text saying "accuracy" | different words to keyword search |

This step adds the second half of the original idea's "smart retrieval": **semantic search**
(meaning) and **hybrid search** (keyword and meaning combined), as tools the agent chooses
between.

## How meaning search works

Every part of the laws is placed as a **dot on a "meaning map"**: dots close together mean
similar things, even with no words in common. A question is placed on the same map; search
returns the nearest dots. A position on the map is a list of numbers called an **embedding**;
the model that computes it is an **embedding model** — it cannot write or answer, only place
text on the map.

## Decisions

**1. The map-maker runs on this computer** (chosen over an online model via OpenRouter).
Free, private, offline, and the Claude Code route stays key-free.

- Model: **`BAAI/bge-small-en-v1.5`**, run with the **`fastembed`** library (ONNX; no GPU,
  no torch). About 70 MB for the model plus ~80 MB of software. 384 numbers per text.
  English. Trained on general text, not law.
- Downloaded once into **`.models/`** in the project folder (ignored by git), not a hidden
  system folder, so it is visible and easy to delete.
- If it proves too weak on the checks below: `BAAI/bge-base-en-v1.5` (~210 MB, 768 numbers,
  sharper, slower) — a one-line change.
- Its published limits (512 word pieces, 384 numbers) are confirmed on this machine before
  the window size is fixed.

**2. Long parts are cut into overlapping windows** ("pages" in conversation; called
*windows* in the code, so they are not confused with PDF pages).

The model reads at most 512 word pieces — about 2,000 characters — and silently ignores the
rest. 126 of 305 articles (41%), 58 recitals and 7 annexes are longer. As one dot, AI Act
Article 5 (11,114 characters) would be placed by its first lines only; points (c)–(h) —
social scoring, emotion recognition, facial recognition — would not exist on the map. And one
dot for a long article is an average of all its topics, close to none of them.

- A window is ~1,500 characters, cut **between lines**, never inside one.
- Each new window repeats the **last 2 lines** of the previous one, so no sentence is lost at
  a seam. (Simulated on AI Act Article 5: 9 windows; point (c) on window 2.)
- A part shorter than one window is one window.
- Every window carries its part's bookmark. About 830 parts → about 2,000 windows.

**3. A part is as close as its closest window.** The part is listed once, with its best
window's score; that window is the **excerpt** shown to the agent — the paragraph that
matched, not the article's first lines.

**4. Three search tools, one per method** (rather than one tool with a method setting), so
each description says when to use it and the trace shows the agent's choice:

| Tool | Best for | Shown in `ask` as |
|---|---|---|
| `keyword_search` (exists) | exact words, phrases, article numbers, names | 🔎 |
| `meaning_search` (new) | ideas in your own words | 🧭 |
| `hybrid_search` (new) | both at once, when unsure | 🔀 |

All three take the same inputs (`query`, `law`, `kind`, `limit`), keep the **grouping**
(articles first, then recitals, then annexes, each ranked within its kind), and return the
same result shape: bookmark, kind, label, title, pages, excerpt, score.

**5. Combined search merges by rank, not by score.** Keyword and meaning scores are on
different scales, so they are not added. Each method votes by position: a part earns
`1 / (60 + its rank)` from each list it appears in, and the votes are summed
(*reciprocal rank fusion*; 60 is the standard constant, not tuned). A part high on both lists
rises; a part top on only one still appears. Done within each kind, so grouping holds.

## The flow

**Once, during `ingest`:** cut every part into windows → the model turns each window into 384
numbers → saved to the shelf with each window's bookmark and position. About a minute.

**Every meaning search:** the model places the question on the map → distance to every window
(cosine similarity; ~2,000 comparisons, a fraction of a second) → each part takes its best
window's score → grouped by kind → results.

## Parts

| File | Change |
|---|---|
| `src/readingroom/windows.py` | new — cut a part into overlapping windows |
| `src/readingroom/meaning.py` | new — the model; build the map; meaning search; rank fusion |
| `src/readingroom/shelf.py` | save and load each law's windows and their numbers |
| `src/readingroom/__main__.py` | `ingest` builds the map; `search --method keyword\|meaning\|hybrid` |
| `src/readingroom/mcp_server.py` | `meaning_search` and `hybrid_search` for both agents |
| `.gitignore` | `.models/` |
| `pyproject.toml` | `fastembed` |

## Errors

- A shelf built before this step has no map: `meaning_search` and `hybrid_search` refuse with
  "run `python -m readingroom ingest` first", in words the agent can pass on.
- The model download fails (no internet on first use): `ingest` says so plainly and still
  builds the rest of the shelf; keyword search keeps working.
- Starting the tools takes a few seconds longer, because the model is loaded once at startup.

## How we will know it works

**Offline tests (seconds, no model):** windows are cut between lines, overlap by 2 lines,
lose no text, and short parts stay whole; nearest-window search and best-window-per-part,
using a tiny fake map-maker with known positions; rank fusion on hand-made lists; grouping
holds for all three methods; refusals for a shelf without a map.

**Real checks on the three laws (with the real model):**

| Search | Method | Expected near the top |
|---|---|---|
| keeping records correct | meaning | GDPR Article 5 |
| prohibited AI practices | meaning | AI Act Article 5 |
| right to be forgotten | meaning | GDPR Article 17 ("right to erasure") |
| explanation of automated decisions | meaning | GDPR Recital 71 |
| rating citizens based on how they behave | meaning | AI Act Article 5 (social scoring, point (c)) |
| "Article 22" | keyword | still works as today |

If the small model fails some, the results are reported and the choice made together — it is
not tuned until it passes.

**Real runs:** two `ask` questions (about 2 cents), to watch whether the agent picks the
right search tool.

## Built in two halves, with a stop after each

1. **The map** — windows, the model, building the map in `ingest`, and
   `search --method meaning` / `--method hybrid` to try by hand. No AI agent involved.
2. **The tools** — `meaning_search` and `hybrid_search` for both agents, then the real runs.

## Costs

- One-time download of about 150 MB.
- `ingest` about a minute slower.
- The tools start a few seconds slower.
- Searching costs nothing: the model runs locally.

## Not in this step

- Re-ranking results with a second, larger model.
- A model trained on legal text.
- Telling the agent *when* to prefer which search — that is the research method, step 6.
  This step only describes each tool honestly.
