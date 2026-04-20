# ADR-006: Stripe for Invoicing and Client Billing

> ⚠ **SUPERSEDED** by ADR-010 (pending, to be authored in Session D). In-app invoicing
> and Stripe integration are being removed entirely. Commerce (checkout, invoicing,
> payments) will be owned by a future Shopify integration. See
> `~/.claude/plans/yes-please-write-the-memoized-karp.md`.

## Status
Superseded by ADR-010

#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  This ADR documents the decision to use Stripe as the invoicing and        ║
# ║  billing platform for Reel48+. Invoicing is a core revenue function:       ║
# ║  every approved order generates an invoice sent to the client company.     ║
# ║  This decision affects the payment data model, webhook architecture,       ║
# ║  and the one exception to the "every endpoint requires JWT auth" rule.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

## Status
Accepted

## Date
2026-04-06

## Context
Reel48+ manages apparel orders on behalf of enterprise clients. When orders are
approved, the client company must be invoiced for the cost of the apparel. This
requires a system that can:

1. Create invoices programmatically from approved order data
2. Assign invoices to specific client companies (mapped to Reel48+ tenants)
3. Track sub-brand context on invoices for per-brand financial reporting
4. Send invoices to clients with hosted payment pages
5. Receive real-time payment status updates
6. Generate PDF invoices for record-keeping
7. Handle both individual orders and consolidated bulk orders on a single invoice

The platform needs a reliable, enterprise-grade invoicing system. Building
custom invoicing infrastructure (payment processing, PDF generation, tax
calculation, payment tracking) is outside Reel48+'s core competency and would
add significant build and maintenance burden.

## Decision
Use **Stripe** as the invoicing and payment platform with a **server-side
integration** pattern. The backend manages all Stripe objects (Customers,
Invoices, InvoiceItems) through the Stripe Python SDK. The frontend displays
invoice data fetched through Reel48+ API endpoints, never directly from Stripe.

**Key mapping:**
- Each Reel48+ company maps to one Stripe Customer
- Sub-brand context is stored as Stripe metadata on invoices
- Approved orders generate draft Stripe Invoices with line items
- Payment status flows back via Stripe webhooks

**Webhook exception:** The Stripe webhook endpoint is one of a small number of
API endpoints that do not require JWT authentication. It is secured by Stripe
webhook signature verification instead. (See also ADR-007 for the self-registration
endpoints, which are the other unauthenticated exceptions.)

## Alternatives Considered

### Build Custom Invoicing
- **Pros:** Full control over invoice format and workflow; no third-party dependency
- **Cons:** Requires building PDF generation, payment processing, tax calculation,
  email delivery, payment tracking, and reconciliation from scratch; ongoing PCI
  compliance burden; months of additional development time
- **Why rejected:** Reel48+ is an apparel management platform, not a payments
  company. The engineering effort to build production-grade invoicing would
  delay launch by 4-8 weeks and create ongoing maintenance burden.

### QuickBooks / Xero Integration
- **Pros:** Full accounting suite; familiar to finance teams; invoice + bookkeeping
  in one system
- **Cons:** APIs are designed for accounting workflows, not programmatic invoice
  generation; complex OAuth flows; rate limits poorly suited to high-volume
  programmatic use; adds a second external system alongside AWS
- **Why rejected:** These tools are designed for human-driven accounting workflows.
  Reel48+ needs programmatic, API-first invoice creation triggered by order
  approval events. Stripe's API is purpose-built for this pattern.

### Square Invoicing
- **Pros:** Competitive pricing; good invoicing API
- **Cons:** Smaller developer ecosystem; fewer webhook events; less granular
  metadata support; weaker enterprise adoption
- **Why rejected:** Stripe has stronger metadata support (critical for carrying
  tenant and sub-brand context on invoices), a more mature webhook system, and
  a larger ecosystem of documentation and community support for the Python SDK.

## Consequences

### Positive
- Invoicing can be built in a single module (~2 weeks) instead of months
- Stripe handles PCI compliance, payment processing, and tax calculation
- Hosted invoice pages give clients a professional payment experience
- Webhook-driven status updates keep local records in sync without polling
- Stripe metadata carries tenant and sub-brand context for financial reporting
- PDF generation is handled by Stripe automatically

### Negative
- External dependency on Stripe for a core revenue function
- Transaction fees (2.9% + 30c per payment, or negotiated enterprise rates)
- Local invoice records must be kept in sync with Stripe via webhooks
- Stripe webhook endpoint is the one exception to the JWT auth pattern,
  requiring separate security handling (signature verification)

### Risks
- **Stripe outage affects invoicing:** Mitigated by local invoice records that
  allow viewing existing invoices even if Stripe is temporarily unreachable.
  New invoice creation would be blocked during an outage.
  _Implementation note (2026-04-09):_ Self-service invoice creation at checkout is
  wrapped in try/except — if Stripe is unavailable, the order still succeeds and
  the invoice can be created manually later. This non-blocking pattern prevents
  Stripe outages from blocking employee order placement.
- **Webhook delivery failures:** Mitigated by Stripe's automatic retry logic
  (up to 72 hours) and idempotent webhook processing on our end.
  _Implementation note (2026-04-09):_ Idempotency is enforced via a `_STATUS_ORDER`
  priority dict that prevents status regression when events arrive out of order or
  are delivered multiple times.
- **Data drift between Stripe and local records:** Mitigated by treating Stripe
  as the source of truth for payment status and using webhooks (not polling)
  for all status updates. Periodic reconciliation job recommended post-launch.
- **Webhook endpoint RLS bypass:** _Discovered during implementation (2026-04-09)._
  The Stripe webhook endpoint must query tenant-scoped tables (invoices) without JWT
  context. It sets RLS session variables to empty strings (same bypass as reel48_admin).
  This is secure because the endpoint verifies the Stripe signature before any DB
  operations, and the bypass only enables reading — it does not create cross-tenant data.

## References
- Stripe Invoicing API: https://stripe.com/docs/invoicing
- Stripe Webhooks: https://stripe.com/docs/webhooks
- Stripe Python SDK: https://stripe.com/docs/api?lang=python
