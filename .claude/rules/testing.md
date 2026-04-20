# Rule: Testing Standards

> ⚠ **SIMPLIFICATION IN PROGRESS** — this file has been stripped as part of the refactor
> documented at `~/.claude/plans/yes-please-write-the-memoized-karp.md`. Previous content
> documented cross-sub-brand isolation tests, Stripe webhook testing, `MockStripeService`,
> and 5-role fixture patterns that are all being removed. Do **not** write cross-sub-brand
> tests. Do **not** reference `MockStripeService`. Cross-company isolation tests remain required.

# Activates for: **/tests/**, **/test_**, **/*_test.py, **/*.test.ts, **/*.spec.ts

## Mandatory Test Categories

Every module MUST include:

1. **Functional tests** — happy path + error cases.
2. **Cross-company isolation tests** — Verify Company A cannot see Company B's data. This is
   the single most important test category for a multi-tenant system.
3. **Authorization tests** — Verify role restrictions work. Test unauthenticated (401),
   insufficient role (403), and correct role (200).

## Backend Conventions (pytest)
- Naming: `test_{action}_{condition}_{expected_result}`
- `asyncio_mode = "auto"` in pyproject.toml.
- Use a separate test database; roll back after each test.
- Use `create_test_token()` helper to generate JWTs.

## Dual Database Sessions (unchanged)
- `admin_db_session` — connects as `postgres` (superuser, bypasses RLS). Used for seeding
  test data and for the `client` fixture's `get_db_session` override.
- `db_session` — connects as `reel48_app` (non-superuser, RLS enforced). Used for isolation
  tests.

## Isolation Test Pattern (use real UUIDs, never empty strings)
```python
async def _set_tenant_context(session, company_id):
    await session.execute(text(f"SET LOCAL app.current_company_id = '{company_id}'"))
```
PostgreSQL does NOT guarantee short-circuit evaluation of OR in RLS policies. Passing an empty
string for `company_id` can cause `::uuid` cast errors. Always pass a real UUID.

## External Service Mock Pattern
Mock external services via a `MockXxxService` class in conftest.py + an autouse fixture that
registers it via `app.dependency_overrides`. Surviving mocks: `MockCognitoService`, `MockS3Service`,
`MockEmailService`.

## Frontend Conventions (Vitest + RTL)
- Naming: `it('should {expected behavior} when {condition}')`
- Prefer accessible queries (`getByRole`, `getByLabelText`) over `getByTestId`.
- Mock API with MSW at the network level.

## Coverage Targets (unchanged)
- Backend: 80%+ overall, 100% on auth middleware + RLS-related code.
- Frontend: 70%+ on components with business logic.

## What Is In Flux (TBD)
- Role fixture names (4-role target). Session A renames fixtures. Session D documents the final set.
- Test file list. ~14 test files are being deleted in Session A (products, catalogs, orders,
  bulk_orders, approvals, invoices, wishlists, sub_brands). Do not try to fix failures in
  those files — they are slated for deletion.

## Common Mistakes to Avoid
- ❌ Testing only the happy path.
- ❌ Skipping isolation tests ("RLS will handle it").
- ❌ Sharing mutable state between tests.
- ❌ Hardcoding UUIDs instead of generating them.
- ❌ Omitting trailing slash on list endpoint URLs (causes 307 redirect).
- ❌ Writing cross-sub-brand isolation tests (sub-brand dimension is being removed).
