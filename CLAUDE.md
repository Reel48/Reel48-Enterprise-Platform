# Reel48+ Enterprise Platform — Root CLAUDE.md

> ⚠ **SIMPLIFICATION IN PROGRESS** — see `~/.claude/plans/yes-please-write-the-memoized-karp.md`.
> This document has been stripped of stale guidance (sub-brand architecture, catalog/products,
> Stripe invoicing, 5-role model). The plan describes a four-session refactor; we are currently
> between Session 0 (harness teardown — done) and Session A (backend teardown). Sections marked
> **TBD** will be written authoritatively in Session D once the code matches. **Do NOT treat
> removed sections as authoritative. Do NOT reintroduce sub-brand scoping, catalog/product
> backend, Stripe invoicing, or the `sub_brand_admin`/`regional_manager` roles.**


## Project Overview

Reel48+ is an enterprise apparel management platform. Companies use it to manage branded
apparel programs for their employees.

**Current simplification direction (being implemented):**
- Tenants are **company-only** (sub-brand dimension is being removed).
- **Commerce** (catalog, products, ordering, checkout, invoicing) will be provided by a
  future Shopify integration. The in-app catalog/product/order/invoicing stack is being
  removed.
- **Roles** collapse from 5 to 4: `reel48_admin`, `company_admin`, `manager`, `employee`.

**Target users:** Enterprise companies managing branded apparel programs for 100+ employees.


## Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic
- **Database:** PostgreSQL 15+ on AWS RDS
- **Authentication:** Amazon Cognito (JWT with custom claims)
- **Email:** Amazon SES
- **File Storage:** Amazon S3 with CloudFront
- **Logging:** structlog (JSON, tenant context bound per request)

### Frontend
- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript (strict)
- **Design System:** IBM Carbon (`@carbon/react`) — primary UI library. See ADR-008 and
  [.claude/rules/carbon-design-system.md](.claude/rules/carbon-design-system.md).
- **Utility CSS:** Tailwind CSS (layout + spacing only; never to override Carbon internals).
- **SCSS:** Sass (required for Carbon theme customization).
- **Auth Integration:** AWS Amplify (Cognito client).
- **Hosting:** Vercel.
- **Testing:** React Testing Library + Vitest.

### Infrastructure
- **Compute:** AWS ECS Fargate (backend containers)
- **CDN:** CloudFront (static assets + S3 pre-signed URLs)
- **Cache:** ElastiCache Redis (rate limiting, sessions)
- **Monitoring:** Sentry + CloudWatch
- **CI/CD:** GitHub Actions


## Multi-Tenancy Architecture

Reel48+ uses **shared-database multi-tenancy** with **PostgreSQL Row-Level Security (RLS)**.

### Isolation Model (company-only)
Every tenant-scoped table includes one isolation column:
- **`company_id`** (UUID, NOT NULL) — the sole tenant boundary.

(The previous two-dimensional model using `sub_brand_id` is being removed. Do not
reintroduce it.)

### RLS Policy Pattern (company-only)
```sql
ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {t} FORCE ROW LEVEL SECURITY;

CREATE POLICY {t}_company_isolation ON {t}
    USING (
        current_setting('app.current_company_id', true) IS NULL
        OR current_setting('app.current_company_id', true) = ''
        OR company_id = current_setting('app.current_company_id')::uuid
    );
```

The empty-string branch is the `reel48_admin` bypass. Platform admins have no
`company_id`, so the auth middleware sets `app.current_company_id = ''`. Application-
layer role checks MUST verify the caller is `reel48_admin` before relying on this bypass.

### Role Model (target, 4 roles)

| Role | `company_id` | Scope |
|------|-------------|-------|
| `reel48_admin` | NULL | Platform operator. Cross-company access. Reel48 employee. |
| `company_admin` | Set | All users + settings within one company. |
| `manager` | Set | Mid-tier admin within one company (future Shopify-approval authority). |
| `employee` | Set | Own profile + whatever commerce surface Shopify provides. |

**Role transition note:** `corporate_admin`, `sub_brand_admin`, and `regional_manager` from
the legacy model collapse to `company_admin` / `manager`. Sessions A/B implement the
migration; Session D writes the final access matrix.


## API Design Conventions

- **Style:** RESTful.
- **Versioning:** URL-based (`/api/v1/...`).
- **Naming:** snake_case for JSON fields and URL path segments. Plural nouns for resources.
- **Tenant context:** NEVER accept `company_id` as a request parameter for tenant-scoped
  endpoints. Platform admin endpoints (`/api/v1/platform/`) MAY accept a target `company_id`
  in the body — the caller must be `reel48_admin`.
- **Response format:** `{"data": <x>, "meta": {...}, "errors": []}`.
- **Error format:** `{"data": null, "errors": [{"code": "X", "message": "..."}]}`.
- **HTTP status:** 200/201/204 for success, 400/401/403/404/409/422 for client errors, 500
  for server.

See [.claude/rules/api-endpoints.md](.claude/rules/api-endpoints.md) for the full list of
unauthenticated endpoint exceptions.


## Database Conventions

- Tables: snake_case, plural (`users`, `companies`).
- Columns: snake_case (`company_id`, `created_at`).
- Indexes: `ix_{table}_{column}`.
- Foreign keys: `fk_{table}_{column}_{ref_table}`.

Every SQLAlchemy model inherits from `GlobalBase` (companies table only) or `CompanyBase`
(every other tenant table). The `TenantBase` class from the old two-dimensional model is
being deleted in Session A — do not use it.

See [.claude/rules/database-migrations.md](.claude/rules/database-migrations.md) for the
migration rules.


## File Storage Conventions

S3 path structure is company-scoped (no sub-brand segment):

```
s3://reel48-assets/{company_id}/logos/
s3://reel48-assets/{company_id}/profiles/
```

All file access goes through CloudFront with pre-signed URLs. See
[.claude/rules/s3-storage.md](.claude/rules/s3-storage.md).


## Commerce & Billing — TBD (Shopify integration)

The in-app catalog, products, ordering, bulk-ordering, approval workflows, and Stripe
invoicing are being removed in Sessions A and B (see plan). The replacement is a future
Shopify integration that will own:
- Product catalog (source of truth: Shopify)
- Checkout and cart
- Invoicing and payments

**Until the Shopify integration lands, there is no commerce surface in-app.** The
`/products` frontend route remains as a "Coming Soon" placeholder. Do not build new
catalog/product/order/invoice models, services, routes, or UI in the meantime.


## Testing Requirements

- **Backend:** pytest + FastAPI TestClient. Factories for test data.
- **Frontend:** Vitest + React Testing Library + MSW.
- **Isolation tests:** Every module MUST include a cross-company test verifying Company A
  cannot see Company B's data. Cross-sub-brand tests are no longer required (sub-brands
  are being removed).
- **Coverage:** Backend 80%+ overall, 100% on auth middleware / RLS. Frontend 70%+ on
  components with business logic.

See [.claude/rules/testing.md](.claude/rules/testing.md).


## Code Quality

### Backend
- **Linter:** Ruff. **Type checking:** mypy (strict). **Config:** pyproject.toml.

### Frontend
- **Linter:** ESLint with Next.js config. **Formatter:** Prettier. **TS:** strict mode.

### Git
- Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- PRs only; no direct push to `main`.


## Module Build Order (current reality)

**Built and still valid:**
1. **Auth & Multi-Tenancy** — Cognito, org-code self-registration, role-based middleware.
2. **Employee Profiles** — PUT /me upsert pattern, S3 photo storage.
3. **Notifications** — in-app feed for announcements.

**Being removed (Sessions A + B of the plan):**
- ~~Product Catalog & Brand Management~~
- ~~Ordering Flow~~
- ~~Bulk Ordering~~
- ~~Approval Workflows~~
- ~~Invoicing & Client Billing (Stripe)~~
- ~~Sub-brand management~~
- ~~Wishlists~~

**Future:**
- **Shopify Integration** — will provide catalog, ordering, checkout, and billing.
  See `prompts/shopify-integration.md` (to be written in Session D).


## Claude Code Session Rules

1. **Consult the plan first.** Every session until Session D is complete should read
   `~/.claude/plans/yes-please-write-the-memoized-karp.md` before making changes.
2. **Do not reintroduce removed systems.** No sub-brand columns, no catalog/product
   models, no Stripe integration, no `sub_brand_admin` / `regional_manager` roles.
3. **Pair code and harness.** When you delete a code file, also delete or update its
   corresponding harness file in the same commit.
4. **Tenant isolation is still mandatory.** Every surviving tenant table needs `company_id`
   + the RLS policy. Every surviving endpoint reads tenant context from the JWT.
5. **Tests alongside implementation.**


## Directory Structure

```
reel48-plus/
├── CLAUDE.md                          # This file
├── .claude/
│   └── rules/                         # Domain-specific rules
│       ├── authentication.md
│       ├── api-endpoints.md
│       ├── carbon-design-system.md
│       ├── database-migrations.md
│       ├── harness-maintenance.md
│       ├── s3-storage.md
│       └── testing.md
├── docs/
│   ├── adr/                           # Architectural Decision Records
│   └── harness-changelog.md           # Append-only audit trail
├── prompts/                           # Reusable prompt templates
├── frontend/                          # Next.js app (see frontend/CLAUDE.md)
├── backend/                           # FastAPI app (see backend/CLAUDE.md)
└── shared/
    └── types/
```

### Non-Application Files (Ignore During Implementation)
`shim-lib/`, `shim-perm/`, `uploads/`, `audit.jsonl`, `.audit-key` — harness tooling only.
Not part of the application codebase.


## ⚙ Harness Maintenance Protocol

The harness must stay current with the code. Every code change pairs with a harness update.
See [.claude/rules/harness-maintenance.md](.claude/rules/harness-maintenance.md) for the
three maintenance triggers (session audit, post-module review, reactive updates).
