import secrets
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.org_code import OrgCode

# 30-char alphabet excluding ambiguous characters: 0/O, 1/I/L
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class OrgCodeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_code(self, company_id: UUID, created_by: UUID) -> OrgCode:
        # Deactivate all existing active codes for this company
        await self.db.execute(
            update(OrgCode)
            .where(OrgCode.company_id == company_id, OrgCode.is_active == True)  # noqa: E712
            .values(is_active=False)
        )

        # Generate unique 8-char code (retry on collision, up to 3 attempts)
        for _ in range(3):
            code = "".join(secrets.choice(ALPHABET) for _ in range(8))
            existing = await self.db.execute(
                select(OrgCode).where(OrgCode.code == code)
            )
            if existing.scalar_one_or_none() is None:
                break
        else:
            # Extremely unlikely — 30^8 = 6.56 × 10^11 possible codes
            code = "".join(secrets.choice(ALPHABET) for _ in range(8))

        org_code = OrgCode(company_id=company_id, code=code, created_by=created_by)
        self.db.add(org_code)
        await self.db.flush()
        await self.db.refresh(org_code)
        return org_code

    async def get_current(self, company_id: UUID) -> OrgCode | None:
        result = await self.db.execute(
            select(OrgCode).where(
                OrgCode.company_id == company_id,
                OrgCode.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def deactivate(self, org_code_id: UUID, company_id: UUID) -> OrgCode:
        result = await self.db.execute(
            select(OrgCode).where(
                OrgCode.id == org_code_id,
                OrgCode.company_id == company_id,
            )
        )
        org_code = result.scalar_one_or_none()
        if org_code is None:
            raise NotFoundError("OrgCode", str(org_code_id))
        org_code.is_active = False  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(org_code)
        return org_code
