import os
import sys

_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else None
if _here and _here not in sys.path:
    sys.path.append(_here)


def _autostart():
    import cangi_freecad
    cangi_freecad.start()


if os.environ.get("CANGI_AUTOSTART", "1") != "0":
    from PySide import QtCore
    QtCore.QTimer.singleShot(0, _autostart)
