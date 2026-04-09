"""
Stripe API integration service.

This is the ONLY file that imports the stripe SDK. All other code calls this
service for Stripe operations. The service is injected as a FastAPI dependency,
making it easily mockable in tests.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.config import settings
from app.core.exceptions import AppException, ValidationError

logger = structlog.get_logger()


class StripeError(AppException):
    """Wraps Stripe SDK errors into the standard AppException hierarchy."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(
            code="STRIPE_ERROR",
            message=message,
            status_code=status_code,
        )


class StripeService:
    """Wraps the Stripe Python SDK for invoice and customer management.

    Follows the External Service Integration Pattern (see backend CLAUDE.md):
    - Stripe import is lazy (inside methods and dependency factory)
    - Maps Stripe SDK exceptions to AppException subclasses
    - Injected via FastAPI Depends() for easy test mocking
    """

    def __init__(self, api_key: str, webhook_secret: str) -> None:
        self._api_key = api_key
        self._webhook_secret = webhook_secret

    def _get_stripe(self) -> Any:
        """Lazy-import stripe and configure it."""
        import stripe  # type: ignore[import-untyped]

        stripe.api_key = self._api_key
        stripe.api_version = settings.STRIPE_API_VERSION
        return stripe

    async def get_or_create_customer(
        self,
        company_id: str,
        company_name: str,
        stripe_customer_id: str | None = None,
    ) -> str:
        """Returns stripe_customer_id, creating a Stripe Customer if needed.

        NOTE: Does NOT update company.stripe_customer_id — caller handles DB update.
        """
        if stripe_customer_id:
            return stripe_customer_id

        stripe = self._get_stripe()
        try:
            customer = stripe.Customer.create(
                name=company_name,
                metadata={"reel48_company_id": company_id},
            )
            logger.info(
                "stripe_customer_created",
                stripe_customer_id=customer.id,
                company_id=company_id,
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error("stripe_customer_create_failed", error=str(e))
            raise StripeError(f"Failed to create Stripe customer: {e}")

    async def create_invoice(
        self,
        customer_id: str,
        metadata: dict[str, str],
        auto_advance: bool = False,
    ) -> dict[str, Any]:
        """Creates a draft Stripe Invoice. Returns the Stripe invoice object as dict."""
        stripe = self._get_stripe()
        try:
            invoice = stripe.Invoice.create(
                customer=customer_id,
                metadata=metadata,
                auto_advance=auto_advance,
            )
            logger.info(
                "stripe_invoice_created",
                stripe_invoice_id=invoice.id,
                customer_id=customer_id,
                auto_advance=auto_advance,
            )
            return dict(invoice)
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_create_failed", error=str(e))
            raise StripeError(f"Failed to create Stripe invoice: {e}")

    async def create_invoice_item(
        self,
        customer_id: str,
        invoice_id: str,
        description: str,
        quantity: int,
        unit_amount_cents: int,
        currency: str = "usd",
    ) -> dict[str, Any]:
        """Creates a Stripe InvoiceItem on the given invoice."""
        stripe = self._get_stripe()
        try:
            item = stripe.InvoiceItem.create(
                customer=customer_id,
                invoice=invoice_id,
                description=description,
                quantity=quantity,
                unit_amount=unit_amount_cents,
                currency=currency,
            )
            logger.info(
                "stripe_invoice_item_created",
                stripe_invoice_id=invoice_id,
                description=description,
                quantity=quantity,
                unit_amount_cents=unit_amount_cents,
            )
            return dict(item)
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_item_create_failed", error=str(e))
            raise StripeError(f"Failed to create Stripe invoice item: {e}")

    async def finalize_invoice(self, stripe_invoice_id: str) -> dict[str, Any]:
        """Finalizes a draft invoice, triggering Stripe to assign an invoice number."""
        stripe = self._get_stripe()
        try:
            invoice = stripe.Invoice.finalize_invoice(stripe_invoice_id)
            logger.info(
                "stripe_invoice_finalized",
                stripe_invoice_id=stripe_invoice_id,
                invoice_number=invoice.get("number"),
            )
            return dict(invoice)
        except stripe.error.InvalidRequestError as e:
            logger.error("stripe_invoice_finalize_failed", error=str(e))
            raise ValidationError(f"Cannot finalize invoice: {e}")
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_finalize_failed", error=str(e))
            raise StripeError(f"Failed to finalize Stripe invoice: {e}")

    async def send_invoice(self, stripe_invoice_id: str) -> dict[str, Any]:
        """Sends a finalized invoice to the customer via email."""
        stripe = self._get_stripe()
        try:
            invoice = stripe.Invoice.send_invoice(stripe_invoice_id)
            logger.info(
                "stripe_invoice_sent",
                stripe_invoice_id=stripe_invoice_id,
            )
            return dict(invoice)
        except stripe.error.InvalidRequestError as e:
            logger.error("stripe_invoice_send_failed", error=str(e))
            raise ValidationError(f"Cannot send invoice: {e}")
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_send_failed", error=str(e))
            raise StripeError(f"Failed to send Stripe invoice: {e}")

    async def void_invoice(self, stripe_invoice_id: str) -> dict[str, Any]:
        """Voids an invoice (e.g., if created in error)."""
        stripe = self._get_stripe()
        try:
            invoice = stripe.Invoice.void_invoice(stripe_invoice_id)
            logger.info(
                "stripe_invoice_voided",
                stripe_invoice_id=stripe_invoice_id,
            )
            return dict(invoice)
        except stripe.error.InvalidRequestError as e:
            logger.error("stripe_invoice_void_failed", error=str(e))
            raise ValidationError(f"Cannot void invoice: {e}")
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_void_failed", error=str(e))
            raise StripeError(f"Failed to void Stripe invoice: {e}")

    async def get_invoice(self, stripe_invoice_id: str) -> dict[str, Any]:
        """Retrieves current invoice state from Stripe."""
        stripe = self._get_stripe()
        try:
            invoice = stripe.Invoice.retrieve(stripe_invoice_id)
            return dict(invoice)
        except stripe.error.StripeError as e:
            logger.error("stripe_invoice_retrieve_failed", error=str(e))
            raise StripeError(f"Failed to retrieve Stripe invoice: {e}")

    def construct_webhook_event(
        self, payload: bytes, sig_header: str
    ) -> dict[str, Any]:
        """Verifies webhook signature and constructs the event object.

        Raises stripe.error.SignatureVerificationError on invalid signature.
        This method is intentionally synchronous — signature verification is
        CPU-bound, not I/O-bound.
        """
        stripe = self._get_stripe()
        event = stripe.Webhook.construct_event(
            payload, sig_header, self._webhook_secret
        )
        return dict(event)


def get_stripe_service() -> StripeService:
    """FastAPI dependency that returns a StripeService configured from settings."""
    return StripeService(
        api_key=settings.STRIPE_SECRET_KEY,
        webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
    )
