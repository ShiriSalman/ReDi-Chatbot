# Tests for the limit per visitor, written from specs/rate_limit_per_visitor.md.
# A fake clock is passed in, so the tests never wait.
from rate_limit import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make_limiter(limit=3, window_seconds=60):
    clock = FakeClock()
    return RateLimiter(limit, window_seconds, clock=clock), clock


# AC1
def test_allows_the_limit_and_refuses_the_next_call():
    limiter, _ = make_limiter(limit=3)

    assert [limiter.allow("visitor") for _ in range(4)] == [True, True, True, False]


def test_a_refused_call_is_not_counted():
    limiter, clock = make_limiter(limit=1, window_seconds=60)
    limiter.allow("visitor")
    clock.now += 30
    limiter.allow("visitor")  # refused

    clock.now += 31  # 61 s after the first call, 31 s after the refused one

    assert limiter.allow("visitor") is True


# AC2
def test_calls_are_allowed_again_after_the_window():
    limiter, clock = make_limiter(limit=2, window_seconds=60)
    limiter.allow("visitor")
    limiter.allow("visitor")

    clock.now += 59
    assert limiter.allow("visitor") is False
    clock.now += 1
    assert limiter.allow("visitor") is True


# AC3
def test_every_key_has_its_own_count():
    limiter, _ = make_limiter(limit=1)

    assert limiter.allow("visitor-a") is True
    assert limiter.allow("visitor-b") is True
    assert limiter.allow("visitor-a") is False


# AC4
def test_inactive_keys_are_forgotten():
    limiter, clock = make_limiter(limit=5, window_seconds=60)
    limiter.allow("visitor-a")
    clock.now += 61

    limiter.allow("visitor-b")

    assert limiter.known_keys() == {"visitor-b"}
