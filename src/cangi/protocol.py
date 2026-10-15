"""Wire format shared with the CAD plugins. Newline-delimited JSON.

plugin -> core, event:  {"platform", "ts", "kind", "id", "type", "props", "cmd"}
plugin -> core, guide:  {"platform", "op": "guide", "action": "ask" | "next" | "back" | "stop", "text": str}
core -> plugin:         {"op": "overlay", "seq": int, "steps": [step, ...], "status": status}

An overlay frame always carries the full set of active steps. An empty list clears the overlay.
status is {"state": "idle" | "thinking" | "error" | "done", "text": str}.
Step kinds and payloads:
  highlight  {"tool": <platform command id>, "subtle": bool}
  arrow      {"world": [x, y, z], "text": str}
  region     {"space": "sketch" | "world", "center": [x, y] or [x, y, z], "radius": float, "text": str}
  panel      {"lines": [str, ...]}
Plugins ignore step kinds they do not support.
"""
import json
from typing import Iterable, Optional

from .walkthrough import Step


def encode(obj: dict) -> bytes:
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")


IDLE = {"state": "idle", "text": ""}


def overlay_frame(seq: int, steps: Iterable[Step], status: Optional[dict] = None) -> dict:
    return {"op": "overlay", "seq": seq, "steps": [s.to_wire() for s in steps],
            "status": status or IDLE}
