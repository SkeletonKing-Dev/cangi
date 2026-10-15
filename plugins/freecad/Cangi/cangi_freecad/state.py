"""Document queries. Plain dicts in the shape of cangi.schema. Call from the GUI thread only."""
from .observers import SKETCH


def constraints(doc):
    out = []
    for obj in doc.Objects:
        if obj.TypeId != SKETCH:
            continue
        for i, c in enumerate(obj.Constraints):
            out.append({"id": "%s.%d" % (obj.Name, i), "type": c.Type,
                        "entity_ids": [obj.Name], "value": c.Value})
    return out


def solver(doc):
    sketches = [o for o in doc.Objects if o.TypeId == SKETCH]
    if not sketches:
        return {"fully_constrained": None, "dof": None, "messages": []}
    return {"fully_constrained": all(bool(s.FullyConstrained) for s in sketches),
            "dof": None, "messages": ["%s solve=%d" % (s.Name, s.solve()) for s in sketches]}


def document(doc):
    return {"name": doc.Name,
            "entities": [{"id": o.Name, "type": o.TypeId, "properties": {}} for o in doc.Objects],
            "constraints": constraints(doc),
            "solver": solver(doc)}
