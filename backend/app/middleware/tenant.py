"""
Tenant context middleware — clears structlog context variables per request.

The actual tenant context (user_id, company_id, role) is bound to structlog
contextvars inside get_tenant_context (dependencies.py), which
runs in the FastAPI dependency layer. This middleware's sole job is to clear
stale contextvars at the start of each request, preventing tenant info from
leaking between requests on the same connection (e.g., keep-alive reuse).
"""

from collections.abc import Callable
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Clear structlog contextvars at the start of each request."""

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        structlog.contextvars.clear_contextvars()
        response: Response = await call_next(request)
        return response
