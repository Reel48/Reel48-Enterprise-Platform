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
- **Async tests:** Use `pytest-asyncio` with `@pytest.mark.asyncio`
- **Database:** Use a separate test database, roll back after each test
- **Auth:** Use `create_test_token()` helper to generate JWTs for different roles

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

## Common Mistakes to Avoid
- ❌ Testing only the happy path
- ❌ Skipping isolation tests ("RLS will handle it")
- ❌ Sharing mutable state between tests (each test should be independent)
- ❌ Testing implementation details instead of behavior
- ❌ Hardcoding UUIDs instead of generating them (causes conflicts in parallel tests)
