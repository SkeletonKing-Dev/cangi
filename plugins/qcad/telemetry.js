// QCAD plugin. Emits JSONL events to cangi hub over TCP; receives overlay frames as JSON lines.
var HOST = "127.0.0.1";
var PORT = 8765;
var PLATFORM = "qcad";
var RECONNECT_MS = 1000;
var MAX_PENDING = 1000;
var DEBUG = false;            // set true for per-event logging

function qd(msg) { if (DEBUG) qDebug(msg); }

function cangiType(entity) {
    if (isNull(entity)) return "";
    var t = entity.getType();
    if (t === RS.EntityLine) return "line";
    if (t === RS.EntityCircle) return "circle";
    if (t === RS.EntityArc) return "arc";
    if (t === RS.EntityPoint) return "point";
    return "entity";
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
    try {
        qDebug("cangi: IIFE start");
        if (qApp.property("cangiInstalled") === true) { qDebug("cangi: guard, abort"); return; }
        qApp.setProperty("cangiInstalled", true);

        var appWin = EAction.getMainWindow();

        // --- dock panel for overlay frames ---
        var label = new QLabel();
        label.wordWrap = true;
        label.margin = 8;
        var dock = new QDockWidget("Cangi", appWin);
        dock.objectName = "CangiPanel";
        dock.setWidget(label);
        appWin.addDockWidget(Qt.RightDockWidgetArea, dock);
        dock.hide();

        // --- TCP transport to the cangi hub ---
        // QCAD's QIODevice.write only accepts QByteArray (or a single char),
        // so every string must be wrapped before hitting the socket.
        var socket = new QTcpSocket(appWin);
        var connected = false;
        var pending = [];       // queued event lines while disconnected
        var rxbuf = "";         // partial-line accumulator
        var lastSeq = -1;

        function writeBytes(s) {
            socket.write(new QByteArray(s));
        }

        function send(obj) {
            obj.platform = PLATFORM;   // hub does raw.pop("platform")
            var line = JSON.stringify(obj) + "\n";
            if (!connected) {
                if (pending.length >= MAX_PENDING) pending.shift();
                pending.push(line);
                return;
            }
            try {
                writeBytes(line);
                socket.flush();
                qd("cangi: wrote " + line.length + " chars");
            } catch (e) {
                qDebug("cangi: write threw " + e);
            }
        }

        function handleFrame(frame) {
            if (!frame || !frame.steps) return;
            if (typeof frame.seq !== "undefined") {
                if (frame.seq === lastSeq) return;
                lastSeq = frame.seq;
            }
            var lines = cangiFrameLines(frame);
            label.text = lines.join("\n");
            if (lines.length > 0) dock.show(); else dock.hide();
        }

        socket.stateChanged.connect(function (st) { qDebug("cangi: socket state=" + st); });
        try { socket.errorOccurred.connect(function (e) { qDebug("cangi: socket error=" + e); }); } catch (x) {}
        try { socket.error.connect(function (e) { qDebug("cangi: socket error=" + e); }); } catch (x) {}

        socket.connected.connect(function () {
            qDebug("cangi: CONNECTED, draining " + pending.length + " pending");
            connected = true;
            var items = pending;
            pending = [];
            for (var i = 0; i < items.length; i++) writeBytes(items[i]);
            socket.flush();
        });

        socket.disconnected.connect(function () {
            qDebug("cangi: DISCONNECTED");
            connected = false;
        });

        socket.readyRead.connect(function () {
            var chunk = socket.readAll();   // QByteArray
            rxbuf += String(chunk);         // yields raw bytes in QCAD 3.33
            var idx;
            while ((idx = rxbuf.indexOf("\n")) >= 0) {
                var line = rxbuf.substring(0, idx);
                rxbuf = rxbuf.substring(idx + 1);
                if (line.length === 0) continue;
                var frame;
                try { frame = JSON.parse(line); } catch (e) { continue; }
                handleFrame(frame);
            }
        });

        function tryConnect() {
            if (connected) return;
            if (String(socket.state()) !== "UnconnectedState") return;
            qDebug("cangi: connectToHost " + HOST + ":" + PORT);
            socket.connectToHost(HOST, PORT);
        }

        var reconnect = new QTimer(appWin);
        reconnect.interval = RECONNECT_MS;
        reconnect.timeout.connect(tryConnect);
        reconnect.start();
        tryConnect();

        // --- transaction events -> hub ---
        var listener = new RTransactionListenerAdapter();
        appWin.addTransactionListener(listener);
        listener.transactionUpdated.connect(function (document, changes) {
            qd("cangi: transactionUpdated fired");
            if (isNull(document) || isNull(changes)) {
                qd("cangi: null changes, skipping");
                return;
            }
            var ts = new Date().getTime() * 1000000;
            var ids = changes.getAffectedObjects();
            if (isNull(ids) || ids.length === 0) return;

            for (var i = 0; i < ids.length; i++) {
                var props = {};
                var pcs = changes.getPropertyChanges(ids[i]);   // per-object overload
                if (pcs) {
                    for (var j = 0; j < pcs.length; j++) {
                        var pc = pcs[j];
                        var name = pc.getPropertyTypeId().getPropertyTitle();
                        props[name] = {
                            old: String(pc.getOldValue()),
                            "new": String(pc.getNewValue())
                        };
                    }
                }
                send({
                    ts: ts,
                    kind: "transactionUpdated",
                    id: String(ids[i]),
                    type: cangiType(document.queryEntityDirect(ids[i])),
                    props: props,
                    cmd: ""
                });
            }
        });

        qDebug("cangi: install complete");
    } catch (e) {
        qDebug("cangi: FATAL " + e + "\n" + (e.stack || ""));
    }
})();