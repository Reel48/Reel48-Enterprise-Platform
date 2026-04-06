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
│   │   ├── base.py                # TenantBase with company_id, sub_brand_id
│   │   ├── company.py
│   │   ├── sub_brand.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── bulk_order.py
│   ├── schemas/                   # Pydantic models for API request/response
│   │   ├── common.py              # Shared schemas (pagination, error response)
│   │   ├── company.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── user.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          # Aggregates all v1 route modules
│   │       ├── auth.py            # Login, register, token refresh
│   │       ├── companies.py
│   │       ├── sub_brands.py
│   │       ├── users.py
│   │       ├── products.py
│   │       ├── orders.py
│   │       ├── bulk_orders.py
│   │       ├── approvals.py
│   │       └── analytics.py
│   └── services/                  # Business logic (called by routes)
│       ├── company_service.py
│       ├── sub_brand_service.py
│       ├── user_service.py
│       ├── product_service.py
│       ├── order_service.py
│       ├── bulk_order_service.py
│       ├── approval_service.py
│       ├── analytics_service.py
│       └── email_service.py       # SES integration
├── migrations/
│   ├── env.py
│   └── versions/                  # Alembic migration files
├── tests/
│   ├── conftest.py                # Shared fixtures (test DB, test tenants, auth tokens)
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_orders.py
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

    context = TenantContext(
        user_id=claims["sub"],
        company_id=claims["custom:company_id"],
        sub_brand_id=claims.get("custom:sub_brand_id"),  # None for corporate_admin
        role=claims["custom:role"],
    )

    # CRITICAL: Set PostgreSQL session variables so RLS policies can reference them.
    # Without this, RLS policies have no way to know which tenant is making the request.
    await db.execute(text(f"SET app.current_company_id = '{context.company_id}'"))
    if context.sub_brand_id:
        await db.execute(text(f"SET app.current_sub_brand_id = '{context.sub_brand_id}'"))
    else:
        await db.execute(text("SET app.current_sub_brand_id = ''"))

    return context
```

### TenantContext Model
```python
# WHY: A dataclass (or Pydantic model) rather than a dict ensures type safety.
# Every endpoint that uses TenantContext gets autocomplete and type checking,
# preventing bugs like misspelling "company_id" as "companyId".

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

@dataclass
class TenantContext:
    user_id: str
    company_id: UUID
    sub_brand_id: Optional[UUID]
    role: str  # One of: corporate_admin, sub_brand_admin, regional_manager, employee

    @property
    def is_corporate_admin(self) -> bool:
        return self.role == "corporate_admin"

    @property
    def is_admin(self) -> bool:
        return self.role in ("corporate_admin", "sub_brand_admin")
```


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


## Testing Patterns

# --- WHY THIS SECTION EXISTS ---
# Backend tests need to verify not just functionality but TENANT ISOLATION.
# This section provides the exact fixtures and patterns Claude Code should
# follow, including the critical cross-tenant access tests.

### Test Fixtures (in conftest.py)
```python
# WHY: These fixtures create a complete test environment with two companies,
# each having two sub-brands, and users at each role level. This lets every
# test verify both functionality AND isolation without redundant setup.

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def test_db():
    """Create a fresh test database with RLS policies."""
    # Set up test database, run migrations, yield, tear down
    ...

@pytest.fixture
async def company_a(test_db):
    """Company A with two sub-brands."""
    company = await create_test_company(name="Company A")
    brand_1 = await create_test_sub_brand(company_id=company.id, name="Brand A1")
    brand_2 = await create_test_sub_brand(company_id=company.id, name="Brand A2")
    return company, brand_1, brand_2

@pytest.fixture
async def company_b(test_db):
    """Company B (separate tenant for isolation testing)."""
    company = await create_test_company(name="Company B")
    brand_1 = await create_test_sub_brand(company_id=company.id, name="Brand B1")
    return company, brand_1

@pytest.fixture
async def corporate_admin_token(company_a):
    """JWT token for Company A's corporate admin (sub_brand_id=None)."""
    return create_test_token(
        company_id=company_a[0].id,
        sub_brand_id=None,
        role="corporate_admin",
    )

@pytest.fixture
async def brand_admin_token(company_a):
    """JWT token for Company A, Brand A1's admin."""
    return create_test_token(
        company_id=company_a[0].id,
        sub_brand_id=company_a[1].id,
        role="sub_brand_admin",
    )
```

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
        USING (company_id = current_setting('app.current_company_id')::uuid)
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
