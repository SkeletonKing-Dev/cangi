import sys
import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from cangi.bus import EventBus
from cangi.overlay import Overlay
from cangi.walkthrough import Diagnosis, WalkthroughController


class Bridge(QObject):
    changed = Signal()


def main():
    app = QApplication(sys.argv)
    screen = app.primaryScreen().geometry()
    overlay = Overlay((screen.x(), screen.y(), screen.width(), screen.height()))
    overlay.tool_rects["test"] = (200, 200, 300, 150)
    ctrl = WalkthroughController()
    bridge = Bridge()
    bridge.changed.connect(lambda: overlay.set_steps(ctrl.active()))

    bus = EventBus()

    def on_event(ev):
        ctrl.handle_diagnosis(Diagnosis(
            next_tool="test", intention_confidence=1.0, t0_ns=ev.timestamp_ns))
        bridge.changed.emit()

    bus.subscribe(on_event)
    bus.start()

    tick = QTimer()
    tick.timeout.connect(lambda: ctrl.tick() and bridge.changed.emit())
    tick.start(100)

    fire = QTimer()
    fire.timeout.connect(lambda: bus.publish("freecad", {
        "ts": time.time_ns(), "kind": "slotChangedObject", "id": "Sketch",
        "type": "Sketcher::SketchObject"}))
    fire.start(3000)

    report = QTimer()
    report.timeout.connect(lambda: print("latency ms:", overlay.latencies_ms[-5:]))
    report.start(5000)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
