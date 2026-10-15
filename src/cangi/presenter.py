import threading
from typing import Protocol, Sequence

from .protocol import overlay_frame
from .walkthrough import WalkthroughController


class FrameSink(Protocol):
    def send(self, frame: dict) -> None: ...


class OverlayPresenter:
    """Sends the controller's current steps to every sink as a full overlay frame."""

    def __init__(self, controller: WalkthroughController, sinks: Sequence[FrameSink]):
        self.controller = controller
        self.sinks = list(sinks)
        self._seq = 0
        self._lock = threading.Lock()

    def refresh(self) -> dict:
        with self._lock:
            self._seq += 1
            frame = overlay_frame(self._seq, self.controller.active())
            for sink in self.sinks:
                sink.send(frame)
            return frame
