# Session A — Backend Teardown + Schema Flatten

Paste this prompt into a fresh Claude Code session at the root of the Reel48+ Development Harness repo.

---

You are executing **Session A** of the simplification refactor. Session 0 (harness teardown) has already landed on `main` — every CLAUDE.md file and `.claude/rules/*.md` now carries a "SIMPLIFICATION IN PROGRESS" banner pointing at the plan. Your job is to tear down the backend code to match.

## Before You Start — Required Reads

1. **Read the full plan:** `~/.claude/plans/yes-please-write-the-memoized-karp.md`. Focus on the "Session A" section; skim the others for context.
2. **Read the project memory:** `~/.claude/projects/-Users-brayden-Desktop-Reel48--Development-Harness/memory/project_simplification_plan.md`.
3. **Read the current harness:** `CLAUDE.md`, `backend/CLAUDE.md`, and every file in `.claude/rules/`. These describe the current (post-Session-0) state, not the pre-refactor architecture. Do not refer to commit history for guidance on what to build.
4. **Verify pre-conditions:** Run `git log -1 --oneline` — the HEAD commit should be `chore(harness): neutralize stale guidance before simplification refactor`. If it's not, stop and confirm with the user.

## Goal

After Session A:
- `cd backend && alembic upgrade head` applies cleanly against a fresh dev DB.
- `cd backend && pytest` passes.
- `cd backend && uvicorn app.main:app --reload` boots without import errors.
- `curl localhost:8000/openapi.json | jq '.paths | keys'` shows only the surviving routes (auth, companies, users, invites, org_codes, employee_profiles, notifications, storage, platform/companies, platform/analytics).
- `grep -r "import stripe\|stripe\." backend/` returns zero hits.

## Scope (from the plan)

You are implementing **Session A, Steps 1–3** of the plan. The summary:

1. **New migration `011_simplify_drop_catalog_orders_invoices_sub_brand.py`** (or, preferred: rewrite migrations 001–002 and drop 003–010 if the user is willing to reset the dev DB — ask before choosing). Drops the `invoices` table; `wishlists`/`approval_*`; all order/bulk-order tables; all catalog/product tables; `sub_brand_id` columns from remaining tenant tables; `invites.target_sub_brand_id`; `sub_brands` table; `companies.stripe_customer_id`. Migrates role strings: `corporate_admin`/`sub_brand_admin` → `company_admin`, `regional_manager` → `manager`. Drop RLS policies **before** dropping columns they reference. Drop tables in FK-safe order.

2. **Delete backend files** — models, services, schemas, routes, platform routes, tests. Exact file list is in the plan under Session A Step 2. Do not edit these files; just `git rm` them.

3. **Edit surviving backend files.** Full list in the plan under Session A Step 3. Highlights:
   - `backend/app/models/base.py`: delete `TenantBase`; every surviving model inherits from `CompanyBase`. Drop `stripe_customer_id` from `companies`.
   - `backend/app/core/tenant.py`: remove `sub_brand_id` field from `TenantContext`; replace role properties with the 4-role set (`is_reel48_admin`, `is_company_admin_or_above`, `is_manager_or_above`).
   - `backend/app/core/dependencies.py` + `app/middleware/tenant.py`: stop reading `custom:sub_brand_id`; remove `SET LOCAL app.current_sub_brand_id` calls.
   - `backend/app/core/config.py` + `.env.example` + `backend/pyproject.toml`: remove Stripe settings and the `stripe` dependency.
   - `backend/app/services/cognito_service.py`: stop writing `custom:sub_brand_id` (the attribute stays in the user pool — AWS can't delete it — but we ignore it).
   - `backend/app/services/registration_service.py` + `app/api/v1/auth.py`: collapse `validate-org-code` and `register` to single-step (no sub-brand list, no sub-brand selection).
   - `backend/app/services/analytics_service.py`: gut. Keep only user/company counts. Delete everything tied to removed tables.
   - `backend/app/api/v1/router.py`: remove every deleted module's import + include_router.
   - `backend/tests/conftest.py`: simplify fixtures (4 roles, no sub-brand fixtures, no `MockStripeService`). Update the `reel48_app` role grants list to match surviving tables.
   - Surviving tests: remove sub-brand fixtures, `sub_brand_admin`/`regional_manager` references, Stripe assertions. Delete tests for removed modules (see plan).

## Guardrails

- **Do not** reintroduce `sub_brand_id` on any remaining table or endpoint.
- **Do not** keep "for compatibility" shims for the removed systems — no empty `invoice_service.py` stubs, no re-exports. Delete fully.
- **Do not** touch the frontend in this session. That's Session B.
- **Do not** touch harness files in this session beyond what pairs with a code change. Session D rewrites the harness authoritatively.
- **Do** add a temporary server-side role normalizer in `get_tenant_context` that maps legacy role strings (`corporate_admin` / `sub_brand_admin` → `company_admin`, `regional_manager` → `manager`) so dev users with stale JWTs still work. Leave a TODO comment referencing the plan's "Existing dev users may have the old role strings" risk.
- **Ask first** before choosing between the two migration approaches in the plan (single squash-and-flatten migration vs. rewriting 001–002 and dropping 003–010).

## Working Style

- Use `TodoWrite` to track progress. Plan the work before you start.
- Commit once at the end with message:
  ```
  refactor(backend): flatten to company-only tenancy; remove catalog/orders/approvals/invoicing
  ```
- Do not push. The user reviews locally.

## Verification Before Committing

Run each of these and paste the result to the user if any fail:

```bash
cd backend
# Drop and recreate dev DB (confirm with user first if DB name isn't obvious)
alembic upgrade head
pytest
uvicorn app.main:app --reload  # Check boot then Ctrl+C
curl -s localhost:8000/openapi.json | jq '.paths | keys'
grep -rn "import stripe\|from stripe\|stripe\." app/ tests/ migrations/ | grep -v ".pyc"  # expect zero
grep -rn "sub_brand_id\|SubBrand\|sub_brand_admin\|regional_manager" app/ migrations/ | grep -v "legacy\|# TODO\|# mapped from"  # only intentional hits (role normalizer)
```

## Stop Conditions

Stop and ask the user before proceeding if:
- The migration strategy (squash vs rewrite) needs confirmation.
- Surviving tests fail in a way that reveals a logic issue, not just a fixture cleanup.
- You discover the codebase has diverged from what the plan assumes (e.g., a file is missing or has been renamed).

Session B (frontend) and Session D (harness rewrite + Cognito cleanup) run in separate sessions after this one lands.
