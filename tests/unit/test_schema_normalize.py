import pytest

from cangi.normalize import KIND_MAP, normalize, normalize_type
from cangi.schema import EVENT_TYPES, PLATFORMS, Event


def test_idempotent(make_raw):
    assert normalize("freecad", make_raw()) == normalize("freecad", make_raw())


def test_fields(make_raw):
    e = normalize("freecad", make_raw())
    assert (e.event_type, e.entity_type, e.platform) == ("object_modified", "sketch", "freecad")
    assert e.command_context == "sketch_edit"
    assert e.properties == {"a": 1}


def test_autocad_type(make_raw):
    e = normalize("autocad", make_raw("ObjectAppended", type="AcDbLine"))
    assert (e.event_type, e.entity_type) == ("object_created", "line")


@pytest.mark.parametrize("raw_type,expected", [
    ("Sketcher::SketchObject", "sketch"),
    ("Part::Feature", "solid"),
    ("Part::Box", "box"),
    ("AcDbCircle", "circle"),
    ("Line", "line"),
    ("", ""),
    (None, ""),
])
def test_normalize_type(raw_type, expected):
    assert normalize_type(raw_type) == expected


def test_unknown_kind(make_raw):
    with pytest.raises(ValueError):
        normalize("qcad", make_raw("nope"))


def test_unknown_platform(make_raw):
    with pytest.raises(ValueError):
        normalize("solidworks", make_raw())


def test_missing_ts():
    with pytest.raises(ValueError):
        normalize("freecad", {"kind": "slotChangedObject"})


def test_kind_map_is_consistent():
    assert set(KIND_MAP) == set(PLATFORMS)
    for kinds in KIND_MAP.values():
        assert set(kinds.values()) <= set(EVENT_TYPES)


def test_event_json_and_hash():
    e = Event(1, "freecad", "object_modified", "S", properties={"a": 1})
    assert '"timestamp_ns":1' in e.to_json()
    hash(e)
