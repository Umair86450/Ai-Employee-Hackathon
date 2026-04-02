"""Retry helpers for transient failures."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any


TRANSIENT_PATTERNS = (
    "timeout",
    "timed out",
    "temporarily unavailable",
    "temporary failure",
    "connection refused",
    "connection reset",
    "broken pipe",
    "service unavailable",
    "network is unreachable",
    "econnreset",
    "dns",
    "name or service not known",
    "try again",
    "too many requests",
    "rate limit",
    "429",
    "502",
    "503",
    "504",
    "unable to reach",
    "server disconnected",
)


def is_transient_error(exc: BaseException) -> bool:
    text = str(exc).strip().lower()
    if not text:
        return False
    return any(pattern in text for pattern in TRANSIENT_PATTERNS)


async def retry_async(
    operation: Callable[[int], Awaitable[Any]],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    is_retryable: Callable[[BaseException], bool] | None = None,
    on_retry: Callable[[int, BaseException, float], Any] | None = None,
) -> Any:
    attempts = max(1, attempts)
    retryable = is_retryable or is_transient_error
    delay = max(0.0, base_delay)
    last_error: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await operation(attempt)
        except Exception as exc:  # pragma: no cover - behavior validated via callers
            last_error = exc
            should_retry = attempt < attempts and retryable(exc)
            if not should_retry:
                raise
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            await asyncio.sleep(delay)
            delay = min(max_delay, delay * 2 if delay else 1.0)

    if last_error is not None:
        raise last_error
    raise RuntimeError("retry_async reached an impossible state")


def retry_sync(
    operation: Callable[[int], Any],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    is_retryable: Callable[[BaseException], bool] | None = None,
    on_retry: Callable[[int, BaseException, float], Any] | None = None,
) -> Any:
    attempts = max(1, attempts)
    retryable = is_retryable or is_transient_error
    delay = max(0.0, base_delay)
    last_error: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return operation(attempt)
        except Exception as exc:
            last_error = exc
            should_retry = attempt < attempts and retryable(exc)
            if not should_retry:
                raise
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            time.sleep(delay)
            delay = min(max_delay, delay * 2 if delay else 1.0)

    if last_error is not None:
        raise last_error
    raise RuntimeError("retry_sync reached an impossible state")
