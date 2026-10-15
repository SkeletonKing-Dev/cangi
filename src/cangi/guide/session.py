from typing import List

from ..schema import Event
from ..walkthrough import Step
from .plan import GuidePlan, GuideStep

FOREVER = float("inf")
PANEL_ID = "guide:panel"
TOOL_ID = "guide:tool"
REGION_ID = "guide:region"


class GuideSession:
    """Position in a plan. Pure state; no threads or I/O."""

    def __init__(self, plan: GuidePlan, platform: str):
        self.plan = plan
        self.platform = platform
        self.index = 0

    @property
    def current(self) -> GuideStep:
        return self.plan.steps[self.index]

    def advance(self) -> bool:
        """Move to the next step. Returns False when the plan is finished."""
        if self.index + 1 >= len(self.plan.steps):
            return False
        self.index += 1
        return True

    def back(self) -> bool:
        if self.index == 0:
            return False
        self.index -= 1
        return True

    def matches(self, event: Event) -> bool:
        """True if the event shows the current step is done."""
        e = self.current.expect
        if e is None or event.platform != self.platform or event.event_type != e.event_type:
            return False
        return not e.entity_type or event.entity_type == e.entity_type

    def overlay_steps(self) -> List[Step]:
        step = self.current
        header = "Step %d/%d" % (self.index + 1, len(self.plan.steps))
        out = [Step(PANEL_ID, "panel", 3, FOREVER, {"lines": [header, step.instruction]})]
        if step.tool:
            out.append(Step(TOOL_ID, "highlight", 5, FOREVER, {"tool": step.tool, "subtle": False}))
        if step.region:
            r = step.region
            out.append(Step(REGION_ID, "region", 8, FOREVER, {
                "space": r.space, "center": list(r.center), "radius": r.radius, "text": r.label}))
        return out
