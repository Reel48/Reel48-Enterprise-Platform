"""Shared service-layer helpers."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User


async def resolve_current_user_id(db: AsyncSession, cognito_sub: str) -> UUID:
    """Look up the User record by cognito_sub and return its id (UUID).

    Used by endpoints that need to set created_by FK (org_codes, invites),
    since TenantContext.user_id is the Cognito 'sub' string, not users.id.
    """
    result = await db.execute(
        select(User.id).where(User.cognito_sub == cognito_sub, User.deleted_at.is_(None))
    )
    user_id = result.scalar_one_or_none()
    if user_id is None:
        raise NotFoundError("User", cognito_sub)
    return user_id
