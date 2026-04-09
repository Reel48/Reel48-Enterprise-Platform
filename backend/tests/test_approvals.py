"""Tests for Module 6 Phase 2: Approval Service (schemas, service, rules, isolation)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.approval_request import ApprovalRequest
from app.models.approval_rule import ApprovalRule
from app.models.bulk_order import BulkOrder
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.models.product import Product
from app.schemas.approval import ApprovalRuleCreate, ApprovalRuleUpdate
from app.services.approval_service import ApprovalService
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_submitted_product(
    db: AsyncSession, company_id, sub_brand_id, created_by
) -> Product:
    """Create a product in 'submitted' status for approval testing."""
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Product {uuid4().hex[:6]}",
        description="Test product for approval",
        sku=f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=Decimal("29.99"),
        sizes=["S", "M", "L"],
        decoration_options=[],
        image_urls=[],
        status="submitted",
        created_by=created_by,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def _create_submitted_catalog(
    db: AsyncSession, company_id, sub_brand_id, created_by
) -> Catalog:
    """Create a catalog in 'submitted' status for approval testing."""
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Catalog {uuid4().hex[:6]}",
        description="Test catalog for approval",
        slug=f"catalog-{uuid4().hex[:6]}",
        payment_model="self_service",
        status="submitted",
        created_by=created_by,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)

    # Add an active product so catalog approval doesn't fail validation
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Catalog Product {uuid4().hex[:6]}",
        sku=f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=Decimal("19.99"),
        sizes=[],
        decoration_options=[],
        image_urls=[],
        status="active",
        created_by=created_by,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)

    cp = CatalogProduct(
        catalog_id=catalog.id,
        product_id=product.id,
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        display_order=0,
    )
    db.add(cp)
    await db.flush()

    return catalog


async def _create_catalog_stub(
    db: AsyncSession, company_id, sub_brand_id, created_by,
) -> Catalog:
    """Create a minimal active catalog for FK satisfaction."""
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Stub Catalog {uuid4().hex[:6]}",
        slug=f"stub-catalog-{uuid4().hex[:6]}",
        payment_model="self_service",
        status="active",
        created_by=created_by,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _create_pending_order(
    db: AsyncSession, company_id, sub_brand_id, user_id, created_by=None,
    total_amount=Decimal("100.00"),
) -> Order:
    """Create an order in 'pending' status for approval testing."""
    # Ensure we have a real catalog for the FK
    catalog = await _create_catalog_stub(
        db, company_id, sub_brand_id, created_by or user_id,
    )
    order = Order(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        user_id=user_id,
        catalog_id=catalog.id,
        order_number=f"ORD-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}",
        status="pending",
        subtotal=total_amount,
        total_amount=total_amount,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return order


async def _create_submitted_bulk_order(
    db: AsyncSession, company_id, sub_brand_id, created_by, total_amount=Decimal("500.00")
) -> BulkOrder:
    """Create a bulk order in 'submitted' status for approval testing."""
    catalog = await _create_catalog_stub(db, company_id, sub_brand_id, created_by)
    bulk_order = BulkOrder(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        catalog_id=catalog.id,
        created_by=created_by,
        title=f"Bulk Order {uuid4().hex[:6]}",
        order_number=f"BLK-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}",
        status="submitted",
        total_items=10,
        total_amount=total_amount,
        submitted_at=datetime.now(UTC),
    )
    db.add(bulk_order)
    await db.flush()
    await db.refresh(bulk_order)
    return bulk_order


# ===========================================================================
# Functional Tests: ApprovalRequest Recording
# ===========================================================================


class TestRecordSubmission:
    async def test_record_submission_creates_approval_request(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin
    ):
        """Create an approval_request record and verify all fields."""
        company, brand_a1, _a2 = company_a
        product = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        svc = ApprovalService(admin_db_session)
        ar = await svc.record_submission(
            entity_type="product",
            entity_id=product.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )

        assert ar.id is not None
        assert ar.entity_type == "product"
        assert ar.entity_id == product.id
        assert ar.company_id == company.id
        assert ar.sub_brand_id == brand_a1.id
        assert ar.requested_by == user_a1_admin.id
        assert ar.status == "pending"
        assert ar.decided_by is None
        assert ar.decided_at is None
        assert ar.decision_notes is None
        assert ar.requested_at is not None

    async def test_record_submission_for_order(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee
    ):
        """Record an order submission (orders start as pending)."""
        company, brand_a1, _a2 = company_a
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        svc = ApprovalService(admin_db_session)
        ar = await svc.record_submission(
            entity_type="order",
            entity_id=order.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        assert ar.entity_type == "order"
        assert ar.entity_id == order.id
        assert ar.status == "pending"


# ===========================================================================
# Functional Tests: Decision Processing
# ===========================================================================


class TestProcessDecision:
    async def test_approve_product_via_approval_service(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
        reel48_admin_user,
    ):
        """Process an approval decision and verify status, decided_by, decided_at."""
        company, brand_a1, _a2 = company_a
        product = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        svc = ApprovalService(admin_db_session)
        ar = await svc.record_submission(
            entity_type="product",
            entity_id=product.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )

        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=reel48_admin_user.id,
            decision="approved",
            decision_notes="Looks good!",
            role="reel48_admin",
            company_id=None,
        )

        assert result.status == "approved"
        assert result.decided_by == reel48_admin_user.id
        assert result.decided_at is not None
        assert result.decision_notes == "Looks good!"

    async def test_reject_product_via_approval_service(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
        reel48_admin_user,
    ):
        """Process a rejection decision and verify status + notes."""
        company, brand_a1, _a2 = company_a
        product = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        svc = ApprovalService(admin_db_session)
        ar = await svc.record_submission(
            entity_type="product",
            entity_id=product.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )

        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=reel48_admin_user.id,
            decision="rejected",
            decision_notes="Needs better description",
            role="reel48_admin",
            company_id=None,
        )

        assert result.status == "rejected"
        assert result.decision_notes == "Needs better description"

    async def test_cannot_decide_already_decided_request(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
        reel48_admin_user,
    ):
        """Cannot approve/reject an already-decided request (returns 403)."""
        company, brand_a1, _a2 = company_a
        product = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        svc = ApprovalService(admin_db_session)
        ar = await svc.record_submission(
            entity_type="product",
            entity_id=product.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )

        # First decision succeeds
        await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=reel48_admin_user.id,
            decision="approved",
            decision_notes=None,
            role="reel48_admin",
            company_id=None,
        )

        # Second decision fails
        with pytest.raises(ForbiddenError, match="Cannot process a decision"):
            await svc.process_decision(
                approval_request_id=ar.id,
                decided_by=reel48_admin_user.id,
                decision="rejected",
                decision_notes=None,
                role="reel48_admin",
                company_id=None,
            )

    async def test_approve_order_via_approval_service(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
        user_a1_manager,
    ):
        """Approve a pending order through the approval service."""
        company, brand_a1, _a2 = company_a
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        svc = ApprovalService(admin_db_session)
        ar = await svc.record_submission(
            entity_type="order",
            entity_id=order.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=user_a1_manager.id,
            decision="approved",
            decision_notes=None,
            role="regional_manager",
            company_id=company.id,
        )

        assert result.status == "approved"
        # Verify the underlying order status was also updated
        await admin_db_session.refresh(order)
        assert order.status == "approved"

    async def test_reject_order_cancels_it(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
        user_a1_manager,
    ):
        """Rejecting an order cancels the underlying order."""
        company, brand_a1, _a2 = company_a
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        svc = ApprovalService(admin_db_session)
        ar = await svc.record_submission(
            entity_type="order",
            entity_id=order.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=user_a1_manager.id,
            decision="rejected",
            decision_notes="Budget exceeded",
            role="regional_manager",
            company_id=company.id,
        )

        assert result.status == "rejected"
        await admin_db_session.refresh(order)
        assert order.status == "cancelled"

    async def test_approve_bulk_order_via_approval_service(
        self, admin_db_session: AsyncSession, company_a, user_a1_manager,
    ):
        """Approve a submitted bulk order through the approval service."""
        company, brand_a1, _a2 = company_a
        bulk_order = await _create_submitted_bulk_order(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        svc = ApprovalService(admin_db_session)
        ar = await svc.record_submission(
            entity_type="bulk_order",
            entity_id=bulk_order.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            requested_by=user_a1_manager.id,
        )

        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=user_a1_manager.id,
            decision="approved",
            decision_notes=None,
            role="regional_manager",
            company_id=company.id,
        )

        assert result.status == "approved"
        await admin_db_session.refresh(bulk_order)
        assert bulk_order.status == "approved"

    async def test_not_found_approval_request(
        self, admin_db_session: AsyncSession,
    ):
        """Getting a non-existent approval request raises NotFoundError."""
        svc = ApprovalService(admin_db_session)
        with pytest.raises(NotFoundError):
            await svc.get_approval_request(uuid4())


# ===========================================================================
# Approval Rules Tests
# ===========================================================================


class TestApprovalRules:
    async def test_create_approval_rule(
        self, admin_db_session: AsyncSession, company_a, user_a_corporate_admin,
    ):
        """Create an approval rule with amount threshold."""
        company, _a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        rule = await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order",
                rule_type="amount_threshold",
                threshold_amount=500.00,
                required_role="corporate_admin",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )

        assert rule.id is not None
        assert rule.company_id == company.id
        assert rule.entity_type == "order"
        assert rule.rule_type == "amount_threshold"
        assert float(rule.threshold_amount) == 500.00
        assert rule.required_role == "corporate_admin"
        assert rule.is_active is True

    async def test_duplicate_rule_raises_conflict(
        self, admin_db_session: AsyncSession, company_a, user_a_corporate_admin,
    ):
        """Cannot create duplicate (company, entity_type, rule_type) combination."""
        company, _a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="bulk_order",
                rule_type="amount_threshold",
                threshold_amount=1000.00,
                required_role="corporate_admin",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )

        with pytest.raises(ConflictError, match="already exists"):
            await svc.create_rule(
                data=ApprovalRuleCreate(
                    entity_type="bulk_order",
                    rule_type="amount_threshold",
                    threshold_amount=2000.00,
                    required_role="sub_brand_admin",
                ),
                company_id=company.id,
                created_by=user_a_corporate_admin.id,
            )

    async def test_deactivate_rule(
        self, admin_db_session: AsyncSession, company_a, user_a_corporate_admin,
    ):
        """Deactivate an approval rule."""
        company, _a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        rule = await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order",
                rule_type="amount_threshold",
                threshold_amount=200.00,
                required_role="sub_brand_admin",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )

        deactivated = await svc.deactivate_rule(rule.id, company.id)
        assert deactivated.is_active is False

    async def test_update_rule(
        self, admin_db_session: AsyncSession, company_a, user_a_corporate_admin,
    ):
        """Update an existing approval rule."""
        company, _a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        rule = await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order",
                rule_type="amount_threshold",
                threshold_amount=300.00,
                required_role="sub_brand_admin",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )

        updated = await svc.update_rule(
            rule_id=rule.id,
            data=ApprovalRuleUpdate(threshold_amount=750.00, required_role="corporate_admin"),
            company_id=company.id,
        )

        assert float(updated.threshold_amount) == 750.00
        assert updated.required_role == "corporate_admin"

    async def test_list_rules(
        self, admin_db_session: AsyncSession, company_a, user_a_corporate_admin,
    ):
        """List approval rules for a company."""
        company, _a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order",
                rule_type="amount_threshold",
                threshold_amount=100.00,
                required_role="regional_manager",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )

        rules, total = await svc.list_rules(company.id)
        assert total >= 1
        assert any(r.entity_type == "order" for r in rules)


# ===========================================================================
# Approval Rules Enforcement Tests
# ===========================================================================


class TestApprovalRulesEnforcement:
    async def test_order_below_threshold_manager_can_approve(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
        user_a1_manager, user_a_corporate_admin,
    ):
        """Order below threshold: regional_manager can approve."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        # Create rule: orders over $500 require corporate_admin
        await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order",
                rule_type="amount_threshold",
                threshold_amount=500.00,
                required_role="corporate_admin",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )

        # Create order for $100 (below threshold)
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
            total_amount=Decimal("100.00"),
        )

        ar = await svc.record_submission(
            entity_type="order", entity_id=order.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        # Manager should be able to approve (below threshold)
        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=user_a1_manager.id,
            decision="approved",
            decision_notes=None,
            role="regional_manager",
            company_id=company.id,
        )
        assert result.status == "approved"

    async def test_order_above_threshold_manager_cannot_approve(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
        user_a1_manager, user_a_corporate_admin,
    ):
        """Order above threshold with required_role=corporate_admin: manager cannot approve."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        # Create rule: orders over $500 require corporate_admin
        await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order",
                rule_type="amount_threshold",
                threshold_amount=500.00,
                required_role="corporate_admin",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )

        # Create order for $1000 (above threshold)
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
            total_amount=Decimal("1000.00"),
        )

        ar = await svc.record_submission(
            entity_type="order", entity_id=order.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        # Manager should be denied (above threshold, needs corporate_admin)
        with pytest.raises(ForbiddenError, match="does not meet"):
            await svc.process_decision(
                approval_request_id=ar.id,
                decided_by=user_a1_manager.id,
                decision="approved",
                decision_notes=None,
                role="regional_manager",
                company_id=company.id,
            )

    async def test_order_above_threshold_corporate_admin_can_approve(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
        user_a_corporate_admin,
    ):
        """Order above threshold: corporate_admin CAN approve."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        # Create rule: orders over $500 require corporate_admin
        await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order",
                rule_type="amount_threshold",
                threshold_amount=500.00,
                required_role="corporate_admin",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )

        # Create order for $1000 (above threshold)
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
            total_amount=Decimal("1000.00"),
        )

        ar = await svc.record_submission(
            entity_type="order", entity_id=order.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        # Corporate admin should be able to approve
        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=user_a_corporate_admin.id,
            decision="approved",
            decision_notes=None,
            role="corporate_admin",
            company_id=company.id,
        )
        assert result.status == "approved"

    async def test_no_active_rule_default_manager_can_approve(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
        user_a1_manager,
    ):
        """No active rule: default behavior (manager_or_above for orders)."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
            total_amount=Decimal("5000.00"),
        )

        ar = await svc.record_submission(
            entity_type="order", entity_id=order.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        # No rules exist — manager can approve any amount
        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=user_a1_manager.id,
            decision="approved",
            decision_notes=None,
            role="regional_manager",
            company_id=company.id,
        )
        assert result.status == "approved"

    async def test_deactivated_rule_treated_as_no_rule(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
        user_a1_manager, user_a_corporate_admin,
    ):
        """Deactivated rule: treated as no rule (default behavior)."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        # Create and deactivate a rule
        rule = await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order",
                rule_type="amount_threshold",
                threshold_amount=100.00,
                required_role="corporate_admin",
            ),
            company_id=company.id,
            created_by=user_a_corporate_admin.id,
        )
        await svc.deactivate_rule(rule.id, company.id)

        # Create order for $5000 (would exceed threshold if rule were active)
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
            total_amount=Decimal("5000.00"),
        )

        ar = await svc.record_submission(
            entity_type="order", entity_id=order.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        # Rule is deactivated — manager can approve even large amount
        result = await svc.process_decision(
            approval_request_id=ar.id,
            decided_by=user_a1_manager.id,
            decision="approved",
            decision_notes=None,
            role="regional_manager",
            company_id=company.id,
        )
        assert result.status == "approved"

    async def test_product_requires_reel48_admin(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
    ):
        """Products always require reel48_admin — corporate_admin cannot approve."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        product = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        ar = await svc.record_submission(
            entity_type="product", entity_id=product.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )

        with pytest.raises(ForbiddenError, match="does not meet"):
            await svc.process_decision(
                approval_request_id=ar.id,
                decided_by=user_a1_admin.id,
                decision="approved",
                decision_notes=None,
                role="corporate_admin",
                company_id=company.id,
            )

    async def test_employee_cannot_approve_order(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
    ):
        """Employees cannot approve orders (below minimum role)."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
        )

        ar = await svc.record_submission(
            entity_type="order", entity_id=order.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        with pytest.raises(ForbiddenError, match="does not meet"):
            await svc.process_decision(
                approval_request_id=ar.id,
                decided_by=user_a1_employee.id,
                decision="approved",
                decision_notes=None,
                role="employee",
                company_id=company.id,
            )


# ===========================================================================
# Queue Query Tests
# ===========================================================================


class TestQueueQueries:
    async def test_list_pending_returns_pending_only(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
        reel48_admin_user,
    ):
        """list_pending returns only pending requests."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        p1 = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        p2 = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        ar1 = await svc.record_submission(
            entity_type="product", entity_id=p1.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )
        ar2 = await svc.record_submission(
            entity_type="product", entity_id=p2.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )

        # Approve one
        await svc.process_decision(
            approval_request_id=ar1.id,
            decided_by=reel48_admin_user.id,
            decision="approved",
            decision_notes=None,
            role="reel48_admin",
            company_id=None,
        )

        # List pending — should only have ar2
        pending, total = await svc.list_pending(
            company_id=company.id, sub_brand_id=None,
            role="reel48_admin",
        )
        pending_ids = [p.id for p in pending]
        assert ar2.id in pending_ids
        assert ar1.id not in pending_ids

    async def test_list_history_returns_decided_only(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
        reel48_admin_user,
    ):
        """list_history returns only decided (approved/rejected) requests."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        p1 = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        p2 = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        ar1 = await svc.record_submission(
            entity_type="product", entity_id=p1.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )
        _ar2 = await svc.record_submission(
            entity_type="product", entity_id=p2.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )

        # Approve ar1
        await svc.process_decision(
            approval_request_id=ar1.id,
            decided_by=reel48_admin_user.id,
            decision="approved",
            decision_notes=None,
            role="reel48_admin",
            company_id=None,
        )

        history, total = await svc.list_history(
            company_id=company.id, sub_brand_id=None,
        )
        history_ids = [h.id for h in history]
        assert ar1.id in history_ids

    async def test_list_pending_with_entity_type_filter(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
        user_a1_employee,
    ):
        """list_pending with entity_type_filter returns only matching type."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        product = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
        )

        await svc.record_submission(
            entity_type="product", entity_id=product.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )
        ar_order = await svc.record_submission(
            entity_type="order", entity_id=order.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        # Filter for orders only
        pending, total = await svc.list_pending(
            company_id=company.id, sub_brand_id=None,
            role="reel48_admin",
            entity_type_filter="order",
        )
        assert all(p.entity_type == "order" for p in pending)
        assert ar_order.id in [p.id for p in pending]

    async def test_regional_manager_sees_only_orders_and_bulk_orders(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
        user_a1_employee, user_a1_manager,
    ):
        """Regional manager cannot see product/catalog approval requests."""
        company, brand_a1, _a2 = company_a
        svc = ApprovalService(admin_db_session)

        product = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
        )

        await svc.record_submission(
            entity_type="product", entity_id=product.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )
        await svc.record_submission(
            entity_type="order", entity_id=order.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_employee.id,
        )

        pending, total = await svc.list_pending(
            company_id=company.id, sub_brand_id=brand_a1.id,
            role="regional_manager",
        )
        # Should only see orders, not products
        assert all(p.entity_type in ("order", "bulk_order") for p in pending)


# ===========================================================================
# Entity Summary Tests
# ===========================================================================


class TestEntitySummary:
    async def test_product_summary(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
    ):
        """get_entity_summary returns product name, no amount."""
        company, brand_a1, _a2 = company_a
        product = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        svc = ApprovalService(admin_db_session)
        name, amount = await svc.get_entity_summary("product", product.id)
        assert name == product.name
        assert amount is None

    async def test_order_summary(
        self, admin_db_session: AsyncSession, company_a, user_a1_employee,
    ):
        """get_entity_summary returns order number and total amount."""
        company, brand_a1, _a2 = company_a
        order = await _create_pending_order(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id,
            total_amount=Decimal("250.00"),
        )

        svc = ApprovalService(admin_db_session)
        name, amount = await svc.get_entity_summary("order", order.id)
        assert name == order.order_number
        assert amount == 250.00

    async def test_bulk_order_summary(
        self, admin_db_session: AsyncSession, company_a, user_a1_manager,
    ):
        """get_entity_summary returns bulk order title and total amount."""
        company, brand_a1, _a2 = company_a
        bulk_order = await _create_submitted_bulk_order(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            total_amount=Decimal("1500.00"),
        )

        svc = ApprovalService(admin_db_session)
        name, amount = await svc.get_entity_summary("bulk_order", bulk_order.id)
        assert name == bulk_order.title
        assert amount == 1500.00


# ===========================================================================
# Isolation Tests
# ===========================================================================


class TestIsolation:
    async def test_company_a_cannot_see_company_b_approval_requests(
        self, admin_db_session: AsyncSession, company_a, company_b,
        user_a1_admin, user_b1_employee,
    ):
        """Company A cannot see Company B's approval requests."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b
        svc = ApprovalService(admin_db_session)

        # Create a product in Company A and Company B
        product_a = await _create_submitted_product(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_admin.id
        )
        product_b = Product(
            company_id=company_b_obj.id,
            sub_brand_id=brand_b1.id,
            name="B Product",
            sku=f"SKU-{uuid4().hex[:8].upper()}",
            unit_price=Decimal("10.00"),
            sizes=[], decoration_options=[], image_urls=[],
            status="submitted",
            created_by=user_b1_employee.id,
        )
        admin_db_session.add(product_b)
        await admin_db_session.flush()
        await admin_db_session.refresh(product_b)

        await svc.record_submission(
            entity_type="product", entity_id=product_a.id,
            company_id=company_a_obj.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )
        await svc.record_submission(
            entity_type="product", entity_id=product_b.id,
            company_id=company_b_obj.id, sub_brand_id=brand_b1.id,
            requested_by=user_b1_employee.id,
        )

        # Query as Company A — should only see Company A's requests
        pending_a, _ = await svc.list_pending(
            company_id=company_a_obj.id, sub_brand_id=None,
            role="reel48_admin",
        )
        assert all(p.company_id == company_a_obj.id for p in pending_a)

        # Query as Company B — should only see Company B's requests
        pending_b, _ = await svc.list_pending(
            company_id=company_b_obj.id, sub_brand_id=None,
            role="reel48_admin",
        )
        assert all(p.company_id == company_b_obj.id for p in pending_b)

    async def test_company_a_cannot_see_company_b_approval_rules(
        self, admin_db_session: AsyncSession, company_a, company_b,
        user_a_corporate_admin, user_b1_employee,
    ):
        """Company A cannot see Company B's approval rules."""
        company_a_obj, _a1, _a2 = company_a
        company_b_obj, _b1 = company_b
        svc = ApprovalService(admin_db_session)

        # Create rules for both companies
        await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order", rule_type="amount_threshold",
                threshold_amount=500.00, required_role="corporate_admin",
            ),
            company_id=company_a_obj.id,
            created_by=user_a_corporate_admin.id,
        )

        # For company B, create a user to use as created_by
        await svc.create_rule(
            data=ApprovalRuleCreate(
                entity_type="order", rule_type="amount_threshold",
                threshold_amount=1000.00, required_role="sub_brand_admin",
            ),
            company_id=company_b_obj.id,
            created_by=user_b1_employee.id,
        )

        # List rules for Company A
        rules_a, _ = await svc.list_rules(company_a_obj.id)
        assert all(r.company_id == company_a_obj.id for r in rules_a)

        # List rules for Company B
        rules_b, _ = await svc.list_rules(company_b_obj.id)
        assert all(r.company_id == company_b_obj.id for r in rules_b)

    async def test_sub_brand_a1_admin_cannot_see_a2_requests(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
    ):
        """Sub-brand A1 admin cannot see sub-brand A2's approval requests."""
        company, brand_a1, brand_a2 = company_a
        svc = ApprovalService(admin_db_session)

        # Create requests in both sub-brands
        p1 = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        p2 = Product(
            company_id=company.id, sub_brand_id=brand_a2.id,
            name="A2 Product", sku=f"SKU-{uuid4().hex[:8].upper()}",
            unit_price=Decimal("10.00"),
            sizes=[], decoration_options=[], image_urls=[],
            status="submitted", created_by=user_a1_admin.id,
        )
        admin_db_session.add(p2)
        await admin_db_session.flush()
        await admin_db_session.refresh(p2)

        await svc.record_submission(
            entity_type="product", entity_id=p1.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )
        await svc.record_submission(
            entity_type="product", entity_id=p2.id,
            company_id=company.id, sub_brand_id=brand_a2.id,
            requested_by=user_a1_admin.id,
        )

        # Query scoped to brand A1
        pending_a1, _ = await svc.list_pending(
            company_id=company.id, sub_brand_id=brand_a1.id,
            role="sub_brand_admin",
        )
        assert all(p.sub_brand_id == brand_a1.id for p in pending_a1)

    async def test_corporate_admin_sees_all_sub_brands(
        self, admin_db_session: AsyncSession, company_a, user_a1_admin,
    ):
        """Corporate admin sees approval requests across all sub-brands."""
        company, brand_a1, brand_a2 = company_a
        svc = ApprovalService(admin_db_session)

        p1 = await _create_submitted_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        p2 = Product(
            company_id=company.id, sub_brand_id=brand_a2.id,
            name="A2 Product", sku=f"SKU-{uuid4().hex[:8].upper()}",
            unit_price=Decimal("10.00"),
            sizes=[], decoration_options=[], image_urls=[],
            status="submitted", created_by=user_a1_admin.id,
        )
        admin_db_session.add(p2)
        await admin_db_session.flush()
        await admin_db_session.refresh(p2)

        await svc.record_submission(
            entity_type="product", entity_id=p1.id,
            company_id=company.id, sub_brand_id=brand_a1.id,
            requested_by=user_a1_admin.id,
        )
        await svc.record_submission(
            entity_type="product", entity_id=p2.id,
            company_id=company.id, sub_brand_id=brand_a2.id,
            requested_by=user_a1_admin.id,
        )

        # Corporate admin: sub_brand_id=None → sees all
        pending, total = await svc.list_pending(
            company_id=company.id, sub_brand_id=None,
            role="corporate_admin",
        )
        sub_brand_ids = {p.sub_brand_id for p in pending}
        assert brand_a1.id in sub_brand_ids
        assert brand_a2.id in sub_brand_ids
