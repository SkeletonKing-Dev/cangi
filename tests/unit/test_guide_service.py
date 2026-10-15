import json

import pytest

from cangi.guide.llm import LLMError
from cangi.guide.service import GuideService
from cangi.presenter import OverlayPresenter
from cangi.schema import Event
from cangi.walkthrough import WalkthroughController

PLAN = json.dumps({"title": "Cube", "steps": [
    {"instruction": "Create a body", "tool": "PartDesign_Body",
     "expect": {"event": "object_created", "type": "body"}},
    {"instruction": "Create a sketch", "tool": "Sketcher_NewSketch",
     "region": {"space": "sketch", "center": [0, 0], "radius": 4, "label": "origin"}},
]})


class FakeChat:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, messages):
        self.calls.append(list(messages))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class Recorder:
    def __init__(self):
        self.frames = []

    def send(self, frame):
        self.frames.append(frame)

    @property
    def last(self):
        return self.frames[-1]


def build(chat, executor=lambda fn: fn()):
    controller = WalkthroughController()
    rec = Recorder()
    presenter = OverlayPresenter(controller, [rec])
    service = GuideService(chat, controller, presenter, executor=executor)
    return service, rec


def ask(service, text="model a cube"):
    service.handle_message({"op": "guide", "action": "ask", "platform": "freecad", "text": text})


def nav(service, action):
    service.handle_message({"op": "guide", "action": action, "platform": "freecad"})


def ids(frame):
    return [s["id"] for s in frame["steps"]]


def test_ask_shows_thinking_then_first_step():
    service, rec = build(FakeChat(PLAN))
    ask(service)
    assert rec.frames[0]["status"]["state"] == "thinking"
    assert ids(rec.last) == ["guide:tool", "guide:panel"]
    assert rec.last["status"]["state"] == "idle"
    tool = next(s for s in rec.last["steps"] if s["id"] == "guide:tool")
    assert tool["payload"]["tool"] == "PartDesign_Body"


def test_prompt_contains_request_context_and_catalog():
    chat = FakeChat(PLAN)
    service, _ = build(chat)
    service.on_event(Event(1, "freecad", "object_created", "Body", "body", command_context="partdesignworkbench"))
    ask(service, "model a cube")
    system, user = chat.calls[0]
    assert "Sketcher_CreateLine" in system["content"]
    assert "model a cube" in user["content"] and "Body (body)" in user["content"]


def test_next_back_and_finish():
    service, rec = build(FakeChat(PLAN))
    ask(service)
    nav(service, "next")
    assert ids(rec.last) == ["guide:region", "guide:tool", "guide:panel"]
    panel = next(s for s in rec.last["steps"] if s["id"] == "guide:panel")
    assert panel["payload"]["lines"] == ["Step 2/2", "Create a sketch"]
    nav(service, "back")
    assert "guide:region" not in ids(rec.last)
    nav(service, "next")
    nav(service, "next")
    assert rec.last["steps"] == []
    assert rec.last["status"] == {"state": "done", "text": "Finished: Cube"}


def test_stop_clears():
    service, rec = build(FakeChat(PLAN))
    ask(service)
    nav(service, "stop")
    assert rec.last["steps"] == [] and rec.last["status"]["state"] == "idle"
    n = len(rec.frames)
    nav(service, "next")
    assert len(rec.frames) == n


def test_expected_event_advances():
    service, rec = build(FakeChat(PLAN))
    ask(service)
    service.on_event(Event(1, "freecad", "object_created", "Body", "sketch"))
    assert "guide:region" not in ids(rec.last)
    service.on_event(Event(1, "freecad", "object_created", "Body", "body"))
    assert "guide:region" in ids(rec.last)


def test_bad_json_is_retried_once_with_error_feedback():
    chat = FakeChat("nonsense", PLAN)
    service, rec = build(chat)
    ask(service)
    assert len(chat.calls) == 2
    assert chat.calls[1][-1]["role"] == "user" and "not usable" in chat.calls[1][-1]["content"]
    assert "guide:panel" in ids(rec.last)


def test_second_bad_reply_reports_error():
    service, rec = build(FakeChat("nonsense", "still nonsense"))
    ask(service)
    assert rec.last["status"]["state"] == "error"
    assert rec.last["steps"] == []


def test_llm_error_reported_without_retry():
    chat = FakeChat(LLMError("rate limited"))
    service, rec = build(chat)
    ask(service)
    assert len(chat.calls) == 1
    assert rec.last["status"] == {"state": "error", "text": "rate limited"}


def test_unexpected_exception_is_contained():
    service, rec = build(FakeChat(RuntimeError("boom")))
    ask(service)
    assert rec.last["status"] == {"state": "error", "text": "unexpected error"}


def test_new_ask_replaces_old_guide_immediately():
    service, rec = build(FakeChat(PLAN, PLAN), executor=lambda fn: None)
    pending = []
    service._executor = pending.append
    ask(service)
    pending.pop()()
    assert "guide:panel" in ids(rec.last)
    ask(service)
    assert rec.last["steps"] == [] and rec.last["status"]["state"] == "thinking"


def test_stale_result_is_discarded():
    pending = []
    service, rec = build(FakeChat(PLAN, PLAN), executor=pending.append)
    ask(service)
    ask(service)
    first, second = pending
    second()
    frames = len(rec.frames)
    first()
    assert len(rec.frames) == frames
    assert "guide:panel" in ids(rec.last)


def test_stop_while_thinking_discards_result():
    pending = []
    service, rec = build(FakeChat(PLAN), executor=pending.append)
    ask(service)
    nav(service, "stop")
    pending[0]()
    assert rec.last["steps"] == [] and rec.last["status"]["state"] == "idle"


def test_ignores_other_messages_and_empty_ask():
    chat = FakeChat()
    service, rec = build(chat)
    service.handle_message({"op": "other"})
    ask(service, "   ")
    nav(service, "dance")
    assert rec.frames == [] and chat.calls == []
