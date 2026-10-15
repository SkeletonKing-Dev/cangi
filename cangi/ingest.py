import json
import logging
import os
import socketserver
import threading
import time

from .bus import EventBus

log = logging.getLogger("cangi.ingest")


class TcpIngest:
    """Newline-delimited JSON over localhost. Each line: raw envelope plus a 'platform' key."""

    def __init__(self, bus: EventBus, host: str = "127.0.0.1", port: int = 8765):
        bus_ref = bus

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                for line in self.rfile:
                    try:
                        raw = json.loads(line)
                        bus_ref.publish(raw.pop("platform"), raw)
                    except Exception as exc:
                        log.warning("bad line: %s", exc)

        socketserver.ThreadingTCPServer.allow_reuse_address = True
        self._server = socketserver.ThreadingTCPServer((host, port), Handler)
        self._server.daemon_threads = True

    def start(self) -> None:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


class FileTailIngest:
    """Tails a JSONL file, publishing every line under a fixed platform."""

    def __init__(self, bus: EventBus, platform: str, path: str, poll_s: float = 0.02):
        self.bus, self.platform, self.path, self.poll_s = bus, platform, path, poll_s
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not os.path.exists(self.path) and not self._stop.is_set():
            time.sleep(self.poll_s)
        with open(self.path, "r") as f:
            f.seek(0, os.SEEK_END)
            while not self._stop.is_set():
                line = f.readline()
                if not line.endswith("\n"):
                    time.sleep(self.poll_s)
                    continue
                try:
                    self.bus.publish(self.platform, json.loads(line))
                except Exception as exc:
                    log.warning("bad line: %s", exc)
