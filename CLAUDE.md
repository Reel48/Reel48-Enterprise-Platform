# Reel48+ Enterprise Platform — Root CLAUDE.md
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This is the ROOT CLAUDE.md — the single most important file in the        ║
# ║  entire harness. Claude Code reads this file automatically at the start    ║
# ║  of every session. Think of it as the "constitution" for your codebase:    ║
# ║  it encodes the decisions, conventions, and patterns that every piece of   ║
# ║  generated code must follow.                                               ║
# ║                                                                            ║
# ║  WHY DOES IT MATTER?                                                       ║
# ║                                                                            ║
# ║  Claude Code agents are stateless — they have no memory between sessions.  ║
# ║  Without this file, every session starts from zero context. Claude might   ║
# ║  use a different naming convention, skip multi-tenancy isolation, or       ║
# ║  structure files differently each time. This file ensures CONSISTENCY      ║
# ║  across every session, every developer, and every module.                  ║
# ║                                                                            ║
# ║  For Reel48+, this is especially critical because the sub-brand            ║
# ║  architecture (company_id + sub_brand_id) must be applied identically      ║
# ║  in every table, every endpoint, and every query — or you have a           ║
# ║  security vulnerability.                                                   ║
# ║                                                                            ║
# ║  HOW TO MAINTAIN IT:                                                       ║
# ║  The Harness Owner updates this file whenever an architectural decision    ║
# ║  changes or when Claude Code repeatedly makes a mistake that a new rule    ║
# ║  would prevent. Every update here improves ALL future sessions.            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


## Project Overview

# --- WHY THIS SECTION EXISTS ---
# Claude Code needs to understand WHAT it's building at a high level so it can
# make appropriate trade-offs. Without this context, it might over-engineer a
# simple feature or under-engineer a security-critical one.

Reel48+ is an enterprise apparel management platform. Companies use it to manage
branded apparel programs for their employees — from catalog setup through ordering,
bulk distribution, and analytics.

**Key differentiator:** Reel48+ supports a **sub-brand architecture** where a single
company (e.g., a corporation) can have multiple subsidiary brands, each with their
own catalogs, employees, and approval workflows, while the corporate parent retains
cross-brand visibility and control.

**Target users:** Enterprise companies with 100–10,000+ employees across multiple
brands or subsidiaries.


## Technology Stack

# --- WHY THIS SECTION EXISTS ---
# This locks in the technology choices so Claude Code never suggests alternatives
# or introduces incompatible libraries. Without this, Claude might use Express
# instead of FastAPI, or suggest MongoDB instead of PostgreSQL. Every technology
# choice here was made deliberately (see the ADRs in docs/adr/ for the reasoning).

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 (async where appropriate)
- **Migrations:** Alembic (all schema changes go through migrations — no raw DDL)
- **Database:** PostgreSQL 15+ on AWS RDS
- **Authentication:** Amazon Cognito (JWT tokens with custom claims)
- **Task Queue:** Amazon SQS (for async processing like bulk order aggregation)
- **Email:** Amazon SES (transactional emails, bulk order reminders)
- **File Storage:** Amazon S3 with CloudFront CDN
- **Invoicing & Payments:** Stripe (invoice generation, client billing, webhook processing)
- **Logging:** structlog (structured JSON logging with tenant context binding)

### Frontend
- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript (strict mode)
- **Design System:** IBM Carbon (`@carbon/react`) — primary component library and design tokens.
  Brand color `#292c2f` (charcoal), teal interactive `#0a6b6b`, plus a 10-color accent palette.
  All color definitions live in `frontend/src/styles/carbon-theme.scss` (single source of truth).
- **Utility CSS:** Tailwind CSS — layout utilities and custom spacing alongside Carbon.
  Color tokens in `frontend/tailwind.config.ts` reference CSS variables from the theme file.
- **SCSS:** Sass (required for Carbon theme customization)
- **Auth Integration:** AWS Amplify (Cognito client)
- **Hosting:** Vercel
- **Testing:** React Testing Library + Vitest

### Infrastructure
- **Compute:** AWS ECS Fargate (backend containers)
- **CDN:** CloudFront (static assets + S3 pre-signed URLs)
- **Cache:** ElastiCache Redis (session management, catalog caching)
- **Monitoring:** Sentry (errors) + CloudWatch (infrastructure)
- **CI/CD:** GitHub Actions


## Multi-Tenancy Architecture

# --- WHY THIS SECTION EXISTS ---
# This is the MOST CRITICAL section in the entire harness. Multi-tenancy with
# sub-brand isolation is what makes Reel48+ an enterprise platform rather than
# a single-company app. Every table, every query, every API endpoint must
# respect these boundaries. If Claude Code skips tenant isolation on even one
# query, that's a data breach waiting to happen.
#
# The dual-dimension model (company_id + sub_brand_id) is unusual — most
# multi-tenant systems only have one dimension. Claude Code needs explicit
# guidance to handle both correctly every time.

### Isolation Model
Reel48+ uses **shared-database multi-tenancy** with **PostgreSQL Row-Level Security (RLS)**.
Every table that contains tenant data includes two isolation columns:

1. **`company_id`** (UUID, NOT NULL) — Primary tenant isolation. Ensures Company A
   can never see Company B's data.
2. **`sub_brand_id`** (UUID, nullable in specific cases) — Secondary isolation within
   a tenant. Ensures Sub-Brand X employees can only see Sub-Brand X data.

**When `sub_brand_id` is NULL:** Only on records that are explicitly company-wide.
For example, a corporate admin user has `sub_brand_id = NULL` because they operate
across all sub-brands. The default sub-brand record itself always has a `sub_brand_id`.

### RLS Policy Pattern
Every table with tenant data MUST have RLS policies. The standard pattern:

```sql
-- Enable RLS on the table
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (prevents bypassing)
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

-- Company-level isolation (applied to all users; reel48_admin bypasses via NULL company_id)
CREATE POLICY {table_name}_company_isolation ON {table_name}
    USING (
        current_setting('app.current_company_id', true) IS NULL
        OR current_setting('app.current_company_id', true) = ''
        OR company_id = current_setting('app.current_company_id')::uuid
    );

-- Sub-brand scoping (applied for non-corporate users)
-- Corporate admins and reel48_admins (sub_brand_id IS NULL in their token) see all sub-brands
-- CRITICAL: Must be AS RESTRICTIVE so it ANDs with company isolation (not ORs).
CREATE POLICY {table_name}_sub_brand_scoping ON {table_name} AS RESTRICTIVE
    USING (
        current_setting('app.current_sub_brand_id', true) IS NULL
        OR current_setting('app.current_sub_brand_id', true) = ''
        OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
    );
```

**CRITICAL: `reel48_admin` RLS bypass.** When a `reel48_admin` is authenticated, the
tenant middleware sets `app.current_company_id` to empty string (not a UUID). The
company isolation policy allows this through, giving platform admins cross-company
visibility. This is intentional and ONLY applies to the `reel48_admin` role. The
application layer MUST verify the role before setting an empty company_id — defense-
in-depth ensures a non-admin user can never trigger this bypass.

### Role Model
Five roles, in descending order of access:

| Role | `company_id` | `sub_brand_id` | Access Scope |
|------|-------------|----------------|--------------|
| `reel48_admin` | NULL | NULL | **Platform operator.** Full access across ALL companies. Manages catalogs, pricing, product approvals, invoicing, and all client company data. This is a Reel48 employee, not a client user. |
| `corporate_admin` | Set | NULL | All sub-brands within their company |
| `sub_brand_admin` | Set | Set | Their assigned sub-brand only |
| `regional_manager` | Set | Set | Their assigned sub-brand only |
| `employee` | Set | Set | Their own profile + sub-brand catalog |

**`reel48_admin` special handling:**
- `company_id` is NULL because platform admins operate across all companies
- RLS policies must allow `reel48_admin` to bypass company isolation (see RLS pattern below)
- The `reel48_admin` role is set in the Cognito JWT `custom:role` claim, same as other roles
- Platform admin endpoints live under `/api/v1/platform/` to separate them from tenant endpoints

### Default Sub-Brand Rule
When a new company is created, a default sub-brand is AUTOMATICALLY created for it.
This ensures every company always has at least one sub-brand, simplifying the data
model (no special cases for "companies without sub-brands").

### Employee Onboarding Paths
# --- ADDED 2026-04-06 after ADR-007 ---
# Reason: Invite-only onboarding was the sole path; self-registration via org code added.
# Impact: Claude Code knows both paths exist and both guarantee valid tenant context.

There are **two** ways employees join a company:

1. **Admin Invite (targeted):** Admin creates an invite for a specific sub-brand and role.
   Single-use token sent via email. Best for targeted onboarding.
2. **Self-Registration via Org Code (bulk):** Employee enters a company-level org code
   during registration, then selects their sub-brand from the company's sub-brand list.
   Assigned `employee` role. Best for large-scale onboarding. See ADR-007 and
   `.claude/rules/authentication.md` for full details.

Both paths guarantee a valid `company_id` and `sub_brand_id` from the moment of user
creation, preserving RLS integrity.


## API Design Conventions

# --- WHY THIS SECTION EXISTS ---
# Consistent API design means Claude Code produces endpoints that feel like they
# were written by one developer. Without these rules, you'd get a mix of naming
# styles, response formats, and error patterns that make the frontend integration
# painful and the codebase hard to maintain.

### General Rules
- **Style:** RESTful (REST before GraphQL — see ADR-004)
- **Versioning:** URL-based (`/api/v1/...`)
- **Naming:** snake_case for JSON fields, plural nouns for resources
  - ✅ `/api/v1/products`, `/api/v1/sub_brands`
  - ❌ `/api/v1/product`, `/api/v1/getProducts`, `/api/v1/subBrands`

### Tenant Context in Every Request
**CRITICAL:** `company_id` and `sub_brand_id` are NEVER accepted as request parameters.
They are ALWAYS extracted from the authenticated user's JWT token by the auth middleware
and injected into the request context. This prevents a malicious user from passing
another tenant's ID in a request body.

```python
# ✅ CORRECT — tenant context comes from the JWT, not the request
@router.get("/api/v1/products")
async def list_products(context: TenantContext = Depends(get_tenant_context)):
    return await product_service.list(context.company_id, context.sub_brand_id)

# ❌ WRONG — never accept tenant IDs as parameters
@router.get("/api/v1/products")
async def list_products(company_id: UUID, sub_brand_id: UUID):
    return await product_service.list(company_id, sub_brand_id)
```

### Standard Response Format
```json
{
  "data": { ... },          // Single object or array
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150
  },
  "errors": []              // Empty array on success
}
```

### Standard Error Format
```json
{
  "data": null,
  "errors": [
    {
      "code": "RESOURCE_NOT_FOUND",
      "message": "Product with ID abc-123 not found",
      "field": null
    }
  ]
}
```

### HTTP Status Codes
- `200` — Success (GET, PUT, PATCH)
- `201` — Created (POST that creates a resource)
- `204` — No Content (DELETE)
- `400` — Validation error (bad input)
- `401` — Unauthenticated (missing or invalid token)
- `403` — Forbidden (valid token but insufficient permissions)
- `404` — Resource not found (within the user's tenant scope)
- `409` — Conflict (duplicate resource, state conflict)
- `422` — Unprocessable Entity (structurally valid but semantically invalid)
- `500` — Internal server error


## Database Conventions

# --- WHY THIS SECTION EXISTS ---
# Naming conventions prevent a chaotic schema where some tables use camelCase,
# others use PascalCase, and column names are inconsistent. These rules ensure
# Claude Code generates migrations that produce a clean, predictable schema.

### Naming
- **Tables:** snake_case, plural (e.g., `products`, `order_line_items`, `sub_brands`)
- **Columns:** snake_case (e.g., `company_id`, `created_at`, `unit_price`)
- **Indexes:** `ix_{table}_{column}` (e.g., `ix_products_company_id`)
- **Foreign keys:** `fk_{table}_{column}_{ref_table}` (e.g., `fk_orders_user_id_users`)
- **Constraints:** `ck_{table}_{description}` (e.g., `ck_orders_status_valid`)

### Base Model
Every SQLAlchemy model inherits from a base that includes:

```python
class TenantBase(Base):
    """
    WHY: This base model ensures EVERY table automatically gets the tenant
    isolation columns. Without this, a developer (or Claude Code) might
    forget to add company_id to a new table, creating a data isolation gap.
    """
    __abstract__ = True

    id = Column(UUID, primary_key=True, default=uuid4)
    company_id = Column(UUID, ForeignKey("companies.id"), nullable=False, index=True)
    sub_brand_id = Column(UUID, ForeignKey("sub_brands.id"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

### Migrations
- ALL schema changes go through Alembic migrations — no raw DDL
- Every migration that creates a table with `company_id` MUST also create the
  corresponding RLS policies in the same migration
- Migrations must be reversible (include both `upgrade()` and `downgrade()`)
- Migration messages follow: `{action}_{entity}_{detail}` (e.g., `create_products_table`,
  `add_sub_brand_id_to_orders`)


## File Storage Conventions

# --- WHY THIS SECTION EXISTS ---
# S3 path structure must mirror the tenant/sub-brand isolation model. If files
# are stored in a flat structure, there's no way to enforce access control at
# the storage level, and a misconfigured query could expose one tenant's assets
# to another.

### S3 Path Structure
```
s3://reel48-assets/{company_id}/{sub_brand_slug}/logos/
s3://reel48-assets/{company_id}/{sub_brand_slug}/products/
s3://reel48-assets/{company_id}/{sub_brand_slug}/catalog/
s3://reel48-assets/{company_id}/shared/                    # Company-wide assets
```

### Pre-signed URLs
All file access goes through CloudFront with pre-signed URLs. Never expose raw S3
URLs to the frontend. Pre-signed URLs expire after 1 hour for downloads, 15 minutes
for uploads.


## Invoicing & Client Billing Conventions

# --- WHY THIS SECTION EXISTS ---
# Invoicing is how Reel48+ monetizes the platform. Reel48 (the platform operator)
# creates and manages invoices for client companies. This is NOT self-billing —
# Reel48 is the vendor, client companies are the customers being billed. Without
# clear conventions here, Claude Code might build invoicing as client-managed,
# miss the Stripe integration patterns, or fail to handle the three distinct
# billing flows correctly.

### Who Creates Invoices
**CRITICAL:** Invoices are created by **Reel48 platform admins** (`reel48_admin` role),
NOT by client company admins. Reel48 is the vendor selling apparel services; client
companies are the customers being billed. Client company admins can VIEW their invoices
but cannot create, edit, or send them.

The one exception is the **self-service flow** where pre-approved, pre-priced products
generate invoices automatically at checkout — but even then, the pricing and product
approval was done by Reel48 ahead of time.

### Three Billing Flows

**Flow 1: Reel48-Assigned Invoices (Bulk Orders)**
```
Reel48 admin creates bulk order for client → Orders fulfilled →
  Reel48 admin creates draft invoice → Reviews → Finalizes and sends →
  Client company pays via Stripe hosted page
```
Used for: Custom bulk orders, unique pricing, non-catalog orders.
Invoice created manually by `reel48_admin` after order completion.

**Flow 2: Pre-Priced Self-Service (Catalog Purchases)**
```
Reel48 admin creates catalog → Sets prices → Approves products →
  Catalog sent to client company → Employees browse and purchase →
  Stripe invoice auto-generated at checkout → Client pays immediately
```
Used for: Standard catalog items with pre-set pricing.
Products are approved by Reel48 ONCE; individual purchases do not need further approval.
Catalog `payment_model` = `self_service`.

**Flow 3: Post-Window Invoicing (Buying Window Catalogs)**
```
Reel48 admin creates catalog → Sets prices → Sets buying window →
  Catalog sent to client company → Employees place orders during window →
  Window closes → Orders tallied → Reel48 admin creates consolidated invoice →
  Client company pays
```
Used for: Seasonal catalogs, event-based ordering, or when the client wants
to pay once after all employees have ordered.
Catalog `payment_model` = `invoice_after_close`.
Buying window deadline can be set by Reel48 admin or adjusted by the client company admin.

### Catalog Payment Model
Every catalog has a `payment_model` field set at the catalog level:
- **`self_service`** — Employees pay at checkout. Stripe invoice auto-created per order.
- **`invoice_after_close`** — Orders tallied during buying window. Consolidated Stripe
  invoice created by Reel48 admin after the window closes.

This is a per-catalog setting that applies to ALL items in that catalog. A single
catalog cannot mix payment models.

### Product Approval by Reel48
- Products and catalogs must be **approved by a `reel48_admin`** before going live
- Once a product is approved and priced, individual employee purchases of that product
  do NOT require further Reel48 approval
- Approval status is tracked on the product/catalog record (`approved_by`, `approved_at`)

### Stripe Integration Model
Reel48+ uses **Stripe** as the invoicing and payment platform. The integration follows
a **server-side only** pattern — the backend creates and manages Stripe objects; the
frontend displays invoice data fetched through our API (never directly from Stripe).

**Stripe Object Mapping:**
| Reel48+ Entity | Stripe Object | Relationship |
|----------------|---------------|-------------|
| Company | Stripe Customer | 1:1 — created when company onboards |
| Sub-Brand | Stripe Customer metadata | Company's Stripe Customer tagged with sub-brand context |
| Self-Service Order | Stripe Invoice + Line Items | Auto-created at checkout |
| Bulk Order / Post-Window | Stripe Invoice + Line Items | Created by Reel48 admin |

### Tenant Isolation in Stripe
- Each **company** maps to a **Stripe Customer** (`stripe_customer_id` stored on the `companies` table)
- Invoices are always created against the company's Stripe Customer
- Sub-brand context is stored as **Stripe metadata** on invoices (`sub_brand_id`, `sub_brand_name`)
  so invoices can be filtered and reported by sub-brand
- **CRITICAL:** The `reel48_admin` creates invoices on behalf of client companies. The
  Stripe Customer ID is looked up from the target company record, NOT from the admin's
  own context (since `reel48_admin` has no `company_id`).

### Invoice Data Model Rules
- The `invoices` table stores a local copy of invoice data alongside the `stripe_invoice_id`
  for cross-referencing. Stripe is the source of truth for payment status; the local table
  enables fast queries, tenant-scoped access, and analytics integration.
- Every invoice row MUST include `company_id` and `sub_brand_id` (standard tenant isolation)
- Invoice line items reference `order_id` or `bulk_order_id` to trace back to the originating order
- Store `stripe_invoice_id`, `stripe_invoice_url`, and `status` on the local record
- Store `billing_flow` on each invoice: `assigned`, `self_service`, or `post_window`
- Payment status is updated via **Stripe webhooks**, not polling

### Webhook Security
- Verify webhook signatures using `stripe.Webhook.construct_event()` with the webhook signing secret
- The webhook endpoint (`/api/v1/webhooks/stripe`) is the ONE endpoint that does NOT require
  JWT authentication (Stripe calls it directly), but it MUST verify the Stripe signature
- Process webhooks idempotently — the same event may be delivered multiple times

### API Endpoints for Invoicing
**Platform admin endpoints (reel48_admin only):**
- `POST /api/v1/platform/invoices` — Create a draft invoice for a client company
- `POST /api/v1/platform/invoices/{invoice_id}/finalize` — Finalize and send
- `GET /api/v1/platform/invoices` — List all invoices across all companies
- `POST /api/v1/platform/catalogs/{catalog_id}/approve` — Approve a catalog for client use

**Client-facing endpoints (tenant-scoped):**
- `GET /api/v1/invoices` — List invoices for the authenticated company (paginated)
- `GET /api/v1/invoices/{invoice_id}` — Invoice detail with line items
- `GET /api/v1/invoices/{invoice_id}/pdf` — Get Stripe-hosted invoice PDF URL

**Webhook endpoint (no JWT, signature-verified):**
- `POST /api/v1/webhooks/stripe` — Stripe webhook receiver


## Testing Requirements

# --- WHY THIS SECTION EXISTS ---
# Tests are the safety net that catches mistakes before they reach production.
# For a multi-tenant system, tests are doubly important because you need to
# verify not just that features work, but that tenant isolation is maintained.
# Every module should include cross-tenant access tests that confirm data
# doesn't leak between companies or sub-brands.

### Backend
- **Framework:** pytest + FastAPI TestClient
- **Fixtures:** Use pytest fixtures for test tenant setup (company, sub-brands, users)
- **Isolation tests:** Every module MUST include tests that verify:
  - Company A cannot see Company B's data
  - Sub-Brand X cannot see Sub-Brand Y's data (within the same company)
  - Corporate admin CAN see all sub-brands within their company

### Frontend
- **Framework:** React Testing Library + Vitest
- **Approach:** Test user interactions, not implementation details
- **Mocking:** Mock API responses with MSW (Mock Service Worker)

### Coverage Targets
- Backend: 80%+ line coverage, 100% on auth and RLS logic
- Frontend: 70%+ on components with business logic


## Code Quality

# --- WHY THIS SECTION EXISTS ---
# Linters and formatters eliminate style debates and catch common errors
# automatically. When Claude Code generates code, it passes through these
# same tools in CI, so the harness should align with them.

### Backend
- **Linter:** Ruff (replaces flake8, isort, black)
- **Type checking:** mypy (strict mode)
- **Config:** pyproject.toml

### Frontend
- **Linter:** ESLint with Next.js config
- **Formatter:** Prettier
- **Type checking:** TypeScript strict mode (tsconfig.json)

### Git
- **Branch naming:** `feature/{module}-{description}`, `fix/{module}-{description}`, `chore/{description}`
- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`)
- **PR process:** All code goes through pull requests. No direct pushes to `main`.


## Module Build Order

# --- WHY THIS SECTION EXISTS ---
# This tells Claude Code what already exists when working on a later module.
# If you're building Module 4 (Ordering), Claude needs to know that Auth,
# Profiles, and Catalog are already complete and can be depended upon.

1. **Auth & Multi-Tenancy** (foundation — everything depends on this; includes both
   invite flow AND org-code self-registration — see ADR-007)
2. **Employee Profiles** (depends on Auth)
3. **Product Catalog & Brand Management** (depends on Auth)
4. **Ordering Flow** (depends on Profiles + Catalog)
5. **Bulk Ordering System** (depends on Ordering)
6. **Approval Workflows** (depends on Ordering)
7. **Invoicing & Client Billing** (depends on Ordering + Approval Workflows)
8. **Analytics Dashboard** (depends on Ordering + Invoicing)
9. **Employee Engagement** (depends on Profiles)


## Claude Code Session Rules

# --- WHY THIS SECTION EXISTS ---
# These rules govern HOW Claude Code should behave during sessions. They prevent
# common pitfalls like trying to build too much in one session (which degrades
# quality) or skipping tests (which creates technical debt).

1. **One module per session.** Focus on a single module's scope. Broad context
   produces lower-quality results.
2. **Always check for existing patterns.** Before generating new code, look at
   existing modules for established patterns and follow them.
3. **Never skip tenant isolation.** Every new table, endpoint, and query must
   include `company_id` and `sub_brand_id` handling. No exceptions.
4. **Write tests alongside implementation.** Tests are not an afterthought —
   they are part of the deliverable.
5. **Use extended thinking for complex logic.** RLS policies, state machines
   (approval workflows, order status), bulk aggregation, and analytics queries
   all benefit from extended thinking mode.
6. **Respect the API contract.** Check `/docs/api/` for existing OpenAPI schemas
   before creating new endpoints. New endpoints must conform to the standard
   response/error format defined above.


## Directory Structure

# --- WHY THIS SECTION EXISTS ---
# A predictable directory structure means Claude Code always knows where to put
# new files and where to find existing ones. Without this, files end up in
# random locations and the codebase becomes hard to navigate.

```
reel48-plus/
├── CLAUDE.md                          # ← You are here (root harness file)
├── .claude/
│   └── rules/                         # Domain-specific rules (auto-activated by file path)
│       ├── database-migrations.md
│       ├── api-endpoints.md
│       ├── authentication.md
│       ├── testing.md
│       ├── s3-storage.md
│       ├── stripe-invoicing.md
│       └── harness-maintenance.md
├── docs/
│   ├── api/                           # OpenAPI schemas (populated as endpoints are built)
│   └── adr/                           # Architectural Decision Records
│       ├── 001-shared-database-multi-tenancy.md
│       ├── 002-rls-over-application-isolation.md
│       ├── 003-default-sub-brand-pattern.md
│       ├── 004-rest-before-graphql.md
│       ├── 005-cognito-over-third-party-auth.md
│       ├── 006-stripe-for-invoicing.md
│       ├── 007-controlled-self-registration.md
│       └── TEMPLATE.md
├── prompts/                           # Reusable prompt templates
│   ├── crud-endpoint.md
│   ├── new-table-migration.md
│   ├── react-component.md
│   ├── test-suite.md
│   ├── self-registration.md
│   └── harness-review.md
├── frontend/
│   ├── CLAUDE.md                      # Frontend-specific conventions
│   ├── src/
│   │   ├── app/                       # Next.js App Router pages
│   │   ├── components/                # Shared UI components
│   │   ├── lib/                       # Utilities, API client, auth helpers
│   │   ├── hooks/                     # Custom React hooks
│   │   ├── styles/                    # Carbon theme overrides and global styles
│   │   └── types/                     # TypeScript type definitions
│   ├── package.json
│   └── tsconfig.json
├── backend/
│   ├── CLAUDE.md                      # Backend-specific conventions
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── core/                      # Config, security, dependencies
│   │   ├── models/                    # SQLAlchemy models
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── api/
│   │   │   └── v1/                    # Versioned API routes
│   │   ├── services/                  # Business logic layer
│   │   └── middleware/                # Auth, tenant context, logging
│   ├── migrations/                    # Alembic migrations
│   ├── tests/                         # pytest tests
│   ├── pyproject.toml
│   └── alembic.ini
└── shared/
    └── types/                         # Shared TypeScript types / API contracts
```

### Non-Application Files (Ignore During Implementation)
The following files and directories exist at the repo root for development tooling
and project management purposes. They are NOT part of the Reel48+ application
codebase. Claude Code should **not modify or reference these** during module builds:

- `shim-lib/`, `shim-perm/` — Development harness tooling (permission shims)
- `uploads/` — Project planning documents
- `Reel48+ Harness Companion Guide.docx` — Build process guide
- `audit.jsonl`, `.audit-key` — Harness audit logs
- `README.md` — Repo-level readme


## ⚙ Harness Maintenance Protocol (MANDATORY)

# --- WHY THIS SECTION EXISTS ---
# The harness is only valuable if it stays current. An outdated harness is
# WORSE than no harness — it gives Claude Code confident but wrong guidance.
# Because Claude Code is doing essentially all the coding on this project,
# the maintenance protocol must be embedded here (in the file Claude Code
# always reads) so it becomes an automatic part of every session's workflow.
#
# This section defines THREE mandatory maintenance triggers that ensure the
# harness evolves alongside the codebase. Skipping harness maintenance is
# treated the same as skipping tests — it is not optional.

### Principle: The Harness Is a Living Document
The harness is NOT a static artifact created once and forgotten. It is a living
control layer that must reflect the CURRENT state of the project's patterns,
conventions, and decisions. Every module built teaches us something. The harness
must capture those lessons so they benefit all future sessions.

### TRIGGER 1: End-of-Session Self-Audit (Every Session)

**When:** At the END of every Claude Code session, BEFORE the final commit.

**What to do:** Review the work completed in this session and ask these questions:

1. **New pattern introduced?** Did this session establish a new code pattern that
   future sessions should follow? (e.g., a new API response shape, a new component
   pattern, a new service method convention)
   → **Action:** Add the pattern to the relevant CLAUDE.md or create a new rule file.

2. **Existing pattern violated?** Did the harness say to do X, but the implementation
   needed to do Y instead? (e.g., a schema that needed a nullable `sub_brand_id` in
   a place the harness says it should never be null)
   → **Action:** Update the harness to reflect the actual correct pattern, with a
   comment explaining why the original guidance was revised.

3. **New decision made?** Did this session require a non-obvious architectural choice?
   (e.g., choosing between WebSockets and polling, deciding on a caching strategy)
   → **Action:** Write a new ADR in `docs/adr/` documenting the decision and rationale.

4. **Missing guidance discovered?** Did Claude Code have to make a judgment call because
   the harness didn't cover the scenario? (e.g., no guidance on how to handle soft
   deletes, or how pagination should work for nested resources)
   → **Action:** Add the missing guidance to the appropriate CLAUDE.md or rule file.

5. **Prompt template needed?** Did this session involve a task pattern that will recur
   in future modules? (e.g., building an approval workflow, creating a dashboard widget)
   → **Action:** Create a new prompt template in `prompts/`.

**Minimum output:** Update `docs/harness-changelog.md` with an entry describing what
was reviewed and what (if anything) was updated. Even if no changes are needed, log
that the review happened. This creates an audit trail.

### TRIGGER 2: Post-Module Harness Review (After Each Module)

**When:** After completing each of the 8 platform modules, BEFORE starting the next one.

**What to do:** Run a dedicated harness review session using the `prompts/harness-review.md`
template. This is a deeper review than the per-session audit.

The review covers:
1. **Pattern consistency:** Do all endpoints in the completed module follow the same
   patterns? Did any drift occur during the multi-session build?
2. **Rule effectiveness:** Did the rule files activate correctly? Were any rules
   missing or insufficient?
3. **ADR currency:** Are all ADRs still accurate? Has any decision been informally
   reversed during implementation?
4. **Cross-module alignment:** Does the completed module's implementation align with
   previously completed modules? Are there inconsistencies to resolve?
5. **Harness gap analysis:** What questions did Claude Code have to answer without
   harness guidance? These gaps need to be filled before the next module.

**Minimum output:** A summary committed to `docs/harness-changelog.md` that includes:
- Module name and completion date
- List of harness files updated (or "no updates needed" with justification)
- Any new patterns or rules added
- Gaps identified for the next module

### TRIGGER 3: Reactive Updates (When Something Goes Wrong)

**When:** Any time Claude Code produces output that:
- Violates a convention that SHOULD have been in the harness but wasn't
- Follows an outdated convention that has since changed
- Makes an architectural choice that conflicts with an ADR
- Repeats a mistake that was already corrected in a previous session

**What to do:** Fix the output, then IMMEDIATELY update the harness to prevent the
same issue in the next session. This is the "if Claude gets it wrong twice, fix the
harness" rule.

**The fix goes in this order:**
1. Identify which harness file SHOULD have prevented the mistake
2. Update that file with the correct guidance
3. If no file covers the scenario, create a new rule file or add a section to the
   relevant CLAUDE.md
4. Log the update in `docs/harness-changelog.md`

### Harness Update Format

When updating any harness file, follow this format for new additions:

```markdown
# --- ADDED {YYYY-MM-DD} after {Module X / Session Y} ---
# Reason: {What went wrong or what was learned}
# Impact: {What this update prevents in future sessions}
{The new guidance}
```

This annotation makes it easy to trace WHY each piece of guidance exists, which
helps during the post-module review when deciding whether guidance is still relevant.

### Harness Files Quick Reference

| I need to update...                  | Edit this file                          |
|--------------------------------------|-----------------------------------------|
| Technology stack or project-wide rule| `/CLAUDE.md` (this file)                |
| React/Next.js/frontend pattern       | `/frontend/CLAUDE.md`                   |
| FastAPI/Python/backend pattern        | `/backend/CLAUDE.md`                    |
| Database or migration rule            | `.claude/rules/database-migrations.md`  |
| API endpoint convention               | `.claude/rules/api-endpoints.md`        |
| Auth or security pattern              | `.claude/rules/authentication.md`       |
| Testing requirement                   | `.claude/rules/testing.md`              |
| S3 / file storage pattern             | `.claude/rules/s3-storage.md`           |
| Stripe / invoicing / billing pattern  | `.claude/rules/stripe-invoicing.md`     |
| Harness maintenance process itself    | `.claude/rules/harness-maintenance.md`  |
| Design system / Carbon pattern        | `.claude/rules/carbon-design-system.md` |
| An architectural decision (why)       | `docs/adr/{NNN}-{title}.md` (new file)  |
| A reusable task pattern               | `prompts/{task-name}.md` (new file)     |
| What changed and when                 | `docs/harness-changelog.md` (append)    |

### What NOT to Do
- ❌ **Never let the harness become stale.** An outdated rule is worse than no rule.
- ❌ **Never update code without considering harness impact.** If you change a pattern
  in the code, update the harness to match.
- ❌ **Never skip the changelog entry.** Even "no changes needed" is worth logging.
- ❌ **Never delete harness guidance without replacement.** If a rule is wrong, replace
  it with the correct guidance — don't just remove it and leave a gap.
- ❌ **Never make harness updates in a separate PR from the code change.** The harness
  update should be in the same commit as the code that prompted it, so the two stay
  in sync in version history.
