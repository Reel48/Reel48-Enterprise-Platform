"""Notification service — create, list, and manage notifications/announcements."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import and_, func, literal, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
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
        sub_brand_id: UUID | None,
        data: NotificationCreate,
        created_by: UUID,
    ) -> Notification:
        """Create a notification/announcement.

        - company scope: sub_brand_id is None on the record (visible to all sub-brands via RLS)
        - sub_brand scope: sub_brand_id set to the creator's sub-brand
        - individual: sub_brand_id set, target_user_id set
        """
        # Determine the sub_brand_id for the notification record
        if data.target_scope == "company":
            record_sub_brand_id = None
        else:
            record_sub_brand_id = sub_brand_id

        # Validate target_user_id for individual scope
        if data.target_scope == "individual":
            if data.target_user_id is None:
                raise ValidationError("target_user_id is required for individual scope")
            # Verify target user exists and belongs to the same company
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
            sub_brand_id=record_sub_brand_id,
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
        sub_brand_id: UUID | None,
        page: int = 1,
        per_page: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int, int]:
        """List notifications visible to the given user.

        Filters: is_active=True, not expired, AND one of:
          - target_scope='company' (company-wide)
          - target_scope='sub_brand' AND sub_brand_id matches
          - target_scope='individual' AND target_user_id matches

        Returns: (notifications, total_count, unread_count)
        """
        now = datetime.now(UTC)
        user_id_str = str(user_id)

        # Base filter: active and not expired
        base_filters = [
            Notification.company_id == company_id,
            Notification.is_active.is_(True),
        ]
        # Not expired: expires_at is NULL or in the future
        expiry_filter = (
            Notification.expires_at.is_(None) | (Notification.expires_at > now)
        )
        base_filters.append(expiry_filter)

        # Visibility: company-wide OR matching sub-brand OR targeted to this user
        visibility_conditions = [
            Notification.target_scope == "company",
        ]
        if sub_brand_id is not None:
            visibility_conditions.append(
                and_(
                    Notification.target_scope == "sub_brand",
                    Notification.sub_brand_id == sub_brand_id,
                )
            )
        visibility_conditions.append(
            and_(
                Notification.target_scope == "individual",
                Notification.target_user_id == user_id,
            )
        )

        visibility_filter = or_(*visibility_conditions)

        # Build query
        query = select(Notification).where(*base_filters, visibility_filter)

        # Unread filter: user_id NOT in read_by JSONB array
        # Use func.cast with literal to ensure proper JSONB comparison
        unread_filter = not_(
            Notification.read_by.op("@>")(
                func.cast(literal(f'["{user_id_str}"]'), JSONB)
            )
        )

        if unread_only:
            query = query.where(unread_filter)

        # Total count (with current filters)
        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        # Unread count (all unread, not just this page)
        unread_query = select(func.count()).select_from(
            select(Notification.id)
            .where(*base_filters, visibility_filter, unread_filter)
            .subquery()
        )
        unread_count = await self.db.scalar(unread_query) or 0

        # Paginate
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
        """Add user_id to the read_by JSONB array if not already present.

        Idempotent — calling twice for the same user has no effect.
        """
        notification = await self._get_notification(notification_id, company_id)

        # Check if already read
        read_by = notification.read_by or []
        if user_id not in read_by:
            # Append using PostgreSQL JSONB concatenation
            notification.read_by = read_by + [user_id]  # type: ignore[assignment]
            await self.db.flush()
            await self.db.refresh(notification)

        return notification

    async def mark_all_as_read(
        self,
        user_id: str,
        company_id: UUID,
        sub_brand_id: UUID | None,
    ) -> int:
        """Mark all unread notifications as read for the given user.

        Returns the count of newly marked notifications.
        """
        now = datetime.now(UTC)
        user_id_str = user_id

        # Same visibility logic as list_notifications_for_user
        base_filters = [
            Notification.company_id == company_id,
            Notification.is_active.is_(True),
            (Notification.expires_at.is_(None) | (Notification.expires_at > now)),
        ]

        visibility_conditions = [
            Notification.target_scope == "company",
        ]
        if sub_brand_id is not None:
            visibility_conditions.append(
                and_(
                    Notification.target_scope == "sub_brand",
                    Notification.sub_brand_id == sub_brand_id,
                )
            )
        visibility_filter = or_(*visibility_conditions)

        # Find unread notifications
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
        sub_brand_id: UUID | None,
        page: int = 1,
        per_page: int = 20,
        notification_type: str | None = None,
    ) -> tuple[list[Notification], int]:
        """Admin view: list all notifications including expired and inactive."""
        query = select(Notification).where(Notification.company_id == company_id)

        if sub_brand_id is not None:
            query = query.where(Notification.sub_brand_id == sub_brand_id)

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
        notification = await self._get_notification(notification_id, company_id)
        notification.is_active = False  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(notification)

        logger.info(
            "notification_deactivated",
            notification_id=str(notification_id),
        )
        return notification

    async def _get_notification(
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
