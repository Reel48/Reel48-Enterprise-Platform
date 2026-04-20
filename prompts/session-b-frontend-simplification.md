# Session B — Frontend Teardown + Role Simplification

Paste this prompt into a fresh Claude Code session at the root of the Reel48+ Development Harness repo **after Session A has landed on `main`**.

---

You are executing **Session B** of the simplification refactor. Session 0 (harness teardown) and Session A (backend teardown) have already landed. Your job is to bring the frontend in line with the trimmed API surface.

## Before You Start — Required Reads

1. **Read the full plan:** `~/.claude/plans/yes-please-write-the-memoized-karp.md`. Focus on the "Session B" section.
2. **Read the project memory:** `~/.claude/projects/-Users-brayden-Desktop-Reel48--Development-Harness/memory/project_simplification_plan.md`.
3. **Read the current harness:** `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/carbon-design-system.md`, `.claude/rules/authentication.md`. These describe the post-Session-0 state. Do not refer to commit history for guidance on what to build.
4. **Verify pre-conditions:**
   - Run `git log -2 --oneline`. The recent two commits should be the Session 0 harness teardown and the Session A backend refactor (subject starts with `refactor(backend): flatten to company-only tenancy...`). If Session A has not landed, stop.
   - Run `cd backend && curl -s localhost:8000/openapi.json | jq '.paths | keys'` (or inspect `app/api/v1/router.py`) to confirm the surviving API surface. Removed endpoints should 404.

## Goal

After Session B:
- `cd frontend && npm run typecheck` passes.
- `cd frontend && npm run build` succeeds.
- `cd frontend && npm run test` passes.
- `cd frontend && npm run dev` — a user can log in, reach the dashboard, see the simplified sidebar, view their profile, and view the Products "Coming Soon" placeholder. Every remaining sidebar link renders a real page; none 404.

## Scope (from the plan)

**Step 1 — Delete page directories** (entire trees):
- `frontend/src/app/(authenticated)/catalog/`
- `frontend/src/app/(authenticated)/orders/`
- `frontend/src/app/(authenticated)/bulk-orders/`
- `frontend/src/app/(authenticated)/wishlist/`
- `frontend/src/app/(authenticated)/invoices/`
- `frontend/src/app/(authenticated)/admin/approvals/`
- `frontend/src/app/(authenticated)/admin/approval-rules/`
- `frontend/src/app/(authenticated)/admin/brands/`
- `frontend/src/app/(platform)/platform/catalogs/`
- `frontend/src/app/(platform)/platform/invoices/`

**Step 2 — Delete components:**
- `frontend/src/components/features/catalog/` (entire dir).
- These analytics components (tied to dropped domains): `SpendBySubBrandTable`, `TopProductsTable`, `SizeDistribution`, `OrderStatusBreakdown`, `ApprovalMetricsCards`, `InvoiceSummaryCards`, `SpendKPICards`, `SpendOverTimeChart`, `RevenueByCompanyTable`. Keep `DateRangeFilter` and `PlatformOverviewCards` (trim the latter to user/company counts only).

**Step 3 — Edit surviving frontend files** (full list in the plan). Highlights:
- `frontend/src/types/auth.ts`: `UserRole = 'reel48_admin' | 'company_admin' | 'manager' | 'employee'`; remove `subBrandId` from `TenantContext`.
- `frontend/src/lib/auth/context.tsx`: stop reading `custom:sub_brand_id`. Map legacy roles on the client (`corporate_admin`/`sub_brand_admin` → `company_admin`, `regional_manager` → `manager`). Leave a TODO noting the shim can be removed after all dev Cognito users have been updated.
- `frontend/src/components/layout/Sidebar.tsx`: rewrite nav arrays for the 4 roles. See the plan for the exact link list. Remove every catalog/orders/bulk-orders/wishlist/invoices/brands/approvals/approval-rules link.
- `frontend/src/app/(public)/register/page.tsx`: collapse to a single-step form (org code + email + name + password). Call `POST /api/v1/auth/register` with all fields on one submit.
- `frontend/src/app/(authenticated)/admin/users/page.tsx` + `_hooks.ts`: remove sub-brand columns, sub-brand filters, `target_sub_brand_id` on invites. Role dropdown: `company_admin` / `manager` / `employee`.
- `frontend/src/app/(authenticated)/dashboard/page.tsx`: remove order/bulk-order/approval-queue/invoice/catalog sections. Keep welcome card, profile onboarding nudge, and a "Shopify integration coming soon" card for admins.
- `frontend/src/app/(authenticated)/admin/analytics/page.tsx` + `(platform)/platform/analytics/page.tsx`: minimal "Users & companies overview".
- `frontend/src/app/(platform)/platform/companies/[id]/page.tsx` + `_hooks.ts`: remove sub-brand tab/list. Keep company overview + user list.
- `frontend/src/app/(authenticated)/settings/page.tsx`: rename from "Brand Settings" to "Company Settings". Remove sub-brand sections.
- `frontend/src/hooks/usePlatformData.ts`: delete hooks for removed domains.
- `frontend/src/app/(authenticated)/products/page.tsx`: **leave as-is** — this is the Shopify placeholder.
- Environment: double-check `frontend/src/lib/` and `.env.example` for any `NEXT_PUBLIC_STRIPE_*` vars and remove them.
- Tests in `frontend/src/__tests__/`: delete sidebar assertions for removed links, delete analytics tests for removed components, update auth/protected-route tests for new roles.

## Guardrails

- **Do not** reintroduce sub-brand concepts in any type, form, or route.
- **Do not** keep dead link entries in the sidebar "for later" — delete them. Shopify routes can be added later under a different path.
- **Do not** touch the backend. Session A is complete.
- **Do not** rewrite `frontend/CLAUDE.md` authoritatively. Session D does that. During this session, you may edit the routing or component sections as you go, but leave the top-of-file "SIMPLIFICATION IN PROGRESS" banner in place.
- **Do** verify `npm run build` after major deletions — the TS compiler will flag dangling imports fast.

## Working Style

- Use `TodoWrite` to track progress.
- Commit once at the end with message:
  ```
  refactor(frontend): remove catalog/orders/approvals/invoices pages; collapse to 4 roles
  ```

## Verification Before Committing

```bash
cd frontend
npm run typecheck
npm run build
npm run test
# Then dev-server smoke test — log in as each role if possible, click every remaining sidebar link
npm run dev
```

Also grep the frontend for leftover references (some will be intentional in tests or the legacy-role shim):
```bash
grep -rn "sub_brand\|subBrand\|SubBrand\|stripe\|Stripe" frontend/src
```

## Stop Conditions

- The backend is exposing endpoints the frontend didn't expect removed → verify against `openapi.json`; if the backend is wrong, stop and flag it.
- The Carbon theme or any shared component breaks in a way that isn't a straightforward import fix.
- A test fails in a way that reveals a logic issue beyond fixture cleanup.

Session D (authoritative harness rewrite, ADRs 009/010, Cognito + Stripe env cleanup, Vercel deploy) runs in a separate session after this one lands.
