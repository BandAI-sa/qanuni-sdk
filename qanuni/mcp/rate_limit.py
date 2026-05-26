"""In-memory rate limiting primitives for the Qanuni MCP server."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import time


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Describe the result of one rate-limit check.

    Args:
        allowed: Whether the request may continue.
        remaining: Remaining request count in the current window.
        retry_after_seconds: Suggested wait time when the request is denied.

    Returns:
        None.

    Raises:
        None.
    """

    allowed: bool
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    """Enforce a fixed-window request budget per caller identity.

    Args:
        window_seconds: Size of the rolling window in seconds.
        max_requests: Maximum number of requests allowed in that window.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, *, window_seconds: int, max_requests: int) -> None:
        """Initialize the limiter with an empty caller history.

        Args:
            window_seconds: Size of the rolling window in seconds.
            max_requests: Maximum number of requests allowed in that window.

        Returns:
            None.

        Raises:
            None.
        """
        self._window_seconds: int = window_seconds
        self._max_requests: int = max_requests
        self._history: dict[str, deque[float]] = {}
        self._lock: Lock = Lock()

    def check(self, identity: str) -> RateLimitDecision:
        """Evaluate whether one caller can perform another request.

        Args:
            identity: Stable caller identity such as an auth principal hash.

        Returns:
            A decision object describing allowance, remaining budget, and retry delay.

        Raises:
            None.
        """
        now: float = time()
        with self._lock:
            timestamps: deque[float] = self._history.setdefault(identity, deque())
            self._prune(now=now, timestamps=timestamps)
            if len(timestamps) >= self._max_requests:
                oldest: float = timestamps[0]
                retry_after_seconds: int = max(
                    1,
                    int(self._window_seconds - (now - oldest)),
                )
                return RateLimitDecision(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=retry_after_seconds,
                )
            timestamps.append(now)
            remaining: int = max(self._max_requests - len(timestamps), 0)
            return RateLimitDecision(
                allowed=True,
                remaining=remaining,
                retry_after_seconds=0,
            )

    def _prune(self, *, now: float, timestamps: deque[float]) -> None:
        """Remove timestamps that have fallen outside the active window.

        Args:
            now: Current wall-clock timestamp used for the rate-limit check.
            timestamps: Mutable timestamp deque for one caller identity.

        Returns:
            None.

        Raises:
            None.
        """
        while timestamps and (now - timestamps[0]) >= self._window_seconds:
            timestamps.popleft()
