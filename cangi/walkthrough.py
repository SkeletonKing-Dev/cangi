import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .schema import Event


@dataclass
class Step:
    id: str
    kind: str
    priority: int
    lifetime_s: float
    payload: Dict = field(default_factory=dict)
    dismiss: Optional[Callable[[Event], bool]] = None
    created: float = field(default_factory=time.monotonic)
    t0_ns: int = 0


class StepQueue:
    def __init__(self, clock=time.monotonic):
        self._steps: Dict[str, Step] = {}
        self._lock = threading.Lock()
        self._clock = clock

    def push(self, step: Step) -> None:
        step.created = self._clock()
        with self._lock:
            self._steps[step.id] = step

    def remove(self, step_id: str) -> None:
        with self._lock:
            self._steps.pop(step_id, None)

    def expire(self) -> bool:
        now = self._clock()
        with self._lock:
            dead = [k for k, s in self._steps.items() if now - s.created >= s.lifetime_s]
            for k in dead:
                del self._steps[k]
        return bool(dead)

    def on_event(self, event: Event) -> bool:
        with self._lock:
            dead = [k for k, s in self._steps.items() if s.dismiss and s.dismiss(event)]
            for k in dead:
                del self._steps[k]
        return bool(dead)

    def active(self) -> List[Step]:
        with self._lock:
            return sorted(self._steps.values(), key=lambda s: -s.priority)

    def empty(self) -> bool:
        with self._lock:
            return not self._steps


@dataclass
class Diagnosis:
    """Placeholder for the CGEM output (EXP-2)."""
    next_tool: Optional[str] = None
    intention_confidence: float = 0.0
    deficiency_constraint: Optional[str] = None
    deficiency_world_pos: Optional[tuple] = None
    deficiency_hint: str = ""
    uncertainty: float = 0.0
    mastery: float = 0.5
    walkthrough_lines: List[str] = field(default_factory=list)
    t0_ns: int = 0


class WalkthroughController:
    UNCERTAIN = 0.7
    CONFIDENT = 0.7
    LOW_MASTERY = 0.4
    HIGH_MASTERY = 0.8

    def __init__(self, queue: Optional[StepQueue] = None):
        self.queue = queue or StepQueue()

    def handle_diagnosis(self, d: Diagnosis) -> None:
        if d.uncertainty >= self.UNCERTAIN:
            return
        if d.next_tool and d.intention_confidence >= self.CONFIDENT:
            self.queue.push(Step(
                "tool", "highlight", 5, 8.0,
                {"tool": d.next_tool, "subtle": d.mastery >= self.HIGH_MASTERY},
                t0_ns=d.t0_ns))
        if d.deficiency_constraint and d.deficiency_world_pos:
            self.queue.push(Step(
                "deficiency", "arrow", 8, 12.0,
                {"world": d.deficiency_world_pos, "text": d.deficiency_hint},
                dismiss=lambda e, c=d.deficiency_constraint: e.entity_id == c and e.event_type == "object_modified",
                t0_ns=d.t0_ns))
        if d.mastery < self.LOW_MASTERY and d.walkthrough_lines:
            self.queue.push(Step(
                "panel", "panel", 3, 30.0, {"lines": d.walkthrough_lines}, t0_ns=d.t0_ns))

    def on_event(self, event: Event) -> bool:
        return self.queue.on_event(event)

    def tick(self) -> bool:
        return self.queue.expire()

    def active(self) -> List[Step]:
        return self.queue.active()
