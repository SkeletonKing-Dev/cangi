// QCAD telemetry. Appends one JSON line per changed object to OUT_PATH.
var OUT_PATH = "/tmp/cangi_qcad.jsonl";

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
    var f = new QFile(OUT_PATH);
    if (!f.open(new QIODevice.OpenMode(QIODevice.Append | QIODevice.Text))) return;
    var s = new QTextStream(f);
    s.writeString(JSON.stringify(obj) + "\n");
    s.flush();
    f.close();
}

var CangiListener = new RTransactionListenerAdapter();
var appWin = EAction.getMainWindow();
appWin.addTransactionListener(CangiListener);

CangiListener.transactionUpdated.connect(function (document, changes) {
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
