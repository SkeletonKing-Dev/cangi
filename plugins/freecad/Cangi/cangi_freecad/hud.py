from .panel import GuidePanel
from .plan import IDLE, plan
from .qt import QtCore, QtWidgets
from .scene import SceneOverlay
from .toolbar import ToolbarHighlight


class Hud:
    """Applies overlay frames: scene graphics, toolbar highlight and the guide dock."""

    def __init__(self, main_window, on_action):
        self.main_window = main_window
        self.panel = GuidePanel(on_action)
        self.scene = SceneOverlay()
        self.toolbar = ToolbarHighlight(main_window)
        self.dock = QtWidgets.QDockWidget("Cangi", main_window)
        self.dock.setObjectName("CangiPanel")
        self.dock.setWidget(self.panel)
        main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dock)
        self._plan = plan([])
        self._status = IDLE

    def apply(self, frame):
        self._plan = plan(frame.get("steps", []))
        self._status = frame.get("status") or IDLE
        self.rerender()

    def rerender(self):
        self.scene.show(self._plan["markers"], self._plan["regions"])
        self.toolbar.set(self._plan["tool"])
        self.panel.show_content(self._plan["lines"], self._status)

    def close(self):
        self.apply({})
        self.main_window.removeDockWidget(self.dock)
        self.dock.deleteLater()
