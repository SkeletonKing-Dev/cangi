import logging
import queue
import threading
import time
from collections import deque
from typing import Callable, List

from .normalize import normalize
from .schema import Event

log = logging.getLogger("cangi.bus")


class EventBus:
    """Bounded queue with a worker thread. Producers never block; when full, the oldest event is dropped."""

    def __init__(self, maxsize: int = 10000):
        self._q = queue.Queue(maxsize)
        self._subs: List[Callable[[Event], None]] = []
        self._stop = threading.Event()
        self._thread = None
        self.dropped = 0
        self.rejected = 0
        self.latencies_ns = deque(maxlen=100000)

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        self._subs.append(callback)

    def publish(self, platform: str, raw: dict) -> None:
        item = (platform, raw)
        try:
            self._q.put_nowait(item)
            return
        except queue.Full:
            pass
        try:
            self._q.get_nowait()
        except queue.Empty:
            pass
        self.dropped += 1
        try:
            self._q.put_nowait(item)
        except queue.Full:
            self.dropped += 1

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="cangi-bus", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not (self._stop.is_set() and self._q.empty()):
            try:
                platform, raw = self._q.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                event = normalize(platform, raw)
            except Exception as exc:
                self.rejected += 1
                log.warning("rejected event: %s", exc)
                continue
            for cb in self._subs:
                try:
                    cb(event)
                except Exception:
                    log.exception("subscriber failed")
            self.latencies_ns.append(time.time_ns() - event.timestamp_ns)
