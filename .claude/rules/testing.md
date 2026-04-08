---
globs: "**/tests/**,**/test_*,**/*_test.py,**/*.test.ts,**/*.spec.ts"
---

# Rule: Testing Standards
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This rule activates when Claude Code is working on test files. It         ║
# ║  enforces testing standards, especially the CRITICAL requirement of        ║
# ║  cross-tenant isolation tests for every module.                            ║
# ║                                                                            ║
# ║  WHY THIS RULE?                                                            ║
# ║                                                                            ║
# ║  Tests are your safety net. For a multi-tenant platform, they're doubly    ║
# ║  important because you need to verify not just "does the feature work?"    ║
# ║  but "does data stay isolated between tenants?" Without explicit           ║
# ║  guidance, Claude Code will write functional tests but skip isolation      ║
# ║  tests — which are the ones that catch the most dangerous bugs.            ║
# ║                                                                            ║
# ║  EXTRA RULE (Recommended addition not in the original plan):               ║
# ║  This file also covers test data factories, which make it fast and easy    ║
# ║  to create realistic test data without duplicating setup code.             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Activates for: **/tests/**, **/test_**, **/*_test.py, **/*.test.ts, **/*.spec.ts

## Mandatory Test Categories

Every module MUST include all three categories of tests:

### 1. Functional Tests
- Verify the feature works as specified
- Cover happy path AND error cases
- Example: "Creating a product with valid data returns 201 and the product object"

### 2. Isolation Tests (CRITICAL — most important)
- **Cross-company test:** Verify Company A cannot access Company B's data
- **Cross-sub-brand test:** Verify Sub-Brand X cannot access Sub-Brand Y's data
  within the same company
- **Corporate admin visibility test:** Verify corporate admin CAN see all sub-brands
- These tests must exist for EVERY data entity in the module

### 3. Authorization Tests
- Verify role restrictions work correctly
- Test that employees cannot access admin endpoints
- Test that sub-brand admins cannot access corporate-admin-only endpoints
- Test that unauthenticated requests receive 401

## Test Data Strategy

### Use Factories, Not Fixtures
```python
# WHY: Factories create test data on-demand with sensible defaults.
# They're better than static fixtures because each test gets fresh data,
# eliminating hidden dependencies between tests. You can also override
# specific fields when a test needs non-default values.

class ProductFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        company_id: UUID,
        sub_brand_id: UUID,
        name: str = "Test Product",
        sku: str | None = None,
        unit_price: float = 29.99,
    ) -> Product:
        product = Product(
            id=uuid4(),
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            name=name,
            sku=sku or f"SKU-{uuid4().hex[:8].upper()}",
            unit_price=unit_price,
        )
        db.add(product)
        await db.commit()
        return product
```

### Multi-Tenant Test Setup
Every test file that tests tenant-scoped data should use this setup:
1. Create Company A with Sub-Brand A1 and Sub-Brand A2
2. Create Company B with Sub-Brand B1
3. Create users at each role level for both companies
4. Create test data in specific company/sub-brand combinations
5. Verify access from different tenant contexts

## Backend Test Conventions (pytest)

- **Naming:** `test_{action}_{condition}_{expected_result}`
  - ✅ `test_create_product_with_valid_data_returns_201`
  - ✅ `test_list_products_as_company_b_returns_empty`
  - ❌ `test_products` (too vague)
- **Async tests:** `asyncio_mode = "auto"` in `pyproject.toml` — no `@pytest.mark.asyncio`
  decorator needed. Async test functions are detected automatically.
- **Database:** Use a separate test database, roll back after each test
- **Auth:** Use `create_test_token()` helper to generate JWTs for different roles

## RLS Testing Infrastructure

# --- ADDED 2026-04-07 after Module 1 Phase 3 ---
# Reason: Phase 3 established the patterns for testing RLS enforcement, dual-session
# database setup, and JWT authentication in tests. Without documenting these, future
# sessions would have to reverse-engineer conftest.py.
# Impact: Future modules follow the established test infrastructure patterns correctly.

### Dual Database Sessions (Superuser vs App Role)
PostgreSQL superusers bypass RLS even with `FORCE ROW LEVEL SECURITY`. The test suite
uses **two separate session factories** to handle this:

- **`admin_db_session`** — Connects as `postgres` (superuser). Bypasses RLS. Used for:
  - Seeding test data (creating companies, users, sub-brands across tenants)
  - The `client` fixture's `get_db_session` override (functional HTTP tests)
- **`db_session`** — Connects as `reel48_app` (non-superuser). RLS enforced. Used for:
  - Isolation tests that verify tenant boundaries via session variable + RLS policy

The `setup_database` fixture creates the `reel48_app` role if it doesn't exist and
grants `SELECT, INSERT, UPDATE, DELETE` on all module tables. When adding new tables
in future modules, **update the grant list** in `setup_database`.

### Alembic Migrations via Subprocess
The `setup_database` fixture runs `subprocess.run(["alembic", "upgrade", "head"])` instead
of the Alembic Python API. This is necessary because `env.py` calls `asyncio.run()` internally,
which conflicts with pytest-asyncio's event loop. The `DATABASE_URL` environment variable is
overridden to point to the test database.

### JWT Test Infrastructure
`create_test_token()` generates real RSA-signed JWTs using a test keypair generated at
module load. A session-scoped autouse fixture (`_patch_jwks`) monkeypatches
`app.core.security._fetch_jwks` to return a JWKS containing the test public key. The
full `validate_cognito_token` pipeline runs (signature, expiry, audience, issuer,
token_use) — only the JWKS HTTP fetch is mocked.

**CRITICAL:** After patching `_fetch_jwks`, the fixture must also reset
`security._jwks_keys = None` and `security._jwks_fetched_at = 0.0` to clear the
module-level JWKS cache. Otherwise the cache retains stale keys from a previous run.

### Isolation Test Pattern (Direct Session Variables)

# --- UPDATED 2026-04-07 after Module 1 Phase 4 ---
# Reason: (1) SET LOCAL does not support bind parameters — must use f-strings.
# (2) Cross-session RLS testing requires COMMITTED data, not just flushed.
# Impact: Isolation tests use correct SQL syntax and commit/cleanup pattern.

Isolation tests use a non-superuser session and set session variables manually
via `SET LOCAL`, then query to verify RLS filtering. **Two critical rules:**

1. **SET LOCAL requires f-strings** (not bind parameters — PostgreSQL limitation).
2. **Data must be COMMITTED**, not just flushed. The RLS-enforced session is a
   separate connection and cannot see uncommitted data from another transaction.
   Each test must commit its seed data, then clean up in a `finally` block.

```python
async def _set_tenant_context(session, company_id, sub_brand_id=""):
    cid = company_id or ""
    sbid = sub_brand_id or ""
    await session.execute(text(f"SET LOCAL app.current_company_id = '{cid}'"))
    await session.execute(text(f"SET LOCAL app.current_sub_brand_id = '{sbid}'"))

# Pattern: seed as superuser (committed), query as app role (RLS enforced),
# clean up in finally block
async with admin_factory() as seed:
    # ... create data ...
    await seed.commit()  # MUST commit — separate session can't see flushed-only data
try:
    async with app_factory() as app_sess:
        async with app_sess.begin():
            await _set_tenant_context(app_sess, str(company_id), str(sub_brand_id))
            rows = (await app_sess.execute(select(Model))).scalars().all()
            # ... assertions ...
finally:
    async with admin_factory() as cleanup:
        # ... delete test data in reverse FK order ...
        await cleanup.commit()
```

### Adding New Tables to the Test Infrastructure
When a new module adds tables:
1. Add `GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO reel48_app` in
   `setup_database`'s grant loop (update the table list in `conftest.py`)
2. Create corresponding multi-tenant fixtures if needed (following the
   `company_a` / `company_b` pattern)
3. Write isolation tests using the `db_session` fixture (not `admin_db_session`)

## Frontend Test Conventions (Vitest + RTL)

- **Naming:** `it('should {expected behavior} when {condition}')`
  - ✅ `it('should display product name when product is loaded')`
  - ✅ `it('should hide admin controls when user is employee role')`
- **Queries:** Prefer accessible queries (`getByRole`, `getByLabelText`)
  over implementation queries (`getByTestId`, CSS selectors)
- **API mocking:** Use MSW (Mock Service Worker) at the network level
- **Tenant-aware:** Mock different TenantContext values to test role-based rendering

## Coverage Requirements
- Backend: 80%+ overall, **100% on auth middleware and RLS-related code**
- Frontend: 70%+ on components with business logic
- Isolation tests: At least one cross-company and one cross-sub-brand test
  per data entity per module

## Self-Registration Test Requirements
# --- ADDED 2026-04-06 after ADR-007 ---
# Reason: Self-registration introduces an unauthenticated endpoint with unique security needs.
# Impact: Claude Code includes security and isolation tests for the registration flow.

When building or modifying the self-registration feature, include these additional tests:

### Functional Tests
- Validating a valid org code returns company name and sub-brand list
- Registering with a valid org code and a selected sub-brand creates a user with
  `role = employee` and the chosen `sub_brand_id`
- Registering with a `sub_brand_id` that does not belong to the org code's company
  returns a generic 400 error
- Registering with an invalid code returns a generic 400 error
- Registering with a deactivated code returns a generic 400 error
- Registering with a duplicate email returns the same generic 400 error (no enumeration)
- Generating a new org code deactivates the previous one
- Only `corporate_admin` (or `reel48_admin`) can generate/view/deactivate org codes

### Security Tests
- Rate limiting: 6th attempt from the same IP within 15 minutes returns 429
  (applies to both validate-org-code and register endpoints)
- Error messages do NOT reveal whether the code exists, is inactive, or the email is taken
- Sub-brand list is only returned for valid org codes (not publicly enumerable)
- Both registration endpoints do NOT require a JWT token

### Isolation Tests
- A user self-registered via Company A's org code CANNOT see Company B's data
- A self-registered user lands on the sub-brand they selected during registration
- Company B's admin CANNOT see or manage Company A's org codes

## External Service Mock Pattern

# --- ADDED 2026-04-08 after Module 1 post-module review ---
# Reason: Module 1 established a reusable pattern for mocking external services
# (CognitoService) that future modules should follow for Stripe, SES, S3.
# Impact: Consistent external service mocking across all modules.

External services (Cognito, Stripe, SES, S3) are mocked in tests via a four-part pattern:

1. **MockXxxService class** in `conftest.py` — Does not call the real API. Records
   calls in lists (e.g., `created_users`, `disabled_users`) for test assertions.
   Does NOT call `super().__init__()` since no real client is needed.

2. **Autouse fixture** that registers the mock via `app.dependency_overrides`:
   ```python
   @pytest.fixture(autouse=True)
   def mock_cognito() -> MockCognitoService:
       mock = MockCognitoService()
       app.dependency_overrides[get_cognito_service] = lambda: mock
       yield mock
       app.dependency_overrides.pop(get_cognito_service, None)
   ```

3. **Yield the mock** so individual tests can inspect recorded calls:
   ```python
   async def test_registration_creates_cognito_user(client, mock_cognito, ...):
       await client.post("/api/v1/auth/register", ...)
       assert len(mock_cognito.created_users) == 1
       assert mock_cognito.created_users[0]["role"] == "employee"
   ```

4. **Cleanup in teardown** — `dependency_overrides.pop()` prevents leakage between tests.

When adding a new external service (e.g., Stripe in Module 7):
- Create `MockStripeService` following the same pattern
- Add an autouse fixture for `get_stripe_service`
- Both mocks coexist in `conftest.py`


## Rate Limit Testing

# --- ADDED 2026-04-08 after Module 1 post-module review ---
# Reason: The autouse `no_rate_limit` fixture disables rate limiting for all tests,
# but rate limiting tests need guidance on how to opt out of this.
# Impact: Tests that verify rate limit behavior know to re-enable it.

An autouse `no_rate_limit` fixture in `conftest.py` disables rate limiting for all
tests by default (prevents tests from hitting Redis). To test rate limiting behavior:

1. **Do NOT** remove the autouse fixture — it protects all other tests
2. **Re-override** the dependency in the specific test function:
   ```python
   async def test_rate_limiting_returns_429(client):
       # Re-enable rate limiting for this test
       app.dependency_overrides[rate_limit_auth] = rate_limit_auth
       try:
           for _ in range(6):
               response = await client.post(
                   "/api/v1/auth/validate-org-code",
                   json={"code": "INVALID1"},
               )
           assert response.status_code == 429
       finally:
           # Restore the no-op override
           app.dependency_overrides[rate_limit_auth] = lambda: None
   ```
3. Rate limit tests require a running Redis instance (or mock `_get_redis_client`)


## Common Mistakes to Avoid
- ❌ Testing only the happy path
- ❌ Skipping isolation tests ("RLS will handle it")
- ❌ Sharing mutable state between tests (each test should be independent)
- ❌ Testing implementation details instead of behavior
- ❌ Hardcoding UUIDs instead of generating them (causes conflicts in parallel tests)
