# Step 3 — readingroom gets its own chef

*Approved 29 Sep 2026.* Makes readingroom usable without Claude Code (option B), while
the Claude Code route (option A) keeps working.

## What this step does

`python -m readingroom ask "question"` lets an AI model, through OpenRouter, research the
shelf with `keyword_search` and answer with citations. Every search is printed as it
happens; the end shows searches, rounds, tokens and cost.

## The parts

| File | What it does |
|---|---|
| `src/readingroom/model.py` | The connection to the model (OpenRouter via the `openai` library). Turns responses into plain `Reply` / `ToolCall` / `Usage` shapes. |
| `src/readingroom/agent.py` | The loop: ask the model → run the search it asks for → hand back the results → repeat until it answers. Safety limit of 10 searches. |
| `src/readingroom/mcp_server.py` | Unchanged role: the one tool. **Both chefs use this same helper program** — Claude Code over MCP, our loop by calling it directly — so they see the same tool, description and errors. |

The key lives in `readingroom/.env` (copied from glassbox), which git ignores. The model
is `openai/gpt-5-mini` unless `READINGROOM_MODEL` in `.env` or `--model` says otherwise.

## Carried over from glassbox

- Only errors that can succeed on a second try are retried (the `openai` library's own
  retry does exactly that), so "out of credit" fails at once instead of stalling.
- Output is capped at 8,000 tokens, and a cut-off answer is always reported as cut off.
- No automatic test calls a real model: the loop is tested with a scripted fake model.

## What the first real run showed

Question: *"What does the GDPR say about automated decision-making?"* — 10 searches,
12 rounds, 45,412 tokens, **$0.0072**.

- **It tried to rebuild Article 22 from fragments.** After finding Article 22 it kept
  searching for sentences inside it ("Paragraph 1 shall not apply", "explicit consent"),
  because the tool only returns ~350-character excerpts and there is no way to read a
  whole article. This is the gap the reading tools (step 4) close.
- **The ending was broken.** At the search limit the loop removed the tool and expected an
  answer; the model instead wrote more search requests as plain text, and the program
  still said it had "answered". The limit is now stated plainly in a message of its own
  ("You have no searches left. Write your final answer now…"). A test checks it.
- Logging noise (`HTTP Request: …`) came from the MCP library's default log level;
  quoted queries were shown with doubled quotes. Both fixed.

Second run, limit forced to 3 searches: a real answer with a citation on every point,
**$0.0046** — and the model said on its own that the excerpts were truncated and it could
not give the full text or exceptions of Article 22, instead of filling the gap from
memory.

## Try it

```bash
python -m readingroom ask "What does the GDPR say about automated decision-making?"
python -m readingroom ask "Which obligations apply to very large online platforms?" --max-searches 5
python -m readingroom ask "..." --model anthropic/<a Claude model on OpenRouter>
```

## Deliberately left out

| Left out | When |
|---|---|
| Reading whole articles / surrounding text | step 4 |
| A web page | later |
| Follow-up questions (conversation memory) | later |

**Status: half 1 complete (29 Sep 2026).** 119 tests, all passing.
Half 2: README for both ways of using readingroom, and `.env.example`.
