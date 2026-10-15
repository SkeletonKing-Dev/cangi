from cangi.guide.plan import Expect, GuidePlan, GuideStep, Region
from cangi.guide.session import GuideSession
from cangi.schema import Event


def make():
    steps = (
        GuideStep("one", tool="Sketcher_CreateLine", region=Region("sketch", (0, 0, 0), 5, "start"),
                  expect=Expect("object_modified", "sketch")),
        GuideStep("two"),
    )
    return GuideSession(GuidePlan("Cube", steps), "freecad")


def test_navigation_bounds():
    s = make()
    assert not s.back()
    assert s.advance() and s.index == 1
    assert not s.advance() and s.index == 1
    assert s.back() and s.index == 0


def test_overlay_steps_for_full_step():
    steps = {x.id: x for x in make().overlay_steps()}
    assert set(steps) == {"guide:panel", "guide:tool", "guide:region"}
    assert steps["guide:panel"].payload["lines"] == ["Step 1/2", "one"]
    assert steps["guide:tool"].payload == {"tool": "Sketcher_CreateLine", "subtle": False}
    assert steps["guide:region"].payload["radius"] == 5 and steps["guide:region"].payload["space"] == "sketch"
    assert all(x.lifetime_s == float("inf") for x in steps.values())


def test_overlay_steps_for_plain_step():
    s = make()
    s.advance()
    assert [x.id for x in s.overlay_steps()] == ["guide:panel"]


def test_matches_event():
    s = make()
    assert s.matches(Event(1, "freecad", "object_modified", "S", "sketch"))
    assert not s.matches(Event(1, "freecad", "object_modified", "S", "body"))
    assert not s.matches(Event(1, "freecad", "object_created", "S", "sketch"))
    assert not s.matches(Event(1, "autocad", "object_modified", "S", "sketch"))
    s.advance()
    assert not s.matches(Event(1, "freecad", "object_modified", "S", "sketch"))
