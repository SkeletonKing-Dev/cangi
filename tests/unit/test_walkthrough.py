from cangi.protocol import encode, overlay_frame
from cangi.schema import Event
from cangi.walkthrough import Diagnosis, Step, StepQueue, WalkthroughController


def test_expiry():
    t = [0.0]
    q = StepQueue(clock=lambda: t[0])
    q.push(Step("a", "highlight", 1, 5.0))
    t[0] = 4.0
    assert not q.expire()
    t[0] = 5.0
    assert q.expire()
    assert q.empty()


def test_dismiss():
    q = StepQueue()
    q.push(Step("a", "arrow", 1, 99, dismiss=lambda e: e.entity_id == "C1"))
    assert not q.on_event(Event(1, "freecad", "object_modified", "C2"))
    assert q.on_event(Event(1, "freecad", "object_modified", "C1"))


def test_dismiss_callback_may_reenter_queue():
    q = StepQueue()
    q.push(Step("a", "arrow", 1, 99, dismiss=lambda e: q.empty() is False))
    assert q.on_event(Event(1, "freecad", "object_modified", "x"))


def test_priority_order():
    q = StepQueue()
    q.push(Step("lo", "text", 1, 9))
    q.push(Step("hi", "text", 9, 9))
    assert [s.id for s in q.active()] == ["hi", "lo"]


def test_uncertain_diagnosis_is_ignored():
    c = WalkthroughController()
    assert not c.handle_diagnosis(Diagnosis(next_tool="x", intention_confidence=1.0, uncertainty=0.9))
    assert c.queue.empty()


def test_rules_by_mastery():
    c = WalkthroughController()
    c.handle_diagnosis(Diagnosis(next_tool="x", intention_confidence=1.0, mastery=0.1,
                                 walkthrough_lines=["one"]))
    assert [s.id for s in c.active()] == ["tool", "panel"]
    assert c.active()[0].payload["subtle"] is False


def test_subtle_highlight_for_experts():
    c = WalkthroughController()
    c.handle_diagnosis(Diagnosis(next_tool="x", intention_confidence=1.0, mastery=0.9))
    assert c.active()[0].payload["subtle"] is True


def test_deficiency_dismissed_by_owning_object_change():
    c = WalkthroughController()
    c.handle_diagnosis(Diagnosis(deficiency_constraint="Sketch.3", deficiency_world_pos=(1, 2, 0)))
    assert not c.on_event(Event(1, "freecad", "object_modified", "Other"))
    assert not c.on_event(Event(1, "freecad", "object_created", "Sketch"))
    assert c.on_event(Event(1, "freecad", "object_modified", "Sketch"))
    assert c.queue.empty()


def test_frame_is_json_serializable_and_full_state():
    c = WalkthroughController()
    c.handle_diagnosis(Diagnosis(next_tool="x", intention_confidence=1.0,
                                 deficiency_constraint="S.0", deficiency_world_pos=(1, 2, 3),
                                 deficiency_hint="h"))
    frame = overlay_frame(7, c.active())
    assert frame["op"] == "overlay" and frame["seq"] == 7
    assert [s["id"] for s in frame["steps"]] == ["deficiency", "tool"]
    assert encode(frame).endswith(b"\n")
    assert overlay_frame(8, [])["steps"] == []
