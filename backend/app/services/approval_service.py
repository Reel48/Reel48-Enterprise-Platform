"""Unified approval workflow service.

Orchestrates approval_requests/approval_rules records and delegates
entity-specific transitions to ProductService, CatalogService,
OrderService, and BulkOrderService.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.approval_request import ApprovalRequest
from app.models.approval_rule import ApprovalRule
from app.models.bulk_order import BulkOrder
from app.models.catalog import Catalog
from app.models.company import Company
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.approval import ApprovalRuleCreate, ApprovalRuleUpdate
from app.services.bulk_order_service import BulkOrderService
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService
from app.services.product_service import ProductService

if TYPE_CHECKING:
    from app.services.email_service import EmailService

logger = structlog.get_logger()

# Role hierarchy for threshold checks (higher index = more authority)
_ROLE_RANK: dict[str, int] = {
    "employee": 0,
    "regional_manager": 1,
    "sub_brand_admin": 2,
    "corporate_admin": 3,
    "reel48_admin": 4,
}

VALID_ENTITY_TYPES = {"product", "catalog", "order", "bulk_order"}


class ApprovalService:
    def __init__(
        self,
        db: AsyncSession,
        email_service: EmailService | None = None,
    ):
        self.db = db
        self._email_service = email_service

    # ------------------------------------------------------------------
    # Submission recording
    # ------------------------------------------------------------------

    async def record_submission(
        self,
        entity_type: str,
        entity_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        requested_by: UUID,
    ) -> ApprovalRequest:
        """Record that an entity has been submitted for approval.

        Called by existing submit endpoints (product submit, catalog submit,
        bulk order submit). For orders, called at order creation time
        (orders start as 'pending' which IS their approval request).
        """
        approval_request = ApprovalRequest(
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            entity_type=entity_type,
            entity_id=entity_id,
            requested_by=requested_by,
            status="pending",
            requested_at=datetime.now(UTC),
        )
        self.db.add(approval_request)
        await self.db.flush()
        await self.db.refresh(approval_request)

        # Send notification to potential approvers (non-blocking)
        await self._notify_approvers(
            entity_type=entity_type,
            entity_id=entity_id,
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            requested_by=requested_by,
        )

        return approval_request

    # ------------------------------------------------------------------
    # Decision processing
    # ------------------------------------------------------------------

    async def process_decision(
        self,
        approval_request_id: UUID,
        decided_by: UUID,
        decision: str,
        decision_notes: str | None,
        role: str,
        company_id: UUID | None,
    ) -> ApprovalRequest:
        """Process an approval or rejection decision.

        Steps:
        1. Load the approval_request, verify it's still pending
        2. Check approval rules (role sufficient?)
        3. Call the appropriate entity service method
        4. Update the approval_request with decision details
        5. Return the updated approval_request
        """
        if decision not in ("approved", "rejected"):
            raise ForbiddenError("Decision must be 'approved' or 'rejected'")

        # 1. Load approval request
        ar = await self.get_approval_request(approval_request_id)
        if ar.status != "pending":
            raise ForbiddenError(
                f"Cannot process a decision on an approval request with status '{ar.status}'"
            )

        # 2. Check approval rules
        has_authority = await self.check_approval_rules(
            entity_type=ar.entity_type,
            entity_id=ar.entity_id,
            company_id=ar.company_id,
            role=role,
        )
        if not has_authority:
            raise ForbiddenError(
                "Your role does not meet the required approval authority for this entity"
            )

        # 3. Delegate to entity-specific service
        await self._delegate_to_entity_service(
            entity_type=ar.entity_type,
            entity_id=ar.entity_id,
            decision=decision,
            decided_by=decided_by,
            company_id=company_id,
        )

        # 4. Update approval request
        ar.decided_by = decided_by  # type: ignore[assignment]
        ar.decided_at = datetime.now(UTC)  # type: ignore[assignment]
        ar.status = decision  # type: ignore[assignment]
        ar.decision_notes = decision_notes  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(ar)

        # 5. Send decision notification to submitter (non-blocking)
        await self._notify_submitter(
            entity_type=ar.entity_type,
            entity_id=ar.entity_id,
            requested_by=ar.requested_by,
            decided_by=decided_by,
            decision=decision,
            decision_notes=decision_notes,
        )

        return ar

    async def _delegate_to_entity_service(
        self,
        entity_type: str,
        entity_id: UUID,
        decision: str,
        decided_by: UUID,
        company_id: UUID | None,
    ) -> None:
        """Call the appropriate entity service approve/reject method."""
        if entity_type == "product":
            svc = ProductService(self.db)
            if decision == "approved":
                await svc.approve_product(entity_id, decided_by)
            else:
                await svc.reject_product(entity_id)

        elif entity_type == "catalog":
            svc_cat = CatalogService(self.db)
            if decision == "approved":
                await svc_cat.approve_catalog(entity_id, decided_by)
            else:
                await svc_cat.reject_catalog(entity_id)

        elif entity_type == "order":
            svc_ord = OrderService(self.db)
            if decision == "approved":
                await svc_ord.approve_order(entity_id, company_id)
            else:
                # Orders don't have a reject method; cancel with decided_by
                await svc_ord.cancel_order(
                    entity_id, company_id, decided_by, is_manager_or_above=True
                )

        elif entity_type == "bulk_order":
            svc_blk = BulkOrderService(self.db)
            if decision == "approved":
                await svc_blk.approve_bulk_order(entity_id, company_id, decided_by)
            else:
                # Bulk orders don't have a reject method; cancel with decided_by
                await svc_blk.cancel_bulk_order(
                    entity_id, company_id, decided_by, is_manager_or_above=True
                )

    # ------------------------------------------------------------------
    # Email notification helpers
    # ------------------------------------------------------------------

    async def _notify_approvers(
        self,
        entity_type: str,
        entity_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        requested_by: UUID,
    ) -> None:
        """Send approval-needed notifications to potential approvers.

        For products/catalogs: notify reel48_admin users.
        For orders/bulk_orders: notify manager_or_above in the same company/sub-brand.
        Failures are logged but do not block the approval request creation.
        """
        if self._email_service is None:
            return

        try:
            entity_name, _ = await self.get_entity_summary(entity_type, entity_id)

            # Look up submitter name
            submitter = await self.db.execute(
                select(User.full_name).where(User.id == requested_by)
            )
            submitter_name = submitter.scalar_one_or_none() or "Unknown"

            # Determine approver recipients
            approver_emails = await self._get_approver_emails(
                entity_type, company_id, sub_brand_id
            )

            approval_url = (
                f"{settings.FRONTEND_BASE_URL}/approvals"
            )

            for email in approver_emails:
                try:
                    await self._email_service.send_approval_needed_notification(
                        to_email=email,
                        entity_type=entity_type,
                        entity_name=entity_name,
                        submitted_by_name=submitter_name,
                        approval_url=approval_url,
                    )
                except Exception:
                    logger.warning(
                        "approval_needed_email_failed",
                        to_email=email,
                        entity_type=entity_type,
                        entity_id=str(entity_id),
                        exc_info=True,
                    )
        except Exception:
            logger.warning(
                "approval_notification_dispatch_failed",
                entity_type=entity_type,
                entity_id=str(entity_id),
                exc_info=True,
            )

    async def _notify_submitter(
        self,
        entity_type: str,
        entity_id: UUID,
        requested_by: UUID,
        decided_by: UUID,
        decision: str,
        decision_notes: str | None,
    ) -> None:
        """Send a decision notification to the original submitter.

        Failures are logged but do not block the decision processing.
        """
        if self._email_service is None:
            return

        try:
            entity_name, _ = await self.get_entity_summary(entity_type, entity_id)

            # Look up submitter email
            submitter_result = await self.db.execute(
                select(User.email).where(User.id == requested_by)
            )
            submitter_email = submitter_result.scalar_one_or_none()
            if not submitter_email:
                logger.warning(
                    "submitter_email_not_found",
                    requested_by=str(requested_by),
                )
                return

            # Look up decider name
            decider_result = await self.db.execute(
                select(User.full_name).where(User.id == decided_by)
            )
            decider_name = decider_result.scalar_one_or_none() or "Unknown"

            await self._email_service.send_approval_decision_notification(
                to_email=submitter_email,
                entity_type=entity_type,
                entity_name=entity_name,
                decision=decision,
                decided_by_name=decider_name,
                decision_notes=decision_notes,
            )
        except Exception:
            logger.warning(
                "decision_notification_failed",
                entity_type=entity_type,
                entity_id=str(entity_id),
                decision=decision,
                exc_info=True,
            )

    async def _get_approver_emails(
        self,
        entity_type: str,
        company_id: UUID,
        sub_brand_id: UUID | None,
    ) -> list[str]:
        """Determine who should receive approval-needed notifications.

        Products/catalogs: reel48_admin users (platform-level approval).
        Orders/bulk_orders: manager_or_above in the same company/sub-brand.
        """
        if entity_type in ("product", "catalog"):
            # Platform admins approve products and catalogs
            result = await self.db.execute(
                select(User.email).where(
                    User.role == "reel48_admin",
                    User.is_active.is_(True),
                )
            )
        else:
            # Managers and admins in the same company/sub-brand
            manager_roles = [
                "regional_manager",
                "sub_brand_admin",
                "corporate_admin",
            ]
            query = select(User.email).where(
                User.company_id == company_id,
                User.role.in_(manager_roles),
                User.is_active.is_(True),
            )
            if sub_brand_id is not None:
                # Include users in the same sub-brand OR corporate admins (sub_brand_id=NULL)
                query = query.where(
                    (User.sub_brand_id == sub_brand_id)
                    | (User.sub_brand_id.is_(None))
                )
            result = await self.db.execute(query)

        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Approval rules evaluation
    # ------------------------------------------------------------------

    async def check_approval_rules(
        self,
        entity_type: str,
        entity_id: UUID,
        company_id: UUID,
        role: str,
    ) -> bool:
        """Check if the user's role satisfies any active approval rules.

        For products and catalogs: always requires reel48_admin (hardcoded,
        no configurable rules -- platform-level approvals).

        For orders and bulk_orders: check the approval_rules table for the
        company. If an amount_threshold rule exists and the entity's total_amount
        exceeds it, the user must have at least the required_role.

        Returns True if the user has sufficient authority, False otherwise.
        """
        # Products and catalogs: hardcoded reel48_admin requirement
        if entity_type in ("product", "catalog"):
            return role == "reel48_admin"

        # Orders and bulk_orders: check configurable rules
        # First, get the entity's total_amount
        entity_amount = await self._get_entity_amount(entity_type, entity_id)

        # Look up active rule for this company + entity_type
        result = await self.db.execute(
            select(ApprovalRule).where(
                ApprovalRule.company_id == company_id,
                ApprovalRule.entity_type == entity_type,
                ApprovalRule.rule_type == "amount_threshold",
                ApprovalRule.is_active.is_(True),
            )
        )
        rule = result.scalar_one_or_none()

        if rule is None:
            # No active rule: default behavior — manager_or_above can approve
            return _ROLE_RANK.get(role, 0) >= _ROLE_RANK["regional_manager"]

        # Rule exists: check if amount exceeds threshold
        if entity_amount is not None and rule.threshold_amount is not None:
            if entity_amount > rule.threshold_amount:
                # Amount exceeds threshold: require at least the rule's required_role
                required_rank = _ROLE_RANK.get(rule.required_role, 0)
                user_rank = _ROLE_RANK.get(role, 0)
                return user_rank >= required_rank

        # Amount is below threshold (or no threshold/amount): default behavior
        return _ROLE_RANK.get(role, 0) >= _ROLE_RANK["regional_manager"]

    async def _get_entity_amount(
        self, entity_type: str, entity_id: UUID
    ) -> Decimal | None:
        """Get the total_amount for an order or bulk_order."""
        if entity_type == "order":
            result = await self.db.execute(
                select(Order.total_amount).where(Order.id == entity_id)
            )
            return result.scalar_one_or_none()
        elif entity_type == "bulk_order":
            result = await self.db.execute(
                select(BulkOrder.total_amount).where(BulkOrder.id == entity_id)
            )
            return result.scalar_one_or_none()
        return None

    # ------------------------------------------------------------------
    # Queue queries
    # ------------------------------------------------------------------

    async def list_pending(
        self,
        company_id: UUID | None,
        sub_brand_id: UUID | None,
        role: str,
        entity_type_filter: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ApprovalRequest], int]:
        """List pending approval requests visible to the current user.

        Visibility:
        - reel48_admin: all pending across all companies
        - corporate_admin: all pending in their company
        - sub_brand_admin: pending in their sub-brand
        - regional_manager: pending orders/bulk_orders in their sub-brand
        """
        query = select(ApprovalRequest).where(ApprovalRequest.status == "pending")

        # Company scoping
        if company_id is not None:
            query = query.where(ApprovalRequest.company_id == company_id)

        # Sub-brand scoping
        if sub_brand_id is not None:
            query = query.where(ApprovalRequest.sub_brand_id == sub_brand_id)

        # Regional managers can only see orders and bulk_orders
        if role == "regional_manager":
            query = query.where(
                ApprovalRequest.entity_type.in_(["order", "bulk_order"])
            )

        # Optional entity type filter
        if entity_type_filter is not None:
            query = query.where(ApprovalRequest.entity_type == entity_type_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.order_by(ApprovalRequest.requested_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def list_history(
        self,
        company_id: UUID | None,
        sub_brand_id: UUID | None,
        entity_type_filter: str | None = None,
        status_filter: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ApprovalRequest], int]:
        """List decided (approved/rejected) approval requests.
        Same visibility rules as list_pending (minus the role-based entity filter)."""
        if status_filter and status_filter in ("approved", "rejected"):
            query = select(ApprovalRequest).where(
                ApprovalRequest.status == status_filter
            )
        else:
            query = select(ApprovalRequest).where(
                ApprovalRequest.status.in_(["approved", "rejected"])
            )

        if company_id is not None:
            query = query.where(ApprovalRequest.company_id == company_id)
        if sub_brand_id is not None:
            query = query.where(ApprovalRequest.sub_brand_id == sub_brand_id)
        if entity_type_filter is not None:
            query = query.where(ApprovalRequest.entity_type == entity_type_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.order_by(ApprovalRequest.decided_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_approval_request(
        self, approval_request_id: UUID
    ) -> ApprovalRequest:
        """Get a single approval request by ID."""
        result = await self.db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_request_id)
        )
        ar = result.scalar_one_or_none()
        if ar is None:
            raise NotFoundError("ApprovalRequest", str(approval_request_id))
        return ar

    async def find_by_entity(
        self, entity_type: str, entity_id: UUID
    ) -> ApprovalRequest | None:
        """Find a pending approval request by entity_type + entity_id.

        Used to sync direct platform approve/reject endpoints with the
        approval_requests audit trail. Returns None if no pending request exists.
        """
        result = await self.db.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.entity_type == entity_type,
                ApprovalRequest.entity_id == entity_id,
                ApprovalRequest.status == "pending",
            )
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Approval rules management
    # ------------------------------------------------------------------

    async def create_rule(
        self,
        data: ApprovalRuleCreate,
        company_id: UUID,
        created_by: UUID,
    ) -> ApprovalRule:
        """Create an approval rule. One active rule per (company, entity_type, rule_type)."""
        # Check for duplicate active rule
        result = await self.db.execute(
            select(ApprovalRule).where(
                ApprovalRule.company_id == company_id,
                ApprovalRule.entity_type == data.entity_type,
                ApprovalRule.rule_type == data.rule_type,
                ApprovalRule.is_active.is_(True),
            )
        )
        if result.scalar_one_or_none() is not None:
            raise ConflictError(
                f"An active {data.rule_type} rule for {data.entity_type} already exists"
            )

        rule = ApprovalRule(
            company_id=company_id,
            entity_type=data.entity_type,
            rule_type=data.rule_type,
            threshold_amount=data.threshold_amount,
            required_role=data.required_role,
            created_by=created_by,
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def update_rule(
        self,
        rule_id: UUID,
        data: ApprovalRuleUpdate,
        company_id: UUID,
    ) -> ApprovalRule:
        """Update an existing approval rule."""
        rule = await self._get_rule(rule_id, company_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def list_rules(
        self,
        company_id: UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ApprovalRule], int]:
        """List approval rules for a company."""
        query = select(ApprovalRule).where(ApprovalRule.company_id == company_id)
        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.order_by(ApprovalRule.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def deactivate_rule(
        self,
        rule_id: UUID,
        company_id: UUID,
    ) -> ApprovalRule:
        """Soft-deactivate a rule (is_active = false)."""
        rule = await self._get_rule(rule_id, company_id)
        rule.is_active = False  # type: ignore[assignment]
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def list_all_rules(
        self,
        company_id_filter: UUID | None = None,
        entity_type_filter: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ApprovalRule], int]:
        """List approval rules across ALL companies. For reel48_admin only."""
        query = select(ApprovalRule)
        if company_id_filter is not None:
            query = query.where(ApprovalRule.company_id == company_id_filter)
        if entity_type_filter is not None:
            query = query.where(ApprovalRule.entity_type == entity_type_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.order_by(ApprovalRule.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def _get_rule(self, rule_id: UUID, company_id: UUID) -> ApprovalRule:
        """Fetch a single approval rule scoped to a company."""
        result = await self.db.execute(
            select(ApprovalRule).where(
                ApprovalRule.id == rule_id,
                ApprovalRule.company_id == company_id,
            )
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise NotFoundError("ApprovalRule", str(rule_id))
        return rule

    # ------------------------------------------------------------------
    # Entity name/amount helpers (for ApprovalQueueItem display)
    # ------------------------------------------------------------------

    async def get_entity_summary(
        self, entity_type: str, entity_id: UUID
    ) -> tuple[str, float | None]:
        """Return (entity_name, entity_amount) for queue display."""
        if entity_type == "product":
            result = await self.db.execute(
                select(Product.name).where(Product.id == entity_id)
            )
            name = result.scalar_one_or_none()
            return name or "Unknown Product", None

        elif entity_type == "catalog":
            result = await self.db.execute(
                select(Catalog.name).where(Catalog.id == entity_id)
            )
            name = result.scalar_one_or_none()
            return name or "Unknown Catalog", None

        elif entity_type == "order":
            result = await self.db.execute(
                select(Order.order_number, Order.total_amount).where(
                    Order.id == entity_id
                )
            )
            row = result.one_or_none()
            if row:
                return row[0], float(row[1]) if row[1] else None
            return "Unknown Order", None

        elif entity_type == "bulk_order":
            result = await self.db.execute(
                select(BulkOrder.title, BulkOrder.total_amount).where(
                    BulkOrder.id == entity_id
                )
            )
            row = result.one_or_none()
            if row:
                return row[0], float(row[1]) if row[1] else None
            return "Unknown Bulk Order", None

        return "Unknown", None

    # ------------------------------------------------------------------
    # Platform admin queries (cross-company)
    # ------------------------------------------------------------------

    async def list_all_approvals(
        self,
        status_filter: str | None = None,
        entity_type_filter: str | None = None,
        company_id_filter: UUID | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ApprovalRequest], int]:
        """List approval requests across ALL companies. For reel48_admin only."""
        query = select(ApprovalRequest)

        if status_filter is not None:
            query = query.where(ApprovalRequest.status == status_filter)
        if entity_type_filter is not None:
            query = query.where(ApprovalRequest.entity_type == entity_type_filter)
        if company_id_filter is not None:
            query = query.where(ApprovalRequest.company_id == company_id_filter)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        query = query.order_by(ApprovalRequest.requested_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_approval_summary(self) -> dict:
        """Aggregate pending approval counts by entity_type and company."""
        # Total pending count
        pending_count = await self.db.scalar(
            select(func.count()).where(ApprovalRequest.status == "pending")
        ) or 0

        # Pending by entity_type
        type_rows = (
            await self.db.execute(
                select(
                    ApprovalRequest.entity_type,
                    func.count().label("cnt"),
                )
                .where(ApprovalRequest.status == "pending")
                .group_by(ApprovalRequest.entity_type)
            )
        ).all()
        by_entity_type = {row[0]: row[1] for row in type_rows}

        # Pending by company (join to get company name)
        company_rows = (
            await self.db.execute(
                select(
                    ApprovalRequest.company_id,
                    Company.name,
                    func.count().label("cnt"),
                )
                .join(Company, Company.id == ApprovalRequest.company_id)
                .where(ApprovalRequest.status == "pending")
                .group_by(ApprovalRequest.company_id, Company.name)
            )
        ).all()
        by_company = [
            {
                "company_id": str(row[0]),
                "company_name": row[1],
                "pending_count": row[2],
            }
            for row in company_rows
        ]

        return {
            "pending_count": pending_count,
            "by_entity_type": by_entity_type,
            "by_company": by_company,
        }
