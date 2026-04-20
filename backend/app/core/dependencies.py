"""
FastAPI dependency injection functions.

CRITICAL: All request-scoped dependencies live here. Import get_db_session
from THIS module — never from app.core.database directly. FastAPI de-duplicates
dependencies by object identity; importing from two different module paths
produces two separate sessions, breaking RLS enforcement.
"""

from uuid import UUID

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings  # noqa: F401 — used by tests patching settings
from app.core.database import get_db_session  # noqa: F401 — re-exported as canonical source
from app.core.exceptions import ForbiddenError
from app.core.security import validate_cognito_token
from app.core.tenant import TenantContext

security_scheme = HTTPBearer()


# TODO(simplification plan): remove this shim once all dev Cognito users have
# been migrated to the new role values (see the "Existing dev users may have
# the old role strings" risk in ~/.claude/plans/yes-please-write-the-memoized-karp.md).
_LEGACY_ROLE_MAP = {
    "corporate_admin": "company_admin",
    "sub_brand_admin": "company_admin",
    "regional_manager": "manager",
}


def _normalize_role(role: str) -> str:
    return _LEGACY_ROLE_MAP.get(role, role)


async def get_tenant_context(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> TenantContext:
    """
    Validate the Cognito JWT and return the tenant context.

    Steps:
    1. Decode and validate the JWT (signature, expiry, audience)
    2. Extract custom claims: company_id, role
    3. Normalize legacy role strings (temporary shim — see TODO above)
    4. Set PostgreSQL session variables for RLS enforcement
    5. Bind structlog context vars for request logging
    6. Return typed TenantContext

    CRITICAL: This dependency and route handlers share the SAME db session
    (FastAPI de-duplicates Depends(get_db_session)). The SET LOCAL calls
    here apply to the same transaction that the route's queries run in.
    """
    claims = await validate_cognito_token(credentials.credentials)

    role = _normalize_role(claims["custom:role"])
    raw_company_id = claims.get("custom:company_id")  # None for reel48_admin

    context = TenantContext(
        user_id=claims["sub"],
        company_id=UUID(raw_company_id) if raw_company_id else None,
        role=role,
    )

    # CRITICAL: Set PostgreSQL session variables so RLS policies can reference them.
    # SET LOCAL scopes values to the current transaction only, preventing leakage
    # across pooled connections. For reel48_admin: empty string triggers RLS bypass.
    # NOTE: SET LOCAL does not support bind parameters. Values come from validated
    # JWTs and are parsed as UUID, so f-string interpolation is safe.
    if context.is_reel48_admin:
        await db.execute(text("SET LOCAL app.current_company_id = ''"))
    else:
        await db.execute(
            text(f"SET LOCAL app.current_company_id = '{context.company_id}'")
        )

    structlog.contextvars.bind_contextvars(
        user_id=context.user_id,
        company_id=str(context.company_id) if context.company_id else None,
        role=context.role,
    )

    return context


# --- Role-checking convenience dependencies ---


async def require_reel48_admin(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """Only reel48_admin (platform operator) can access."""
    if not context.is_reel48_admin:
        raise ForbiddenError("Platform admin role required")
    return context


async def require_company_admin(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """company_admin or reel48_admin can access."""
    if not context.is_company_admin_or_above:
        raise ForbiddenError("Company admin role required")
    return context


async def require_manager(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """manager or any admin can access."""
    if not context.is_manager_or_above:
        raise ForbiddenError("Manager role required")
    return context


__all__ = [
    "get_db_session",
    "get_tenant_context",
    "require_company_admin",
    "require_manager",
    "require_reel48_admin",
]
