# Prompt Template: Test Suite
#
# Use this template when you need Claude Code to create a comprehensive test
# suite for an existing module, especially the critical isolation tests.

## Template

```
Create a comprehensive test suite for the {MODULE_NAME} module.

### Module Under Test
- Backend files: {list key files — routes, services, models}
- Frontend files: {list key components if applicable}

### Test Categories Required

#### 1. Functional Tests
{List the key operations to test with expected outcomes:}
- Create {entity} with valid data → 201, returns entity
- Create {entity} with invalid data → 422, returns validation errors
- List {entities} with pagination → 200, returns page with correct count
- Get {entity} by ID → 200 if found, 404 if not
- Update {entity} → 200 with updated fields
- Delete {entity} → 204

#### 2. Isolation Tests (CRITICAL)
- Create data in Company A → query as Company B → returns empty (cross-company)
- Create data in Sub-Brand A1 → query as Sub-Brand A2 → returns empty (cross-sub-brand)
- Create data in both Sub-Brand A1 and A2 → query as corporate admin → returns both
- Attempt to access Company A's specific resource ID as Company B → 404 (not 403!)
  (Return 404, not 403, to avoid confirming the resource exists in another tenant)

#### 3. Authorization Tests
- Attempt admin action as employee → 403
- Attempt corporate-only action as sub-brand admin → 403
- Attempt any action without auth token → 401
- Verify {role} CAN perform {specific permitted actions}

### Test Setup
Use these fixtures from conftest.py:
- company_a (with sub_brands a1, a2)
- company_b (with sub_brand b1)
- Tokens: reel48_admin_token, corporate_admin_token, brand_admin_token, employee_token, company_b_token

### Acceptance Criteria
- [ ] At least one cross-company isolation test per data entity
- [ ] At least one cross-sub-brand isolation test per data entity
- [ ] Corporate admin visibility test (sees all sub-brands)
- [ ] Role authorization tests for every protected endpoint
- [ ] Edge cases: empty results, invalid IDs, duplicate resources
- [ ] All tests are independent (no shared mutable state)
- [ ] Async tests use @pytest.mark.asyncio
```
