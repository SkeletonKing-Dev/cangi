from cangi.guide.context import ContextTracker
from cangi.schema import Event


def ev(t, id="", type="", cmd=""):
    return Event(1, "freecad", t, id, type, command_context=cmd)


def test_summary_tracks_objects_and_mode():
    c = ContextTracker()
    assert c.summary("freecad") == "mode: unknown; objects: none"
    c.update(ev("object_created", "Body", "body", "partdesignworkbench"))
    c.update(ev("object_modified", "Sketch", "sketch", "sketch_edit"))
    assert c.summary("freecad") == "mode: sketch_edit; objects: Body (body), Sketch (sketch)"
    c.update(ev("object_deleted", "Sketch"))
    assert "Sketch" not in c.summary("freecad")
    c.update(ev("document_closed"))
    assert c.summary("freecad").endswith("objects: none")


def test_platforms_are_separate():
    c = ContextTracker()
    c.update(ev("object_created", "A", "box"))
    assert c.summary("autocad").endswith("objects: none")
