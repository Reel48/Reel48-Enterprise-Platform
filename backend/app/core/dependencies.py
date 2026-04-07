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


async def get_tenant_context(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> TenantContext:
    """
    Validate the Cognito JWT and return the tenant context.

    Steps:
    1. Decode and validate the JWT (signature, expiry, audience)
    2. Extract custom claims: company_id, sub_brand_id, role
    3. Set PostgreSQL session variables for RLS enforcement
    4. Bind structlog context vars for request logging
    5. Return typed TenantContext

    CRITICAL: This dependency and route handlers share the SAME db session
    (FastAPI de-duplicates Depends(get_db_session)). The SET LOCAL calls
    here apply to the same transaction that the route's queries run in.
    """
    claims = await validate_cognito_token(credentials.credentials)

    # Extract role FIRST — reel48_admin has no company_id or sub_brand_id in JWT.
    role = claims["custom:role"]
    raw_company_id = claims.get("custom:company_id")  # None for reel48_admin
    raw_sub_brand_id = claims.get("custom:sub_brand_id")  # None for corporate_admin & reel48_admin

    context = TenantContext(
        user_id=claims["sub"],
        company_id=UUID(raw_company_id) if raw_company_id else None,
        sub_brand_id=UUID(raw_sub_brand_id) if raw_sub_brand_id else None,
        role=role,
    )

    # CRITICAL: Set PostgreSQL session variables so RLS policies can reference them.
    # SET LOCAL scopes values to the current transaction only, preventing leakage
    # across pooled connections. For reel48_admin: empty string triggers RLS bypass.
    # Parameterized queries for defense-in-depth (values come from validated JWTs).
    # NOTE: SET LOCAL does not support bind parameters ($1) in PostgreSQL.
    # Values are safe — company_id and sub_brand_id are parsed as UUID from validated JWTs.
    if context.is_reel48_admin:
        await db.execute(text("SET LOCAL app.current_company_id = ''"))
        await db.execute(text("SET LOCAL app.current_sub_brand_id = ''"))
    else:
        await db.execute(
            text(f"SET LOCAL app.current_company_id = '{context.company_id}'")
        )
        if context.sub_brand_id:
            await db.execute(
                text(f"SET LOCAL app.current_sub_brand_id = '{context.sub_brand_id}'")
            )
        else:
            # corporate_admin: no sub_brand_id → empty string (sees all sub-brands via RLS)
            await db.execute(text("SET LOCAL app.current_sub_brand_id = ''"))

    # Bind tenant info to structlog so every downstream log line includes it
    structlog.contextvars.bind_contextvars(
        user_id=context.user_id,
        company_id=str(context.company_id) if context.company_id else None,
        sub_brand_id=str(context.sub_brand_id) if context.sub_brand_id else None,
        role=context.role,
    )

    return context


# --- Role-checking convenience dependencies ---
# Use these in route signatures for declarative authorization:
#   context: TenantContext = Depends(require_admin)


async def require_reel48_admin(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """Only reel48_admin (platform operator) can access."""
    if not context.is_reel48_admin:
        raise ForbiddenError("Platform admin role required")
    return context


async def require_corporate_admin(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """corporate_admin or reel48_admin can access."""
    if not context.is_corporate_admin_or_above:
        raise ForbiddenError("Corporate admin role required")
    return context


async def require_admin(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """Any admin role (sub_brand_admin, corporate_admin, reel48_admin) can access."""
    if not context.is_admin:
        raise ForbiddenError("Admin role required")
    return context


async def require_manager(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """regional_manager or any admin can access."""
    if not context.is_manager_or_above:
        raise ForbiddenError("Manager role required")
    return context


__all__ = [
    "get_db_session",
    "get_tenant_context",
    "require_admin",
    "require_corporate_admin",
    "require_manager",
    "require_reel48_admin",
]
