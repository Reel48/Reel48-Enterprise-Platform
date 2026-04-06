---
globs: "**/api/**,**/routes/**,**/endpoints/**"
---

# Rule: API Endpoints
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This rule activates when Claude Code is working on API route files.       ║
# ║  It enforces the Reel48+ API conventions: tenant context from JWT only,    ║
# ║  standard response format, proper role checking, and defense-in-depth      ║
# ║  data filtering.                                                           ║
# ║                                                                            ║
# ║  WHY THIS RULE?                                                            ║
# ║                                                                            ║
# ║  API endpoints are the attack surface. A single endpoint that accepts      ║
# ║  company_id as a query parameter (instead of extracting it from the JWT)   ║
# ║  is a privilege escalation vulnerability. This rule makes that mistake     ║
# ║  impossible to forget.                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Activates for: **/api/**, **/routes/**, **/endpoints/**

## Mandatory Requirements for Every Endpoint

### 1. Tenant context MUST come from the JWT token
- Use `context: TenantContext = Depends(get_tenant_context)` on every protected endpoint
- NEVER accept `company_id` or `sub_brand_id` as query parameters, path parameters,
  or request body fields
- The ONLY exception: super-admin endpoints (if implemented) that explicitly operate
  across tenants with additional authorization

### 2. Use the standard response format
```python
# Every successful response:
{"data": <result>, "meta": {"page": 1, "per_page": 20, "total": 100}, "errors": []}

# Every error response:
{"data": null, "errors": [{"code": "ERROR_CODE", "message": "Human-readable message"}]}
```

### 3. Role-based access control
- Check the user's role BEFORE executing any business logic
- Use explicit role checks, not implicit ones:
  ```python
  # ✅ CORRECT — explicit role check
  if not context.is_admin:
      raise HTTPException(status_code=403, detail="Admin role required")

  # ❌ WRONG — no role check, relies only on RLS
  # (RLS handles data isolation, but not FEATURE access)
  ```

### 4. Defense-in-depth filtering
- Even though RLS handles isolation at the database level, ALSO filter by
  `company_id` and `sub_brand_id` in your SQLAlchemy queries
- This provides a second layer of protection if RLS is accidentally misconfigured

### 5. URL conventions
- Plural nouns: `/api/v1/products`, NOT `/api/v1/product`
- snake_case: `/api/v1/sub_brands`, NOT `/api/v1/subBrands`
- Versioned: Always under `/api/v1/`
- Resource IDs in path: `/api/v1/products/{product_id}`
- Actions as sub-resources: `/api/v1/orders/{order_id}/approve`

### 6. Pagination on all list endpoints
- Accept `page` and `per_page` query parameters
- Default: `page=1`, `per_page=20`
- Maximum `per_page`: 100
- Return total count in the `meta` object

## Common Mistakes to Avoid
- ❌ Accepting tenant IDs as request parameters
- ❌ Returning data without the standard wrapper format
- ❌ Forgetting pagination on list endpoints
- ❌ Using 200 for creation (use 201)
- ❌ Returning sensitive fields (password hashes, internal IDs) in responses
- ❌ Missing role checks on admin-only endpoints
