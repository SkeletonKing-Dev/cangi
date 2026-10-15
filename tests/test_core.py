import time
import unittest

from cangi.bus import EventBus
from cangi.normalize import normalize
from cangi.schema import Event
from cangi.walkthrough import Diagnosis, Step, StepQueue, WalkthroughController


def raw(kind="slotChangedObject", ts=1, id="Sketch", type="Sketcher::SketchObject"):
    return {"ts": ts, "kind": kind, "id": id, "type": type, "props": {"a": 1}, "cmd": "sketch_edit"}


class NormalizeTests(unittest.TestCase):
    def test_idempotent(self):
        self.assertEqual(normalize("freecad", raw()), normalize("freecad", raw()))

    def test_fields(self):
        e = normalize("freecad", raw())
        self.assertEqual((e.event_type, e.entity_type, e.platform), ("object_modified", "sketch", "freecad"))

    def test_autocad_type(self):
        e = normalize("autocad", raw("ObjectAppended", type="AcDbLine"))
        self.assertEqual((e.event_type, e.entity_type), ("object_created", "line"))

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            normalize("qcad", raw("nope"))

    def test_json(self):
        self.assertIn('"timestamp_ns":1', normalize("freecad", raw()).to_json())


class BusTests(unittest.TestCase):
    def test_delivery_and_reject(self):
        got = []
        bus = EventBus()
        bus.subscribe(got.append)
        bus.start()
        bus.publish("freecad", raw(ts=time.time_ns()))
        bus.publish("freecad", raw("bad"))
        time.sleep(0.2)
        bus.stop()
        self.assertEqual(len(got), 1)
        self.assertEqual(bus.rejected, 1)

    def test_drop_oldest(self):
        bus = EventBus(maxsize=3)
        for i in range(10):
            bus.publish("freecad", raw(ts=i))
        self.assertEqual(bus.dropped, 7)


class WalkthroughTests(unittest.TestCase):
    def test_expiry(self):
        t = [0.0]
        q = StepQueue(clock=lambda: t[0])
        q.push(Step("a", "highlight", 1, 5.0))
        t[0] = 4.0
        self.assertFalse(q.expire())
        t[0] = 5.0
        self.assertTrue(q.expire())
        self.assertTrue(q.empty())

    def test_dismiss(self):
        q = StepQueue()
        q.push(Step("a", "arrow", 1, 99, dismiss=lambda e: e.entity_id == "C1"))
        self.assertFalse(q.on_event(Event(1, "freecad", "object_modified", "C2")))
        self.assertTrue(q.on_event(Event(1, "freecad", "object_modified", "C1")))

    def test_rules(self):
        c = WalkthroughController()
        c.handle_diagnosis(Diagnosis(next_tool="x", intention_confidence=1.0, uncertainty=0.9))
        self.assertTrue(c.queue.empty())
        c.handle_diagnosis(Diagnosis(next_tool="x", intention_confidence=1.0, mastery=0.1,
                                     walkthrough_lines=["one"]))
        self.assertEqual([s.id for s in c.active()], ["tool", "panel"])

    def test_priority_order(self):
        q = StepQueue()
        q.push(Step("lo", "text", 1, 9))
        q.push(Step("hi", "text", 9, 9))
        self.assertEqual([s.id for s in q.active()], ["hi", "lo"])


if __name__ == "__main__":
    unittest.main()
