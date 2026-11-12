"""Small in-memory sliding-window rate limiter (no extra dependency).

Limits are per server process. That is fine for a single instance; if you run several
workers or instances, each keeps its own counters (move this to Redis then).
A limit of 0 (or less) in settings disables that rule.
"""

import math
import threading
import time
from collections import deque
from typing import Dict, Sequence, Tuple

from fastapi import HTTPException, Request

from app.config import settings

# (name, name of the Settings attribute holding the limit, window in seconds)
Rule = Tuple[str, str, float]


class RateLimiter:
    def __init__(self) -> None:
        self._events: Dict[str, deque] = {}
        self._windows: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._last_prune = time.monotonic()

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._windows.clear()

    # -- internals (call with the lock held) ---------------------------------
    def _prune(self, now: float) -> None:
        if now - self._last_prune < 60:
            return
        self._last_prune = now
        for key in list(self._events):
            q, window = self._events[key], self._windows[key]
            while q and q[0] <= now - window:
                q.popleft()
            if not q:
                del self._events[key], self._windows[key]

    def _queue(self, key: str, window: float, now: float) -> deque:
        q = self._events.setdefault(key, deque())
        self._windows[key] = window
        while q and q[0] <= now - window:
            q.popleft()
        return q

    def _retry_after(self, ident: str, rules: Sequence[Rule], cost: int, now: float) -> float:
        wait = 0.0
        for name, attr, window in rules:
            limit = int(getattr(settings, attr))
            if limit <= 0:
                continue
            q = self._queue(f"{name}:{ident}", window, now)
            over = len(q) + cost - limit
            if over > 0:
                # wait until enough old events have expired
                wait = max(wait, (q[over - 1] + window - now) if over <= len(q) else window)
        return wait

    @staticmethod
    def _raise(wait: float) -> None:
        secs = max(1, math.ceil(wait))
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please try again in {secs} second{'s' if secs != 1 else ''}.",
            headers={"Retry-After": str(secs)},
        )

    # -- public API -------------------------------------------------------------
    def hit(self, ident: str, rules: Sequence[Rule], cost: int = 1) -> None:
        """Count `cost` events against every rule, or raise 429 (and count nothing) if any would overflow."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            wait = self._retry_after(ident, rules, cost, now)
            if wait > 0:
                self._raise(wait)
            for name, attr, window in rules:
                if int(getattr(settings, attr)) > 0:
                    self._queue(f"{name}:{ident}", window, now).extend([now] * cost)

    def check(self, ident: str, rules: Sequence[Rule]) -> None:
        """Raise 429 if the next event would overflow a rule, without counting anything."""
        now = time.monotonic()
        with self._lock:
            wait = self._retry_after(ident, rules, 1, now)
            if wait > 0:
                self._raise(wait)

    def record(self, ident: str, rules: Sequence[Rule]) -> None:
        """Count one event without ever raising (e.g. a failed login)."""
        now = time.monotonic()
        with self._lock:
            for name, attr, window in rules:
                if int(getattr(settings, attr)) > 0:
                    self._queue(f"{name}:{ident}", window, now).append(now)


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def limit_ip(name: str, attr: str, window: float):
    """FastAPI dependency: limit requests per client IP."""
    def dependency(request: Request) -> None:
        limiter.hit(client_ip(request), [(name, attr, window)])
    return dependency
