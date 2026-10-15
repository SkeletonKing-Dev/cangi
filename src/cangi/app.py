import logging
import threading
from typing import Callable, List, Optional

from .bus import EventBus
from .files import FileSink, FileTailIngest
from .guide import ChatClient, GuideService
from .hub import Hub
from .presenter import OverlayPresenter
from .schema import Event
from .walkthrough import Diagnosis, WalkthroughController

log = logging.getLogger("cangi.app")

Diagnoser = Callable[[Event], Optional[Diagnosis]]


class Pipeline:
    """Plugins -> bus -> diagnoser -> walkthrough controller -> overlay frames -> plugins."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                 qcad_in: Optional[str] = None, qcad_out: Optional[str] = None,
                 diagnoser: Optional[Diagnoser] = None,
                 chat: Optional[ChatClient] = None,
                 on_event: Optional[Callable[[Event], None]] = None,
                 tick_s: float = 0.1):
        self.bus = EventBus()
        self.controller = WalkthroughController()
        self.hub = Hub(self.bus, host, port, on_message=self._on_message)
        sinks = [self.hub]
        if qcad_out:
            sinks.append(FileSink(qcad_out))
        self.presenter = OverlayPresenter(self.controller, sinks)
        self.guide = GuideService(chat, self.controller, self.presenter) if chat else None
        self._tails: List[FileTailIngest] = []
        if qcad_in:
            self._tails.append(FileTailIngest(self.bus, "qcad", qcad_in))
        self._diagnoser = diagnoser
        self._on_event = on_event
        self._tick_s = tick_s
        self._stop = threading.Event()
        self._ticker = None
        self.bus.subscribe(self._handle)

    def _on_message(self, message: dict) -> None:
        if self.guide:
            self.guide.handle_message(message)
        elif message.get("op") == "guide" and message.get("action") == "ask":
            self.presenter.refresh({"state": "error", "text": "Guide is off. Start cangi run with --guide."})

    def _handle(self, event: Event) -> None:
        if self._on_event:
            self._on_event(event)
        if self.guide:
            self.guide.on_event(event)
        changed = self.controller.on_event(event)
        if self._diagnoser:
            diagnosis = self._diagnoser(event)
            if diagnosis:
                changed = self.controller.handle_diagnosis(diagnosis) or changed
        if changed:
            self.presenter.refresh()

    def _tick_loop(self) -> None:
        while not self._stop.wait(self._tick_s):
            if self.controller.tick():
                self.presenter.refresh()

    def start(self) -> None:
        self._stop.clear()
        self.bus.start()
        self.hub.start()
        for t in self._tails:
            t.start()
        self._ticker = threading.Thread(target=self._tick_loop, name="cangi-tick", daemon=True)
        self._ticker.start()

    def stop(self) -> None:
        self._stop.set()
        if self._ticker:
            self._ticker.join(timeout=2)
        for t in self._tails:
            t.stop()
        self.hub.stop()
        self.bus.stop()
