from app.utils.rate_limit import RateLimiter


def test_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")


def test_limits_are_per_client():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("a")


def test_window_expiry_allows_again(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.utils.rate_limit.time.monotonic", lambda: now[0])
    limiter = RateLimiter(max_requests=1, window_seconds=10)
    assert limiter.allow("a")
    assert not limiter.allow("a")
    now[0] += 11
    assert limiter.allow("a")
