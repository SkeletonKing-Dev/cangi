import pytest

from tests.helpers import LineSocket, raw


@pytest.fixture
def make_raw():
    return raw


@pytest.fixture
def connect():
    opened = []

    def _connect(address):
        c = LineSocket(address)
        opened.append(c)
        return c

    yield _connect
    for c in opened:
        c.close()
