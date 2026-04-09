# Reel48+ Backend — CLAUDE.md
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This is the BACKEND-SPECIFIC CLAUDE.md. Claude Code reads it              ║
# ║  automatically whenever working on files inside /backend. It supplements   ║
# ║  the root CLAUDE.md with FastAPI, SQLAlchemy, and Python-specific          ║
# ║  conventions.                                                              ║
# ║                                                                            ║
# ║  WHY A SEPARATE FILE?                                                      ║
# ║                                                                            ║
# ║  Python/FastAPI has fundamentally different patterns than TypeScript/React. ║
# ║  Keeping them in separate files means Claude Code gets focused, relevant   ║
# ║  context when working in each part of the codebase. A single massive       ║
# ║  CLAUDE.md would dilute the important details.                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


## Framework & Configuration

- **Python 3.11+** (use modern syntax: `match` statements, `type` aliases, `|` union)
- **FastAPI** with async endpoints where I/O-bound (database, S3, SES)
- **SQLAlchemy 2.0** with async sessions
- **Alembic** for all database migrations
- **Pydantic v2** for request/response validation
- **pytest** for testing


## Local Development Setup

# --- ADDED 2026-04-07 after Phase 1 scaffolding ---
# Reason: No guidance existed for build backend, venv management, or first-run setup.
# Impact: Future sessions can activate the venv and run the app without guessing.

### Build Backend & Virtual Environment
- **Build backend:** Hatchling (`[build-system] requires = ["hatchling"]` in `pyproject.toml`)
- **Package config:** `[tool.hatch.build.targets.wheel] packages = ["app"]` — required because
  the package directory is named `app/`, not `reel48_backend/`
- **Virtual environment:** `backend/.venv/` — created with `python3.11 -m venv .venv`
- **Install:** `cd backend && source .venv/bin/activate && pip install -e ".[dev]"`
- **Run:** `uvicorn app.main:app --reload`
- **Environment variables:** Copy `.env.example` to `.env` and fill in values

### structlog Configuration
structlog is configured in `app/main.py` at module level. In DEBUG mode it uses
`ConsoleRenderer` (human-readable); in production it uses `JSONRenderer`. The
`merge_contextvars` processor is included so that tenant context can be bound to
log entries via `structlog.contextvars.bind_contextvars()` in the auth middleware.


## Project Structure

# --- WHY THIS SECTION EXISTS ---
# A layered architecture (routes → services → models) keeps business logic
# separate from HTTP concerns and database concerns. This makes code testable,
# reusable, and easier for Claude Code to generate correctly — it always knows
# which layer a piece of logic belongs in.

```
backend/
├── app/
│   ├── main.py                    # FastAPI app initialization, middleware, startup
│   ├── core/
│   │   ├── config.py              # Settings from environment variables (Pydantic BaseSettings)
│   │   ├── database.py            # SQLAlchemy engine, session factory, base model
│   │   ├── security.py            # JWT validation, password hashing utilities
│   │   └── dependencies.py        # FastAPI dependency injection functions
│   ├── middleware/
│   │   ├── auth.py                # Cognito JWT validation middleware
│   │   ├── tenant.py              # Sets PostgreSQL session variables for RLS
│   │   └── logging.py             # Request/response logging
│   ├── models/                    # SQLAlchemy ORM models (one file per entity)
│   │   ├── base.py                # GlobalBase, CompanyBase, TenantBase (see Model Base Classes)
│   │   ├── company.py
│   │   ├── sub_brand.py
│   │   ├── user.py
│   │   ├── invite.py              # Admin invite tokens (Module 1)
│   │   ├── org_code.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── bulk_order.py
│   │   └── invoice.py
│   ├── schemas/                   # Pydantic models for API request/response
│   │   ├── common.py              # Shared schemas (pagination, error response)
│   │   ├── company.py
│   │   ├── invite.py              # Invite create/response schemas
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── invoice.py
│   │   ├── org_code.py
│   │   └── user.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          # Aggregates all v1 route modules
│   │       ├── auth.py            # Register, validate-org-code (login & token refresh are Amplify client-side)
│   │       ├── companies.py
│   │       ├── sub_brands.py
│   │       ├── users.py
│   │       ├── products.py
│   │       ├── orders.py
│   │       ├── bulk_orders.py
│   │       ├── approvals.py
│   │       ├── invites.py              # Invite creation and management (admin)
│   │       ├── org_codes.py            # Org code management (corporate_admin)
│   │       ├── invoices.py
│   │       ├── webhooks.py            # Stripe webhook receiver
│   │       ├── analytics.py
│   │       └── platform/              # Reel48 admin endpoints (cross-company)
│   │           ├── bulk_orders.py     # Cross-company bulk order visibility
│   │           ├── catalogs.py        # Catalog management, pricing, approval
│   │           ├── invoices.py        # Invoice creation for client companies
│   │           └── companies.py       # Client company management
│   └── services/                  # Business logic (called by routes)
│       ├── company_service.py
│       ├── sub_brand_service.py
│       ├── user_service.py
│       ├── product_service.py
│       ├── order_service.py
│       ├── bulk_order_service.py
│       ├── approval_service.py
│       ├── invite_service.py      # Invite creation, token generation, consumption
│       ├── org_code_service.py    # Org code generation, validation, registration
│       ├── analytics_service.py
│       ├── email_service.py       # SES integration
│       ├── invoice_service.py     # Stripe invoice lifecycle
│       └── stripe_service.py      # Stripe API client wrapper
├── migrations/
│   ├── env.py
│   └── versions/                  # Alembic migration files
├── tests/
│   ├── conftest.py                # Shared fixtures (test DB, test tenants, auth tokens)
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_orders.py
│   ├── test_invoices.py
│   ├── test_self_registration.py  # Org code registration, rate limiting, isolation
│   ├── test_isolation.py          # Cross-tenant and cross-sub-brand access tests
│   └── factories/                 # Test data factories
│       ├── company_factory.py
│       └── user_factory.py
├── pyproject.toml
└── alembic.ini
```


## Authentication Middleware

# --- WHY THIS SECTION EXISTS ---
# This is the security gatekeeper. Every authenticated request passes through
# this middleware, which validates the JWT token, extracts the tenant context,
# and sets PostgreSQL session variables for RLS. If this middleware has a bug,
# every endpoint is vulnerable. Claude Code needs the exact pattern to follow.

### JWT Validation Flow
```python
# WHY: This dependency is injected into every protected endpoint via FastAPI's
# Depends() system. It validates the Cognito JWT, extracts tenant claims, and
# returns a structured TenantContext object. The rest of the endpoint code never
# touches the raw JWT — it only works with the validated, typed context.

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_tenant_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> TenantContext:
    """
    Validates the Cognito JWT and returns the tenant context.

    Steps:
    1. Decode and validate the JWT (signature, expiry, audience)
    2. Extract custom claims: company_id, sub_brand_id, role
    3. Set PostgreSQL session variables for RLS enforcement
    4. Return typed TenantContext
    """
    token = credentials.credentials
    claims = await validate_cognito_token(token)

    # Extract role FIRST — reel48_admin has no company_id or sub_brand_id in JWT.
    # Using .get() with None avoids KeyError for missing claims.
    role = claims["custom:role"]
    raw_company_id = claims.get("custom:company_id")  # None for reel48_admin
    raw_sub_brand_id = claims.get("custom:sub_brand_id")  # None for corporate_admin & reel48_admin

    context = TenantContext(
        user_id=claims["sub"],
        company_id=UUID(raw_company_id) if raw_company_id else None,
        sub_brand_id=UUID(raw_sub_brand_id) if raw_sub_brand_id else None,
        role=role,
    )

    # CRITICAL: Set PostgreSQL session variables so RLS policies can reference them.
    # Without this, RLS policies have no way to know which tenant is making the request.
    # For reel48_admin: company_id is empty string, which triggers the RLS bypass.
    # SET LOCAL scopes values to the current transaction only, preventing leakage
    # across pooled connections.
    # NOTE: SET LOCAL does not support bind parameters ($1) in PostgreSQL.
    # Values are safe — company_id and sub_brand_id are parsed as UUID from validated JWTs.
    if context.is_reel48_admin:
        await db.execute(text("SET LOCAL app.current_company_id = ''"))
        await db.execute(text("SET LOCAL app.current_sub_brand_id = ''"))
    else:
        await db.execute(
            text(f"SET LOCAL app.current_company_id = '{context.company_id}'")
        )
        if context.sub_brand_id:
            await db.execute(
                text(f"SET LOCAL app.current_sub_brand_id = '{context.sub_brand_id}'")
            )
        else:
            await db.execute(text("SET LOCAL app.current_sub_brand_id = ''"))

    # Bind tenant info to structlog so every downstream log line includes it
    structlog.contextvars.bind_contextvars(
        user_id=context.user_id,
        company_id=str(context.company_id) if context.company_id else None,
        sub_brand_id=str(context.sub_brand_id) if context.sub_brand_id else None,
        role=context.role,
    )

    return context
```

### SET LOCAL vs SET
# --- ADDED 2026-04-07 during Phase 3 implementation ---
# Reason: Connection pooling can leak SET variables between requests. SET LOCAL
# is scoped to the transaction and avoids this risk entirely.
# Impact: Prevents subtle tenant isolation leaks in production under load.

The auth middleware uses `SET LOCAL` (not `SET`) for PostgreSQL session variables. `SET LOCAL`
scopes the value to the current **transaction** only — when the transaction commits or rolls
back, the value is discarded. Since `get_db_session()` wraps each request in a transaction,
this ensures session variables never leak between requests on the same pooled connection.
Plain `SET` persists for the connection's lifetime, which is dangerous with connection pooling.

### SET LOCAL Does Not Support Bind Parameters
# --- ADDED 2026-04-07 after Module 1 Phase 4 ---
# Reason: Using parameterized queries (`text("SET LOCAL ... = :val")`) with SET LOCAL
# causes `PostgresSyntaxError: syntax error at or near "$1"`. PostgreSQL's SET statement
# does not support bind parameters.
# Impact: All SET LOCAL calls must use f-string interpolation. This is safe because the
# values are UUIDs parsed from validated JWTs, not user-supplied strings.

PostgreSQL's `SET LOCAL` does not support bind parameters (`$1`, `:param`). You must use
f-string interpolation for the values. This is safe in the auth middleware because values
are UUIDs parsed from validated JWT claims (not raw user input):

```python
# ✅ CORRECT — f-string (safe: values are validated UUIDs from JWTs)
await db.execute(text(f"SET LOCAL app.current_company_id = '{context.company_id}'"))

# ❌ WRONG — bind parameters cause PostgresSyntaxError
await db.execute(text("SET LOCAL app.current_company_id = :cid"), {"cid": str(context.company_id)})
```

### SQLAlchemy: Refresh After Flush for Server-Side Column Updates
# --- ADDED 2026-04-07 after Module 1 Phase 4 ---
# Reason: SQLAlchemy's `onupdate=func.now()` expires the `updated_at` attribute after
# flush(). When Pydantic's `model_validate(from_attributes=True)` reads it, it triggers
# a lazy load outside the greenlet context, causing MissingGreenlet errors.
# Impact: All service methods that modify and return objects must refresh after flush.

When a model has `server_default` or `onupdate` columns (like `updated_at`), SQLAlchemy
marks those attributes as expired after `flush()`. If Pydantic tries to read the expired
attribute (e.g., during `model_validate()`), it triggers a lazy load that fails with
`MissingGreenlet` in async code. Always `await db.refresh(obj)` after `flush()` when
the object will be serialized:

```python
# ✅ CORRECT — refresh reloads expired attributes
await self.db.flush()
await self.db.refresh(obj)
return obj  # Safe for Pydantic serialization

# ❌ WRONG — expired updated_at causes MissingGreenlet
await self.db.flush()
return obj  # Pydantic reads updated_at → lazy load → crash
```

### Login & Token Refresh
# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: Ambiguity about whether login/refresh were backend endpoints or client-side.
# Impact: Claude Code knows NOT to build backend login/refresh endpoints.

Login and token refresh are handled **entirely client-side** by AWS Amplify
(`@aws-amplify/auth`). There are NO backend endpoints for login or token refresh.
Amplify communicates directly with Cognito. The backend only validates JWTs — it
never issues them.

### Unauthenticated Endpoint Exceptions
# --- UPDATED 2026-04-07 after Module 1 Phase 5 ---
# Reason: Added invite registration endpoint and generic error response pattern.
# Impact: All unauthenticated endpoints are documented.
Four endpoints do NOT use `get_tenant_context` because they receive requests without JWTs:
1. **`POST /api/v1/webhooks/stripe`** — Stripe webhook. Secured by signature verification.
2. **`POST /api/v1/auth/validate-org-code`** — Validates an org code and returns the
   company name + list of sub-brands. Rate-limited (5 attempts per IP per 15 minutes).
3. **`POST /api/v1/auth/register`** — Self-registration via org code. Accepts the org
   code, employee-selected `sub_brand_id`, and user details. The `sub_brand_id` is
   validated server-side to confirm it belongs to the org code's company.
   Rate-limited (shares the same 5 attempts/IP/15 min window as validate-org-code).
   See ADR-007 for full details.
4. **`POST /api/v1/auth/register-from-invite`** — Invite-based registration. Validates
   the invite token (not expired, not consumed, email match), creates the Cognito user,
   and inserts the local User record. NOT rate-limited (token is single-use).

**Generic error responses:** All auth endpoints return identical error messages regardless
of the specific failure cause (invalid code vs inactive code vs duplicate email). This
prevents enumeration attacks. Use `AppException(code="REGISTRATION_FAILED", message="Registration failed")`
for all registration failures and `AppException(code="INVALID_REQUEST", message="Invalid registration code")`
for all org code validation failures.

### TenantContext Model
# --- UPDATED 2026-04-07 during Phase 3 implementation ---
# Reason: Original example used `Optional[UUID]` syntax; implementation uses modern
# `UUID | None` union syntax (Python 3.10+). Updated to match actual code.
# Impact: Harness examples match the codebase.
```python
# WHY: A dataclass rather than a dict ensures type safety.
# Every endpoint that uses TenantContext gets autocomplete and type checking,
# preventing bugs like misspelling "company_id" as "companyId".
# Lives in: app/core/tenant.py

from dataclasses import dataclass
from uuid import UUID

@dataclass
class TenantContext:
    user_id: str
    company_id: UUID | None   # None for reel48_admin (cross-company access)
    sub_brand_id: UUID | None  # None for corporate_admin & reel48_admin
    role: str  # One of: reel48_admin, corporate_admin, sub_brand_admin, regional_manager, employee

    @property
    def is_reel48_admin(self) -> bool:
        """Platform operator. Cross-company access."""
        return self.role == "reel48_admin"

    @property
    def is_corporate_admin_or_above(self) -> bool:
        """Corporate admin or platform admin. Use for: manage sub-brands,
        manage all users, generate org codes, view company-wide analytics."""
        return self.role in ("reel48_admin", "corporate_admin")

    @property
    def is_admin(self) -> bool:
        """Any admin role (including sub_brand_admin). Use for: create products,
        manage catalog, approve orders. WARNING: Do NOT use for operations
        restricted to corporate_admin+ (use is_corporate_admin_or_above instead)."""
        return self.role in ("reel48_admin", "corporate_admin", "sub_brand_admin")

    @property
    def is_manager_or_above(self) -> bool:
        """Regional manager or any admin. Use for: create bulk orders, approve orders."""
        return self.role in ("reel48_admin", "corporate_admin", "sub_brand_admin", "regional_manager")
```

### `reel48_admin` and `company_id`: NULL vs Empty String
**Important distinction:** The `reel48_admin` role has `company_id = None` in the Python
`TenantContext` dataclass (because platform admins don't belong to any company). However,
the auth middleware sets the PostgreSQL session variable `app.current_company_id` to an
**empty string** (`''`), not NULL. This is because PostgreSQL's `current_setting()` returns
a string, and the RLS company isolation policy checks for `= ''` as the bypass signal.
In short: **`None` in Python, `''` in PostgreSQL** — both represent "no company scope."

### TenantContext.user_id vs users.id (created_by FK Pattern)

# --- ADDED 2026-04-08 after Module 1 post-module review ---
# Reason: Multiple endpoints need to set `created_by` FKs, but TenantContext.user_id
# is the Cognito 'sub' string, not the local users.id UUID. Without guidance, Claude
# Code may incorrectly use TenantContext.user_id as a FK value.
# Impact: Future modules correctly resolve the local user ID for FK columns.

`TenantContext.user_id` is the Cognito `sub` (a string). FK columns like `created_by`
reference `users.id` (a UUID). These are different values. To bridge this gap, use
`resolve_current_user_id(db, context.user_id)` from `app.services.helpers`:

```python
from app.services.helpers import resolve_current_user_id

# In route handler:
created_by = await resolve_current_user_id(db, context.user_id)
org_code = await service.generate_code(company_id, created_by)
```

This helper looks up the User record by `cognito_sub` and returns the `users.id` UUID.
It raises `NotFoundError` if no matching user exists (which shouldn't happen for
authenticated users, but provides defense-in-depth).


## Endpoint Pattern

# --- WHY THIS SECTION EXISTS ---
# A consistent endpoint structure means Claude Code generates routes that all
# look and behave the same way. This makes the codebase predictable and
# makes it easy to review generated code — you know exactly what to look for.

Every API endpoint follows this structure:

```python
# WHY: The layered pattern (route → service → model) separates concerns:
# - Routes handle HTTP (request parsing, response formatting, status codes)
# - Services handle business logic (validation, authorization, orchestration)
# - Models handle data access (queries, mutations)
# This means you can test business logic without spinning up an HTTP server.

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_tenant_context, get_db_session
from app.schemas.product import ProductCreate, ProductResponse, ProductListResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])

@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = 1,
    per_page: int = 20,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List products visible to the current user.

    - Corporate admin: sees all products across all sub-brands
    - Sub-brand admin/manager/employee: sees only their sub-brand's catalog
    """
    service = ProductService(db)
    products, total = await service.list_products(
        company_id=context.company_id,
        sub_brand_id=context.sub_brand_id,  # None for corporate_admin → no sub-brand filter
        page=page,
        per_page=per_page,
    )
    return ProductListResponse(
        data=products,
        meta={"page": page, "per_page": per_page, "total": total},
        errors=[],
    )


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new product. Requires admin role."""
    if not context.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    service = ProductService(db)
    product = await service.create_product(
        data=product_in,
        company_id=context.company_id,
        sub_brand_id=context.sub_brand_id,
    )
    return ProductResponse(data=product, errors=[])
```

### Company-Scoped Endpoint Guard

# --- ADDED 2026-04-08 after Module 1 post-module review ---
# Reason: Three route files independently created the same guard pattern to reject
# reel48_admin requests on tenant-scoped CRUD endpoints. Documenting it prevents
# inconsistent implementations in future modules.
# Impact: Future modules use a consistent guard for company-scoped endpoints.

For tenant CRUD endpoints that operate within a single company (not platform-wide),
add a guard that rejects `reel48_admin` requests with a redirect to platform endpoints.
The `reel48_admin` role has `company_id = None` in TenantContext, so these endpoints
cannot determine which company to operate on:

```python
def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped write endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError(
            "Use platform endpoints for cross-company operations"
        )
    return context.company_id
```

This is a **route-level** helper (defined at the top of each route module), not a
FastAPI dependency. It is called inside route handlers after `get_tenant_context`.

### Platform Admin Endpoint Pattern

# --- ADDED 2026-04-08 after Module 3 Phase 4 ---
# Reason: Module 3 introduced the first platform admin endpoints for approval workflow.
# Impact: Future modules (Invoicing, Analytics) follow the same pattern for reel48_admin
# cross-company endpoints.

Platform admin endpoints live under `/api/v1/platform/{resource}/` and use
`require_reel48_admin` as their auth dependency. Key differences from tenant endpoints:

1. **No `_require_company_id` guard** — reel48_admin has no company_id (that's the point).
2. **Cross-company queries** — Service methods like `list_all_products()` skip the
   `company_id` filter. Optional `?company_id=` query param for narrowing results.
3. **`resolve_current_user_id`** — Platform endpoints that set `approved_by` must resolve
   the admin's local User ID from their cognito_sub. This requires a reel48_admin User
   record to exist in the database (associated with an internal "Reel48 Operations" company).
4. **Status transition actions** — Endpoints like `/approve`, `/reject`, `/activate` are
   POST actions on individual resources, not PATCH updates.

```python
# Platform endpoint pattern:
router = APIRouter(prefix="/platform/products", tags=["platform-products"])

@router.post("/{product_id}/approve", response_model=ApiResponse[ProductResponse])
async def approve_product(
    product_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProductResponse]:
    approved_by = await resolve_current_user_id(db, context.user_id)
    service = ProductService(db)
    product = await service.approve_product(product_id, approved_by)
    return ApiResponse(data=ProductResponse.model_validate(product))
```

### Delete Endpoint Return Conventions

# --- ADDED 2026-04-08 after Module 1 post-module review ---
# Reason: Inconsistent HTTP status codes for soft-delete vs hard-delete endpoints
# across Module 1 (companies/sub_brands returned 200, users returned 204).
# Impact: Future modules return consistent status codes for delete operations.

- **Soft-delete** (sets `deleted_at` or `is_active = false`): Return **200** with
  `ApiResponse[T]` containing the deactivated/deleted resource. The caller sees the
  final state of the record.
- **Hard-delete** (row permanently removed): Return **204 No Content** with no body.
  The resource no longer exists, so there is nothing to return.


### PUT /me Upsert Pattern for Owned Resources

# --- ADDED 2026-04-08 after Module 2 Phase 1 ---
# Reason: Employee profiles introduced a "one resource per user" pattern where
# the client shouldn't need to check existence before creating/updating.
# Impact: Future modules with per-user resources (preferences, settings) follow
# the same upsert pattern.

When a resource has a 1:1 relationship with the authenticated user (e.g., employee
profile, user preferences), use a `PUT /me` upsert endpoint instead of separate
POST + PUT:

```python
@router.put("/me", response_model=ApiResponse[ResourceResponse])
async def upsert_my_resource(
    data: ResourceCreate,  # NOT ResourceUpdate — employees cannot set admin-only fields
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
):
    user_id = await resolve_current_user_id(db, context.user_id)
    service = ResourceService(db)
    resource = await service.upsert(user_id, context.company_id, context.sub_brand_id, data)
    return ApiResponse(data=ResourceResponse.model_validate(resource))
```

**Key rules:**
- Use `ResourceCreate` schema (not `Update`) so employees cannot set admin-only fields
  (e.g., `onboarding_complete`). Admin-only updates go through `PATCH /{id}`.
- The service checks for an existing record by `user_id`; creates if not found, updates
  if found. Always `flush()` + `refresh()` before returning.
- Returns 200 in both create and update cases (upsert is idempotent).

### Trailing Slash Behavior in Tests

# --- ADDED 2026-04-08 after Module 2 Phase 1 ---
# Reason: FastAPI redirects `/profiles` to `/profiles/` with a 307, causing tests
# that omit the trailing slash to fail with unexpected 307 responses.
# Impact: All future tests use trailing slashes on list endpoint URLs.

FastAPI's default `redirect_slashes=True` causes `GET /api/v1/profiles` to return
a **307 Temporary Redirect** to `/api/v1/profiles/`. In tests, always include the
trailing slash for list endpoints:

```python
# ✅ CORRECT — trailing slash for list endpoints
await client.get("/api/v1/profiles/", headers=...)

# ❌ WRONG — causes 307 redirect in tests
await client.get("/api/v1/profiles", headers=...)
```

This applies to all `router.get("/")` list endpoints. Individual resource endpoints
(`/profiles/me`, `/profiles/{id}`) are not affected.


## Service Layer Pattern

# --- WHY THIS SECTION EXISTS ---
# Services contain the business logic that Claude Code needs to get right.
# By defining the pattern here, Claude Code knows to put authorization checks,
# validation, and orchestration in services — not in routes or models.

```python
# WHY: Services are where the real work happens. They orchestrate between
# models, apply business rules, and handle cross-cutting concerns. Routes
# just parse HTTP and call services. This separation means business logic
# is testable without HTTP overhead.

class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_products(
        self,
        company_id: UUID,
        sub_brand_id: Optional[UUID],
        page: int,
        per_page: int,
    ) -> tuple[list[Product], int]:
        """
        List products with tenant scoping.

        Note: RLS policies handle the base isolation, but we still apply
        explicit filters for clarity and defense-in-depth. If RLS is
        accidentally disabled, the explicit filters still protect the data.
        """
        query = select(Product).where(Product.company_id == company_id)

        # Sub-brand scoping (corporate_admin has sub_brand_id=None, sees all)
        if sub_brand_id is not None:
            query = query.where(Product.sub_brand_id == sub_brand_id)

        # Pagination
        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        return result.scalars().all(), total
```

### Company Creation & Default Sub-Brand Atomicity

# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: ADR-003 requires atomic company + default sub-brand creation, but no
# guidance on which service owns the transaction.
# Impact: Prevents companies from existing without a default sub-brand.

`company_service.create_company()` is responsible for atomically creating both the
company AND its default sub-brand in a single database transaction. This ensures the
ADR-003 guarantee that every company always has at least one sub-brand. The service
either creates both records or neither (rollback on failure). Do NOT split this across
two separate service calls or two separate transactions.


### External Service Integration Pattern (Dependency Injection)

# --- ADDED 2026-04-07 after Module 1 Phase 5 ---
# Reason: CognitoService established a reusable pattern for wrapping external APIs
# (boto3, Stripe, SES) as injectable FastAPI dependencies. Future services (Stripe,
# SES, S3) should follow the same pattern.
# Impact: Consistent external service integration across all modules.

External AWS services (Cognito, Stripe, SES, S3) are wrapped in service classes and
injected as FastAPI dependencies. This centralizes credential management and enables
easy test mocking via `app.dependency_overrides`.

```python
# Pattern: Service class + FastAPI dependency factory

class CognitoService:
    def __init__(self, client: Any, user_pool_id: str) -> None:
        self._client = client  # boto3 client (injected)
        self._user_pool_id = user_pool_id

    async def create_cognito_user(self, ...) -> str:
        try:
            response = self._client.admin_create_user(...)
            return self._extract_sub(response)
        except self._client.exceptions.UsernameExistsException:
            raise ConflictError(...)  # Map AWS exceptions to AppExceptions

def get_cognito_service() -> CognitoService:
    """FastAPI dependency — creates boto3 client + returns service."""
    import boto3  # type: ignore[import-untyped]
    client = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)
    return CognitoService(client, settings.COGNITO_USER_POOL_ID)

# In routes: inject via Depends()
@router.post("/")
async def create_user(
    cognito_service: CognitoService = Depends(get_cognito_service),
): ...

# In tests: override via dependency_overrides
app.dependency_overrides[get_cognito_service] = lambda: mock_cognito_service
```

**Key rules:**
- boto3 imports live ONLY in the dependency factory (lazy import), not at module top level
- Map AWS SDK exceptions to `AppException` subclasses inside the service class
- Services that need an external service accept it as an **optional constructor parameter**
  for backward compatibility (e.g., `UserService(db, cognito_service=None)`)


## Pydantic Schema Conventions

# --- WHY THIS SECTION EXISTS ---
# Pydantic schemas validate incoming data and serialize outgoing data. Having
# consistent patterns here prevents Claude Code from mixing up request schemas
# with response schemas or forgetting to exclude sensitive fields from responses.

```python
# WHY: Separate Create/Update/Response schemas enforce the principle that
# what you accept in a request is different from what you return in a response.
# For example, you never return a password hash, and you never accept an ID
# in a create request (the server generates it).

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

# --- Base schemas (shared fields) ---
class ProductBase(BaseModel):
    name: str
    description: str | None = None
    unit_price: float
    sku: str

# --- Request schemas ---
class ProductCreate(ProductBase):
    """Used for POST /products. No id, no timestamps — server generates those."""
    decoration_options: list[str] = []
    sizes: list[str] = []

class ProductUpdate(BaseModel):
    """Used for PATCH /products/{id}. All fields optional for partial updates."""
    name: str | None = None
    description: str | None = None
    unit_price: float | None = None

# --- Response schemas ---
class ProductResponse(BaseModel):
    """Used in API responses. Includes server-generated fields."""
    model_config = ConfigDict(from_attributes=True)  # Allows from SQLAlchemy models

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    name: str
    description: str | None
    unit_price: float
    sku: str
    created_at: datetime
    updated_at: datetime

# --- Standard API wrapper (matches the format defined in root CLAUDE.md) ---
class ApiResponse[T](BaseModel):
    data: T
    meta: dict = {}
    errors: list = []
```


## Model Base Classes

# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: The root CLAUDE.md defines TenantBase (company_id + sub_brand_id), but several
# Module 1 tables don't fit that shape. Without alternatives, Claude Code must invent
# ad-hoc base classes inconsistently.
# Impact: Every model has a clear, correct base class to inherit from.

Not every table has both `company_id` AND `sub_brand_id`. Use the right base for
each table:

```python
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
from uuid import uuid4

class Base(DeclarativeBase):
    """SQLAlchemy declarative base. All models inherit from this (directly or via mixins)."""
    pass

class GlobalBase(Base):
    """
    For tables with NO tenant isolation columns.
    Used by: companies (the tenant identity table itself)
    """
    __abstract__ = True

    id = Column(UUID, primary_key=True, default=uuid4)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class CompanyBase(Base):
    """
    For tables scoped to a company but NOT to a sub-brand.
    Used by: sub_brands, org_codes, invites (company-level entities)
    """
    __abstract__ = True

    id = Column(UUID, primary_key=True, default=uuid4)
    company_id = Column(UUID, ForeignKey("companies.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class TenantBase(Base):
    """
    For tables scoped to BOTH company AND sub-brand (the common case).
    Used by: users, products, orders, bulk_orders, invoices, etc.
    """
    __abstract__ = True

    id = Column(UUID, primary_key=True, default=uuid4)
    company_id = Column(UUID, ForeignKey("companies.id"), nullable=False, index=True)
    sub_brand_id = Column(UUID, ForeignKey("sub_brands.id"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

### Which Base to Use

| Table | Base Class | Why |
|-------|-----------|-----|
| `companies` | `GlobalBase` | IS the tenant — has no company_id FK |
| `sub_brands` | `CompanyBase` | Belongs to a company, but IS the sub-brand — no sub_brand_id FK |
| `org_codes` | `CompanyBase` | Company-level codes, no sub-brand scoping |
| `invites` | `CompanyBase` | Invite targets a sub-brand, but the FK is explicit (`target_sub_brand_id`), not the TenantBase `sub_brand_id` |
| `users` | `TenantBase` | Scoped to company + sub-brand |
| `employee_profiles` | `TenantBase` | Scoped to company + sub-brand (one per user) |
| `products` | `TenantBase` | Scoped to company + sub-brand |
| `orders` | `TenantBase` | Scoped to company + sub-brand |
| `order_line_items` | `TenantBase` | Scoped to company + sub-brand |
| `bulk_orders` | `TenantBase` | Scoped to company + sub-brand |
| `bulk_order_items` | `TenantBase` | Scoped to company + sub-brand |
| `approval_requests` | `TenantBase` | Scoped to company + sub-brand |
| `approval_rules` | `CompanyBase` | Company-level rules, no sub-brand scoping |
| `invoices` | `TenantBase` | Scoped to company + sub-brand |


## Database Session & RLS Setup

# --- WHY THIS SECTION EXISTS ---
# Every database query must run in a session that has the tenant context
# variables set, so RLS policies can filter data correctly. This section
# shows exactly how to configure the session — getting this wrong means
# RLS doesn't work and all tenants can see all data.

```python
# WHY: The get_db_session dependency creates a new session for each request,
# sets the tenant context variables, and ensures the session is properly
# closed after the request completes. The tenant variables are what RLS
# policies reference to filter data.

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### CRITICAL: Session Sharing Between Dependencies

# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: The harness showed get_tenant_context and route handlers both using
# Depends(get_db_session) without explaining they receive the SAME session.
# Impact: Prevents silent RLS bypass from accidental session duplication.

FastAPI **de-duplicates** generator dependencies within a single request. When both
`get_tenant_context` and a route handler declare `db: AsyncSession = Depends(get_db_session)`,
they receive the **same session instance**. This is essential — `get_tenant_context` sets
the PostgreSQL session variables (`app.current_company_id`, `app.current_sub_brand_id`)
on that session, and the route's queries execute against the same session with those
variables in effect.

**Rules:**
1. **Never create alternative session factories** or wrapper dependencies (e.g.,
   `get_readonly_session()`). A second factory produces a separate session without
   RLS variables set — silently exposing all tenant data.
2. **Never import `get_db_session` from a different module path.** FastAPI de-duplicates
   by object identity. If two imports resolve to different function objects, you get
   two sessions.
3. **Always import from `app.core.dependencies`** — the single canonical source.
4. If you need a session outside of a request context (e.g., in a background task or
   CLI script), you must manually set the RLS session variables before executing queries.


## Deletion Strategy

# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: No project-wide default for soft vs hard deletes. CRUD prompt asks but harness didn't answer.
# Impact: Claude Code applies consistent deletion patterns across all modules.

- **User-facing entities** (users, products, orders, invoices, catalogs, sub-brands):
  Use **soft delete** with a `deleted_at` (DateTime, nullable) column. Soft-deleted
  records are excluded from queries by default but retained for audit trails and
  potential recovery. Add a `deleted_at IS NULL` filter in service layer queries.
- **Transient/internal data** (invite tokens, rate limit counters, session data):
  Use **hard delete**. No audit trail needed for ephemeral records.
- **Org codes:** Use **deactivation** (`is_active = false`), not deletion. Org codes
  are never deleted because they may be referenced by user `org_code_id` foreign keys.


## Module 1 Table Schemas

# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: companies, sub_brands, users, and invites are built in Module 1 but had no
# defined schemas. Without these, Claude Code must guess at column lists.
# Impact: Module 1 tables are fully specified before implementation begins.

### `companies` Table (GlobalBase)
```
id                      UUID        PRIMARY KEY
name                    VARCHAR(255) NOT NULL
slug                    VARCHAR(100) NOT NULL UNIQUE  -- URL-safe identifier
stripe_customer_id      TEXT        NULL              -- Set during Stripe onboarding
is_active               BOOLEAN     NOT NULL DEFAULT true
created_at              TIMESTAMP   NOT NULL
updated_at              TIMESTAMP   NOT NULL
```
RLS: `companies_isolation` policy matching `id` against `app.current_company_id`.

### `sub_brands` Table (CompanyBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
name                    VARCHAR(255) NOT NULL
slug                    VARCHAR(100) NOT NULL          -- Unique within company
is_default              BOOLEAN     NOT NULL DEFAULT false
is_active               BOOLEAN     NOT NULL DEFAULT true
created_at              TIMESTAMP   NOT NULL
updated_at              TIMESTAMP   NOT NULL

UNIQUE(company_id, slug)
```
RLS: Company isolation only (no sub-brand scoping — this IS the sub-brand).
`is_default = true` for the auto-created default sub-brand (see ADR-003).

### `users` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
cognito_sub             VARCHAR(255) NOT NULL UNIQUE   -- Cognito user ID (maps to JWT "sub")
email                   VARCHAR(255) NOT NULL UNIQUE   -- Globally unique (matches Cognito user pool constraint)
full_name               VARCHAR(255) NOT NULL
role                    VARCHAR(50)  NOT NULL           -- Duplicated from Cognito for local queries
registration_method     VARCHAR(20)  NOT NULL DEFAULT 'invite'  -- 'invite' or 'self_registration'
org_code_id             UUID        NULL (FK → org_codes)       -- Set for self-registered users
is_active               BOOLEAN     NOT NULL DEFAULT true
deleted_at              TIMESTAMP   NULL               -- Soft delete
created_at              TIMESTAMP   NOT NULL
updated_at              TIMESTAMP   NOT NULL
```
RLS: Standard company isolation + sub-brand scoping.
`sub_brand_id` is NULL for `corporate_admin` users (they span all sub-brands).
`role` is stored locally to enable role-based queries without parsing JWTs (e.g.,
"list all admins in this company"). Cognito remains the authoritative source for
auth decisions; the local copy is for query convenience.

### `invites` Table (CompanyBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
target_sub_brand_id     UUID        NOT NULL (FK → sub_brands)  -- The sub-brand the invitee joins
email                   VARCHAR(255) NOT NULL
role                    VARCHAR(50)  NOT NULL DEFAULT 'employee'
token                   VARCHAR(64)  NOT NULL UNIQUE   -- Secure random token
expires_at              TIMESTAMP   NOT NULL           -- 72 hours from creation
consumed_at             TIMESTAMP   NULL               -- Set when invite is used
created_by              UUID        NOT NULL (FK → users)
created_at              TIMESTAMP   NOT NULL
updated_at              TIMESTAMP   NOT NULL
```
RLS: Company isolation only (no `sub_brand_id` column — uses `target_sub_brand_id` FK instead).
Note: Uses `CompanyBase`, not `TenantBase`, because the FK to sub_brands is explicitly
named `target_sub_brand_id` (the invite targets a sub-brand, but isn't "owned by" one).

### `org_codes` Table (CompanyBase)
# --- ADDED 2026-04-06 during pre-production harness review ---
# Reason: org_codes schema was in self-registration.md but missing from canonical Module 1 section.
# Impact: All Module 1 tables are defined in one place for implementation consistency.
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
code                    VARCHAR(8)  NOT NULL UNIQUE   -- 8-char uppercase alphanumeric (30-char alphabet)
is_active               BOOLEAN     NOT NULL DEFAULT true
created_by              UUID        NOT NULL (FK → users)
created_at              TIMESTAMP   NOT NULL
updated_at              TIMESTAMP   NOT NULL
```
RLS: Company isolation only (no `sub_brand_id` — org codes are per-company).
Only one active code per company at a time. Generating a new code deactivates the previous.
Public lookup (unauthenticated `POST /api/v1/auth/register`) queries this table via direct
`WHERE code = :code` outside the RLS-scoped session. See ADR-007.


## Module 2 Table Schema

### `employee_profiles` Table (TenantBase)
# --- ADDED 2026-04-08 during Module 2 Phase 1 ---
# Reason: Module 2 adds the employee_profiles table. Documenting it here for
# implementation consistency with Module 1 table schemas.
# Impact: Future modules know the employee_profiles shape for FK references.
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
user_id                 UUID        NOT NULL UNIQUE (FK → users)
department              VARCHAR(255) NULL
job_title               VARCHAR(255) NULL
location                VARCHAR(255) NULL       -- office/site name
shirt_size              VARCHAR(10)  NULL       -- XS, S, M, L, XL, 2XL, 3XL
pant_size               VARCHAR(20)  NULL
shoe_size               VARCHAR(20)  NULL
delivery_address_line1  VARCHAR(255) NULL
delivery_address_line2  VARCHAR(255) NULL
delivery_city           VARCHAR(100) NULL
delivery_state          VARCHAR(100) NULL
delivery_zip            VARCHAR(20)  NULL
delivery_country        VARCHAR(100) NULL
notes                   TEXT         NULL
profile_photo_url       TEXT         NULL       -- S3 pre-signed URL (upload TBD)
onboarding_complete     BOOLEAN      NOT NULL DEFAULT false
deleted_at              TIMESTAMP    NULL       -- soft delete
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
One profile per user (UNIQUE on `user_id`). Created via `PUT /profiles/me` upsert.
Composite index on `(company_id, department)` for common query pattern.


## Module 3 Table Schemas

### `products` Table (TenantBase)
# --- ADDED 2026-04-08 during Module 3 Phase 1 ---
# Reason: Module 3 adds product catalog tables. Documenting them here for
# implementation consistency and FK references in future modules.
# Impact: Future modules (Ordering, Invoicing) know the products/catalogs shape.
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
name                    VARCHAR(255) NOT NULL
description             TEXT         NULL
sku                     VARCHAR(100) NOT NULL
unit_price              NUMERIC(10,2) NOT NULL, CHECK >= 0
sizes                   JSONB        NOT NULL DEFAULT '[]'
decoration_options      JSONB        NOT NULL DEFAULT '[]'
image_urls              JSONB        NOT NULL DEFAULT '[]'
status                  VARCHAR(20)  NOT NULL DEFAULT 'draft'  -- draft|submitted|approved|active|archived
approved_by             UUID         NULL (FK → users)
approved_at             TIMESTAMP    NULL
created_by              UUID         NOT NULL (FK → users)
deleted_at              TIMESTAMP    NULL       -- soft delete
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
Partial unique index: `(company_id, sku) WHERE deleted_at IS NULL`.
Composite index: `(company_id, status)`.

### `catalogs` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
name                    VARCHAR(255) NOT NULL
description             TEXT         NULL
slug                    VARCHAR(100) NOT NULL
payment_model           VARCHAR(30)  NOT NULL   -- 'self_service' | 'invoice_after_close'
status                  VARCHAR(20)  NOT NULL DEFAULT 'draft'  -- draft|submitted|approved|active|closed|archived
buying_window_opens_at  TIMESTAMP    NULL
buying_window_closes_at TIMESTAMP    NULL
approved_by             UUID         NULL (FK → users)
approved_at             TIMESTAMP    NULL
created_by              UUID         NOT NULL (FK → users)
deleted_at              TIMESTAMP    NULL       -- soft delete
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
Partial unique index: `(company_id, slug) WHERE deleted_at IS NULL`.
Composite index: `(company_id, status)`.

### `catalog_products` Junction Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
catalog_id              UUID        NOT NULL (FK → catalogs)
product_id              UUID        NOT NULL (FK → products)
display_order           INTEGER      NOT NULL DEFAULT 0
price_override          NUMERIC(10,2) NULL     -- overrides products.unit_price for this catalog
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
UNIQUE constraint on `(catalog_id, product_id)`.


## Module 4 Table Schemas

# --- ADDED 2026-04-08 during Module 4 Phase 3 ---
# Reason: Module 4 adds orders and order_line_items tables. Documenting them here
# for implementation consistency and FK references in future modules (Bulk Ordering,
# Invoicing).
# Impact: Future modules know the orders/order_line_items shape for FK references.

### `orders` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
user_id                 UUID        NOT NULL (FK → users)     -- employee who placed the order
catalog_id              UUID        NOT NULL (FK → catalogs)  -- catalog the order was placed against
order_number            VARCHAR(30)  NOT NULL UNIQUE           -- ORD-YYYYMMDD-XXXX format
status                  VARCHAR(20)  NOT NULL DEFAULT 'pending' -- pending|approved|processing|shipped|delivered|cancelled
shipping_address_line1  VARCHAR(255) NULL
shipping_address_line2  VARCHAR(255) NULL
shipping_city           VARCHAR(100) NULL
shipping_state          VARCHAR(100) NULL
shipping_zip            VARCHAR(20)  NULL
shipping_country        VARCHAR(100) NULL
notes                   TEXT         NULL
subtotal                NUMERIC(10,2) NOT NULL DEFAULT 0
total_amount            NUMERIC(10,2) NOT NULL DEFAULT 0
cancelled_at            TIMESTAMP    NULL
cancelled_by            UUID         NULL (FK → users)
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
Shipping address is copied from request body or employee profile at order time.

### `order_line_items` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
order_id                UUID        NOT NULL (FK → orders)
product_id              UUID        NOT NULL (FK → products)
product_name            VARCHAR(255) NOT NULL   -- snapshot at order time
product_sku             VARCHAR(100) NOT NULL   -- snapshot at order time
unit_price              NUMERIC(10,2) NOT NULL  -- snapshot (catalog override or product price)
quantity                INTEGER      NOT NULL DEFAULT 1
size                    VARCHAR(20)  NULL
decoration              VARCHAR(255) NULL
line_total              NUMERIC(10,2) NOT NULL  -- unit_price × quantity
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
Line items snapshot product details at order time so price/name changes don't affect historical orders.


## Module 5 Table Schemas

# --- ADDED 2026-04-09 during Module 5 Phase 1 ---
# Reason: Module 5 adds bulk_orders and bulk_order_items tables. Documenting them here
# for implementation consistency and FK references in future modules (Invoicing).
# Impact: Future modules know the bulk order shape for FK references and status lifecycle.

### `bulk_orders` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
catalog_id              UUID        NOT NULL (FK → catalogs)  -- which catalog items are from
created_by              UUID        NOT NULL (FK → users)     -- manager/admin who created it
title                   VARCHAR(255) NOT NULL                  -- descriptive name
description             TEXT         NULL
order_number            VARCHAR(30)  NOT NULL UNIQUE           -- BLK-YYYYMMDD-XXXX format
status                  VARCHAR(20)  NOT NULL DEFAULT 'draft'  -- draft|submitted|approved|processing|shipped|delivered|cancelled
total_items             INTEGER      NOT NULL DEFAULT 0        -- denormalized count of bulk_order_items
total_amount            NUMERIC(10,2) NOT NULL DEFAULT 0       -- denormalized sum of item line totals
submitted_at            TIMESTAMP    NULL
approved_by             UUID         NULL (FK → users)
approved_at             TIMESTAMP    NULL
cancelled_at            TIMESTAMP    NULL
cancelled_by            UUID         NULL (FK → users)
notes                   TEXT         NULL
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
CHECK constraints: status IN valid values, total_items >= 0, total_amount >= 0.
Composite index: `(company_id, status)`.

### `bulk_order_items` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
bulk_order_id           UUID        NOT NULL (FK → bulk_orders)
employee_id             UUID        NULL (FK → users)         -- target employee (NULL = unassigned/general stock)
product_id              UUID        NOT NULL (FK → products)
product_name            VARCHAR(255) NOT NULL                  -- snapshot at add time
product_sku             VARCHAR(100) NOT NULL                  -- snapshot at add time
unit_price              NUMERIC(10,2) NOT NULL                 -- snapshot (catalog override or product price)
quantity                INTEGER      NOT NULL DEFAULT 1
size                    VARCHAR(20)  NULL
decoration              VARCHAR(255) NULL
line_total              NUMERIC(10,2) NOT NULL                 -- unit_price × quantity
notes                   TEXT         NULL                      -- per-item notes
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
CHECK constraints: quantity > 0, unit_price >= 0, line_total >= 0.
Items snapshot product details at add time (same pattern as order_line_items).


## Module 6 Table Schemas

# --- ADDED 2026-04-09 during Module 6 Phase 1 ---
# Reason: Module 6 adds approval workflow tables. Documenting them here for
# implementation consistency and FK references in future modules (Invoicing).
# Impact: Future modules know the approval_requests/approval_rules shape.

### `approval_requests` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
sub_brand_id            UUID        NULL (FK → sub_brands, indexed)
entity_type             VARCHAR(30)  NOT NULL         -- 'product', 'catalog', 'order', 'bulk_order'
entity_id               UUID         NOT NULL         -- polymorphic FK (no DB-level FK constraint)
requested_by            UUID         NOT NULL (FK → users)
decided_by              UUID         NULL (FK → users)
status                  VARCHAR(20)  NOT NULL DEFAULT 'pending'  -- pending|approved|rejected
decision_notes          TEXT         NULL
requested_at            TIMESTAMP    NOT NULL DEFAULT now()
decided_at              TIMESTAMP    NULL
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Standard company isolation (PERMISSIVE) + sub-brand scoping (RESTRICTIVE).
CHECK constraints: entity_type IN valid values, status IN valid values.
Composite index: `(entity_type, entity_id)` for polymorphic lookups,
`(company_id, status)` for approval queue queries.
Approval records are permanent audit trail — never soft-deleted.

### `approval_rules` Table (CompanyBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK → companies, indexed)
entity_type             VARCHAR(30)  NOT NULL         -- 'order', 'bulk_order'
rule_type               VARCHAR(30)  NOT NULL         -- 'amount_threshold'
threshold_amount        NUMERIC(10,2) NULL            -- e.g., 500.00 means orders over $500 need higher approval
required_role           VARCHAR(50)  NOT NULL         -- 'corporate_admin', 'sub_brand_admin', 'regional_manager'
is_active               BOOLEAN      NOT NULL DEFAULT true
created_by              UUID         NOT NULL (FK → users)
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
RLS: Company isolation only (no sub-brand scoping — rules are company-wide).
CHECK constraints: entity_type IN ('order', 'bulk_order'), rule_type IN ('amount_threshold'),
required_role IN valid values, threshold_amount >= 0.
UNIQUE constraint: `(company_id, entity_type, rule_type)` — one rule per type per company.
Composite index: `(company_id, entity_type)` for rule lookup.


## Approval Workflow Patterns

# --- ADDED 2026-04-09 during Module 6 Phase 2 ---
# Reason: Module 6 introduces a unified ApprovalService that orchestrates entity-specific
# approval methods and evaluates configurable approval rules. This pattern is new to the
# codebase and needs documentation for future modules (Invoicing may need approvals).
# Impact: Future modules that add approvable entities know the integration pattern.

### Unified ApprovalService
The `ApprovalService` in `app/services/approval_service.py` is the central orchestrator
for all approval workflows. It does NOT replace entity-specific approve/reject methods —
it wraps them with audit trail recording and rule evaluation.

**Delegation pattern:** The service delegates to entity-specific methods:
- `product` → `ProductService.approve_product()` / `reject_product()`
- `catalog` → `CatalogService.approve_catalog()` / `reject_catalog()`
- `order` → `OrderService.approve_order()` (rejection = `cancel_order()`)
- `bulk_order` → `BulkOrderService.approve_bulk_order()` (rejection = `cancel_bulk_order()`)

### Role Hierarchy for Approval Rules
Approval rules use a numeric rank for role comparison:
```
employee=0 < regional_manager=1 < sub_brand_admin=2 < corporate_admin=3 < reel48_admin=4
```
- Products and catalogs: always require `reel48_admin` (hardcoded, no configurable rules)
- Orders and bulk_orders: check `approval_rules` table. If an `amount_threshold` rule
  exists and the entity exceeds it, the user must have `>= required_role` rank.
- No active rule: default to `regional_manager` or above.

### Service-Level Tests Pattern
ApprovalService tests use direct model creation (not HTTP endpoints) because the service
layer is the deliverable for Phase 2. Tests create SQLAlchemy models directly in the
`admin_db_session`, then call service methods. FK constraints require real referenced
records (e.g., orders need a real catalog, bulk orders need a real catalog + user).


## Order Placement Patterns

# --- ADDED 2026-04-08 during Module 4 end-of-module harness review ---
# Reason: Order placement involves several non-obvious patterns (price snapshotting,
# shipping address resolution, order number generation, catalog validation) that
# future modules (Bulk Ordering, Invoicing) need to understand and follow.
# Impact: Module 5 (Bulk Ordering) can reuse the same validation and snapshotting logic.

### Price Snapshotting
Line items snapshot product details at order time so future price/name changes don't
affect historical orders. Price resolution order:
1. **`catalog_product.price_override`** — If the catalog has a price override for the
   product, use it.
2. **`product.unit_price`** — Fallback to the product's base price.

The resolved price is stored as `order_line_items.unit_price` (immutable after creation).
Product name and SKU are also snapshotted (`product_name`, `product_sku`).

### Shipping Address Resolution
Shipping address is resolved at order time with this priority:
1. **Explicit request body** — If `shipping_address_line1` is provided in the request,
   use all address fields from the request.
2. **Employee profile fallback** — If no address in the request, look up the employee's
   `EmployeeProfile.delivery_address_*` fields. If the profile exists and has an address,
   copy it to the order.
3. **NULL** — If neither source has an address, all shipping fields are NULL.

### Order Number Format
`ORD-YYYYMMDD-XXXX` where XXXX is 4 random hex characters (uppercase). Generated via
`secrets.token_hex(2).upper()`. Uniqueness enforced by checking against existing orders
with up to 5 retry attempts. The UNIQUE constraint on `order_number` provides a final
safety net.

### Catalog Validation at Order Time
Before an order is placed, the service validates:
1. **Catalog exists** and belongs to the user's company (`company_id` match).
2. **Catalog is active** (`status == 'active'`). Draft, submitted, or archived catalogs
   reject orders with 403.
3. **Buying window enforcement** (for `invoice_after_close` catalogs only):
   - If `buying_window_opens_at` is set and in the future → 422 "not open yet"
   - If `buying_window_closes_at` is set and in the past → 422 "window has closed"
   - `self_service` catalogs have no buying window constraints.
4. **Product validation** per line item:
   - Product must be in the catalog (`catalog_products` junction exists)
   - Product must be active (`status == 'active'`)
   - Size must be in `product.sizes` list (if provided and product has sizes)
   - Decoration must be in `product.decoration_options` list (if provided)


## Order Retrieval: Role-Based Visibility

# --- ADDED 2026-04-08 during Module 4 Phase 3 ---
# Reason: Orders use a different visibility pattern than products/catalogs. Products
# use status-based visibility (admins see all statuses, employees see only active).
# Orders use ownership-based visibility (managers see all in scope, employees see
# only their own). Documenting prevents confusion in future modules.
# Impact: Future modules (Bulk Ordering, Invoicing) follow the same ownership-based
# pattern where applicable.

### List Endpoint Behavior (`GET /api/v1/orders/`)
- **Managers and admins** (`regional_manager`, `sub_brand_admin`, `corporate_admin`):
  See all orders within their company/sub-brand scope. Corporate admins (sub_brand_id=None)
  see orders across all sub-brands in their company.
- **Employees**: See only orders where `Order.user_id` matches their own local user ID.
  The service uses `list_my_orders()` which adds a `user_id` filter.

### Explicit "My Orders" Endpoint (`GET /api/v1/orders/my/`)
Always returns only the authenticated user's own orders, regardless of role. This is
useful for managers/admins who want to see orders they personally placed (not all orders
in their scope). Defined BEFORE `/{order_id}` in the router to prevent FastAPI from
parsing "my" as a UUID path parameter.

### Get Order Detail (`GET /api/v1/orders/{order_id}`)
Returns the order with nested `line_items`. Employees can only see their own orders —
if the order's `user_id` doesn't match, a 404 is returned (not 403, to prevent
information leakage about other orders' existence).

### Pattern Summary
| Role | `GET /orders/` | `GET /orders/my/` | `GET /orders/{id}` |
|------|---------------|-------------------|-------------------|
| `corporate_admin` | All company orders | Own orders only | Any company order |
| `sub_brand_admin` | All sub-brand orders | Own orders only | Any sub-brand order |
| `regional_manager` | All sub-brand orders | Own orders only | Any sub-brand order |
| `employee` | Own orders only | Own orders only | Own orders only |


## Order Status Lifecycle & Transitions

# --- ADDED 2026-04-08 during Module 4 Phase 4 ---
# Reason: Order status transitions have strict rules about which statuses can
# transition to which, and who is authorized to perform each transition.
# Impact: Future modules (Bulk Ordering, Invoicing) know the order lifecycle and
# authorization model.

### Status Transitions
```
pending → approved → processing → shipped → delivered
pending → cancelled        (owner or manager_or_above)
approved → cancelled       (manager_or_above only)
```
- **pending:** Initial status after order placement. Can be cancelled by the order
  owner (employee) or any manager_or_above.
- **approved:** Manager has approved the order. Only manager_or_above can cancel.
  Employees CANNOT cancel their own order after approval.
- **processing:** Order is being processed/fulfilled. No cancellation allowed.
- **shipped:** Order has been shipped. No cancellation allowed.
- **delivered:** Terminal state. Order complete.
- **cancelled:** Terminal state. Records `cancelled_at` timestamp and `cancelled_by` user ID.

### Authorization Rules
| Transition | Who Can Perform |
|-----------|----------------|
| pending → approved | `manager_or_above` (`regional_manager`, `sub_brand_admin`, `corporate_admin`, `reel48_admin`) |
| pending → cancelled | Order owner (any role) OR `manager_or_above` |
| approved → cancelled | `manager_or_above` only |
| approved → processing | `manager_or_above` |
| processing → shipped | `manager_or_above` |
| shipped → delivered | `manager_or_above` |

### Endpoint Pattern
Status transitions use `POST /api/v1/orders/{order_id}/{action}` (not PATCH).
The cancel endpoint uses `get_tenant_context` (any role can attempt); all others
use `require_manager` dependency. Authorization for cancel is checked in the
service layer based on ownership and role.

### Invalid Transitions
Any transition not listed above returns 403 (ForbiddenError). Cancelled and
delivered orders cannot transition to any other status.


## Bulk Order Status Lifecycle & Transitions

# --- ADDED 2026-04-09 during Module 5 Phase 6 ---
# Reason: Bulk orders have a distinct lifecycle from individual orders (includes
# draft stage, submit guard, item locking). Documenting prevents confusion in
# future modules (Invoicing needs to know when a bulk order is ready for billing).
# Impact: Module 7 (Invoicing) knows bulk orders in 'delivered' or 'approved' status
# are eligible for invoice creation.

### Status Transitions
```
draft → submitted → approved → processing → shipped → delivered
draft → cancelled       (creator or manager_or_above)
submitted → cancelled   (manager_or_above only)
approved → cancelled    (manager_or_above only)
```

- **draft:** Initial status. Items can be added/updated/removed. Session metadata
  (title, description, notes) can be edited. Can be hard-deleted.
- **submitted:** Locked — no item changes allowed. Requires at least one item to
  submit. Records `submitted_at` timestamp.
- **approved:** Records `approved_by` and `approved_at`. Ready for fulfillment.
- **processing/shipped/delivered:** Fulfillment stages. Cannot be cancelled.
- **cancelled:** Terminal state. Records `cancelled_at` and `cancelled_by`.

### Authorization
| Transition | Who Can Perform |
|-----------|----------------|
| draft → submitted | `manager_or_above` |
| submitted → approved | `manager_or_above` |
| approved → processing | `manager_or_above` |
| processing → shipped | `manager_or_above` |
| shipped → delivered | `manager_or_above` |
| draft → cancelled | Creator or `manager_or_above` |
| submitted → cancelled | `manager_or_above` only |
| approved → cancelled | `manager_or_above` only |

### Endpoint Pattern
Status transitions use `POST /api/v1/bulk_orders/{bulk_order_id}/{action}` (not PATCH).
All transition endpoints use `require_manager` dependency except cancel, which uses
`get_tenant_context` (creator can cancel their own draft). Authorization for cancel is
checked in the service layer based on ownership, role, and current status.

### Invalid Transitions
Any transition not listed above returns 403 (ForbiddenError). Cancelled and
delivered bulk orders cannot transition to any other status. Processing and shipped
bulk orders cannot be cancelled.

### Key Differences from Individual Orders (Module 4)
- Bulk orders start as `draft` (individual orders start as `pending`)
- Explicit `draft → submitted` transition with item guard
- Items are locked after submission (individual orders have no draft editing stage)
- `approved_by` and `approved_at` tracked on bulk orders (not on individual orders)
- Created by managers/admins (individual orders created by any authenticated user)
- Draft bulk orders can be hard-deleted (individual orders cannot be deleted)


## Bulk Order Patterns

# --- ADDED 2026-04-09 during Module 5 Phase 6 ---
# Reason: Bulk ordering introduces several patterns not present in individual ordering:
# draft workflow, automatic total recalculation, employee assignment, and hard delete.
# Impact: Future modules (Invoicing, Analytics) understand bulk order mechanics.

### Draft Workflow
Unlike individual orders (which are submitted immediately), bulk orders follow a
**draft workflow**: create session → add items → submit. This allows managers to
build up an order over time before submitting for approval.

### Total Recalculation
`total_items` and `total_amount` on `bulk_orders` are denormalized aggregates that
auto-update on every item add/update/remove:
- `total_items` = SUM of all item quantities (NOT count of rows). A bulk order with
  3 items of quantities 5, 10, 3 has `total_items = 18`.
- `total_amount` = SUM of all item `line_total` values.
- Recalculation uses `func.coalesce(func.sum(...), 0)` to handle empty item lists.

### Employee Assignment
Items can target specific employees (via `employee_id`) or be unassigned
(`employee_id = NULL` = general stock). Employee validation checks `company_id`
only (not `sub_brand_id`) to support corporate admin cross-sub-brand bulk orders.

### Order Number Format
`BLK-YYYYMMDD-XXXX` where XXXX is 4 random hex characters (uppercase). Same
collision-retry pattern as individual orders (`ORD-YYYYMMDD-XXXX`).

### Price Snapshotting
Same pattern as individual orders: catalog `price_override` → product `unit_price`
fallback. Product name and SKU are snapshotted at item add time.

### Hard Delete for Drafts
Draft bulk orders are hard-deleted (row removed) rather than soft-deleted. Drafts
are ephemeral like unsaved documents — same reasoning as draft catalog deletion in
Module 3. Only `draft` status allows deletion; all other statuses return 403.

### Item Locking After Submission
Once a bulk order is submitted (`status != 'draft'`), all item management endpoints
(add, update, remove) return 403. This prevents modifications to orders that are
already in the approval/fulfillment pipeline.

### Catalog Validation
BulkOrderService duplicates catalog validation from OrderService (catalog exists,
belongs to company, is active, buying window enforcement). The duplication keeps
services self-contained rather than extracting a shared helper.

### Tenant Endpoints (14 total)
- CRUD: create, list, get (with items), update, delete
- Status transitions: submit, approve, process, ship, deliver, cancel
- Item management: add item, update item, remove item

### Platform Endpoints (2)
- `GET /api/v1/platform/bulk_orders/` — Cross-company list with optional filters
- `GET /api/v1/platform/bulk_orders/{id}` — Cross-company detail with items


## Product Status Lifecycle & Visibility

# --- ADDED 2026-04-08 during Module 3 Phase 2 ---
# Reason: The status transition rules (which statuses allow edits/deletes) and
# role-based visibility rules (employees see only active) were implemented in code
# but not documented in the harness.
# Impact: Future modules (Ordering, Approval Workflows) know the product lifecycle.

### Status Transitions
```
draft → submitted → approved → active → archived
```
- **draft:** Initial status. Editable, deletable (soft-delete), submittable.
- **submitted:** Awaiting Reel48 admin approval. No edits or deletes allowed.
- **approved:** Approved by `reel48_admin`. No edits. (Module 6 builds approval endpoints.)
- **active:** Live in catalog, purchasable by employees. No edits.
- **archived:** Removed from active catalog. No edits.

### Edit/Delete Restrictions
- Only products in `draft` status can be updated (`PATCH`), deleted (`DELETE`), or
  submitted (`POST .../submit`). All other statuses return 403.
- This prevents changes to products that are in-review, approved, or live in catalogs.

### Role-Based Visibility
- **Admins** (`sub_brand_admin`, `corporate_admin`, `reel48_admin`): See products in
  ALL statuses for management purposes. Can filter by `?status=` query parameter.
- **Non-admins** (`regional_manager`, `employee`): See ONLY `active` products. Draft,
  submitted, approved, and archived products are hidden. This applies to both list and
  get-by-ID endpoints (get returns 404 for non-active products when called by non-admins).
- **Sub-brand scoping:** Sub-brand-scoped admins see only their sub-brand's products.
  Corporate admins see all sub-brands' products within their company.


## Catalog Status Lifecycle & Visibility

# --- ADDED 2026-04-08 during Module 3 Phase 3 ---
# Reason: Catalogs follow a similar lifecycle to products but with additional
# constraints (submit requires products, buying window validation). Documenting
# here ensures future modules (Ordering, Approval Workflows) know catalog lifecycle.
# Impact: Future modules handle catalog statuses correctly and know the submit guard.

### Status Transitions
```
draft → submitted → approved → active → closed → archived
```
- **draft:** Initial status. Editable, deletable (soft-delete), submittable.
- **submitted:** Awaiting Reel48 admin approval. Submit requires at least one product.
- **approved:** Approved by `reel48_admin`. (Module 6 builds approval endpoints.)
- **active:** Live catalog, employees can browse and order. No edits.
- **closed:** Buying window has closed (for `invoice_after_close` catalogs).
- **archived:** Removed from active use. No edits.

### Edit/Delete Restrictions
- Only catalogs in `draft` status can be updated (`PATCH`), deleted (`DELETE`), or
  submitted (`POST .../submit`). All other statuses return 403.
- Deleting a draft catalog also hard-deletes its catalog_products junction entries.
- Products can only be added to or removed from draft catalogs.

### Submit Guard
- A catalog CANNOT be submitted if it has zero products (returns 422).
- This prevents empty catalogs from entering the approval workflow.

### Buying Window Validation
- `payment_model` is set at creation and is NOT updatable.
- `invoice_after_close`: Both `buying_window_opens_at` and `buying_window_closes_at`
  are required. `opens_at` must be before `closes_at`.
- `self_service`: Both window fields must be NULL. Setting them is a 422 error.

### Role-Based Visibility
- Same pattern as products: admins see all statuses, non-admins see only `active`.

### Slug Auto-Generation
Catalog slugs are auto-generated from the name at creation time:
- Lowercase, replace non-alphanumeric characters with hyphens, strip edges
- Collision handling: append `-2`, `-3`, etc. within the same company
- Slugs are regenerated on name update (also with collision handling)
- No third-party slug library — uses a simple `re.sub()` helper in the service


## Error Handling

# --- WHY THIS SECTION EXISTS ---
# Consistent error responses make frontend integration predictable. If every
# endpoint returns errors in a different format, the frontend API client can't
# handle them uniformly. This section ensures Claude Code always uses the same
# error pattern.

### Custom Exception Classes
```python
# WHY: Custom exceptions map business logic errors to HTTP responses cleanly.
# The exception handler in main.py catches these and formats them into the
# standard error response format, so routes don't need try/except blocks.

class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

class NotFoundError(AppException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} with ID {resource_id} not found",
            status_code=404,
        )

class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)

class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(code="CONFLICT", message=message, status_code=409)
```

### Exception Handler (in main.py)
```python
# WHY: A global exception handler catches AppExceptions and converts them
# into the standard JSON error format. This means routes can just `raise
# NotFoundError(...)` without worrying about HTTP response formatting.

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "errors": [{"code": exc.code, "message": exc.message}]},
    )
```


## Rate Limiting Pattern

# --- ADDED 2026-04-06 during pre-build harness review ---
# --- UPDATED 2026-04-07 after Module 1 Phase 5 ---
# Reason: Actual implementation uses a dependency factory pattern with graceful
# degradation and lazy Redis singleton, not a simple inline function.
# Impact: Harness code example matches the real implementation.

Rate limiting is implemented as a **FastAPI dependency factory** using Redis (ElastiCache).
It is applied to unauthenticated endpoints that cannot rely on JWT-based identity.

```python
# app/core/rate_limit.py
from app.core.exceptions import RateLimitError

def check_rate_limit(
    group: str = "auth",
    max_attempts: int = 5,
    window_seconds: int = 900,
) -> Callable[..., Coroutine[Any, Any, None]]:
    """
    Returns a FastAPI dependency that enforces rate limiting.
    Graceful degradation: if Redis unavailable, request passes through.
    """
    async def _dependency(request: Request) -> None:
        client = await _get_redis_client()
        if client is None:
            return  # Graceful degradation

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{group}:{client_ip}"

        try:
            current: int = await client.incr(key)
            if current == 1:
                await client.expire(key, window_seconds)
            if current > max_attempts:
                raise RateLimitError()
        except RateLimitError:
            raise
        except Exception:
            return  # Graceful degradation

    return _dependency

# Pre-configured dependency for auth endpoints (5 attempts per 15 minutes)
rate_limit_auth = check_rate_limit(group="auth", max_attempts=5, window_seconds=900)

# Usage in routes:
@router.post("/validate-org-code")
async def validate_org_code(
    body: ValidateOrgCodeRequest,
    _rate_limit: None = Depends(rate_limit_auth),  # Shared "auth" group
):
    ...
```

**Key design decisions:**
- **Factory pattern:** `check_rate_limit()` returns a dependency closure. Pre-configured
  `rate_limit_auth` is shared across auth endpoints.
- **Graceful degradation:** If Redis is unavailable, requests pass through. Registration
  should not be blocked by infrastructure issues. Log warnings for debugging.
- **Group-based:** `validate-org-code` and `register` share the same rate limit window
  (`group="auth"`) so an attacker can't use 5 attempts on validate then 5 more on register.
- **IP-based:** Uses `request.client.host`. Behind a load balancer, configure
  `X-Forwarded-For` trust via FastAPI's `--proxy-headers` flag.
- **RateLimitError:** Uses the custom `RateLimitError(AppException)` (HTTP 429) to go
  through the standard `app_exception_handler`, not a raw HTTPException.
- **Redis key pattern:** `rate_limit:{group}:{ip}` with TTL = window duration.
- **Lazy Redis singleton:** `_get_redis_client()` creates the Redis connection on first
  use and caches it. Returns `None` if connection fails.


## Testing Patterns

# --- WHY THIS SECTION EXISTS ---
# Backend tests need to verify not just functionality but TENANT ISOLATION.
# This section provides the exact fixtures and patterns Claude Code should
# follow, including the critical cross-tenant access tests.

### Test Fixtures (in conftest.py)

# --- UPDATED 2026-04-07 during Phase 3 implementation ---
# Reason: Phase 3 implemented the actual conftest.py. Harness now documents the real
# patterns including dual-session RLS testing, JWKS monkeypatch, and Alembic subprocess.
# Impact: Future sessions understand the test infrastructure without reverse-engineering conftest.py.

#### Database Setup: Alembic Migrations via Subprocess
The `setup_database` fixture runs Alembic migrations against the test database. It uses
`subprocess.run(["alembic", "upgrade", "head"])` instead of the Alembic Python API because
`env.py` calls `asyncio.run()` internally, which conflicts with pytest-asyncio's event loop.
The `DATABASE_URL` environment variable is overridden to point to the test database.

#### Two Database Sessions: Superuser vs App Role
PostgreSQL superusers bypass RLS even with `FORCE ROW LEVEL SECURITY`. Tests use two sessions:
- **`admin_db_session`** — Connects as `postgres` (superuser). Used to seed test data that
  bypasses RLS (e.g., creating companies, users across tenants). Also used by the `client`
  fixture for functional HTTP tests where RLS interference is unwanted.
- **`db_session`** — Connects as `reel48_app` (non-superuser). RLS is enforced. Used by
  isolation tests to verify that session variables + RLS policies correctly filter data.

The `setup_database` fixture creates the `reel48_app` role and grants it permissions on
all Module 1 tables. The role connects via `TEST_DATABASE_URL_APP` env var (defaults to
`postgresql+asyncpg://reel48_app:reel48_app@localhost:5432/reel48_test`).

#### JWT Authentication: Real Tokens with Monkeypatched JWKS
`create_test_token()` signs real JWTs with a test RSA private key (generated at module load).
A session-scoped autouse fixture monkeypatches `app.core.security._fetch_jwks` to return a
JWKS containing the test public key. The full `validate_cognito_token` path runs (signature,
expiry, audience, issuer, token_use) — only the HTTP fetch is mocked.

**CRITICAL:** The fixture must also reset `security._jwks_keys = None` and
`security._jwks_fetched_at = 0.0` after patching, otherwise the cache retains stale keys.

#### Multi-Tenant Fixtures
```python
@pytest.fixture
async def company_a(admin_db_session):
    """Returns: (company, brand_a1, brand_a2)"""

@pytest.fixture
async def company_b(admin_db_session):
    """Returns: (company, brand_b1)"""

# Token fixtures (real signed JWTs):
def reel48_admin_token() -> str                     # No company, no sub-brand
def company_a_corporate_admin_token(company_a) -> str  # Company A, no sub-brand
def company_a_brand_a1_admin_token(company_a) -> str   # Company A, Brand A1
def company_a_brand_a1_employee_token(company_a) -> str
def company_a_brand_a2_employee_token(company_a) -> str
def company_b_employee_token(company_b) -> str         # Company B, Brand B1
```

#### Client Fixture
The `client` fixture overrides `get_db_session` with `admin_db_session` (superuser), so
route handlers can insert/query data without RLS interference. This is correct for
**functional tests** (testing endpoint behavior). **Isolation tests** must use `db_session`
directly (non-superuser, RLS enforced) and set session variables manually.

### Cross-Tenant Isolation Test Pattern
```python
# WHY: These are the most important tests in the entire suite. They verify
# that the security boundaries actually work. Every module MUST include
# versions of these tests for its specific data.

async def test_company_b_cannot_see_company_a_products(
    client: AsyncClient, company_a, company_b, company_b_token
):
    """Verify cross-company isolation: Company B should see zero Company A products."""
    # Create a product in Company A
    await create_test_product(company_id=company_a[0].id, sub_brand_id=company_a[1].id)

    # Query as Company B — should return empty
    response = await client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {company_b_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 0


async def test_brand_a2_cannot_see_brand_a1_products(
    client: AsyncClient, company_a, brand_a2_token
):
    """Verify cross-sub-brand isolation within the same company."""
    # Create a product in Brand A1
    await create_test_product(company_id=company_a[0].id, sub_brand_id=company_a[1].id)

    # Query as Brand A2 admin — should return empty
    response = await client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {brand_a2_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 0


async def test_corporate_admin_sees_all_sub_brands(
    client: AsyncClient, company_a, corporate_admin_token
):
    """Verify corporate admin has cross-sub-brand visibility."""
    # Create products in both Brand A1 and Brand A2
    await create_test_product(company_id=company_a[0].id, sub_brand_id=company_a[1].id)
    await create_test_product(company_id=company_a[0].id, sub_brand_id=company_a[2].id)

    # Query as corporate admin — should see both
    response = await client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {corporate_admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
```


## Alembic Migration Conventions

# --- WHY THIS SECTION EXISTS ---
# Every table that stores tenant data MUST have RLS policies, and those
# policies MUST be created in the same migration as the table. If they're
# in separate migrations, there's a window where the table exists without
# isolation — a security risk during development and a potential production
# issue if a migration is partially applied.

### Migration Template
```python
# WHY: This template ensures every new table migration includes RLS policies
# by default. Claude Code should use this pattern for every migration that
# creates a tenant-scoped table.

"""create_products_table

Revision ID: abc123
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

def upgrade():
    # 1. Create the table
    op.create_table(
        'products',
        sa.Column('id', UUID(), primary_key=True),
        sa.Column('company_id', UUID(), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('sub_brand_id', UUID(), sa.ForeignKey('sub_brands.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # 2. Create indexes for common query patterns
    op.create_index('ix_products_company_id', 'products', ['company_id'])
    op.create_index('ix_products_sub_brand_id', 'products', ['sub_brand_id'])
    op.create_index('ix_products_sku', 'products', ['sku'])

    # 3. CRITICAL: Enable RLS and create policies IN THE SAME MIGRATION
    op.execute("ALTER TABLE products ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE products FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY products_company_isolation ON products
        USING (
            current_setting('app.current_company_id', true) IS NULL
            OR current_setting('app.current_company_id', true) = ''
            OR company_id = current_setting('app.current_company_id')::uuid
        )
    """)
    op.execute("""
        CREATE POLICY products_sub_brand_scoping ON products AS RESTRICTIVE
        USING (
            current_setting('app.current_sub_brand_id', true) IS NULL
            OR current_setting('app.current_sub_brand_id', true) = ''
            OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
        )
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS products_sub_brand_scoping ON products")
    op.execute("DROP POLICY IF EXISTS products_company_isolation ON products")
    op.drop_table('products')
```


## Logging & Observability

# --- WHY THIS SECTION EXISTS ---
# Structured logging lets you filter logs by tenant, sub-brand, or user.
# Without structured logging, debugging a production issue for a specific
# tenant means grep-ing through unstructured text — slow and error-prone.

Use **structlog** for structured JSON logging:

```python
import structlog

logger = structlog.get_logger()

# WHY: Binding tenant context to the logger means every log line from that
# request automatically includes company_id and sub_brand_id. When debugging
# a tenant-specific issue, you can filter by company_id instantly.
logger = logger.bind(
    company_id=str(context.company_id),
    sub_brand_id=str(context.sub_brand_id),
    user_id=context.user_id,
)

logger.info("product_created", product_id=str(product.id), sku=product.sku)
# Output: {"event": "product_created", "company_id": "...", "sub_brand_id": "...", "product_id": "...", "sku": "..."}
```
