SKETCH = "Sketcher::SketchObject"
SKETCH_PROPS = ("Constraints", "Geometry")


def plain(v, depth=0):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if depth > 2:
        return str(v)
    if isinstance(v, (list, tuple)):
        return [plain(x, depth + 1) for x in v[:50]]
    if isinstance(v, dict):
        return {str(k): plain(x, depth + 1) for k, x in v.items()}
    if hasattr(v, "x") and hasattr(v, "y"):
        return [v.x, v.y, getattr(v, "z", 0.0)]
    return str(v)


def sketch_state(obj):
    return {
        "constraint_count": len(obj.Constraints),
        "geometry_count": len(obj.Geometry),
        "fully_constrained": getattr(obj, "FullyConstrained", None),
        "constraints": [
            {"type": c.Type, "name": c.Name, "first": c.First, "second": c.Second, "value": c.Value}
            for c in obj.Constraints],
    }


def context():
    try:
        import FreeCADGui as Gui
        vp = Gui.ActiveDocument.getInEdit() if Gui.ActiveDocument else None
        if vp is not None and vp.Object.TypeId == SKETCH:
            return "sketch_edit"
        return Gui.activeWorkbench().name().lower()
    except Exception:
        return ""


class DocObserver:
    """emit(kind, entity_id, entity_type, props=None)"""

    def __init__(self, emit, on_activate=None):
        self.emit = emit
        self.on_activate = on_activate
        self._last = {}

    def slotCreatedDocument(self, doc):
        self.emit("slotCreatedDocument", doc.Name, "document")

    def slotDeletedDocument(self, doc):
        self.emit("slotDeletedDocument", doc.Name, "document")

    def slotActivatedDocument(self, doc):
        self.emit("slotActivatedDocument", doc.Name, "document")
        if self.on_activate:
            self.on_activate()

    def slotCreatedObject(self, obj):
        self.emit("slotCreatedObject", obj.Name, obj.TypeId)

    def slotDeletedObject(self, obj):
        for key in [k for k in self._last if k[0] == obj.Name]:
            del self._last[key]
        self.emit("slotDeletedObject", obj.Name, obj.TypeId)

    def slotChangedObject(self, obj, prop):
        try:
            new = plain(getattr(obj, prop))
        except Exception:
            new = None
        key = (obj.Name, prop)
        old = self._last.get(key)
        self._last[key] = new
        props = {"property": prop, "old": old, "new": new}
        if obj.TypeId == SKETCH and prop in SKETCH_PROPS:
            try:
                props.update(sketch_state(obj))
            except Exception:
                pass
        self.emit("slotChangedObject", obj.Name, obj.TypeId, props)


class SelObserver:
    def __init__(self, emit):
        self.emit = emit

    def addSelection(self, doc, obj, sub, pos):
        self.emit("selection", obj, "", {"action": "add", "doc": doc, "sub": sub})

    def removeSelection(self, doc, obj, sub):
        self.emit("selection", obj, "", {"action": "remove", "doc": doc, "sub": sub})

    def clearSelection(self, doc):
        self.emit("selection", "", "", {"action": "clear", "doc": doc})
