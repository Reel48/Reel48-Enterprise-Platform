# Harness Changelog
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This is the HARNESS CHANGELOG — a chronological log of every change       ║
# ║  made to the development harness (CLAUDE.md files, rule files, ADRs,       ║
# ║  and prompt templates).                                                    ║
# ║                                                                            ║
# ║  WHY DOES IT EXIST?                                                        ║
# ║                                                                            ║
# ║  The changelog serves three critical purposes:                             ║
# ║                                                                            ║
# ║  1. AUDIT TRAIL: Proves that harness reviews are actually happening.       ║
# ║     If there's no changelog entry after a module, the review was skipped.  ║
# ║                                                                            ║
# ║  2. KNOWLEDGE CAPTURE: Records WHY each change was made. Six months from   ║
# ║     now, you'll wonder "why does this rule exist?" The changelog tells     ║
# ║     you which module, which session, and which mistake prompted it.        ║
# ║                                                                            ║
# ║  3. TREND TRACKING: Over time, the changelog reveals whether the harness   ║
# ║     is improving. Fewer reactive updates per module = the harness is       ║
# ║     maturing. More gaps found = the project is hitting new territory.      ║
# ║                                                                            ║
# ║  HOW TO USE:                                                               ║
# ║  Append a new entry at the TOP of the log (newest first) after every       ║
# ║  session audit, post-module review, or reactive update. Follow the         ║
# ║  format shown in the initial entry below.                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

---

## 2026-04-20 — Session 0: Harness Teardown (Simplification Refactor)

**Type:** Preemptive teardown before major architectural simplification.
**Session:** Session 0 of the four-session plan at `~/.claude/plans/yes-please-write-the-memoized-karp.md`.

### Why
The platform is being simplified before launch:
- Sub-brand dimension (`sub_brand_id`) is being removed from every table, endpoint, and UI.
- Catalog, Products, Orders, Bulk Orders, Wishlists, and Approvals are being deleted entirely.
- Stripe invoicing (all three flows, the webhook, `StripeService`, local `invoices` table) is being removed — Shopify will own commerce.
- Role model collapses from 5 to 4: `reel48_admin`, `company_admin`, `manager`, `employee`.

The existing harness (~800 lines of sub-brand rules in the root CLAUDE.md alone, multiple rule files, 3 ADRs, ~10 prompts) would actively mislead Sessions A and B if left in place — Claude Code would faithfully re-implement what we are trying to remove. This session neutralizes the stale guidance first.

### Changes Made

- **Deleted:** `.claude/rules/stripe-invoicing.md` (Stripe integration removed).
- **Deleted prompts (12 files):** `module4-ordering-flow.md`, `module5-bulk-ordering.md`, `module6-approval-workflows.md`, `module7-invoicing-billing.md`, `module9-employee-engagement.md`, all `frontend-crud-session{1,2,3,4,5,6,7}-*.md`.
- **Rewrote rule files** down to only rules that are still true today, with a top-of-file "SIMPLIFICATION IN PROGRESS" banner: `.claude/rules/authentication.md`, `.claude/rules/database-migrations.md`, `.claude/rules/testing.md`, `.claude/rules/api-endpoints.md`, `.claude/rules/s3-storage.md`.
- **Rewrote the three CLAUDE.md files** (root, backend, frontend) with the same banner. Stripped Module 3–9 table schemas, `TenantBase` references, Stripe integration patterns, invoice lifecycle rules, order/bulk-order state machines, 5-role authorization examples, two-step registration, sub-brand-scoped routing, and `{sub_brand_slug}` in S3 paths.
- **Added superseded banners to ADRs:**
  - ADR-001 (shared-database multi-tenancy) — partially superseded (RLS decision stands; sub-brand dimension removed).
  - ADR-003 (default sub-brand pattern) — superseded by ADR-009 (pending).
  - ADR-006 (Stripe for invoicing) — superseded by ADR-010 (pending).
  - ADR-007 (controlled self-registration) — partially superseded (org-code concept stands; two-step flow + sub-brand selection removed).
- **Memory:** Added `project_simplification_plan.md` memory; updated `MEMORY.md` index; flagged `project_production_infra.md` (Stripe being decommissioned) and `project_frontend_pages.md` (superseded by simplification plan).

### Impact
Sessions A (backend), B (frontend), and D (authoritative harness rewrite) can now proceed without being misled by the old harness. ADRs 009 and 010 will be authored in Session D to make the "superseded by" pointers real. The top-of-file banners in each CLAUDE.md will be removed in Session D once the code matches the final architecture.

---

## 2026-04-13 — Corporate Admin Sidebar Redesign (Session Audit)

**Type:** End-of-session audit (Trigger 1) — redesigned sidebar navigation for
the corporate_admin role.
**Session:** Frontend-only session to restructure corporate admin navigation.

### Changes Made

- **File changed:** `frontend/src/components/layout/Sidebar.tsx`
- **Change:** Replaced inherited `corporateAdminNav` (spread from subBrandAdminNav)
  with a flat 13-item array. Added bottom profile section with initials/S3 photo,
  user name, role label, and link to /profile. Profile data fetched via React Query
  `['my-profile']` cache. New icons imported: `Product`, `Idea`, `AiGenerate`,
  `ArrowsHorizontal`.
- **Reason:** Sidebar needed a curated, intentional ordering for corporate admins
  rather than the accumulated inheritance from lower roles.
- **Impact:** Corporate admin sidebar now shows exactly 13 items in a specific order
  with a profile section at the bottom. Other roles unchanged.

- **Files created:** `frontend/src/app/(authenticated)/inside/page.tsx`,
  `frontend/src/app/(authenticated)/ai/page.tsx`,
  `frontend/src/app/(authenticated)/products/page.tsx`
- **Change:** Three new placeholder pages for InsideReel48+, Reel48+ AI, and Products.
- **Reason:** New sidebar items needed corresponding routes.

- **Files changed:** `frontend/src/app/(authenticated)/catalog/page.tsx`,
  `frontend/src/app/(authenticated)/admin/approvals/page.tsx`,
  `frontend/src/app/(authenticated)/settings/page.tsx`
- **Change:** Added in-page subpage buttons (Manage Catalogs, Approval Rules,
  Sub-Brands) to their respective parent pages, visible only to appropriate roles.
  Settings page title changed to "Brand Settings".
- **Reason:** These subpages were removed from the sidebar and made accessible
  via buttons within their parent pages instead.

### New Pattern: Flat Role-Specific Navigation Arrays

The `corporateAdminNav` is now a flat, non-inherited array rather than spreading
from lower-role arrays. This allows curated ordering and item selection per role.
Other roles still use the inheritance model — the flat approach will be applied
to them in future sessions.

### New Pattern: Subpage Buttons Instead of Sidebar Items

Some pages (Manage Catalogs, Approval Rules, Sub-Brands) are accessed via
buttons within their parent pages rather than as dedicated sidebar items.
These buttons use `useHasRole()` for role-gated visibility.

### Reviewed — No Additional Harness Updates Needed

- No new patterns that need CLAUDE.md or rule file updates beyond this changelog
- No ADR needed (UI-only change, no architectural decision)
- No missing guidance discovered

---

## 2026-04-10 — User Management Page Enhancement (Session Audit)

**Type:** End-of-session audit (Trigger 1) — enhanced admin/users page with full
invite management, org code management, and bug fixes.
**Session:** Frontend-only session to add missing user management capabilities.

### Changes Made

- **File changed:** `frontend/src/app/(authenticated)/admin/users/page.tsx`
- **Change:** Restructured into 3 Carbon Tabs (Users, Invites, Org Code). Fixed
  invite modal (was sending `fullName` instead of `targetSubBrandId`). Fixed
  deactivate endpoint (`POST /deactivate` → `DELETE /users/{id}`).
- **Reason:** Backend APIs for invites and org codes existed but had no frontend.
  Invite modal was non-functional due to schema mismatch with backend.
- **Impact:** Admins can now manage invites (list, create with sub-brand, delete)
  and corporate admins can manage org codes (generate, copy, deactivate).

- **File changed:** `frontend/src/app/(authenticated)/admin/users/_types.ts` (new)
- **Change:** Extracted User, Invite, OrgCode, SubBrand interfaces.
- **Reason:** Page was growing too large for a single file; co-located types keep
  the page manageable.

- **File changed:** `frontend/src/app/(authenticated)/admin/users/_hooks.ts` (new)
- **Change:** 9 React Query hooks for all CRUD operations across users, invites,
  sub-brands, and org codes.
- **Reason:** Same extraction rationale. Hooks handle API calls, cache invalidation,
  and 404-as-null pattern for org codes.

- **File changed:** `frontend/CLAUDE.md`
- **Change:** Updated routing structure to document new `_types.ts` and `_hooks.ts`
  co-located files under `admin/users/`.
- **Reason:** Future sessions need to know these files exist.

### Patterns Established

- **Co-located underscore files for complex pages:** When a page grows beyond ~300
  lines, extract hooks into `_hooks.ts` and types into `_types.ts` in the same
  directory. The `_` prefix tells Next.js these are not route segments.
- **Org code 404-as-null pattern:** `useCurrentOrgCode()` catches 404 from the API
  and returns `null` as data instead of throwing. Uses `retry: false` for 404s.
- **Sub-brand auto-select for sub_brand_admin:** In invite modals, auto-set
  `inviteSubBrandId` from `user.tenantContext.subBrandId` and show a read-only
  field instead of a dropdown.

### Harness Review
- New pattern introduced? Yes — co-located `_hooks.ts`/`_types.ts` for complex pages.
- Existing pattern violated? No.
- New decision made? No — all patterns follow existing Carbon + React Query conventions.
- Missing guidance discovered? No.
- Prompt template needed? No — this is a one-off page enhancement.

---

## 2026-04-10 — Frontend-Backend Field Name Audit & Fix (TRIGGER 3)

**Type:** Reactive update (Trigger 3) — multiple frontend pages used field names
that did not match backend Pydantic response schemas.
**Session:** Systematic audit of all frontend TypeScript types and page files against
backend schemas to eliminate runtime errors (403, 404, 422) and TypeScript compile errors.

### Root Cause
Frontend type definitions were authored speculatively during page creation without
cross-referencing the actual backend Pydantic response schemas. The API client's
`deepTransformKeys` converts snake_case→camelCase automatically, but the frontend
types assumed field names that didn't exist in the backend (e.g., `itemCount` instead
of `totalItems`, `requestType` instead of `entityType`, `profilePhotoS3Key` instead
of `profilePhotoUrl`).

### Changes Made

- **7 type definition files rewritten** to exactly match backend schemas:
  - `types/orders.ts` — removed `itemCount`, renamed `totalPrice`→`lineTotal`, added shipping/cancel fields
  - `types/bulk-orders.ts` — `name`→`title`, `itemCount`→`totalItems`, `createdById`→`createdBy`, `lineItems`→`items`
  - `types/profiles.ts` — removed `fullName`/`email` (not in backend profile), `profilePhotoS3Key`→`profilePhotoUrl`, fixed `SHIRT_SIZES` (removed 4XL/5XL)
  - `types/invoices.ts` — `createdById`→`createdBy`, removed `companyName`, added missing fields
  - `types/catalogs.ts` — removed `productCount`/`companyName`, added `slug`/`approvedBy`/`createdBy`/`deletedAt`
  - `types/approvals.ts` — complete rewrite (all field names were wrong)
  - `types/companies.ts` — removed `stripeCustomerId`

- **10 page files fixed** to use correct field names:
  - `orders/page.tsx` — `itemCount`→`subtotal` column with `formatPrice` renderer
  - `orders/[id]/page.tsx` — `OrderWithItems` import, `lineItems.length`, `lineTotal`
  - `bulk-orders/page.tsx` — `title`, `totalItems`, `createdBy`
  - `bulk-orders/[id]/page.tsx` — same plus `items` instead of `lineItems`
  - `profile/page.tsx` — `fullName`/`email` sourced from `useAuth()` (read-only), `profilePhotoUrl`
  - `admin/approvals/page.tsx` — `entityType`, `requestedBy`, removed `amount` column, `decidedBy`/`decidedAt`
  - `catalog/page.tsx` — removed `productCount` reference
  - `platform/companies/[id]/page.tsx` — `stripeCustomerId`→`slug`
  - `platform/catalogs/page.tsx` — removed `companyName`/`productCount`
  - `platform/invoices/page.tsx` + `[id]/page.tsx` — `companyName`→`companyId`

- **Reason:** Runtime errors (422 from unknown fields, undefined property access) and TypeScript compile errors
- **Impact:** All 30+ frontend pages now use field names that exactly match backend API responses; `tsc --noEmit` passes with 0 errors

### Session Review
- **New pattern?** Yes — when profile data doesn't include user identity fields (`fullName`, `email`), source them from `useAuth()` context instead. This is because the backend Profile model is separate from the User model.
- **Pattern violated?** Yes — the original page builds created type definitions without verifying against backend schemas. This violated the implicit principle of "types must match the API contract."
- **New decision?** No
- **Missing guidance?** Yes — the harness had no explicit rule requiring frontend type definitions to be verified against backend Pydantic schemas. Added note below.
- **Reusable task?** Yes — the audit methodology (compare every backend schema file against every frontend type file) could be a prompt template for future use.

### Harness Gap Identified
**Gap:** No rule explicitly requires that frontend TypeScript types match backend Pydantic
response schemas field-by-field. The API naming convention section in `frontend/CLAUDE.md`
mentions snake_case→camelCase transformation but doesn't mandate verifying field names
against the actual backend schema files.

**Recommendation:** When building frontend pages that consume API data, always read the
corresponding backend schema file (`backend/app/schemas/{module}.py`) and verify that
every field in the frontend TypeScript interface maps to a real field in the Pydantic
response model (after camelCase transformation).

### Harness Health Metrics
- **Mistakes caught:** 35+ field name mismatches across 7 type files and 10 page files
- **Harness gaps:** 1 (missing schema verification rule)
- **Rules added:** 0 (recommendation noted above; formal rule addition deferred)
- **First-attempt acceptance rate:** TypeScript passed with 0 errors after all fixes applied

---

## 2026-04-10 — Build Remaining 9 Frontend Pages (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Session:** Build 9 remaining frontend pages identified by cross-referencing sidebar
links, href patterns, and router.push calls against existing page.tsx files.

### Changes Made

- **Files created:** 9 new page components
  - `frontend/src/app/(authenticated)/orders/[id]/page.tsx` — Order detail with line items, cancel action
  - `frontend/src/app/(authenticated)/bulk-orders/[id]/page.tsx` — Bulk order detail with submit/approve/cancel
  - `frontend/src/app/(authenticated)/bulk-orders/new/page.tsx` — Create bulk order form
  - `frontend/src/app/(platform)/platform/companies/[id]/page.tsx` — Company detail with edit form and sub-brands list
  - `frontend/src/app/(platform)/platform/invoices/[id]/page.tsx` — Invoice detail with Stripe info and lifecycle actions
  - `frontend/src/app/(authenticated)/settings/page.tsx` — Account info and password change form
  - `frontend/src/app/(authenticated)/admin/users/page.tsx` — User management with invite modal and role filter
  - `frontend/src/app/(authenticated)/admin/brands/page.tsx` — Sub-brand management with create modal
  - `frontend/src/app/(authenticated)/invoices/page.tsx` — Tenant-scoped invoice list with status filter
  - **Reason:** In-app links (detail pages from list views, sidebar nav, header menu) pointed to routes without page.tsx files
  - **Impact:** All frontend navigation links now resolve to real pages; 30 total routes compile

### Session Review
- **New pattern?** No — all pages follow established patterns
- **Pattern violated?** Minor: Carbon `Dropdown` requires a `label` prop (not just `titleText`). Fixed during build verification.
- **New decision?** No
- **Missing guidance?** The `ApiResponse.meta` type is `Record<string, unknown>`, causing `total > perPage` to fail TypeScript strict checks. Fixed with `Number()` cast. This is a pre-existing type gap in `types/api.ts` (the `meta` type is too loose), not a harness gap.
- **Reusable task?** No

### Harness Health Metrics
- **Mistakes per module:** 2 minor TS errors (missing Dropdown `label`, `unknown` comparison) — fixed in same session
- **Harness gaps:** 0
- **Rules added:** 0
- **First-attempt acceptance rate:** Build succeeded on third attempt after two quick fixes

---

## 2026-04-10 — Build Missing Frontend Pages (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Session:** Build 8 missing frontend pages that caused 404 errors in production

### Changes Made

- **Files created:** 7 new TypeScript type definition files in `frontend/src/types/`
  - `orders.ts`, `catalogs.ts`, `bulk-orders.ts`, `approvals.ts`, `invoices.ts`, `companies.ts`, `profiles.ts`
  - **Reason:** Pages need typed interfaces for API responses; no domain types existed beyond engagement/auth/storage
  - **Impact:** All future frontend work on these domains has typed interfaces ready

- **Files created:** 8 new page components
  - `frontend/src/app/(authenticated)/profile/page.tsx`
  - `frontend/src/app/(authenticated)/orders/page.tsx`
  - `frontend/src/app/(authenticated)/catalog/page.tsx`
  - `frontend/src/app/(authenticated)/admin/approvals/page.tsx`
  - `frontend/src/app/(authenticated)/bulk-orders/page.tsx`
  - `frontend/src/app/(platform)/platform/companies/page.tsx`
  - `frontend/src/app/(platform)/platform/catalogs/page.tsx`
  - `frontend/src/app/(platform)/platform/invoices/page.tsx`
  - **Reason:** Sidebar navigation linked to these routes but no page.tsx existed, causing 404s in production
  - **Impact:** All sidebar navigation links now resolve to real pages

### Session Review
- **New pattern?** No — all pages follow established patterns from dashboard, notifications, wishlist, and analytics pages
- **Pattern violated?** No
- **New decision?** No — all pages use existing conventions (DataTable key destructuring, React Query hooks, Carbon components, status color mapping)
- **Missing guidance?** No — the existing harness rules (carbon-design-system.md DataTable key pattern, api-endpoints.md, frontend CLAUDE.md) covered all scenarios
- **Reusable task?** No — the `prompts/frontend-missing-pages.md` prompt already existed from the prior session

### Harness Health Metrics
- **Mistakes per module:** 0 — build passed on first attempt with zero TS errors
- **Harness gaps:** 0 — all patterns were well-documented
- **Rules added:** 0
- **First-attempt acceptance rate:** Build succeeded first try

---

## 2026-04-10 — Production Deployment & Infrastructure Session (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Session:** Production infrastructure deployment

### Changes Made
- **File changed:** `vercel.json`
- **Change:** Removed `rootDirectory` property (project-level setting, not valid in vercel.json schema)
- **Reason:** Vercel deployment failed with schema validation error

- **File created:** `prompts/frontend-missing-pages.md`
- **Change:** Comprehensive prompt template for building 8 missing frontend pages that cause 404 errors
- **Reason:** Sidebar navigation links to pages without page.tsx files; work deferred to dedicated session

### Session Review
- **New pattern?** No — deployment follows standard AWS/Vercel patterns
- **Pattern violated?** No
- **New decision?** Docker images for ECS Fargate must be built with `--platform linux/amd64` on Apple Silicon Macs
- **Missing guidance?** Production deployment procedures not documented in harness (acceptable — one-time setup, not a recurring pattern)
- **Reusable task?** The `prompts/frontend-missing-pages.md` prompt was created for the page-building session

### Deployment Notes (For Reference)
- All 9 Alembic migrations applied to production RDS
- ACM certificate required adding `0 issue "amazon.com"` CAA record to DNS
- ECS task definition pinned to `runtimePlatform: {cpuArchitecture: X86_64}`
- SES MAIL FROM DNS records added; awaiting propagation
- 8 frontend pages identified as missing — prompt created, work deferred to next session

### Frontend Pages Status
**Built:** dashboard, notifications, wishlist, onboarding, admin/analytics, platform/dashboard, platform/analytics
**Missing (404):** catalog, orders, profile, bulk-orders, admin/approvals, platform/companies, platform/catalogs, platform/invoices
**Also missing but lower priority:** invoices (tenant), admin/users, admin/brands, settings

---

## 2026-04-10 — S3 Storage Service Phase 4: Frontend Integration & Harness Updates (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** S3 Storage Service — Phase 4 (Final Phase)

### Changes Made
- **File created:** `frontend/src/types/storage.ts`
- **Change:** TypeScript types for storage API (UploadUrlResponse, DownloadUrlResponse, StorageCategory). Uses camelCase field names matching the API client's automatic snake_case → camelCase transform.
- **Reason:** Typed API contract for frontend storage operations

- **File created:** `frontend/src/hooks/useStorage.ts`
- **Change:** Two React Query mutation hooks: `useFileUpload()` (full upload flow: client-side size validation → get pre-signed URL → PUT to S3 → return s3Key) and `useDownloadUrl()` (resolve s3Key to download URL)
- **Reason:** Reusable hooks for all frontend components that upload or display S3 files

- **File created:** `frontend/src/components/ui/S3Image.tsx`
- **Change:** First component in `src/components/ui/`. Resolves an s3Key to a pre-signed download URL and displays via `next/image`. Shows Carbon `Loading` spinner during resolution, fallback on null/error.
- **Reason:** Common pattern of "I have an s3_key, show the image" needed a reusable component

- **File created:** `frontend/src/__tests__/storage.test.tsx`
- **Change:** 9 tests covering useFileUpload (3 tests: upload flow, size rejection, S3 failure), useDownloadUrl (1 test), S3Image (5 tests: null fallback, custom fallback, loading state, image render, error fallback)
- **Reason:** Frontend test coverage for storage hooks and component

- **File changed:** `frontend/CLAUDE.md`
- **Change:** Added S3Image to component locations listing; added "S3 File Upload Pattern" section documenting the pre-signed URL upload flow, hooks, types, and display component
- **Reason:** Future sessions know the S3 frontend integration pattern

- **File changed:** `.claude/rules/s3-storage.md`
- **Change:** Added "Implementation Lessons" section covering: S3Service dependency injection pattern, tenant validation on downloads, JSONB array update pattern, profile photo S3 key storage, frontend upload pattern, reel48_admin rejection on tenant endpoints
- **Reason:** Captures implementation details and edge cases from all 4 phases

### Notes
- No database migration was needed (no new tables — S3 storage uses existing columns)
- S3Service follows the established External Service Integration Pattern (CognitoService, StripeService, EmailService)
- S3Image is the first component in `src/components/ui/` (directory created in this phase)
- All 106 frontend tests pass (97 existing + 9 new)
- TypeScript compiles clean, ESLint passes (warnings only in test mock files, consistent with existing tests)

### Self-Audit Checklist
- [x] **New pattern?** Yes — S3 pre-signed URL upload pattern added to frontend CLAUDE.md
- [x] **Pattern violated?** No
- [x] **New decision?** No — frontend types use camelCase (matches existing API client transform convention)
- [x] **Missing guidance?** Yes — s3-storage rule had no implementation lessons section; added
- [x] **Reusable task?** No — S3 upload hook is reusable, documented in frontend CLAUDE.md
- [x] **Changelog updated?** Yes (this entry)

---

## 2026-04-10 — S3 Storage Service Phase 3: Profile Photo Management (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** S3 Storage Service — Phase 3

### Changes Made
- **File changed:** `backend/app/schemas/employee_profile.py`
- **Change:** Added `ProfilePhotoSet` schema for `POST /profiles/me/photo` request body
- **Reason:** New endpoint needs a schema for the `s3_key` field

- **File changed:** `backend/app/services/employee_profile_service.py`
- **Change:** Added `set_profile_photo()` and `remove_profile_photo()` methods with S3 key validation (company_id prefix + profiles category path)
- **Reason:** Profile photo management requires tenant-scoped S3 key validation, following the same pattern as `ProductService.add_product_image()`

- **File changed:** `backend/app/api/v1/employee_profiles.py`
- **Change:** Added `POST /profiles/me/photo` and `DELETE /profiles/me/photo` endpoints
- **Reason:** Employees need endpoints to manage their own profile photos

- **File changed:** `backend/tests/test_employee_profiles.py`
- **Change:** Added 12 tests across 3 test classes: `TestSetProfilePhoto` (6 tests), `TestRemoveProfilePhoto` (4 tests), `TestProfilePhotoAuthorization` (2 tests)
- **Reason:** Functional, isolation, and authorization tests for profile photo management

### Self-Audit Checklist
- [x] **New pattern?** No — follows existing S3 key validation pattern from product images
- [x] **Pattern violated?** No
- [x] **New decision?** No
- [x] **Missing guidance?** No
- [x] **Reusable task?** No
- [x] **Changelog updated?** Yes (this entry)

---

## 2026-04-09 — Module 9 Post-Module Harness Review (TRIGGER 2)

**Type:** Post-module harness review (Trigger 2)
**Module:** Module 9 — Employee Engagement (Complete)

### Post-Module Review (5 Steps)

**Step 1 — Pattern Consistency:**
- All Module 9 endpoints follow standard patterns: TenantContext from JWT, `_require_company_id` guard, standard ApiResponse wrapper, role checks before business logic.
- Notification endpoints use `is_admin` for create/deactivate, `is_corporate_admin_or_above` for company-scope notifications. Consistent with Module 6 authorization patterns.
- Wishlist endpoints are open to all authenticated roles (any employee can manage their own wishlist). Consistent with Module 2 (profile management).
- Both tables use TenantBase with standard dual RLS policies (PERMISSIVE company + RESTRICTIVE sub-brand).
- Frontend components follow Carbon-first approach with Tailwind for layout. No custom UI wrappers.

**Step 2 — Rule Effectiveness:**
- `carbon-design-system.md` activated correctly for all frontend component work. ProgressIndicator, Toggle, Pagination, Tag all used from Carbon.
- `testing.md` activated correctly. RLS isolation tests follow the established dual-session pattern with real UUIDs.
- `api-endpoints.md` enforced trailing slashes, pagination, standard response format.
- No rules were missing or insufficient for Module 9 work.

**Step 3 — ADR Currency:**
- All existing ADRs remain valid. No decisions were reversed during Module 9.
- No new architectural decisions required — Module 9 reused established patterns.

**Step 4 — Cross-Module Alignment:**
- Notification visibility logic (company/sub-brand/individual scopes) is unique to Module 9 but follows the same tenant isolation principles as all other modules.
- Wishlist's product validation (must be active to wishlist) aligns with Module 4's catalog validation pattern.
- `read_by` JSONB array for notification read tracking is a Module 9 innovation (avoids a join table). This pattern is self-contained and doesn't affect other modules.
- Onboarding wizard's `POST /profiles/me/onboarding-complete` follows the Module 2 upsert pattern.

**Step 5 — Gap Analysis:**
- No harness gaps encountered during Module 9. All patterns were covered by existing guidance.
- Module 9 is the final module in the build order, so no forward-looking gaps to fill.

### Harness Files Updated
- **`backend/CLAUDE.md`** — Added Module 9 table schemas (notifications, wishlists) and updated the "Which Base to Use" table.
- **`docs/harness-changelog.md`** — This entry.

### Test Coverage Added
- **`backend/tests/test_isolation.py`** — Added 6 RLS isolation tests: company isolation, sub-brand scoping, and reel48_admin bypass for both notifications and wishlists tables.
- **`frontend/src/__tests__/notifications.test.tsx`** — 9 tests covering feed rendering, unread count, empty states, type tags, mark-as-read + navigation, toggle filter.
- **`frontend/src/__tests__/wishlist.test.tsx`** — 11 tests covering item rendering, prices, SKUs, unavailable tags, notes, empty state, remove action, Browse Catalogs button.

### Harness Health Metrics
| Metric | Module 9 Value |
|--------|---------------|
| Mistakes per module | 0 (no harness violations) |
| Harness gaps per module | 0 |
| Rules added per module | 0 (existing rules sufficient) |
| First-attempt acceptance rate | ~95% |

---

## 2026-04-09 — Module 8 Phases 4-5: Analytics Dashboard UI (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 8 — Analytics Dashboard (Phases 4-5)

### Work Completed
- Created 18 new frontend files for the analytics dashboard UI:
  - `frontend/src/types/analytics.ts` — TypeScript interfaces for all analytics API responses
  - `frontend/src/hooks/useAnalytics.ts` — 8 React Query hooks for client analytics
  - `frontend/src/hooks/usePlatformAnalytics.ts` — 7 React Query hooks for platform analytics
  - 11 feature components in `frontend/src/components/features/analytics/`
  - Client analytics page at `frontend/src/app/(authenticated)/admin/analytics/page.tsx`
  - Platform analytics page at `frontend/src/app/(platform)/platform/analytics/page.tsx`
- Updated `frontend/src/components/layout/Sidebar.tsx` — added Analytics link to
  `subBrandAdminNav` and `platformAdminNav`
- Installed `@carbon/charts-react` and `d3` for chart rendering

### Harness Review
- **New pattern?** YES — Carbon DataTable `getHeaderProps`/`getRowProps` return objects
  with a `key` property. Spreading these onto JSX while also providing an explicit `key`
  causes a TS duplicate-key error. The fix is to destructure `key` out of the spread.
  → **Action:** Added pattern to `.claude/rules/carbon-design-system.md`.
- **Pattern violated?** No.
- **New decision?** `@carbon/charts-react` chosen for charting (official Carbon library).
  Loaded via `next/dynamic` with `ssr: false` to avoid D3 SSR issues. Uses `ScaleTypes`
  enum from `@carbon/charts/interfaces` for type-safe chart configuration.
- **Missing guidance?** No gaps — existing Carbon, Tailwind, and API client conventions
  covered all needs.
- **Prompt template needed?** No.

### Files Updated
- **`.claude/rules/carbon-design-system.md`** — Added DataTable key destructuring pattern.
- **`docs/harness-changelog.md`** — This entry.

---

## 2026-04-09 — Module 8 Phase 3: Platform Analytics API Endpoints (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 8 — Analytics Dashboard (Phase 3)

### Work Completed
- Created `backend/app/api/v1/platform/analytics.py` — 7 reel48_admin-only analytics endpoints
- Registered platform analytics router in `backend/app/api/v1/router.py`
- Added 35 tests to `backend/tests/test_analytics.py` (7 functional, 28 authorization) —
  all 550 tests passing

### Harness Review
- **New pattern?** No — followed the existing platform endpoint pattern (prefix `/platform/`,
  `require_reel48_admin` dependency). Reused existing AnalyticsService methods and response
  schemas from Phases 1-2.
- **Pattern violated?** No.
- **New decision?** No — the revenue/over-time endpoint reuses `SpendOverTimeResponse` rather
  than creating a separate schema, which is consistent with the data shape.
- **Missing guidance?** No gaps encountered.
- **Prompt template needed?** No.

### Files Updated
- **`backend/CLAUDE.md`** — Added `analytics.py` to the platform directory listing.

---

## 2026-04-09 — Module 8 Phase 2: Client Analytics API Endpoints (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 8 — Analytics Dashboard (Phase 2)

### Work Completed
- Created `backend/app/api/v1/analytics.py` — 8 tenant-scoped analytics endpoints
- Registered analytics router in `backend/app/api/v1/router.py`
- Added 30+ API-level tests to `backend/tests/test_analytics.py` (functional, authorization,
  isolation) — all 515 tests passing (442 existing + 73 analytics)

### Harness Review
- **New pattern?** No — followed existing patterns from `invoices.py` router (guard functions,
  `_require_company_id`, role-specific access checks).
- **Pattern violated?** No.
- **New decision?** No.
- **Missing guidance?** No gaps encountered.
- **Prompt template needed?** No.

### Notes
- API-level isolation tests cannot assert exact tenant-scoped values because the `client`
  fixture uses `admin_db_session` (superuser, bypasses RLS). True isolation is verified at
  the service level (Phase 1 tests). This is consistent with the existing test architecture
  documented in `.claude/rules/testing.md`.

---

## 2026-04-09 — Module 8 Phase 1: AnalyticsService Core Aggregation Queries (TRIGGER 1)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 8 — Analytics Dashboard (Phase 1)

### Work Completed
- Created `backend/app/services/analytics_service.py` — 10 aggregation methods querying
  existing Module 1–7 tables (no new migrations needed)
- Created `backend/app/schemas/analytics.py` — 12 Pydantic response schemas
- Created `backend/tests/test_analytics.py` — 21 tests (15 functional, 4 isolation, 2 platform)
- All 463 tests passing (442 existing + 21 new, zero regressions)

### Harness Updates
- **File changed:** `.claude/rules/testing.md`
- **Change:** Added "CRITICAL: RLS Isolation Tests Must Use Real UUIDs (Not Empty Strings)"
  section. Updated `_set_tenant_context` example to require both real UUID values.
- **Reason:** PostgreSQL does NOT guarantee short-circuit evaluation of OR expressions in
  RLS policies. `SET LOCAL app.current_sub_brand_id = ''` causes `::uuid` cast to fail at
  the database level even when the empty-string check (`= ''`) appears earlier in the OR
  chain. This caused 4 isolation test failures.
- **Impact:** Future isolation tests avoid the empty-string UUID cast trap by always using
  real UUID values from the test tenant fixtures.

### New Patterns Introduced
- **Python-side aggregation of individual + bulk orders:** Analytics methods merge data from
  `orders`/`order_line_items` and `bulk_orders`/`bulk_order_items` in Python (dict merging)
  rather than SQL UNION, because the table schemas differ.
- **`_apply_date_range` helper:** Reusable date filtering across all analytics methods.
- **Committed data pattern for isolation tests:** Seed data via `admin_factory()` with
  explicit commit, query via `app_factory()` (RLS-enforced), cleanup in `finally` block.

### Self-Audit Checklist
- [x] New pattern? → Python-side aggregation documented above
- [x] Pattern violated? → RLS empty-string UUID cast issue documented in testing.md
- [x] New decision? → No new ADR needed (analytics queries are straightforward)
- [x] Missing guidance? → Added RLS UUID guidance to testing.md
- [x] Reusable task? → No new prompt template needed
- [x] Changelog updated? → This entry

---

## 2026-04-09 — Module 7 Post-Module Harness Review (TRIGGER 2)

**Type:** Post-module harness review (Trigger 2)
**Module:** Module 7 — Invoicing & Client Billing (Complete)

### Pattern Consistency Scan
All Module 7 code reviewed for consistency with established patterns:
- **Endpoints:** All follow route → service → model pattern. Platform endpoints
  (`/platform/invoices`) use `require_reel48_admin`. Client endpoints (`/invoices`)
  use `get_tenant_context`. Webhook endpoint (`/webhooks/stripe`) is unauthenticated
  with Stripe signature verification. ✅
- **Response formats:** All use `ApiResponse[T]` / `ApiListResponse[T]`. ✅
- **URL conventions:** snake_case, plural nouns, versioned under `/api/v1/`. ✅
- **RLS policies:** `invoices` table has both `invoices_company_isolation` (PERMISSIVE)
  and `invoices_sub_brand_scoping` (RESTRICTIVE) in the same migration. ✅
- **Migration:** Reversible (`upgrade` + `downgrade`), includes CHECK constraints,
  composite indexes, and RLS in same migration. ✅
- **Service layer:** `InvoiceService` follows the same pattern as all other services
  (db + optional external service in constructor). ✅
- **StripeService:** Follows External Service Integration Pattern (lazy import,
  dependency injection, AppException mapping). ✅
- **No inconsistencies found.**

### Rule Effectiveness Review
| Rule File | Activated? | Effective? | Notes |
|-----------|-----------|------------|-------|
| `stripe-invoicing.md` | ✅ | ✅ | Provided sufficient guidance for all three billing flows, Stripe integration, and webhook handling. Missing: webhook RLS bypass, status priority for idempotent webhooks, self-service auto_advance distinction — now added. |
| `api-endpoints.md` | ✅ | ✅ | Platform endpoint exception (accepting target company_id) worked correctly for invoice creation. |
| `database-migrations.md` | ✅ | ✅ | Migration followed template exactly. Single-migration pattern appropriate for one table. |
| `testing.md` | ✅ | ✅ | MockStripeService follows External Service Mock Pattern. Webhook testing guidance was a gap — filled in Phase 6. |
| `authentication.md` | ✅ | ✅ | Role-Based Access Matrix correctly reflects implementation: employees cannot view invoices, sub_brand_admin/regional_manager can view their brand's invoices. |

### ADR Currency Check
- **ADR-006 (Stripe for Invoicing):** Updated Risks section with three implementation
  findings: (1) self-service non-blocking pattern, (2) idempotent webhook processing
  via `_STATUS_ORDER`, (3) webhook RLS bypass pattern. Core decision remains sound.

### Harness Files Updated
1. **`backend/CLAUDE.md`** — Added Module 7 invoices table schema documentation and
   Invoice Status Lifecycle section (status transitions, API-driven vs webhook-driven,
   `_STATUS_ORDER` priority mechanism, self-service auto-generation pattern, revenue
   categorization for Module 8 Analytics).
2. **`.claude/rules/stripe-invoicing.md`** — Added "Implementation Lessons (Module 7)"
   section with five documented patterns: webhook RLS bypass, idempotent webhook
   processing, self-service non-blocking/auto_advance, synchronous webhook verification,
   API version pinning. Added 3 new entries to Common Mistakes.
3. **`docs/adr/006-stripe-for-invoicing.md`** — Updated Risks section with
   implementation notes on non-blocking self-service, idempotent webhook processing,
   and webhook RLS bypass.
4. **`docs/harness-changelog.md`** — This entry.

### Gap Analysis
Scenarios the harness didn't fully cover before Module 7:
1. **Webhook RLS bypass** — How unauthenticated endpoints query tenant-scoped tables.
   Gap filled: documented in backend CLAUDE.md (Unauthenticated Endpoint Exceptions)
   during Phase 4, and in stripe-invoicing.md during this review.
2. **Invoice status priority/idempotency** — The `_STATUS_ORDER` mechanism for
   preventing status regression on out-of-order webhooks. Gap filled: documented in
   backend CLAUDE.md (Invoice Status Lifecycle) and stripe-invoicing.md.
3. **Self-service vs admin auto_advance difference** — Self-service uses
   `auto_advance=True`; admin invoices use `False`. Gap filled: documented in
   stripe-invoicing.md and backend CLAUDE.md.
4. **Revenue categorization** — Which invoice statuses count as revenue for analytics.
   Gap filled: documented in backend CLAUDE.md (Invoice Status Lifecycle) for Module 8.

### Cross-Module Alignment
- Module 7 invoice creation follows the same service pattern as Modules 4-6.
- `StripeService` follows the same External Service Integration Pattern as
  `CognitoService` (Module 1) and `EmailService` (Module 6).
- `MockStripeService` follows the same test mock pattern as `MockCognitoService`
  and `MockEmailService`.
- Self-service invoice auto-generation follows the same non-blocking pattern as
  approval email notifications (Module 6).
- No cross-module inconsistencies found.

### Metrics
| Metric | Module 7 Value | Trend |
|--------|---------------|-------|
| Mistakes per module | 0 | Stable (same as Modules 5-6) |
| Harness gaps found | 4 (all filled) | Stable |
| Rules added/updated | 3 files updated, 0 new rules | Decreasing (harness maturing) |
| First-attempt acceptance rate | ~95% | Stable |

---

## 2026-04-09 — Module 7 Phase 6 (Comprehensive Invoice Tests)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 7 — Invoicing & Client Billing (Phase 6)

### What was built
- `backend/tests/conftest.py` — Added `MockStripeService` class and autouse `mock_stripe`
  fixture following the External Service Mock Pattern. Records created invoices, customers,
  invoice items, finalized/sent/voided invoices. Provides `construct_webhook_event()` that
  can be overridden per-test for signature failure testing.
- `backend/tests/test_invoices.py` — 30 tests across 6 test classes:
  - `TestAssignedInvoice` (7 tests): create from orders/bulk orders, validation guard, finalize, send, void
  - `TestPostWindowInvoice` (3 tests): create after window closes, guard before close, payment model guard
  - `TestClientInvoiceViewing` (3 tests): list, detail, PDF URL
  - `TestStripeWebhooks` (6 tests): paid, payment_failed, finalized, invalid/missing signature, idempotent processing
  - `TestInvoiceAuthorization` (6 tests): reel48_admin-only create/finalize, employee denied, role-based viewing
  - `TestInvoiceIsolation` (4 tests): cross-company, cross-sub-brand, corporate admin visibility, platform admin
- `backend/tests/test_isolation.py` — Added 3 RLS-level isolation tests for invoices:
  company isolation, sub-brand scoping, reel48_admin bypass.

### Harness files updated
- **`.claude/rules/testing.md`** — Updated External Service Mock Pattern to list all
  three implemented mocks (Cognito, Stripe, Email). Added new "Webhook Endpoint Testing"
  section documenting signature verification tests, idempotent processing tests, status
  non-regression tests, and webhook test data setup patterns.

### Metrics
- Tests added: 33 (30 in test_invoices.py + 3 RLS in test_isolation.py)
- Total test count: 442 (409 existing + 33 new)
- Harness gaps found: 1 (no webhook testing guidance — now filled)
- Patterns violated: 0

### Notes
- 3 self-service flow tests from the original spec were omitted because self-service
  invoice auto-generation is triggered during order placement (OrderService.create_order),
  not via the invoice API endpoints. Testing these requires placing orders against
  self-service catalogs, which is a Module 4 + Module 7 integration test.
- `ValidationError` in the app maps to HTTP 422 (not 400). Tests were adjusted accordingly.

---

## 2026-04-09 — Module 7 Phase 5 (Client-Facing Endpoints & Self-Service Integration)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 7 — Invoicing & Client Billing (Phase 5)

### What was built
- `backend/app/api/v1/invoices.py` — Tenant-scoped client-facing invoice endpoints:
  `GET /invoices/`, `GET /invoices/{id}`, `GET /invoices/{id}/pdf`. Employee role is
  blocked (403). Corporate admins see all sub-brands; sub_brand_admin and
  regional_manager see their sub-brand only. PDF endpoint caches Stripe PDF URL locally.
- `backend/app/api/v1/router.py` — Registered client invoice router.
- `backend/app/services/order_service.py` — Added optional `stripe_service` parameter
  to `OrderService.__init__()`. After order creation, if catalog has
  `payment_model='self_service'`, auto-generates a Stripe invoice via
  `InvoiceService.create_self_service_invoice()`. Non-blocking (try/except with warning).
- `backend/app/api/v1/orders.py` — Injects `StripeService` dependency and passes to
  `OrderService` on the create_order endpoint.

### Harness review
1. **New pattern?** Yes — non-blocking external service integration in OrderService.
   This follows the same pattern as email notifications in ApprovalService (try/except
   with warning log). Already documented in backend CLAUDE.md under
   "Email Notification Pattern (Non-Blocking SES)". The self-service invoice integration
   follows the identical pattern, so no new documentation needed beyond this changelog.
2. **New pattern?** Yes — client-facing invoice endpoints introduce an employee-exclusion
   guard (`_require_invoice_access`). This is a role-check at the route level, distinct
   from the `_require_company_id` guard. The pattern aligns with the Role-Based Access
   Matrix in `.claude/rules/authentication.md` which specifies employees cannot view invoices.
3. **Pattern violated?** No.
4. **New decision?** No.
5. **Missing guidance?** No — all patterns are covered by existing harness documentation.
6. **Prompt template needed?** No.

### Files changed
- **`backend/app/api/v1/invoices.py`** — New file (client-facing invoice endpoints)
- **`backend/app/api/v1/router.py`** — Added invoices_router import and registration
- **`backend/app/services/order_service.py`** — Added stripe_service param and self-service integration
- **`backend/app/api/v1/orders.py`** — Added stripe_service injection for create_order
- **`docs/harness-changelog.md`** — This entry

---

## 2026-04-09 — Module 7 Phase 4 (Stripe Webhook Handler)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 7 — Invoicing & Client Billing (Phase 4)

### What was built
- `backend/app/api/v1/webhooks.py` — Stripe webhook endpoint (`POST /api/v1/webhooks/stripe`).
  Unauthenticated — security via Stripe signature verification. Sets RLS session variables
  to empty string for platform-level cross-company invoice lookup. Dispatches to
  `InvoiceService.handle_webhook_event()` for idempotent status updates.
- `backend/app/api/v1/router.py` — Registered webhook router.

### Harness review
1. **New pattern?** Yes — webhook RLS bypass pattern. The webhook endpoint sets
   `app.current_company_id = ''` and `app.current_sub_brand_id = ''` directly
   (without JWT/TenantContext) to enable cross-company invoice lookup. This is the
   same bypass mechanism as `reel48_admin`, but triggered by signature verification
   instead of JWT role. Documented in backend CLAUDE.md under Unauthenticated Endpoint
   Exceptions.
2. **Pattern violated?** No.
3. **New decision?** No — follows the stripe-invoicing rule for webhook handling.
4. **Missing guidance?** The webhook entry in Unauthenticated Endpoint Exceptions was
   missing the RLS bypass detail. Updated to include it.
5. **Prompt template needed?** No.

### Files changed
- **`backend/app/api/v1/webhooks.py`** — New file (webhook endpoint)
- **`backend/app/api/v1/router.py`** — Added webhook router registration
- **`backend/CLAUDE.md`** — Updated webhook entry in Unauthenticated Endpoint Exceptions
  with RLS bypass pattern
- **`docs/harness-changelog.md`** — This entry

---

## 2026-04-09 — Module 7 Phase 3 (Platform Admin Invoice Endpoints)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 7 — Invoicing & Client Billing (Phase 3)

### What was built
- `backend/app/api/v1/platform/invoices.py` — Six platform admin endpoints for invoice
  lifecycle management: create (assigned/post_window), finalize, send, void, list (with
  filters), and get detail. All use `require_reel48_admin` auth dependency.
- `backend/app/schemas/invoice.py` — Updated `InvoiceCreate` schema: changed single
  `order_id`/`bulk_order_id` to list fields (`order_ids`/`bulk_order_ids`), restricted
  `billing_flow` validator to `assigned`/`post_window` only (self_service is auto-generated,
  not manually created), removed `buying_window_closes_at` (derived from catalog).
- `backend/app/api/v1/router.py` — Registered platform invoices router.

### Harness review
1. **New pattern?** No — follows the established platform endpoint pattern from
   `platform/products.py` and `platform/catalogs.py` exactly (require_reel48_admin,
   resolve_current_user_id, StripeService injection via Depends).
2. **Pattern violated?** No.
3. **New decision?** No — all decisions follow existing stripe-invoicing rule guidance.
4. **Missing guidance?** The root CLAUDE.md endpoint list was missing `/send`, `/void`,
   and `GET /{invoice_id}` for platform invoices. Updated to include the full set of 6
   platform invoice endpoints.
5. **Prompt template needed?** No.

### Files changed
- **`backend/app/api/v1/platform/invoices.py`** — New file (6 endpoints)
- **`backend/app/schemas/invoice.py`** — Updated InvoiceCreate schema
- **`backend/app/api/v1/router.py`** — Added platform invoices router registration
- **`CLAUDE.md`** — Updated API Endpoints for Invoicing section with full platform endpoint list
- **`docs/harness-changelog.md`** — This entry

---

## 2026-04-09 — Module 7 Phase 2 (Stripe & Invoice Services)

**Type:** End-of-session self-audit (Trigger 1)
**Module:** Module 7 — Invoicing & Client Billing (Phase 2)

### What was built
- `backend/app/services/stripe_service.py` — Thin Stripe SDK wrapper following the
  External Service Integration Pattern (dependency-injectable, testable via mocking).
  Methods: get_or_create_customer, create_invoice, create_invoice_item, finalize_invoice,
  send_invoice, void_invoice, get_invoice, construct_webhook_event.
- `backend/app/services/invoice_service.py` — Core business logic for the three billing
  flows (assigned, self-service, post-window), invoice lifecycle actions (finalize, send,
  void), idempotent webhook handlers, and tenant-scoped + platform-admin queries.
- `backend/app/core/config.py` — Added STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
  STRIPE_API_VERSION settings.

### Harness review
1. **New pattern?** Yes — StripeService introduces `StripeError(AppException)` for mapping
   Stripe SDK errors to the standard AppException hierarchy (HTTP 502). Added to
   backend CLAUDE.md under Stripe Service Integration section.
2. **Pattern violated?** No — follows established CognitoService/EmailService patterns.
3. **New decision?** Webhook idempotency uses status ordering (`_STATUS_ORDER` dict) to
   prevent status regression when events arrive out of order. Not ADR-worthy — standard
   webhook handling pattern.
4. **Missing guidance?** No — stripe-invoicing.md rule covered all scenarios.
5. **Prompt template needed?** No — this is module-specific, not a recurring pattern.

### Files changed
- **`backend/app/core/config.py`** — Added Stripe settings
- **`backend/app/services/stripe_service.py`** — New file (StripeService + StripeError)
- **`backend/app/services/invoice_service.py`** — New file (InvoiceService)
- **`backend/CLAUDE.md`** — Added Stripe Service Integration section
- **`docs/harness-changelog.md`** — This entry

---

## 2026-04-09 — Module 6 Completion (Approval Workflows — Post-Module Harness Review)

**Type:** Post-module harness review (MANDATORY — Trigger 2)
**Module:** Module 6 — Approval Workflows (Phases 1-5 complete)

### Pattern Consistency Scan
All Module 6 code reviewed for consistency with established patterns:
- **Endpoints:** All 6 tenant endpoints + 6 platform endpoints follow the standard
  route → service → model pattern. `_require_company_id` guard used consistently.
  Response format uses `ApiResponse[T]` / `ApiListResponse[T]`. Pagination on all
  list endpoints.
- **Models:** `ApprovalRequest` uses `TenantBase`, `ApprovalRule` uses `CompanyBase` —
  correct for their scoping needs. Both documented in backend CLAUDE.md Model Base Classes.
- **RLS:** Both tables have correct policies in migration 006. `approval_requests` has
  company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE). `approval_rules`
  has company isolation only (no sub-brand column).
- **Service layer:** `ApprovalService` follows the dependency-injected constructor pattern.
  Email service is optional parameter (backward compatible). Flush+refresh pattern used
  consistently.
- **Tests:** 93 new tests across 3 files (test_approvals.py, test_approval_endpoints.py,
  test_approval_notifications.py). Isolation tests included for cross-company and cross-
  sub-brand boundaries.

### Rule Effectiveness Review
- `database-migrations.md`: Activated correctly — RLS policies created in same migration.
- `api-endpoints.md`: Activated — tenant context from JWT enforced on all protected endpoints.
- `authentication.md`: Needed update — approval-specific permissions not in access matrix.
  **Fixed in this review.**
- `testing.md`: Effective — isolation tests, mock patterns, and fixture patterns all followed.

### ADR Currency Check
- All existing ADRs (001-007) remain valid. No conflicts or reversals.
- No new ADR needed: polymorphic entity reference (`entity_type` + `entity_id`) is a standard
  pattern, not a project-specific architectural decision.

### Cross-Module Alignment
- Module 6 integrates cleanly with Modules 3-5: submit endpoints in products, catalogs,
  orders, and bulk_orders now call `ApprovalService.record_submission()`. Platform
  approve/reject endpoints sync approval_requests via `find_by_entity()`.
- Consistent patterns: email notifications follow the same External Service Integration
  Pattern as CognitoService (Module 1). Non-blocking dispatch matches the pattern
  documented in backend CLAUDE.md.

### Gap Analysis
- No gaps discovered. All Module 6 scenarios were covered by existing harness guidance
  or documented in per-phase updates.

### Harness Files Updated (This Review)
- **`.claude/rules/authentication.md`** — Added 4 approval-related rows to the Role-Based
  Access Matrix: View approval queue, Approve/reject (products/catalogs), Approve/reject
  (orders/bulk), Manage approval rules.
- **`docs/harness-changelog.md`** — This completion entry.

### Harness Health Metrics (Module 6 Overall)
| Metric | Value | Notes |
|--------|-------|-------|
| Mistakes per module | 0 | All patterns followed correctly |
| Harness gaps per module | 0 | Existing guidance sufficient |
| Rules added per module | 1 | Authentication access matrix update |
| New patterns documented | 4 | Polymorphic entity ref, unified approval queue, configurable rules, non-blocking SES notifications |
| First-attempt acceptance rate | ~95% | Minor iteration on email template testing |

### Test Results
- Total tests: 409 (316 original + 93 Module 6)
- All passing (0 failures, 0 errors)

### Module 6 Key Patterns Summary (for Modules 7-8 Reference)
1. **Polymorphic entity reference:** `entity_type` (VARCHAR) + `entity_id` (UUID) columns
   on `approval_requests`. No DB-level FK — application layer resolves the entity.
2. **Unified approval queue:** Single `approval_requests` table tracks all approvals.
   `ApprovalService` delegates to entity-specific services for state transitions.
3. **Configurable approval rules:** `approval_rules` table with `amount_threshold` rule
   type. Products/catalogs always require reel48_admin (hardcoded). Orders/bulk_orders
   check configurable rules.
4. **Non-blocking SES notifications:** `EmailService` injected optionally. Failures
   logged but never block business logic.
5. **Approval sync pattern:** Direct entity approve/reject endpoints (e.g.,
   `POST /platform/products/{id}/approve`) sync the `approval_requests` audit trail
   via `ApprovalService.find_by_entity()`.

---

## 2026-04-09 — Module 6 Phase 5 (Approval Notifications via SES)

**Type:** End-of-session self-audit
**Module:** Module 6 — Approval Workflows (Phase 5: Email Notifications)

### Harness files updated
- **`backend/CLAUDE.md`** — Added "Email Notification Pattern (Non-Blocking SES)" section
  documenting the EmailService integration, non-blocking dispatch pattern, recipient
  resolution logic, config settings, and MockEmailService testing pattern.

### Changes made this session
- **New file:** `backend/app/services/email_service.py` — SES integration following the
  External Service Integration Pattern (CognitoService precedent). Includes HTML/text
  email templates for approval_needed and approval_decision notifications.
- **Updated:** `backend/app/core/config.py` — Added `SES_REGION`, `SES_SENDER_EMAIL`,
  and `FRONTEND_BASE_URL` settings.
- **Updated:** `backend/app/services/approval_service.py` — Added optional `email_service`
  parameter, `_notify_approvers()`, `_notify_submitter()`, and `_get_approver_emails()`
  methods. Notifications dispatched from `record_submission()` and `process_decision()`.
- **Updated:** 8 endpoint files to inject `EmailService` via `Depends(get_email_service)`
  where approval submissions or decisions occur.
- **Updated:** `backend/tests/conftest.py` — Added `MockEmailService` class and autouse
  `mock_email` fixture following the established external service mock pattern.
- **New file:** `backend/tests/test_approval_notifications.py` — 11 tests covering
  submission notifications, decision notifications, email failure resilience, and
  full integration flows.

### Self-audit checklist
- [x] **New pattern?** Yes — non-blocking email dispatch within service methods. Documented
  in backend CLAUDE.md.
- [x] **Pattern violated?** No — followed the existing External Service Integration Pattern.
- [x] **New decision?** No — SES was already the chosen email provider (root CLAUDE.md).
- [x] **Missing guidance?** Filled — added MockEmailService testing guidance.
- [x] **Reusable task?** Not yet — email templates are inline. A template system may be
  needed if email complexity grows.
- [x] **Changelog updated?** This entry.

### Test results
- 409 total tests: all passing (0 failures, 0 errors)
- 11 new notification tests added


## 2026-04-09 — Module 6 Phase 4 (Platform Admin Approval Dashboard)

**Type:** End-of-session self-audit
**Module:** Module 6 — Approval Workflows (Phase 4: Platform Endpoints)

### Self-Audit Checklist
- [x] **New pattern?** → Platform approval endpoints follow the established platform
  endpoint pattern (`require_reel48_admin`, cross-company queries with optional
  `company_id` filter). The summary endpoint introduces a new aggregation pattern
  (GROUP BY with JOIN to companies for display names). No new harness rule needed —
  follows existing patterns documented in backend CLAUDE.md.
- [ ] **Pattern violated?** → No violations. All endpoints use `require_reel48_admin`,
  standard response format, and pagination.
- [ ] **New decision?** → No ADR-worthy decisions.
- [ ] **Missing guidance?** → No gaps discovered. Platform approval endpoints follow
  the same patterns as `platform/products.py`, `platform/bulk_orders.py`.
- [ ] **Reusable task?** → No new prompt template needed.
- [x] **Changelog updated?** → This entry.

### Files Changed
- **`backend/app/api/v1/platform/approvals.py`** — New file: platform approval list,
  summary, detail, approve/reject endpoints (reel48_admin only).
- **`backend/app/api/v1/platform/approval_rules.py`** — New file: platform approval
  rules list endpoint (reel48_admin only, cross-company with filters).
- **`backend/app/services/approval_service.py`** — Added `list_all_approvals()`,
  `get_approval_summary()`, and `list_all_rules()` methods.
- **`backend/app/schemas/approval.py`** — Added `ApprovalSummaryResponse` and
  `CompanyPendingCount` schemas.
- **`backend/app/api/v1/router.py`** — Registered platform approval routers.
- **`backend/tests/test_platform_approvals.py`** — New file: 21 tests covering
  cross-company visibility, filters, summary stats, approve/reject, and 403 auth.

### Harness Health Metrics
- **Mistakes:** 0 (all patterns followed correctly on first attempt)
- **Gaps:** 0
- **Rules added:** 0 (existing patterns were sufficient)
- **First-attempt acceptance rate:** 100% (21/21 tests passed on first run)

---

## 2026-04-09 — Module 6 Phase 3 (Approval Queue & Decision Endpoints)

**Type:** End-of-session self-audit
**Module:** Module 6 — Approval Workflows (Phase 3: Endpoints & Integration)

### Self-Audit Checklist
- [x] **New pattern?** → Approval sync pattern: direct platform approve/reject endpoints
  (e.g., `POST /platform/products/{id}/approve`) now sync the corresponding
  `approval_requests` record via `ApprovalService.find_by_entity()`. This keeps the
  unified approval queue consistent even when approvals happen through entity-specific
  endpoints. Documented inline — no separate harness update needed as it follows the
  existing delegation pattern.
- [x] **New pattern?** → Submit endpoints now call `ApprovalService.record_submission()`
  to create audit trail records. Products, catalogs, bulk orders (on submit) and orders
  (on create) all record approval requests automatically.
- [ ] **Pattern violated?** → No violations. All endpoints follow the standard guard
  pattern (`_require_company_id`), response format (`ApiResponse[T]`), and role checks.
- [ ] **New decision?** → No ADR-worthy decisions.
- [ ] **Missing guidance?** → No gaps discovered. The approval queue endpoints follow
  the same patterns as existing list/detail endpoints.
- [ ] **Reusable task?** → No new prompt template needed.
- [x] **Changelog updated?** → This entry.

### Files Changed
- **`backend/app/api/v1/approvals.py`** — New file: approval queue endpoints (pending,
  history, detail, approve, reject).
- **`backend/app/api/v1/approval_rules.py`** — New file: approval rules CRUD endpoints
  (create, list, update, deactivate).
- **`backend/app/api/v1/router.py`** — Added approval and approval_rules routers.
- **`backend/app/api/v1/products.py`** — Submit now records approval_request.
- **`backend/app/api/v1/catalogs.py`** — Submit now records approval_request.
- **`backend/app/api/v1/orders.py`** — Create now records approval_request; approve syncs.
- **`backend/app/api/v1/bulk_orders.py`** — Submit now records approval_request; approve syncs.
- **`backend/app/api/v1/platform/products.py`** — Approve/reject now sync approval_requests.
- **`backend/app/api/v1/platform/catalogs.py`** — Approve/reject now sync approval_requests.
- **`backend/app/services/approval_service.py`** — Added `find_by_entity()` method and
  `status_filter` parameter to `list_history()`.
- **`backend/tests/test_approval_endpoints.py`** — New file: 29 tests covering pending
  queue, history, decisions, integration, rules endpoints, rules enforcement, and isolation.
- **`docs/harness-changelog.md`** — This entry.

### Metrics
- Existing tests: 348 → still passing (0 regressions)
- New tests: 29 (all passing)
- Total: 377 tests passing

---

## 2026-04-09 — Module 6 Phase 2 (Approval Service & Schemas)

**Type:** End-of-session self-audit
**Module:** Module 6 — Approval Workflows (Phase 2: Service Layer)

### Self-Audit Checklist
- [x] **New pattern?** → Unified orchestrator service pattern: `ApprovalService` wraps
  existing entity-specific approve/reject methods with audit trail recording and
  configurable approval rules evaluation. Delegates to `ProductService`, `CatalogService`,
  `OrderService`, `BulkOrderService` rather than duplicating transition logic. Documented
  in `backend/CLAUDE.md` Approval Workflow Patterns section.
- [x] **New pattern?** → Service-level test pattern: Phase 2 tests call service methods
  directly rather than going through HTTP endpoints. FK constraints require real referenced
  records (stub catalogs, real users). Documented in backend CLAUDE.md.
- [ ] **Pattern violated?** → No violations. Schemas follow Pydantic v2 conventions
  (ConfigDict, from_attributes). Service follows the db-injected constructor pattern.
- [ ] **New decision?** → No ADR-worthy decisions. Role hierarchy ranking is a
  straightforward implementation of the documented role model.
- [ ] **Missing guidance?** → No gaps discovered. The entity service methods were
  well-documented from Modules 3-5.
- [ ] **Reusable task?** → No new prompt template needed.
- [x] **Changelog updated?** → This entry.

### Files Changed
- **`backend/app/schemas/approval.py`** — New file: Pydantic request/response schemas
  for approval requests, queue items, and approval rules.
- **`backend/app/services/approval_service.py`** — New file: Unified ApprovalService
  with record_submission, process_decision, check_approval_rules, queue queries,
  and rule CRUD.
- **`backend/tests/test_approvals.py`** — New file: 32 tests covering functional,
  rules enforcement, queue queries, entity summaries, and isolation.
- **`backend/CLAUDE.md`** — Added Approval Workflow Patterns section.
- **`docs/harness-changelog.md`** — This entry.

### Metrics
- Existing tests: 316 → still passing (0 regressions)
- New tests: 32 (all passing)
- Total: 348

---

## 2026-04-09 — Module 6 Phase 1 (Approval Tables)

**Type:** End-of-session self-audit
**Module:** Module 6 — Approval Workflows (Phase 1: Database Migration)

### Self-Audit Checklist
- [x] **New pattern?** → Polymorphic entity reference pattern: `approval_requests` uses
  `entity_type` + `entity_id` columns instead of direct FK to allow referencing products,
  catalogs, orders, and bulk orders from a single table. No DB-level FK constraint on
  `entity_id`. Documented in `backend/CLAUDE.md` Module 6 Table Schemas.
- [ ] **Pattern violated?** → No violations. Migration follows the same pattern as 004/005.
  TenantBase model for approval_requests, CompanyBase model for approval_rules. Standard
  RLS policies applied.
- [ ] **New decision?** → No ADR-worthy decisions. Polymorphic entity reference is a standard
  pattern; approval_rules as CompanyBase (company-wide, not per-sub-brand) follows the same
  reasoning as org_codes.
- [ ] **Missing guidance?** → No gaps discovered. The migration, model, and test
  infrastructure patterns are well-established from Modules 1-5.
- [ ] **Reusable task?** → No new prompt template needed.
- [x] **Changelog updated?** → This entry.

### Files Changed
- **`backend/CLAUDE.md`** — Added Module 6 Table Schemas section (approval_requests,
  approval_rules) and updated Model Base Classes table with new models.
- **`docs/harness-changelog.md`** — This entry.

---

## 2026-04-09 — Module 5 Completion (Bulk Ordering System)

**Type:** End-of-module self-audit + harness review
**Module:** Module 5 — Bulk Ordering System (Phases 1-6)

### Self-Audit Checklist
- [x] **New pattern?** → Draft workflow (create → add items → submit), automatic total
  recalculation on item changes, item-level employee assignment, submit guard (must have
  items), post-submit item locking, hard-delete for draft bulk orders. All documented in
  new "Bulk Order Status Lifecycle & Transitions" and "Bulk Order Patterns" sections of
  `backend/CLAUDE.md`.
- [ ] **Pattern violated?** → No violations. All 14 tenant endpoints + 2 platform endpoints
  follow the established route → service → model pattern, same RLS policies, same response
  format, same role checks as Modules 1-4.
- [ ] **New decision?** → No ADR-worthy decisions. All choices (hard delete for drafts,
  company-only employee validation, duplicated catalog validation, total_items = SUM of
  quantities) are consistent with established patterns or documented in the new Bulk Order
  Patterns section.
- [ ] **Missing guidance?** → No gaps. Bulk order lifecycle and patterns were undocumented
  before this review — now filled. No shared catalog validation helper was created; the
  duplication between OrderService and BulkOrderService is acceptable per the "keep services
  self-contained" principle.
- [ ] **Reusable task?** → Considered `prompts/draft-workflow.md` but the draft → submit →
  approve pattern is too domain-specific to bulk ordering. If Module 8 (Employee Engagement)
  introduces similar workflows, this decision can be revisited.
- [x] **Changelog updated?** → This entry.

### Harness Files Updated
- **`backend/CLAUDE.md`** — Added "Bulk Order Status Lifecycle & Transitions" section
  (status flow, authorization matrix, endpoint pattern, differences from individual orders).
  Added "Bulk Order Patterns" section (draft workflow, total recalculation, employee
  assignment, order number format, price snapshotting, hard delete, item locking, catalog
  validation, endpoint inventory).

### Post-Module Pattern Consistency Review
- All 14 bulk order endpoints + 2 platform endpoints follow the established
  route → service → model pattern
- RLS policies follow the standard two-policy pattern (company isolation PERMISSIVE +
  sub-brand scoping RESTRICTIVE)
- All endpoints use TenantContext from JWT with defense-in-depth company_id filtering
- Status transitions use POST /{action} pattern (consistent with Module 4 orders)
- Tests cover functional, authorization, isolation, and state transition categories

### Session Metrics
- Tests before module: 265
- Tests after module: 316
- New tests added: 51
- Harness gaps found: 0 (table schemas documented during Phase 1; lifecycle/patterns
  documented during this Phase 6 review)

### Post-Module Harness Review Addendum (Deep Review)

**Performed:** 2026-04-09 (dedicated review session after module completion)

#### Cross-Module Alignment Verified
All Module 5 patterns are consistent with Modules 1-4:
- TenantBase inheritance, RLS (PERMISSIVE + RESTRICTIVE), `_require_company_id` guard,
  `resolve_current_user_id`, `flush()`+`refresh()`, `ApiResponse`/`ApiListResponse`,
  status transitions via `POST /{action}`, platform endpoints via `require_reel48_admin`,
  price snapshotting, catalog validation, order number generation with collision retry.
- No inconsistencies found. No improvements requiring backport.

#### ADR Currency Check
All 8 ADRs (001-008) verified as current. ADR-006 (Stripe) will be exercised
when bulk orders enter the "assigned" billing flow in Module 7.

#### Rule File Effectiveness
All 8 rule files assessed. `database-migrations.md`, `api-endpoints.md`,
`authentication.md`, `testing.md`, and `harness-maintenance.md` actively guided
Module 5 development. No rule modifications needed.

#### Test Gap Noted
No explicit cross-sub-brand isolation test for bulk orders (Brand A2 can't see
Brand A1's bulk orders). The same RLS policy pattern is validated in Modules 1-4,
so this is low risk. Consider adding in a future session if time permits.

#### Forward-Looking: Module 7 (Invoicing) Preparation
The `invoices` table schema in `stripe-invoicing.md` references `bulk_order_id` FK,
but no guidance exists for which bulk order statuses are eligible for invoice creation.
Recommend adding this guidance during Module 7 Phase 1.

#### Harness Health Metrics (Module 5)
| Metric | Value | Trend |
|--------|-------|-------|
| Mistakes per module | 0 | Stable (0 in Module 4 too) |
| Harness gaps per module | 0 new (1 filled during Phase 1) | Decreasing |
| Rules added per module | 0 new rule files | Stabilizing |
| First-attempt acceptance rate | ~100% | Stable |

---

## 2026-04-09 — Module 5 Phase 5 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Module:** Module 5 — Bulk Ordering System (Phase 5: Platform Admin Endpoints)

### Self-Audit Checklist
- [ ] **New pattern?** → No new patterns. Phase 5 follows the exact platform endpoint pattern established in Module 4 Phase 5 (`platform/orders.py`): `require_reel48_admin` dependency, `list_all_*` service method with optional company_id/status filters, cross-company detail endpoint with no company_id filter.
- [ ] **Pattern violated?** → No deviations. The endpoint, service method, and test patterns all mirror `platform/orders.py`.
- [ ] **New decision?** → No ADR-worthy decisions.
- [ ] **Missing guidance?** → No gaps discovered.
- [ ] **Reusable task?** → No new prompt templates needed.
- [x] **Changelog updated?** → This entry.

### Harness Files Updated
- **`backend/CLAUDE.md`** — Added `bulk_orders.py` to the `platform/` directory listing in the project structure section.

### Session Metrics
- **Tests written:** 6 (cross-company list, filter by company, filter by status, detail with items, 2 authorization checks)
- **Total test suite:** 322 passed, 0 failed
- **Mistakes caught by harness:** 0
- **Gaps found:** 0

### Implementation Notes
- `list_all_bulk_orders()` service method follows the same pattern as `list_all_orders()`: no company_id filter by default, optional company_id_filter and status_filter params
- Tests create bulk orders via API (not direct DB inserts) using manager tokens for both Company A and Company B, ensuring the full endpoint pipeline runs
- Status filter test creates two bulk orders, submits one, then verifies filter correctly partitions results

---

## 2026-04-09 — Module 5 Phase 3 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Module:** Module 5 — Bulk Ordering System (Phase 3: Item Management)

### Self-Audit Checklist
- [ ] **New pattern?** → No new patterns. Phase 3 reuses the exact same product/catalog validation, price snapshotting, size/decoration validation, and Decimal arithmetic patterns established in Module 4's `OrderService._validate_line_items()`. The `_recalculate_totals()` method uses `func.coalesce(func.sum(...), 0)` for denormalized totals — standard SQLAlchemy aggregation.
- [ ] **Pattern violated?** → No deviations. Item endpoints use `require_manager`, `_require_company_id`, and return standard `ApiResponse`/204 patterns. Employee validation checks `company_id` only (not sub_brand), matching the documented cross-sub-brand bulk order design.
- [ ] **New decision?** → No ADR-worthy decisions. Product_id is immutable on items (remove + re-add to change product) — consistent with order_line_items being immutable snapshots.
- [ ] **Missing guidance?** → No gaps discovered. The prompt provided exhaustive implementation details and all validation patterns were covered by existing harness rules.
- [ ] **Reusable task?** → No new prompt templates needed.
- [x] **Changelog updated?** → This entry.

### Harness Files Updated
- None — no new patterns or gaps identified.

### Session Metrics
- **Tests written:** 14 (8 add-item, 2 update-item, 2 remove-item, 2 state/totals)
- **Total test suite:** 294 passed, 0 failed
- **Mistakes caught by harness:** 0
- **Gaps found:** 0

### Implementation Notes
- `add_item()` follows the same validation chain as `OrderService._validate_line_items()`: catalog membership → product active → price resolution → size/decoration validation → employee validation
- `_recalculate_totals()` uses SUM(quantity) for total_items (not COUNT of rows), matching the schema documentation that total_items = sum of all quantities
- `update_item()` uses lazy product loading — only fetches the product if size or decoration validation is needed
- Employee validation is company_id-only (no sub_brand_id check) to support corporate admin cross-sub-brand bulk orders

---

## 2026-04-09 — Module 5 Phase 2 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Module:** Module 5 — Bulk Ordering System (Phase 2: Session CRUD)

### Self-Audit Checklist
- [ ] **New pattern?** → No new patterns. Phase 2 follows the exact service/endpoint/schema patterns established in Module 4 (OrderService). Draft-only edit/delete guards follow the same pattern as catalog draft restrictions in Module 3.
- [ ] **Pattern violated?** → No deviations. All endpoints use `require_manager` dependency, `_require_company_id` guard, `resolve_current_user_id` for created_by FK, `flush() + refresh()` pattern, and standard ApiResponse/ApiListResponse wrappers.
- [ ] **New decision?** → No ADR-worthy decisions. Hard delete for draft bulk orders is consistent with the established pattern (draft catalogs also hard-delete with their junction entries).
- [ ] **Missing guidance?** → No gaps discovered. The harness provided complete guidance for bulk order CRUD — catalog validation, order number generation, and role-based access were all well-documented from Module 4.
- [ ] **Reusable task?** → No new prompt templates needed.
- [x] **Changelog updated?** → This entry.

### Harness Files Updated
- None — no new patterns or gaps identified.

### Session Metrics
- **Tests written:** 15 (5 create, 2 list, 1 get, 2 update, 2 delete, 2 auth, 1 isolation)
- **Total test suite:** 280 passed, 0 failed
- **Mistakes caught by harness:** 0
- **Gaps found:** 0

### Implementation Notes
- BulkOrderService duplicates `_validate_catalog()` from OrderService as specified (keeps services self-contained)
- Order number format: `BLK-YYYYMMDD-XXXX` (same collision-retry pattern as `ORD-` numbers)
- Tests for non-draft status guards insert directly via admin_db_session with a real catalog (FK constraint requires it)

---

## 2026-04-09 — Module 5 Phase 1 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Module:** Module 5 — Bulk Ordering System (Phase 1: Database Migration)

### Self-Audit Checklist
- [x] **New pattern?** → No new patterns. Phase 1 follows the exact migration and model patterns established in Module 4 (migration 004). Bulk order items use the same product snapshotting pattern as order_line_items.
- [ ] **Pattern violated?** → No deviations. Migration uses same style as 004 (sa.Column, UUID(as_uuid=True), sa.ForeignKey(name=...), sa.text("now()"), op.execute() for RLS).
- [ ] **New decision?** → No ADR-worthy decisions. Bulk orders use same status set as individual orders plus 'submitted' (for manager submission to admin approval).
- [x] **Missing guidance?** → Module 5 table schemas were not in backend/CLAUDE.md. Now documented. `bulk_orders` and `bulk_order_items` added to "Which Base to Use" table.
- [ ] **Reusable task?** → No new prompt templates needed — migration pattern is well-established.
- [x] **Changelog updated?** → This entry.

### Harness Files Updated
- **`backend/CLAUDE.md`** — Added "Module 5 Table Schemas" section with `bulk_orders` and `bulk_order_items` schemas. Added both tables to "Which Base to Use" table.

### Session Metrics
- **Tests written:** 0 (Phase 1 is migration + models only; verified all 265 existing tests pass)
- **Total test suite:** 265 passed, 0 failed
- **Mistakes caught by harness:** 0
- **Gaps found:** 1 (table schemas not documented — filled)

---

## 2026-04-08 — Module 4 Completion (Ordering Flow)

**Type:** End-of-module self-audit + harness review
**Module:** Module 4 — Ordering Flow (Phases 1-5)

### Self-Audit Checklist
- [x] **New pattern?** → Price snapshotting at order time (catalog override → product price fallback), shipping address resolution (explicit → profile → null), order number generation (ORD-YYYYMMDD-XXXX with collision retry), ownership-based list visibility (employees see own vs managers see all), status transition endpoints (POST /{action} not PATCH). All documented in `backend/CLAUDE.md`.
- [ ] **Pattern violated?** → No deviations from harness patterns. All endpoints use TenantContext from JWT, defense-in-depth filtering, standard response format, and proper role checks.
- [ ] **New decision?** → No ADR-worthy decisions. Cancelled is a status (not a deletion) — consistent with the soft-delete strategy for user-facing entities. No tax/shipping calculation in initial build (total = subtotal).
- [x] **Missing guidance?** → Order placement patterns (snapshotting, shipping resolution, catalog validation) were not in the harness before Phase 6. Now documented in `backend/CLAUDE.md`.
- [ ] **Reusable task?** → Considered `prompts/ordering-pattern.md` but Module 5 (Bulk Ordering) has sufficiently different semantics (admin-initiated, no employee self-service) that a shared template would over-generalize. The patterns documented in `backend/CLAUDE.md` are sufficient.
- [x] **Changelog updated?** → This entry.

### Harness Files Updated
- **`backend/CLAUDE.md`** — Added "Order Placement Patterns" section (price snapshotting, shipping address resolution, order number format, catalog validation). Added `order_line_items` to "Which Base to Use" table. (Table schemas, role-based visibility, and status lifecycle sections were already added during Phases 3-4.)

### Post-Module Pattern Consistency Review
- All 5 order endpoints + 2 platform endpoints follow the established route → service → model pattern.
- All queries include defense-in-depth `company_id` filtering alongside RLS.
- Both `orders` and `order_line_items` tables have company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE) RLS policies in the same migration.
- Naming conventions consistent: snake_case endpoints, plural nouns, standard response wrapper.
- No RLS gaps: `conftest.py` grants include both new tables.

### Session Metrics
- **Tests written (Module 4 total):** 54 (22 placement + 14 list/get + 12 transitions + 6 platform)
- **Total test suite:** 265 passed, 0 failed
- **Mistakes caught by harness:** 1 (incorrect `fulfilled` status name corrected to `processing` during Phase 4)
- **Gaps found:** 3 (table schemas, role-based visibility, order placement patterns — all filled)

---

## 2026-04-08 — Module 4 Phase 5 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Module:** Module 4 — Ordering Flow (Phase 5: Platform Admin Order Endpoints)

### Self-Audit Checklist
- [x] **New pattern?** No — followed existing platform admin endpoint pattern from `platform/products.py` and `platform/catalogs.py` exactly.
- [x] **Pattern violated?** No.
- [x] **New decision?** No.
- [x] **Missing guidance?** No.
- [x] **Reusable task?** No.
- [x] **Changelog updated?** This entry.

### Summary
Added `GET /api/v1/platform/orders/` (list with filters) and `GET /api/v1/platform/orders/{id}` (detail with line items) for reel48_admin cross-company visibility. Added `list_all_orders()` to OrderService. 6 new tests covering cross-company listing, company/status filters, detail retrieval, and authorization rejection for corporate_admin and employee roles. All 265 tests passing. No harness updates needed — existing patterns applied cleanly.

---

## 2026-04-08 — Module 4 Phase 4 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Module:** Module 4 — Ordering Flow (Phase 4: Order Status Transitions)

### Self-Audit Checklist
- [x] **New pattern?** Yes — order status transition endpoints using `POST /{id}/{action}` pattern with role-based authorization. Cancel uses `get_tenant_context` with service-layer ownership check; all others use `require_manager` dependency. Documented in `backend/CLAUDE.md`.
- [x] **Pattern violated?** Yes — the Module 4 table schema listed `fulfilled` as a status but implementation uses `processing`. Fixed in `backend/CLAUDE.md`.
- [ ] **New decision?** No — transition rules and authorization were specified in the prompt.
- [ ] **Missing guidance?** No — existing harness patterns for service methods, endpoints, and testing were sufficient.
- [ ] **Reusable task?** No — status transition pattern is documented inline.
- [x] **Changelog updated?** This entry.

### Harness Files Updated
- **`backend/CLAUDE.md`** — Fixed order status list (`fulfilled` → `processing`). Added "Order Status Lifecycle & Transitions" section documenting the state machine, authorization rules per transition, endpoint pattern, and invalid transition handling.

### Session Metrics
- **Tests written:** 12 new (4 functional, 5 authorization, 3 invalid transitions)
- **Total order tests:** 48 passed (36 Phases 2-3 + 12 Phase 4)
- **Mistakes caught by harness:** 0
- **Gaps found:** 1 (incorrect status name `fulfilled` vs `processing` in table schema — fixed)

---

## 2026-04-08 — Module 4 Phase 3 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Module:** Module 4 — Ordering Flow (Phase 3: Order List & Get Endpoints)

### Self-Audit Checklist
- [x] **New pattern?** Yes — ownership-based visibility for orders (managers see all in scope, employees see only own). This differs from the status-based visibility used by products/catalogs. Also introduced the `/my/` explicit endpoint pattern. Both documented in `backend/CLAUDE.md`.
- [x] **Pattern violated?** No — followed existing patterns for pagination, defense-in-depth filtering, and standard response format.
- [x] **New decision?** No — the role-based visibility split was specified in the prompt and aligns with the auth access matrix.
- [ ] **Reusable task?** No — standard CRUD list/get pattern.
- [x] **Changelog updated?** This entry.

### Harness Files Updated
- **`backend/CLAUDE.md`** — Added "Module 4 Table Schemas" section documenting `orders` and `order_line_items` tables (column definitions, RLS policies, snapshot pattern). Added "Order Retrieval: Role-Based Visibility" section documenting the ownership-based visibility pattern, the `/my/` endpoint pattern, and the role-to-endpoint access matrix.
- **`.claude/rules/testing.md`** — Added "Role-Specific User + Token Fixtures" section listing all User+Token fixture pairs vs token-only fixtures, explaining when to use each. Documents the new `user_a1_manager` + `user_a1_manager_token` fixtures.

### New Fixtures Added
- `user_a1_manager` + `user_a1_manager_token` in `conftest.py` — regional_manager User record with matching JWT. Previously only the token fixture existed without a backing User record.

### Session Metrics
- **Tests written:** 14 new (5 functional, 6 role-visibility, 3 isolation)
- **Total order tests:** 36 passed (22 Phase 2 + 14 Phase 3)
- **Mistakes caught by harness:** 0
- **Gaps found:** 2 (Module 4 table schemas not documented, role-based list visibility pattern not documented — both now fixed)

---

## 2026-04-08 — Module 3 Phase 3 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Module:** Module 3 — Product Catalog & Brand Management (Phase 3: Catalogs CRUD + Catalog-Product Association)

### Self-Audit Checklist
- [x] **New pattern?** Yes — catalog slug auto-generation with collision handling, submit-guard (requires products), buying window validation tied to payment_model. Added to `backend/CLAUDE.md`.
- [x] **Pattern violated?** No — followed the products.py endpoint, service, and schema patterns exactly.
- [x] **New decision?** No — payment_model and buying window behavior were already specified in root CLAUDE.md.
- [x] **Missing guidance?** Catalog status lifecycle and slug generation were not documented. Added to `backend/CLAUDE.md`.
- [ ] **Reusable task?** No — the catalog CRUD pattern is the same as the product CRUD pattern.
- [x] **Changelog updated?** This entry.

### Harness Files Updated
- **`backend/CLAUDE.md`** — Added "Catalog Status Lifecycle & Visibility" section documenting status transitions, edit/delete restrictions, submit guard, buying window validation, role-based visibility, and slug auto-generation pattern.

### Session Metrics
- **Tests written:** 28 (8 create, 4 list, 2 get, 2 update, 2 submit, 1 delete, 6 catalog-products, 3 isolation)
- **Total test suite:** 193 passed, 0 failed
- **Mistakes caught by harness:** 0 (patterns from Phase 2 carried over cleanly)
- **Gaps found:** 1 (catalog lifecycle not documented — now fixed)

---

## 2026-04-08 — Module 3 Phase 2 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Author:** Claude Code
**Scope:** Module 3 Phase 2 — Products CRUD (service, schemas, API endpoints, 24 tests)

### Self-Audit Checklist

| Question | Finding | Action |
|----------|---------|--------|
| New pattern introduced? | YES — Product status lifecycle with draft-only edit/delete restrictions; status-based visibility (employees see only active); submit endpoint for status transitions | Added "Product Status Lifecycle & Visibility" section to backend/CLAUDE.md |
| Existing pattern violated? | NO — followed employee_profiles patterns for service, schema, endpoint, and test structure | No action |
| New decision made? | Draft-only editing is an implicit constraint not previously documented. Employees seeing only active products is a visibility rule not in the harness. | Documented in backend/CLAUDE.md |
| Missing guidance discovered? | NO — harness covered CRUD patterns, defense-in-depth, SKU uniqueness, and test organization | No action |
| Prompt template needed? | NO — standard CRUD build following established patterns | No action |

### Harness Files Updated

| File | Change |
|------|--------|
| `backend/CLAUDE.md` | Added "Product Status Lifecycle & Visibility" section documenting status transitions, edit restrictions, and role-based visibility |
| `docs/harness-changelog.md` | This entry |

### Module 3 Phase 2 Completeness Summary

| Area | Count | Status |
|------|-------|--------|
| Schema file | 1 (product.py) | Complete |
| Service file | 1 (product_service.py) | Complete |
| Endpoint file | 1 (products.py) | Complete |
| Router update | 1 (router.py) | Complete |
| Tests | 24 (7 create, 5 list, 3 get, 2 update, 2 delete, 2 submit, 3 isolation) | All passing |
| Total test suite | 165 tests | All passing |

---

## 2026-04-08 — Module 3 Phase 1 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Author:** Claude Code
**Scope:** Module 3 Phase 1 — Product Catalog database foundation (migration, models, conftest grants)

### Self-Audit Checklist

| Question | Finding | Action |
|----------|---------|--------|
| New pattern introduced? | NO — followed existing Module 1/2 migration and model patterns exactly | No action |
| Existing pattern violated? | NO — all TenantBase, RLS, and naming conventions followed | No action |
| New decision made? | Minor — JSONB columns with `server_default='[]'::jsonb` for product sizing/decoration/images, partial unique indexes for soft-delete-safe uniqueness | Not significant enough for ADR; standard PostgreSQL patterns |
| Missing guidance discovered? | NO — harness covered all scenarios (TenantBase shape, RLS policies, migration grouping, conftest grants) | No action |
| Prompt template needed? | NO — standard migration + model creation, no reusable pattern to extract | No action |

### Harness Files Updated

| File | Change |
|------|--------|
| `backend/CLAUDE.md` | Added "Module 3 Table Schemas" section with products, catalogs, catalog_products column specs |
| `backend/tests/conftest.py` | Added products, catalogs, catalog_products to reel48_app GRANT list |
| `docs/harness-changelog.md` | This entry |

### Module 3 Phase 1 Completeness Summary

| Area | Count | Status |
|------|-------|--------|
| Alembic migration | 1 (003 — 3 tables + RLS) | Complete |
| SQLAlchemy models | 3 (Product, Catalog, CatalogProduct) | Complete |
| Models __init__.py | Updated with 3 new imports | Complete |
| conftest.py grants | 3 tables added to reel48_app | Complete |
| Existing tests | 141 | All passing (no regressions) |

### Remaining Module 3 Work
- **Phase 2:** Pydantic schemas, CRUD endpoints, service layer, tests for products
- **Phase 3:** Catalog endpoints, catalog-product association, approval workflow
- **Phase 4:** Frontend catalog browsing UI

### Harness Health Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Patterns violated during Module 3 P1 | 0 | Stable (0 in Module 2 P1 also) |
| Harness gaps found | 0 | Improving (was 2 in Module 2 P1) |
| New rules/sections added | 1 (table schema docs) | Decreasing |
| Backend test count | 141 | No change (database-only phase) |

---

## 2026-04-08 — Module 2 Phase 1 End-of-Session Self-Audit

**Type:** End-of-session self-audit
**Author:** Claude Code
**Scope:** Module 2 Phase 1 — Employee Profiles (backend only: model, migration, endpoints, service, tests)

### Self-Audit Checklist

| Question | Finding | Action |
|----------|---------|--------|
| New pattern introduced? | YES — `PUT /me` upsert for 1:1 user-owned resources | Documented in `backend/CLAUDE.md` |
| Existing pattern violated? | NO — all Module 1 patterns followed correctly | No action |
| New decision made? | Minor — upsert via PUT instead of separate POST/PUT | Documented as pattern, not significant enough for ADR |
| Missing guidance discovered? | YES — trailing slash on list endpoint URLs causes 307 in tests | Documented in `backend/CLAUDE.md` and `.claude/rules/testing.md` |
| Prompt template needed? | NO — standard CRUD module, no reusable pattern to extract | No action |

### Harness Files Updated

| File | Change |
|------|--------|
| `backend/CLAUDE.md` | Added `employee_profiles` to "Which Base to Use" table |
| `backend/CLAUDE.md` | Added "Module 2 Table Schema" section with `employee_profiles` column spec |
| `backend/CLAUDE.md` | Added "PUT /me Upsert Pattern for Owned Resources" section |
| `backend/CLAUDE.md` | Added "Trailing Slash Behavior in Tests" section |
| `.claude/rules/testing.md` | Added trailing slash mistake to "Common Mistakes to Avoid" |
| `docs/harness-changelog.md` | This entry |

### Module 2 Phase 1 Completeness Summary

| Area | Count | Status |
|------|-------|--------|
| Backend model | 1 (EmployeeProfile) | Complete |
| Alembic migration | 1 (002 — table + RLS) | Complete |
| Backend endpoints | 6 (GET/PUT /me, GET list, GET/PATCH/DELETE by ID) | Complete |
| Backend service | 1 (EmployeeProfileService — 7 methods) | Complete |
| Backend tests | 25 (16 functional, 6 authorization, 3 isolation) | All passing |
| Total test count | 141 (116 Module 1 + 25 Module 2) | All passing |

### Remaining Module 2 Work
- **Profile photo upload (S3):** Scoped out of Phase 1. The `profile_photo_url` column exists but upload functionality deferred to a later phase when S3 integration is built.

### Harness Health Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Patterns violated during Module 2 P1 | 0 | Improving (was 4 in Module 1) |
| Harness gaps found | 2 (upsert pattern, trailing slash) | Decreasing (was 6+6 in Module 1) |
| New rules/sections added | 4 | Stabilizing (was 14 in Module 1) |
| Backend test count | 141 | 9 files |

---

## 2026-04-08 — Module 1 Formal Post-Module Harness Review

**Type:** Post-module harness review (deep audit)
**Author:** Claude Code
**Scope:** Complete file-by-file review of all Module 1 code for pattern compliance, harness gap identification, rule effectiveness assessment, ADR verification, and harness updates.

### Pattern Consistency Scan Results

**Models (5/5 PASS):** All models use the correct base class (GlobalBase, CompanyBase, TenantBase).
**Migration (PASS):** Single migration creates all 5 tables with RLS policies in the same file. ENABLE + FORCE on all tables. RESTRICTIVE on sub-brand scoping. Circular FK resolved with deferred constraint. Downgrade reverses cleanly.
**Endpoints (PASS with 1 fix):** All use TenantContext from JWT. Standard response format. Pagination on all list endpoints. Explicit role checks. Defense-in-depth filtering in all services.
**Frontend (PASS):** `'use client'` on all Carbon imports. Carbon-first UI. Tailwind for layout only. Correct icon typing and Header className usage. API client transforms snake/camelCase correctly.

### Consistency Fix Applied
- **`DELETE /users/{user_id}`** changed from 204 (no body) to 200 with `ApiResponse[UserResponse]` — aligns with companies/sub_brands soft-delete pattern.
- **`UserService.soft_delete_user`** now returns the User object (was `None`).
- Test updated to assert 200 + response body.

### Harness Gaps Found and Filled

| Gap | File Updated | Section Added |
|-----|-------------|---------------|
| No soft-delete vs hard-delete HTTP status convention | `backend/CLAUDE.md`, `.claude/rules/api-endpoints.md` | "Delete Endpoint Return Conventions" |
| `resolve_current_user_id` helper undocumented | `backend/CLAUDE.md` | "TenantContext.user_id vs users.id" |
| `_require_company_id` guard pattern undocumented | `backend/CLAUDE.md` | "Company-Scoped Endpoint Guard" |
| External service mock pattern undocumented | `.claude/rules/testing.md` | "External Service Mock Pattern" |
| Rate limit test bypass undocumented | `.claude/rules/testing.md` | "Rate Limit Testing" |
| Multi-table migration guidance missing | `.claude/rules/database-migrations.md` | "Multi-table migrations are acceptable" |

### Rule File Effectiveness Assessment

| Rule File | Activated? | Effective? | Changes Made |
|-----------|-----------|------------|--------------|
| `database-migrations.md` | YES | YES | Added multi-table migration note |
| `api-endpoints.md` | YES | YES | Added soft-delete convention |
| `authentication.md` | YES | YES | No changes needed |
| `testing.md` | YES | YES | Added 2 new sections |
| `carbon-design-system.md` | YES | YES | No changes needed |
| `s3-storage.md` | NO (expected) | N/A | — |
| `stripe-invoicing.md` | NO (expected) | N/A | — |
| `harness-maintenance.md` | YES | YES | No changes needed |

### ADR Verification

All 8 ADRs reviewed. All active. No decisions reversed. No new ADRs needed.
- ADR-001 through ADR-005, ADR-007, ADR-008: Fully implemented and matching.
- ADR-006 (Stripe): Not yet implemented (Module 7). Still valid.

### Harness Health Metrics (Updated)

| Metric | Value | Trend |
|--------|-------|-------|
| Patterns violated during Module 1 | 4 | Baseline |
| Harness gaps found (in-session) | 6 | Baseline |
| Harness gaps found (post-module review) | 6 more | Expected for first module |
| Total harness rules added (Module 1) | 14 sections | Stabilizing expected |
| Backend test count | 116 | 8 files |
| Frontend test count | 43 | 7 files |

### Files Modified in This Review
- **`backend/app/api/v1/users.py`** — DELETE endpoint: 204→200 with response body
- **`backend/app/services/user_service.py`** — `soft_delete_user` now returns User
- **`backend/tests/test_users.py`** — Updated assertion for DELETE response
- **`backend/CLAUDE.md`** — Added 3 sections: resolve_current_user_id, _require_company_id guard, delete conventions
- **`.claude/rules/testing.md`** — Added 2 sections: external service mocks, rate limit testing
- **`.claude/rules/database-migrations.md`** — Added multi-table migration note
- **`.claude/rules/api-endpoints.md`** — Added soft-delete return convention
- **`docs/harness-changelog.md`** — This entry

### Readiness for Module 2 (Employee Profiles)
The harness is ready. Module 2 will depend on:
- Auth middleware + TenantContext (fully documented)
- User model + CRUD (consistent patterns, tested)
- Frontend auth + layout shell (Carbon-first, tested)
- New patterns documented: resolve_current_user_id, _require_company_id guard, external service mocking, soft-delete conventions

---

## 2026-04-08 — Module 1 Post-Module Review (Phases 1–7 Complete)

**Type:** End-of-session self-audit (Phase 7)
**Author:** Claude Code
**Scope:** Full Module 1 (Auth & Multi-Tenancy) review — backend (7 phases), frontend (2 phases), harness updates.

### Module 1 Completeness Summary

| Area | Count | Status |
|------|-------|--------|
| Backend models | 5 (Company, SubBrand, User, Invite, OrgCode) | Complete |
| Alembic migrations | 1 (all 5 tables + RLS policies) | Complete |
| Backend endpoints | 19 CRUD + 3 auth/registration | Complete |
| Backend services | 7 + CognitoService + RegistrationService | Complete |
| Backend tests | 116 test functions across 8 files | All passing |
| Frontend pages | 5 (login, register, invite landing, invite/[token], dashboard placeholder) | Complete |
| Frontend components | Header, Sidebar, MainLayout, ProtectedRoute, ErrorBoundary | Complete |
| Frontend tests | 43 tests across 7 files | All passing |
| TODOs/FIXMEs | 0 in both backend and frontend | Clean |

### Pattern Consistency Scan
- All 5 tables have RLS policies created in the same migration
- All CRUD endpoints use TenantContext from JWT (no tenant IDs accepted as params)
- All unauthenticated endpoints (validate-org-code, register, register-from-invite) use `skipAuth` and rate limiting
- Standard API response format (`{ data, meta, errors }`) used consistently
- Frontend follows Carbon-first pattern with Tailwind for layout only

### Phase 7 Self-Audit Findings

1. **New pattern introduced? YES — `skipAuth` on API client**
   - Registration pages need to call unauthenticated endpoints. Added `skipAuth?: boolean` option to the API client's `FetchOptions`. When true, skips `fetchAuthSession()` and 401 retry.
   - **Action:** Documented in `frontend/CLAUDE.md` under "Unauthenticated API Calls (`skipAuth`)" section.

2. **Existing pattern violated? NO** — All Phase 7 code follows login page patterns exactly.

3. **New decision? NO** — Registration flow design followed ADR-007 and the Phase 7 prompt.

4. **Missing guidance discovered? YES — `invite/page.tsx` landing page**
   - The routing structure in `frontend/CLAUDE.md` listed `invite/[token]/page.tsx` but not the `invite/page.tsx` landing page for manual token entry.
   - **Action:** Updated routing structure to include `invite/page.tsx`.

5. **Prompt template needed? NO** — Registration pages are a one-time build.

### Files Updated
- **`frontend/CLAUDE.md`** — Added `skipAuth` API client documentation; updated routing structure to include `invite/page.tsx`; updated API client code example with `skipAuth` option signatures
- **`docs/harness-changelog.md`** — This entry

### Harness Health Metrics (Module 1 Complete)
| Metric | Value | Notes |
|--------|-------|-------|
| Patterns violated across all phases | 4 | Route group collision, ErrorBoundary class component, RESTRICTIVE RLS, SET LOCAL bind params |
| Harness gaps found | 6 | Vitest setup, matchMedia polyfill, Amplify v6 mocks, route collisions, skipAuth, invite landing page |
| Rules added (total) | 8 sections | Test infrastructure, route collision, icon typing, Header style, RESTRICTIVE RLS, SET LOCAL, skipAuth, invite route |
| Backend test count | 116 | 8 test files |
| Frontend test count | 43 | 7 test files |

### What Module 2 Needs
Module 2 (Employee Profiles) will depend on:
- Auth middleware and TenantContext (Module 1 Phase 3)
- User model and CRUD endpoints (Module 1 Phase 4)
- Frontend auth integration and layout shell (Module 1 Phase 6)
- The `skipAuth` pattern is NOT needed for Module 2 (all profile endpoints are authenticated)

---

## 2026-04-08 — Module 1 Phase 7: Registration Pages (Frontend)

**Type:** End-of-session self-audit
**Author:** Claude Code
**Session scope:** Phase 7 — Self-registration page (two-step org code flow), invite registration page (dynamic route + landing), API client `skipAuth` option, TypeScript registration types, 17 new tests.

### Changes Made
- **`src/types/registration.ts`** (new) — TypeScript types for registration API responses
- **`src/lib/api/client.ts`** (modified) — Added `skipAuth?: boolean` to FetchOptions and all api methods
- **`src/app/(public)/register/page.tsx`** (new) — Two-step self-registration: org code validation → registration form with sub-brand dropdown
- **`src/app/(public)/invite/page.tsx`** (new) — Landing page for manual invite token entry
- **`src/app/(public)/invite/[token]/page.tsx`** (new) — Invite registration form with token from URL
- **`src/__tests__/register-page.test.tsx`** (new) — 9 tests covering both steps, validation, success/error
- **`src/__tests__/invite-page.test.tsx`** (new) — 8 tests covering landing page and token registration

### Verification
- `npm run lint` — No warnings or errors
- `npm run type-check` — Clean
- `npm run test:run` — 43/43 passing (26 existing + 17 new)
- `npm run build` — Compiled successfully, all routes generated

---

## 2026-04-07 — Module 1 Phase 6: Frontend Application Shell

**Type:** End-of-session self-audit
**Author:** Claude Code
**Session scope:** Phase 6 — Next.js 14 project setup, Amplify v6 auth integration, Carbon layout (Header + Sidebar + MainLayout), login page, API client with snake/camel transform, and 26 frontend tests. 35 new files created.

### Self-Audit Findings

1. **New patterns introduced? YES**
   - **`window.matchMedia` polyfill for jsdom:** Carbon's `useMatchMedia` hook calls `window.matchMedia()` which doesn't exist in jsdom. All test suites using Carbon layout components (SideNav, Header) will fail without this polyfill in the test setup file.
   - **Amplify v6 modular imports:** `getCurrentUser()` throws when no session (v5 returned null). Custom claims accessed via bracket notation: `payload['custom:company_id']`.
   - **Carbon `CarbonIconType`:** When a component prop accepts a Carbon icon, use `CarbonIconType` from `@carbon/icons-react/lib/CarbonIcon` — not `React.ComponentType<{ size?: number }>` (TS error due to `size` accepting `string | number`).
   - **Carbon `<Header>` does not accept `style` prop:** Use Tailwind `className` instead.
   - **`QueryClient` via `useState`:** Must be created inside `useState(() => new QueryClient(...))` in providers to avoid re-creation on re-render.
   - **Action:** Added all patterns to `frontend/CLAUDE.md` (Amplify v6 API, test infrastructure, route collision rule) and `.claude/rules/carbon-design-system.md` (icon typing, Header style prop).

2. **Existing pattern violated? YES — route group collision**
   - The harness routing structure showed `(authenticated)/dashboard/page.tsx` and `(platform)/dashboard/page.tsx` as sibling pages. Next.js route groups strip parenthesized names from URLs, so both resolved to `/dashboard` and caused a build error.
   - **Fix:** Platform pages nested under `(platform)/platform/` directory, producing `/platform/dashboard`, `/platform/companies`, etc.
   - **Action:** Updated routing structure in `frontend/CLAUDE.md` with the correct layout and added "Route Group Collision Rule" section.

3. **Existing pattern violated? YES — Error boundary exception**
   - The harness said "functional components only" but React error boundaries require class components.
   - **Action:** Updated `frontend/CLAUDE.md` component conventions to note the ErrorBoundary exception.

4. **New decision made? NO** — All tech choices followed existing harness guidance.

5. **Missing guidance discovered? YES**
   - No documentation of Vitest config patterns (jsdom env, path alias, globals, setup file).
   - No documentation of how to mock Amplify auth and Next.js navigation in tests.
   - No mention that `window.matchMedia` needs polyfilling for Carbon in jsdom.
   - No mention of route group URL collision behavior.
   - **Action:** Added "Test Infrastructure Patterns" section to `frontend/CLAUDE.md` covering vitest config, matchMedia polyfill, Amplify mock pattern, and Next.js navigation mock pattern. Added "Route Group Collision Rule" section.

6. **Prompt template needed? NO** — Frontend scaffolding is a one-time setup.

### Files Updated
- **`frontend/CLAUDE.md`** — Updated Amplify config to v6 function pattern; added Amplify v6 Auth API Surface section; added Test Infrastructure Patterns section (matchMedia polyfill, Amplify mock, Next.js navigation mock); updated routing structure for platform group collision fix; added Route Group Collision Rule; updated component conventions for ErrorBoundary class component exception
- **`.claude/rules/carbon-design-system.md`** — Added Carbon Icon Typing section (`CarbonIconType`); added Carbon Header `style` Prop section; added 2 new entries to Common Mistakes to Avoid

### Harness Health Metrics (Phase 6)
| Metric | Value | Notes |
|--------|-------|-------|
| Patterns violated | 2 | Route group collision, Error boundary class component |
| Harness gaps found | 4 | Vitest setup, matchMedia polyfill, Amplify v6 mocks, route collisions |
| Rules added | 4 sections | Test Infrastructure, Route Group Collision, Icon Typing, Header Style |
| Rules updated | 3 sections | Amplify config, Routing Structure, Component Conventions |
| First-attempt accuracy | High | 26/26 tests pass after 2 targeted fixes (matchMedia polyfill, mock override for null values) |

### What Phase 7 Needs
Phase 7 (Registration pages) will need:
- `/register` page with two-step org code flow (validate → form expand)
- `/invite/[token]` page for invite-based registration
- Integration with `POST /api/v1/auth/validate-org-code` and `POST /api/v1/auth/register`
- Carbon `Dropdown` for sub-brand selection
- Error handling matching the generic-error pattern (no enumeration)

---

## 2026-04-07 — Module 1 Phase 4: CRUD Endpoints, Schemas & Services

**Type:** End-of-session self-audit
**Author:** Claude Code
**Session scope:** Phase 4 — Pydantic schemas, service layer, API endpoints, and tests for all 5 Module 1 entities (Companies, SubBrands, OrgCodes, Users, Invites). 22 new files, 93 tests passing, ruff + mypy clean.

### Self-Audit Findings

1. **New patterns introduced? YES**
   - `db.refresh()` after `flush()` in service methods where `onupdate=func.now()` expires attributes — prevents `MissingGreenlet` when Pydantic serializes the response.
   - Isolation test commit/cleanup pattern: seed data must be COMMITTED (not just flushed) for cross-session RLS testing, with explicit cleanup in `finally` blocks.
   - **Action:** Added both patterns to `backend/CLAUDE.md` with examples.

2. **Existing pattern violated? YES — critical RLS bug fixed**
   - PostgreSQL combines multiple PERMISSIVE policies with OR. The `users_sub_brand_scoping` policy was PERMISSIVE (default), meaning sub-brand filtering was ineffective — any row passing company isolation was visible regardless of sub-brand. **This was a data leakage vulnerability.**
   - **Fix:** Changed `users_sub_brand_scoping` to `AS RESTRICTIVE` in the migration. RESTRICTIVE policies are ANDed with PERMISSIVE policies.
   - **Action:** Updated RLS template in root `CLAUDE.md` and `.claude/rules/database-migrations.md` to use `AS RESTRICTIVE` for sub-brand scoping. Added new "RESTRICTIVE vs PERMISSIVE" section to database-migrations rule.

3. **Existing pattern violated? YES — SET LOCAL bind parameters**
   - Harness showed `SET LOCAL` with bind parameters (`:param`). PostgreSQL's SET statement does not support bind parameters — causes `PostgresSyntaxError`.
   - **Fix:** Changed to f-string interpolation. Safe because values are validated UUIDs from JWTs.
   - **Action:** Added "SET LOCAL Does Not Support Bind Parameters" section to `backend/CLAUDE.md`. Updated isolation test pattern in `.claude/rules/testing.md`.

4. **New decision? YES — pytest-asyncio session-scoped loop**
   - Added `asyncio_default_fixture_loop_scope = "session"` and `asyncio_default_test_loop_scope = "session"` to `pyproject.toml`. Required because session-scoped fixtures (database engines) must share the same event loop as tests.

5. **Missing guidance discovered? NO** — All other patterns were covered by existing harness.

6. **Prompt template needed? NO** — Phase 4 patterns are now documented in harness files.

### Files Updated
- `CLAUDE.md` — RLS template: added `AS RESTRICTIVE` to sub-brand scoping policy
- `backend/CLAUDE.md` — Added: SET LOCAL bind parameter limitation, db.refresh() after flush pattern
- `.claude/rules/database-migrations.md` — Added: RESTRICTIVE vs PERMISSIVE section, updated RLS template
- `.claude/rules/testing.md` — Updated isolation test pattern with f-string SET LOCAL and commit requirement

---

## 2026-04-07 — Module 1 Phase 3: Auth Middleware & Tenant Context

**Type:** End-of-session self-audit
**Author:** Claude Code
**Session scope:** Phase 3 — JWT validation (`security.py`), TenantContext dataclass (`tenant.py`), `get_tenant_context` dependency with SET LOCAL session variables, TenantContextMiddleware, conftest.py rewrite with dual-session RLS testing, 28 tests (auth + isolation)

### Self-Audit Findings

1. **New pattern introduced? YES**
   - `SET LOCAL` instead of `SET` for PostgreSQL session variables — scopes values to the
     current transaction, preventing leakage across pooled connections.
   - Dual-session test infrastructure: `admin_db_session` (superuser, bypasses RLS) and
     `db_session` (non-superuser `reel48_app`, RLS enforced).
   - Alembic migrations via subprocess in tests to avoid `asyncio.run()` conflict with
     pytest-asyncio.
   - JWKS monkeypatch pattern: patch `_fetch_jwks` + reset module-level cache.
   - **Action:** Updated `backend/CLAUDE.md` (SET LOCAL, testing patterns); added RLS
     testing infrastructure section to `.claude/rules/testing.md`.

2. **Existing pattern violated? YES — improved**
   - The harness (root CLAUDE.md and backend CLAUDE.md) showed plain `SET` for session
     variables. Implementation used `SET LOCAL` which is safer with connection pooling.
   - **Action:** Updated `backend/CLAUDE.md` JWT Validation Flow to use `SET LOCAL` and
     added "SET LOCAL vs SET" explanation section.
   - The harness showed `@pytest.mark.asyncio` decorator, but the project uses
     `asyncio_mode = "auto"` (no decorator needed).
   - **Action:** Updated `.claude/rules/testing.md` async test convention.

3. **New decision made? YES**
   - `SET LOCAL` over `SET` for session variables (safety improvement).
   - Non-superuser test role (`reel48_app`) required because PostgreSQL superusers
     bypass RLS even with `FORCE ROW LEVEL SECURITY`.
   - Both are implementation details, not significant enough for standalone ADRs.

4. **Missing guidance discovered? YES**
   - No documentation of dual-session test infrastructure or JWKS monkeypatch pattern.
   - No mention that `asyncio_mode = "auto"` eliminates the need for `@pytest.mark.asyncio`.
   - **Action:** Added comprehensive RLS Testing Infrastructure section to
     `.claude/rules/testing.md` covering dual sessions, Alembic subprocess, JWT test
     infrastructure, isolation test pattern, and guidance for adding new tables.

5. **Prompt template needed? NO**
   - Auth middleware is a one-time foundation, not a recurring pattern.

### Files Updated
- **File:** `backend/CLAUDE.md`
  - **Change:** Updated TenantContext to `UUID | None` syntax; updated JWT Validation Flow
    to use `SET LOCAL`; added "SET LOCAL vs SET" section; replaced placeholder test fixture
    docs with actual Phase 3 infrastructure (Alembic subprocess, dual sessions, JWKS
    monkeypatch, fixture signatures, client fixture explanation)
  - **Reason:** Phase 3 implemented the actual auth and test infrastructure — harness must
    match reality
  - **Impact:** Future sessions understand the complete test infrastructure without
    reverse-engineering conftest.py

- **File:** `.claude/rules/testing.md`
  - **Change:** Fixed async test convention (`asyncio_mode = "auto"`, no decorator needed);
    added "RLS Testing Infrastructure" section covering dual sessions, Alembic subprocess,
    JWT test infrastructure, isolation test pattern, and new-table checklist
  - **Reason:** Phase 3 established test patterns that all future modules depend on
  - **Impact:** Future modules follow the established dual-session and JWKS patterns
    correctly; know to update grant list when adding tables

### Harness Health Metrics (Phase 3)
| Metric | Value | Notes |
|--------|-------|-------|
| Patterns violated | 1 (improved) | `SET` → `SET LOCAL` — safer pattern adopted |
| Harness gaps found | 2 | Dual-session testing, asyncio_mode convention — now documented |
| Rules added | 1 section | "RLS Testing Infrastructure" in testing.md |
| Rules updated | 3 sections | TenantContext, JWT Validation Flow, Testing Patterns in backend/CLAUDE.md |
| First-attempt accuracy | High | Implementation matched plan; ruff/mypy issues were mechanical |

### What Phase 4 Needs
Phase 4 (CRUD endpoints for Module 1 entities) will need:
- Route handlers using `get_tenant_context` for tenant-scoped endpoints
- Service layer with defense-in-depth filtering alongside RLS
- Pydantic request/response schemas following the standard response format
- Functional + isolation + authorization tests per entity

---

## 2026-04-07 — Module 1 Phase 2: SQLAlchemy Models + Alembic Migration with RLS

**Type:** End-of-session self-audit
**Author:** Claude Code
**Session scope:** Phase 2 — 5 SQLAlchemy models (Company, SubBrand, User, Invite, OrgCode) + single Alembic migration with RLS policies

### Self-Audit Findings

1. **New pattern introduced? YES**
   - Deferred FK pattern for circular dependencies: when two tables reference each other
     (org_codes ↔ users), create one table without the FK constraint, create the other
     with its FK, then add the deferred FK via `op.create_foreign_key()`.
   - Single migration for tightly coupled identity tables (all 5 Module 1 tables in one
     migration) rather than one migration per table.
   - **Action:** Added "Circular Foreign Key Dependencies" section to
     `.claude/rules/database-migrations.md` documenting the deferred FK pattern.

2. **Existing pattern violated? NO**
   - All models use the correct base classes (GlobalBase, CompanyBase, TenantBase).
   - All RLS policies follow the exact templates from the harness.
   - FK and index naming follows `fk_{table}_{column}_{ref_table}` and `ix_{table}_{column}`.
   - Migration is fully reversible with correct downgrade ordering.

3. **New decision made? YES — minor**
   - Used a single migration for all 5 identity tables rather than one per table. These
     tables form a tightly coupled identity layer with no valid intermediate state. Not
     significant enough for a standalone ADR.

4. **Missing guidance discovered? YES**
   - No documented pattern for resolving circular FK dependencies in migrations.
   - **Action:** Added guidance to `.claude/rules/database-migrations.md` (see above).

5. **Prompt template needed? NO**
   - Identity table creation is a one-time task, not a recurring pattern.

### Files Updated
- **File:** `.claude/rules/database-migrations.md`
  - **Change:** Added "Circular Foreign Key Dependencies" section with deferred FK pattern
  - **Reason:** org_codes ↔ users circular FK had no documented resolution
  - **Impact:** Future modules with cross-table FK cycles have a standard approach

### Harness Health Metrics (Phase 2)
| Metric | Value | Notes |
|--------|-------|-------|
| Patterns violated | 0 | All harness conventions followed correctly |
| Harness gaps found | 1 | Circular FK resolution — now documented |
| Rules added | 1 section | "Circular Foreign Key Dependencies" in database-migrations.md |
| First-attempt accuracy | High | Models and migration matched harness schemas on first pass |

### What Phase 3 Needs
Phase 3 (auth middleware, tenant context, JWT validation) will need:
- `app/middleware/` — tenant context middleware that sets RLS session variables
- `app/core/security.py` — JWT validation against Cognito JWKS
- `get_tenant_context` dependency — extracts claims, sets PostgreSQL session vars
- Tests for cross-tenant isolation using the models created in this phase

---

## 2026-04-07 — Module 1 Phase 1: Backend Project Scaffolding

**Type:** End-of-session self-audit
**Author:** Claude Code
**Session scope:** Phase 1 — Backend scaffolding (FastAPI app, config, base models, Alembic, test skeleton)

### Self-Audit Findings

1. **New pattern introduced? YES**
   - Build backend: Hatchling with `packages = ["app"]` (required because the package
     dir is `app/`, not `reel48_backend/`)
   - Virtual environment: `backend/.venv/` created with `python3.11 -m venv .venv`
   - structlog configuration pattern: `ConsoleRenderer` in DEBUG, `JSONRenderer` in prod,
     with `merge_contextvars` for tenant context binding
   - **Action:** Added "Local Development Setup" section to `backend/CLAUDE.md`

2. **Existing pattern violated? YES — fixed**
   - The harness mandates `get_db_session` be imported from `app.core.dependencies`
     (the single canonical source for session de-duplication). Phase 1 initially placed
     it only in `app.core.database` without a re-export from `dependencies.py`.
   - **Action:** Created `app/core/dependencies.py` that re-exports `get_db_session` from
     `app.core.database`. Updated `tests/conftest.py` to import from the canonical path.
     All future code must import from `app.core.dependencies`, never `app.core.database`.

3. **New decision made? YES — minor**
   - Chose Hatchling as build backend (lightweight, Pydantic-friendly). Not significant
     enough for a standalone ADR — documented in `backend/CLAUDE.md` setup section.

4. **Missing guidance discovered? YES**
   - No guidance on Python virtual environment management or build backend
   - No `.env.example` template for backend environment variables
   - No structlog configuration pattern documented
   - **Action:** Added all three to `backend/CLAUDE.md`. Created `backend/.env.example`.

5. **Prompt template needed? NO**
   - Phase 1 scaffolding is a one-time task, not a recurring pattern.

### Files Updated
- **File:** `backend/CLAUDE.md`
  - **Change:** Added "Local Development Setup" section covering build backend (Hatchling),
    venv location, install command, run command, env var setup, and structlog config pattern.
  - **Reason:** No harness guidance existed for how to set up or run the backend locally.
  - **Impact:** Future sessions can activate the environment without guessing.

### Files Created
- **File:** `backend/.env.example`
  - **Change:** Template listing all required environment variables with placeholder values.
  - **Reason:** Settings loaded from env vars but no reference existed for which vars to set.
  - **Impact:** New developers (and new Claude Code sessions) can set up the backend quickly.

- **File:** `backend/app/core/dependencies.py`
  - **Change:** Created as the canonical re-export point for `get_db_session`.
  - **Reason:** Harness session-sharing rule requires single import path for de-duplication.
  - **Impact:** Prevents silent RLS bypass from importing `get_db_session` from the wrong path.

### Harness Health Metrics (Phase 1)
| Metric | Value | Notes |
|--------|-------|-------|
| Patterns violated | 1 | `get_db_session` import path — caught and fixed during audit |
| Harness gaps found | 3 | Build backend, .env template, structlog config |
| Rules added | 1 section | "Local Development Setup" in backend/CLAUDE.md |
| First-attempt accuracy | High | All patterns from harness followed correctly otherwise |

---

## 2026-04-06 — Pre-Production Harness Review #3: Final Fixes Before Module 1

**Type:** Pre-build review (final pre-production audit)
**Author:** Claude Code
**Findings:** 3 actionable issues fixed, 5 minor/deferred items noted

### Changes Made

1. **File changed:** `.claude/rules/database-migrations.md`
   **Change:** Added `invites` table as a special case in the "Identity & Company-Level Tables" section
   **Reason:** `invites` uses `CompanyBase` (no `sub_brand_id` column) but was not listed alongside `companies`, `sub_brands`, and `org_codes`. Without this, the standard two-policy RLS template would be applied, referencing a non-existent column.
   **Impact:** Prevents migration failure from applying sub-brand scoping policy to `invites` table.

2. **File changed:** `backend/CLAUDE.md`
   **Change:** Added `org_codes` table schema to Module 1 Table Schemas section
   **Reason:** `org_codes` is a Module 1 table but its schema was only in `prompts/self-registration.md`, not in the canonical schema section alongside `companies`, `sub_brands`, `users`, and `invites`.
   **Impact:** All five Module 1 tables are now defined in one place for implementation consistency.

3. **File changed:** `backend/CLAUDE.md`
   **Change:** Added `UNIQUE` constraint and note to `users.email` column definition
   **Reason:** Cognito enforces global email uniqueness per user pool, but the database schema didn't specify a matching constraint. Ambiguity could lead to a missing or incorrectly scoped constraint.
   **Impact:** Database constraint matches Cognito behavior; prevents duplicate email entries.

### Deferred Items (address during build)
- Rate limit dependency should be first `Depends()` parameter (ordering note)
- `.env.example` manifest to be created during Module 1 scaffolding
- Frontend `api.delete<T>` return type cleanup during frontend implementation

---

## 2026-04-06 — Pre-Build Harness Review #2: Inconsistency & Gap Fix (Pre-Module 1)

**Type:** Pre-build review (comprehensive cross-file consistency audit)
**Author:** Claude Code
**Findings:** 3 critical, 9 moderate, 4 minor across 6 files

### Changes Made

- **File:** `backend/CLAUDE.md` — `get_tenant_context` code
  - **Change:** Fixed `reel48_admin` crash — bracket access on `claims["custom:company_id"]` replaced with `.get()` + None-safe UUID parsing. Role extracted first.
  - **Reason:** CRITICAL — `reel48_admin` has no `custom:company_id` claim; bracket access raises `KeyError` or UUID cast fails
  - **Impact:** Platform admin authentication no longer crashes on first request

- **File:** `backend/CLAUDE.md` — new "Session Sharing Between Dependencies" section
  - **Change:** Documented FastAPI dependency de-duplication; added 4 rules about session identity
  - **Reason:** CRITICAL — no documentation that route's `db` and `get_tenant_context`'s `db` are the same session. Misunderstanding silently disables RLS.
  - **Impact:** Prevents accidental session duplication that would bypass all tenant isolation

- **File:** `prompts/crud-endpoint.md` — Product example
  - **Change:** Changed `soft delete (set is_active=false)` to `soft delete (set deleted_at=now())`
  - **Reason:** CRITICAL — contradicted the canonical `deleted_at` pattern in backend/CLAUDE.md Deletion Strategy
  - **Impact:** CRUD template now matches the authoritative soft-delete pattern

- **File:** `backend/CLAUDE.md` — new "Model Base Classes" section
  - **Change:** Defined `GlobalBase`, `CompanyBase`, `TenantBase` hierarchy with usage table
  - **Reason:** `org_codes`, `sub_brands`, `companies` don't fit `TenantBase`. Self-registration prompt said "use a custom base" but none existed.
  - **Impact:** Every Module 1 model has a clear, correct base class

- **File:** `.claude/rules/database-migrations.md` — new "Special Cases: Identity & Company-Level Tables" section
  - **Change:** Added RLS patterns for `companies` (id-based isolation) and `sub_brands` (company isolation only)
  - **Reason:** Only `org_codes` exception was documented. `companies` and `sub_brands` have different RLS shapes.
  - **Impact:** Claude Code applies correct RLS for all Module 1 tables

- **File:** `backend/CLAUDE.md` — project structure
  - **Change:** Added `invite.py` to models, schemas, routes; added `invite_service.py` to services; updated `base.py` description
  - **Reason:** Invite flow is Module 1 scope but had no model/schema/route listed
  - **Impact:** Invite feature has defined file locations before implementation

- **File:** `backend/CLAUDE.md` — new "Module 1 Table Schemas" section
  - **Change:** Defined full column schemas for `companies`, `sub_brands`, `users`, `invites` tables
  - **Reason:** These are the first tables built in Module 1 but had no defined column lists
  - **Impact:** Module 1 tables are fully specified before implementation begins

- **File:** `backend/CLAUDE.md` — auth.py description + new "Login & Token Refresh" section
  - **Change:** Clarified that login/token refresh are Amplify client-side (no backend endpoints). Updated `auth.py` description.
  - **Reason:** `auth.py` said "Login, register, token refresh" but login/refresh weren't in the unauthenticated endpoint list
  - **Impact:** Claude Code won't build unnecessary backend login endpoints

- **File:** `backend/CLAUDE.md` — TenantContext model
  - **Change:** Added `is_corporate_admin_or_above` and `is_manager_or_above` helpers. Added docstrings with usage guidance and WARNING on `is_admin`.
  - **Reason:** `is_admin` includes `sub_brand_admin` but 6+ operations are restricted to `corporate_admin+`
  - **Impact:** Prevents authorization bugs from using `is_admin` for corporate-only operations

- **File:** `frontend/CLAUDE.md` — TenantContext interface
  - **Change:** Changed `companyId: string` to `companyId: string | null` with comment
  - **Reason:** `reel48_admin` has no company; type didn't reflect this
  - **Impact:** TypeScript correctly models the null case for platform admins

- **File:** `backend/CLAUDE.md` — new "Rate Limiting Pattern" section
  - **Change:** Defined FastAPI dependency pattern with Redis, key structure, shared group, 429 response format
  - **Reason:** Both unauthenticated auth endpoints need rate limiting but no implementation pattern existed
  - **Impact:** Consistent rate limiting across all unauthenticated endpoints

- **File:** `backend/CLAUDE.md` — new "Company Creation & Default Sub-Brand Atomicity" section
  - **Change:** Documented that `company_service.create_company()` owns atomic company + default sub-brand creation
  - **Reason:** ADR-003 requires atomicity but no service was assigned ownership
  - **Impact:** Prevents companies from existing without a default sub-brand

### Gaps Remaining (Minor — addressable during implementation)
- `shared/types/` directory undocumented
- `harness-maintenance.md` glob pattern `**/CLAUDE.md` fires every session
- `sub_brands.is_default` column now defined in table schema (resolved)
- `catalogs` model deferred to Module 3

### Notes
This was the second pre-build review. The first (below) caught 7 issues; this one caught 16.
The increase reflects a deeper cross-file consistency analysis. All 3 critical issues and
9 moderate issues are now resolved. The harness is ready for Module 1 implementation.

---

## 2026-04-06 — Pre-Build Harness Review (Pre-Module 1)

**Type:** End-of-session self-audit (full harness consistency review)
**Author:** Claude Code

### Changes Made
- **File:** `prompts/harness-review.md`
  - **Change:** Updated ADR range from `001-006` to `001-007`
  - **Reason:** ADR-007 was added but harness-review prompt wasn't updated to include it
  - **Impact:** Post-module reviews now check all 7 ADRs

- **File:** `CLAUDE.md` (root)
  - **Change:** Fixed `Guide.docx` reference to `Reel48+ Harness Companion Guide.docx`
  - **Reason:** Filename in harness didn't match actual file on disk
  - **Impact:** Prevents confusion about non-application file inventory

- **File:** `CLAUDE.md` (root)
  - **Change:** Added `structlog` to backend technology stack
  - **Reason:** `backend/CLAUDE.md` specifies structlog for logging but root tech stack omitted it
  - **Impact:** Root tech stack is now complete and consistent with backend CLAUDE.md

- **File:** `docs/adr/006-stripe-for-invoicing.md`
  - **Change:** Updated "only API endpoint" language to "one of a small number" with reference to ADR-007
  - **Reason:** After ADR-007, there are three unauthenticated endpoints, not one
  - **Impact:** ADR-006 no longer contains outdated claim about webhook being the sole exception

- **File:** `frontend/CLAUDE.md`
  - **Change:** Added "API Naming Convention" section documenting snake_case (backend) to camelCase (frontend) transformation
  - **Reason:** No guidance existed on how API key naming transforms between backend and frontend
  - **Impact:** Prevents confusion during API integration; establishes that the API client handles key transformation

- **File:** `backend/CLAUDE.md`
  - **Change:** Added "Deletion Strategy" section establishing soft delete (user-facing entities) vs hard delete (transient data) defaults
  - **Reason:** CRUD prompt template asks "soft delete or hard delete" but no harness file provided a project-wide default
  - **Impact:** Claude Code applies consistent deletion patterns without needing per-entity guidance

- **File:** `backend/CLAUDE.md`
  - **Change:** Added `reel48_admin_token` fixture to conftest.py example
  - **Reason:** Test fixture examples included corporate_admin and brand_admin tokens but not the platform admin token
  - **Impact:** Claude Code includes reel48_admin in test setups for cross-company visibility testing

### Gaps Identified
- `.env.example` files — deferred to Module 1 setup
- Bulk order data model guidance — deferred to Module 5
- Invoice prompt template — deferred to Module 7 (per existing changelog note)

### Notes
- 7 files updated, 0 new files created
- All changes are minor consistency fixes and gap fills — no architectural changes
- Harness is now ready for Module 1 (Auth & Multi-Tenancy) development

---

## 2026-04-06 — Self-Registration: Sub-Brand Selection by Employee

**Type:** Reactive update (user requirement — employees should choose their sub-brand)
**Author:** Claude Code

### Changes Made
- **File:** `docs/adr/007-controlled-self-registration.md`
  - **Change:** Rewrote Decision section to describe a two-step registration flow where the employee selects their sub-brand after entering a valid org code. Replaced "Per-Sub-Brand Org Codes" alternative with "Default Sub-Brand Only (No User Choice)" alternative. Updated Consequences and Risks to reflect sub-brand visibility trade-off and removal of admin reassignment bottleneck. Removed the constraint about not exposing sub-brand names.
  - **Reason:** User requested employees choose their own sub-brand instead of being auto-assigned to the default sub-brand and waiting for admin reassignment.
  - **Impact:** Claude Code builds a two-step registration flow with sub-brand selection instead of default-sub-brand-only assignment.

- **File:** `.claude/rules/authentication.md`
  - **Change:** Rewrote "How Self-Registration Works" to describe the two-step flow (validate org code, then register with sub-brand selection). Updated Critical Rules to require server-side validation of submitted `sub_brand_id`. Updated rate limiting to cover both endpoints.
  - **Reason:** Registration flow fundamentally changed from single-step to two-step.
  - **Impact:** Claude Code generates both endpoints and validates sub-brand ownership server-side.

- **File:** `CLAUDE.md` (root)
  - **Change:** Updated Employee Onboarding Paths description to say employees "select their sub-brand" instead of being "auto-assigned to the default sub-brand."
  - **Reason:** Root CLAUDE.md must reflect the current onboarding behavior.
  - **Impact:** Every session knows self-registration includes sub-brand selection.

- **File:** `backend/CLAUDE.md`
  - **Change:** Updated Unauthenticated Endpoint Exceptions to list three endpoints (validate-org-code, register, stripe webhook) instead of two. Described the validate endpoint's role.
  - **Reason:** New endpoint added to the unauthenticated exception list.
  - **Impact:** Claude Code knows there are now three unauthenticated endpoints.

- **File:** `frontend/CLAUDE.md`
  - **Change:** Rewrote Self-Registration Note to describe the two-step UI flow: org code entry, then sub-brand dropdown + user details. Specified dropdown behavior for single-sub-brand companies.
  - **Reason:** Frontend registration page is fundamentally different with sub-brand selection.
  - **Impact:** Claude Code builds a two-step form with conditional sub-brand dropdown.

- **File:** `.claude/rules/api-endpoints.md`
  - **Change:** Added `POST /api/v1/auth/validate-org-code` as a third unauthenticated endpoint exception. Updated register endpoint description.
  - **Reason:** New unauthenticated endpoint for the two-step flow.
  - **Impact:** Claude Code won't add JWT requirements to the validate-org-code endpoint.

- **File:** `prompts/self-registration.md`
  - **Change:** Added ValidateOrgCodeRequest/Response schemas and the validate-org-code endpoint section (Step 1). Rewrote the register endpoint flow (Step 2) to accept and validate `sub_brand_id`. Rewrote frontend section to describe two-step form with conditional dropdown. Updated all test names and acceptance criteria.
  - **Reason:** Prompt template must match the revised two-step flow.
  - **Impact:** Claude Code building from this template produces the correct two-step implementation.

- **File:** `.claude/rules/testing.md`
  - **Change:** Updated functional tests to cover org code validation returning sub-brand list, registration with selected sub-brand, and cross-company sub-brand rejection. Updated security tests to cover both endpoints. Updated isolation test to verify user lands on selected sub-brand.
  - **Reason:** Test requirements must match the revised flow.
  - **Impact:** Claude Code includes sub-brand validation tests.

### Gaps Identified
- None. All files referencing default-sub-brand auto-assignment have been updated.

### Notes
- This changes the registration from a 1-endpoint flow to a 2-endpoint flow.
- The `POST /api/v1/auth/validate-org-code` endpoint is the third unauthenticated exception (after Stripe webhooks and the register endpoint itself).
- Sub-brand names are now visible to anyone with a valid org code. This is an intentional trade-off: sub-brand names are not sensitive, and the org code gates access.
- For companies with a single sub-brand, the sub-brand dropdown is hidden and that sub-brand is auto-selected — the UX is identical to the previous default-sub-brand behavior.

---

## 2026-04-06 — Controlled Self-Registration via Org Code (ADR-007)

**Type:** Feature addition (new onboarding path)
**Author:** Claude Code

### Changes Made

- **File:** `docs/adr/007-controlled-self-registration.md` (NEW)
  - **Change:** Created ADR documenting the decision to add org-code self-registration alongside the existing invite flow. Covers alternatives considered (email domain verification, batch CSV, per-sub-brand codes) and risks.
  - **Reason:** Invite-only onboarding creates friction for large companies with 500+ employees.
  - **Impact:** Claude Code understands WHY self-registration was added and won't suggest incompatible alternatives.

- **File:** `.claude/rules/authentication.md`
  - **Change:** Added "Self-Registration via Org Code" section with full flow documentation. Added `Generate/manage org codes` row to access matrix. Updated common mistakes to prohibit registration without org code OR invite (not just invite). Added `**/register*,**/org_code*` to globs.
  - **Reason:** Auth rule file is the primary reference for all onboarding flows.
  - **Impact:** Claude Code generates correct self-registration endpoints with rate limiting and no enumeration leakage.

- **File:** `CLAUDE.md` (root)
  - **Change:** Added "Employee Onboarding Paths" subsection under Multi-Tenancy (documents both invite and org-code paths). Updated Module 1 description to include self-registration. Added `007-controlled-self-registration.md` to ADR listing and `self-registration.md` to prompts listing in directory structure.
  - **Reason:** Root CLAUDE.md must reflect that two onboarding paths exist and both maintain RLS integrity.
  - **Impact:** Every session knows self-registration is part of Module 1.

- **File:** `backend/CLAUDE.md`
  - **Change:** Added `org_code.py` to models, schemas, routes, and services directories. Added `org_code_service.py` to services. Added `test_self_registration.py` to tests. Added "Unauthenticated Endpoint Exceptions" subsection documenting both Stripe webhook and registration as JWT-free endpoints.
  - **Reason:** Backend structure must include all new files for the feature.
  - **Impact:** Claude Code creates org code files in the correct locations.

- **File:** `frontend/CLAUDE.md`
  - **Change:** Added descriptive comment to `/register` route. Added "Self-Registration Note" section clarifying that post-login behavior is identical for invite and self-registered users.
  - **Reason:** Frontend must know the register page exists and that TenantContext is the same regardless of registration method.
  - **Impact:** Claude Code doesn't add unnecessary frontend logic to distinguish registration methods.

- **File:** `.claude/rules/api-endpoints.md`
  - **Change:** Expanded Exception 1 numbering, added Exception 2 documenting the self-registration endpoint as the second unauthenticated endpoint alongside Stripe webhooks.
  - **Reason:** The "tenant context from JWT" rule now has two exceptions, not one.
  - **Impact:** Claude Code won't incorrectly add JWT requirements to the registration endpoint.

- **File:** `.claude/rules/database-migrations.md`
  - **Change:** Added "Special Case: org_codes Table" section explaining that this table has company_id but no sub_brand_id, needs company isolation RLS but not sub-brand scoping, and has a public lookup path that bypasses RLS.
  - **Reason:** org_codes is the first table that breaks the "every tenant table has both isolation columns" pattern.
  - **Impact:** Claude Code generates correct RLS policies for this table without adding unnecessary sub-brand scoping.

- **File:** `.claude/rules/testing.md`
  - **Change:** Added "Self-Registration Test Requirements" section with functional tests (valid/invalid/inactive code, deactivation, role checks), security tests (rate limiting, no enumeration), and isolation tests (cross-company, default sub-brand).
  - **Reason:** Self-registration has unique security concerns (unauthenticated endpoint, rate limiting) that standard testing guidance doesn't cover.
  - **Impact:** Claude Code includes security and rate-limiting tests for registration.

- **File:** `prompts/self-registration.md` (NEW)
  - **Change:** Created prompt template covering: org_codes migration, OrgCode model, Pydantic schemas, registration endpoint, org code management endpoints, frontend register page, and full test suite with acceptance criteria.
  - **Reason:** Self-registration is a distinct feature pattern that benefits from a dedicated prompt template.
  - **Impact:** Future sessions building this feature get a complete, detailed starting prompt.

### Gaps Identified
- None. All harness files that reference authentication, onboarding, or unauthenticated endpoints have been updated.

### Notes
- This is the second feature to introduce an unauthenticated endpoint exception (after Stripe webhooks in ADR-006). Both are documented consistently across api-endpoints.md and backend/CLAUDE.md.
- The org_codes table is the first to use company_id without sub_brand_id, establishing a precedent for company-level-only tables.
- Total harness files: 26 (was 24; added ADR-007 and self-registration prompt template).

---

## 2026-04-06 — Pre-Production Consistency Audit (Pre-Stage 1)

**Type:** End-of-session self-audit (cross-file consistency check)
**Author:** Claude Code

### Issues Found and Fixed
- **File:** `.claude/rules/database-migrations.md` — **CRITICAL.** RLS company isolation template was missing the `IS NULL` / `= ''` bypass for `reel48_admin`. Would have caused all platform admin queries to fail. Updated to match the 3-condition pattern in root CLAUDE.md.
- **File:** `backend/CLAUDE.md` — **CRITICAL.** Same RLS template issue in the migration example code. Updated to match.
- **File:** `.claude/rules/api-endpoints.md` — **MODERATE.** Used vague "super-admin" terminology and didn't document that `/api/v1/platform/` endpoints may accept target `company_id` in request body. Replaced with explicit `reel48_admin` guidance and platform endpoint pattern.
- **File:** `frontend/CLAUDE.md` — **MINOR.** Had duplicate "new invoice" route under both `(authenticated)` and `(platform)` groups. Removed the `(authenticated)` version since only `reel48_admin` creates invoices.
- **File:** `CLAUDE.md` (root) — **MINOR.** Referenced `stripe_payment_status` column but the actual schema in `stripe-invoicing.md` uses `status`. Changed to `status` for consistency.
- **File:** `prompts/test-suite.md` — **MINOR.** Test fixture list was missing `reel48_admin_token`. Added it.
- **File:** `prompts/harness-review.md` — **MINOR.** ADR range referenced `001-005` but should be `001-006` after Stripe ADR was added. Updated.

### Gaps Identified
- None remaining. All cross-file inconsistencies resolved.

---

## 2026-04-06 — Reel48 Admin Role & Billing Model Revision (Pre-Stage 1)

**Type:** Reactive update (user correction — invoicing model was wrong)
**Author:** Claude Code

### Changes Made
- **File:** `CLAUDE.md` (root)
  - **Change:** Added `reel48_admin` as the top-level platform operator role. Expanded four-role model to five roles. Added RLS bypass mechanism (empty string `company_id`). Restructured invoicing conventions around three billing flows (assigned, self-service, post-window). Added per-catalog `payment_model` setting. Split API endpoints into platform admin vs client-facing.
  - **Reason:** User clarified that Reel48 (platform operator) creates and assigns invoices to client companies — not client admins. This required a dedicated platform admin role with cross-company access.
  - **Impact:** Claude Code now understands the full role hierarchy, knows reel48_admin bypasses RLS, and generates correct invoice creation patterns.

- **File:** `backend/CLAUDE.md`
  - **Change:** Updated `TenantContext` dataclass with `is_reel48_admin` property and `Optional[UUID]` company_id. Updated auth middleware to set empty string RLS variables for reel48_admin. Added `platform/` route directory for admin-only endpoints. Added `catalog_id`, `billing_flow`, `buying_window_closes_at`, `created_by` fields to invoice model.
  - **Reason:** Backend needs to handle the reel48_admin's null company_id without breaking RLS.
  - **Impact:** Claude Code generates correct middleware and route patterns for the platform admin.

- **File:** `frontend/CLAUDE.md`
  - **Change:** Added `reel48_admin` to `UserRole` type. Added entire `(platform)/` route group with dashboard, companies, catalogs (including approval page), and invoices management.
  - **Reason:** Platform admin needs a separate UI section for cross-company operations.
  - **Impact:** Claude Code generates the correct route structure for the platform admin portal.

- **File:** `.claude/rules/authentication.md`
  - **Change:** Added `reel48_admin` to Cognito custom attributes, role hierarchy, and access matrix. Expanded matrix to 17 action rows covering invoice, catalog, and analytics permissions at every scope level.
  - **Reason:** The access matrix must reflect the new top-level role and invoice-specific permissions.
  - **Impact:** Claude Code applies correct role checks for every endpoint.

- **File:** `.claude/rules/stripe-invoicing.md`
  - **Change:** Added "Who Creates Invoices" section (reel48_admin only). Added "Three Billing Flows" section. Rewrote invoice creation pattern to show reel48_admin creating invoices for target companies. Updated Critical Rules, Required Columns (added `billing_flow`, `buying_window_closes_at`, `catalog_id`, `created_by`), Test Cases (expanded to 15), and Common Mistakes (added 5 new anti-patterns).
  - **Reason:** Every section needed revision to reflect reel48_admin as invoice creator and three distinct billing flows.
  - **Impact:** Claude Code has complete, correct guidance for all three billing flows.

- **File:** `Reel48+ Harness Companion Guide.docx`
  - **Change:** Updated to v2.3. Updated role hierarchy references to five-role model. Updated rule file descriptions to reference reel48_admin and three billing flows.
  - **Reason:** Guide must reflect the revised role model and billing architecture.
  - **Impact:** Team members have accurate documentation.

### Gaps Identified
- None. All harness files have been updated to reflect the revised billing model.

### Notes
- This was the most significant structural change since initial harness creation. The original model assumed client admins created invoices; the corrected model has Reel48 as the sole invoice creator (except auto-generated self-service invoices).
- The `reel48_admin` role introduces the only RLS bypass in the system — uses empty string company_id to pass through all company isolation policies.

---

## 2026-04-06 — Stripe Invoicing & Client Billing (Pre-Stage 1)

**Type:** Reactive update (gap identified — missing core business functionality)
**Author:** Claude Code

### Changes Made
- **File:** `CLAUDE.md` (root)
  - **Change:** Added Stripe to technology stack. Added "Invoicing & Client Billing Conventions" section with Stripe object mapping, tenant isolation patterns, invoice lifecycle, webhook security, and API endpoints. Updated module build order to include Module 7 (Invoicing & Client Billing) and renumbered subsequent modules (now 9 total). Updated directory structure to include `stripe-invoicing.md` rule and `006-stripe-for-invoicing.md` ADR.
  - **Reason:** Invoicing is a critical revenue function that was entirely missing from the harness. Without this, Claude Code would have no guidance for Stripe integration, invoice data modeling, or the webhook authentication exception.
  - **Impact:** Claude Code now has complete guidance for building the invoicing module, including the one endpoint that breaks the JWT-auth-everywhere pattern (Stripe webhooks).

- **File:** `backend/CLAUDE.md`
  - **Change:** Added `invoice.py` to models, schemas, routes, and services directories. Added `webhooks.py` route, `stripe_service.py` service, and `test_invoices.py` to directory structure.
  - **Reason:** Backend needs invoice-specific files in each architectural layer.
  - **Impact:** Claude Code knows exactly where to create invoicing files.

- **File:** `frontend/CLAUDE.md`
  - **Change:** Added `/invoices` routes (list, new, detail) and invoice components (InvoiceTable, InvoiceDetail, CreateInvoiceForm) to component architecture.
  - **Reason:** Frontend needs invoice management pages and components.
  - **Impact:** Claude Code knows the frontend invoice page structure and component organization.

- **File:** `.claude/rules/authentication.md`
  - **Change:** Added invoice permissions to the role-based access matrix: Create/send invoices (admin only), View invoices (all) for corporate_admin, View invoices (brand) for admin + manager.
  - **Reason:** Invoicing has distinct role requirements not covered by the existing matrix.
  - **Impact:** Claude Code applies correct role checks on invoice endpoints.

- **File:** `.claude/rules/stripe-invoicing.md` (NEW)
  - **Change:** Created new rule file with globs for invoice/billing/stripe/webhook files. Covers Stripe API patterns, company-to-customer mapping, invoice creation from orders, webhook handling, data model, environment variables, and testing requirements.
  - **Reason:** Stripe integration introduces unique patterns (server-side only, webhook auth exception, cents-vs-dollars conversion, idempotent processing) that need dedicated rule guidance.
  - **Impact:** When Claude Code works on any invoice or Stripe file, it gets focused guidance specific to billing.

- **File:** `docs/adr/006-stripe-for-invoicing.md` (NEW)
  - **Change:** Created ADR documenting the choice of Stripe over custom invoicing, QuickBooks/Xero, and Square. Covers consequences, risks, and mitigation strategies.
  - **Reason:** Stripe is a significant technology decision affecting revenue, data model, and security patterns.
  - **Impact:** Claude Code understands WHY Stripe was chosen and won't suggest alternatives.

- **File:** `Reel48+ Harness Companion Guide.docx`
  - **Change:** Updated to v2.2. Added stripe-invoicing.md to rule file inventory, ADR 006 to ADR inventory, new files to complete inventory, updated total file count to 24.
  - **Reason:** Guide must reflect all harness additions.
  - **Impact:** Team members have accurate documentation of the full harness.

### New Module Added
- **Module 7: Invoicing & Client Billing** — positioned after Approval Workflows (depends on approved orders), before Analytics Dashboard (which now incorporates invoice/revenue data).

### Gaps Identified
- Invoice-related prompt template (`prompts/invoice-module.md`) may be needed when Module 7 build begins. Defer creation until then.

---

## 2026-04-06 — Rule File Frontmatter Fix (Pre-Stage 1)

**Type:** Reactive update
**Author:** Claude Code

### Changes Made
- **File:** All 6 rule files in `.claude/rules/`
  - **Change:** Added YAML frontmatter with `globs:` patterns for conditional activation
  - **Reason:** Rule files used comment-based activation patterns (`# Activates for: ...`) which Claude Code does not parse. Without proper `globs:` frontmatter, all rules load in every session regardless of which files are being edited, wasting context and diluting focused guidance.
  - **Impact:** Rules now activate only when Claude Code works on matching file paths (e.g., `database-migrations.md` only loads when editing files in `**/migrations/**` or `**/models/**`).

- **File:** `Reel48+ Harness Companion Guide.docx`
  - **Change:** Updated Section 3.1 to explain YAML frontmatter requirement for rule file activation.
  - **Reason:** The guide described rule activation conceptually but did not mention the required frontmatter format.
  - **Impact:** Team members understand that rule files require `globs:` frontmatter, not just descriptive comments.

### Glob patterns applied
| Rule File | Globs |
|-----------|-------|
| `database-migrations.md` | `**/migrations/**,**/models/**,**/*alembic*` |
| `api-endpoints.md` | `**/api/**,**/routes/**,**/endpoints/**` |
| `authentication.md` | `**/auth/**,**/security/**,**/middleware/auth*,**/login*,**/cognito*` |
| `testing.md` | `**/tests/**,**/test_*,**/*_test.py,**/*.test.ts,**/*.spec.ts` |
| `s3-storage.md` | `**/storage/**,**/upload*,**/s3*,**/assets/**,**/media/**` |
| `harness-maintenance.md` | `**/CLAUDE.md,**/.claude/**,**/docs/adr/**,**/prompts/**` |

---

## 2026-04-06 — Repo Structure Fix (Pre-Stage 1)

**Type:** Reactive update
**Author:** Claude Code

### Changes Made
- **File:** All harness files (CLAUDE.md, .claude/rules/*, backend/CLAUDE.md, frontend/CLAUDE.md, docs/*, prompts/*)
  - **Change:** Moved from `outputs/` subdirectory to the repository root
  - **Reason:** Claude Code auto-discovers CLAUDE.md and .claude/rules/ relative to the repo root. Files nested under `outputs/` would not be loaded automatically at session start.
  - **Impact:** Harness now activates correctly — CLAUDE.md loads every session, rule files trigger on matching file paths, and directory-level CLAUDE.md files load when working in backend/ or frontend/.

- **File:** `.gitignore`
  - **Change:** Updated `.claude/` ignore rule to use `.claude/*` with `!.claude/rules/` exception
  - **Reason:** The original `.claude/` rule ignored the entire directory including rule files. The new pattern ignores session data while tracking rule files in git.
  - **Impact:** Rule files are now version-controlled while session data remains excluded.

- **File:** `Reel48+ Harness Companion Guide.docx`
  - **Change:** Updated version to v2.1. Revised Section 9 (Getting Started Checklist) steps 1–2 to reflect that harness files are already at the repo root, not requiring a manual copy step.
  - **Reason:** The guide's setup instructions referenced the old workflow of copying files into a repo. Files now ship in the correct location.
  - **Impact:** New team members following the guide will not encounter misleading setup instructions.

### Notes
- No harness guidance content was changed — only file locations and documentation references.
- The `outputs/` directory has been removed entirely.

---

## 2026-04-06 — Initial Harness Creation (Pre-Stage 1)

**Type:** Initial setup
**Author:** Harness Owner

### Files Created
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Root harness — project-wide conventions, stack, multi-tenancy, API patterns |
| `frontend/CLAUDE.md` | Frontend conventions — Next.js, Cognito, components, state management |
| `backend/CLAUDE.md` | Backend conventions — FastAPI, SQLAlchemy, auth middleware, testing |
| `.claude/rules/database-migrations.md` | Rule: RLS policies, indexes, reversible migrations |
| `.claude/rules/api-endpoints.md` | Rule: tenant context from JWT, response format, role checks |
| `.claude/rules/authentication.md` | Rule: Cognito, JWT validation, invite flow, role hierarchy |
| `.claude/rules/testing.md` | Rule: three test categories, factories, coverage targets |
| `.claude/rules/s3-storage.md` | Rule: tenant-scoped paths, pre-signed URLs, upload validation |
| `.claude/rules/harness-maintenance.md` | Rule: self-audit, post-module review, changelog protocol |
| `docs/adr/TEMPLATE.md` | ADR template for future decisions |
| `docs/adr/001-shared-database-multi-tenancy.md` | Decision: shared DB over separate databases/schemas |
| `docs/adr/002-rls-over-application-isolation.md` | Decision: RLS over app-layer-only isolation |
| `docs/adr/003-default-sub-brand-pattern.md` | Decision: auto-create default sub-brand per company |
| `docs/adr/004-rest-before-graphql.md` | Decision: REST-first API design |
| `docs/adr/005-cognito-over-third-party-auth.md` | Decision: Cognito over Auth0/self-hosted |
| `prompts/crud-endpoint.md` | Template: building complete CRUD APIs |
| `prompts/new-table-migration.md` | Template: creating tables with RLS |
| `prompts/react-component.md` | Template: building React components |
| `prompts/test-suite.md` | Template: comprehensive test suites |
| `prompts/harness-review.md` | Template: post-module harness review |
| `docs/harness-changelog.md` | This file — change audit trail |

### Decisions Made
- Harness structure follows the Specification → Harness → Output model from the Build Process Plan
- All CLAUDE.md files include rich inline comments explaining WHY each section exists
- Rule files use file-path-based activation patterns
- ADRs document the 5 key architectural decisions from the Technical Architecture doc
- Harness maintenance protocol embedded directly in root CLAUDE.md so Claude Code reads it every session
- Three maintenance triggers defined: end-of-session audit, post-module review, reactive updates

### Baseline Metrics
- Total harness files: 21
- Total lines of guidance: ~2,800
- Modules completed: 0 (pre-build)
- Known gaps: None yet (first session hasn't happened)

### Next Steps
- Run pilot session (Week 3 of Stage 1) to validate the harness
- Adjust based on pilot results and log changes here
- Begin Stage 2 infrastructure provisioning using the harness

---

<!--
TEMPLATE FOR NEW ENTRIES (copy and fill in):

## {YYYY-MM-DD} — {Module Name / Session Description}

**Type:** {Session audit | Post-module review | Reactive update}
**Author:** {Name or role}
**Module:** {Module number and name, if applicable}

### Changes Made
- **File:** {path}
  - **Change:** {what was added/modified/removed}
  - **Reason:** {what prompted the change}
  - **Impact:** {what this prevents or enables}

### Gaps Identified
- {Description of gap and which upcoming module it affects}

### Metrics
- Mistakes caught by harness this session: {N}
- Mistakes NOT caught (harness gaps): {N}
- First-attempt acceptance rate: {%}

### Notes
{Any additional observations or context}

-->

## 2026-04-06 — IBM Carbon Design System Adoption (Pre-Build)

**Type:** Reactive update (architectural decision before Module 1 frontend build)
**Module:** N/A — cross-cutting frontend architecture change

### Changes Made
- **File:** `docs/adr/008-ibm-carbon-design-system.md` (NEW)
  - **Change:** Created ADR documenting the decision to adopt IBM Carbon over shadcn/ui, MUI, Fluent UI, and Headless UI
  - **Reason:** Reel48+ is ~70% dense admin tooling; Carbon's enterprise design language (data tables, workflow patterns, accessibility) is purpose-built for this use case
  - **Impact:** Claude Code understands why Carbon was chosen and will not suggest alternative design systems

- **File:** `CLAUDE.md` (root, Technology Stack + Directory Structure)
  - **Change:** Updated frontend styling from "Tailwind CSS" to Carbon as primary design system with Tailwind as utility layer; added SCSS and `src/styles/` to directory structure
  - **Reason:** Carbon requires SCSS for theming; Tailwind is retained for layout utilities
  - **Impact:** Claude Code will list correct dependencies when scaffolding the frontend project

- **File:** `frontend/CLAUDE.md` (Framework & Configuration, Component Locations, Styling Rules)
  - **Change:** Rewrote Framework & Configuration for Carbon+Tailwind hybrid; restructured `src/components/ui/` from custom primitives (Button, Input, Modal, DataTable) to Reel48+-specific compositions built from Carbon primitives; replaced Tailwind-only styling rules with Carbon-first hierarchy; removed cva/clsx references; added Carbon import examples and usage guidance
  - **Reason:** Carbon components replace custom UI primitives; Carbon's prop-based variant system replaces cva/clsx
  - **Impact:** Claude Code will import from `@carbon/react` for standard UI elements, will not create wrapper components, and will follow the correct styling hierarchy

- **File:** `prompts/react-component.md` (Styling section + Acceptance Criteria)
  - **Change:** Updated styling instructions to Carbon-first approach; added two acceptance criteria (uses Carbon where available, no Tailwind overrides on Carbon internals)
  - **Reason:** Component generation prompt must align with the new design system
  - **Impact:** Every generated component will follow Carbon-first conventions

### Gaps Identified
- Carbon + Next.js SCSS configuration (`next.config.js` sassOptions) will need to be documented in frontend/CLAUDE.md when the project is scaffolded
- Carbon Grid vs Tailwind Grid usage boundaries may need refinement after the first module is built

### Notes
Decision was made after evaluating IBM Carbon, shadcn/ui, MUI, Fluent UI, and Headless UI against the Reel48+ frontend requirements. Carbon won on enterprise UI/UX quality for data-dense workflows despite requiring a relaxation of the original Tailwind-only constraint.

---

## 2026-04-07 — Carbon Design System Harness Gap Review (Pre-Module 1)

### Summary
Reviewed the Carbon design system implementation across the harness for completeness
and accuracy before any frontend code is generated. Identified and closed 7 gaps that
would have caused incorrect or inconsistent code generation.

### Files Changed

- **File:** `.claude/rules/carbon-design-system.md` (**NEW**)
  - **Change:** Created dedicated rule file for Carbon conventions, activated by component/styling file paths. Covers: component selection, import patterns, icon usage, styling boundaries (Carbon vs Tailwind), CSS load order, SCSS/theming rules, and common mistakes.
  - **Reason:** Every other major domain (auth, database, API, testing, S3, Stripe) had an auto-activated rule file. Carbon had none, meaning no path-triggered reinforcement when editing component files.
  - **Impact:** Claude Code now receives Carbon-specific guidance automatically when working on any component, style, or layout file.

- **File:** `frontend/CLAUDE.md` (Theming section)
  - **Change:** Fixed outdated Carbon v10 token names (`$interactive-01` → `$interactive`, `$ui-background` → `$background`). Added `carbon-theme.scss` scaffold showing correct v11 `@use` module syntax. Added global stylesheet import order example.
  - **Reason:** Original references used Carbon v10 token names; `@carbon/react` is v11. Missing scaffold meant Claude Code would guess the SCSS structure.
  - **Impact:** Prevents broken SCSS compilation and incorrect token overrides from the first scaffolding session.

- **File:** `frontend/CLAUDE.md` (Framework & Configuration section)
  - **Change:** Added "Next.js Configuration for Carbon SCSS" subsection with `sassOptions`, `sass` devDependency requirement, and Dart Sass module system notes.
  - **Reason:** Without correct `next.config.mjs` settings, the first `npm run dev` would fail on SCSS imports.
  - **Impact:** Prevents immediate build failure during frontend scaffolding.

- **File:** `frontend/CLAUDE.md` (Responsive Design section)
  - **Change:** Replaced vague "page-level vs fine-grained" guidance with a concrete decision rule: Carbon Grid for outer page column structure, Tailwind for arranging items within a Carbon Column.
  - **Reason:** Original guidance was ambiguous; Claude Code would make inconsistent layout decisions.
  - **Impact:** Consistent layout approach across all pages and components.

- **File:** `frontend/CLAUDE.md` (new Tailwind-Carbon Token Alignment section)
  - **Change:** Added guidance on referencing Carbon CSS custom properties (`var(--cds-interactive)`) in `tailwind.config.ts`. Full mapping deferred to Module 1 scaffolding.
  - **Reason:** ADR-008 and frontend/CLAUDE.md both mentioned aligning tokens but never showed how.
  - **Impact:** Prevents color drift between Carbon components and Tailwind utility classes.

- **File:** `CLAUDE.md` (Harness Files Quick Reference table)
  - **Change:** Added row: `Design system / Carbon pattern → .claude/rules/carbon-design-system.md`
  - **Reason:** New rule file needs to be discoverable in the quick reference.
  - **Impact:** Future sessions know where to find and update Carbon conventions.

### Gaps Resolved from Previous Review
- ✅ "Carbon + Next.js SCSS configuration will need to be documented" — now documented
- ✅ "Carbon Grid vs Tailwind Grid usage boundaries may need refinement" — now refined with decision rule

### Deferred Items
- Full Tailwind-to-Carbon token mapping in `tailwind.config.ts` — deferred to Module 1 scaffolding when exact brand colors are known
- `prompts/frontend-scaffold.md` template — deferred to just before Module 1 begins

---

## 2026-04-07 — Supporting Document Sync (Post-Carbon Integration)

### Summary
Verified all supporting documents in the harness against the current state after
IBM Carbon design system integration. Found and fixed outdated references in the
companion guide and harness-review prompt template.

### Files Changed

- **File:** `Reel48+ Harness Companion Guide.docx`
  - **Change:** Updated version v2.4 → v2.5. Added ADR-008 (IBM Carbon) to Section 4.1 ADR Inventory table, Section 7.2 Supporting Files table, and Section 8 Complete File Inventory. Added `carbon-design-system.md` to Section 3.2 Rule File Inventory and Section 8. Updated frontend/CLAUDE.md description (Section 2.2) to mention Carbon. Updated ADR count (Seven → Eight), file count (27 → 30), ADR range (001-007 → 001-008). Updated Section 3.2 note about new rule files.
  - **Reason:** Companion guide was last updated at v2.4 (self-registration). Carbon additions from ADR-008 and the new rule file were not reflected.
  - **Impact:** Companion guide now accurately describes the full harness including Carbon design system coverage.

- **File:** `prompts/harness-review.md`
  - **Change:** Updated ADR range reference from "001-007" to "001-008" in the ADR Check step.
  - **Reason:** ADR-008 was added but the review template still referenced the old range.
  - **Impact:** Post-module harness reviews will now include ADR-008 in their currency check.

### Documents Verified (No Changes Needed)
- `backend/CLAUDE.md` — Current and consistent
- `prompts/crud-endpoint.md` — Current and consistent
- `prompts/new-table-migration.md` — Current and consistent
- `prompts/react-component.md` — Already updated for Carbon in prior session
- `prompts/self-registration.md` — Current and consistent
- `prompts/test-suite.md` — Current and consistent
- `docs/adr/001-008` — All ADRs current
- All `.claude/rules/*.md` — All current

---

## 2026-04-07 — Color Scheme Defined (Brand Identity Finalized)

### Summary
Defined the complete Reel48+ color system. Brand anchor is `#292c2f` (dark charcoal).
Primary interactive is teal (`#0a6b6b`), replacing Carbon's default IBM blue. A 10-color
fashion-inspired accent palette was created for charts, badges, and categories. All colors
are centralized in `carbon-theme.scss` with CSS custom properties bridged into Tailwind.

### Files Created
- **File:** `frontend/src/styles/carbon-theme.scss`
  - **Change:** Created as the single source of truth for all Reel48+ colors. Contains
    Carbon v11 token overrides (brand charcoal, teal interactive, teal info) and `:root`
    CSS custom properties for the accent palette (amethyst, azure, evergreen, garnet,
    coral, oxblood, navy, rose, saffron, midnight-teal) plus charcoal/teal scales.
  - **Impact:** Every future component session has definitive color values from day one.

- **File:** `frontend/tailwind.config.ts`
  - **Change:** Created with three color groups: Carbon token bridges (`var(--cds-...)`),
    charcoal/teal scales (`var(--r48-...)`), and accent palette. Zero raw hex — all
    values reference CSS custom properties from `carbon-theme.scss`.
  - **Impact:** Tailwind utilities (`bg-accent-amethyst`, `text-charcoal-900`, etc.)
    stay in sync with Carbon theme automatically.

### Files Updated
- **File:** `frontend/CLAUDE.md` (Theming section)
  - **Change:** Replaced placeholder theme scaffold with finalized color values. Added
    Brand Color System Overview table, Accent Palette table with Tailwind class names,
    and Color Usage Patterns section (header/sidebar, buttons, badges, charts, tables).
    Updated Tailwind-Carbon Token Alignment section to reference actual config.
  - **Reason:** Placeholder values (`#0f62fe`, "replace with actual brand values") were
    still present from pre-color-scheme era.
  - **Impact:** Claude Code has complete color guidance in the frontend CLAUDE.md.

- **File:** `.claude/rules/carbon-design-system.md` (Sass Module System section)
  - **Change:** Replaced `#0f62fe` placeholder in SCSS example with actual Reel48+ values
    (`#292c2f` brand, `#0a6b6b` teal interactive, `#0d8a8a` info). Added "Reel48+ Color
    System Quick Reference" subsection with key hex values, CSS variable names, accent
    palette list, and dark brand zone layout pattern.
  - **Reason:** Rule file is the primary reference when building components — having color
    values here prevents round-trips to the theme file.
  - **Impact:** Component authors get correct colors on first attempt.

- **File:** `prompts/react-component.md` (Styling section)
  - **Change:** Expanded the theme tokens line into a full "Color System" subsection with
    brand charcoal, primary interactive, status badge accent mappings, chart color order,
    selected row color, and the no-arbitrary-hex rule.
  - **Reason:** Template previously just said "reference brand colors from carbon-theme.scss"
    with no specifics.
  - **Impact:** Every component created from this template includes correct color usage.

- **File:** `docs/adr/008-ibm-carbon-design-system.md`
  - **Change:** Added "Addendum" section noting theming is finalized with specific values
    and pointing to `carbon-theme.scss` as the source of truth.
  - **Reason:** ADR discussed theming abstractly but didn't note when values were locked in.
  - **Impact:** Future readers know the color scheme is defined, not pending.

- **File:** `CLAUDE.md` (root — Technology Stack / Frontend section)
  - **Change:** Added brand color reference and pointer to `carbon-theme.scss` in the
    Design System line item.
  - **Reason:** Root CLAUDE.md is read every session but had no mention of the brand color
    or where to find the color definitions.
  - **Impact:** Every session starts with awareness that the color system exists and where
    to find it.

### Previously Deferred Items Now Resolved
- ✅ "Full Tailwind-to-Carbon token mapping in `tailwind.config.ts`" — now created with
  full mapping including accent palette
- ✅ Color scheme / brand identity — fully defined

---

## 2026-04-07 — Module 1 Phase 5: Self-Registration, Invite Consumption & Cognito Integration

### Session Summary
Phase 5 completes Module 1 (Auth & Multi-Tenancy) by building the two employee
onboarding flows (self-registration via org code, invite-based registration) and
connecting them to AWS Cognito for real user provisioning.

### New Files Created
- `app/services/cognito_service.py` — CognitoService wrapping boto3 admin APIs
- `app/core/rate_limit.py` — Redis-based rate limiting dependency
- `app/schemas/auth.py` — Auth request/response schemas
- `app/services/registration_service.py` — Registration business logic
- `app/api/v1/auth.py` — Three unauthenticated auth endpoints
- `tests/test_registration.py` — 23 tests across 6 test classes

### Files Modified
- `app/core/exceptions.py` — Added `RateLimitError`
- `app/services/user_service.py` — Cognito integration (create + soft-delete)
- `app/api/v1/users.py` — Inject `CognitoService` dependency
- `app/api/v1/router.py` — Wire auth router
- `tests/conftest.py` — Mock Cognito, no-op rate limit, org_code + invite fixtures

### End-of-Session Self-Audit

**1. New pattern introduced? YES**
- **External Service Integration Pattern:** CognitoService established the pattern for
  wrapping AWS services as injectable FastAPI dependencies with lazy boto3 imports and
  `app.dependency_overrides` for test mocking. Documented in backend CLAUDE.md.
- **Rate Limit Dependency Factory:** `check_rate_limit()` returns a dependency closure
  with graceful degradation. Updated the harness code example to match implementation.

**2. Existing pattern violated? YES (minor)**
- The harness rate limiting example used a simple inline function; the actual
  implementation used a factory pattern returning a closure. Updated backend CLAUDE.md
  to match the real implementation.
- The unauthenticated endpoints list had 3 entries; a 4th was added
  (`POST /api/v1/auth/register-from-invite`). Updated backend CLAUDE.md.

**3. New decision made? NO**
- All architectural decisions were already documented in ADR-007 and the plan.
  No new non-obvious choices were needed.

**4. Missing guidance discovered? YES**
- **Generic error responses:** No harness guidance on returning identical error
  messages for security-sensitive endpoints (preventing enumeration). Added as a
  note under "Unauthenticated Endpoint Exceptions" in backend CLAUDE.md.

**5. Prompt template needed? NO**
- The external service integration pattern is documented in CLAUDE.md. A dedicated
  prompt template is not needed until a second service (Stripe/SES) is built.

### Harness Files Updated
- **`backend/CLAUDE.md`:**
  - Updated "Rate Limiting Pattern" section with factory pattern + graceful degradation
  - Updated "Unauthenticated Endpoint Exceptions" to include 4th endpoint + generic errors
  - Added "External Service Integration Pattern" subsection under Service Layer Pattern
- **`docs/harness-changelog.md`:** This entry

### Test Results
- 116 tests pass (93 existing + 23 new)
- ruff: All checks passed
- mypy: No issues found in 46 source files

---

## 2026-04-08 — Module 3 Phase 4: Platform Admin Endpoints & Post-Module Harness Review

### Session Type: End-of-Module (Module 3 complete)

### What Was Built
- Platform admin endpoints under `/api/v1/platform/products/` and `/api/v1/platform/catalogs/`
- Product approval workflow: `submitted → approved → active` (with reject → draft)
- Catalog approval workflow: `submitted → approved → active → closed → archived` (with reject → draft)
- Catalog approval validates all products are approved/active before allowing catalog approval
- Cross-company list endpoints with optional `?status=` and `?company_id=` filters
- 18 new platform admin tests (all passing)

### End-of-Session Self-Audit

**1. New pattern introduced? YES**
- **Platform admin endpoint pattern:** `require_reel48_admin` + `resolve_current_user_id`
  for `approved_by` FK, no `_require_company_id` guard, cross-company service methods.
  → Added to `backend/CLAUDE.md` under "Platform Admin Endpoint Pattern".

**2. Existing pattern violated? NO**
- All platform endpoints follow the established conventions (ApiResponse wrapper,
  status codes, role checking via dependencies).

**3. New decision made? YES**
- **reel48_admin User records:** Platform admins need a User record in the database
  for `resolve_current_user_id` to work (setting `approved_by` FKs). The User model
  requires `company_id NOT NULL`, so reel48_admin users are associated with an internal
  "Reel48 Operations" company. The JWT still has no `company_id` claim (RLS bypass).
  This is not an ADR-level decision — it follows naturally from the existing model.

**4. Missing guidance discovered? YES**
- No guidance existed for testing platform admin endpoints that need `resolve_current_user_id`.
  → Added "Platform Admin (reel48_admin) Test Fixtures" section to `.claude/rules/testing.md`.

**5. Prompt template needed? NO**
- The platform endpoint pattern is documented in backend/CLAUDE.md. Future platform
  endpoints (invoicing, analytics) follow the same shape.

### Post-Module Review (Module 3 Complete)

**Pattern consistency:** All 4 phases (database, products CRUD, catalogs CRUD, platform admin)
follow consistent patterns: ApiResponse/ApiListResponse wrappers, PaginationMeta, service
layer for business logic, route layer for HTTP concerns.

**Rule effectiveness:** The `database-migrations.md` rule correctly guided RLS creation.
The `api-endpoints.md` rule prevented tenant ID acceptance as parameters. The `testing.md`
rule ensured isolation tests were written alongside functional tests.

**ADR currency:** All existing ADRs remain accurate. No informal reversals during Module 3.

**Cross-module alignment:** Module 3 endpoints match Module 1 and Module 2 patterns.
The `_require_company_id` guard is consistent across products.py, catalogs.py, and all
tenant-scoped route files. The `_create_user` / `_create_product` test helpers follow
the same factory pattern established in Module 1 tests.

**Gap analysis:** The platform admin endpoint pattern was the main gap. Now documented.

### Harness Files Updated
- **`backend/CLAUDE.md`:** Added "Platform Admin Endpoint Pattern" subsection
- **`.claude/rules/testing.md`:** Added "Platform Admin (reel48_admin) Test Fixtures" section
- **`docs/harness-changelog.md`:** This entry

### Test Results
- 211 tests pass (193 existing + 18 new)
- All Module 3 phases complete: database, products CRUD, catalogs CRUD, platform admin


---

## 2026-04-09 — Module 5, Phase 4: Bulk Order Status Transitions

### Session Summary
Added status transition endpoints for the bulk order lifecycle: submit, approve,
process, ship, deliver, and cancel. This mirrors the individual order lifecycle
(Module 4 Phase 4) with key differences: bulk orders start in `draft` (not `pending`),
require explicit submission with at least one item, and record `approved_by`/`approved_at`
on approval.

### What Was Built
- **Service layer:** 6 transition methods on `BulkOrderService` — `submit_bulk_order`,
  `approve_bulk_order`, `process_bulk_order`, `ship_bulk_order`, `deliver_bulk_order`,
  `cancel_bulk_order`
- **Route endpoints:** 6 POST endpoints at `/{bulk_order_id}/{action}` following the
  same pattern as `orders.py` status transitions
- **Tests:** 16 new tests covering:
  - 8 lifecycle happy-path tests (submit, submit-empty-fails, submit-non-draft-fails,
    approve, approve-non-submitted-fails, process, ship, deliver)
  - 5 cancel tests (draft, submitted, approved, processing-fails, delivered-fails)
  - 3 item-locking tests (cannot add/update/remove items after submit)

### End-of-Session Self-Audit
1. **New pattern?** No — status transition endpoints follow the same pattern established
   in Module 4 Phase 4. The `cancel_bulk_order` cancel authorization pattern (creator OR
   manager for draft, manager-only for submitted/approved) is consistent with Module 4.
2. **Existing pattern violated?** No — all endpoints use `require_manager`, `_require_company_id`,
   `resolve_current_user_id`, and `ApiResponse` wrapper consistently.
3. **New decision?** No — all lifecycle transitions follow the spec from the prompt.
4. **Missing guidance discovered?** No gaps encountered.
5. **Prompt template needed?** No — the status transition pattern is well-established.

### Harness Files Updated
- **`docs/harness-changelog.md`:** This entry (no other harness files needed updating)

### Test Results
- 45 bulk order tests pass (29 from Phases 2–3 + 16 new Phase 4)
- All Phase 4 tests green on first run


---

## 2026-04-09 — Module 9 Phase 4: Enhanced Employee Dashboard (Frontend)

### Session Overview
Built the enhanced employee dashboard frontend, transforming the stub dashboard into a
personalized engagement hub with notification and wishlist integration.

### What Was Built
- **TypeScript types:** `engagement.ts` — notification and wishlist response types
- **React Query hooks:** `useEngagement.ts` — 8 hooks for notifications (list, mark read,
  mark all read, unread count) and wishlists (list, add, remove, check)
- **NotificationBell component:** Header-integrated bell icon with unread count badge,
  dropdown panel showing recent notifications with type tags and timestamps, mark-all-read
  action, and click-to-navigate on notifications with `link_url`
- **Notifications page:** Full-page feed with pagination, unread/all toggle, type icons,
  empty state messaging
- **Wishlist page:** Product card grid with image, price, SKU, availability badges,
  remove button, and empty state with catalog browse CTA
- **Enhanced Dashboard:** Complete rewrite with role-aware layout:
  - Employee: welcome + profile completeness bar, 4 KPI cards (orders, catalogs, wishlist,
    notifications), recent orders with status badges, unread notifications, wishlist highlights
  - Manager/Admin: team overview cards (team orders, pending approvals, analytics link)
    rendered above the employee dashboard
- **Sidebar:** Added Notifications and Wishlist links for all roles
- **Header:** Integrated NotificationBell component

### End-of-Session Self-Audit
1. **New pattern?** Yes — the dashboard uses a role-aware composition pattern where the
   manager/admin view extends the employee view with additional cards. This pattern
   (conditionally rendering extra sections based on role) is documented implicitly by the
   code structure. No new harness rule needed — it follows the existing role-based
   rendering guidance in frontend CLAUDE.md.
2. **Existing pattern violated?** No — all components use `'use client'`, Carbon components
   for UI elements, Tailwind for layout, `next/image` for images, and the existing API
   client + React Query patterns.
3. **New decision?** No — all decisions follow the established Module 8 analytics dashboard
   patterns (hooks file, Carbon Tile/Tag components, KPI cards).
4. **Missing guidance discovered?** No gaps encountered.
5. **Prompt template needed?** No — the engagement UI patterns are standard.

### Harness Files Updated
- **`frontend/CLAUDE.md`:** Added `notifications/page.tsx` and `wishlist/page.tsx` to the
  routing structure. Added `engagement/NotificationBell.tsx` to the component directory listing.
- **`docs/harness-changelog.md`:** This entry.

### Verification
- TypeScript: `npx tsc --noEmit` — exit 0, no errors
- ESLint: `npx next lint` — exit 0, no warnings or errors


## 2026-04-10 — S3 Storage Service Phase 1

### Session Summary
Built the S3 Storage Service Phase 1: S3Service wrapper, storage API endpoints for
pre-signed URL generation, Pydantic schemas, test infrastructure updates (MockS3Service),
and 23 comprehensive tests.

### Files Created
- **`backend/app/services/s3_service.py`:** S3Service class wrapping boto3 for pre-signed
  URL generation. Includes `_CATEGORY_RULES` dict for file type validation per category
  (logos, products, catalog, profiles). Dependency factory `get_s3_service()` follows
  the same lazy-import pattern as CognitoService and StripeService.
- **`backend/app/schemas/storage.py`:** Pydantic schemas for upload/download URL requests
  and responses. Includes `file_extension` normalizer (adds dot prefix, lowercases).
- **`backend/app/api/v1/storage.py`:** Two tenant-scoped endpoints:
  - `POST /api/v1/storage/upload-url` — Generates pre-signed PUT URL (15 min expiry)
  - `POST /api/v1/storage/download-url` — Generates pre-signed GET URL (1 hour expiry)
    with tenant validation (company_id prefix check on s3_key)
- **`backend/tests/test_storage.py`:** 23 tests covering functional, isolation,
  authorization, and mock verification scenarios.

### Files Modified
- **`backend/app/core/config.py`:** Added `S3_BUCKET_NAME`, `CLOUDFRONT_DOMAIN`,
  `AWS_REGION` settings.
- **`backend/app/api/v1/router.py`:** Registered storage router.
- **`backend/tests/conftest.py`:** Added `MockS3Service` class and `mock_s3` autouse
  fixture. Mock replicates validation logic so tests reflect real behavior.
- **`backend/CLAUDE.md`:** Added S3Service to project structure, schemas, services,
  tests listings, and External Service Integration Pattern section.
- **`docs/harness-changelog.md`:** This entry.

### End-of-Session Self-Audit
1. **New pattern?** Yes — tenant-scoped file path validation on download URLs
   (company_id prefix check). Documented in backend CLAUDE.md under S3Service section.
2. **Existing pattern violated?** No — follows established External Service Integration
   Pattern (lazy import, dependency injection, mock in conftest).
3. **New decision?** No — all S3 conventions were already defined in
   `.claude/rules/s3-storage.md`. Implementation follows them faithfully.
4. **Missing guidance discovered?** No gaps encountered.
5. **Prompt template needed?** No — the storage endpoint pattern is straightforward.

### Test Results
- Backend: 655 passed (632 existing + 23 new storage tests), 0 failed


## 2026-04-10 — S3 Storage Service Phase 2: Product Image Management

### Summary
Added product image management endpoints that integrate S3 storage with the Product
model. Images are managed through dedicated POST/DELETE endpoints (not through the
general product update endpoint) with tenant validation on S3 keys.

### Files Created
None.

### Files Modified
- **`backend/app/services/product_service.py`:** Added `add_product_image()` and
  `remove_product_image()` methods with tenant validation, draft-only restriction,
  image limit (10), and S3 key path validation.
- **`backend/app/schemas/product.py`:** Added `ProductAddImage` schema with `s3_key` field.
- **`backend/app/api/v1/products.py`:** Added `POST /{product_id}/images` and
  `DELETE /{product_id}/images/{index}` endpoints. Both require admin role.
- **`backend/tests/test_products.py`:** Added 13 new tests across 4 test classes:
  `TestAddProductImage` (6 tests), `TestRemoveProductImage` (4 tests),
  `TestProductImageIsolation` (1 test), `TestProductImageAuthorization` (2 tests).
- **`backend/CLAUDE.md`:** Added "Product Image Management (S3 Storage Phase 2)" section
  documenting the endpoints, validation rules, and JSONB mutation pattern.
- **`docs/harness-changelog.md`:** This entry.

### End-of-Session Self-Audit
1. **New pattern?** Yes — JSONB array mutation pattern (copy-modify-reassign instead of
   in-place mutation). Documented in backend CLAUDE.md under the new section.
2. **Existing pattern violated?** No — follows established admin-only endpoint pattern
   with `require_admin` and `_require_company_id` guard.
3. **New decision?** No — S3 key validation rules were already defined in
   `.claude/rules/s3-storage.md` and the Phase 2 prompt.
4. **Missing guidance discovered?** No gaps encountered.
5. **Prompt template needed?** No — the image management pattern is product-specific.

### Test Results
- Backend: 37 product tests passed (24 existing + 13 new image tests), 0 failed


## 2026-04-13 — Link Stripe Invoice Flow + Searchable Company Selection

### Files Changed
- **`.claude/rules/stripe-invoicing.md`** — Added `linked` billing flow documentation
- **`backend/migrations/versions/010_add_linked_billing_flow.py`** — New migration adding `linked` to billing_flow CHECK constraint
- **`backend/app/schemas/invoice.py`** — Added `InvoiceLinkRequest` schema
- **`backend/app/services/invoice_service.py`** — Added `link_invoice()` method and `_map_stripe_status()` helper
- **`backend/app/api/v1/platform/invoices.py`** — Added `POST /link` endpoint
- **`frontend/src/hooks/usePlatformData.ts`** — New shared hooks for platform company/sub-brand queries
- **`frontend/src/app/(platform)/platform/catalogs/page.tsx`** — Replaced company Dropdown with searchable ComboBox
- **`frontend/src/app/(platform)/platform/invoices/page.tsx`** — Replaced Create Invoice modal with Link Invoice modal using searchable ComboBox
- **`frontend/src/types/invoices.ts`** — Added `linked` to BillingFlow type
- **`frontend/src/app/(platform)/platform/invoices/[id]/page.tsx`** — Updated billingFlowLabel
- **`frontend/src/app/(authenticated)/invoices/page.tsx`** — Updated billingFlowLabel
- **`frontend/src/app/(authenticated)/invoices/[id]/page.tsx`** — Updated billingFlowLabel
- **`backend/tests/test_invoices.py`** — Added TestLinkInvoice test class (9 tests)
- **`backend/tests/conftest.py`** — Enhanced MockStripeService.get_invoice() with richer data

### Changes
1. **New `linked` billing flow:** Allows reel48_admin to import existing Stripe invoices (including historical) into the platform by entering the Stripe invoice ID. System auto-fetches amount, status, URLs, and invoice number from Stripe.
2. **Searchable company selection:** Replaced all company selection dropdowns with Carbon ComboBox (searchable typeahead). Extracted `usePlatformCompanies()` and `usePlatformCompanySubBrands()` to shared hooks.
3. **Stripe status mapping:** Maps Stripe statuses (draft, open, paid, void, uncollectible) to local statuses. Supports historical invoices by extracting `paid_at` from `status_transitions`.

### Reason
User needs a simpler way to track invoices — entering a Stripe ID and assigning to a company, rather than building invoices from orders. Searchable company selection needed for scalability as the customer base grows.

### Impact
- Fourth billing flow available alongside assigned/self_service/post_window
- All platform admin company pickers are now searchable
- Historical invoice data can be imported for existing customers
