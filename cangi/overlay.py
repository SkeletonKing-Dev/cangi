import math
import time
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from .walkthrough import Step


class Overlay(QWidget):
    def __init__(self, geometry: Tuple[int, int, int, int],
                 mapper: Optional[Callable[[float, float, float], Tuple[float, float]]] = None,
                 tool_rects: Optional[dict] = None):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setGeometry(*geometry)
        self.mapper = mapper
        self.tool_rects = tool_rects or {}
        self.steps: List[Step] = []
        self.latencies_ms: List[float] = []
        self._timed = set()

    def set_steps(self, steps: List[Step]) -> None:
        self.steps = steps
        if steps:
            self.show()
            self.update()
        else:
            self.hide()

    def _local(self, x: float, y: float) -> QPointF:
        return QPointF(self.mapFromGlobal(QPoint(int(x), int(y))))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for s in self.steps:
            if s.kind == "highlight":
                self._highlight(p, s)
            elif s.kind == "arrow":
                self._arrow(p, s)
            elif s.kind == "panel":
                self._panel(p, s)
        p.end()
        now = time.time_ns()
        for s in self.steps:
            key = (s.id, s.t0_ns)
            if s.t0_ns and key not in self._timed:
                self._timed.add(key)
                self.latencies_ms.append((now - s.t0_ns) / 1e6)

    def _highlight(self, p, s):
        rect = s.payload.get("rect") or self.tool_rects.get(s.payload.get("tool"))
        if not rect:
            return
        alpha = 80 if s.payload.get("subtle") else 255
        p.setPen(QPen(QColor(255, 200, 0, alpha), 3))
        p.setBrush(QBrush(QColor(255, 200, 0, alpha // 5)))
        tl = self._local(rect[0], rect[1])
        p.drawRect(QRectF(tl.x(), tl.y(), rect[2], rect[3]))

    def _arrow(self, p, s):
        if not self.mapper:
            return
        sx, sy = self.mapper(*s.payload["world"])
        tip = self._local(sx, sy)
        tail = QPointF(tip.x() - 80, tip.y() - 60)
        ang = math.atan2(tip.y() - tail.y(), tip.x() - tail.x())
        head = QPolygonF([
            tip,
            QPointF(tip.x() - 14 * math.cos(ang - 0.4), tip.y() - 14 * math.sin(ang - 0.4)),
            QPointF(tip.x() - 14 * math.cos(ang + 0.4), tip.y() - 14 * math.sin(ang + 0.4)),
        ])
        p.setPen(QPen(QColor(230, 60, 60), 3))
        p.drawLine(tail, tip)
        p.setBrush(QBrush(QColor(230, 60, 60)))
        p.drawPolygon(head)
        text = s.payload.get("text", "")
        if text:
            box = QRectF(tail.x() - 160, tail.y() - 28, 220, 28)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(30, 30, 30, 220)))
            p.drawRoundedRect(box, 4, 4)
            p.setPen(QColor(255, 255, 255))
            p.drawText(box, Qt.AlignCenter, text)

    def _panel(self, p, s):
        lines = s.payload.get("lines", [])
        box = QRectF(self.width() - 320, 20, 300, 24 * len(lines) + 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(30, 30, 30, 200)))
        p.drawRoundedRect(box, 6, 6)
        p.setPen(QColor(255, 255, 255))
        for i, line in enumerate(lines):
            p.drawText(QRectF(box.x() + 10, box.y() + 8 + 24 * i, 280, 24), Qt.AlignVCenter, line)
