"""The connection to the AI model, through OpenRouter.

Nothing else in readingroom talks to the model library directly. The research loop
only sees the small, plain shapes below - so a fake model can stand in for the real
one in tests, and switching provider later means changing this file only.

Two lessons carried over from glassbox:
- Only retry errors that can succeed on a second try (dropped connections, rate
  limits, server errors). The openai library's own retry does exactly that; an
  "out of credit" or "bad key" error fails at once instead of stalling.
- Never lose the signal that an answer was cut off at the length limit.
"""
import os
from dataclasses import dataclass, field

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-5-mini"
# Without a cap the library asks for the model's maximum output, and OpenRouter
# reserves credit for all of it. 8,000 tokens is far more than an answer needs.
MAX_OUTPUT_TOKENS = 8000


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text, exactly as the model wrote it - it may be malformed


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float | None = None  # US dollars, when OpenRouter reports it

    def __add__(self, other: "Usage") -> "Usage":
        cost = None if self.cost is None and other.cost is None else (self.cost or 0) + (other.cost or 0)
        return Usage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens, cost)


@dataclass(frozen=True)
class Reply:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    cut_off: bool = False  # True when the model hit the length limit mid-answer
    usage: Usage = Usage()


class OpenRouterModel:
    def __init__(self, model: str | None = None):
        from openai import OpenAI

        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is not set. Put it in a .env file in the "
                               "readingroom folder - see .env.example.")
        self.model = model or os.environ.get("READINGROOM_MODEL") or DEFAULT_MODEL
        self._client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key, max_retries=3)

    def respond(self, messages: list[dict], tools: list[dict] | None) -> Reply:
        request = {"model": self.model, "messages": messages,
                   "max_completion_tokens": MAX_OUTPUT_TOKENS,
                   "extra_body": {"usage": {"include": True}}}  # ask OpenRouter to report cost
        if tools:
            request["tools"] = tools
        return reply_from(self._client.chat.completions.create(**request))


def reply_from(completion) -> Reply:
    """Turn the library's response object into our plain Reply."""
    choice = completion.choices[0]
    calls = [ToolCall(id=c.id, name=c.function.name, arguments=c.function.arguments)
             for c in (choice.message.tool_calls or [])]
    u = completion.usage
    usage = Usage(input_tokens=u.prompt_tokens, output_tokens=u.completion_tokens,
                  cost=getattr(u, "cost", None)) if u else Usage()
    return Reply(text=choice.message.content or "", tool_calls=calls,
                 cut_off=choice.finish_reason == "length", usage=usage)
