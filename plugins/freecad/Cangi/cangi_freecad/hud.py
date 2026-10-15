import logging

log = logging.getLogger("cangi.hud")

MARKER_COLOR = (0.9, 0.24, 0.24)
STYLE_STRONG = "border: 2px solid #ffc800; background: rgba(255, 200, 0, 60);"
STYLE_SUBTLE = "border: 1px solid rgba(255, 200, 0, 140);"
ROOT_NAME = "CangiHud"


def plan(steps):
    """Reduce wire steps to what the HUD draws. Pure function."""
    tool = None
    markers = []
    lines = []
    for s in sorted(steps, key=lambda s: -s.get("priority", 0)):
        p = s.get("payload", {})
        if s["kind"] == "highlight" and tool is None and p.get("tool"):
            tool = (p["tool"], bool(p.get("subtle")))
        elif s["kind"] == "arrow" and p.get("world"):
            markers.append((tuple(p["world"]), p.get("text", "")))
        elif s["kind"] == "panel":
            lines.extend(p.get("lines", []))
    return {"tool": tool, "markers": markers, "lines": lines}


def build_scene(markers):
    """Coin3D subgraph: a constant-size ring and a screen-aligned label per marker."""
    from pivy import coin
    root = coin.SoSeparator()
    root.setName(ROOT_NAME)
    depth = coin.SoDepthBuffer()
    depth.test.setValue(False)
    root.addChild(depth)
    mat = coin.SoMaterial()
    mat.diffuseColor.setValue(*MARKER_COLOR)
    root.addChild(mat)
    font = coin.SoFont()
    font.size.setValue(14)
    root.addChild(font)
    for (x, y, z), text in markers:
        sep = coin.SoSeparator()
        pt = coin.SoCoordinate3()
        pt.point.setValue(x, y, z)
        ring = coin.SoMarkerSet()
        ring.markerIndex.setValue(coin.SoMarkerSet.CIRCLE_LINE_9_9)
        ring.numPoints.setValue(1)
        move = coin.SoTranslation()
        move.translation.setValue(x, y, z)
        label = coin.SoText2()
        label.string.setValue("    " + text)
        for node in (pt, ring, move, label):
            sep.addChild(node)
        root.addChild(sep)
    return root


class Hud:
    """In-application overlay: Coin3D markers in the active 3D view, toolbar button highlight, dock panel."""

    def __init__(self, main_window):
        from .qt import QtCore, QtWidgets
        self._qt = QtWidgets
        self._core = QtCore
        self.main_window = main_window
        self._plan = plan([])
        self._scene = None
        self._scene_graph = None
        self._styled = {}
        self._label = QtWidgets.QLabel()
        self._label.setWordWrap(True)
        self._label.setMargin(8)
        self._dock = QtWidgets.QDockWidget("Cangi", main_window)
        self._dock.setObjectName("CangiPanel")
        self._dock.setWidget(self._label)
        main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._dock)
        self._dock.hide()

    def apply(self, steps):
        self._plan = plan(steps)
        self.rerender()

    def rerender(self):
        self._render_scene()
        self._render_tool()
        self._render_panel()

    def clear(self):
        self.apply([])

    def _render_scene(self):
        self._remove_scene()
        markers = self._plan["markers"]
        if not markers:
            return
        try:
            import FreeCADGui as Gui
            view = Gui.ActiveDocument.ActiveView
            graph = view.getSceneGraph()
            root = build_scene(markers)
            graph.addChild(root)
        except Exception:
            log.exception("scene overlay failed")
            return
        self._scene, self._scene_graph = root, graph

    def _remove_scene(self):
        if self._scene is not None:
            try:
                self._scene_graph.removeChild(self._scene)
            except Exception:
                pass
        self._scene = self._scene_graph = None

    def _buttons(self, command):
        out = []
        for b in self.main_window.findChildren(self._qt.QToolButton):
            action = b.defaultAction()
            if action is not None and action.objectName() == command:
                out.append(b)
        return out

    def _render_tool(self):
        for button, old in self._styled.items():
            try:
                button.setStyleSheet(old)
            except RuntimeError:
                pass
        self._styled = {}
        if not self._plan["tool"]:
            return
        command, subtle = self._plan["tool"]
        for button in self._buttons(command):
            self._styled[button] = button.styleSheet()
            button.setStyleSheet(STYLE_SUBTLE if subtle else STYLE_STRONG)

    def _render_panel(self):
        lines = self._plan["lines"]
        if lines:
            self._label.setText("\n".join(lines))
            self._dock.show()
        else:
            self._dock.hide()
