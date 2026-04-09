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
