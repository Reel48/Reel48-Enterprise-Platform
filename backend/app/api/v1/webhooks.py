"""Stripe webhook receiver.

This is one of the UNAUTHENTICATED endpoint exceptions — it does NOT use
get_tenant_context. Security comes from Stripe webhook signature verification.
See backend CLAUDE.md > Unauthenticated Endpoint Exceptions.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.services.invoice_service import InvoiceService
from app.services.stripe_service import StripeService, get_stripe_service

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> dict[str, str]:
    """Stripe webhook receiver.

    - Verifies the webhook signature (security — no JWT needed)
    - Sets RLS session variables to empty string (platform-level bypass)
    - Dispatches to InvoiceService.handle_webhook_event()
    - Returns 200 quickly
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("webhook_missing_signature")
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    # Verify webhook signature — raises on invalid signature
    try:
        event = stripe_service.construct_webhook_event(payload, sig_header)
    except Exception:
        logger.warning("webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "unknown")
    stripe_invoice_id = event.get("data", {}).get("object", {}).get("id", "unknown")

    logger.info(
        "webhook_received",
        event_type=event_type,
        stripe_invoice_id=stripe_invoice_id,
    )

    # Set RLS session variables to empty string — webhook handler acts as
    # platform-level operation (same bypass as reel48_admin). This allows
    # queries to find invoices across all companies.
    await db.execute(text("SET LOCAL app.current_company_id = ''"))
    await db.execute(text("SET LOCAL app.current_sub_brand_id = ''"))

    # Dispatch to InvoiceService for idempotent processing
    service = InvoiceService(db)
    await service.handle_webhook_event(event)

    return {"status": "ok"}
