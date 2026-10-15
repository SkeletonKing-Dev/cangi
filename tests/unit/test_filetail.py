import json
import os

from cangi.bus import EventBus
from cangi.files import FileSink, FileTailIngest


def make(tmp_path):
    bus = EventBus()
    bus.publish = lambda platform, raw: published.append((platform, raw))
    published = []
    path = tmp_path / "in.jsonl"
    return FileTailIngest(bus, "qcad", str(path)), path, published


def test_starts_at_end_of_existing_file(tmp_path):
    tail, path, published = make(tmp_path)
    path.write_text('{"old": 1}\n')
    tail.poll_once()
    with open(path, "a") as f:
        f.write('{"new": 1}\n')
    assert tail.poll_once() == 1
    assert published == [("qcad", {"new": 1})]


def test_waits_for_file(tmp_path):
    tail, path, published = make(tmp_path)
    assert tail.poll_once() == 0
    path.write_text("")
    tail.poll_once()
    with open(path, "a") as f:
        f.write('{"a": 1}\n')
    assert tail.poll_once() == 1


def test_partial_line_is_not_lost(tmp_path):
    tail, path, published = make(tmp_path)
    path.write_text("")
    tail.poll_once()
    with open(path, "a") as f:
        f.write('{"a": ')
    assert tail.poll_once() == 0
    with open(path, "a") as f:
        f.write('1}\n{"b": 2}\n')
    assert tail.poll_once() == 2
    assert [r for _, r in published] == [{"a": 1}, {"b": 2}]


def test_bad_line_is_skipped(tmp_path):
    tail, path, published = make(tmp_path)
    path.write_text("")
    tail.poll_once()
    with open(path, "a") as f:
        f.write('not json\n{"ok": 1}\n')
    assert tail.poll_once() == 1


def test_truncation_restarts_from_beginning(tmp_path):
    tail, path, published = make(tmp_path)
    path.write_text("")
    tail.poll_once()
    with open(path, "a") as f:
        f.write('{"a": 1}\n')
    tail.poll_once()
    path.write_text('{"b":2}\n')
    assert tail.poll_once() == 1
    assert published[-1][1] == {"b": 2}


def test_file_sink_replaces_atomically(tmp_path):
    p = tmp_path / "frame.json"
    sink = FileSink(str(p))
    sink.send({"seq": 1})
    sink.send({"seq": 2})
    assert json.loads(p.read_text()) == {"seq": 2}
    assert os.listdir(tmp_path) == ["frame.json"]
