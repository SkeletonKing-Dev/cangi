import json
import logging
import os
import tempfile
import threading
import time

from .bus import EventBus

log = logging.getLogger("cangi.files")


class FileTailIngest:
    """Tails a JSONL file and publishes every complete line under a fixed platform."""

    def __init__(self, bus: EventBus, platform: str, path: str, poll_s: float = 0.02):
        self.bus, self.platform, self.path, self.poll_s = bus, platform, path, poll_s
        self._stop = threading.Event()
        self._thread = None
        self._file = None
        self._buf = b""

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="cangi-tail", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def poll_once(self) -> int:
        """Read what is available now. Returns the number of lines published."""
        if self._file is None:
            if not os.path.exists(self.path):
                return 0
            self._file = open(self.path, "rb")
            self._file.seek(0, os.SEEK_END)
        if os.fstat(self._file.fileno()).st_size < self._file.tell():
            self._file.seek(0)
            self._buf = b""
        self._buf += self._file.read()
        *lines, self._buf = self._buf.split(b"\n")
        n = 0
        for line in lines:
            if not line.strip():
                continue
            try:
                self.bus.publish(self.platform, json.loads(line))
                n += 1
            except ValueError as exc:
                log.warning("bad line: %s", exc)
        return n

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self.poll_once():
                time.sleep(self.poll_s)
        if self._file:
            self._file.close()


class FileSink:
    """Writes each overlay frame to a file, replacing the previous one atomically."""

    def __init__(self, path: str):
        self.path = path

    def send(self, frame: dict) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".cangi_")
        with os.fdopen(fd, "w") as f:
            json.dump(frame, f, separators=(",", ":"))
        os.replace(tmp, self.path)
