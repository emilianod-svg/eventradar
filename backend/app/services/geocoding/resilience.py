"""Resiliencia simple para proveedores de geocodificación."""

from __future__ import annotations

import asyncio
import random
import time


class AsyncRateLimiter:
    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval_seconds = max(min_interval_seconds, 0.0)
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def wait(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            wait_seconds = self._min_interval_seconds - elapsed
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._last_call = time.monotonic()


class CircuitBreaker:
    def __init__(self, failure_threshold: int, reset_seconds: float) -> None:
        self.failure_threshold = max(failure_threshold, 1)
        self.reset_seconds = max(reset_seconds, 1.0)
        self.failures = 0
        self.opened_at: float | None = None

    def allow_request(self) -> bool:
        if self.opened_at is None:
            return True
        if (time.monotonic() - self.opened_at) >= self.reset_seconds:
            self.failures = 0
            self.opened_at = None
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()


def jitter(base_seconds: float, jitter_seconds: float, attempt: int) -> float:
    return (base_seconds * (2**attempt)) + random.uniform(0.0, max(jitter_seconds, 0.0))
