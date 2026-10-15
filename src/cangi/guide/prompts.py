from typing import Dict

from ..schema import EVENT_TYPES
from .catalog import APP_NAMES

SCHEMA = """{
  "title": "short title",
  "steps": [
    {
      "instruction": "one user action, imperative, max 2 sentences",
      "tool": "command id from the list, or null",
      "region": {"space": "sketch", "center": [x, y], "radius": r, "label": "short"} or null,
      "expect": {"event": "event type", "type": "entity type"} or null
    }
  ]
}"""


def system_prompt(platform: str, catalog: Dict[str, str]) -> str:
    app = APP_NAMES.get(platform, platform or "a CAD application")
    tools = "\n".join("  %s: %s" % (k, v) for k, v in catalog.items()) or "  (none)"
    return (
        "You are a CAD tutor inside %s. Guide the user through their task one action at a time.\n"
        "Reply with a single JSON object and nothing else (no markdown, no commentary):\n%s\n\n"
        "Rules:\n"
        "- 4 to 10 steps. Each step is one action the user can do and then confirm.\n"
        "- tool: the toolbar command the user needs for this step. Use an id from the list exactly, or null.\n"
        "- region: circle an area the user must look at. space \"sketch\" uses sketch coordinates in mm "
        "with the origin at (0, 0); space \"world\" uses model coordinates. Use it for drawing steps, "
        "for example the corner where a rectangle starts. Otherwise null.\n"
        "- expect: the event that shows the step is done. event is one of: %s. "
        "type is a lowercase entity type such as sketch, body, pad, box. Use null if unsure.\n"
        "- Prefer the PartDesign workflow (Body, Sketch, Pad) for parametric parts. "
        "Use Part primitives only for a quick shape.\n"
        "- Say which workbench is needed when it matters.\n\n"
        "Available tools:\n%s"
    ) % (app, SCHEMA, ", ".join(EVENT_TYPES), tools)


def user_prompt(request: str, context: str) -> str:
    return "Current state: %s\n\nUser request: %s" % (context, request)


def repair_prompt(error: str) -> str:
    return ("That reply was not usable (%s). Reply again with only the JSON object described "
            "in the instructions." % error)
