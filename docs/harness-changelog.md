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
