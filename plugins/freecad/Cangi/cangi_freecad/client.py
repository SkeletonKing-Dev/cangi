import json
import logging
import queue
import socket
import threading

log = logging.getLogger("cangi.client")


class Client:
    """Sends events to the hub and hands received overlay frames to on_frame (called on a worker thread)."""

    def __init__(self, platform, host, port, on_frame, retry_s=1.0, maxsize=10000):
        self.platform = platform
        self.host = host
        self.port = port
        self.on_frame = on_frame
        self.retry_s = retry_s
        self._outbox = queue.Queue(maxsize)
        self._pending = None
        self._stop = threading.Event()
        self._thread = None

    def send(self, raw):
        data = dict(raw, platform=self.platform)
        line = (json.dumps(data, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            self._outbox.put_nowait(line)
        except queue.Full:
            pass

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="cangi-client", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _run(self):
        while not self._stop.is_set():
            try:
                sock = socket.create_connection((self.host, self.port), timeout=2)
            except OSError:
                self._stop.wait(self.retry_s)
                continue
            sock.settimeout(None)
            self._session(sock)
            self._stop.wait(self.retry_s)

    def _session(self, sock):
        closed = threading.Event()
        reader = threading.Thread(target=self._read, args=(sock, closed), daemon=True)
        reader.start()
        while not self._stop.is_set() and not closed.is_set():
            if self._pending is None:
                try:
                    self._pending = self._outbox.get(timeout=0.2)
                except queue.Empty:
                    continue
            try:
                sock.sendall(self._pending)
            except OSError:
                break
            self._pending = None
        closed.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()
        reader.join(timeout=1)

    def _read(self, sock, closed):
        buf = b""
        try:
            while True:
                data = sock.recv(65536)
                if not data:
                    break
                buf += data
                *lines, buf = buf.split(b"\n")
                for line in lines:
                    self._dispatch(line)
        except OSError:
            pass
        closed.set()

    def _dispatch(self, line):
        try:
            frame = json.loads(line)
        except ValueError:
            log.warning("bad frame")
            return
        if frame.get("op") != "overlay":
            return
        try:
            self.on_frame(frame)
        except Exception:
            log.exception("frame handler failed")
