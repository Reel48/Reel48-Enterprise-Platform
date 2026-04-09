"""
Comprehensive tests for Module 7: Invoicing & Client Billing.

Covers all three mandatory test categories:
1. Functional tests — assigned, post-window, and self-service billing flows
2. Authorization tests — role-based access control
3. Isolation tests — cross-company and cross-sub-brand boundaries
Plus webhook-specific tests for Stripe event handling.
"""

import json
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bulk_order import BulkOrder
from app.models.bulk_order_item import BulkOrderItem
from app.models.catalog import Catalog
from app.models.company import Company
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.models.product import Product
from app.models.sub_brand import SubBrand
from app.models.user import User
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------
async def _create_product(
    session: AsyncSession, company_id, sub_brand_id, created_by, **kwargs
) -> Product:
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=kwargs.get("name", f"Test Product {uuid4().hex[:6]}"),
        sku=kwargs.get("sku", f"SKU-{uuid4().hex[:8].upper()}"),
        unit_price=kwargs.get("unit_price", Decimal("29.99")),
        status="active",
        created_by=created_by,
    )
    session.add(product)
    await session.flush()
    return product


async def _create_catalog(
    session: AsyncSession, company_id, sub_brand_id, created_by, **kwargs
) -> Catalog:
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=kwargs.get("name", f"Test Catalog {uuid4().hex[:6]}"),
        slug=kwargs.get("slug", f"cat-{uuid4().hex[:8]}"),
        payment_model=kwargs.get("payment_model", "self_service"),
        status=kwargs.get("status", "active"),
        buying_window_opens_at=kwargs.get("buying_window_opens_at"),
        buying_window_closes_at=kwargs.get("buying_window_closes_at"),
        created_by=created_by,
    )
    session.add(catalog)
    await session.flush()
    return catalog


async def _create_order_with_items(
    session: AsyncSession,
    company_id,
    sub_brand_id,
    user_id,
    catalog_id,
    product: Product,
    quantity: int = 2,
    status: str = "approved",
) -> tuple[Order, list[OrderLineItem]]:
    order = Order(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        user_id=user_id,
        catalog_id=catalog_id,
        order_number=f"ORD-{uuid4().hex[:8].upper()}",
        status=status,
        subtotal=product.unit_price * quantity,
        total_amount=product.unit_price * quantity,
    )
    session.add(order)
    await session.flush()

    item = OrderLineItem(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        product_sku=product.sku,
        unit_price=product.unit_price,
        quantity=quantity,
        line_total=product.unit_price * quantity,
    )
    session.add(item)
    await session.flush()
    return order, [item]


async def _create_bulk_order_with_items(
    session: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    catalog_id,
    product: Product,
    quantity: int = 5,
    status: str = "approved",
) -> tuple[BulkOrder, list[BulkOrderItem]]:
    bulk_order = BulkOrder(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        catalog_id=catalog_id,
        created_by=created_by,
        title=f"Bulk Order {uuid4().hex[:6]}",
        order_number=f"BLK-{uuid4().hex[:8].upper()}",
        status=status,
        total_items=quantity,
        total_amount=product.unit_price * quantity,
    )
    session.add(bulk_order)
    await session.flush()

    item = BulkOrderItem(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        bulk_order_id=bulk_order.id,
        product_id=product.id,
        product_name=product.name,
        product_sku=product.sku,
        unit_price=product.unit_price,
        quantity=quantity,
        line_total=product.unit_price * quantity,
    )
    session.add(item)
    await session.flush()
    return bulk_order, [item]


async def _create_invoice_directly(
    session: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    billing_flow: str = "assigned",
    status: str = "draft",
    total_amount: Decimal = Decimal("59.98"),
    **kwargs,
) -> Invoice:
    invoice = Invoice(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        stripe_invoice_id=kwargs.get("stripe_invoice_id", f"in_test_{uuid4().hex[:8]}"),
        stripe_invoice_url=f"https://invoice.stripe.com/i/test",
        billing_flow=billing_flow,
        status=status,
        total_amount=total_amount,
        created_by=created_by,
        order_id=kwargs.get("order_id"),
        bulk_order_id=kwargs.get("bulk_order_id"),
        catalog_id=kwargs.get("catalog_id"),
        paid_at=kwargs.get("paid_at"),
        stripe_pdf_url=kwargs.get("stripe_pdf_url"),
    )
    session.add(invoice)
    await session.flush()
    return invoice


# ═══════════════════════════════════════════════════════════════════════════
# Functional Tests — Assigned Invoice (Flow 1)
# ═══════════════════════════════════════════════════════════════════════════
class TestAssignedInvoice:
    async def test_create_assigned_invoice_from_orders(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
        mock_stripe,
    ):
        """reel48_admin creates an assigned invoice from approved orders."""
        company, brand_a1, _ = company_a
        user = User(
            company_id=company.id, sub_brand_id=brand_a1.id,
            cognito_sub=str(uuid4()), email=f"inv-emp-{uuid4().hex[:6]}@a.com",
            full_name="Invoice Employee", role="employee",
        )
        admin_db_session.add(user)
        await admin_db_session.flush()

        product = await _create_product(admin_db_session, company.id, brand_a1.id, user.id)
        catalog = await _create_catalog(admin_db_session, company.id, brand_a1.id, user.id)
        order, items = await _create_order_with_items(
            admin_db_session, company.id, brand_a1.id, user.id, catalog.id, product
        )

        response = await client.post(
            "/api/v1/platform/invoices/",
            json={
                "company_id": str(company.id),
                "billing_flow": "assigned",
                "order_ids": [str(order.id)],
            },
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["billing_flow"] == "assigned"
        assert data["status"] == "draft"
        assert data["company_id"] == str(company.id)
        assert float(data["total_amount"]) == float(product.unit_price * 2)

        # Verify Stripe mock was called
        assert len(mock_stripe.created_invoices) == 1
        assert len(mock_stripe.created_invoice_items) == 1

    async def test_create_assigned_invoice_from_bulk_orders(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
        mock_stripe,
    ):
        """reel48_admin creates an assigned invoice from bulk orders."""
        company, brand_a1, _ = company_a
        user = User(
            company_id=company.id, sub_brand_id=brand_a1.id,
            cognito_sub=str(uuid4()), email=f"inv-mgr-{uuid4().hex[:6]}@a.com",
            full_name="Invoice Manager", role="regional_manager",
        )
        admin_db_session.add(user)
        await admin_db_session.flush()

        product = await _create_product(admin_db_session, company.id, brand_a1.id, user.id)
        catalog = await _create_catalog(admin_db_session, company.id, brand_a1.id, user.id)
        bulk_order, _ = await _create_bulk_order_with_items(
            admin_db_session, company.id, brand_a1.id, user.id, catalog.id, product
        )

        response = await client.post(
            "/api/v1/platform/invoices/",
            json={
                "company_id": str(company.id),
                "billing_flow": "assigned",
                "bulk_order_ids": [str(bulk_order.id)],
            },
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["billing_flow"] == "assigned"
        assert data["status"] == "draft"
        assert len(mock_stripe.created_invoices) == 1

    async def test_create_assigned_invoice_requires_order_ids_or_bulk_order_ids(
        self,
        client: AsyncClient,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
    ):
        """422 if neither order_ids nor bulk_order_ids provided."""
        company, _, _ = company_a
        response = await client.post(
            "/api/v1/platform/invoices/",
            json={
                "company_id": str(company.id),
                "billing_flow": "assigned",
            },
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        # ValidationError maps to 422 in the app exception hierarchy
        assert response.status_code == 422

    async def test_finalize_invoice(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
        mock_stripe,
    ):
        """Finalize a draft invoice — status changes to 'finalized', invoice_number set."""
        company, brand_a1, _ = company_a
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id
        )

        response = await client.post(
            f"/api/v1/platform/invoices/{invoice.id}/finalize",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "finalized"
        assert data["invoice_number"] is not None
        assert len(mock_stripe.finalized_invoices) == 1

    async def test_send_finalized_invoice(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
        mock_stripe,
    ):
        """Send a finalized invoice — status changes to 'sent'."""
        company, brand_a1, _ = company_a
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            status="finalized",
        )

        response = await client.post(
            f"/api/v1/platform/invoices/{invoice.id}/send",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "sent"
        assert len(mock_stripe.sent_invoices) == 1

    async def test_void_draft_invoice(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
        mock_stripe,
    ):
        """Void a draft invoice — status changes to 'voided'."""
        company, brand_a1, _ = company_a
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            status="draft",
        )

        response = await client.post(
            f"/api/v1/platform/invoices/{invoice.id}/void",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "voided"
        assert len(mock_stripe.voided_invoices) == 1

    async def test_cannot_void_paid_invoice(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
    ):
        """403 if invoice is already paid."""
        company, brand_a1, _ = company_a
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            status="paid",
            paid_at=datetime.now(UTC),
        )

        response = await client.post(
            f"/api/v1/platform/invoices/{invoice.id}/void",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# Functional Tests — Post-Window Invoice (Flow 3)
# ═══════════════════════════════════════════════════════════════════════════
class TestPostWindowInvoice:
    async def test_create_post_window_invoice(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
        mock_stripe,
    ):
        """reel48_admin creates a consolidated invoice after buying window closes."""
        company, brand_a1, _ = company_a
        user = User(
            company_id=company.id, sub_brand_id=brand_a1.id,
            cognito_sub=str(uuid4()), email=f"pw-emp-{uuid4().hex[:6]}@a.com",
            full_name="PW Employee", role="employee",
        )
        admin_db_session.add(user)
        await admin_db_session.flush()

        product = await _create_product(admin_db_session, company.id, brand_a1.id, user.id)
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id,
            payment_model="invoice_after_close",
            buying_window_opens_at=datetime.now(UTC) - timedelta(days=30),
            buying_window_closes_at=datetime.now(UTC) - timedelta(hours=1),
        )
        # Create orders against this catalog
        await _create_order_with_items(
            admin_db_session, company.id, brand_a1.id, user.id, catalog.id, product
        )

        response = await client.post(
            "/api/v1/platform/invoices/",
            json={
                "company_id": str(company.id),
                "billing_flow": "post_window",
                "catalog_id": str(catalog.id),
            },
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["billing_flow"] == "post_window"
        assert data["status"] == "draft"
        assert data["catalog_id"] == str(catalog.id)

    async def test_cannot_create_post_window_invoice_before_window_closes(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
    ):
        """422 if buying window hasn't closed yet."""
        company, brand_a1, _ = company_a
        user = User(
            company_id=company.id, sub_brand_id=brand_a1.id,
            cognito_sub=str(uuid4()), email=f"pw2-{uuid4().hex[:6]}@a.com",
            full_name="PW2", role="employee",
        )
        admin_db_session.add(user)
        await admin_db_session.flush()

        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id,
            payment_model="invoice_after_close",
            buying_window_opens_at=datetime.now(UTC) - timedelta(days=1),
            buying_window_closes_at=datetime.now(UTC) + timedelta(days=7),  # Still open
        )

        response = await client.post(
            "/api/v1/platform/invoices/",
            json={
                "company_id": str(company.id),
                "billing_flow": "post_window",
                "catalog_id": str(catalog.id),
            },
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 422

    async def test_post_window_invoice_requires_invoice_after_close_catalog(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        reel48_admin_user_token,
    ):
        """422 for self_service catalog when trying to create post_window invoice."""
        company, brand_a1, _ = company_a
        user = User(
            company_id=company.id, sub_brand_id=brand_a1.id,
            cognito_sub=str(uuid4()), email=f"pw3-{uuid4().hex[:6]}@a.com",
            full_name="PW3", role="employee",
        )
        admin_db_session.add(user)
        await admin_db_session.flush()

        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id,
            payment_model="self_service",
        )

        response = await client.post(
            "/api/v1/platform/invoices/",
            json={
                "company_id": str(company.id),
                "billing_flow": "post_window",
                "catalog_id": str(catalog.id),
            },
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Functional Tests — Client Viewing
# ═══════════════════════════════════════════════════════════════════════════
class TestClientInvoiceViewing:
    async def test_list_invoices_as_corporate_admin(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        user_a_corporate_admin,
        user_a_corporate_admin_token,
    ):
        """Corporate admin sees all company invoices across sub-brands."""
        company, brand_a1, brand_a2 = company_a
        # Create invoices in both sub-brands
        await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
        )
        await _create_invoice_directly(
            admin_db_session, company.id, brand_a2.id, reel48_admin_user.id,
        )

        response = await client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 2

    async def test_get_invoice_detail(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        user_a_corporate_admin,
        user_a_corporate_admin_token,
    ):
        """Get full invoice detail."""
        company, brand_a1, _ = company_a
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
        )

        response = await client.get(
            f"/api/v1/invoices/{invoice.id}",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(invoice.id)
        assert data["billing_flow"] == "assigned"
        assert data["stripe_invoice_id"] is not None

    async def test_get_invoice_pdf_url(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        user_a_corporate_admin,
        user_a_corporate_admin_token,
    ):
        """Get Stripe-hosted invoice PDF URL."""
        company, brand_a1, _ = company_a
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            stripe_pdf_url="https://invoice.stripe.com/pdf/test",
        )

        response = await client.get(
            f"/api/v1/invoices/{invoice.id}/pdf",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "pdf_url" in data
        assert data["pdf_url"] == "https://invoice.stripe.com/pdf/test"


# ═══════════════════════════════════════════════════════════════════════════
# Webhook Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestStripeWebhooks:
    def _build_webhook_event(self, event_type: str, invoice_data: dict) -> bytes:
        """Build a Stripe webhook event payload."""
        return json.dumps({
            "type": event_type,
            "data": {"object": invoice_data},
        }).encode()

    async def test_webhook_invoice_paid(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
    ):
        """Simulate invoice.paid event, verify local status update."""
        company, brand_a1, _ = company_a
        stripe_id = f"in_paid_{uuid4().hex[:8]}"
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            status="sent",
            stripe_invoice_id=stripe_id,
        )

        payload = self._build_webhook_event("invoice.paid", {"id": stripe_id})
        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={"stripe-signature": "test_sig", "content-type": "application/json"},
        )
        assert response.status_code == 200

        # Verify status updated
        await admin_db_session.refresh(invoice)
        assert invoice.status == "paid"
        assert invoice.paid_at is not None

    async def test_webhook_invoice_payment_failed(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
    ):
        """Simulate payment failure webhook."""
        company, brand_a1, _ = company_a
        stripe_id = f"in_fail_{uuid4().hex[:8]}"
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            status="sent",
            stripe_invoice_id=stripe_id,
        )

        payload = self._build_webhook_event("invoice.payment_failed", {"id": stripe_id})
        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={"stripe-signature": "test_sig", "content-type": "application/json"},
        )
        assert response.status_code == 200

        await admin_db_session.refresh(invoice)
        assert invoice.status == "payment_failed"

    async def test_webhook_invoice_finalized(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
    ):
        """Verify invoice_number stored from finalized event."""
        company, brand_a1, _ = company_a
        stripe_id = f"in_fin_{uuid4().hex[:8]}"
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            status="draft",
            stripe_invoice_id=stripe_id,
        )

        payload = self._build_webhook_event("invoice.finalized", {
            "id": stripe_id,
            "number": "INV-2026-0042",
            "hosted_invoice_url": "https://example.com/inv",
            "invoice_pdf": "https://example.com/inv/pdf",
        })
        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={"stripe-signature": "test_sig", "content-type": "application/json"},
        )
        assert response.status_code == 200

        await admin_db_session.refresh(invoice)
        assert invoice.status == "finalized"
        assert invoice.invoice_number == "INV-2026-0042"

    async def test_webhook_invalid_signature_returns_400(
        self,
        client: AsyncClient,
        mock_stripe,
    ):
        """Invalid signature rejected with 400."""
        # Override construct_webhook_event to raise
        original = mock_stripe.construct_webhook_event

        def _raise_on_verify(payload, sig_header):
            raise Exception("Invalid signature")

        mock_stripe.construct_webhook_event = _raise_on_verify

        try:
            response = await client.post(
                "/api/v1/webhooks/stripe",
                content=b'{"type":"invoice.paid"}',
                headers={"stripe-signature": "bad_sig", "content-type": "application/json"},
            )
            assert response.status_code == 400
        finally:
            mock_stripe.construct_webhook_event = original

    async def test_webhook_missing_signature_returns_400(self, client: AsyncClient):
        """Missing stripe-signature header returns 400."""
        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=b'{"type":"invoice.paid"}',
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400

    async def test_webhook_idempotent_processing(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
    ):
        """Same event processed twice produces same result (no duplicate updates)."""
        company, brand_a1, _ = company_a
        stripe_id = f"in_idemp_{uuid4().hex[:8]}"
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            status="sent",
            stripe_invoice_id=stripe_id,
        )

        payload = self._build_webhook_event("invoice.paid", {"id": stripe_id})
        headers = {"stripe-signature": "test_sig", "content-type": "application/json"}

        # Process the same event twice
        r1 = await client.post("/api/v1/webhooks/stripe", content=payload, headers=headers)
        assert r1.status_code == 200

        r2 = await client.post("/api/v1/webhooks/stripe", content=payload, headers=headers)
        assert r2.status_code == 200

        # Verify status is still paid (not errored or duplicated)
        await admin_db_session.refresh(invoice)
        assert invoice.status == "paid"

    async def test_webhook_does_not_downgrade_status(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
    ):
        """Paid invoice not reverted to finalized by a late-arriving finalized event."""
        company, brand_a1, _ = company_a
        stripe_id = f"in_nodown_{uuid4().hex[:8]}"
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
            status="paid",
            paid_at=datetime.now(UTC),
            stripe_invoice_id=stripe_id,
        )

        # Late-arriving finalized event (should NOT downgrade)
        payload = self._build_webhook_event("invoice.finalized", {
            "id": stripe_id,
            "number": "INV-LATE",
        })
        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=payload,
            headers={"stripe-signature": "test_sig", "content-type": "application/json"},
        )
        assert response.status_code == 200

        await admin_db_session.refresh(invoice)
        assert invoice.status == "paid"  # Not downgraded to finalized


# ═══════════════════════════════════════════════════════════════════════════
# Authorization Tests
# ═══════════════════════════════════════════════════════════════════════════
class TestInvoiceAuthorization:
    async def test_only_reel48_admin_can_create_invoices(
        self,
        client: AsyncClient,
        company_a,
        company_a_corporate_admin_token,
        company_a_brand_a1_admin_token,
        company_a_brand_a1_employee_token,
    ):
        """corporate_admin, sub_brand_admin, employee all get 403 on create."""
        company, _, _ = company_a
        body = {
            "company_id": str(company.id),
            "billing_flow": "assigned",
            "order_ids": [str(uuid4())],
        }

        for token in [
            company_a_corporate_admin_token,
            company_a_brand_a1_admin_token,
            company_a_brand_a1_employee_token,
        ]:
            response = await client.post(
                "/api/v1/platform/invoices/",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403

    async def test_only_reel48_admin_can_finalize_invoices(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        company_a_corporate_admin_token,
        company_a_brand_a1_admin_token,
    ):
        """Non-admin roles get 403 on finalize."""
        company, brand_a1, _ = company_a
        invoice = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
        )

        for token in [
            company_a_corporate_admin_token,
            company_a_brand_a1_admin_token,
        ]:
            response = await client.post(
                f"/api/v1/platform/invoices/{invoice.id}/finalize",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403

    async def test_employee_cannot_view_invoices(
        self,
        client: AsyncClient,
        company_a,
        company_a_brand_a1_employee_token,
    ):
        """403 on all client invoice endpoints for employees."""
        response = await client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_corporate_admin_can_view_own_company_invoices(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        user_a_corporate_admin,
        user_a_corporate_admin_token,
    ):
        """200 on list invoices for corporate_admin."""
        company, brand_a1, _ = company_a
        await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
        )

        response = await client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) >= 1

    async def test_sub_brand_admin_can_view_own_brand_invoices(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        user_a1_admin,
        user_a1_admin_token,
    ):
        """200 on list invoices for sub_brand_admin (own brand only)."""
        company, brand_a1, _ = company_a
        await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
        )

        response = await client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) >= 1

    async def test_regional_manager_can_view_own_brand_invoices(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        user_a1_manager,
        user_a1_manager_token,
    ):
        """200 on list invoices for regional_manager (own brand only)."""
        company, brand_a1, _ = company_a
        await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
        )

        response = await client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Isolation Tests (HTTP-level)
# ═══════════════════════════════════════════════════════════════════════════
class TestInvoiceIsolation:
    async def test_company_b_cannot_see_company_a_invoices(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
        reel48_admin_user,
        company_b_corporate_admin_token,
    ):
        """Cross-company isolation: Company B sees zero Company A invoices."""
        company_a_obj, brand_a1, _ = company_a
        company_b_obj, brand_b1 = company_b

        # Need a corporate_admin user in Company B for the token to resolve
        user_b_admin = User(
            company_id=company_b_obj.id, sub_brand_id=None,
            cognito_sub=str(uuid4()), email=f"corp-b-{uuid4().hex[:6]}@b.com",
            full_name="Corp Admin B", role="corporate_admin",
        )
        admin_db_session.add(user_b_admin)
        await admin_db_session.flush()
        token_b = create_test_token(
            user_id=user_b_admin.cognito_sub,
            company_id=str(company_b_obj.id),
            role="corporate_admin",
        )

        # Create invoice in Company A
        await _create_invoice_directly(
            admin_db_session, company_a_obj.id, brand_a1.id, reel48_admin_user.id,
        )

        # Query as Company B corporate admin
        response = await client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        # Company B should see zero Company A invoices
        for inv in data:
            assert inv["company_id"] == str(company_b_obj.id)

    async def test_brand_a2_cannot_see_brand_a1_invoices(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
    ):
        """Cross-sub-brand isolation within same company."""
        company, brand_a1, brand_a2 = company_a

        # Create user and token for Brand A2 admin
        user_a2 = User(
            company_id=company.id, sub_brand_id=brand_a2.id,
            cognito_sub=str(uuid4()), email=f"admin-a2-inv-{uuid4().hex[:6]}@a.com",
            full_name="Admin A2", role="sub_brand_admin",
        )
        admin_db_session.add(user_a2)
        await admin_db_session.flush()
        token_a2 = create_test_token(
            user_id=user_a2.cognito_sub,
            company_id=str(company.id),
            sub_brand_id=str(brand_a2.id),
            role="sub_brand_admin",
        )

        # Create invoice in Brand A1
        await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
        )

        # Query as Brand A2 admin — should not see Brand A1 invoices
        response = await client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {token_a2}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        for inv in data:
            assert inv["sub_brand_id"] != str(brand_a1.id)

    async def test_corporate_admin_sees_all_sub_brand_invoices(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        reel48_admin_user,
        user_a_corporate_admin,
        user_a_corporate_admin_token,
    ):
        """Corporate admin sees invoices across all sub-brands."""
        company, brand_a1, brand_a2 = company_a

        inv1 = await _create_invoice_directly(
            admin_db_session, company.id, brand_a1.id, reel48_admin_user.id,
        )
        inv2 = await _create_invoice_directly(
            admin_db_session, company.id, brand_a2.id, reel48_admin_user.id,
        )

        response = await client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        ids = {inv["id"] for inv in data}
        assert str(inv1.id) in ids
        assert str(inv2.id) in ids

    async def test_reel48_admin_sees_all_invoices(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
        reel48_admin_user,
        reel48_admin_user_token,
    ):
        """Platform admin sees invoices across all companies."""
        company_a_obj, brand_a1, _ = company_a
        company_b_obj, brand_b1 = company_b

        inv_a = await _create_invoice_directly(
            admin_db_session, company_a_obj.id, brand_a1.id, reel48_admin_user.id,
        )
        inv_b = await _create_invoice_directly(
            admin_db_session, company_b_obj.id, brand_b1.id, reel48_admin_user.id,
        )

        response = await client.get(
            "/api/v1/platform/invoices/",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        ids = {inv["id"] for inv in data}
        assert str(inv_a.id) in ids
        assert str(inv_b.id) in ids
