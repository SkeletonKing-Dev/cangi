import os
import time

_running = {}


def start(host=None, port=None):
    if _running:
        return
    import FreeCAD
    import FreeCADGui as Gui
    from .client import Client
    from .hud import Hud
    from .observers import DocObserver, SelObserver, context
    from .qt import QtCore

    class Bridge(QtCore.QObject):
        frame = QtCore.Signal(object)

    host = host or os.environ.get("CANGI_HOST", "127.0.0.1")
    port = int(port or os.environ.get("CANGI_PORT", "8765"))

    hud = Hud(Gui.getMainWindow())
    bridge = Bridge()
    bridge.frame.connect(hud.apply)
    client = Client("freecad", host, port, on_frame=lambda f: bridge.frame.emit(f.get("steps", [])))

    def emit(kind, entity_id, entity_type, props=None):
        client.send({"ts": time.time_ns(), "kind": kind, "id": entity_id,
                     "type": entity_type, "props": props or {}, "cmd": context()})

    doc_obs = DocObserver(emit, on_activate=hud.rerender)
    sel_obs = SelObserver(emit)
    FreeCAD.addDocumentObserver(doc_obs)
    Gui.Selection.addObserver(sel_obs)
    client.start()
    _running.update(client=client, hud=hud, bridge=bridge, doc_obs=doc_obs, sel_obs=sel_obs)


def stop():
    if not _running:
        return
    import FreeCAD
    import FreeCADGui as Gui

    FreeCAD.removeDocumentObserver(_running["doc_obs"])
    Gui.Selection.removeObserver(_running["sel_obs"])
    _running["client"].stop()
    _running["hud"].clear()
    _running.clear()
