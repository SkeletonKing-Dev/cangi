import pytest

from cangi.bus import EventBus
from cangi.hub import Hub
from tests.helpers import wait_for

pytestmark = pytest.mark.integration


@pytest.fixture
def hub():
    bus = EventBus()
    got = []
    bus.subscribe(got.append)
    bus.start()
    h = Hub(bus, port=0)
    h.start()
    h.got = got
    yield h
    h.stop()
    bus.stop()


def test_event_reaches_bus(hub, connect, make_raw):
    c = connect(hub.address)
    c.send(dict(make_raw(ts=5), platform="freecad"))
    assert wait_for(lambda: len(hub.got) == 1)
    assert hub.got[0].platform == "freecad" and hub.got[0].timestamp_ns == 5


def test_bad_lines_do_not_break_connection(hub, connect, make_raw):
    c = connect(hub.address)
    c.sock.sendall(b"garbage\n[1,2]\n{\"no\":\"platform\"}\n")
    c.send(dict(make_raw(ts=7), platform="freecad"))
    assert wait_for(lambda: len(hub.got) == 1)


def test_broadcast_reaches_all_clients(hub, connect):
    a, b = connect(hub.address), connect(hub.address)
    assert wait_for(lambda: hub.client_count() == 2)
    hub.send({"op": "overlay", "seq": 1, "steps": []})
    assert a.recv()["seq"] == 1
    assert b.recv()["seq"] == 1


def test_late_client_gets_last_frame(hub, connect):
    hub.send({"op": "overlay", "seq": 4, "steps": []})
    c = connect(hub.address)
    assert c.recv()["seq"] == 4


def test_disconnected_client_is_removed(hub, connect):
    c = connect(hub.address)
    assert wait_for(lambda: hub.client_count() == 1)
    c.close()
    assert wait_for(lambda: hub.client_count() == 0)
    hub.send({"op": "overlay", "seq": 1, "steps": []})
