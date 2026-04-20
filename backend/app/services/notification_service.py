"""Notification service — create, list, and manage notifications/announcements."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import and_, func, literal, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate

logger = structlog.get_logger()


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_notification(
        self,
        company_id: UUID,
        data: NotificationCreate,
        created_by: UUID,
    ) -> Notification:
        """Create a notification/announcement.

        - company scope: visible to every user in the company
        - individual scope: target_user_id set, only that user sees it
        """
        if data.target_scope == "individual":
            if data.target_user_id is None:
                raise ValidationError("target_user_id is required for individual scope")
            result = await self.db.execute(
                select(User.id).where(
                    User.id == data.target_user_id,
                    User.company_id == company_id,
                    User.deleted_at.is_(None),
                )
            )
            if result.scalar_one_or_none() is None:
                raise NotFoundError("User", str(data.target_user_id))
        elif data.target_user_id is not None:
            raise ValidationError("target_user_id should only be set for individual scope")

        notification = Notification(
            company_id=company_id,
            title=data.title,
            body=data.body,
            notification_type=data.notification_type,
            target_scope=data.target_scope,
            target_user_id=data.target_user_id,
            link_url=data.link_url,
            expires_at=data.expires_at,
            created_by=created_by,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)

        logger.info(
            "notification_created",
            notification_id=str(notification.id),
            target_scope=data.target_scope,
            company_id=str(company_id),
        )
        return notification

    async def list_notifications_for_user(
        self,
        user_id: UUID,
        company_id: UUID,
        page: int = 1,
        per_page: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int, int]:
        """List notifications visible to the given user.

        Filters: is_active=True, not expired, AND one of:
          - target_scope='company' (company-wide)
          - target_scope='individual' AND target_user_id matches

        Returns: (notifications, total_count, unread_count)
        """
        now = datetime.now(UTC)
        user_id_str = str(user_id)

        base_filters = [
            Notification.company_id == company_id,
            Notification.is_active.is_(True),
        ]
        expiry_filter = (
            Notification.expires_at.is_(None) | (Notification.expires_at > now)
        )
        base_filters.append(expiry_filter)

        visibility_filter = or_(
            Notification.target_scope == "company",
            and_(
                Notification.target_scope == "individual",
                Notification.target_user_id == user_id,
            ),
        )

        query = select(Notification).where(*base_filters, visibility_filter)

        unread_filter = not_(
            Notification.read_by.op("@>")(
                func.cast(literal(f'["{user_id_str}"]'), JSONB)
            )
        )

        if unread_only:
            query = query.where(unread_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        unread_query = select(func.count()).select_from(
            select(Notification.id)
            .where(*base_filters, visibility_filter, unread_filter)
            .subquery()
        )
        unread_count = await self.db.scalar(unread_query) or 0

        query = query.order_by(Notification.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        return notifications, total or 0, unread_count

    async def mark_as_read(
        self,
        notification_id: UUID,
        user_id: str,
        company_id: UUID,
    ) -> Notification:
        """Add user_id to the read_by JSONB array if not already present (idempotent)."""
        notification = await self.get_notification(notification_id, company_id)

        read_by = notification.read_by or []
        if user_id not in read_by:
            notification.read_by = read_by + [user_id]  # type: ignore[assignment]
            await self.db.flush()
            await self.db.refresh(notification)

        return notification

    async def mark_all_as_read(
        self,
        user_id: str,
        company_id: UUID,
    ) -> int:
        """Mark all unread visible notifications as read. Returns count newly marked."""
        now = datetime.now(UTC)
        user_id_str = user_id

        base_filters = [
            Notification.company_id == company_id,
            Notification.is_active.is_(True),
            (Notification.expires_at.is_(None) | (Notification.expires_at > now)),
        ]

        visibility_filter = or_(
            Notification.target_scope == "company",
            and_(
                Notification.target_scope == "individual",
                Notification.target_user_id == user_id,
            ),
        )

        unread_filter = not_(
            Notification.read_by.op("@>")(
                func.cast(literal(f'["{user_id_str}"]'), JSONB)
            )
        )

        query = (
            select(Notification)
            .where(*base_filters, visibility_filter, unread_filter)
        )
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        count = 0
        for notification in notifications:
            read_by = notification.read_by or []
            if user_id_str not in read_by:
                notification.read_by = read_by + [user_id_str]  # type: ignore[assignment]
                count += 1

        if count > 0:
            await self.db.flush()

        return count

    async def list_notifications_admin(
        self,
        company_id: UUID,
        page: int = 1,
        per_page: int = 20,
        notification_type: str | None = None,
    ) -> tuple[list[Notification], int]:
        """Admin view: list all notifications including expired and inactive."""
        query = select(Notification).where(Notification.company_id == company_id)

        if notification_type is not None:
            query = query.where(Notification.notification_type == notification_type)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.order_by(Notification.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def deactivate_notification(
        self,
        notification_id: UUID,
        company_id: UUID,
    ) -> Notification:
        """Soft-deactivate a notification (set is_active=False)."""
        notification = await self.get_notification(notification_id, company_id)
        notification.is_active = False  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(notification)

        logger.info(
            "notification_deactivated",
            notification_id=str(notification_id),
        )
        return notification

    async def get_notification(
        self,
        notification_id: UUID,
        company_id: UUID,
    ) -> Notification:
        """Fetch a single notification by ID with company_id filter."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.company_id == company_id,
            )
        )
        notification = result.scalar_one_or_none()
        if notification is None:
            raise NotFoundError("Notification", str(notification_id))
        return notification
