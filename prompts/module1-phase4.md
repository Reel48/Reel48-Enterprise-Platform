# Module 1 Phase 4 Prompt — CRUD Endpoints for Identity Entities

Copy everything below the line and paste it as your first message in a new Claude Code session.

---

Continue with Module 1 Phase 4 per the harness. Phases 1–3 are complete on `main` (`27a20f6`).

- **Phase 1** scaffolded the backend (FastAPI app, config, base models, Alembic, health endpoint, test skeleton).
- **Phase 2** created the 5 identity models (Company, SubBrand, User, Invite, OrgCode) and a single Alembic migration with RLS policies for all 5 tables.
- **Phase 3** added the auth plumbing: JWT validation (`security.py`), TenantContext dataclass (`tenant.py`), `get_tenant_context` dependency with `SET LOCAL` session variables (`dependencies.py`), TenantContextMiddleware, and 28 tests (auth + RLS isolation).

**Phase 4 scope: CRUD endpoints, Pydantic schemas, and service layer for the 5 Module 1 identity entities.**

No new models or migrations are needed — all 5 tables and their RLS policies already exist. This phase builds the API layer on top of them.

### What to build (in this order)

**1. Companies** (`reel48_admin`-only management + tenant-scoped read)

- **Schemas** (`app/schemas/company.py`): `CompanyCreate` (name, slug), `CompanyUpdate` (name, slug, is_active — all optional), `CompanyResponse` (all fields except `stripe_customer_id`)
- **Service** (`app/services/company_service.py`): CRUD with slug uniqueness validation. `create_company()` MUST atomically create the company AND a default sub-brand in one transaction (ADR-003). Soft delete is NOT needed for companies (use `is_active` deactivation).
- **Endpoints** (`app/api/v1/companies.py`):
  - `GET /api/v1/companies` — `reel48_admin`: list all companies (paginated). `corporate_admin`/below: return only their own company.
  - `GET /api/v1/companies/{company_id}` — `reel48_admin`: any company. Others: own company only (enforce via tenant context).
  - `POST /api/v1/companies` — `reel48_admin` only. Returns 201.
  - `PATCH /api/v1/companies/{company_id}` — `reel48_admin` only.
  - `DELETE /api/v1/companies/{company_id}` — `reel48_admin` only. Deactivates (`is_active = false`), does NOT delete.

**2. Sub-Brands** (company-scoped management)

- **Schemas** (`app/schemas/sub_brand.py`): `SubBrandCreate` (name, slug), `SubBrandUpdate` (name, slug, is_active — all optional), `SubBrandResponse`
- **Service** (`app/services/sub_brand_service.py`): CRUD with slug uniqueness within company. Cannot deactivate the last active sub-brand in a company. Cannot deactivate a default sub-brand.
- **Endpoints** (`app/api/v1/sub_brands.py`):
  - `GET /api/v1/sub_brands` — List sub-brands visible to the user. `corporate_admin`: all in their company. `sub_brand_admin`/below: their own sub-brand only (application-layer filter on `context.sub_brand_id`; RLS handles company isolation).
  - `GET /api/v1/sub_brands/{sub_brand_id}` — Single sub-brand (tenant-scoped).
  - `POST /api/v1/sub_brands` — `corporate_admin` or above. Company ID comes from tenant context (not request body).
  - `PATCH /api/v1/sub_brands/{sub_brand_id}` — `corporate_admin` or above.
  - `DELETE /api/v1/sub_brands/{sub_brand_id}` — `corporate_admin` or above. Deactivates, does NOT delete. Reject if it's the default or the last active sub-brand.

**3. Org Codes** (company-level, `corporate_admin`+)

- **Schemas** (`app/schemas/org_code.py`): `OrgCodeResponse` (id, company_id, code, is_active, created_by, created_at). No `OrgCodeCreate` body needed — the code is auto-generated server-side.
- **Service** (`app/services/org_code_service.py`): Generate 8-char uppercase alphanumeric code (30-char alphabet excluding 0/O/1/I/L). Auto-deactivate the previous active code for the same company. Validate code format.
- **Endpoints** (`app/api/v1/org_codes.py`):
  - `POST /api/v1/org_codes` — `corporate_admin` or above. Generates a new code, deactivates previous. Returns 201.
  - `GET /api/v1/org_codes/current` — `corporate_admin` or above. Returns the current active code for the user's company.
  - `DELETE /api/v1/org_codes/{org_code_id}` — `corporate_admin` or above. Deactivates (sets `is_active = false`), does NOT delete.

**4. Users** (tenant-scoped management)

- **Schemas** (`app/schemas/user.py`): `UserCreate` (email, full_name, role, sub_brand_id — for admin-created users), `UserUpdate` (full_name, role, sub_brand_id, is_active — all optional), `UserResponse` (exclude `cognito_sub` and `deleted_at` from response)
- **Service** (`app/services/user_service.py`): CRUD with email uniqueness validation. Soft delete (`deleted_at`). Exclude soft-deleted users from list/get queries (`deleted_at IS NULL`). Role changes must be validated (e.g., only `corporate_admin`+ can assign admin roles). Creating a user here is the **database record only** — Cognito user creation is a separate concern (Phase 5 or self-registration flow).
- **Endpoints** (`app/api/v1/users.py`):
  - `GET /api/v1/users` — `sub_brand_admin`+: list users in scope. `corporate_admin`: all users in company. `sub_brand_admin`: users in their sub-brand. Employees cannot list other users.
  - `GET /api/v1/users/{user_id}` — Admins: any user in scope. Employees: own profile only (`context.user_id` match).
  - `GET /api/v1/users/me` — Any authenticated user. Returns own profile.
  - `POST /api/v1/users` — `sub_brand_admin`+ (creates a user record; does NOT create Cognito user).
  - `PATCH /api/v1/users/{user_id}` — `sub_brand_admin`+ for users in scope. Employees can update own `full_name` only.
  - `DELETE /api/v1/users/{user_id}` — `sub_brand_admin`+. Soft delete (sets `deleted_at`).

**5. Invites** (admin-managed, company-scoped)

- **Schemas** (`app/schemas/invite.py`): `InviteCreate` (email, target_sub_brand_id, role — defaults to `employee`), `InviteResponse` (all fields; mask token in list responses, show full token only on create).
- **Service** (`app/services/invite_service.py`): Generate 64-char secure random token (`secrets.token_urlsafe`). Set `expires_at` to 72 hours from creation. Validate `target_sub_brand_id` belongs to the admin's company. Prevent duplicate active invites for the same email in the same company.
- **Endpoints** (`app/api/v1/invites.py`):
  - `GET /api/v1/invites` — `sub_brand_admin`+: list invites in scope. `corporate_admin`: all in company. `sub_brand_admin`: filtered by their `target_sub_brand_id`.
  - `POST /api/v1/invites` — `sub_brand_admin`+. `sub_brand_admin` can only invite to their own sub-brand; `corporate_admin` can invite to any sub-brand. Returns 201 with full token.
  - `DELETE /api/v1/invites/{invite_id}` — `sub_brand_admin`+. Hard delete (invites are transient).

### Wire up the router

Update `app/api/v1/router.py` to include all 5 new sub-routers. Uncomment and import each one.

### Cross-cutting requirements

1. **All endpoints use `TenantContext` from JWT** — never accept `company_id` or `sub_brand_id` as request parameters (except `target_sub_brand_id` in invite creation, which is validated server-side).
2. **Defense-in-depth filtering** — apply `company_id` and `sub_brand_id` filters in service queries alongside RLS.
3. **Standard response format** — wrap all responses in `ApiResponse[T]` or `ApiListResponse[T]` from `app/schemas/common`. Use `PaginationMeta` on list endpoints.
4. **Pagination** on all list endpoints — `page` (default 1) and `per_page` (default 20, max 100) query params.
5. **Error responses** use `AppException` subclasses from `app/core/exceptions` (`NotFoundError`, `ForbiddenError`, `ConflictError`, `ValidationError`).
6. **Role-checking** — use the existing dependency helpers (`require_reel48_admin`, `require_corporate_admin`, `require_admin`, `require_manager`) from `app/core/dependencies` where they fit. For more nuanced checks (e.g., employees can view own profile but not others), do explicit checks in the route or service.

### Tests

For each entity, write tests in a single file (`tests/test_companies.py`, `tests/test_sub_brands.py`, etc.) covering:

1. **Functional**: Create, read, update, delete operations (happy path + error cases).
2. **Authorization**: Verify role restrictions (e.g., employee cannot create a company, `sub_brand_admin` cannot create an org code).
3. **Isolation**: Company A cannot see Company B's data. Sub-Brand A2 cannot see Sub-Brand A1's users (within the same company). Corporate admin CAN see all sub-brands.

Use the existing test infrastructure from `conftest.py` — `client`, `admin_db_session`, `company_a`, `company_b`, token fixtures, and `create_test_token()`.

### Constraints

- Do NOT build the self-registration endpoints (`POST /api/v1/auth/validate-org-code` and `POST /api/v1/auth/register`) in this phase — those require Cognito integration and rate limiting (Redis), which are separate concerns for a later phase.
- Do NOT build Cognito user creation — `POST /api/v1/users` creates a **database record only**. The Cognito-side user provisioning is out of scope.
- Do NOT create new Alembic migrations — all tables already exist.
- Run `ruff check app/ tests/` and `mypy app/` after implementation to ensure linting and type-checking pass.
- Run `pytest tests/ -v` to verify all tests pass (existing Phase 3 tests + new Phase 4 tests). The 14 non-DB tests should still pass without PostgreSQL; DB-dependent tests require a running PostgreSQL instance.
