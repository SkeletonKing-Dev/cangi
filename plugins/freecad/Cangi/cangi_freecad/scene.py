"""Coin3D overlay drawn inside the active 3D view."""
import logging

from .observers import SKETCH
from .plan import circle_points

log = logging.getLogger("cangi.scene")

COLOR = (0.9, 0.24, 0.24)
ROOT_NAME = "CangiHud"


def active_sketch():
    """The sketch being edited, else the most recent sketch in the active document."""
    import FreeCAD
    import FreeCADGui as Gui
    if Gui.ActiveDocument:
        vp = Gui.ActiveDocument.getInEdit()
        if vp is not None and vp.Object.TypeId == SKETCH:
            return vp.Object
    doc = FreeCAD.ActiveDocument
    sketches = [o for o in doc.Objects if o.TypeId == SKETCH] if doc else []
    return sketches[-1] if sketches else None


def resolve_regions(regions):
    """Regions to (world polyline, label position, text). Sketch coordinates go through the sketch placement."""
    import FreeCAD
    sketch = active_sketch() if any(r["space"] == "sketch" for r in regions) else None
    out = []
    for r in regions:
        pts = circle_points(r["center"], r["radius"])
        if r["space"] == "sketch" and sketch is not None:
            placement = getattr(sketch, "getGlobalPlacement", lambda: sketch.Placement)()
            vecs = [placement.multVec(FreeCAD.Vector(*p)) for p in pts]
            pts = [(v.x, v.y, v.z) for v in vecs]
        out.append((pts, pts[len(pts) // 4], r["text"]))
    return out


def build(markers, rings):
    from pivy import coin
    root = coin.SoSeparator()
    root.setName(ROOT_NAME)
    depth = coin.SoDepthBuffer()
    depth.test.setValue(False)
    root.addChild(depth)
    light = coin.SoLightModel()
    light.model.setValue(coin.SoLightModel.BASE_COLOR)
    root.addChild(light)
    mat = coin.SoMaterial()
    mat.diffuseColor.setValue(*COLOR)
    root.addChild(mat)
    style = coin.SoDrawStyle()
    style.lineWidth.setValue(3)
    root.addChild(style)
    font = coin.SoFont()
    font.size.setValue(14)
    root.addChild(font)
    for pts, label_at, text in rings:
        sep = coin.SoSeparator()
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, len(pts), pts)
        line = coin.SoLineSet()
        line.numVertices.setValue(len(pts))
        sep.addChild(coords)
        sep.addChild(line)
        if text:
            sep.addChild(_label(coin, label_at, text))
        root.addChild(sep)
    for (x, y, z), text in markers:
        sep = coin.SoSeparator()
        pt = coin.SoCoordinate3()
        pt.point.setValue(x, y, z)
        ring = coin.SoMarkerSet()
        ring.markerIndex.setValue(coin.SoMarkerSet.CIRCLE_LINE_9_9)
        ring.numPoints.setValue(1)
        sep.addChild(pt)
        sep.addChild(ring)
        sep.addChild(_label(coin, (x, y, z), text))
        root.addChild(sep)
    return root


def _label(coin, at, text):
    sep = coin.SoSeparator()
    move = coin.SoTranslation()
    move.translation.setValue(*at)
    label = coin.SoText2()
    label.string.setValue("    " + text)
    sep.addChild(move)
    sep.addChild(label)
    return sep


class SceneOverlay:
    def __init__(self):
        self._root = None
        self._graph = None

    def show(self, markers, regions):
        self.clear()
        if not markers and not regions:
            return
        try:
            import FreeCADGui as Gui
            graph = Gui.ActiveDocument.ActiveView.getSceneGraph()
            root = build(markers, resolve_regions(regions))
            graph.addChild(root)
        except Exception:
            log.exception("scene overlay failed")
            return
        self._root, self._graph = root, graph

    def clear(self):
        if self._root is not None:
            try:
                self._graph.removeChild(self._root)
            except Exception:
                pass
        self._root = self._graph = None
