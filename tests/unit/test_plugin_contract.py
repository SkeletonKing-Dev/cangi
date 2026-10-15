"""Plugin output must be accepted by the core normalizer."""
import json
import pathlib

import pytest

from cangi.normalize import normalize
from cangi_freecad.observers import DocObserver, SelObserver, plain

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


class Obj:
    def __init__(self, name, type_id, **attrs):
        self.Name, self.TypeId = name, type_id
        self.__dict__.update(attrs)


class Constraint:
    Type, Name, First, Second, Value = "Distance", "c", 0, -1, 5.0


def collect():
    out = []

    def emit(kind, entity_id, entity_type, props=None):
        out.append({"ts": 1, "kind": kind, "id": entity_id, "type": entity_type,
                    "props": props or {}, "cmd": ""})
    return out, emit


def test_freecad_events_normalize():
    out, emit = collect()
    d = DocObserver(emit)
    sketch = Obj("Sketch", "Sketcher::SketchObject", Constraints=[Constraint()], Geometry=[1, 2],
                 FullyConstrained=False, Placement=[0, 0, 0])
    d.slotCreatedDocument(Obj("Doc", "x"))
    d.slotActivatedDocument(Obj("Doc", "x"))
    d.slotCreatedObject(sketch)
    d.slotChangedObject(sketch, "Constraints")
    d.slotDeletedObject(sketch)
    d.slotDeletedDocument(Obj("Doc", "x"))
    s = SelObserver(emit)
    s.addSelection("Doc", "Sketch", "Edge1", (0, 0, 0))
    s.removeSelection("Doc", "Sketch", "Edge1")
    s.clearSelection("Doc")
    types = [normalize("freecad", r).event_type for r in out]
    assert types == ["document_created", "document_activated", "object_created", "object_modified",
                     "object_deleted", "document_closed", "selection_changed", "selection_changed",
                     "selection_changed"]
    json.dumps(out)


def test_sketch_state_only_for_constraint_and_geometry_props():
    out, emit = collect()
    d = DocObserver(emit)
    sketch = Obj("S", "Sketcher::SketchObject", Constraints=[Constraint()], Geometry=[],
                 FullyConstrained=True, Label="a")
    d.slotChangedObject(sketch, "Label")
    d.slotChangedObject(sketch, "Constraints")
    assert "constraints" not in out[0]["props"]
    assert out[1]["props"]["constraint_count"] == 1
    assert out[1]["props"]["fully_constrained"] is True


def test_changed_tracks_old_value_and_forgets_deleted_objects():
    out, emit = collect()
    d = DocObserver(emit)
    o = Obj("B", "Part::Box", Length=1)
    d.slotChangedObject(o, "Length")
    o.Length = 2
    d.slotChangedObject(o, "Length")
    assert (out[1]["props"]["old"], out[1]["props"]["new"]) == (1, 2)
    d.slotDeletedObject(o)
    assert d._last == {}


def test_activation_callback():
    called = []
    d = DocObserver(lambda *a, **k: None, on_activate=lambda: called.append(1))
    d.slotActivatedDocument(Obj("Doc", "x"))
    assert called == [1]


def test_plain_handles_vectors_and_depth():
    class V:
        x, y, z = 1.0, 2.0, 3.0
    assert plain(V()) == [1.0, 2.0, 3.0]
    assert plain([[[[1]]]]) == [[[ "[1]" ]]]
    assert plain(object()).startswith("<object")


@pytest.mark.parametrize("platform", ["autocad", "qcad"])
def test_fixture_lines_normalize(platform):
    lines = (FIXTURES / (platform + ".jsonl")).read_text().splitlines()
    assert lines
    for line in lines:
        raw = json.loads(line)
        raw.pop("platform", None)
        normalize(platform, raw)
