"""In-memory, per-client token buckets for a single-process server."""

import math
import time
from collections.abc import Callable


class RateLimiter:
    """Refill each client's bucket continuously; one request spends one token.

    Called only from the event loop, so no locking is needed.
    """

    def __init__(
        self,
        per_minute: int,
        burst: int,
        clock: Callable[[], float] = time.monotonic,
        max_clients: int = 10_000,
    ):
        self.rate = per_minute / 60
        self.burst = burst
        self.clock = clock
        self.max_clients = max_clients
        self.buckets: dict[str, tuple[float, float]] = {}

    def acquire(self, key: str) -> float:
        """Spend a token and return 0, or return the seconds until one is available."""
        now = self.clock()
        tokens, updated = self.buckets.get(key, (self.burst, now))
        tokens = min(self.burst, tokens + (now - updated) * self.rate)
        if tokens >= 1:
            self._store(key, tokens - 1, now)
            return 0.0
        self._store(key, tokens, now)
        return (1 - tokens) / self.rate

    def _store(self, key: str, tokens: float, now: float) -> None:
        if key not in self.buckets and len(self.buckets) >= self.max_clients:
            self._prune(now)
        self.buckets[key] = (tokens, now)

    def _prune(self, now: float) -> None:
        """Forget refilled buckets; if every client is still active, forget the oldest."""
        refill_time = self.burst / self.rate
        self.buckets = {
            key: value for key, value in self.buckets.items() if now - value[1] < refill_time
        }
        if len(self.buckets) >= self.max_clients:
            oldest = min(self.buckets, key=lambda key: self.buckets[key][1])
            del self.buckets[oldest]


def retry_after_header(seconds: float) -> str:
    return str(max(1, math.ceil(seconds)))
