"""Wire format shared with the CAD plugins. Newline-delimited JSON.

plugin -> core: {"platform", "ts", "kind", "id", "type", "props", "cmd"}
core -> plugin: {"op": "overlay", "seq": int, "steps": [step, ...]}

An overlay frame always carries the full set of active steps. An empty list clears the overlay.
Step kinds and payloads:
  highlight  {"tool": <platform command id>, "subtle": bool}
  arrow      {"world": [x, y, z], "text": str}
  panel      {"lines": [str, ...]}
"""
import json
from typing import Iterable

from .walkthrough import Step


def encode(obj: dict) -> bytes:
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")


def overlay_frame(seq: int, steps: Iterable[Step]) -> dict:
    return {"op": "overlay", "seq": seq, "steps": [s.to_wire() for s in steps]}
