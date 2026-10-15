import statistics
import time

from .bus import EventBus


def _event(i: int) -> dict:
    return {"ts": time.time_ns(), "kind": "slotChangedObject", "id": "o%d" % i,
            "type": "Sketcher::SketchObject", "props": {"i": i}}


def run(name: str, n: int, duration_s: float) -> None:
    bus = EventBus()
    bus.subscribe(lambda e: None)
    bus.start()
    gap = duration_s / n
    t0 = time.perf_counter()
    for i in range(n):
        bus.publish("freecad", _event(i))
        if gap:
            while time.perf_counter() - t0 < (i + 1) * gap:
                time.sleep(0.0005)
    time.sleep(0.3)
    bus.stop()
    lat = sorted(bus.latencies_ns)
    if not lat:
        print("%s: no events delivered" % name)
        return

    def ms(v):
        return v / 1e6

    print("%s: n=%d delivered=%d dropped=%d p50=%.3fms p99=%.3fms max=%.3fms" % (
        name, n, len(lat), bus.dropped, ms(statistics.median(lat)),
        ms(lat[max(int(len(lat) * 0.99) - 1, 0)]), ms(lat[-1])))


def main() -> None:
    run("normal 120 events / 10s", 120, 10)
    run("burst 5000 events", 5000, 0)
