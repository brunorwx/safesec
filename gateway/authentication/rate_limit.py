"""Simple fixed-window rate limiter for authenticated endpoints."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta


class RateLimiter:
    def __init__(self, *, limit: int, window: timedelta = timedelta(minutes=1)) -> None:
        if limit < 1 or window.total_seconds() <= 0:
            raise ValueError("rate limit and window must be positive")
        self.limit = limit
        self.window = window
        self._requests: defaultdict[str, list[datetime]] = defaultdict(list)

    def allow(self, subject: str, *, now: datetime | None = None) -> bool:
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        cutoff = moment - self.window
        recent = [request for request in self._requests[subject] if request > cutoff]
        self._requests[subject] = recent
        if len(recent) >= self.limit:
            return False
        recent.append(moment)
        return True
