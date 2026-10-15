from cangi.presenter import OverlayPresenter
from cangi.walkthrough import Diagnosis, WalkthroughController


class Recorder:
    def __init__(self):
        self.frames = []

    def send(self, frame):
        self.frames.append(frame)


def test_refresh_sends_full_state_with_increasing_seq():
    c = WalkthroughController()
    a, b = Recorder(), Recorder()
    p = OverlayPresenter(c, [a, b])
    p.refresh()
    c.handle_diagnosis(Diagnosis(next_tool="x", intention_confidence=1.0))
    p.refresh()
    assert [f["seq"] for f in a.frames] == [1, 2]
    assert a.frames == b.frames
    assert a.frames[0]["steps"] == []
    assert a.frames[1]["steps"][0]["id"] == "tool"


def test_status_is_part_of_every_frame_until_replaced():
    c = WalkthroughController()
    r = Recorder()
    p = OverlayPresenter(c, [r])
    p.refresh({"state": "thinking", "text": "x"})
    p.refresh()
    assert r.frames[1]["status"] == {"state": "thinking", "text": "x"}
    p.refresh({"state": "idle", "text": ""})
    assert r.frames[2]["status"]["state"] == "idle"
