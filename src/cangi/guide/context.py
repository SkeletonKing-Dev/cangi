import threading
from typing import Dict

from ..schema import Event

MAX_LISTED = 30


class ContextTracker:
    """Keeps a short description of what is open in each application, for the model prompt."""

    def __init__(self):
        self._lock = threading.Lock()
        self._objects: Dict[str, Dict[str, str]] = {}
        self._mode: Dict[str, str] = {}

    def update(self, event: Event) -> None:
        with self._lock:
            objs = self._objects.setdefault(event.platform, {})
            if event.command_context:
                self._mode[event.platform] = event.command_context
            if event.event_type in ("object_created", "object_modified") and event.entity_id:
                objs[event.entity_id] = event.entity_type
            elif event.event_type == "object_deleted":
                objs.pop(event.entity_id, None)
            elif event.event_type == "document_closed":
                objs.clear()

    def summary(self, platform: str) -> str:
        with self._lock:
            objs = list(self._objects.get(platform, {}).items())[:MAX_LISTED]
            mode = self._mode.get(platform, "unknown")
        listed = ", ".join("%s (%s)" % (k, v or "object") for k, v in objs) or "none"
        return "mode: %s; objects: %s" % (mode, listed)
