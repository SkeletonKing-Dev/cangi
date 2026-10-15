from .schema import EVENT_TYPES, PLATFORMS, Event

KIND_MAP = {
    "freecad": {
        "slotCreatedDocument": "document_created",
        "slotActivatedDocument": "document_activated",
        "slotDeletedDocument": "document_closed",
        "slotCreatedObject": "object_created",
        "slotChangedObject": "object_modified",
        "slotDeletedObject": "object_deleted",
        "selection": "selection_changed",
    },
    "autocad": {
        "DocumentCreated": "document_created",
        "DocumentActivated": "document_activated",
        "DocumentToBeDestroyed": "document_closed",
        "ObjectAppended": "object_created",
        "ObjectModified": "object_modified",
        "ObjectErased": "object_deleted",
        "CommandWillStart": "command_start",
        "CommandEnded": "command_end",
    },
    "qcad": {
        "transactionUpdated": "object_modified",
    },
}

TYPE_ALIASES = {
    "sketcher::sketchobject": "sketch",
    "sketch": "sketch",
    "part::feature": "solid",
    "document": "document",
}


def normalize_type(raw_type: str) -> str:
    t = (raw_type or "").strip().lower()
    if t in TYPE_ALIASES:
        return TYPE_ALIASES[t]
    if t.startswith("acdb"):
        t = t[4:]
    return t.split("::")[-1]


def normalize(platform: str, raw: dict) -> Event:
    if platform not in PLATFORMS:
        raise ValueError("unknown platform: %s" % platform)
    kind = raw.get("kind")
    event_type = KIND_MAP[platform].get(kind)
    if event_type is None:
        raise ValueError("unknown %s event kind: %s" % (platform, kind))
    if "ts" not in raw:
        raise ValueError("missing ts")
    return Event(
        timestamp_ns=int(raw["ts"]),
        platform=platform,
        event_type=event_type,
        entity_id=str(raw.get("id", "")),
        entity_type=normalize_type(raw.get("type", "")),
        properties=dict(raw.get("props") or {}),
        command_context=str(raw.get("cmd", "")),
    )
