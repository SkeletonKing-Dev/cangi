import pytest

from cangi.guide.llm import LLMConfig, LLMError, OpenAICompatClient
from tests.integration.fake_llm import FakeLLM, completion

pytestmark = pytest.mark.integration

MESSAGES = [{"role": "user", "content": "hi"}]


def client(fake, **kw):
    return OpenAICompatClient(LLMConfig(api_key="k", base_url=fake.base_url, model="m", timeout_s=3, **kw))


def test_request_shape_and_reply():
    with FakeLLM([completion("hello")]) as fake:
        assert client(fake).complete(MESSAGES) == "hello"
    req = fake.requests[0]
    assert req["path"] == "/v1/chat/completions"
    assert req["headers"]["Authorization"] == "Bearer k"
    assert req["headers"]["User-Agent"].startswith("cangi")
    assert req["body"]["model"] == "m" and req["body"]["messages"] == MESSAGES
    assert req["body"]["reasoning_effort"] == "low"


def test_retries_without_optional_params_on_400():
    with FakeLLM([(400, {"error": "unknown param"}), completion("ok")]) as fake:
        assert client(fake).complete(MESSAGES) == "ok"
    assert "reasoning_effort" in fake.requests[0]["body"]
    assert "reasoning_effort" not in fake.requests[1]["body"]


def test_400_without_optional_params_is_an_error():
    with FakeLLM([(400, {"error": "bad"})]) as fake:
        with pytest.raises(LLMError) as e:
            client(fake, reasoning_effort=None).complete(MESSAGES)
    assert e.value.status == 400


@pytest.mark.parametrize("status,fragment", [(401, "authentication"), (403, "authentication"),
                                             (429, "rate limited"), (500, "error 500")])
def test_http_errors_have_readable_messages(status, fragment):
    with FakeLLM([(status, {})]) as fake:
        with pytest.raises(LLMError, match=fragment):
            client(fake).complete(MESSAGES)


@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": [{"message": {"content": None}}]},
                                  {"choices": [{"message": {"content": "  "}}]}])
def test_unusable_responses(body):
    with FakeLLM([(200, body)]) as fake:
        with pytest.raises(LLMError):
            client(fake).complete(MESSAGES)


def test_unreachable_service():
    c = OpenAICompatClient(LLMConfig(api_key="k", base_url="http://127.0.0.1:1/v1", timeout_s=1))
    with pytest.raises(LLMError, match="cannot reach"):
        c.complete(MESSAGES)


def test_config_from_env(monkeypatch):
    monkeypatch.delenv("CANGI_LLM_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMError):
        LLMConfig.from_env()
    monkeypatch.setenv("GROQ_API_KEY", "g")
    assert LLMConfig.from_env().api_key == "g"
    monkeypatch.setenv("CANGI_LLM_API_KEY", "c")
    monkeypatch.setenv("CANGI_LLM_MODEL", "other")
    cfg = LLMConfig.from_env()
    assert (cfg.api_key, cfg.model) == ("c", "other")
