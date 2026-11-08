"""Refresh on demand, but not more often than the sources can reasonably be asked."""
import threading
import time


class ThrottledRefresh:
    """Calls `fetch` at most once per `min_interval` seconds; in between, returns
    the last result. A failed fetch is not remembered, so it can be retried at once."""

    def __init__(self, fetch, min_interval: float = 60, clock=time.monotonic):
        self._fetch = fetch
        self._min_interval = min_interval
        self._clock = clock
        self._lock = threading.Lock()
        self._last_result = None
        self._last_time = None

    def __call__(self):
        with self._lock:
            now = self._clock()
            if self._last_time is not None and now - self._last_time < self._min_interval:
                return self._last_result
            self._last_result = self._fetch()
            self._last_time = now
            return self._last_result
