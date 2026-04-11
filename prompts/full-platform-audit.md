# Reel48+ Full Platform Audit — All 9 Modules
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PURPOSE                                                                   ║
# ║                                                                            ║
# ║  This prompt runs a COMPREHENSIVE audit of the entire Reel48+ codebase     ║
# ║  after all 9 modules have been completed. It verifies correctness,         ║
# ║  consistency, security, and completeness across every layer: database,     ║
# ║  backend, frontend, tests, and harness.                                    ║
# ║                                                                            ║
# ║  This is NOT a quick review. This is an exhaustive, line-by-line audit     ║
# ║  that should leave NOTHING unchecked. When this audit passes, the          ║
# ║  platform is ready for deployment preparation.                             ║
# ║                                                                            ║
# ║  HOW TO USE                                                                ║
# ║                                                                            ║
# ║  Paste this entire prompt into a fresh Claude Code session. The session    ║
# ║  will read the CLAUDE.md harness automatically. Work through each          ║
# ║  section sequentially. For each check, report PASS or FAIL with details.  ║
# ║  At the end, produce a summary report.                                     ║
# ║                                                                            ║
# ║  IMPORTANT: Do NOT fix issues during this audit unless explicitly asked.   ║
# ║  The goal is to IDENTIFY all issues first, then prioritize fixes.          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

---

Run a comprehensive platform audit of the Reel48+ enterprise apparel platform.
All 9 modules have been completed. Your job is to verify everything was built
correctly, consistently, and completely according to the harness (CLAUDE.md,
rule files, ADRs).

Read the root CLAUDE.md, all rule files in `.claude/rules/`, and all ADRs in
`docs/adr/` before beginning. These define the "contract" — everything built
must conform to them.

**Output format:** For each section, produce a checklist with PASS/FAIL per item.
For any FAIL, include: the file path, what's wrong, what it should be, and
severity (CRITICAL / HIGH / MEDIUM / LOW). At the end, produce a consolidated
summary report.

---

## PART 1: DATABASE & MIGRATION AUDIT

### 1.1 Migration File Integrity
Read every migration file in `backend/migrations/versions/`. For each migration:

- [ ] Has both `upgrade()` and `downgrade()` functions
- [ ] `downgrade()` properly reverses everything in `upgrade()` (drops in reverse order)
- [ ] Follows naming convention: `{action}_{entity}_{detail}`
- [ ] No raw DDL — uses Alembic operations (`op.create_table`, `op.execute` for RLS only)
- [ ] Alembic revision chain is unbroken (each `down_revision` points to the previous)

**Migrations to audit:**
```
001_create_module1_identity_tables.py
002_create_employee_profiles_table.py
003_create_module3_catalog_tables.py
004_create_module4_order_tables.py
005_create_module5_bulk_order_tables.py
006_create_module6_approval_tables.py
007_create_module7_invoice_tables.py
009_create_notifications_and_wishlists_tables.py
```

**CRITICAL CHECK — Migration gap:** There is no migration `008`. Verify this is
intentional and does not break the Alembic revision chain.

### 1.2 RLS Policy Completeness
For EVERY table created across all migrations, verify:

- [ ] `ALTER TABLE {table} ENABLE ROW LEVEL SECURITY` is present
- [ ] `ALTER TABLE {table} FORCE ROW LEVEL SECURITY` is present
- [ ] Company isolation policy exists (PERMISSIVE) with the correct 3-branch USING clause:
      `IS NULL OR = '' OR company_id = ::uuid`
- [ ] Sub-brand scoping policy exists (AS RESTRICTIVE) for tables with `sub_brand_id`
- [ ] Sub-brand scoping is correctly marked `AS RESTRICTIVE` (not default PERMISSIVE)
- [ ] Tables that are company-only (sub_brands, org_codes, invites) have company
      isolation but NO sub-brand scoping (correct — they have no sub_brand_id column)
- [ ] The `companies` table uses `id = ` (not `company_id = `) in its isolation policy
- [ ] RLS policies are created in the SAME migration as their table (not deferred)

**Tables to verify RLS on:**
```
companies, sub_brands, org_codes, users, invites,
employee_profiles, products, catalogs, catalog_products,
orders, order_line_items, bulk_orders, bulk_order_items,
approval_requests, approval_rules, invoices,
notifications, wishlists
```

### 1.3 Tenant Isolation Columns
For every model in `backend/app/models/`, verify the correct base class:

- [ ] `Company` → `GlobalBase` (no tenant columns — IS the tenant)
- [ ] `SubBrand` → `CompanyBase` (company_id only)
- [ ] `OrgCode` → `CompanyBase` (company_id only)
- [ ] `Invite` → `CompanyBase` (company_id only, uses `target_sub_brand_id` instead)
- [ ] `User` → `TenantBase` (company_id + sub_brand_id)
- [ ] `EmployeeProfile` → `TenantBase`
- [ ] `Product` → `TenantBase`
- [ ] `Catalog` → `TenantBase`
- [ ] `CatalogProduct` → `TenantBase`
- [ ] `Order` → `TenantBase`
- [ ] `OrderLineItem` → `TenantBase`
- [ ] `BulkOrder` → `TenantBase`
- [ ] `BulkOrderItem` → `TenantBase`
- [ ] `ApprovalRequest` → `TenantBase`
- [ ] `ApprovalRule` → `TenantBase`
- [ ] `Invoice` → `TenantBase`
- [ ] `Notification` → `TenantBase`
- [ ] `Wishlist` → `TenantBase`

### 1.4 Foreign Key Integrity
For every model, verify:

- [ ] All foreign keys reference the correct parent table
- [ ] `ON DELETE` behavior is appropriate (CASCADE for child records, RESTRICT for
      references that should prevent deletion)
- [ ] Circular FK dependencies are resolved with deferred constraints (e.g., org_codes ↔ users)
- [ ] All FK columns are indexed (check for missing indexes)

### 1.5 Column Completeness
For each model, verify it has all columns specified in the CLAUDE.md or module prompts:

- [ ] `Invoice` model has ALL required columns from `.claude/rules/stripe-invoicing.md`:
      `stripe_invoice_id`, `stripe_invoice_url`, `stripe_pdf_url`, `invoice_number`,
      `billing_flow`, `status`, `total_amount`, `currency`, `due_date`,
      `buying_window_closes_at`, `created_by`, `paid_at`
- [ ] `Order` model has status field with valid status values
- [ ] `BulkOrder` model has status lifecycle: draft → submitted → approved → processing → shipped → delivered → cancelled
- [ ] `Catalog` model has `payment_model` field (self_service / invoice_after_close)
- [ ] `Product` model has `approved_by`, `approved_at` fields
- [ ] `Catalog` model has `approved_by`, `approved_at` fields
- [ ] `User` model has `registration_method` field
- [ ] `Notification` model has appropriate fields (title, body, type, read status, target scope)
- [ ] `Wishlist` model has `user_id` and `product_id` references
- [ ] All models have `created_at` and `updated_at` audit columns

### 1.6 Naming Convention Compliance
Across all models and migrations:

- [ ] All table names are snake_case and plural
- [ ] All column names are snake_case
- [ ] All indexes follow `ix_{table}_{column}` pattern
- [ ] All foreign keys follow `fk_{table}_{column}_{ref_table}` pattern
- [ ] All check constraints follow `ck_{table}_{description}` pattern

---

## PART 2: BACKEND API AUDIT

### 2.1 Endpoint Inventory
Read `backend/app/api/v1/router.py` and every route file. Create a complete
inventory of ALL endpoints. For each endpoint, verify:

- [ ] Correct HTTP method (GET for reads, POST for creates, PUT/PATCH for updates, DELETE for deletes)
- [ ] Correct status codes (200 for GET/PUT, 201 for POST creates, 204 for hard deletes)
- [ ] URL follows conventions: `/api/v1/{plural_snake_case_resource}`
- [ ] Resource IDs in path: `/api/v1/{resource}/{resource_id}`

### 2.2 Tenant Context Enforcement
For EVERY endpoint (except the 3 unauthenticated exceptions), verify:

- [ ] Uses `context: TenantContext = Depends(get_tenant_context)` or equivalent
- [ ] NEVER accepts `company_id` or `sub_brand_id` as query/path/body parameters
      (exception: `reel48_admin` platform endpoints that accept a target `company_id`)
- [ ] Passes tenant context to service layer

**Unauthenticated endpoint exceptions (verify these do NOT use TenantContext):**
- [ ] `POST /api/v1/auth/validate-org-code` — rate-limited, no JWT
- [ ] `POST /api/v1/auth/register` — rate-limited, no JWT
- [ ] `POST /api/v1/webhooks/stripe` — Stripe signature verified, no JWT

### 2.3 Response Format Compliance
For EVERY endpoint, verify responses match the standard format:

- [ ] Success: `{"data": ..., "meta": {...}, "errors": []}`
- [ ] Error: `{"data": null, "errors": [{"code": "...", "message": "..."}]}`
- [ ] List endpoints include `meta` with `page`, `per_page`, `total`

### 2.4 Pagination
For EVERY list endpoint, verify:

- [ ] Accepts `page` and `per_page` query parameters
- [ ] Defaults: `page=1`, `per_page=20`
- [ ] Maximum `per_page` is enforced (100)
- [ ] Returns total count in `meta`

### 2.5 Role-Based Access Control
For each endpoint, verify the correct role restrictions per the access matrix
in `.claude/rules/authentication.md`:

**Platform admin endpoints (`/api/v1/platform/...`):**
- [ ] ALL platform endpoints check for `reel48_admin` role
- [ ] Reject non-admin roles with 403

**Company admin endpoints:**
- [ ] Corporate admin endpoints check for `corporate_admin` or higher
- [ ] Sub-brand admin endpoints check for `sub_brand_admin` or higher

**Employee endpoints:**
- [ ] Employee can only access their own profile and orders
- [ ] Employee CANNOT access: analytics, invoices, approval queues, admin functions

**Specific role checks to verify:**
- [ ] Only `reel48_admin` can create/finalize/send/void invoices
- [ ] Only `reel48_admin` can approve/reject products and catalogs
- [ ] Only `corporate_admin`+ can generate/manage org codes
- [ ] Only `corporate_admin`+ can manage sub-brands
- [ ] Only `corporate_admin`+ can manage approval rules
- [ ] `employee` cannot see analytics endpoints (returns 403)
- [ ] Managers/admins can create bulk orders; employees cannot
- [ ] Approval queue shows only items the user's role can approve

### 2.6 Defense-in-Depth Filtering
For every service method that queries tenant data, verify:

- [ ] SQLAlchemy queries include explicit `company_id` and `sub_brand_id` filters
      in addition to RLS (double protection)
- [ ] Queries that return a single resource verify the resource belongs to the
      requesting user's tenant scope

### 2.7 Stripe Integration (Module 7)
Read all Stripe-related code in `backend/app/services/stripe_service.py`,
`backend/app/services/invoice_service.py`, and `backend/app/api/v1/webhooks.py`:

- [ ] Stripe API key is loaded from environment variable, never hardcoded
- [ ] Stripe API version is pinned
- [ ] All Stripe API calls are server-side only (no frontend imports)
- [ ] Invoice creation uses `auto_advance=False` for admin-created invoices
- [ ] Self-service invoices use `auto_advance=True`
- [ ] Amounts converted to cents for Stripe API (`int(amount * 100)`)
- [ ] Stripe metadata includes `reel48_company_id` and `reel48_sub_brand_id`
- [ ] Webhook endpoint verifies signature with `stripe.Webhook.construct_event()`
- [ ] Webhook processing is idempotent (handles duplicate events)
- [ ] Status priority prevents webhook status regression
- [ ] Webhook handler sets RLS session variables to empty strings before querying
- [ ] `billing_flow` is correctly set on every invoice: `assigned`, `self_service`, `post_window`
- [ ] Three billing flows are all implemented:
  - [ ] Flow 1: Reel48-assigned (manual admin creation)
  - [ ] Flow 2: Self-service (auto at checkout)
  - [ ] Flow 3: Post-window (consolidated after buying window closes)

### 2.8 Authentication Flow (Module 1)
Read `backend/app/api/v1/auth.py`, `backend/app/core/security.py`,
`backend/app/services/cognito_service.py`, `backend/app/services/registration_service.py`:

- [ ] JWT validation: signature, expiry, audience, issuer, token_use all checked
- [ ] JWKS caching with refresh
- [ ] Custom claims extracted: `custom:company_id`, `custom:sub_brand_id`, `custom:role`
- [ ] PostgreSQL session variables set after token validation
- [ ] Two onboarding paths both implemented:
  - [ ] Admin invite flow (single-use token, 72-hour expiry)
  - [ ] Self-registration via org code (two-step: validate → register)
- [ ] Rate limiting on unauthenticated endpoints (5 per IP per 15 min)
- [ ] Self-registered users always get `role = employee`
- [ ] Sub-brand validation: submitted `sub_brand_id` belongs to the org code's company
- [ ] Generic error messages (no enumeration of codes, emails, or sub-brands)

### 2.9 Service Layer Completeness
Verify every service file exists and has the expected methods:

- [ ] `cognito_service.py` — create user, disable user, update attributes
- [ ] `registration_service.py` — register via invite, register via org code
- [ ] `company_service.py` — CRUD for companies
- [ ] `sub_brand_service.py` — CRUD for sub-brands, default sub-brand creation
- [ ] `user_service.py` — CRUD, role management
- [ ] `invite_service.py` — create, consume, expire invites
- [ ] `org_code_service.py` — generate, validate, deactivate org codes
- [ ] `employee_profile_service.py` — CRUD for employee profiles
- [ ] `product_service.py` — CRUD, approve/reject products
- [ ] `catalog_service.py` — CRUD, approve/reject, manage buying windows, payment models
- [ ] `order_service.py` — create, update status, cancel orders
- [ ] `bulk_order_service.py` — CRUD, status lifecycle, item management
- [ ] `approval_service.py` — submit, approve, reject, approval queue, audit trail
- [ ] `invoice_service.py` — create, finalize, send, void, webhook processing
- [ ] `stripe_service.py` — Stripe API wrapper (customers, invoices, webhook verification)
- [ ] `email_service.py` — SES email sending
- [ ] `analytics_service.py` — aggregation queries for all analytics endpoints
- [ ] `notification_service.py` — create, list, mark read, announcements
- [ ] `wishlist_service.py` — add, remove, list wishlist items

### 2.10 Default Sub-Brand Rule
Verify that when a new company is created, a default sub-brand is automatically
created for it. Check:

- [ ] Company creation service/endpoint triggers default sub-brand creation
- [ ] The default sub-brand has a recognizable name (e.g., "Default" or company name)
- [ ] The default sub-brand has a valid `sub_brand_id` (not NULL)

---

## PART 3: FRONTEND AUDIT

### 3.1 App Router Structure
Read the Next.js App Router layout in `frontend/src/app/`. Verify:

- [ ] Route groups are correctly structured: `(public)`, `(authenticated)`, `(platform)`
- [ ] Public routes: `/login`, `/register`, `/invite/[token]`
- [ ] Authenticated routes: `/dashboard`, `/onboarding`, `/notifications`, `/wishlist`
- [ ] Platform routes: `/platform/dashboard`, `/platform/analytics`
- [ ] Admin analytics: `/admin/analytics`
- [ ] Each route group has its own `layout.tsx`
- [ ] Root layout imports global styles correctly

### 3.2 Authentication & Authorization (Frontend)
Read `frontend/src/lib/auth/context.tsx`, `frontend/src/lib/auth/hooks.ts`,
`frontend/src/components/features/auth/ProtectedRoute.tsx`:

- [ ] AuthProvider wraps the app and provides TenantContext to all children
- [ ] Token storage uses Amplify (NOT localStorage)
- [ ] Token refresh is handled automatically
- [ ] ProtectedRoute component guards authenticated routes
- [ ] Role-based rendering hides/shows features based on user role
- [ ] Logout clears all auth state

### 3.3 Carbon Design System Compliance
Read all component files in `frontend/src/components/`. Verify:

- [ ] Carbon components used (NOT custom recreations): Button, TextInput, Modal,
      DataTable, Tabs, Notification, Tag, Breadcrumb, Loading, Pagination, etc.
- [ ] Named imports from `@carbon/react` (no wildcard imports)
- [ ] Icons imported from `@carbon/react/icons` or `@carbon/icons-react`
- [ ] Icon sizing uses `size` prop (not Tailwind classes)
- [ ] No Tailwind classes overriding Carbon component internals
- [ ] Tailwind used ONLY for layout: flex, grid, gap, margin, padding
- [ ] `'use client'` directive on all files importing Carbon components
- [ ] Carbon v11 token names used (not v10)
- [ ] DataTable uses key destructuring pattern (no duplicate key errors)

### 3.4 Styling
Read `frontend/src/styles/carbon-theme.scss` and `frontend/src/app/globals.scss`:

- [ ] Carbon styles load BEFORE Tailwind directives
- [ ] `@use` syntax (not `@import`) for Carbon SCSS
- [ ] Theme customization uses `$fallback: themes.$g10` with `$theme: (...)`
- [ ] Brand color `#292c2f` (charcoal) is configured
- [ ] Teal interactive `#0a6b6b` is configured
- [ ] Accent palette defined for badges/charts
- [ ] No v10 token names in SCSS

### 3.5 API Client
Read `frontend/src/lib/api/client.ts`:

- [ ] Centralized API client with base URL configuration
- [ ] Automatic JWT token attachment on requests
- [ ] Response transformation to standard format
- [ ] Error handling for 401 (trigger token refresh)
- [ ] Error handling for 403, 404, 500
- [ ] No Stripe SDK imports in frontend code

### 3.6 TypeScript Types
Read `frontend/src/types/`. Verify:

- [ ] All API response types defined
- [ ] User roles typed as union type matching the 5 backend roles
- [ ] Tenant context type matches backend TenantContext
- [ ] All entity types defined: Company, SubBrand, User, Product, Catalog,
      Order, BulkOrder, Invoice, Notification, Wishlist, etc.
- [ ] Analytics types defined
- [ ] Registration types defined

### 3.7 Key Pages and Components
Verify these critical pages/components exist and are functional:

- [ ] Login page with email/password form
- [ ] Registration page with two-step org code flow
- [ ] Invite acceptance page
- [ ] Employee dashboard with: profile nudge, recent orders, active catalogs,
      notifications, wishlist highlights
- [ ] Onboarding wizard
- [ ] Notification bell component (header)
- [ ] Notification feed page
- [ ] Wishlist page
- [ ] Product card component
- [ ] Sidebar navigation with role-based menu items
- [ ] Header with user info and notification bell
- [ ] Admin analytics page (corporate/sub-brand admin)
- [ ] Platform analytics page (reel48_admin)
- [ ] Platform dashboard

---

## PART 4: TEST SUITE AUDIT

### 4.1 Test Infrastructure
Read `backend/tests/conftest.py`. Verify:

- [ ] Dual database sessions: `admin_db_session` (superuser) and `db_session` (reel48_app role)
- [ ] `setup_database` fixture grants permissions to `reel48_app` on ALL tables
      (check that tables from ALL 9 modules are included in the grant list)
- [ ] Alembic migrations run via subprocess (not Python API)
- [ ] JWT test infrastructure: `create_test_token()` with RSA keypair
- [ ] JWKS patching with cache reset (`_jwks_keys = None`, `_jwks_fetched_at = 0.0`)
- [ ] Multi-tenant fixtures: Company A (Brand A1, A2) and Company B (Brand B1)
- [ ] Role-specific User + Token fixture pairs (cognito_sub matches)
- [ ] Token-only fixtures for 403 tests
- [ ] `reel48_admin_user` + `reel48_admin_user_token` fixtures
- [ ] MockCognitoService autouse fixture
- [ ] MockStripeService autouse fixture
- [ ] MockEmailService autouse fixture
- [ ] `no_rate_limit` autouse fixture

### 4.2 Test Coverage by Module

**Module 1 — Auth & Multi-Tenancy:**
- [ ] `test_auth.py` — login, token validation, role extraction
- [ ] `test_registration.py` — invite flow, org code flow, rate limiting, error generics
- [ ] `test_companies.py` — CRUD, default sub-brand auto-creation
- [ ] `test_sub_brands.py` — CRUD, company-scoped access
- [ ] `test_users.py` — CRUD, role management
- [ ] `test_invites.py` — create, consume, expire, single-use enforcement
- [ ] `test_org_codes.py` — generate, validate, deactivate, one-active-per-company
- [ ] `test_isolation.py` — RLS enforcement for all Module 1 tables

**Module 2 — Employee Profiles:**
- [ ] `test_employee_profiles.py` — CRUD, profile completeness, tenant scoping

**Module 3 — Product Catalog & Brand Management:**
- [ ] `test_products.py` — CRUD, approve/reject, tenant isolation
- [ ] `test_catalogs.py` — CRUD, approve/reject, payment models, buying windows
- [ ] `test_platform_catalog.py` — reel48_admin catalog management

**Module 4 — Ordering Flow:**
- [ ] `test_orders.py` — create, status transitions, role-based visibility, tenant isolation
- [ ] `test_platform_orders.py` — reel48_admin order management

**Module 5 — Bulk Ordering:**
- [ ] `test_bulk_orders.py` — CRUD, status lifecycle, item management, tenant isolation
- [ ] `test_platform_bulk_orders.py` — reel48_admin bulk order management

**Module 6 — Approval Workflows:**
- [ ] `test_approvals.py` — submit, approve, reject, audit trail
- [ ] `test_approval_endpoints.py` — approval queue, role-based filtering
- [ ] `test_platform_approvals.py` — reel48_admin approval dashboard
- [ ] `test_approval_notifications.py` — email notifications on approval events

**Module 7 — Invoicing & Client Billing:**
- [ ] `test_invoices.py` — create, finalize, send, void, webhook processing
- [ ] Stripe webhook tests: signature verification, idempotent processing, status non-regression
- [ ] All three billing flows tested (assigned, self_service, post_window)
- [ ] Client-facing invoice visibility (corporate_admin can view, employee cannot)

**Module 8 — Analytics Dashboard:**
- [ ] `test_analytics.py` — all analytics endpoints, role-based scoping, date filtering
- [ ] Platform admin analytics vs tenant analytics separation

**Module 9 — Employee Engagement:**
- [ ] `test_notifications.py` — CRUD, read/unread, announcements, tenant isolation
- [ ] `test_wishlists.py` — add/remove, duplicate prevention, tenant isolation

### 4.3 Mandatory Test Categories (Every Module)
For EACH module, verify all three categories exist:

**Functional tests:**
- [ ] Happy path for every endpoint
- [ ] Error cases (validation errors, not found, conflicts)
- [ ] Status transitions and business rules

**Isolation tests:**
- [ ] Cross-company: Company A cannot see Company B's data
- [ ] Cross-sub-brand: Brand A1 cannot see Brand A2's data (within same company)
- [ ] Corporate admin CAN see all sub-brands within their company
- [ ] reel48_admin CAN see all companies

**Authorization tests:**
- [ ] Each role tested against endpoints they should/shouldn't access
- [ ] 401 for unauthenticated requests
- [ ] 403 for insufficient permissions
- [ ] Employee cannot access admin endpoints
- [ ] Sub-brand admin cannot access corporate admin endpoints

### 4.4 Specific Critical Test Cases
Verify these specific high-risk test cases exist:

**Security:**
- [ ] Rate limiting returns 429 after 5 attempts (org code + registration endpoints)
- [ ] Webhook endpoint rejects invalid Stripe signatures (400)
- [ ] Generic error messages don't reveal org code existence or email registration status
- [ ] Tenant context cannot be spoofed via request parameters

**Data integrity:**
- [ ] Invoices cannot be created before buying window closes (post-window flow)
- [ ] Self-registered users always get `employee` role (cannot escalate)
- [ ] Invite tokens are single-use (second use fails)
- [ ] Only one active org code per company (generating new deactivates old)
- [ ] Duplicate webhook events don't cause duplicate updates
- [ ] Invoice status cannot regress (paid → sent should be rejected)

**Business rules:**
- [ ] Default sub-brand created when company is created
- [ ] Bulk order status lifecycle enforced (can't skip states)
- [ ] Order status transitions enforced
- [ ] Product/catalog must be approved before going live
- [ ] Approval rules trigger correctly (e.g., orders above threshold require higher approval)

### 4.5 Frontend Tests
Read all test files in `frontend/src/__tests__/`:

- [ ] `api-client.test.ts` — API client configuration, token attachment, error handling
- [ ] `auth-context.test.tsx` — AuthProvider, login, logout, token refresh
- [ ] `login-page.test.tsx` — form rendering, validation, submission
- [ ] `register-page.test.tsx` — two-step org code flow, sub-brand selection
- [ ] `invite-page.test.tsx` — invite token acceptance flow
- [ ] `protected-route.test.tsx` — route guarding, role-based redirects
- [ ] `sidebar.test.tsx` — role-based navigation items
- [ ] `product-card.test.tsx` — product display, wishlist integration
- [ ] `dashboard-onboarding.test.tsx` — onboarding wizard, profile nudges
- [ ] `onboarding-wizard.test.tsx` — step-by-step onboarding flow
- [ ] `notifications.test.tsx` — notification feed, read/unread, bell component
- [ ] `wishlist.test.tsx` — add/remove items, empty state

### 4.6 Test Execution
Run the full test suite and report results:

```bash
# Backend tests
cd backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -100

# Frontend tests
cd frontend && npx vitest run --reporter=verbose 2>&1 | tail -100
```

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] No skipped tests without documented reason
- [ ] No warnings that indicate real issues

---

## PART 5: SECURITY AUDIT

### 5.1 Authentication Security
- [ ] JWT tokens validated server-side (not just decoded)
- [ ] JWKS endpoint cached with refresh on failure
- [ ] Token expiry checked
- [ ] Audience and issuer verified
- [ ] No tokens stored in localStorage (frontend)
- [ ] Refresh token handling via Amplify

### 5.2 Authorization Security
- [ ] Role checks happen server-side (not just frontend)
- [ ] RLS enabled AND forced on every tenant table
- [ ] Sub-brand scoping uses `AS RESTRICTIVE` (AND logic, not OR)
- [ ] Defense-in-depth: service layer filters by tenant even with RLS
- [ ] Platform admin endpoints verify `reel48_admin` role
- [ ] `reel48_admin` RLS bypass only triggered when role is verified

### 5.3 Input Validation
- [ ] All request bodies validated via Pydantic schemas
- [ ] No raw SQL with user input (parameterized queries only)
- [ ] Exception: `SET LOCAL` uses f-strings for session variables, but these values
      come from the validated JWT (not user input) — verify this is the case
- [ ] File upload validation: type, size, sanitized filenames
- [ ] Rate limiting on unauthenticated endpoints

### 5.4 Webhook Security
- [ ] Stripe webhook verifies signature before processing
- [ ] Webhook endpoint does NOT use JWT authentication
- [ ] Webhook returns 200 quickly (heavy processing via SQS)
- [ ] Webhook processing is idempotent

### 5.5 Data Exposure Prevention
- [ ] No password hashes in API responses
- [ ] No internal IDs leaked (Stripe customer IDs, Cognito sub, etc.)
- [ ] Error messages don't reveal internal state (generic errors for auth failures)
- [ ] Pre-signed URLs have appropriate expiry (1hr download, 15min upload)
- [ ] No raw S3 URLs exposed to frontend

---

## PART 6: CROSS-MODULE CONSISTENCY AUDIT

### 6.1 Pattern Consistency
Compare patterns across all 9 modules. Report any inconsistencies:

- [ ] All models use the same base classes consistently
- [ ] All endpoints use the same response format
- [ ] All endpoints use the same error format
- [ ] All list endpoints have pagination
- [ ] All service methods follow the same pattern (tenant filtering, error handling)
- [ ] All role checks use the same mechanism
- [ ] Delete endpoints consistently use 200 (soft) or 204 (hard)

### 6.2 Naming Consistency
- [ ] All API endpoints use snake_case and plural nouns
- [ ] All JSON response fields use snake_case
- [ ] All database tables/columns use snake_case
- [ ] All Python files use snake_case
- [ ] All TypeScript files use appropriate casing (PascalCase for components)
- [ ] No mixed naming styles within a module

### 6.3 Import and Dependency Hygiene
- [ ] No circular imports in backend Python code
- [ ] No unused imports
- [ ] Service layer properly separated from API layer (no direct DB queries in routes)
- [ ] No direct Stripe SDK imports in frontend code
- [ ] Backend dependencies in `pyproject.toml` match what's imported
- [ ] Frontend dependencies in `package.json` match what's imported

---

## PART 7: HARNESS COMPLIANCE AUDIT

### 7.1 CLAUDE.md Accuracy
Read the root `CLAUDE.md` and verify every statement is still accurate:

- [ ] Technology stack section matches actual dependencies
- [ ] Multi-tenancy architecture section matches implementation
- [ ] Role model table matches actual role behavior
- [ ] API conventions match actual endpoint patterns
- [ ] Database conventions match actual schema
- [ ] Module build order matches what was actually built
- [ ] Directory structure matches actual directory structure

### 7.2 Rule File Accuracy
For each rule file in `.claude/rules/`, verify:

- [ ] `authentication.md` — role hierarchy, access matrix, onboarding flows all accurate
- [ ] `database-migrations.md` — RLS patterns, base classes, circular FK resolution all accurate
- [ ] `api-endpoints.md` — tenant context, response format, unauthenticated exceptions all accurate
- [ ] `testing.md` — test infrastructure, fixture patterns, mock patterns all accurate
- [ ] `stripe-invoicing.md` — billing flows, webhook patterns, data model all accurate
- [ ] `s3-storage.md` — path structure, pre-signed URL patterns accurate
- [ ] `carbon-design-system.md` — import patterns, styling boundaries, theme config accurate
- [ ] `harness-maintenance.md` — maintenance protocol, checklist accurate

### 7.3 ADR Accuracy
For each ADR in `docs/adr/`, verify the decision is still valid and matches implementation:

- [ ] `001` — Shared database multi-tenancy (implemented correctly)
- [ ] `002` — RLS over application isolation (implemented correctly)
- [ ] `003` — Default sub-brand pattern (implemented correctly)
- [ ] `004` — REST before GraphQL (no GraphQL introduced)
- [ ] `005` — Cognito over third-party auth (Cognito used)
- [ ] `006` — Stripe for invoicing (Stripe used)
- [ ] `007` — Controlled self-registration (both flows implemented)
- [ ] `008` — IBM Carbon design system (Carbon used, Tailwind for layout only)

### 7.4 Harness Changelog
Read `docs/harness-changelog.md`:

- [ ] Entries exist for each module completion
- [ ] End-of-session audits logged
- [ ] All harness updates have corresponding changelog entries

---

## PART 8: COMPLETENESS CHECKLIST

### 8.1 Module Completeness Matrix
For each module, verify ALL expected deliverables exist:

| Module | Models | Migrations | Services | Endpoints | Schemas | Tests | Frontend |
|--------|--------|-----------|----------|-----------|---------|-------|----------|
| 1. Auth & Multi-Tenancy | Company, SubBrand, User, Invite, OrgCode | 001 | 7 services | auth, companies, sub_brands, users, invites, org_codes | auth, company, sub_brand, user, invite, org_code | test_auth, test_registration, test_companies, test_sub_brands, test_users, test_invites, test_org_codes, test_isolation | login, register, invite, auth context |
| 2. Employee Profiles | EmployeeProfile | 002 | employee_profile_service | employee_profiles | employee_profile | test_employee_profiles | (profile UI) |
| 3. Catalog & Brand Mgmt | Product, Catalog, CatalogProduct | 003 | product_service, catalog_service | products, catalogs, platform/products, platform/catalogs | product, catalog | test_products, test_catalogs, test_platform_catalog | product card |
| 4. Ordering Flow | Order, OrderLineItem | 004 | order_service | orders, platform/orders | order | test_orders, test_platform_orders | (order UI) |
| 5. Bulk Ordering | BulkOrder, BulkOrderItem | 005 | bulk_order_service | bulk_orders, platform/bulk_orders | bulk_order | test_bulk_orders, test_platform_bulk_orders | (bulk order UI) |
| 6. Approval Workflows | ApprovalRequest, ApprovalRule | 006 | approval_service | approvals, approval_rules, platform/approvals, platform/approval_rules | approval | test_approvals, test_approval_endpoints, test_platform_approvals, test_approval_notifications | (approval UI) |
| 7. Invoicing & Billing | Invoice | 007 | invoice_service, stripe_service | invoices, platform/invoices, webhooks | invoice | test_invoices | (invoice UI) |
| 8. Analytics Dashboard | (none — reads existing) | (none) | analytics_service | analytics, platform/analytics | analytics | test_analytics | analytics pages |
| 9. Employee Engagement | Notification, Wishlist | 009 | notification_service, wishlist_service | notifications, wishlists | notification, wishlist | test_notifications, test_wishlists | notifications, wishlist, onboarding, dashboard |

For each cell, verify the deliverable exists and is non-trivial (not just stubs).

### 8.2 Missing Pieces
Check for anything that should exist but doesn't:

- [ ] Is there a migration `008`? If not, why? (Module 8 has no tables — confirm this is correct)
- [ ] Are there any TODO/FIXME/HACK comments left in the code?
- [ ] Are there any empty service methods or stub endpoints?
- [ ] Are there any models referenced but not defined?
- [ ] Are there any imports that reference non-existent modules?

### 8.3 Environment Configuration
Read `backend/app/core/config.py`:

- [ ] All required environment variables documented
- [ ] Stripe keys loaded from env vars
- [ ] Database URL loaded from env vars
- [ ] Cognito configuration loaded from env vars
- [ ] Redis/ElastiCache configuration for rate limiting
- [ ] SES configuration for email

---

## PART 9: FINAL SUMMARY REPORT

After completing all checks above, produce a summary report with:

1. **Total checks performed:** (count)
2. **Passes:** (count)
3. **Failures by severity:**
   - CRITICAL (security vulnerabilities, data isolation gaps): (count + list)
   - HIGH (broken functionality, missing required features): (count + list)
   - MEDIUM (inconsistencies, non-standard patterns): (count + list)
   - LOW (style issues, minor naming inconsistencies): (count + list)
4. **Top 5 issues to fix first** (prioritized by risk)
5. **Modules with the most issues** (ranked)
6. **Harness accuracy score:** (% of harness statements that match implementation)
7. **Test coverage gaps:** (any untested areas identified)
8. **Overall platform readiness assessment:** (Ready / Needs Work / Significant Issues)

---

# END OF AUDIT PROMPT
