import json
import socket
import time


def raw(kind="slotChangedObject", ts=1, id="Sketch", type="Sketcher::SketchObject", **extra):
    d = {"ts": ts, "kind": kind, "id": id, "type": type, "props": {"a": 1}, "cmd": "sketch_edit"}
    d.update(extra)
    return d


def wait_for(predicate, timeout=3.0, step=0.01):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(step)
    return False


class LineSocket:
    def __init__(self, address):
        self.sock = socket.create_connection(address, timeout=3)
        self.buf = b""

    def send(self, obj):
        self.sock.sendall((json.dumps(obj) + "\n").encode())

    def recv(self, timeout=3.0):
        self.sock.settimeout(timeout)
        while b"\n" not in self.buf:
            data = self.sock.recv(65536)
            if not data:
                raise ConnectionError("closed")
            self.buf += data
        line, self.buf = self.buf.split(b"\n", 1)
        return json.loads(line)

    def close(self):
        self.sock.close()
