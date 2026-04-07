"""
Redis-based rate limiting for unauthenticated endpoints.

Both auth endpoints (validate-org-code and register) share the same
rate limit window via the "auth" group. This prevents an attacker from
using 5 attempts on validate then 5 more on register.

Graceful degradation: if Redis is unavailable, the request is allowed
through (don't block registration because Redis is down).
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import structlog
from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitError

logger = structlog.get_logger()

_redis_client: Any = None


async def _get_redis_client() -> Any:
    """Lazy singleton Redis client. Returns None if connection fails."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as redis

        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Verify connectivity
        await _redis_client.ping()
        return _redis_client
    except Exception:
        logger.warning("redis_connection_failed", redis_url=settings.REDIS_URL)
        return None


def check_rate_limit(
    group: str = "auth",
    max_attempts: int = 5,
    window_seconds: int = 900,
) -> Callable[..., Coroutine[Any, Any, None]]:
    """
    Returns a FastAPI dependency that enforces rate limiting.

    Usage in routes:
        @router.post("/endpoint")
        async def my_endpoint(
            _rate_limit: None = Depends(rate_limit_auth),
        ):
    """

    async def _dependency(request: Request) -> None:
        client = await _get_redis_client()
        if client is None:
            return  # Graceful degradation

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{group}:{client_ip}"

        try:
            current: int = await client.incr(key)
            if current == 1:
                await client.expire(key, window_seconds)
            if current > max_attempts:
                raise RateLimitError()
        except RateLimitError:
            raise
        except Exception:
            logger.warning("redis_rate_limit_error", group=group, ip=client_ip)
            return  # Graceful degradation

    return _dependency


# Pre-configured dependency for auth endpoints (5 attempts per 15 minutes)
rate_limit_auth = check_rate_limit(group="auth", max_attempts=5, window_seconds=900)
