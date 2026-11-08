"""The page's "Actualizar datos" button must not hammer the sources."""
import pytest

from informate.live import ThrottledRefresh


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def counting_fetch():
    calls = []

    def fetch():
        calls.append(1)
        return {"fetch_number": len(calls)}

    return fetch, calls


def test_first_request_fetches_from_the_sources():
    fetch, calls = counting_fetch()
    refresh = ThrottledRefresh(fetch, min_interval=60, clock=Clock())
    assert refresh() == {"fetch_number": 1}
    assert len(calls) == 1


def test_a_second_request_soon_after_reuses_the_last_result():
    fetch, calls = counting_fetch()
    clock = Clock()
    refresh = ThrottledRefresh(fetch, min_interval=60, clock=clock)
    refresh()
    clock.now += 59
    assert refresh() == {"fetch_number": 1}
    assert len(calls) == 1


def test_a_request_after_the_interval_fetches_again():
    fetch, calls = counting_fetch()
    clock = Clock()
    refresh = ThrottledRefresh(fetch, min_interval=60, clock=clock)
    refresh()
    clock.now += 61
    assert refresh() == {"fetch_number": 2}


def test_a_failed_fetch_is_reported_and_can_be_retried_at_once():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError("source is down")
        return {"ok": True}

    refresh = ThrottledRefresh(flaky, min_interval=60, clock=Clock())
    with pytest.raises(ConnectionError):
        refresh()
    assert refresh() == {"ok": True}
