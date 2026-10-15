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
    """Bounded queue with one worker thread. Producers never block; when full the oldest event is dropped."""

    def __init__(self, maxsize: int = 10000):
        self._q = queue.Queue(maxsize)
        self._subs: List[Callable[[Event], None]] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self.dropped = 0
        self.rejected = 0
        self.latencies_ns = deque(maxlen=100000)

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        with self._lock:
            self._subs.append(callback)

    def publish(self, platform: str, raw: dict) -> None:
        item = (platform, raw)
        with self._lock:
            while True:
                try:
                    self._q.put_nowait(item)
                    return
                except queue.Full:
                    try:
                        self._q.get_nowait()
                        self.dropped += 1
                    except queue.Empty:
                        pass

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="cangi-bus", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

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
            self.latencies_ns.append(time.time_ns() - event.timestamp_ns)
            with self._lock:
                subs = list(self._subs)
            for cb in subs:
                try:
                    cb(event)
                except Exception:
                    log.exception("subscriber failed")
