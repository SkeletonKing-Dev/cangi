// QCAD plugin. Events go out through EVENTS_PATH (JSONL); overlay frames come in through FRAMES_PATH (JSON).
var EVENTS_PATH = "/tmp/cangi_qcad.jsonl";
var FRAMES_PATH = "/tmp/cangi_qcad_overlay.json";
var POLL_MS = 100;

function cangiType(entity) {
    if (isNull(entity)) return "";
    var t = entity.getType();
    if (t === RS.EntityLine) return "line";
    if (t === RS.EntityCircle) return "circle";
    if (t === RS.EntityArc) return "arc";
    if (t === RS.EntityPoint) return "point";
    return "entity";
}

function cangiWrite(obj) {
    var f = new QFile(EVENTS_PATH);
    if (!f.open(new QIODevice.OpenMode(QIODevice.Append | QIODevice.Text))) return;
    var s = new QTextStream(f);
    s.writeString(JSON.stringify(obj) + "\n");
    s.flush();
    f.close();
}

function cangiReadFrame() {
    var f = new QFile(FRAMES_PATH);
    if (!f.exists() || !f.open(new QIODevice.OpenMode(QIODevice.ReadOnly | QIODevice.Text))) return null;
    var text = new QTextStream(f).readAll();
    f.close();
    try {
        return JSON.parse(text);
    } catch (e) {
        return null;
    }
}

function cangiFrameLines(frame) {
    var steps = frame.steps.slice().sort(function (a, b) { return b.priority - a.priority; });
    var lines = [];
    for (var i = 0; i < steps.length; i++) {
        var p = steps[i].payload;
        if (steps[i].kind === "highlight" && p.tool) {
            lines.push("Next tool: " + p.tool);
        } else if (steps[i].kind === "arrow") {
            lines.push(p.text + " (" + p.world[0] + ", " + p.world[1] + ")");
        } else if (steps[i].kind === "panel") {
            lines = lines.concat(p.lines);
        }
    }
    return lines;
}

(function () {
    if (qApp.property("cangiInstalled") === true) return;
    qApp.setProperty("cangiInstalled", true);

    var appWin = EAction.getMainWindow();

    var listener = new RTransactionListenerAdapter();
    appWin.addTransactionListener(listener);
    listener.transactionUpdated.connect(function (document, changes) {
        var ts = new Date().getTime() * 1000000;
        var ids = changes.getAffectedObjects();
        var list = changes.getPropertyChanges(ids);
        for (var i = 0; i < ids.length; i++) {
            var props = {};
            if (list && list[i]) {
                for (var j = 0; j < list[i].length; j++) {
                    var pc = list[i][j];
                    var name = pc.getPropertyTypeId().getPropertyTitle();
                    props[name] = { old: String(pc.getOldValue()), "new": String(pc.getNewValue()) };
                }
            }
            cangiWrite({
                ts: ts,
                kind: "transactionUpdated",
                id: String(ids[i]),
                type: cangiType(document.queryEntityDirect(ids[i])),
                props: props,
                cmd: ""
            });
        }
    });

    var label = new QLabel();
    label.wordWrap = true;
    label.margin = 8;
    var dock = new QDockWidget("Cangi", appWin);
    dock.objectName = "CangiPanel";
    dock.setWidget(label);
    appWin.addDockWidget(Qt.RightDockWidgetArea, dock);
    dock.hide();

    var lastSeq = -1;
    var timer = new QTimer(appWin);
    timer.interval = POLL_MS;
    timer.timeout.connect(function () {
        var frame = cangiReadFrame();
        if (frame === null || frame.seq === lastSeq) return;
        lastSeq = frame.seq;
        var lines = cangiFrameLines(frame);
        label.text = lines.join("\n");
        if (lines.length > 0) dock.show(); else dock.hide();
    });
    timer.start();
})();
