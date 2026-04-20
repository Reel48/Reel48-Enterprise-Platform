import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.invite import Invite
from app.schemas.invite import InviteCreate

VALID_INVITE_ROLES = {"employee", "manager", "company_admin"}


class InviteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_invites(
        self,
        company_id: UUID,
        page: int,
        per_page: int,
    ) -> tuple[list[Invite], int]:
        query = select(Invite).where(Invite.company_id == company_id)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def create_invite(
        self,
        company_id: UUID,
        data: InviteCreate,
        created_by_user_id: UUID,
    ) -> Invite:
        if data.role not in VALID_INVITE_ROLES:
            raise ValidationError(f"Invalid invite role: {data.role}", field="role")

        now = datetime.now(UTC)
        existing = await self.db.execute(
            select(Invite).where(
                Invite.company_id == company_id,
                Invite.email == data.email,
                Invite.consumed_at.is_(None),
                Invite.expires_at > now,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(
                f"An active invite already exists for '{data.email}' in this company"
            )

        token = secrets.token_hex(32)

        invite = Invite(
            company_id=company_id,
            email=data.email,
            role=data.role,
            token=token,
            expires_at=now + timedelta(hours=72),
            created_by=created_by_user_id,
        )
        self.db.add(invite)
        await self.db.flush()
        await self.db.refresh(invite)
        return invite

    async def delete_invite(self, invite_id: UUID, company_id: UUID) -> None:
        result = await self.db.execute(
            select(Invite).where(
                Invite.id == invite_id,
                Invite.company_id == company_id,
            )
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise NotFoundError("Invite", str(invite_id))
        await self.db.delete(invite)
        await self.db.flush()
