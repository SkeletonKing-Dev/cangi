from .plan import status_text
from .qt import QtWidgets


class GuidePanel(QtWidgets.QWidget):
    """Ask box, status line, current instruction and navigation buttons."""

    def __init__(self, on_action):
        super().__init__()
        self._on_action = on_action
        self._input = QtWidgets.QLineEdit()
        self._input.setPlaceholderText("Ask for help, e.g. model a cube")
        ask = QtWidgets.QPushButton("Ask")
        self._status = QtWidgets.QLabel()
        self._text = QtWidgets.QLabel()
        for label in (self._status, self._text):
            label.setWordWrap(True)
        self._back = QtWidgets.QPushButton("Back")
        self._next = QtWidgets.QPushButton("Next")
        self._stop = QtWidgets.QPushButton("Stop")

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self._input)
        top.addWidget(ask)
        nav = QtWidgets.QHBoxLayout()
        for b in (self._back, self._next, self._stop):
            nav.addWidget(b)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self._status)
        layout.addWidget(self._text)
        layout.addLayout(nav)
        layout.addStretch(1)

        self._input.returnPressed.connect(self._submit)
        ask.clicked.connect(lambda *_: self._submit())
        self._back.clicked.connect(lambda *_: on_action("back", ""))
        self._next.clicked.connect(lambda *_: on_action("next", ""))
        self._stop.clicked.connect(lambda *_: on_action("stop", ""))
        self.show_content([], {})

    def _submit(self):
        text = self._input.text().strip()
        if text:
            self._on_action("ask", text)

    def show_content(self, lines, status):
        self._text.setText("\n".join(lines))
        self._status.setText(status_text(status))
        for b in (self._back, self._next, self._stop):
            b.setEnabled(bool(lines))
