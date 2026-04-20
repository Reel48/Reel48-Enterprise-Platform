---
globs: "**/api/**,**/routes/**,**/endpoints/**"
---

# Rule: API Endpoints

> ⚠ **SIMPLIFICATION IN PROGRESS** — stripped as part of the refactor documented at
> `~/.claude/plans/yes-please-write-the-memoized-karp.md`. Previous content referenced
> `sub_brand_id`, the Stripe webhook exception, and a two-step self-registration endpoint.
> All three are being removed. Do **not** reintroduce `sub_brand_id` on endpoint signatures.

# Activates for: **/api/**, **/routes/**, **/endpoints/**

## Mandatory Requirements for Every Endpoint

### 1. Tenant context MUST come from the JWT token
- Use `context: TenantContext = Depends(get_tenant_context)` on every protected endpoint.
- NEVER accept `company_id` as a query parameter, path parameter, or request body field for
  **tenant-scoped** endpoints.
- **Exception 1 — `reel48_admin` platform endpoints** (under `/api/v1/platform/`). The
  `reel48_admin` role operates cross-company and has no `company_id` of its own, so platform
  admin endpoints MAY accept a target `company_id` in the request body. These endpoints MUST
  verify the caller has `role == 'reel48_admin'` before reading the target `company_id`.
- **Exception 2 — Unauthenticated auth endpoints** that do NOT use `get_tenant_context`:
  1. `POST /api/v1/auth/validate-org-code` — Validates an org code and returns the company
     name. Rate-limited (5 attempts/IP/15 min).
  2. `POST /api/v1/auth/register` — Single-step self-registration with org code + user
     details. Rate-limited (shared window with validate-org-code).

  (Note: the Stripe webhook endpoint has been removed. If future webhooks are added, they
  become additional exceptions — document them here.)

### 2. Use the standard response format
```python
# Every successful response:
{"data": <result>, "meta": {"page": 1, "per_page": 20, "total": 100}, "errors": []}

# Every error response:
{"data": null, "errors": [{"code": "ERROR_CODE", "message": "Human-readable message"}]}
```

### 3. Role-based access control
- Check the user's role BEFORE executing any business logic.
- Use explicit role checks, not implicit ones. RLS handles data isolation, not feature access.

### 4. Defense-in-depth filtering
- Even though RLS handles isolation at the database level, ALSO filter by `company_id` in
  SQLAlchemy queries. Second layer of protection if RLS is accidentally misconfigured.

### 5. URL conventions
- Plural nouns: `/api/v1/users`, NOT `/api/v1/user`.
- snake_case (for any multi-word path segment).
- Versioned: Always under `/api/v1/`.
- Resource IDs in path: `/api/v1/users/{user_id}`.
- Actions as sub-resources: `/api/v1/users/{user_id}/deactivate`.

### 6. Pagination on all list endpoints
- Accept `page` and `per_page` query parameters.
- Default: `page=1`, `per_page=20`. Maximum `per_page`: 100.
- Return total count in the `meta` object.

### 7. Delete endpoint return conventions
- **Soft-delete** (sets `deleted_at` or `is_active = false`): Return **200** with
  `ApiResponse[T]` containing the deactivated resource.
- **Hard-delete** (row permanently removed): Return **204 No Content** with no body.

## Common Mistakes to Avoid
- ❌ Accepting tenant IDs as request parameters (for tenant-scoped endpoints).
- ❌ Returning data without the standard wrapper format.
- ❌ Forgetting pagination on list endpoints.
- ❌ Using 200 for creation (use 201).
- ❌ Returning sensitive fields (password hashes, internal IDs) in responses.
- ❌ Missing role checks on admin-only endpoints.
- ❌ Reintroducing `sub_brand_id` as a request parameter or query filter.
