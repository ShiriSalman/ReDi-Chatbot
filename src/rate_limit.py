"""A small limit per visitor: at most `limit` calls in the last `window_seconds`.

See specs/rate_limit_per_visitor.md for the expected behavior and
tests/test_rate_limit.py for the tests.

Everything is kept in memory only. gunicorn runs one worker with several threads
(Dockerfile), so one lock is enough to keep the counts correct.
"""
import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, limit, window_seconds, clock=time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        # The clock is passed in, so tests can move time forward without waiting
        self.clock = clock
        self.lock = threading.Lock()
        # key -> times of the calls in the current window, oldest first
        self.calls = {}

    def allow(self, key):
        """Return True and count the call if key has fewer than `limit` calls in the
        window; otherwise return False. A refused call is not counted."""
        now = self.clock()
        with self.lock:
            self.forget_old_calls(now)
            times = self.calls.setdefault(key, deque())
            if len(times) >= self.limit:
                return False
            times.append(now)
            return True

    def forget_old_calls(self, now):
        """Drop calls older than the window, and keys that have no calls left."""
        for key in list(self.calls):
            times = self.calls[key]
            while times and now - times[0] >= self.window_seconds:
                times.popleft()
            if not times:
                del self.calls[key]

    def known_keys(self):
        """The keys that still have calls in memory (for tests)."""
        with self.lock:
            return set(self.calls)
