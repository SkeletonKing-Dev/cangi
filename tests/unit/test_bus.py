import time

from cangi.bus import EventBus

from tests.helpers import wait_for


def test_delivery_and_reject(make_raw):
    got = []
    bus = EventBus()
    bus.subscribe(got.append)
    bus.start()
    bus.publish("freecad", make_raw(ts=time.time_ns()))
    bus.publish("freecad", make_raw("bad"))
    assert wait_for(lambda: len(got) == 1 and bus.rejected == 1)
    bus.stop()
    assert len(bus.latencies_ns) == 1


def test_drop_oldest(make_raw):
    bus = EventBus(maxsize=3)
    for i in range(10):
        bus.publish("freecad", make_raw(ts=i))
    assert bus.dropped == 7
    assert [bus._q.get_nowait()[1]["ts"] for _ in range(3)] == [7, 8, 9]


def test_failing_subscriber_does_not_stop_others(make_raw):
    got = []
    bus = EventBus()
    bus.subscribe(lambda e: 1 / 0)
    bus.subscribe(got.append)
    bus.start()
    bus.publish("freecad", make_raw(ts=time.time_ns()))
    assert wait_for(lambda: len(got) == 1)
    bus.stop()


def test_stop_drains_queue(make_raw):
    got = []
    bus = EventBus()
    bus.subscribe(got.append)
    for i in range(50):
        bus.publish("freecad", make_raw(ts=time.time_ns()))
    bus.start()
    bus.stop()
    assert len(got) == 50
