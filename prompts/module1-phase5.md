# Module 1 Phase 5 Prompt — Self-Registration, Invite Consumption & Cognito Integration

Copy everything below the line and paste it as your first message in a new Claude Code session.

---

Continue with Module 1 Phase 5 per the harness. Phases 1–4 are complete on `main`.

- **Phase 1** scaffolded the backend (FastAPI app, config, base models, Alembic, health endpoint, test skeleton).
- **Phase 2** created the 5 identity models (Company, SubBrand, User, Invite, OrgCode) and a single Alembic migration with RLS policies for all 5 tables.
- **Phase 3** added the auth plumbing: JWT validation (`security.py`), TenantContext dataclass (`tenant.py`), `get_tenant_context` dependency with `SET LOCAL` session variables, role-checking dependencies (`require_reel48_admin`, `require_corporate_admin`, `require_admin`, `require_manager`), and 19 auth tests.
- **Phase 4** built the full CRUD layer: Pydantic schemas, service classes, and API endpoints for all 5 identity entities (Companies, SubBrands, OrgCodes, Users, Invites), plus 74 tests (functional, authorization, and isolation). Also fixed the `users_sub_brand_scoping` RLS policy to use `AS RESTRICTIVE`.

**Phase 5 scope: Self-registration via org code, invite consumption, and Cognito user provisioning.**

This phase completes Module 1 by building the two employee onboarding flows (invite + self-registration) and connecting them to AWS Cognito for actual user creation. Phase 4 created database records with placeholder `cognito_sub` values — Phase 5 makes the full flow work end-to-end.

### What to build

**1. Cognito Service** (`app/services/cognito_service.py`)

A service class that wraps the AWS Cognito `AdminCreateUser` / `AdminSetUserPassword` / `AdminUpdateUserAttributes` APIs via `boto3`. This is the ONLY file that imports `boto3` — all other code calls this service.

Methods:
- `create_cognito_user(email, password, company_id, sub_brand_id, role) -> str` — Creates a Cognito user with custom attributes (`custom:company_id`, `custom:sub_brand_id`, `custom:role`). Returns the Cognito `sub` (UUID string). Sets the password directly (no temp password flow for self-registration). Triggers Cognito email verification.
- `get_cognito_user(cognito_sub) -> dict | None` — Fetch user attributes from Cognito by sub.
- `update_cognito_attributes(cognito_sub, attributes: dict) -> None` — Update custom attributes (for role changes, sub-brand reassignment).
- `disable_cognito_user(cognito_sub) -> None` — Disable the Cognito user (for soft-delete sync).

**IMPORTANT for testing:** The Cognito service must be easily mockable. Define a protocol/interface or use dependency injection so tests can swap in a mock without hitting real AWS. Consider making `cognito_service` a FastAPI dependency or using a class that accepts a boto3 client.

**2. Rate Limiting Dependency** (`app/core/rate_limit.py`)

Implement the rate limiting pattern from `backend/CLAUDE.md` using Redis. Both unauthenticated auth endpoints share the same rate limit window.

- `check_rate_limit(request, group="auth", max_attempts=5, window_seconds=900)` — FastAPI dependency. Increments a Redis counter keyed by `rate_limit:{group}:{client_ip}`. Returns 429 when exceeded.
- **Redis client setup:** Use `redis.asyncio` with `settings.REDIS_URL`. Create a module-level client (or lazy singleton).
- **Graceful degradation:** If Redis is unavailable, log a warning and allow the request (don't block registration because Redis is down). Tests should mock Redis.

**3. Org Code Validation Endpoint** (`app/api/v1/auth.py`)

`POST /api/v1/auth/validate-org-code` — **Unauthenticated**, rate-limited.

Request body: `{ "code": "REEL7K3M" }`

On success (valid, active org code):
```json
{
  "data": {
    "company_name": "Acme Corp",
    "sub_brands": [
      { "id": "uuid", "name": "North Division", "slug": "north-division", "is_default": true },
      { "id": "uuid", "name": "South Division", "slug": "south-division", "is_default": false }
    ]
  },
  "errors": []
}
```

On failure (invalid code, inactive code, any error): Return a **generic 400** with no details about what went wrong (prevent enumeration):
```json
{ "data": null, "errors": [{ "code": "INVALID_REQUEST", "message": "Invalid registration code" }] }
```

**CRITICAL:** This endpoint does NOT use `get_tenant_context`. It queries the `org_codes` table directly (outside RLS-scoped session) using a superuser/admin database session, since there's no JWT. You'll need a separate `get_db_session_no_rls` dependency or use the existing session before SET LOCAL is called. Think about the cleanest way to handle this — the key constraint is that the query must not be filtered by RLS (there's no tenant context to set).

**4. Self-Registration Endpoint** (`app/api/v1/auth.py`)

`POST /api/v1/auth/register` — **Unauthenticated**, rate-limited (shares the "auth" group).

Request body:
```json
{
  "code": "REEL7K3M",
  "sub_brand_id": "uuid",
  "email": "jane@example.com",
  "full_name": "Jane Smith",
  "password": "SecureP@ss123"
}
```

Flow:
1. Re-validate the org code (`is_active = true`). Resolve `company_id` from the org code.
2. Validate `sub_brand_id` belongs to the resolved company.
3. Check email uniqueness (both in local database AND Cognito — or just local, since Cognito will reject duplicates too).
4. Create Cognito user via `cognito_service.create_cognito_user()` with `role = "employee"`.
5. Create the local `users` table record with `cognito_sub` from Cognito, `registration_method = "self_registration"`, `org_code_id` set.
6. Return 201 with a success message (NOT the user record — the user hasn't verified email yet).

On ANY failure: return a **generic 400** (same message regardless of cause — duplicate email, bad code, bad sub_brand). This prevents enumeration.

Password requirements: Delegate to Cognito's password policy (don't duplicate validation server-side). If Cognito rejects the password, catch the error and return the generic 400.

**5. Invite Registration Endpoint** (`app/api/v1/auth.py`)

`POST /api/v1/auth/register-from-invite` — **Unauthenticated** (no rate limit needed — tokens are single-use and time-limited).

Request body:
```json
{
  "token": "the-64-char-invite-token",
  "email": "jane@example.com",
  "full_name": "Jane Smith",
  "password": "SecureP@ss123"
}
```

Flow:
1. Look up the invite by `token`. Validate it's not expired (`expires_at > now`) and not consumed (`consumed_at IS NULL`).
2. Verify the email matches the invite's `email` field (case-insensitive).
3. Create Cognito user via `cognito_service.create_cognito_user()` with the invite's `company_id`, `target_sub_brand_id`, and `role`.
4. Create the local `users` table record with `cognito_sub` from Cognito, `registration_method = "invite"`.
5. Mark the invite as consumed (`consumed_at = now`).
6. Return 201 with success.

On failure: return a **generic 400** for invalid/expired/consumed tokens.

**6. Update Existing User Service**

Modify `user_service.py` so that `create_user()` (the admin-created path from Phase 4) also calls Cognito to create the user. Currently it generates a placeholder `cognito_sub = str(uuid4())`. After this phase:
- Admin creates user via `POST /api/v1/users` → service calls Cognito → stores real `cognito_sub`.
- The admin-created user receives a Cognito email with a temporary password (use `AdminCreateUser` with `TemporaryPassword`).

### Schemas for new endpoints

`app/schemas/auth.py`:
- `ValidateOrgCodeRequest(BaseModel)`: `code: str`
- `ValidateOrgCodeResponse(BaseModel)`: `company_name: str`, `sub_brands: list[SubBrandSummary]`
- `SubBrandSummary(BaseModel)`: `id: UUID`, `name: str`, `slug: str`, `is_default: bool`
- `SelfRegisterRequest(BaseModel)`: `code: str`, `sub_brand_id: UUID`, `email: str`, `full_name: str`, `password: str`
- `InviteRegisterRequest(BaseModel)`: `token: str`, `email: str`, `full_name: str`, `password: str`
- `RegisterResponse(BaseModel)`: `message: str`

### Wire up the router

Add the auth router to `app/api/v1/router.py`. The auth endpoints live at `/api/v1/auth/`.

### Tests

Write tests in `tests/test_registration.py` covering:

**Functional — Self-Registration:**
- Valid org code returns company name and sub-brand list
- Register with valid code + valid sub-brand creates user with `role = employee` and `registration_method = self_registration`
- Register with `sub_brand_id` not belonging to the code's company → generic 400
- Register with invalid/inactive code → generic 400
- Register with duplicate email → same generic 400 (no enumeration)
- Generating a new org code deactivates the previous one (already tested in Phase 4, but verify the registration endpoint rejects the old code)

**Functional — Invite Registration:**
- Register with valid invite token creates user with correct company, sub-brand, and role
- Register with expired token → generic 400
- Register with already-consumed token → generic 400
- Register with wrong email (doesn't match invite) → generic 400
- After successful registration, invite is marked consumed (cannot be reused)

**Security:**
- Rate limiting: 6th attempt from same IP within 15 minutes returns 429 (applies to validate-org-code AND register endpoints sharing the "auth" group)
- Error messages do NOT reveal whether the code exists, is inactive, or the email is taken
- Both registration endpoints do NOT require a JWT token (test without Authorization header)

**Authorization:**
- Only `corporate_admin`+ can generate/view/deactivate org codes (already tested in Phase 4)

**Isolation:**
- A user self-registered via Company A's org code CANNOT see Company B's data (verify by creating the user, then making authenticated requests)
- Company B's admin CANNOT see Company A's org codes (already tested in Phase 4)

### Testing Cognito and Redis

Both Cognito and Redis are external dependencies that must be mocked in tests:

- **Cognito:** Mock the `cognito_service` (or the boto3 client it uses). The mock should return a fake `cognito_sub` on user creation and succeed for all operations. Test error handling by making the mock raise exceptions.
- **Redis:** Mock the Redis client. The rate limit tests need the mock to track call counts. Other tests should have rate limiting pass-through (mock returns low counts).

### Constraints

- Do NOT create new Alembic migrations — all tables already exist.
- Do NOT build login or token refresh endpoints — those are client-side (AWS Amplify).
- Do NOT send actual emails in tests — mock SES/Cognito.
- The rate limit Redis dependency should be mockable via FastAPI dependency override in tests.
- Run `ruff check app/ tests/` and `mypy app/` after implementation.
- Run `pytest tests/ -v` to verify ALL tests pass (existing 93 + new Phase 5 tests).
