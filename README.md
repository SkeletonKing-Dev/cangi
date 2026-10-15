# CANGI EXP-1

Telemetry, shared schema and HUD overlay.

## Setup

    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install PySide6              # only needed for the overlay and demo

Python 3.11+. The core (schema, bus, normalizer, walkthrough) has no dependencies.

## Check the core

    python -m unittest discover -s tests -t .
    python bench.py

## Overlay demo

    python demo.py

Every 3 seconds a synthetic event shows a yellow rectangle on screen for 8 seconds.
Clicks pass through it. Render latency is printed every 5 seconds.

## Event receiver (AutoCAD and QCAD)

    python run_ingest.py

Listens on TCP 127.0.0.1:8765 and tails /tmp/cangi_qcad.jsonl. Prints each normalized event as JSON.
Start this before the CAD plugins. Change the QCAD file with `--qcad-file`.

## FreeCAD

In FreeCAD's Python console (View > Panels > Python console):

```    
import sys
sys.path.append("~/Code/FYP/APEX-GUI/cangi_exp1/")
from cangi.bus import EventBus
from cangi.freecad_adapter import FreeCADAdapter
bus = EventBus()
bus.subscribe(lambda e: print(e.to_json()))
bus.start()
adapter = FreeCADAdapter(bus)
adapter.connect()
```

Create a sketch, add geometry and constraints, and events print in the console.
Stop with `adapter.disconnect()`.

## AutoCAD (2025+)

1. Create a C# class library targeting net8.0-windows.
2. Add `plugins/autocad/Telemetry.cs`.
3. Reference AcMgd.dll, AcDbMgd.dll and AcCoreMgd.dll from the AutoCAD install folder, with Copy Local set to false.
4. Build, run `run_ingest.py`, then run `NETLOAD` in AutoCAD and select the built dll.

Draw, move or erase objects and events appear in the receiver.

## QCAD (3.30+)

1. Edit `OUT_PATH` at the top of `plugins/qcad/telemetry.js` if not on Linux or macOS (use a path the receiver can read).
2. Run `run_ingest.py --qcad-file <same path>`.
3. In QCAD, run the script (Misc > Development > Run Script).

Edit entities and events appear in the receiver.

## Layout

    cangi/schema.py            shared schema
    cangi/adapter.py           adapter interface
    cangi/normalize.py         raw event to shared schema
    cangi/bus.py               queue, worker thread, latency stats
    cangi/ingest.py            TCP and file ingest
    cangi/freecad_adapter.py   FreeCAD observers
    cangi/walkthrough.py       step queue and controller
    cangi/overlay.py           Qt overlay
    plugins/                   AutoCAD (C#) and QCAD (JS)
