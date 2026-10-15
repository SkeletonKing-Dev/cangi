import json

import pytest

from cangi.app import Pipeline
from cangi.demo import demo_diagnoser
from tests.helpers import wait_for

pytestmark = pytest.mark.integration


@pytest.fixture
def pipeline():
    p = Pipeline(port=0, diagnoser=demo_diagnoser, tick_s=0.02)
    p.start()
    yield p
    p.stop()


def modify(make_raw, id="Sketch"):
    return dict(make_raw(ts=1, id=id), platform="freecad")


def test_event_produces_overlay_frame(pipeline, connect, make_raw):
    c = connect(pipeline.hub.address)
    c.send(modify(make_raw))
    frame = c.recv()
    assert frame["op"] == "overlay"
    assert [s["id"] for s in frame["steps"]] == ["deficiency", "tool", "panel"]
    tool = next(s for s in frame["steps"] if s["id"] == "tool")
    assert tool["payload"]["tool"] == "Sketcher_CreateLine"


def test_owner_change_dismisses_deficiency(pipeline, connect, make_raw):
    c = connect(pipeline.hub.address)
    c.send(modify(make_raw))
    first = c.recv()
    assert any(s["id"] == "deficiency" for s in first["steps"])
    pipeline.controller.queue.remove("tool")
    pipeline.controller.queue.remove("panel")
    pipeline._diagnoser = None
    c.send(modify(make_raw))
    frames = []
    assert wait_for(lambda: frames.append(c.recv()) or frames[-1]["steps"] == [])
    assert frames[-1]["seq"] > first["seq"]


def test_steps_expire(pipeline, connect, make_raw):
    now = [0.0]
    pipeline.controller.queue._clock = lambda: now[0]
    c = connect(pipeline.hub.address)
    c.send(modify(make_raw))
    assert c.recv()["steps"]
    now[0] = 100.0
    frame = c.recv()
    assert frame["steps"] == []


def test_unknown_events_produce_no_frame(pipeline, connect, make_raw):
    c = connect(pipeline.hub.address)
    c.send(dict(make_raw("bogus"), platform="freecad"))
    c.send(modify(make_raw))
    frame = c.recv()
    assert frame["seq"] == 1
    assert pipeline.bus.rejected == 1


def test_qcad_file_roundtrip(tmp_path, make_raw):
    events = tmp_path / "events.jsonl"
    frames = tmp_path / "frames.json"
    events.write_text("")
    p = Pipeline(port=0, qcad_in=str(events), qcad_out=str(frames), diagnoser=demo_diagnoser)
    p.start()
    try:
        assert wait_for(lambda: p._tails[0]._file is not None)
        raw = make_raw("transactionUpdated", ts=1, id="12", type="line")
        with open(events, "a") as f:
            f.write(json.dumps(raw) + "\n")
        assert wait_for(lambda: frames.exists())
        frame = json.loads(frames.read_text())
        tool = next(s for s in frame["steps"] if s["id"] == "tool")
        assert tool["payload"]["tool"] == "LineAction"
    finally:
        p.stop()
