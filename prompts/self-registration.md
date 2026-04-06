# Prompt Template: Self-Registration via Org Code
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS?                                                             ║
# ║                                                                            ║
# ║  This is a REUSABLE PROMPT TEMPLATE for building the org-code self-        ║
# ║  registration feature. It covers the org_codes table, the registration     ║
# ║  endpoint, the org code management endpoints, the frontend register page,  ║
# ║  and the test suite. See ADR-007 for the architectural decision behind     ║
# ║  this feature.                                                             ║
# ║                                                                            ║
# ║  WHEN TO USE:                                                              ║
# ║  Use this template when building or modifying the self-registration flow   ║
# ║  as part of Module 1 (Auth & Multi-Tenancy).                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

## Template

```
Build the self-registration via org code feature for Reel48+.

### 1. Database: org_codes table

Create an Alembic migration for the `org_codes` table:
- id (UUID, PK)
- company_id (UUID, NOT NULL, FK -> companies, indexed)
- code (VARCHAR(8), NOT NULL, UNIQUE, indexed)
- is_active (BOOLEAN, NOT NULL, DEFAULT true)
- created_by (UUID, NOT NULL, FK -> users)
- created_at, updated_at (standard timestamps)

RLS: Company isolation policy only (no sub_brand_id on this table).
No sub-brand scoping policy.

Also add to the `users` table:
- registration_method (TEXT, NOT NULL, DEFAULT 'invite') — values: invite, self_registration
- org_code_id (UUID, nullable, FK -> org_codes)

### 2. SQLAlchemy Model: OrgCode

Create `app/models/org_code.py` with the OrgCode model. This model has `company_id`
but NOT `sub_brand_id` (org codes are company-level). It does NOT inherit from TenantBase
since it lacks sub_brand_id — use a custom base with company_id, id, and timestamps.

### 3. Pydantic Schemas: org_code.py

- OrgCodeResponse: id, code, is_active, created_at
- OrgCodeCreate: (empty — code is auto-generated server-side)
- RegisterRequest: org_code (str), email (str), full_name (str), password (str)
- RegisterResponse: message (str) — generic success message, no sensitive data

### 4. Self-Registration Endpoint

`POST /api/v1/auth/register` — UNAUTHENTICATED (does NOT use get_tenant_context).

This is the second unauthenticated endpoint exception (alongside Stripe webhooks).
Security: org code validation + rate limiting (5 attempts per IP per 15 minutes via Redis).

Flow:
1. Validate request body (org code format, email format, password strength)
2. Check rate limit — return 429 if exceeded
3. Look up org code: SELECT * FROM org_codes WHERE code = :code AND is_active = true
4. If not found: return 400 with GENERIC error ("Registration failed")
5. Resolve company_id from the org code
6. Look up default sub-brand: SELECT id FROM sub_brands WHERE company_id = :cid AND is_default = true
7. Check for duplicate email (or handle Cognito's UsernameExistsException)
8. Create Cognito user via Admin API with custom attributes:
   - custom:company_id = resolved company_id
   - custom:sub_brand_id = default sub_brand_id
   - custom:role = employee
9. Create user row in database with registration_method = 'self_registration', org_code_id
10. Return 201 with generic success message

CRITICAL: All error cases (invalid code, inactive code, duplicate email) return the
SAME generic error message. Never reveal which condition failed.

### 5. Org Code Management Endpoints (authenticated, corporate_admin only)

- POST /api/v1/org_codes — Generate new org code for the admin's company.
  Auto-deactivates any previous active code. Returns the new code.
  Code generation: 8 chars from alphabet ABCDEFGHJKMNPQRSTUVWXYZ2345679 (30 chars).
- GET /api/v1/org_codes/current — View the current active org code.
- DELETE /api/v1/org_codes/{id} — Deactivate a specific org code.

All three use TenantContext from JWT. Filter by context.company_id (defense-in-depth).
Role check: context.role in ('corporate_admin', 'reel48_admin').

### 6. Frontend: Register Page

Create `src/app/(public)/register/page.tsx`:
- Form fields: Org Code, Email, Full Name, Password, Confirm Password
- On submit: POST /api/v1/auth/register (no auth token needed)
- On success: redirect to "Check your email for verification" page
- On error: display generic "Registration failed. Please check your org code and try again."
- Link to /login for existing users
- Link to /invite/[token] flow is separate (different page)

### 7. Tests

Write tests in `tests/test_self_registration.py`:

Functional:
- test_register_with_valid_org_code_creates_employee_on_default_sub_brand
- test_register_with_invalid_code_returns_400
- test_register_with_inactive_code_returns_400
- test_register_with_duplicate_email_returns_400
- test_error_messages_are_identical_for_all_failure_cases
- test_generate_org_code_deactivates_previous
- test_only_corporate_admin_can_generate_org_code
- test_only_corporate_admin_can_view_org_code
- test_only_corporate_admin_can_deactivate_org_code

Security:
- test_rate_limit_blocks_after_5_attempts
- test_register_endpoint_does_not_require_jwt

Isolation:
- test_self_registered_user_cannot_see_other_company_data
- test_self_registered_user_lands_on_default_sub_brand
- test_company_b_admin_cannot_see_company_a_org_codes

### Acceptance Criteria
- [ ] org_codes table created with Alembic migration including company isolation RLS
- [ ] Registration endpoint is unauthenticated and rate-limited
- [ ] Self-registered users get role=employee and default sub_brand_id
- [ ] All error responses are generic (no enumeration)
- [ ] Org code management requires corporate_admin role
- [ ] Only one active code per company at a time
- [ ] Standard response format: { data, meta, errors }
- [ ] All tests pass, including isolation and security tests
- [ ] users table has registration_method and org_code_id columns

### Existing Code Context
- Auth middleware: app/middleware/auth.py
- Base model: app/models/base.py (TenantBase — note: org_codes does NOT use TenantBase)
- Cognito config: app/core/security.py
- Redis/rate limiting: app/core/dependencies.py or new rate_limit.py utility
- Default sub-brand lookup: sub_brand_service.py (is_default=true query)
```
