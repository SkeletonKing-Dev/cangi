import json

import pytest

from cangi.app import Pipeline
from cangi.guide import LLMConfig, OpenAICompatClient
from tests.integration.fake_llm import FakeLLM, completion

pytestmark = pytest.mark.integration

PLAN = json.dumps({"title": "Cube", "steps": [
    {"instruction": "Create a body", "tool": "PartDesign_Body",
     "expect": {"event": "object_created", "type": "body"}},
    {"instruction": "Create a sketch", "tool": "Sketcher_NewSketch",
     "region": {"space": "sketch", "center": [0, 0], "radius": 4, "label": "origin"}},
]})


def ask(c, text="model a cube"):
    c.send({"platform": "freecad", "op": "guide", "action": "ask", "text": text})


def frames_until(c, predicate, limit=10):
    seen = []
    for _ in range(limit):
        seen.append(c.recv())
        if predicate(seen[-1]):
            return seen
    raise AssertionError("condition not reached: %r" % seen)


def has(frame, step_id):
    return any(s["id"] == step_id for s in frame["steps"])


def test_ask_over_the_wire_with_http_llm(connect):
    with FakeLLM([completion(PLAN)]) as fake:
        chat = OpenAICompatClient(LLMConfig("k", fake.base_url, "m", timeout_s=3))
        p = Pipeline(port=0, chat=chat)
        p.start()
        try:
            c = connect(p.hub.address)
            ask(c)
            seen = frames_until(c, lambda f: has(f, "guide:panel"))
            assert seen[0]["status"]["state"] == "thinking"
            panel = next(s for s in seen[-1]["steps"] if s["id"] == "guide:panel")
            assert panel["payload"]["lines"] == ["Step 1/2", "Create a body"]
            assert "model a cube" in fake.requests[0]["body"]["messages"][1]["content"]
        finally:
            p.stop()


def test_buttons_and_event_driven_advance(connect):
    class Chat:
        def complete(self, messages):
            return PLAN

    p = Pipeline(port=0, chat=Chat())
    p.start()
    try:
        c = connect(p.hub.address)
        ask(c)
        frames_until(c, lambda f: has(f, "guide:panel") and not has(f, "guide:region"))
        c.send({"platform": "freecad", "ts": 1, "kind": "slotCreatedObject", "id": "Body",
                "type": "PartDesign::Body", "props": {}, "cmd": ""})
        frames_until(c, lambda f: has(f, "guide:region"))
        c.send({"platform": "freecad", "op": "guide", "action": "back"})
        frames_until(c, lambda f: not has(f, "guide:region") and has(f, "guide:panel"))
        c.send({"platform": "freecad", "op": "guide", "action": "stop"})
        last = frames_until(c, lambda f: f["steps"] == [])[-1]
        assert last["status"]["state"] == "idle"
    finally:
        p.stop()


def test_llm_failure_reaches_the_plugin(connect):
    with FakeLLM([(429, {})]) as fake:
        chat = OpenAICompatClient(LLMConfig("k", fake.base_url, "m", timeout_s=3))
        p = Pipeline(port=0, chat=chat)
        p.start()
        try:
            c = connect(p.hub.address)
            ask(c)
            last = frames_until(c, lambda f: f["status"]["state"] == "error")[-1]
            assert "rate limited" in last["status"]["text"]
        finally:
            p.stop()


def test_guide_disabled_reports_how_to_enable(connect):
    p = Pipeline(port=0)
    p.start()
    try:
        c = connect(p.hub.address)
        ask(c)
        frame = c.recv()
        assert frame["status"]["state"] == "error" and "--guide" in frame["status"]["text"]
    finally:
        p.stop()
