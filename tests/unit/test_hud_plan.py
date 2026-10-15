from cangi_freecad.plan import plan


def step(kind, priority, **payload):
    return {"id": kind, "kind": kind, "priority": priority, "payload": payload}


def test_empty():
    assert plan([]) == {"tool": None, "markers": [], "regions": [], "lines": []}


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
    assert plan(steps) == {"tool": None, "markers": [], "regions": [], "lines": []}


def test_regions():
    steps = [step("region", 8, space="sketch", center=[1, 2], radius=3, text="here"),
             step("region", 8, space="sketch", center=[1, 2], radius=0)]
    assert plan(steps)["regions"] == [{"space": "sketch", "center": (1, 2), "radius": 3.0, "text": "here"}]


def test_circle_points_closed_and_at_radius():
    from cangi_freecad.plan import circle_points
    pts = circle_points((1, 2), 5, n=8)
    assert len(pts) == 9
    assert all(abs(a - b) < 1e-9 for a, b in zip(pts[0], pts[-1]))
    assert all(abs(((x - 1) ** 2 + (y - 2) ** 2) ** 0.5 - 5) < 1e-9 for x, y, _ in pts)


def test_status_text():
    from cangi_freecad.plan import status_text
    assert status_text({"state": "error", "text": "x"}) == "Error: x"
    assert status_text({"state": "thinking", "text": "Thinking..."}) == "Thinking..."
    assert status_text({}) == ""
