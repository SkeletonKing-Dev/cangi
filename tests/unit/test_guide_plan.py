import json

import pytest

from cangi.guide.plan import MAX_STEPS, PlanError, extract_json, parse_plan

TOOLS = {"Sketcher_CreateLine", "PartDesign_Pad"}


def reply(steps, title="Cube"):
    return json.dumps({"title": title, "steps": steps})


def test_valid_plan():
    plan = parse_plan(reply([{
        "instruction": "Draw a line",
        "tool": "Sketcher_CreateLine",
        "region": {"space": "sketch", "center": [0, 0], "radius": 5, "label": "start"},
        "expect": {"event": "object_modified", "type": "Sketch"},
    }]), TOOLS)
    s = plan.steps[0]
    assert plan.title == "Cube"
    assert s.tool == "Sketcher_CreateLine"
    assert s.region.center == (0.0, 0.0, 0.0) and s.region.radius == 5.0 and s.region.label == "start"
    assert (s.expect.event_type, s.expect.entity_type) == ("object_modified", "sketch")


@pytest.mark.parametrize("text", [
    "```json\n%s\n```",
    "Sure, here is the plan:\n%s\nGood luck.",
    "  %s  ",
])
def test_extract_from_decorated_reply(text):
    body = reply([{"instruction": "x"}])
    assert extract_json(text % body)["title"] == "Cube"


def test_no_json():
    with pytest.raises(PlanError):
        parse_plan("I cannot help with that", TOOLS)


@pytest.mark.parametrize("data", [[], {"steps": "no"}, {"steps": []}, {"steps": [{"tool": "x"}]},
                                  {"steps": [5, None]}])
def test_unusable_plans(data):
    with pytest.raises(PlanError):
        parse_plan(json.dumps(data), TOOLS)


def test_unknown_tool_is_dropped_but_step_kept():
    plan = parse_plan(reply([{"instruction": "x", "tool": "Made_Up"}]), TOOLS)
    assert plan.steps[0].tool is None


@pytest.mark.parametrize("region", [
    {"space": "moon", "center": [0, 0], "radius": 1},
    {"space": "sketch", "center": [0], "radius": 1},
    {"space": "sketch", "center": [0, 0], "radius": 0},
    {"space": "sketch", "center": [0, 0], "radius": -1},
    {"space": "sketch", "center": [0, "a"], "radius": 1},
    {"space": "sketch", "center": [0, True], "radius": 1},
    {"space": "sketch", "center": [0, 0], "radius": 1e12},
    "circle",
])
def test_bad_region_is_dropped(region):
    plan = parse_plan(reply([{"instruction": "x", "region": region}]), TOOLS)
    assert plan.steps[0].region is None


def test_nan_region_is_dropped():
    text = '{"steps":[{"instruction":"x","region":{"space":"sketch","center":[NaN,0],"radius":1}}]}'
    assert parse_plan(text, TOOLS).steps[0].region is None


def test_bad_expect_is_dropped():
    plan = parse_plan(reply([{"instruction": "x", "expect": {"event": "explode"}}]), TOOLS)
    assert plan.steps[0].expect is None


def test_step_cap_and_text_cap():
    plan = parse_plan(reply([{"instruction": "x" * 1000}] * 50), TOOLS)
    assert len(plan.steps) == MAX_STEPS
    assert len(plan.steps[0].instruction) <= 400
