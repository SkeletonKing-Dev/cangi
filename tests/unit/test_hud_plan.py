from cangi_freecad.hud import plan


def step(kind, priority, **payload):
    return {"id": kind, "kind": kind, "priority": priority, "payload": payload}


def test_empty():
    assert plan([]) == {"tool": None, "markers": [], "lines": []}


def test_highest_priority_highlight_wins():
    steps = [step("highlight", 1, tool="A"), {"id": "h2", "kind": "highlight", "priority": 5,
                                              "payload": {"tool": "B", "subtle": True}}]
    assert plan(steps)["tool"] == ("B", True)


def test_markers_and_lines():
    steps = [step("arrow", 8, world=[1, 2, 3], text="here"), step("panel", 3, lines=["a", "b"])]
    p = plan(steps)
    assert p["markers"] == [((1, 2, 3), "here")]
    assert p["lines"] == ["a", "b"]


def test_incomplete_payloads_are_ignored():
    steps = [step("highlight", 1), step("arrow", 1), step("panel", 1)]
    assert plan(steps) == {"tool": None, "markers": [], "lines": []}
