# Module 7: Invoicing & Client Billing — Phase-by-Phase Implementation Prompts
#
# Each phase below is a self-contained prompt designed to be pasted into a
# fresh Claude Code session. The session will read the CLAUDE.md harness files
# automatically — these prompts provide MODULE-SPECIFIC context that the
# harness doesn't cover.
#
# IMPORTANT: Run phases in order. Each phase depends on the prior phase's output.
#
# MODULE 7 OVERVIEW:
# Invoicing is how Reel48+ generates revenue. Reel48 (the platform operator)
# bills client companies for apparel orders fulfilled through the platform.
# This module implements the full invoice lifecycle: creation, finalization,
# sending, payment tracking, and client-facing visibility.
#
# Three billing flows (defined in root CLAUDE.md):
# - Flow 1: Reel48-Assigned Invoices — reel48_admin manually creates invoices
#   for bulk/custom orders after fulfillment. billing_flow = 'assigned'
# - Flow 2: Self-Service — Auto-generated invoices at checkout for pre-priced
#   catalog items. billing_flow = 'self_service'
# - Flow 3: Post-Window — Consolidated invoice after a buying window closes.
#   billing_flow = 'post_window'
#
# Key architectural points:
# - Stripe is the invoicing/payment platform (ADR-006)
# - All Stripe API calls are server-side only (never in frontend)
# - reel48_admin creates/finalizes/sends invoices; client admins can only VIEW
# - Stripe webhook endpoint is unauthenticated (signature-verified)
# - Local `invoices` table mirrors Stripe data for tenant-scoped queries
# - Stripe is source of truth for payment status; local records enable fast
#   queries and RLS-scoped access
#
# What ALREADY EXISTS (do not rebuild):
# - Company model with `stripe_customer_id` field (models/company.py)
# - Orders (Module 4) with status lifecycle and line items
# - Bulk Orders (Module 5) with status lifecycle and items
# - Catalogs (Module 3) with `payment_model` field ('self_service' | 'invoice_after_close')
# - Approval Workflows (Module 6) wrapping all entity approvals
# - Email Service (Module 6) with SES integration pattern
# - All tenant isolation infrastructure (RLS, TenantContext, auth middleware)
#
# What Module 7 BUILDS:
# - `invoices` table with RLS policies (migration 007)
# - StripeService (Stripe API client wrapper, dependency-injectable)
# - InvoiceService (invoice lifecycle: create, finalize, sync from webhooks)
# - Stripe webhook endpoint (unauthenticated, signature-verified)
# - Platform admin invoice endpoints (create, finalize, list, detail)
# - Client-facing invoice endpoints (list, detail, PDF URL)
# - Self-service invoice auto-generation at order checkout
# - Post-window consolidated invoice creation
# - Comprehensive tests (functional, isolation, authorization, webhook)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Database Migration — Invoices Table
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 7 Phase 1: the Alembic migration, SQLAlchemy model, Pydantic schemas,
and test infrastructure updates for the invoicing system.

## Context

We are building Module 7 (Invoicing & Client Billing) of the Reel48+ enterprise
apparel platform. Modules 1-6 are complete:
- Module 1: Auth, Companies, Sub-Brands, Users (migration `001`)
- Module 2: Employee Profiles (migration `002`)
- Module 3: Products, Catalogs, Catalog-Products (migration `003`)
- Module 4: Orders, Order Line Items (migration `004`)
- Module 5: Bulk Orders, Bulk Order Items (migration `005`)
- Module 6: Approval Requests, Approval Rules (migration `006`)

The current test suite has 409 passing tests. The branch is `main`.
Create a new branch `feature/module7-phase1-invoice-tables` from `main`
before starting.

## What to Build

### 1. Alembic migration: `backend/migrations/versions/007_create_module7_invoice_tables.py`

Create the `invoices` table (TenantBase shape):

```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL FK → companies.id
sub_brand_id            UUID        NULL FK → sub_brands.id
order_id                UUID        NULL FK → orders.id          -- for individual order invoices
bulk_order_id           UUID        NULL FK → bulk_orders.id     -- for bulk order invoices
catalog_id              UUID        NULL FK → catalogs.id        -- for self-service/post-window flows
stripe_invoice_id       TEXT        NOT NULL UNIQUE              -- Stripe's invoice ID (e.g., "in_xxx")
stripe_invoice_url      TEXT        NULL                         -- hosted invoice page URL
stripe_pdf_url          TEXT        NULL                         -- invoice PDF download URL
invoice_number          TEXT        NULL                         -- assigned by Stripe on finalization
billing_flow            VARCHAR(20) NOT NULL                     -- 'assigned', 'self_service', 'post_window'
status                  VARCHAR(20) NOT NULL DEFAULT 'draft'     -- 'draft', 'finalized', 'sent', 'paid', 'payment_failed', 'voided'
total_amount            NUMERIC(10,2) NOT NULL                   -- in dollars (convert to cents for Stripe only)
currency                VARCHAR(3)  NOT NULL DEFAULT 'usd'
due_date                DATE        NULL
buying_window_closes_at TIMESTAMP WITH TIME ZONE NULL            -- for post_window flow only
created_by              UUID        NOT NULL FK → users.id       -- the reel48_admin who created it (or system user for auto-generated)
paid_at                 TIMESTAMP WITH TIME ZONE NULL
created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
```

CHECK constraints:
- `ck_invoices_billing_flow_valid`: billing_flow IN ('assigned', 'self_service', 'post_window')
- `ck_invoices_status_valid`: status IN ('draft', 'finalized', 'sent', 'paid', 'payment_failed', 'voided')
- `ck_invoices_total_amount_non_negative`: total_amount >= 0

Indexes:
- `ix_invoices_company_id` on (company_id)
- `ix_invoices_sub_brand_id` on (sub_brand_id)
- `ix_invoices_stripe_invoice_id` on (stripe_invoice_id) — already UNIQUE, but explicit index
- `ix_invoices_company_id_status` on (company_id, status) — for filtered list queries
- `ix_invoices_billing_flow` on (billing_flow)

RLS policies (in the same migration):
- `invoices_company_isolation` — standard PERMISSIVE company isolation
- `invoices_sub_brand_scoping` — standard RESTRICTIVE sub-brand scoping

Include both `upgrade()` and `downgrade()` functions.

### 2. SQLAlchemy model: `backend/app/models/invoice.py`

Create the `Invoice` model inheriting from `TenantBase`. Follow the same pattern as
`Order` and `BulkOrder` models. Include all columns from the migration.

### 3. Update `backend/app/models/__init__.py`

Add the `Invoice` import.

### 4. Pydantic schemas: `backend/app/schemas/invoice.py`

Create the following schemas following the pattern in `backend/app/schemas/order.py`:

- **`InvoiceCreate`** — Used by reel48_admin to create an assigned or post-window invoice.
  Fields: `company_id` (UUID, required — target company), `sub_brand_id` (UUID, optional),
  `order_id` (UUID, optional), `bulk_order_id` (UUID, optional), `catalog_id` (UUID, optional),
  `billing_flow` (str, required), `due_date` (date, optional),
  `buying_window_closes_at` (datetime, optional).
  NOTE: `company_id` is accepted here because this is a platform admin endpoint —
  the reel48_admin has no company_id of their own and must specify the target company.

- **`InvoiceResponse`** — Full invoice representation for API responses.
  All columns from the model. Uses `ConfigDict(from_attributes=True)`.

- **`InvoiceListResponse`** — Alias for `ApiListResponse[InvoiceResponse]`.

- **`InvoiceSummary`** — Lighter version for list views (omit stripe URLs, include
  id, invoice_number, billing_flow, status, total_amount, currency, company_id,
  sub_brand_id, created_at, paid_at).

### 5. Update test infrastructure: `backend/tests/conftest.py`

- Add `GRANT SELECT, INSERT, UPDATE, DELETE ON invoices TO reel48_app` in the
  `setup_database` fixture's grant loop.

### 6. Verification

- Run `alembic upgrade head` against the test database to verify the migration applies cleanly.
- Run the full existing test suite (409 tests) to confirm no regressions.
- Run `alembic downgrade -1` then `alembic upgrade head` to verify reversibility.

## What NOT to Build Yet
- No service layer (Phase 2)
- No API endpoints (Phases 3-5)
- No Stripe integration (Phase 2)
- No webhook handler (Phase 4)
- No tests beyond migration verification (Phase 6)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Stripe Service & Invoice Service
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 7 Phase 2: the StripeService wrapper and InvoiceService business logic
layer.

## Context

Phase 1 is complete — the `invoices` table, `Invoice` model, and Pydantic schemas
exist. Now build the service layer that manages the invoice lifecycle and integrates
with Stripe.

Create a new branch `feature/module7-phase2-invoice-services` from `main`.

## What to Build

### 1. Stripe Service: `backend/app/services/stripe_service.py`

A thin wrapper around the Stripe Python SDK, following the External Service Integration
Pattern established by CognitoService (see backend CLAUDE.md). This service is
dependency-injectable and testable via mocking.

```python
class StripeService:
    def __init__(self, api_key: str, webhook_secret: str):
        self._api_key = api_key
        self._webhook_secret = webhook_secret

    async def get_or_create_customer(self, company: Company) -> str:
        """Returns stripe_customer_id, creating a Stripe Customer if needed."""
        # If company.stripe_customer_id exists, return it
        # Otherwise, create via stripe.Customer.create() and return the new ID
        # NOTE: Does NOT update company.stripe_customer_id — caller handles DB update

    async def create_invoice(
        self,
        customer_id: str,
        metadata: dict,
        auto_advance: bool = False,
    ) -> dict:
        """Creates a draft Stripe Invoice. Returns the Stripe invoice object as dict."""

    async def create_invoice_item(
        self,
        customer_id: str,
        invoice_id: str,
        description: str,
        quantity: int,
        unit_amount_cents: int,
        currency: str = "usd",
    ) -> dict:
        """Creates a Stripe InvoiceItem on the given invoice."""

    async def finalize_invoice(self, stripe_invoice_id: str) -> dict:
        """Finalizes a draft invoice, triggering Stripe to assign an invoice number."""

    async def send_invoice(self, stripe_invoice_id: str) -> dict:
        """Sends a finalized invoice to the customer via email."""

    async def void_invoice(self, stripe_invoice_id: str) -> dict:
        """Voids an invoice (e.g., if created in error)."""

    async def get_invoice(self, stripe_invoice_id: str) -> dict:
        """Retrieves current invoice state from Stripe."""

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> dict:
        """Verifies webhook signature and constructs the event object.
        Raises stripe.error.SignatureVerificationError on invalid signature."""


def get_stripe_service() -> StripeService:
    """FastAPI dependency factory."""
    return StripeService(
        api_key=settings.STRIPE_SECRET_KEY,
        webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
    )
```

Key implementation rules:
- `import stripe` inside method bodies (lazy import), not at module level
- Pin the API version: `stripe.api_version = "2024-06-20"`
- All amounts sent to Stripe must be in cents: `int(amount * 100)`
- All amounts stored locally are in dollars (Numeric(10,2))
- Set `auto_advance=False` on invoice creation (manual finalization required)
- Include `reel48_company_id` and `reel48_sub_brand_id` in all Stripe metadata
- Map Stripe SDK exceptions to AppException subclasses

### 2. Invoice Service: `backend/app/services/invoice_service.py`

The core business logic layer for invoice lifecycle management.

```python
class InvoiceService:
    def __init__(
        self,
        db: AsyncSession,
        stripe_service: StripeService | None = None,
    ):
        self.db = db
        self._stripe = stripe_service

    # === Platform Admin Operations (reel48_admin only) ===

    async def create_assigned_invoice(
        self,
        company_id: UUID,
        created_by: UUID,
        order_ids: list[UUID] | None = None,
        bulk_order_ids: list[UUID] | None = None,
        sub_brand_id: UUID | None = None,
    ) -> Invoice:
        """
        Flow 1: Create an assigned invoice for a client company from specific orders.
        - Looks up the company and its stripe_customer_id (creates if needed)
        - Creates a draft Stripe Invoice
        - Adds line items from the referenced orders/bulk orders
        - Creates the local Invoice record
        - Returns the Invoice with stripe_invoice_id populated
        """

    async def create_post_window_invoice(
        self,
        catalog_id: UUID,
        created_by: UUID,
    ) -> Invoice:
        """
        Flow 3: Create a consolidated invoice after a buying window closes.
        - Validates the catalog exists and has payment_model = 'invoice_after_close'
        - Validates the buying window has closed (buying_window_closes_at < now)
        - Gathers all approved orders placed against this catalog
        - Creates a single Stripe Invoice with all line items
        - Creates the local Invoice record with billing_flow = 'post_window'
        """

    async def create_self_service_invoice(
        self,
        order: Order,
        line_items: list[OrderLineItem],
    ) -> Invoice:
        """
        Flow 2: Auto-generate an invoice at checkout for a self-service catalog.
        Called during order placement (OrderService.create_order) when the catalog
        has payment_model = 'self_service'.
        - Looks up the company's stripe_customer_id
        - Creates and auto-finalizes a Stripe Invoice
        - Creates the local Invoice record with billing_flow = 'self_service'
        - NOTE: auto_advance=True for self-service (immediate billing)
        """

    async def finalize_invoice(self, invoice_id: UUID) -> Invoice:
        """Finalize a draft invoice. Stripe assigns an invoice number."""

    async def send_invoice(self, invoice_id: UUID) -> Invoice:
        """Send a finalized invoice to the client company."""

    async def void_invoice(self, invoice_id: UUID) -> Invoice:
        """Void an invoice (only draft or finalized, not paid)."""

    # === Webhook Handlers ===

    async def handle_webhook_event(self, event: dict) -> None:
        """
        Dispatch webhook events to specific handlers.
        Process idempotently — check current status before updating.
        """

    async def handle_invoice_finalized(self, stripe_invoice: dict) -> None:
        """Update local status to 'finalized', store invoice_number."""

    async def handle_invoice_sent(self, stripe_invoice: dict) -> None:
        """Update local status to 'sent'."""

    async def handle_invoice_paid(self, stripe_invoice: dict) -> None:
        """Update local status to 'paid', record paid_at timestamp."""

    async def handle_payment_failed(self, stripe_invoice: dict) -> None:
        """Update local status to 'payment_failed'."""

    async def handle_invoice_voided(self, stripe_invoice: dict) -> None:
        """Update local status to 'voided'."""

    # === Client-Facing Queries ===

    async def list_invoices(
        self,
        company_id: UUID,
        sub_brand_id: UUID | None,
        page: int,
        per_page: int,
        status: str | None = None,
        billing_flow: str | None = None,
    ) -> tuple[list[Invoice], int]:
        """List invoices with tenant scoping and optional filters."""

    async def get_invoice(
        self,
        invoice_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
    ) -> Invoice:
        """Get a single invoice by ID with tenant scoping."""

    # === Platform Admin Queries ===

    async def list_all_invoices(
        self,
        company_id: UUID | None = None,
        status: str | None = None,
        billing_flow: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Invoice], int]:
        """Cross-company invoice list for reel48_admin. Optional company_id filter."""
```

Key implementation rules:
- The `stripe_service` parameter is optional for backward compatibility (test convenience)
- Use `flush()` + `refresh()` before returning Invoice objects (MissingGreenlet prevention)
- Webhook handlers MUST be idempotent — check current status before updating
  (e.g., don't update a 'paid' invoice to 'finalized' if events arrive out of order)
- For assigned invoices, order_ids/bulk_order_ids reference the source orders for line items
- For self-service, the invoice is created during order placement
- For post-window, the invoice is created after the buying window closes
- The company's `stripe_customer_id` is updated on the Company record when first created
- Total amounts stored in dollars (Numeric), converted to cents only for Stripe API calls
- All Stripe operations wrapped in try/except with structured logging

### 3. Add environment variables to `backend/app/core/config.py`

Add to the Settings class:
- `STRIPE_SECRET_KEY: str = ""`
- `STRIPE_WEBHOOK_SECRET: str = ""`
- `STRIPE_API_VERSION: str = "2024-06-20"`

### 4. Wire up StripeService dependency in `backend/app/core/dependencies.py`

Add `get_stripe_service` import/export if not already there, or keep it in
`stripe_service.py` and import from there in routes.

## What NOT to Build Yet
- No API endpoints (Phases 3-5)
- No webhook route handler (Phase 4)
- No tests yet (Phase 6)
- No frontend integration
- Do NOT modify OrderService to auto-generate self-service invoices yet (Phase 5)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Platform Admin Invoice Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 7 Phase 3: the reel48_admin endpoints for creating, managing, and
viewing invoices across all client companies.

## Context

Phase 2 is complete — StripeService and InvoiceService exist. Now build the platform
admin endpoints that let reel48_admin create and manage invoices for client companies.

Create a new branch `feature/module7-phase3-platform-invoice-endpoints` from `main`.

## What to Build

### 1. Platform invoice routes: `backend/app/api/v1/platform/invoices.py`

Follow the platform endpoint pattern from `backend/app/api/v1/platform/products.py`.
All endpoints use `require_reel48_admin` as their auth dependency.

**Endpoints:**

```
POST   /api/v1/platform/invoices/                  — Create a draft invoice (assigned or post-window)
POST   /api/v1/platform/invoices/{invoice_id}/finalize  — Finalize a draft invoice
POST   /api/v1/platform/invoices/{invoice_id}/send      — Send a finalized invoice
POST   /api/v1/platform/invoices/{invoice_id}/void      — Void a draft or finalized invoice
GET    /api/v1/platform/invoices/                   — List all invoices (cross-company, with filters)
GET    /api/v1/platform/invoices/{invoice_id}       — Get invoice detail
```

**Create invoice request body:**
```json
{
  "company_id": "uuid",           // Required: target client company
  "billing_flow": "assigned",     // Required: 'assigned' or 'post_window'
  "sub_brand_id": "uuid",         // Optional: sub-brand scoping
  "order_ids": ["uuid", ...],     // For assigned: individual order IDs
  "bulk_order_ids": ["uuid", ...],// For assigned: bulk order IDs
  "catalog_id": "uuid",           // For post_window: the catalog with closed window
  "due_date": "2026-05-01"        // Optional: payment due date
}
```

**Validation rules for create:**
- `billing_flow` must be 'assigned' or 'post_window' (self_service is auto-generated)
- For 'assigned': at least one of `order_ids` or `bulk_order_ids` must be provided
- For 'post_window': `catalog_id` is required, catalog must have
  `payment_model = 'invoice_after_close'` and `buying_window_closes_at < now()`
- The target company must exist and be active
- Referenced orders/bulk orders must belong to the target company

**List endpoint query params:**
- `company_id` (optional filter)
- `status` (optional filter)
- `billing_flow` (optional filter)
- `page`, `per_page` (standard pagination)

### 2. Register the platform invoice router

Add the platform invoices router to `backend/app/api/v1/router.py` under the
platform prefix, following the pattern of existing platform routers.

### 3. Pydantic schemas for create request

Add `InvoiceCreateRequest` schema to `backend/app/schemas/invoice.py` if not already
covered by Phase 1's `InvoiceCreate` schema. This should match the create endpoint's
request body above.

## What NOT to Build Yet
- No client-facing endpoints (Phase 5)
- No webhook handler (Phase 4)
- No self-service auto-generation (Phase 5)
- No tests yet (Phase 6)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: Stripe Webhook Handler
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 7 Phase 4: the Stripe webhook endpoint that receives payment status
updates and syncs them to the local `invoices` table.

## Context

Phase 3 is complete — platform admin endpoints can create and manage invoices. Now
build the webhook endpoint that Stripe calls when invoice statuses change (paid,
finalized, failed, etc.).

Create a new branch `feature/module7-phase4-stripe-webhooks` from `main`.

## What to Build

### 1. Webhook route: `backend/app/api/v1/webhooks.py`

This is one of the UNAUTHENTICATED endpoint exceptions documented in backend CLAUDE.md.
It does NOT use `get_tenant_context`. Security comes from Stripe webhook signature
verification.

```python
@router.post("/api/v1/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """
    Stripe webhook receiver.
    - Verifies the webhook signature
    - Dispatches to InvoiceService.handle_webhook_event()
    - Returns 200 quickly (heavy processing can be deferred via SQS later)
    """
```

**Implementation rules:**
- Read the raw request body: `payload = await request.body()`
- Get the signature header: `sig_header = request.headers.get("stripe-signature")`
- Verify via `stripe_service.construct_webhook_event(payload, sig_header)`
- On invalid signature: return HTTP 400 (not 401/403)
- On valid signature: dispatch to `InvoiceService.handle_webhook_event(event)`
- Always return `{"status": "ok"}` with HTTP 200 after successful processing
- Log every webhook event with event type and Stripe invoice ID via structlog

**Webhook events to handle:**
| Stripe Event | Local Action |
|-------------|-------------|
| `invoice.finalized` | Status → 'finalized', store invoice_number, store stripe_invoice_url |
| `invoice.sent` | Status → 'sent' |
| `invoice.paid` | Status → 'paid', record paid_at timestamp |
| `invoice.payment_failed` | Status → 'payment_failed' |
| `invoice.voided` | Status → 'voided' |

**Idempotency rules:**
- Before updating, check the current local status
- Don't downgrade status (e.g., don't change 'paid' back to 'finalized')
- Status progression: draft → finalized → sent → paid (terminal)
- 'payment_failed' and 'voided' are also terminal states
- If the event has already been processed (status already matches), return 200 silently

### 2. Register the webhook router

Add the webhook router to `backend/app/api/v1/router.py`. This router should NOT
be nested under a prefix that requires authentication.

### 3. RLS considerations for webhook processing

The webhook endpoint does NOT have a tenant context (no JWT). The webhook handler
needs to look up the local invoice by `stripe_invoice_id` and update it. Since there's
no JWT, there are no RLS session variables set.

**Solution:** The webhook handler should use the `admin_db_session` pattern — either:
- Use a direct SQL query that bypasses RLS (not recommended), OR
- Set the RLS session variables based on the invoice's `company_id` after looking it up
  (preferred — maintains defense-in-depth), OR
- Use a superuser connection for webhook processing (simplest for now)

Choose the simplest approach: since the `get_db_session` dependency is overridden in
tests with superuser access, and the production connection can use appropriate
credentials for webhook processing, the webhook handler can work with the standard
session. The key is that it queries by `stripe_invoice_id` (globally unique) rather
than requiring tenant scoping.

**IMPORTANT:** If the standard session uses the `reel48_app` role with RLS, the webhook
handler must set `app.current_company_id = ''` (empty string) to bypass company
isolation — similar to how `get_tenant_context` handles `reel48_admin`. This makes the
webhook handler act as a platform-level operation.

## What NOT to Build Yet
- No client-facing endpoints (Phase 5)
- No self-service auto-generation (Phase 5)
- No tests yet (Phase 6)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: Client-Facing Endpoints & Self-Service Integration
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 7 Phase 5: the tenant-scoped invoice viewing endpoints for client
company admins, and the self-service invoice auto-generation integration with
the existing OrderService.

## Context

Phase 4 is complete — platform admin endpoints and webhook handler exist. Now build
the client-facing endpoints and integrate self-service invoice generation into the
existing order placement flow.

Create a new branch `feature/module7-phase5-client-endpoints` from `main`.

## What to Build

### 1. Client-facing invoice routes: `backend/app/api/v1/invoices.py`

These are tenant-scoped endpoints using `get_tenant_context`. Client company admins
can VIEW their invoices but NEVER create, edit, or send them.

**Endpoints:**
```
GET    /api/v1/invoices/                    — List invoices for the authenticated company
GET    /api/v1/invoices/{invoice_id}        — Invoice detail
GET    /api/v1/invoices/{invoice_id}/pdf    — Get Stripe-hosted invoice PDF URL
```

**Authorization:**
- `corporate_admin`: Sees all invoices across all sub-brands in their company
- `sub_brand_admin`: Sees invoices for their sub-brand only
- `regional_manager`: Sees invoices for their sub-brand only
- `employee`: NO access (403 on all invoice endpoints)
- See the Role-Based Access Matrix in `.claude/rules/authentication.md`

**List endpoint query params:**
- `status` (optional filter)
- `billing_flow` (optional filter)
- `page`, `per_page` (standard pagination)

**PDF endpoint:**
- Returns a redirect or JSON with the Stripe-hosted PDF URL
- If `stripe_pdf_url` is populated on the local record, return it directly
- Otherwise, fetch from Stripe API and cache on the local record

### 2. Register the client invoice router

Add to `backend/app/api/v1/router.py`.

### 3. Self-service invoice auto-generation

Modify `backend/app/services/order_service.py` to auto-generate an invoice when an
order is placed against a `self_service` catalog.

**Integration point:** In `OrderService.create_order()`, after the order and line items
are created successfully:

```python
# After order creation, check if catalog is self-service
if catalog.payment_model == "self_service":
    invoice_service = InvoiceService(self.db, stripe_service=self._stripe)
    try:
        await invoice_service.create_self_service_invoice(order, line_items)
    except Exception:
        logger.warning("self_service_invoice_creation_failed", order_id=str(order.id), exc_info=True)
        # Don't fail the order if invoice creation fails — it can be retried
```

**Key rules for self-service integration:**
- Invoice creation is non-blocking — if Stripe fails, the order still succeeds
- The invoice references the order via `order_id`
- `billing_flow = 'self_service'`
- `auto_advance = True` for self-service (Stripe automatically sends to customer)
- `created_by` is the employee placing the order (resolved via `resolve_current_user_id`)
- Log warnings on failure (same pattern as email notifications in Module 6)

### 4. Add StripeService as optional dependency on OrderService

Update `OrderService.__init__` to accept an optional `stripe_service` parameter
(same pattern as `approval_service` accepting `email_service`).

## What NOT to Build Yet
- No tests yet (Phase 6)
- No frontend integration
- No analytics integration (Module 8)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: Tests — Functional, Isolation, Authorization, Webhooks
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 7 Phase 6: comprehensive tests for all invoicing functionality.

## Context

Phases 1-5 are complete — the full invoicing feature is implemented. Now write
the test suite covering all three mandatory test categories (functional, isolation,
authorization) plus webhook-specific tests.

Create a new branch `feature/module7-phase6-invoice-tests` from `main`.

## What to Build

### 1. Mock Stripe Service: Add to `backend/tests/conftest.py`

Follow the External Service Mock Pattern established by `MockCognitoService` and
`MockEmailService`:

```python
class MockStripeService:
    """Mock StripeService that records calls without hitting Stripe API."""

    def __init__(self):
        self.created_customers: list[dict] = []
        self.created_invoices: list[dict] = []
        self.created_invoice_items: list[dict] = []
        self.finalized_invoices: list[str] = []
        self.sent_invoices: list[str] = []
        self.voided_invoices: list[str] = []
        self._invoice_counter = 0

    async def get_or_create_customer(self, company) -> str:
        customer_id = f"cus_test_{uuid4().hex[:8]}"
        self.created_customers.append({"company_id": str(company.id), "customer_id": customer_id})
        return company.stripe_customer_id or customer_id

    async def create_invoice(self, customer_id, metadata, auto_advance=False) -> dict:
        self._invoice_counter += 1
        invoice_id = f"in_test_{self._invoice_counter}"
        invoice = {
            "id": invoice_id,
            "customer": customer_id,
            "metadata": metadata,
            "auto_advance": auto_advance,
            "hosted_invoice_url": f"https://invoice.stripe.com/i/{invoice_id}",
            "invoice_pdf": f"https://invoice.stripe.com/i/{invoice_id}/pdf",
            "status": "draft",
        }
        self.created_invoices.append(invoice)
        return invoice

    async def create_invoice_item(self, customer_id, invoice_id, description, quantity, unit_amount_cents, currency="usd") -> dict:
        item = {
            "invoice": invoice_id,
            "description": description,
            "quantity": quantity,
            "unit_amount": unit_amount_cents,
            "currency": currency,
        }
        self.created_invoice_items.append(item)
        return item

    async def finalize_invoice(self, stripe_invoice_id) -> dict:
        self.finalized_invoices.append(stripe_invoice_id)
        return {"id": stripe_invoice_id, "status": "open", "number": f"INV-{len(self.finalized_invoices):04d}"}

    async def send_invoice(self, stripe_invoice_id) -> dict:
        self.sent_invoices.append(stripe_invoice_id)
        return {"id": stripe_invoice_id, "status": "open"}

    async def void_invoice(self, stripe_invoice_id) -> dict:
        self.voided_invoices.append(stripe_invoice_id)
        return {"id": stripe_invoice_id, "status": "void"}

    def construct_webhook_event(self, payload, sig_header) -> dict:
        """For webhook tests: return parsed JSON directly (no signature verification)."""
        import json
        return json.loads(payload)
```

Add an autouse fixture:
```python
@pytest.fixture(autouse=True)
def mock_stripe(app) -> MockStripeService:
    mock = MockStripeService()
    app.dependency_overrides[get_stripe_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_stripe_service, None)
```

### 2. Invoice test file: `backend/tests/test_invoices.py`

#### Functional Tests (Assigned Invoice — Flow 1)
- `test_create_assigned_invoice_from_orders` — reel48_admin creates invoice from approved orders, verify Stripe calls and local record
- `test_create_assigned_invoice_from_bulk_orders` — Same for bulk orders
- `test_create_assigned_invoice_requires_order_ids_or_bulk_order_ids` — 422 if neither provided
- `test_finalize_invoice` — Verify status changes to 'finalized' and invoice_number is set
- `test_send_finalized_invoice` — Verify status changes to 'sent'
- `test_void_draft_invoice` — Verify status changes to 'voided'
- `test_cannot_void_paid_invoice` — 403 if invoice is already paid

#### Functional Tests (Post-Window — Flow 3)
- `test_create_post_window_invoice` — reel48_admin creates consolidated invoice after window closes
- `test_cannot_create_post_window_invoice_before_window_closes` — 422 if window still open
- `test_post_window_invoice_requires_invoice_after_close_catalog` — 422 for self_service catalog

#### Functional Tests (Self-Service — Flow 2)
- `test_self_service_order_auto_generates_invoice` — Place order on self-service catalog, verify invoice created
- `test_self_service_invoice_has_correct_billing_flow` — billing_flow = 'self_service'
- `test_self_service_invoice_failure_does_not_block_order` — Stripe failure logged but order succeeds

#### Functional Tests (Client Viewing)
- `test_list_invoices_as_corporate_admin` — Sees all company invoices
- `test_get_invoice_detail` — Returns full invoice data
- `test_get_invoice_pdf_url` — Returns Stripe PDF URL

#### Webhook Tests
- `test_webhook_invoice_paid` — Simulate invoice.paid event, verify local status update
- `test_webhook_invoice_payment_failed` — Simulate payment failure
- `test_webhook_invoice_finalized` — Verify invoice_number stored
- `test_webhook_invalid_signature_returns_400` — Invalid signature rejected
- `test_webhook_idempotent_processing` — Same event processed twice produces same result
- `test_webhook_does_not_downgrade_status` — Paid invoice not reverted to finalized

#### Authorization Tests
- `test_only_reel48_admin_can_create_invoices` — corporate_admin, sub_brand_admin, employee all get 403
- `test_only_reel48_admin_can_finalize_invoices` — Same
- `test_employee_cannot_view_invoices` — 403 on all invoice endpoints
- `test_corporate_admin_can_view_own_company_invoices` — 200
- `test_sub_brand_admin_can_view_own_brand_invoices` — 200
- `test_regional_manager_can_view_own_brand_invoices` — 200

#### Isolation Tests (CRITICAL)
- `test_company_b_cannot_see_company_a_invoices` — Cross-company isolation
- `test_brand_a2_cannot_see_brand_a1_invoices` — Cross-sub-brand isolation within same company
- `test_corporate_admin_sees_all_sub_brand_invoices` — Corporate admin cross-sub-brand visibility
- `test_reel48_admin_sees_all_invoices` — Platform admin cross-company visibility

### 3. RLS isolation tests: Add to `backend/tests/test_isolation.py`

Add invoice-specific RLS tests following the existing pattern (direct session
variables with non-superuser session):
- `test_invoices_company_isolation_rls` — Set company_id A, query, verify no company B invoices
- `test_invoices_sub_brand_scoping_rls` — Set sub_brand_id A1, verify no A2 invoices
- `test_invoices_reel48_admin_bypass_rls` — Empty company_id sees all invoices

### 4. Verification

- Run the full test suite. All existing tests (409+) must still pass.
- All new invoice tests must pass.
- No regressions in Modules 1-6.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: End-of-Module Harness Review
# ═══════════════════════════════════════════════════════════════════════════════

Perform the mandatory post-module harness review for Module 7 (Invoicing & Client
Billing). Follow the Harness Maintenance Protocol defined in the root CLAUDE.md.

## Context

Module 7 is complete across Phases 1-6. All tests pass. Perform the TRIGGER 2:
Post-Module Harness Review before Module 8 (Analytics Dashboard) begins.

Create a new branch `chore/module7-harness-review` from `main`.

## Checklist

### 1. Pattern Consistency Scan
Review all Module 7 code for consistency with established patterns:
- Do all endpoints follow the route → service → model pattern?
- Are response formats consistent (`ApiResponse[T]`, `ApiListResponse[T]`)?
- Are naming conventions consistent (snake_case URLs, plural nouns)?
- Does the `invoices` table have correct RLS policies?
- Do all platform endpoints use `require_reel48_admin`?
- Do all client endpoints use `get_tenant_context`?
- Is the webhook endpoint properly unauthenticated with signature verification?

### 2. Rule Effectiveness Review
For each rule file that activated during Module 7:
- `stripe-invoicing.md` — Did it provide sufficient guidance for the Stripe integration?
- `api-endpoints.md` — Did the platform endpoint exception work correctly?
- `database-migrations.md` — Did the migration follow the template?
- `testing.md` — Did the mock pattern guidance work for MockStripeService?
- `authentication.md` — Is the Role-Based Access Matrix correct for invoice visibility?

### 3. Harness Updates
Update the following based on Module 7 implementation:
- **Backend CLAUDE.md:** Add Module 7 table schema documentation, StripeService
  integration pattern, webhook handler pattern
- **`.claude/rules/stripe-invoicing.md`:** Update with any lessons learned during
  implementation (e.g., edge cases in webhook idempotency, Stripe API version handling)
- **`.claude/rules/authentication.md`:** Verify invoice access in the Role-Based
  Access Matrix matches implementation
- **`docs/harness-changelog.md`:** Add Module 7 completion entry

### 4. Gap Analysis
Identify scenarios the harness didn't cover:
- Self-service invoice failure handling (non-blocking pattern)
- Webhook RLS bypass pattern (how to handle unauthenticated DB operations)
- Post-window invoice timing edge cases
- Any Stripe-specific patterns that should be documented for future reference

### 5. ADR Currency Check
Review ADR-006 (Stripe for Invoicing). Update the "Consequences" or "Risks" sections
if implementation revealed anything not originally anticipated.

### 6. Commit
Commit all harness updates with:
`chore: Module 7 harness review — add invoicing patterns docs and changelog entry`
