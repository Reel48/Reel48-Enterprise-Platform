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

## Invoice Creation Pattern

### From Approved Orders
```python
# WHY: Invoices are created ONLY from approved orders. This prevents
# billing for orders that haven't been reviewed. The invoice carries
# both company_id and sub_brand_id for tenant isolation and sub-brand
# reporting.

async def create_invoice_from_order(
    order: Order,
    context: TenantContext,
    db: AsyncSession,
) -> Invoice:
    stripe_customer_id = await get_or_create_stripe_customer(order.company)

    # Create Stripe invoice
    stripe_invoice = stripe.Invoice.create(
        customer=stripe_customer_id,
        metadata={
            "reel48_company_id": str(order.company_id),
            "reel48_sub_brand_id": str(order.sub_brand_id),
            "reel48_order_id": str(order.id),
        },
        auto_advance=False,  # Keep as draft until explicitly finalized
    )

    # Add line items from order
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
        company_id=order.company_id,
        sub_brand_id=order.sub_brand_id,
        order_id=order.id,
        stripe_invoice_id=stripe_invoice.id,
        stripe_invoice_url=stripe_invoice.hosted_invoice_url,
        status="draft",
        total_amount=order.total_amount,
    )
    db.add(invoice)
    await db.commit()
    return invoice
```

### Critical Rules for Invoice Creation
- Invoices are ALWAYS created as **draft** first (`auto_advance=False`)
- An admin must explicitly finalize and send the invoice
- Line item amounts are converted to **cents** for Stripe (`int(amount * 100)`)
- Every Stripe object carries `reel48_company_id` and `reel48_sub_brand_id` in metadata
- The local `invoices` table mirrors Stripe data for tenant-scoped querying

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
id                  UUID        PRIMARY KEY
company_id          UUID        NOT NULL (FK → companies, tenant isolation)
sub_brand_id        UUID        NULL (FK → sub_brands, sub-brand scoping)
order_id            UUID        NULL (FK → orders, for individual orders)
bulk_order_id       UUID        NULL (FK → bulk_orders, for bulk orders)
stripe_invoice_id   TEXT        NOT NULL UNIQUE (Stripe's invoice ID, e.g., "in_xxx")
stripe_invoice_url  TEXT        NULL (hosted invoice page URL)
stripe_pdf_url      TEXT        NULL (invoice PDF download URL)
invoice_number      TEXT        NULL (assigned by Stripe on finalization)
status              TEXT        NOT NULL (draft, finalized, sent, paid, payment_failed, voided)
total_amount        NUMERIC     NOT NULL (in dollars, for local queries)
currency            TEXT        NOT NULL DEFAULT 'usd'
due_date            DATE        NULL
paid_at             TIMESTAMP   NULL
created_at          TIMESTAMP   NOT NULL
updated_at          TIMESTAMP   NOT NULL
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
1. **Functional:** Create invoice from approved order, verify line items match
2. **Functional:** Finalize invoice, verify Stripe status updates locally
3. **Functional:** Simulate `invoice.paid` webhook, verify local status update
4. **Isolation:** Company B cannot see Company A's invoices
5. **Isolation:** Sub-Brand Y cannot see Sub-Brand X's invoices
6. **Authorization:** Employees cannot create or finalize invoices
7. **Authorization:** Regional managers can view but not create invoices
8. **Idempotency:** Processing the same webhook event twice produces no duplicate updates
9. **Webhook security:** Requests with invalid signatures are rejected with 400

## Common Mistakes to Avoid
- ❌ Accepting Stripe customer IDs from request parameters (derive from TenantContext)
- ❌ Storing amounts in cents in the local database (store dollars; convert to cents only for Stripe API calls)
- ❌ Forgetting to verify webhook signatures (security vulnerability)
- ❌ Processing webhooks synchronously for heavy operations (use SQS)
- ❌ Not handling duplicate webhook deliveries (Stripe may retry)
- ❌ Using Stripe as the sole data store (maintain local records for tenant-scoped queries)
- ❌ Auto-advancing invoices (always keep as draft until admin explicitly finalizes)
- ❌ Importing `stripe` in frontend code (server-side only)
