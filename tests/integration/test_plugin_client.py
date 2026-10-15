import pytest

from cangi.app import Pipeline
from cangi.demo import demo_diagnoser
from cangi_freecad.client import Client
from tests.helpers import wait_for

pytestmark = pytest.mark.integration


def test_plugin_client_sends_events_and_receives_frames(make_raw):
    pipeline = Pipeline(port=0, diagnoser=demo_diagnoser)
    pipeline.start()
    frames = []
    host, port = pipeline.hub.address
    client = Client("freecad", host, port, frames.append, retry_s=0.05)
    client.start()
    try:
        client.send(make_raw(ts=1))
        assert wait_for(lambda: frames)
        assert frames[0]["op"] == "overlay"
        assert {s["id"] for s in frames[0]["steps"]} == {"tool", "deficiency", "panel"}
    finally:
        client.stop()
        pipeline.stop()


def test_plugin_client_connects_after_hub_starts_and_keeps_queued_events(make_raw):
    pipeline = Pipeline(port=0, diagnoser=demo_diagnoser)
    host, port = pipeline.hub.address
    pipeline.hub.stop()
    pipeline = Pipeline(port=port, diagnoser=demo_diagnoser)
    frames = []
    client = Client("freecad", host, port, frames.append, retry_s=0.05)
    client.send(make_raw(ts=1))
    client.start()
    try:
        pipeline.start()
        assert wait_for(lambda: frames)
    finally:
        client.stop()
        pipeline.stop()
