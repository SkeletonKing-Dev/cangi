import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Optional, Protocol

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-20b"
USER_AGENT = "cangi/0.2"


class LLMError(Exception):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


@dataclass
class LLMConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_s: float = 60.0
    max_tokens: int = 4096
    temperature: float = 0.2
    reasoning_effort: Optional[str] = "low"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        key = os.environ.get("CANGI_LLM_API_KEY") or os.environ.get("GROQ_API_KEY")
        if not key:
            raise LLMError("no API key: set CANGI_LLM_API_KEY (or GROQ_API_KEY)")
        return cls(
            api_key=key,
            base_url=os.environ.get("CANGI_LLM_BASE_URL", DEFAULT_BASE_URL),
            model=os.environ.get("CANGI_LLM_MODEL", DEFAULT_MODEL))


class ChatClient(Protocol):
    def complete(self, messages: List[dict]) -> str: ...


class OpenAICompatClient:
    """Chat completions over any OpenAI-compatible endpoint, using only the standard library."""

    def __init__(self, config: LLMConfig):
        self.config = config

    def complete(self, messages: List[dict]) -> str:
        body = {"model": self.config.model, "messages": messages,
                "temperature": self.config.temperature, "max_tokens": self.config.max_tokens}
        extra = {"reasoning_effort": self.config.reasoning_effort} if self.config.reasoning_effort else {}
        try:
            data = self._post(dict(body, **extra))
        except LLMError as exc:
            if exc.status != 400 or not extra:
                raise
            data = self._post(body)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError("unexpected response from the model service")
        if not content or not content.strip():
            raise LLMError("the model returned an empty reply")
        return content

    def _post(self, body: dict) -> dict:
        req = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT,
                     "Authorization": "Bearer " + self.config.api_key})
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LLMError(_http_message(exc), exc.code)
        except (urllib.error.URLError, OSError) as exc:
            raise LLMError("cannot reach the model service: %s" % getattr(exc, "reason", exc))
        except ValueError:
            raise LLMError("the model service returned invalid JSON")


def _http_message(exc: urllib.error.HTTPError) -> str:
    if exc.code in (401, 403):
        return "authentication failed, check the API key"
    if exc.code == 429:
        return "rate limited by the model service, try again shortly"
    try:
        snippet = exc.read().decode("utf-8", "replace")[:200]
    except OSError:
        snippet = ""
    return "model service error %d: %s" % (exc.code, snippet)
