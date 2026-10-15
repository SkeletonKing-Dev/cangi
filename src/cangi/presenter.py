import threading
from typing import Optional, Protocol, Sequence

from .protocol import IDLE, overlay_frame
from .walkthrough import WalkthroughController


class FrameSink(Protocol):
    def send(self, frame: dict) -> None: ...


class OverlayPresenter:
    """Sends the controller's current steps and the current status to every sink as a full overlay frame."""

    def __init__(self, controller: WalkthroughController, sinks: Sequence[FrameSink]):
        self.controller = controller
        self.sinks = list(sinks)
        self._seq = 0
        self._status = IDLE
        self._lock = threading.Lock()

    def refresh(self, status: Optional[dict] = None) -> dict:
        """Send a frame. A given status replaces the current one."""
        with self._lock:
            if status is not None:
                self._status = status
            self._seq += 1
            frame = overlay_frame(self._seq, self.controller.active(), self._status)
            for sink in self.sinks:
                sink.send(frame)
            return frame
