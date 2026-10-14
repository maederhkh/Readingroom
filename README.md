# readingroom

**A research assistant that may only consult the documents on its own shelf.**

You give it legal texts as PDFs. It searches them, reads the relevant parts in full, searches
again when the first results are thin, and answers with a citation for every statement —
`[gdpr/article-22, p. 46]`. If the documents do not contain the answer, it says so instead of
filling the gap from memory.

It is a learning project: small, readable, and built step by step. Every step's design and
findings are written up in [`docs/steps/`](docs/steps/).

---

## How it works

```
your PDFs ──► the shelf ──► tools ──► an agent ──► a cited answer
```

**The shelf.** Each PDF is turned into clean text — page headers and footnotes removed — and
cut into the law's own parts, each with a **bookmark**:

| Part | What it is | Bookmark |
|---|---|---|
| Articles | the binding rules | `gdpr/article-22` |
| Recitals | the numbered "Whereas" paragraphs that explain how to read the articles | `gdpr/recital-71` |
| Annexes | lists and details the articles refer to | `eu-ai-act/annex-III` |

A bookmark points into one clean copy of the law, so every quotation can be checked against
the original, page by page.

**The tools.** Plain code the agent can call:

| Tool | What it does |
|---|---|
| `keyword_search` | find the parts containing some words; best articles first, then recitals, then annexes |
| `read` | open one part in full by its bookmark |
| `list_documents` | what is on the shelf |

**The agent.** An AI model decides which tool to use, with which words, and when it has
enough to answer. Two can do this job, and both use exactly the same tools:

- **Claude Code**, if you already use it — the tools appear inside it.
- **readingroom's own agent**, `readingroom ask`, which runs on its own with an OpenRouter key.

---

## Setup

You need **Python 3.12+** and [**uv**](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/maederhkh/Readingroom.git readingroom
cd readingroom
uv venv
uv pip install -e ".[dev]"
```

**Add your documents.** Create a `documents/` folder and put the PDFs in it. readingroom is
built and tested on EU regulations from EUR-Lex, one law per file:

| Law | Official PDF |
|---|---|
| GDPR | https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32016R0679 |
| AI Act | https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32024R1689 |
| Digital Services Act | https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32022R2065 |

Make sure each file contains **one law only** — some EUR-Lex downloads are a whole Official
Journal issue with several laws bound together.

**Build the shelf:**

```bash
python -m readingroom ingest
```

```
digital-services-act   102 pages   405,353 characters    93 articles  156 recitals   0 annexes
eu-ai-act              144 pages   570,890 characters   113 articles  180 recitals  13 annexes
gdpr                    88 pages   346,255 characters    99 articles  173 recitals   0 annexes
```

*(On Windows, use `.venv\Scripts\python` instead of `python` in every command, or activate the
environment first with `.venv\Scripts\activate`. On macOS/Linux: `source .venv/bin/activate`.)*

---

## Using it

### Look at the shelf yourself — no AI involved

```bash
python -m readingroom inspect gdpr                  # every article, with pages
python -m readingroom inspect gdpr --article 22     # one article in full
python -m readingroom inspect gdpr --recital 71
python -m readingroom inspect eu-ai-act --annex III
python -m readingroom search "automated decision-making"
python -m readingroom search "\"kept up to date\""  # an exact phrase
```

### Ask a question — readingroom's own agent

Copy `.env.example` to `.env` and add an [OpenRouter](https://openrouter.ai/keys) key. Then:

```bash
python -m readingroom ask "Which AI systems count as high-risk under the AI Act?"
```

You watch the research happen, then get the answer and its cost:

```
  🔎 search: high-risk law=eu-ai-act  → 15 results (top: eu-ai-act/article-9)
  📖 read: eu-ai-act/article-6  → Article 6 — Classification rules for high-risk AI systems (pp. 53–54)
  📖 read: eu-ai-act/annex-III  → Annex III — High-risk AI systems referred to in Article 6(2) (pp. 127–129)

  Answer
  ...

  3 searches · 3 reads · 7 rounds · 46,387 tokens · $0.0079
```

A question typically costs **under one cent** with the default model, `openai/gpt-5-mini`.
Choose another with `--model` or `READINGROOM_MODEL` in `.env`. The agent stops after 12 tool
calls (`--max-tool-calls` to change it).

**Privacy:** your question and the passages the tools return are sent to OpenRouter and the
model provider. That is harmless for public legislation; think twice before putting
confidential documents on the shelf.

### Ask a question — in Claude Code

Open the `readingroom` folder in [Claude Code](https://claude.com/claude-code) after building
the shelf. The project's `.mcp.json` tells Claude Code to start readingroom's tools; approve the
`readingroom` server when asked (once). Then ask, for example:

> *Using the readingroom tools, what does the GDPR say about automated decision-making?*

No OpenRouter key is needed — Claude Code is the agent. `.mcp.json` points at
`.venv/Scripts/python.exe`, the Windows location; on macOS/Linux change it to `.venv/bin/python`.

---

## What it cannot do yet

- **It matches words, not meaning.** "keeping records correct" will not find "accurate and kept
  up to date". Meaning search is the next step.
- **Its research method is minimal.** It is told to rely only on the documents and to cite
  everything — nothing more. Teaching it to break questions apart and compare sources comes later.
- **One kind of document.** It is built for EU legislation in the Official Journal layout.
  Other PDFs will be read, but their structure (articles, recitals, annexes) will not be found.

## Tests

```bash
python -m pytest -q
```

About 180 checks; none of them calls an AI model or costs anything. The ones that read the real
laws skip themselves if `documents/` is empty.

## Project layout

| Path | What |
|---|---|
| `src/readingroom/` | the code: cleaning, parts, shelf, search, tools, agent |
| `tests/` | the checks |
| `docs/steps/` | each step's design and what building it taught us |
| `.mcp.json` | tells Claude Code how to start the tools |
