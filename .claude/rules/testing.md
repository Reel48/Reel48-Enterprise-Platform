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

### Platform Admin (reel48_admin) Test Fixtures

# --- ADDED 2026-04-08 after Module 3 Phase 4 ---
# Reason: Platform admin endpoints need `resolve_current_user_id` to set `approved_by`
# FKs. The reel48_admin_token fixture has no matching User record. New fixtures solve this.
# Impact: Future modules testing platform admin endpoints use the correct fixtures.

The `reel48_admin_token` fixture generates a JWT with no `company_id` and a random
`cognito_sub` that does NOT map to any User record. This is fine for testing auth
rejection (403 checks) but **not** for endpoints that call `resolve_current_user_id`.

For platform admin endpoints that need a real User record (e.g., to set `approved_by`):
- **`reel48_company`** — Creates an internal "Reel48 Operations" company + sub-brand
- **`reel48_admin_user`** — Creates a User with `role=reel48_admin` in that company
- **`reel48_admin_user_token`** — JWT with the user's `cognito_sub` but NO `company_id`
  claim (matching real behavior where reel48_admin JWTs have no company)

Use `reel48_admin_user_token` (not `reel48_admin_token`) when the endpoint needs to
resolve the admin's local User ID.

### Role-Specific User + Token Fixtures

# --- ADDED 2026-04-08 during Module 4 Phase 3 ---
# Reason: Module 4 introduced role-based visibility (managers see all orders,
# employees see own). Testing this requires User records with matching JWT tokens
# for each role. Several "token-only" fixtures existed without backing User records.
# Impact: Future modules use the correct fixtures when testing role-based endpoints.

Many test scenarios require both a **User record** and a **matching JWT token** (where
the token's `cognito_sub` maps to the User). Token-only fixtures (e.g.,
`company_a_brand_a1_manager_token`) generate random `cognito_sub` values that don't
match any User — these are fine for auth/403 tests but fail when endpoints call
`resolve_current_user_id`.

**User + Token fixture pairs (cognito_sub matches):**
- `user_a1_employee` + `user_a1_employee_token` — Employee in Company A, Brand A1
- `user_a1_admin` + `user_a1_admin_token` — Sub-brand admin in Company A, Brand A1
- `user_a1_manager` + `user_a1_manager_token` — Regional manager in Company A, Brand A1
- `user_a_corporate_admin` + `user_a_corporate_admin_token` — Corporate admin in Company A (sub_brand_id=None)
- `user_b1_employee` — Employee in Company B, Brand B1 (token created inline via `create_test_token`)
- `reel48_admin_user` + `reel48_admin_user_token` — Platform admin (no company_id in JWT)

**Token-only fixtures (no matching User record):**
- `reel48_admin_token`, `company_a_corporate_admin_token`, `company_a_brand_a1_admin_token`,
  `company_a_brand_a1_employee_token`, `company_a_brand_a2_employee_token`,
  `company_b_employee_token`, `company_a_brand_a2_admin_token`,
  `company_b_corporate_admin_token`, `company_a_brand_a1_manager_token`

Use token-only fixtures for permission rejection tests (403 checks). Use User + Token
pairs when the endpoint resolves the user's local ID.

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
async def _set_tenant_context(session, company_id, sub_brand_id):
    await session.execute(text(f"SET LOCAL app.current_company_id = '{company_id}'"))
    await session.execute(text(f"SET LOCAL app.current_sub_brand_id = '{sub_brand_id}'"))

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

### CRITICAL: RLS Isolation Tests Must Use Real UUIDs (Not Empty Strings)

# --- ADDED 2026-04-09 after Module 8 Phase 1 ---
# Reason: PostgreSQL does NOT guarantee short-circuit evaluation of OR in RLS
# policies. Setting session variables to '' causes `::uuid` cast errors even when
# an earlier OR branch (= '') is true, because the planner may evaluate all branches.
# Impact: All isolation tests pass real UUIDs for both company_id and sub_brand_id.

PostgreSQL's RLS policies contain expressions like:
```sql
current_setting('app.current_sub_brand_id', true) = ''
OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
```

**The OR is NOT guaranteed to short-circuit.** If `app.current_sub_brand_id` is set to
`''`, the `::uuid` cast in the third branch may still be evaluated, causing
`invalid input syntax for type uuid: ""`. This happens because:
1. Custom GUC variables default to `''` (empty string), not NULL
2. PostgreSQL may evaluate all OR branches during RLS policy checks
3. The `::uuid` cast fails on empty strings

**Rule:** In isolation tests using the `reel48_app` role, ALWAYS pass **real UUID values**
for both `company_id` and `sub_brand_id`. Never use empty strings.

- To test **company isolation:** Set company_id to Company A's UUID and sub_brand_id to
  Brand A1's UUID. Verify Company B's data is not visible.
- To test **sub-brand isolation:** Set both to Company A / Brand A1. Verify Brand A2 and
  Company B data is not visible.
- To test **reel48_admin cross-company visibility:** Use `admin_db_session` (superuser)
  instead of `reel48_app` role. The actual application routes reel48_admin requests
  through the superuser session via the `client` fixture.

**This does NOT affect production code.** The `get_tenant_context` middleware sets session
variables on the superuser session (via `get_db_session`), which bypasses RLS entirely.
The RLS policies only activate for the non-superuser `reel48_app` role used in tests.

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

When adding a new external service:
- Create a `MockXxxService` class following the same pattern
- Add an autouse fixture via `app.dependency_overrides`
- All mocks coexist in `conftest.py`

**Implemented mocks (as of Module 7):**
- `MockCognitoService` — Records `created_users`, `disabled_users`, etc.
- `MockStripeService` — Records `created_invoices`, `created_customers`,
  `created_invoice_items`, `finalized_invoices`, `sent_invoices`, `voided_invoices`.
  Also provides `construct_webhook_event()` which can be overridden per-test to
  simulate signature verification failures.
- `MockEmailService` — Records `sent_emails` for notification assertions.


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


## Webhook Endpoint Testing

# --- ADDED 2026-04-09 after Module 7 Phase 6 ---
# Reason: Webhook endpoints (Stripe) have unique testing requirements: no JWT auth,
# signature verification, idempotent processing, and status non-regression. Phase 6
# established the patterns for testing all of these.
# Impact: Future webhook integrations (SES notifications, etc.) follow this pattern.

Webhook endpoints are unauthenticated and verify signatures instead of JWTs. Testing
requires different patterns than standard endpoint tests:

### Signature Verification Tests
The `MockStripeService.construct_webhook_event()` returns a dict by default (simulating
valid signature). To test signature failure, override the method per-test:

```python
async def test_webhook_rejects_invalid_signature(client, mock_stripe):
    import stripe
    mock_stripe.construct_webhook_event = Mock(
        side_effect=stripe.error.SignatureVerificationError("bad sig", "sig_header")
    )
    response = await client.post(
        "/api/v1/webhooks/stripe",
        content=b'{"type": "invoice.paid"}',
        headers={"stripe-signature": "invalid"},
    )
    assert response.status_code == 400
```

### Idempotent Processing Tests
The invoice webhook handler uses a `_STATUS_ORDER` dict to prevent status regression.
Test that processing the same event twice produces no error and no duplicate update:

```python
async def test_webhook_idempotent_processing(client, ...):
    # First call: sets status to "paid"
    response1 = await client.post("/api/v1/webhooks/stripe", ...)
    assert response1.status_code == 200

    # Second call: same event, no error, no regression
    response2 = await client.post("/api/v1/webhooks/stripe", ...)
    assert response2.status_code == 200
    # Invoice still shows "paid" (not reset)
```

### Status Non-Regression Tests
Verify that a lower-priority webhook event cannot regress a higher-priority status:
```python
# Invoice is already "paid" → "invoice.sent" webhook should NOT downgrade to "sent"
```

### Webhook Test Data Setup
Webhook tests need a pre-existing invoice record with a `stripe_invoice_id` that
matches the webhook payload's `data.object.id`. Create the invoice directly in the
database (not via API) to isolate webhook logic from creation logic.


## Common Mistakes to Avoid
- ❌ Testing only the happy path
- ❌ Skipping isolation tests ("RLS will handle it")
- ❌ Sharing mutable state between tests (each test should be independent)
- ❌ Testing implementation details instead of behavior
- ❌ Hardcoding UUIDs instead of generating them (causes conflicts in parallel tests)
- ❌ Omitting trailing slash on list endpoint URLs (causes 307 redirect — use `/api/v1/profiles/` not `/api/v1/profiles`)
