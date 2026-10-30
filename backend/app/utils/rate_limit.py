import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status


class RateLimiter:
    """In-memory sliding-window limiter keyed by client IP (single-process only)."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()

    async def __call__(self, request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        if not self.allow(client):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
