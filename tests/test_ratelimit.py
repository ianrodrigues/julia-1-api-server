"""Token-bucket arithmetic with a fake clock, and per-client limits over HTTP."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.ratelimit import RateLimiter, retry_after_header


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_burst_then_refill_at_rate():
    clock = FakeClock()
    limiter = RateLimiter(per_minute=60, burst=3, clock=clock)
    assert [limiter.acquire("a") for _ in range(3)] == [0, 0, 0]
    assert limiter.acquire("a") == 1.0
    clock.now = 0.5
    assert limiter.acquire("a") == 0.5
    clock.now = 1.0
    assert limiter.acquire("a") == 0
    clock.now = 100.0
    assert [limiter.acquire("a") for _ in range(3)] == [0, 0, 0]
    assert limiter.acquire("a") > 0


def test_clients_have_separate_buckets():
    limiter = RateLimiter(per_minute=60, burst=1, clock=FakeClock())
    assert limiter.acquire("a") == 0
    assert limiter.acquire("a") > 0
    assert limiter.acquire("b") == 0


def test_client_table_is_bounded():
    clock = FakeClock()
    limiter = RateLimiter(per_minute=60, burst=1, clock=clock, max_clients=2)
    for key in "abc":
        limiter.acquire(key)
        clock.now += 0.1
    assert len(limiter.buckets) == 2
    assert "a" not in limiter.buckets
    clock.now = 10.0
    limiter.acquire("d")
    assert set(limiter.buckets) == {"d"}


def test_retry_after_is_whole_seconds_of_at_least_one():
    assert retry_after_header(0.01) == "1"
    assert retry_after_header(1.2) == "2"


def limited_client(**options):
    # No lifespan: routes answer 503, but the middleware still runs first.
    settings = Settings(_env_file=None, rate_limit_per_minute=1, rate_limit_burst=2, **options)
    return TestClient(create_app(settings))


def test_excess_requests_get_429_but_health_is_exempt():
    client = limited_client()
    assert [client.get("/v1/info").status_code for _ in range(3)] == [503, 503, 429]
    response = client.get("/v1/info")
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests; retry later"}
    assert int(response.headers["Retry-After"]) > 1
    assert all(client.get("/health").status_code == 503 for _ in range(5))


def test_configured_header_identifies_clients_behind_a_proxy():
    client = limited_client(client_ip_header="CF-Connecting-IP")
    first, second = {"CF-Connecting-IP": "203.0.113.1"}, {"CF-Connecting-IP": "203.0.113.2"}
    assert [client.get("/v1/info", headers=first).status_code for _ in range(3)][-1] == 429
    assert client.get("/v1/info", headers=second).status_code == 503


def test_header_is_ignored_unless_configured():
    client = limited_client()
    for address in ("203.0.113.1", "203.0.113.2", "203.0.113.3"):
        response = client.get("/v1/info", headers={"CF-Connecting-IP": address})
    assert response.status_code == 429


def test_zero_disables_limiting():
    client = TestClient(create_app(Settings(_env_file=None, rate_limit_per_minute=0)))
    assert all(client.get("/v1/info").status_code == 503 for _ in range(20))
