"""Tests for Module 6 Phase 5: Approval email notifications via SES.

Verifies that:
- Submitting an entity triggers approval_needed emails to the correct recipients
- Approving/rejecting triggers decision emails to the submitter
- Email failures do not block approval request creation or decision processing
- Full integration flow: submit -> approval_needed email -> approve -> decision email
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_request import ApprovalRequest
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.product import Product
from app.models.user import User
from tests.conftest import MockEmailService, create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_product(
    db: AsyncSession, company_id, sub_brand_id, created_by,
    *, status: str = "draft",
) -> Product:
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Product {uuid4().hex[:6]}",
        sku=f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=Decimal("29.99"),
        sizes=["S", "M", "L"],
        decoration_options=[],
        image_urls=[],
        status=status,
        created_by=created_by,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def _create_catalog_with_product(
    db: AsyncSession, company_id, sub_brand_id, created_by,
) -> tuple[Catalog, Product]:
    """Create an active catalog with one active product (for order creation)."""
    product = await _create_product(
        db, company_id, sub_brand_id, created_by, status="active",
    )
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Catalog {uuid4().hex[:6]}",
        slug=f"catalog-{uuid4().hex[:6]}",
        payment_model="self_service",
        status="active",
        created_by=created_by,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    cp = CatalogProduct(
        catalog_id=catalog.id,
        product_id=product.id,
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        display_order=0,
    )
    db.add(cp)
    await db.flush()
    return catalog, product


async def _create_approval_request(
    db: AsyncSession, entity_type, entity_id, company_id, sub_brand_id,
    requested_by, *, status="pending",
) -> ApprovalRequest:
    ar = ApprovalRequest(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        entity_type=entity_type,
        entity_id=entity_id,
        requested_by=requested_by,
        status=status,
        requested_at=datetime.now(UTC),
    )
    db.add(ar)
    await db.flush()
    await db.refresh(ar)
    return ar


# ===========================================================================
# Submission Notification Tests
# ===========================================================================


class TestSubmissionNotifications:
    """Verify that submitting entities triggers approval_needed emails."""

    async def test_submit_product_sends_approval_needed_to_reel48_admin(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        user_a1_admin_token: str,
        reel48_admin_user,
        mock_email: MockEmailService,
    ):
        """Submitting a product sends approval_needed email to reel48_admin users."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="draft",
        )

        response = await client.post(
            f"/api/v1/products/{product.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200

        # Should have sent at least one approval_needed email
        needed_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_needed"
        ]
        assert len(needed_emails) >= 1
        assert needed_emails[0]["entity_type"] == "product"
        assert needed_emails[0]["to_email"] == reel48_admin_user.email

    async def test_submit_catalog_sends_approval_needed_to_reel48_admin(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        user_a1_admin_token: str,
        reel48_admin_user,
        mock_email: MockEmailService,
    ):
        """Submitting a catalog sends approval_needed email to reel48_admin users."""
        company, brand_a1, _a2 = company_a
        # Create a draft catalog with one active product (submit guard)
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="active",
        )
        catalog = Catalog(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            name=f"Catalog {uuid4().hex[:6]}",
            slug=f"catalog-{uuid4().hex[:6]}",
            payment_model="self_service",
            status="draft",
            created_by=user_a1_admin.id,
        )
        admin_db_session.add(catalog)
        await admin_db_session.flush()
        await admin_db_session.refresh(catalog)
        cp = CatalogProduct(
            catalog_id=catalog.id,
            product_id=product.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            display_order=0,
        )
        admin_db_session.add(cp)
        await admin_db_session.flush()

        response = await client.post(
            f"/api/v1/catalogs/{catalog.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200

        needed_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_needed"
        ]
        assert len(needed_emails) >= 1
        assert needed_emails[0]["entity_type"] == "catalog"

    async def test_create_order_sends_approval_needed_to_managers(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token: str,
        user_a1_manager,
        mock_email: MockEmailService,
    ):
        """Creating an order sends approval_needed email to managers in the sub-brand."""
        company, brand_a1, _a2 = company_a
        catalog, product = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [{
                    "product_id": str(product.id),
                    "quantity": 1,
                    "size": "M",
                }],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201

        needed_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_needed"
        ]
        assert len(needed_emails) >= 1
        assert needed_emails[0]["entity_type"] == "order"
        # Manager in the same sub-brand should be a recipient
        manager_emails = [e["to_email"] for e in needed_emails]
        assert user_a1_manager.email in manager_emails


# ===========================================================================
# Decision Notification Tests
# ===========================================================================


class TestDecisionNotifications:
    """Verify that approving/rejecting triggers decision emails to submitter."""

    async def test_approve_via_approval_queue_sends_decision_email(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        reel48_admin_user,
        reel48_admin_user_token: str,
        mock_email: MockEmailService,
    ):
        """Approving via the approval queue endpoint sends decision email to submitter."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        mock_email.sent_emails.clear()
        response = await client.post(
            f"/api/v1/platform/approvals/{ar.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200

        decision_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_decision"
        ]
        assert len(decision_emails) == 1
        assert decision_emails[0]["to_email"] == user_a1_admin.email
        assert decision_emails[0]["decision"] == "approved"
        assert decision_emails[0]["entity_type"] == "product"

    async def test_reject_via_approval_queue_sends_decision_email_with_notes(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        reel48_admin_user,
        reel48_admin_user_token: str,
        mock_email: MockEmailService,
    ):
        """Rejecting sends decision email with rejection notes."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        mock_email.sent_emails.clear()
        response = await client.post(
            f"/api/v1/platform/approvals/{ar.id}/reject",
            json={"decision_notes": "Product images are too low resolution"},
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200

        decision_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_decision"
        ]
        assert len(decision_emails) == 1
        assert decision_emails[0]["decision"] == "rejected"
        assert decision_emails[0]["decision_notes"] == "Product images are too low resolution"

    async def test_platform_product_approve_sends_decision_email(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        reel48_admin_user,
        reel48_admin_user_token: str,
        mock_email: MockEmailService,
    ):
        """Approving via platform/products endpoint sends decision email to submitter."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="submitted",
        )
        # Create a matching approval request (the platform endpoint syncs with it)
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        mock_email.sent_emails.clear()
        response = await client.post(
            f"/api/v1/platform/products/{product.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200

        decision_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_decision"
        ]
        assert len(decision_emails) == 1
        assert decision_emails[0]["to_email"] == user_a1_admin.email
        assert decision_emails[0]["decision"] == "approved"

    async def test_platform_product_reject_sends_decision_email(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        reel48_admin_user,
        reel48_admin_user_token: str,
        mock_email: MockEmailService,
    ):
        """Rejecting via platform/products endpoint sends rejection email."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="submitted",
        )
        await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        mock_email.sent_emails.clear()
        response = await client.post(
            f"/api/v1/platform/products/{product.id}/reject",
            json={"rejection_reason": "Not compliant"},
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200

        decision_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_decision"
        ]
        assert len(decision_emails) == 1
        assert decision_emails[0]["decision"] == "rejected"
        assert decision_emails[0]["decision_notes"] == "Not compliant"


# ===========================================================================
# Email Failure Resilience Tests
# ===========================================================================


class TestEmailFailureResilience:
    """Verify that email failures do not prevent approval operations."""

    async def test_email_failure_does_not_block_submission(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        user_a1_admin_token: str,
        reel48_admin_user,
        mock_email: MockEmailService,
    ):
        """If email sending fails, the approval request is still created."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="draft",
        )

        # Make the mock raise on send
        original_send = mock_email.send_approval_needed_notification

        async def failing_send(*args, **kwargs):
            raise Exception("SES connection timeout")

        mock_email.send_approval_needed_notification = failing_send

        try:
            response = await client.post(
                f"/api/v1/products/{product.id}/submit",
                headers={"Authorization": f"Bearer {user_a1_admin_token}"},
            )
            # Product submission should still succeed
            assert response.status_code == 200

            # Verify approval request was created despite email failure
            from sqlalchemy import select
            result = await admin_db_session.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.entity_type == "product",
                    ApprovalRequest.entity_id == product.id,
                )
            )
            ar = result.scalar_one_or_none()
            assert ar is not None
            assert ar.status == "pending"
        finally:
            mock_email.send_approval_needed_notification = original_send

    async def test_email_failure_does_not_block_decision(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        reel48_admin_user,
        reel48_admin_user_token: str,
        mock_email: MockEmailService,
    ):
        """If email sending fails, the approval decision still goes through."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="submitted",
        )
        ar = await _create_approval_request(
            admin_db_session, "product", product.id,
            company.id, brand_a1.id, user_a1_admin.id,
        )

        # Make the mock raise on send
        original_send = mock_email.send_approval_decision_notification

        async def failing_send(*args, **kwargs):
            raise Exception("SES connection timeout")

        mock_email.send_approval_decision_notification = failing_send

        try:
            response = await client.post(
                f"/api/v1/platform/approvals/{ar.id}/approve",
                headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
            )
            # Decision should still succeed
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["status"] == "approved"
        finally:
            mock_email.send_approval_decision_notification = original_send


# ===========================================================================
# Integration Flow Tests
# ===========================================================================


class TestFullNotificationFlow:
    """End-to-end: submit -> approval_needed email -> approve -> decision email."""

    async def test_full_product_approval_flow_sends_both_emails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        user_a1_admin_token: str,
        reel48_admin_user,
        reel48_admin_user_token: str,
        mock_email: MockEmailService,
    ):
        """Full flow: submit product -> approval_needed -> approve -> decision email."""
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="draft",
        )

        # Step 1: Submit product
        response = await client.post(
            f"/api/v1/products/{product.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200

        # Verify approval_needed email was sent to reel48_admin
        needed_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_needed"
        ]
        assert len(needed_emails) >= 1
        assert needed_emails[0]["to_email"] == reel48_admin_user.email
        assert needed_emails[0]["submitted_by_name"] == user_a1_admin.full_name

        # Step 2: Approve via platform approvals
        from sqlalchemy import select
        result = await admin_db_session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.entity_type == "product",
                ApprovalRequest.entity_id == product.id,
            )
        )
        ar = result.scalar_one()

        mock_email.sent_emails.clear()
        response = await client.post(
            f"/api/v1/platform/approvals/{ar.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200

        # Verify decision email was sent to submitter
        decision_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_decision"
        ]
        assert len(decision_emails) == 1
        assert decision_emails[0]["to_email"] == user_a1_admin.email
        assert decision_emails[0]["decision"] == "approved"
        assert decision_emails[0]["decided_by_name"] == reel48_admin_user.full_name

    async def test_order_approval_notification_targets_correct_recipients(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token: str,
        user_a1_manager,
        user_a1_admin,
        mock_email: MockEmailService,
    ):
        """Order submission notifies managers, not reel48_admin (different from products)."""
        company, brand_a1, _a2 = company_a
        catalog, product = await _create_catalog_with_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [{
                    "product_id": str(product.id),
                    "quantity": 1,
                    "size": "M",
                }],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201

        needed_emails = [
            e for e in mock_email.sent_emails
            if e.get("type") == "approval_needed"
        ]
        # Should target managers/admins in the same company/sub-brand
        recipient_emails = {e["to_email"] for e in needed_emails}
        assert user_a1_manager.email in recipient_emails
        assert user_a1_admin.email in recipient_emails
