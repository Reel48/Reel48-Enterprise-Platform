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
    # across pooled connections. Use parameterized queries for defense-in-depth.
    if context.is_reel48_admin:
        await db.execute(text("SET LOCAL app.current_company_id = ''"))
        await db.execute(text("SET LOCAL app.current_sub_brand_id = ''"))
    else:
        await db.execute(text("SET LOCAL app.current_company_id = :cid"), {"cid": str(context.company_id)})
        if context.sub_brand_id:
            await db.execute(text("SET LOCAL app.current_sub_brand_id = :sbid"), {"sbid": str(context.sub_brand_id)})
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

### Login & Token Refresh
# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: Ambiguity about whether login/refresh were backend endpoints or client-side.
# Impact: Claude Code knows NOT to build backend login/refresh endpoints.

Login and token refresh are handled **entirely client-side** by AWS Amplify
(`@aws-amplify/auth`). There are NO backend endpoints for login or token refresh.
Amplify communicates directly with Cognito. The backend only validates JWTs — it
never issues them.

### Unauthenticated Endpoint Exceptions
Three endpoints do NOT use `get_tenant_context` because they receive requests without JWTs:
1. **`POST /api/v1/webhooks/stripe`** — Stripe webhook. Secured by signature verification.
2. **`POST /api/v1/auth/validate-org-code`** — Validates an org code and returns the
   company name + list of sub-brands. Rate-limited (5 attempts per IP per 15 minutes).
3. **`POST /api/v1/auth/register`** — Self-registration via org code. Accepts the org
   code, employee-selected `sub_brand_id`, and user details. The `sub_brand_id` is
   validated server-side to confirm it belongs to the org code's company.
   Rate-limited (shares the same 5 attempts/IP/15 min window as validate-org-code).
   See ADR-007 for full details.

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
| `products` | `TenantBase` | Scoped to company + sub-brand |
| `orders` | `TenantBase` | Scoped to company + sub-brand |
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
# Reason: Both unauthenticated auth endpoints need rate limiting but no
# implementation pattern was defined (middleware vs dependency, Redis keys, etc.).
# Impact: Claude Code generates consistent rate limiting for all unauthenticated endpoints.

Rate limiting is implemented as a **FastAPI dependency** using Redis (ElastiCache).
It is applied to unauthenticated endpoints that cannot rely on JWT-based identity.

```python
from fastapi import Depends, HTTPException, Request
import redis.asyncio as redis

redis_client = redis.from_url(settings.REDIS_URL)

async def check_rate_limit(
    request: Request,
    group: str = "auth",       # Shared window for related endpoints
    max_attempts: int = 5,
    window_seconds: int = 900,  # 15 minutes
):
    """
    Rate limit by client IP. Raises 429 when limit is exceeded.
    Endpoints sharing the same `group` share the same counter.
    """
    client_ip = request.client.host
    key = f"rate_limit:{group}:{client_ip}"

    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_seconds)

    if current > max_attempts:
        raise HTTPException(
            status_code=429,
            detail={"data": None, "errors": [{"code": "RATE_LIMITED", "message": "Too many attempts. Please try again later."}]},
        )

# Usage in routes:
@router.post("/api/v1/auth/validate-org-code")
async def validate_org_code(
    body: ValidateOrgCodeRequest,
    _rate_limit: None = Depends(check_rate_limit),  # Shared "auth" group
):
    ...
```

**Key design decisions:**
- **Group-based:** `validate-org-code` and `register` share the same rate limit window
  (`group="auth"`) so an attacker can't use 5 attempts on validate then 5 more on register.
- **IP-based:** Uses `request.client.host`. Behind a load balancer, configure
  `X-Forwarded-For` trust via FastAPI's `--proxy-headers` flag.
- **Standard error format:** 429 responses use the same `{data, errors}` envelope.
- **Redis key pattern:** `rate_limit:{group}:{ip}` with TTL = window duration.


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
        CREATE POLICY products_sub_brand_scoping ON products
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
