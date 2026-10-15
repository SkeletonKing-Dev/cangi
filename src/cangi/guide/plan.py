import json
import math
import re
from dataclasses import dataclass
from typing import Any, Collection, Optional, Tuple

from ..schema import EVENT_TYPES

MAX_STEPS = 12
MAX_TEXT = 400
MAX_RADIUS = 1e6
SPACES = ("sketch", "world")


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class Region:
    space: str
    center: Tuple[float, float, float]
    radius: float
    label: str = ""


@dataclass(frozen=True)
class Expect:
    event_type: str
    entity_type: str = ""


@dataclass(frozen=True)
class GuideStep:
    instruction: str
    tool: Optional[str] = None
    region: Optional[Region] = None
    expect: Optional[Expect] = None


@dataclass(frozen=True)
class GuidePlan:
    title: str
    steps: Tuple[GuideStep, ...]


def extract_json(text: str) -> Any:
    """Parse the first JSON value in a model reply, tolerating code fences and surrounding prose."""
    text = (text or "").strip()
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1).strip())
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start:end + 1])
    for c in candidates:
        try:
            return json.loads(c)
        except ValueError:
            continue
    raise PlanError("reply contains no valid JSON")


def _number(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError("not a finite number")
    return float(v)


def _text(v: Any) -> str:
    return v.strip()[:MAX_TEXT] if isinstance(v, str) else ""


def _region(raw: Any) -> Optional[Region]:
    try:
        space = raw["space"]
        center = [_number(c) for c in raw["center"]]
        radius = _number(raw["radius"])
        if space not in SPACES or len(center) not in (2, 3) or not 0 < radius <= MAX_RADIUS:
            return None
        center += [0.0] * (3 - len(center))
        return Region(space, tuple(center), radius, _text(raw.get("label")))
    except (KeyError, TypeError, ValueError):
        return None


def _expect(raw: Any) -> Optional[Expect]:
    if not isinstance(raw, dict) or raw.get("event") not in EVENT_TYPES:
        return None
    return Expect(raw["event"], _text(raw.get("type")).lower())


def parse_plan(text: str, tools: Collection[str]) -> GuidePlan:
    """Validate a model reply. Unusable optional parts are dropped; a plan needs at least one step."""
    data = extract_json(text)
    if not isinstance(data, dict) or not isinstance(data.get("steps"), list):
        raise PlanError('JSON must be an object with a "steps" list')
    steps = []
    for raw in data["steps"][:MAX_STEPS]:
        if not isinstance(raw, dict):
            continue
        instruction = _text(raw.get("instruction"))
        if not instruction:
            continue
        tool = raw.get("tool")
        steps.append(GuideStep(
            instruction=instruction,
            tool=tool if isinstance(tool, str) and tool in tools else None,
            region=_region(raw.get("region")),
            expect=_expect(raw.get("expect"))))
    if not steps:
        raise PlanError("plan has no usable steps")
    return GuidePlan(_text(data.get("title")) or "Guide", tuple(steps))
