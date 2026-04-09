---
globs: "**/invoice*,**/billing*,**/stripe*,**/webhook*,**/payment*"
---

# Rule: Stripe Invoicing & Client Billing
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This rule activates when Claude Code is working on invoicing, billing,    ║
# ║  Stripe integration, or webhook handling files. It enforces the patterns   ║
# ║  for creating, managing, and tracking invoices assigned to client          ║
# ║  companies through Stripe.                                                ║
# ║                                                                            ║
# ║  WHY THIS RULE?                                                            ║
# ║                                                                            ║
# ║  Invoicing is how Reel48+ generates revenue. It touches payment data,      ║
# ║  financial records, and external APIs (Stripe). Mistakes here have real    ║
# ║  financial consequences: incorrect amounts, invoices sent to wrong         ║
# ║  clients, duplicate charges, or lost payment notifications. This rule      ║
# ║  ensures Claude Code treats invoicing with the rigor it requires.          ║
# ║                                                                            ║
# ║  The Stripe integration also introduces a unique pattern: webhook          ║
# ║  endpoints that receive external requests without JWT authentication.      ║
# ║  This is the ONLY exception to the "every endpoint uses TenantContext"     ║
# ║  rule, and it must be handled carefully.                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

## Stripe API Integration Pattern

### Server-Side Only
- ALL Stripe API calls happen on the **backend only**
- The frontend NEVER imports or calls the Stripe SDK directly
- The frontend displays invoice data fetched through our own API endpoints
- Store the Stripe secret key in environment variables (`STRIPE_SECRET_KEY`), never in code
- Store the webhook signing secret in environment variables (`STRIPE_WEBHOOK_SECRET`)

### Stripe Client Setup
```python
# WHY: A centralized Stripe client ensures consistent configuration and
# makes it easy to swap API keys between environments (dev/staging/prod).

import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = "2024-06-20"  # Pin the API version to avoid breaking changes
```

### Company-to-Customer Mapping
```python
# WHY: Each Reel48+ company maps to exactly one Stripe Customer. This mapping
# is created during company onboarding and stored on the companies table.
# All invoices for that company are created against this Stripe Customer.

async def get_or_create_stripe_customer(company: Company) -> str:
    """Returns the stripe_customer_id for a company, creating if needed."""
    if company.stripe_customer_id:
        return company.stripe_customer_id

    customer = stripe.Customer.create(
        name=company.name,
        metadata={
            "reel48_company_id": str(company.id),
        },
    )
    company.stripe_customer_id = customer.id
    await db.commit()
    return customer.id
```

## Who Creates Invoices

**CRITICAL:** Only `reel48_admin` can create and send invoices. Reel48 is the vendor;
client companies are the customers being billed. Client admins can VIEW their invoices
but never create, edit, or send them. The one exception is auto-generated invoices in
the self-service flow (where Reel48 pre-approved the pricing).

## Three Billing Flows

### Flow 1: Reel48-Assigned Invoices (Bulk/Custom Orders)
The `reel48_admin` manually creates an invoice for a client company after a bulk order
or custom order is fulfilled. Used when pricing is unique or negotiated per-order.

### Flow 2: Self-Service (Pre-Priced Catalog)
Products are approved and priced by `reel48_admin` ahead of time. The catalog
`payment_model` is set to `self_service`. When employees purchase, a Stripe invoice
is auto-generated at checkout. No further Reel48 approval needed per purchase.

### Flow 3: Post-Window Invoicing
The `reel48_admin` creates a catalog with `payment_model = invoice_after_close` and
sets a buying window. Employees order during the window. After the window closes,
the `reel48_admin` creates a consolidated invoice for all orders in that window.
The buying window deadline can also be adjusted by the client company's admin.

## Invoice Creation Pattern

### Reel48 Admin Creating an Invoice (Flows 1 & 3)
```python
# WHY: The reel48_admin creates invoices on behalf of client companies.
# The company_id comes from the target company, NOT from the admin's
# TenantContext (since reel48_admin has no company_id).

async def create_invoice_for_company(
    company_id: UUID,  # Target client company — looked up, not from JWT
    order_ids: list[UUID],
    context: TenantContext,
    db: AsyncSession,
) -> Invoice:
    # CRITICAL: Only reel48_admin can call this
    if not context.is_reel48_admin:
        raise ForbiddenError("Only Reel48 platform admins can create invoices")

    company = await db.get(Company, company_id)
    stripe_customer_id = await get_or_create_stripe_customer(company)

    # Create Stripe invoice
    stripe_invoice = stripe.Invoice.create(
        customer=stripe_customer_id,
        metadata={
            "reel48_company_id": str(company_id),
            "reel48_created_by": context.user_id,
        },
        auto_advance=False,  # Keep as draft until explicitly finalized
    )

    # Add line items from orders
    for order in orders:
        for item in order.line_items:
            stripe.InvoiceItem.create(
                customer=stripe_customer_id,
                invoice=stripe_invoice.id,
                description=f"{item.product.name} (x{item.quantity})",
                quantity=item.quantity,
                unit_amount=int(item.unit_price * 100),  # Stripe uses cents
                currency="usd",
            )

    # Create local invoice record
    invoice = Invoice(
        company_id=company_id,
        sub_brand_id=orders[0].sub_brand_id,
        stripe_invoice_id=stripe_invoice.id,
        stripe_invoice_url=stripe_invoice.hosted_invoice_url,
        billing_flow="assigned",  # or "post_window"
        status="draft",
        total_amount=sum(o.total_amount for o in orders),
    )
    db.add(invoice)
    await db.commit()
    return invoice
```

### Critical Rules for Invoice Creation
- Only `reel48_admin` can create, finalize, and send invoices (except self-service auto-generation)
- Invoices are ALWAYS created as **draft** first (`auto_advance=False`)
- The `reel48_admin` must explicitly finalize and send the invoice
- Line item amounts are converted to **cents** for Stripe (`int(amount * 100)`)
- Every Stripe object carries `reel48_company_id` and `reel48_sub_brand_id` in metadata
- The local `invoices` table mirrors Stripe data for tenant-scoped querying
- The `billing_flow` field must be set correctly: `assigned`, `self_service`, or `post_window`
- For `post_window` invoices, wait until the buying window closes before creating the invoice
- Client admins can VIEW their company's invoices but NEVER create, edit, or send them

## Webhook Handling

### Endpoint Pattern
```python
# WHY: The Stripe webhook endpoint is the ONLY endpoint that does not use
# JWT authentication. Stripe sends POST requests directly to this URL.
# Security comes from verifying the webhook signature, not from JWTs.

@router.post("/api/v1/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process the event
    if event["type"] == "invoice.paid":
        await handle_invoice_paid(event["data"]["object"], db)
    elif event["type"] == "invoice.payment_failed":
        await handle_payment_failed(event["data"]["object"], db)
    elif event["type"] == "invoice.finalized":
        await handle_invoice_finalized(event["data"]["object"], db)

    return {"status": "ok"}
```

### Webhook Security Rules
1. **ALWAYS verify the signature** using `stripe.Webhook.construct_event()`
2. **Process idempotently** — check if the event has already been processed before acting
3. **Use the raw request body** for signature verification (not parsed JSON)
4. **Return 200 quickly** — do heavy processing asynchronously via SQS if needed
5. **Log every webhook event** with the event type and Stripe invoice ID for debugging

### Webhook Events to Handle
| Stripe Event | Action |
|-------------|--------|
| `invoice.finalized` | Update local invoice status to "finalized", store invoice number |
| `invoice.sent` | Update local invoice status to "sent" |
| `invoice.paid` | Update local invoice status to "paid", record payment date |
| `invoice.payment_failed` | Update local invoice status to "payment_failed", alert admin |
| `invoice.voided` | Update local invoice status to "voided" |

## Invoice Data Model

### Required Columns on `invoices` Table
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, tenant isolation)
sub_brand_id            UUID        NULL (FK → sub_brands, sub-brand scoping)
order_id                UUID        NULL (FK → orders, for individual orders)
bulk_order_id           UUID        NULL (FK → bulk_orders, for bulk orders)
catalog_id              UUID        NULL (FK → catalogs, for self-service/post-window flows)
stripe_invoice_id       TEXT        NOT NULL UNIQUE (Stripe's invoice ID, e.g., "in_xxx")
stripe_invoice_url      TEXT        NULL (hosted invoice page URL)
stripe_pdf_url          TEXT        NULL (invoice PDF download URL)
invoice_number          TEXT        NULL (assigned by Stripe on finalization)
billing_flow            TEXT        NOT NULL (assigned, self_service, post_window)
status                  TEXT        NOT NULL (draft, finalized, sent, paid, payment_failed, voided)
total_amount            NUMERIC     NOT NULL (in dollars, for local queries)
currency                TEXT        NOT NULL DEFAULT 'usd'
due_date                DATE        NULL
buying_window_closes_at TIMESTAMP   NULL (for post_window flow only)
created_by              UUID        NOT NULL (FK → users, the reel48_admin who created it)
paid_at                 TIMESTAMP   NULL
created_at              TIMESTAMP   NOT NULL
updated_at              TIMESTAMP   NOT NULL
```

### RLS Policies
The `invoices` table MUST have standard company isolation and sub-brand scoping
policies, created in the same migration as the table (per database-migrations rule).

## Environment Variables
```
STRIPE_SECRET_KEY=sk_test_...        # Stripe secret API key
STRIPE_WEBHOOK_SECRET=whsec_...      # Webhook endpoint signing secret
STRIPE_PUBLISHABLE_KEY=pk_test_...   # Only if client-side Stripe.js is needed later
```

### Frontend Environment
```
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...   # Only if Stripe.js needed
```
Note: The initial implementation does NOT need Stripe.js on the frontend. Invoices are
managed entirely server-side. The publishable key is only needed if a future iteration
adds client-side payment collection (e.g., Stripe Checkout for self-service payment).

## Testing Invoice Functionality

### Use Stripe Test Mode
- All development and testing uses Stripe **test mode** API keys
- Use Stripe's test clock feature for testing subscription/due date scenarios
- Use Stripe CLI (`stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`)
  to test webhook delivery locally

### Required Test Cases
1. **Functional (Assigned):** reel48_admin creates invoice from approved bulk order, verify line items match
2. **Functional (Self-Service):** Employee purchases from self-service catalog, auto-invoice generated
3. **Functional (Post-Window):** reel48_admin creates consolidated invoice after buying window closes
4. **Functional:** reel48_admin finalizes invoice, verify Stripe status updates locally
5. **Functional:** Simulate `invoice.paid` webhook, verify local status update
6. **Isolation:** Company B cannot see Company A's invoices
7. **Isolation:** Sub-Brand Y cannot see Sub-Brand X's invoices
8. **Authorization:** Only reel48_admin can create and finalize invoices
9. **Authorization:** corporate_admin can view their company's invoices but NOT create them
10. **Authorization:** sub_brand_admin and regional_manager can view their brand's invoices only
11. **Authorization:** Employees cannot view, create, or finalize invoices
12. **Billing Flow:** `billing_flow` field is correctly set for each flow type
13. **Buying Window:** Post-window invoices cannot be created before the window closes
14. **Idempotency:** Processing the same webhook event twice produces no duplicate updates
15. **Webhook security:** Requests with invalid signatures are rejected with 400

## Implementation Lessons (Module 7)

# --- ADDED 2026-04-09 during Module 7 post-module harness review ---
# Reason: Module 7 implementation revealed patterns and edge cases not
# anticipated by the original rule file.
# Impact: Future sessions working on invoicing or Stripe code avoid these pitfalls.

### Webhook RLS Bypass Pattern
The webhook endpoint is unauthenticated (no JWT → no TenantContext). To query the
`invoices` table (which has RLS), the webhook handler must manually set the PostgreSQL
session variables to empty strings before querying:
```python
await db.execute(text("SET LOCAL app.current_company_id = ''"))
await db.execute(text("SET LOCAL app.current_sub_brand_id = ''"))
```
This triggers the same RLS bypass as `reel48_admin`, enabling cross-company invoice
lookup by `stripe_invoice_id`. This pattern applies to any future webhook handler that
needs to query tenant-scoped tables without JWT context.

### Idempotent Webhook Processing with Status Priority
Stripe may deliver events out of order (e.g., `invoice.sent` arriving after
`invoice.paid`). The `_STATUS_ORDER` dict in `InvoiceService` assigns numeric
priority to each status. Webhook handlers only update the local status when the
incoming status has a **higher** priority than the current status. This prevents
status regression and makes processing idempotent across duplicate deliveries.

### Self-Service Invoices: Non-Blocking and auto_advance=True
Self-service invoice creation (during order placement) differs from admin-created
invoices:
- Uses `auto_advance=True` (Stripe auto-sends the invoice) vs `auto_advance=False`
  for admin-created invoices.
- Wrapped in try/except — if Stripe fails, the order still succeeds. The invoice
  can be created manually later.
- `created_by` is the order owner (employee), not a reel48_admin.

### StripeService: Synchronous Webhook Verification
`construct_webhook_event()` is intentionally **not async**. Stripe signature
verification is CPU-bound (HMAC computation), not I/O-bound. The method raises
`stripe.error.SignatureVerificationError` on invalid signatures, which the webhook
endpoint catches and returns 400.

### Stripe API Version Pinning
The `StripeService` sets `stripe.api_version` from `settings.STRIPE_API_VERSION`
(configured in environment variables). Pinning the API version prevents breaking
changes when Stripe rolls out new versions. The version should only be updated
deliberately after reviewing Stripe's changelog.

## Common Mistakes to Avoid
- ❌ Allowing client admins to create invoices (only `reel48_admin` creates invoices)
- ❌ Accepting Stripe customer IDs from request parameters (look up from the target company)
- ❌ Using the admin's TenantContext company_id for invoices (reel48_admin has no company_id; use the target company_id from the request)
- ❌ Storing amounts in cents in the local database (store dollars; convert to cents only for Stripe API calls)
- ❌ Forgetting to verify webhook signatures (security vulnerability)
- ❌ Processing webhooks synchronously for heavy operations (use SQS)
- ❌ Not handling duplicate webhook deliveries (Stripe may retry)
- ❌ Using Stripe as the sole data store (maintain local records for tenant-scoped queries)
- ❌ Auto-advancing invoices (always keep as draft until reel48_admin explicitly finalizes)
- ❌ Importing `stripe` in frontend code (server-side only)
- ❌ Creating post-window invoices before the buying window has closed
- ❌ Omitting the `billing_flow` field on invoice records
- ❌ Letting self-service invoices skip Stripe (all payments go through Stripe)
- ❌ Using `auto_advance=True` for admin-created invoices (only self-service uses auto_advance)
- ❌ Forgetting to set RLS session variables in the webhook handler (causes empty query results)
- ❌ Downgrading invoice status on out-of-order webhook events (use `_STATUS_ORDER` priority)
