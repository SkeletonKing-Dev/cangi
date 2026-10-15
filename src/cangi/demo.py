from typing import Optional

from .schema import Event
from .walkthrough import Diagnosis

DEMO_TOOLS = {"freecad": "Sketcher_CreateLine", "autocad": "LINE", "qcad": "LineAction"}


def demo_diagnoser(event: Event) -> Optional[Diagnosis]:
    """Stand-in for the CGEM. Reacts to every object change with a fixed diagnosis."""
    if event.event_type != "object_modified" or not event.entity_id:
        return None
    return Diagnosis(
        next_tool=DEMO_TOOLS.get(event.platform),
        intention_confidence=1.0,
        deficiency_constraint=event.entity_id + ".0",
        deficiency_world_pos=(0.0, 0.0, 0.0),
        deficiency_hint="demo: check constraints here",
        mastery=0.2,
        walkthrough_lines=["demo step 1: select a tool", "demo step 2: add a constraint"],
        t0_ns=event.timestamp_ns,
    )
