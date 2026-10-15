import json
import logging
import socketserver
import threading
from typing import Callable, Optional, Set, Tuple

from .bus import EventBus
from .protocol import encode

log = logging.getLogger("cangi.hub")


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _Client:
    def __init__(self, sock):
        self.sock = sock
        self._lock = threading.Lock()

    def send(self, data: bytes) -> bool:
        with self._lock:
            try:
                self.sock.sendall(data)
                return True
            except OSError:
                return False


class Hub:
    """TCP endpoint for plugins. Reads events into the bus and broadcasts overlay frames to every client."""

    def __init__(self, bus: EventBus, host: str = "127.0.0.1", port: int = 8765,
                 on_message: Optional[Callable[[dict], None]] = None):
        self.bus = bus
        self._on_message = on_message
        self._clients: Set[_Client] = set()
        self._lock = threading.Lock()
        self._last: Optional[bytes] = None
        self._serving = False
        hub = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                hub._serve(self.request, self.rfile)

        self._server = _Server((host, port), Handler)

    @property
    def address(self) -> Tuple[str, int]:
        return self._server.server_address[:2]

    def start(self) -> None:
        self._serving = True
        threading.Thread(target=self._server.serve_forever, name="cangi-hub", daemon=True).start()

    def stop(self) -> None:
        if self._serving:
            self._server.shutdown()
            self._serving = False
        self._server.server_close()

    def send(self, frame: dict) -> None:
        data = encode(frame)
        with self._lock:
            self._last = data
            clients = list(self._clients)
        for c in clients:
            if not c.send(data):
                self._drop(c)

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def _drop(self, client: _Client) -> None:
        with self._lock:
            self._clients.discard(client)

    def _serve(self, sock, rfile) -> None:
        client = _Client(sock)
        with self._lock:
            self._clients.add(client)
            last = self._last
        if last:
            client.send(last)
        try:
            for line in rfile:
                self._ingest(line)
        except OSError:
            pass
        finally:
            self._drop(client)

    def _ingest(self, line: bytes) -> None:
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("not an object")
            if "op" in raw:
                self._dispatch(raw)
                return
            platform = raw.pop("platform")
        except (ValueError, KeyError) as exc:
            log.warning("bad line: %r", exc)
            return
        self.bus.publish(platform, raw)

    def _dispatch(self, message: dict) -> None:
        if self._on_message is None:
            return
        try:
            self._on_message(message)
        except Exception:
            log.exception("message handler failed")
