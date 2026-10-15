# cangi

Telemetry from CAD applications into one shared event schema, and walkthrough overlays drawn back
inside the CAD application.

Supported: FreeCAD, AutoCAD (2025+), QCAD (3.30+).

## How it works

    CAD plugin  --events-->  cangi (bus, diagnoser, walkthrough)  --overlay frames-->  CAD plugin

- Each plugin is thin. It reports raw events and draws whatever overlay frame it is sent.
- The Python side normalizes events, decides what to show, and sends the full list of active steps.
- Overlays use each application's own facilities, not a separate window, so they stay on top and
  follow the application.
- FreeCAD and AutoCAD talk to `cangi run` over TCP (127.0.0.1:8765). QCAD uses two files.

| | events out | overlay in | overlay drawn with |
|---|---|---|---|
| FreeCAD | TCP | TCP | Coin3D markers in the 3D view, toolbar button style, dock panel |
| AutoCAD | TCP | TCP | transient graphics in the drawing, palette panel |
| QCAD | JSONL file | JSON file | dock panel |

Wire format: `src/cangi/protocol.py`.

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/). The core has no runtime dependencies.

    uv sync
    uv run pytest
    uv run cangi run --demo --echo

`--demo` shows a fixed overlay on every object change, so you can check a plugin end to end.
Without it the overlay stays empty until a real diagnoser is plugged in (see below).

Options for `cangi run`: `--host`, `--port`, `--qcad-in`, `--qcad-out`, `--guide`, `--demo`, `--echo`, `--log-level`.

## FreeCAD

Copy or symlink `plugins/freecad/Cangi` into the FreeCAD user Mod directory, then restart FreeCAD.

    # Linux
    mkdir -p ~/.local/share/FreeCAD/v1-1/Mod/
    ln -s "$PWD/plugins/freecad/Cangi" ~/.local/share/FreeCAD/v1-1/Mod/Cangi

    # Mac
    ln -s "$PWD/plugins/freecad/Cangi" "$HOME/Library/Application Support/FreeCAD/Mod/Cangi"

Note: you can find the exact path by typing `App.getUserAppDataDir()` in the FreeCAD Python console.

The plugin starts with the GUI. It reads `CANGI_HOST` and `CANGI_PORT` (default 127.0.0.1:8765).
Set `CANGI_AUTOSTART=0` to start it manually from the Python console:

    import cangi_freecad
    cangi_freecad.start()
    cangi_freecad.stop()

The plugin uses only the standard library and FreeCAD's own Qt and pivy. It does not need the cangi package installed in FreeCAD.

## Guide (LLM)

Temporary stand-in for the analysis engine. The user asks in plain language, the model returns a
step-by-step plan, and cangi walks the user through it inside FreeCAD.

1. Get an API key. The defaults target Groq's OpenAI-compatible endpoint with `openai/gpt-oss-20b`.
   Any OpenAI-compatible service works by changing the variables below.
2. Copy `.env.example` to `.env` and fill it in:

       CANGI_LLM_API_KEY=...
       CANGI_LLM_BASE_URL=https://api.groq.com/openai/v1
       CANGI_LLM_MODEL=openai/gpt-oss-20b

3. Start the server with the guide enabled:

       uv run --env-file .env cangi run --guide

4. In FreeCAD open the "Cangi" dock on the right, type a request such as `help me model a cube`
   and press Enter.

Each step shows:

- an instruction and "Step n/m" in the dock
- a yellow outline on the toolbar button to use (only when that button is on screen, so switch to
  the right workbench first)
- a red circle in the sketch where to work, drawn in sketch coordinates through the sketch placement
- Back, Next and Stop buttons. A step also advances by itself when the model's expected event
  happens (for example a sketch is created). Wrong or missing expectations never block Next.

Plans are validated before use. Tool ids outside `src/cangi/guide/catalog.py` and malformed regions
are dropped, and a reply that is not valid JSON is retried once. Errors such as a bad key or a rate
limit are shown in the dock.

## AutoCAD

    cd plugins/autocad
    dotnet build -p:AutoCadDir="C:\Program Files\Autodesk\AutoCAD 2025"

Start `cangi run`, then in AutoCAD run `NETLOAD` and select `bin/Debug/net8.0-windows/Cangi.AutoCad.dll`.
`CANGI_HOST` and `CANGI_PORT` are honoured.

## QCAD

1. Optionally edit `EVENTS_PATH` and `FRAMES_PATH` at the top of `plugins/qcad/telemetry.js`.
2. Run `uv run cangi run --qcad-in /tmp/cangi_qcad.jsonl --qcad-out /tmp/cangi_qcad_overlay.json`.
3. In QCAD run the script (Misc > Development > Run Script).

## Plugging in a diagnoser

`Pipeline` takes a `diagnoser(event) -> Diagnosis | None`. `cangi.demo.demo_diagnoser` is a stand-in.

    from cangi.app import Pipeline
    pipeline = Pipeline(diagnoser=my_diagnoser)
    pipeline.start()

Step kinds a diagnosis can produce:

| kind | payload | drawn as |
|---|---|---|
| highlight | tool (command id), subtle | toolbar button highlight (FreeCAD), panel line elsewhere |
| arrow | world [x, y, z], text | marker and label at the model position |
| region | space (sketch or world), center, radius, text | circle with a label (FreeCAD only) |
| panel | lines | text panel |

## Layout

    src/cangi/
      schema.py, normalize.py    shared event schema, raw event to schema
      bus.py                     bounded queue, worker thread, latency stats
      hub.py                     TCP endpoint: events in, frames out
      files.py                   JSONL tail and atomic frame file (QCAD)
      walkthrough.py             steps, expiry, diagnosis rules
      presenter.py, protocol.py  steps to overlay frames
      app.py, demo.py, cli.py    pipeline wiring, demo diagnoser, `cangi` command
      bench.py                   `cangi bench`
      guide/                     temporary LLM guide, delete when the engine replaces it
        llm.py                   OpenAI-compatible client, config from environment
        prompts.py, catalog.py   system prompt, toolbar command ids the model may use
        plan.py                  parse and validate the model reply
        session.py               position in a plan, steps for the overlay
        context.py               what is open in the CAD application, for the prompt
        service.py               ask, navigation, stale-result handling
    plugins/
      freecad/Cangi/             FreeCAD Mod: client, observers, plan, scene, toolbar, panel, hud
      autocad/                   C# project
      qcad/telemetry.js
    tests/
      unit/                      no sockets or threads beyond the bus
      integration/               hub, pipeline, plugin client, LLM client against a local fake endpoint
      fixtures/                  sample plugin output per platform

## Tests

    uv run pytest                      all
    uv run pytest tests/unit           fast
    uv run pytest -m integration       sockets and files

The tests never call a real model. The FreeCAD HUD (Coin3D, Qt) and the AutoCAD and QCAD plugins
are not covered by automated tests.
They need the host application. Plugin output is checked against the core normalizer using the
fixtures.

## Known limits

- The guide's ask box and region circles exist in FreeCAD only. AutoCAD and QCAD show the
  instruction text but cannot ask yet.
- Model plans can be wrong, for example a hallucinated coordinate or a skipped step. Back and Next
  always work.
- QCAD draws no markers in the drawing, only the panel.
- AutoCAD markers do not update on pan or zoom until the next frame. The tool highlight is shown as
  panel text.
- The frame file tail cannot detect a truncation to the same or a larger size.
