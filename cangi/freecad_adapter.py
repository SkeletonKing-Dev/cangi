import time
from typing import Callable, List, Tuple

from .adapter import PlatformAdapter
from .bus import EventBus
from .schema import Action, Constraint, DocumentState, Entity, SolverState

SKETCH = "Sketcher::SketchObject"


def _plain(v, depth=0):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if depth > 2:
        return str(v)
    if isinstance(v, (list, tuple)):
        return [_plain(x, depth + 1) for x in v[:50]]
    if isinstance(v, dict):
        return {str(k): _plain(x, depth + 1) for k, x in v.items()}
    if hasattr(v, "x") and hasattr(v, "y"):
        return [v.x, v.y, getattr(v, "z", 0.0)]
    return str(v)


def _constraint_dict(c):
    return {"type": c.Type, "name": c.Name, "first": c.First, "second": c.Second, "value": c.Value}


def _sketch_state(obj) -> dict:
    return {
        "constraint_count": len(obj.Constraints),
        "geometry_count": len(obj.Geometry),
        "fully_constrained": bool(obj.FullyConstrained),
        "constraints": [_constraint_dict(c) for c in obj.Constraints],
    }


def _context() -> str:
    try:
        import FreeCADGui as Gui
        vp = Gui.ActiveDocument.getInEdit() if Gui.ActiveDocument else None
        if vp is not None and vp.Object.TypeId == SKETCH:
            return "sketch_edit"
        return Gui.activeWorkbench().name().lower()
    except Exception:
        return ""


class _DocObserver:
    def __init__(self, emit):
        self.emit = emit
        self._last = {}

    def slotCreatedDocument(self, doc):
        self.emit("slotCreatedDocument", doc.Name, "document")

    def slotDeletedDocument(self, doc):
        self.emit("slotDeletedDocument", doc.Name, "document")

    def slotActivatedDocument(self, doc):
        self.emit("slotActivatedDocument", doc.Name, "document")

    def slotCreatedObject(self, obj):
        self.emit("slotCreatedObject", obj.Name, obj.TypeId)

    def slotDeletedObject(self, obj):
        self.emit("slotDeletedObject", obj.Name, obj.TypeId)

    def slotChangedObject(self, obj, prop):
        try:
            new = _plain(getattr(obj, prop))
        except Exception:
            new = None
        key = (obj.Name, prop)
        old = self._last.get(key)
        self._last[key] = new
        props = {"property": prop, "old": old, "new": new}
        try:
            if obj.TypeId == SKETCH:
                props.update(_sketch_state(obj))
        except Exception:
            pass
        self.emit("slotChangedObject", obj.Name, obj.TypeId, props)


class _SelObserver:
    def __init__(self, emit):
        self.emit = emit

    def addSelection(self, doc, obj, sub, pos):
        self.emit("selection", obj, "", {"action": "add", "doc": doc, "sub": sub})

    def removeSelection(self, doc, obj, sub):
        self.emit("selection", obj, "", {"action": "remove", "doc": doc, "sub": sub})

    def clearSelection(self, doc):
        self.emit("selection", "", "", {"action": "clear", "doc": doc})


class FreeCADAdapter(PlatformAdapter):
    def __init__(self, bus: EventBus):
        self.bus = bus
        self._doc_obs = None
        self._sel_obs = None

    def _emit(self, kind, entity_id, entity_type, props=None):
        self.bus.publish("freecad", {
            "ts": time.time_ns(), "kind": kind, "id": entity_id,
            "type": entity_type, "props": props or {}, "cmd": _context(),
        })

    def connect(self) -> bool:
        import FreeCAD as App
        self._doc_obs = _DocObserver(self._emit)
        App.addDocumentObserver(self._doc_obs)
        try:
            import FreeCADGui as Gui
            self._sel_obs = _SelObserver(self._emit)
            Gui.Selection.addObserver(self._sel_obs)
        except ImportError:
            pass
        return True

    def disconnect(self) -> None:
        import FreeCAD as App
        if self._doc_obs:
            App.removeDocumentObserver(self._doc_obs)
        if self._sel_obs:
            import FreeCADGui as Gui
            Gui.Selection.removeObserver(self._sel_obs)
        self._doc_obs = self._sel_obs = None

    def _doc(self):
        import FreeCAD as App
        return App.ActiveDocument

    def get_entity(self, entity_id: str) -> Entity:
        obj = self._doc().getObject(entity_id)
        return Entity(obj.Name, obj.TypeId, {"label": obj.Label})

    def get_constraints(self) -> List[Constraint]:
        out = []
        for obj in self._doc().Objects:
            if obj.TypeId != SKETCH:
                continue
            for i, c in enumerate(obj.Constraints):
                out.append(Constraint("%s.%d" % (obj.Name, i), c.Type, [obj.Name], c.Value))
        return out

    def get_solver_state(self) -> SolverState:
        sketches = [o for o in self._doc().Objects if o.TypeId == SKETCH]
        if not sketches:
            return SolverState()
        msgs = ["%s solve=%d" % (s.Name, s.solve()) for s in sketches]
        return SolverState(all(s.FullyConstrained for s in sketches), None, msgs)

    def get_document_state(self) -> DocumentState:
        doc = self._doc()
        return DocumentState(
            doc.Name,
            [Entity(o.Name, o.TypeId) for o in doc.Objects],
            self.get_constraints(),
            self.get_solver_state(),
        )

    def subscribe(self, callback: Callable[[Action], None]) -> None:
        self.bus.subscribe(callback)

    def world_to_screen(self, x: float, y: float, z: float = 0.0) -> Tuple[float, float]:
        import FreeCAD as App
        import FreeCADGui as Gui
        view = Gui.ActiveDocument.ActiveView
        px, py = view.getPointOnViewport(App.Vector(x, y, z))
        return float(px), float(py)
