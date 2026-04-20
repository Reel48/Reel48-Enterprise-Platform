# Session D — Authoritative Harness Rewrite + Cognito & Stripe Cleanup

Paste this prompt into a fresh Claude Code session at the root of the Reel48+ Development Harness repo **after Sessions A and B have landed on `main`**.

---

You are executing **Session D** of the simplification refactor. Sessions 0 (harness teardown), A (backend), and B (frontend) have landed. The code now matches the target architecture: company-only tenancy, 4 roles, no catalog/products/orders/invoicing. Your job is to rewrite the harness **authoritatively** against the code that exists on disk — remove every "SIMPLIFICATION IN PROGRESS" banner, write ADRs 009 and 010, and do the final Cognito + Stripe cleanup.

## Before You Start — Required Reads

1. **Read the full plan:** `~/.claude/plans/yes-please-write-the-memoized-karp.md`. Focus on the "Session D" section.
2. **Read the project memory:** `~/.claude/projects/-Users-brayden-Desktop-Reel48--Development-Harness/memory/project_simplification_plan.md`.
3. **Survey the actual code on disk.** This is critical — the harness you write must match reality, not the plan's intent:
   - `ls backend/app/models/ backend/app/services/ backend/app/api/v1/ backend/app/api/v1/platform/ backend/app/schemas/`
   - `ls frontend/src/app/\(authenticated\)/ frontend/src/app/\(platform\)/platform/`
   - `ls frontend/src/components/features/`
   - Read `backend/app/core/tenant.py`, `backend/app/models/base.py`, `backend/app/api/v1/auth.py`, `backend/app/core/dependencies.py` to confirm the final shapes of `TenantContext`, `CompanyBase`, the auth flow, and middleware.
   - Read `frontend/src/types/auth.ts`, `frontend/src/lib/auth/context.tsx`, `frontend/src/components/layout/Sidebar.tsx`.
4. **Verify pre-conditions:** `git log -4 --oneline` should show recent commits for Session 0 (harness teardown), Session A (backend refactor), and Session B (frontend refactor). If any are missing, stop.

## Goal

After Session D:
- No file in `CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`, or `.claude/rules/*.md` carries a "SIMPLIFICATION IN PROGRESS" banner.
- No rule file contains a "TBD" stub — every rule that remains is authoritative.
- ADRs 009 and 010 exist. The "superseded by" banners on ADRs 003 and 006 point at real files.
- Grep for `sub_brand`, `subBrand`, `catalog`, `product_service`, `order_service`, `regional_manager`, `sub_brand_admin`, `stripe`, `invoice` across the repo: every remaining hit is intentional (legacy-role mapping shim, changelog entry, ADR rationale, Shopify TODO).
- Stripe webhook endpoint is disabled in the Stripe dashboard; `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` are removed from Vercel env vars.
- Vercel preview deploys successfully. A new user can register via org code and land on the dashboard as `company_admin`.

## Scope (from the plan)

### Step 1 — Rewrite the three CLAUDE.md files authoritatively
- `CLAUDE.md`: remove the top banner. Write the final §Multi-Tenancy (company-only), §Role Model (4 roles), §Module Build Order (Auth, Profiles, Notifications built; Shopify Integration TBD).
- `backend/CLAUDE.md`: remove the banner. Write the final §Model Base Classes (`GlobalBase` + `CompanyBase`), §TenantContext example (no `sub_brand_id`), §Auth Middleware example (`SET LOCAL app.current_company_id` only). Document the surviving models/services/routes — use the actual on-disk inventory, not aspirational lists.
- `frontend/CLAUDE.md`: remove the banner. Rewrite §Routing Structure to match the actual `frontend/src/app/` tree. Rewrite §Authentication (single-step registration, 4 roles). Update §Component Locations to match what's actually in `frontend/src/components/` after Session B.

### Step 2 — Finalize rule files in `.claude/rules/`
- `authentication.md`: final §Role Hierarchy (4 roles), §Role-Based Access Matrix, single-step self-registration flow. Note that `custom:sub_brand_id` still exists in Cognito but is ignored.
- `database-migrations.md`: final company-only RLS template. Document `GlobalBase` + `CompanyBase`. Document the surviving tables' actual schemas (pull from the migration file).
- `testing.md`: final fixture patterns (4 roles, cross-company isolation only). Document the surviving mocks (`MockCognitoService`, `MockS3Service`, `MockEmailService`).
- `api-endpoints.md`: final endpoint conventions. Unauthenticated list: only the two auth endpoints.
- `s3-storage.md`: final company-scoped path structure.
- `carbon-design-system.md` and `harness-maintenance.md`: confirm still accurate; minor edits only.

### Step 3 — ADRs
- Write `docs/adr/009-flatten-to-company-only-tenancy.md`. Document the decision: sub-brand complexity outweighed benefit; any tenant needing brand separation becomes its own company. Update the banner on ADR-003 to say "Superseded by ADR-009" (remove "pending").
- Write `docs/adr/010-defer-commerce-to-shopify.md`. Document the removal of in-app catalog/products/orders/invoicing. Shopify will own commerce end-to-end. Update the banner on ADR-006 to remove "pending".
- Edit `docs/adr/007-controlled-self-registration.md`: finalize the note about sub-brand selection being removed per ADR-009.

### Step 4 — Prompts
- Edit `prompts/self-registration.md` to the single-step flow.
- Edit `prompts/frontend-missing-pages.md` to list only the pages that still exist.
- Edit `prompts/full-platform-audit.md` to audit only the surviving modules.
- Write a new `prompts/shopify-integration.md` stub describing the future Shopify connect flow so future sessions have a starting point.
- Delete these three session prompts (`prompts/session-a-backend-simplification.md`, `prompts/session-b-frontend-simplification.md`, `prompts/session-d-harness-rewrite.md`) — they've served their purpose.

### Step 5 — Cognito + Stripe cleanup (operational, not code)
- **Cognito:** The `custom:sub_brand_id` attribute cannot be deleted from an existing Cognito user pool (AWS limitation). Leave it; the backend ignores it. If any existing test/dev users have old `custom:role` values (`corporate_admin`, `sub_brand_admin`, `regional_manager`), write a one-off AWS CLI script to update them via `admin-update-user-attributes`. Document the exact command in the session notes; do NOT automate it in application code.
- **Stripe:**
  - Stripe Dashboard → disable the webhook endpoint that pointed at `/api/v1/webhooks/stripe`.
  - Vercel → remove `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` from project env vars in every environment (Production, Preview, Development).
  - AWS Secrets Manager (if used) → remove the Stripe secrets from any secret manager entry.
  - Do NOT rotate the Stripe API key. Do NOT delete the Stripe account — leave it intact in case it's reused later.
- **If the legacy role normalizer shim** (added in Session A's `get_tenant_context`) is ready to be removed because all dev users are updated, remove it and delete the corresponding frontend shim in `frontend/src/lib/auth/context.tsx`. Otherwise, leave both shims with a dated TODO.

### Step 6 — Changelog + commit
- Append a dated entry to `docs/harness-changelog.md` for Session D with the file list + ADR summaries. (Session 0's entry is already there.)
- Commit with message:
  ```
  chore(harness): rewrite harness for simplified architecture; add ADRs 009, 010
  ```

## Guardrails

- **Do not** leave any "TBD" or "SIMPLIFICATION IN PROGRESS" marker anywhere in the harness when you commit.
- **Do not** document sections aspirationally. If `backend/app/services/` has 8 files, document 8 files — not 10, not 6.
- **Do not** invent behavior. If you're unsure how the final code works, read the code before writing the rule.
- **Do not** touch production Stripe secrets without user confirmation. Ask before running any CLI that modifies Vercel env or Stripe dashboard state.

## Working Style

- Use `TodoWrite` to track progress.
- Read actual code files to verify every rule you write.
- For each harness file: read current contents → note what's accurate → rewrite the rest.
- Commit once at the end.

## Verification Before Committing

```bash
# No banners or TBD stubs
grep -rn "SIMPLIFICATION IN PROGRESS\|^> ⚠\|TBD" CLAUDE.md backend/CLAUDE.md frontend/CLAUDE.md .claude/rules/

# ADRs exist
ls docs/adr/009-flatten-to-company-only-tenancy.md docs/adr/010-defer-commerce-to-shopify.md

# Banners on superseded ADRs no longer say "pending"
grep -rn "pending" docs/adr/

# No residual sub-brand / catalog / stripe references in production code
grep -rn "sub_brand_id\|subBrandId\|import stripe\|StripeService" backend/ frontend/src/ | grep -v "test\|# legacy"

# Repo builds + tests pass
cd backend && pytest
cd frontend && npm run typecheck && npm run build && npm run test
```

## Final Smoke Test

Deploy to Vercel preview. Register a new user via org code. Confirm they:
1. Receive the Cognito verification email.
2. Can verify and log in.
3. Land on `/dashboard` with the correct role-scoped sidebar.
4. Can reach their profile, edit it, and upload a profile photo (S3 still works).
5. Cannot navigate to any removed page (`/catalog`, `/orders`, `/invoices`, etc.) — should 404.

## Stop Conditions

- Stripe credentials need to be removed from production and you don't have confirmation to do so.
- You discover the actual code diverges from the plan's assumptions — stop and summarize the divergence before rewriting rules that would codify the divergence.
- Any verification step fails.

Once Session D lands, the simplification refactor is complete. Update `project_simplification_plan.md` memory to mark the refactor as done and remove the stale warnings from the other memory entries.
