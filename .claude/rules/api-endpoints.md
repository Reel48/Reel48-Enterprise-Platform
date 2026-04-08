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
  or request body fields for **tenant-scoped** endpoints
- **Exception 1: `reel48_admin` platform endpoints** (under `/api/v1/platform/`).
  The `reel48_admin` role operates cross-company (has no `company_id` of its own),
  so platform admin endpoints MAY accept a target `company_id` in the request body
  to specify which client company to operate on. These endpoints MUST verify the
  caller has the `reel48_admin` role before accepting the target company_id.
  Example: `POST /api/v1/platform/invoices` accepts `company_id` to create an
  invoice for a specific client company.
- **Exception 2: Unauthenticated endpoints** that do NOT use `get_tenant_context`:
  1. `POST /api/v1/webhooks/stripe` — Secured by Stripe webhook signature verification.
  2. `POST /api/v1/auth/validate-org-code` — Validates org code, returns company name
     + sub-brand list. Rate-limited (5 attempts/IP/15 min). See ADR-007.
  3. `POST /api/v1/auth/register` — Self-registration with org code + selected sub-brand.
     Rate-limited (shared window with validate-org-code). See ADR-007.

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

### 7. Delete endpoint return conventions

# --- ADDED 2026-04-08 after Module 1 post-module review ---
# Reason: Inconsistent DELETE responses across Module 1 endpoints.
# Impact: All future delete endpoints use consistent status codes.

- **Soft-delete** (sets `deleted_at` or `is_active = false`): Return **200** with
  `ApiResponse[T]` containing the deactivated resource. The caller sees the final state.
- **Hard-delete** (row permanently removed): Return **204 No Content** with no body.

## Common Mistakes to Avoid
- ❌ Accepting tenant IDs as request parameters
- ❌ Returning data without the standard wrapper format
- ❌ Forgetting pagination on list endpoints
- ❌ Using 200 for creation (use 201)
- ❌ Returning sensitive fields (password hashes, internal IDs) in responses
- ❌ Missing role checks on admin-only endpoints
