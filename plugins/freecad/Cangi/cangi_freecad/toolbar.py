from .qt import QtWidgets

STYLE_STRONG = "border: 2px solid #ffc800; background: rgba(255, 200, 0, 60);"
STYLE_SUBTLE = "border: 1px solid rgba(255, 200, 0, 140);"


class ToolbarHighlight:
    """Outlines the toolbar buttons of a FreeCAD command and restores them afterwards."""

    def __init__(self, main_window):
        self.main_window = main_window
        self._styled = {}

    def set(self, tool):
        """tool is (command name, subtle) or None."""
        self._restore()
        if not tool:
            return
        command, subtle = tool
        for button in self.main_window.findChildren(QtWidgets.QToolButton):
            action = button.defaultAction()
            if action is not None and action.objectName() == command:
                self._styled[button] = button.styleSheet()
                button.setStyleSheet(STYLE_SUBTLE if subtle else STYLE_STRONG)

    def _restore(self):
        for button, old in self._styled.items():
            try:
                button.setStyleSheet(old)
            except RuntimeError:
                pass
        self._styled = {}
