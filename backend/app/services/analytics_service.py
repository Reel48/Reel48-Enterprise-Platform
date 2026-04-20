"""Analytics service — minimal user/company counts.

Most analytics (spend, orders, approvals, invoicing) were removed in the
simplification refactor. Commerce analytics will return when the Shopify
integration lands.
"""

from __future__ import annotations

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.user import User

logger = structlog.get_logger()


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_company_overview(self) -> dict:
        """Company-scoped overview: active user count. Called with RLS enabled."""
        active_users = (
            await self.db.execute(
                select(func.count(User.id)).where(
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )
        ).scalar() or 0

        return {
            "active_users": active_users,
        }

    async def get_platform_overview(self) -> dict:
        """Cross-company platform metrics. Called with RLS bypass (reel48_admin)."""
        total_companies = (
            await self.db.execute(
                select(func.count(Company.id)).where(Company.is_active.is_(True))
            )
        ).scalar() or 0

        total_users = (
            await self.db.execute(
                select(func.count(User.id)).where(
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )
        ).scalar() or 0

        return {
            "total_companies": total_companies,
            "total_users": total_users,
        }
