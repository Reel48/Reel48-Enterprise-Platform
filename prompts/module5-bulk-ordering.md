# Module 5: Bulk Ordering System — Phase-by-Phase Implementation Prompts
#
# Each phase below is a self-contained prompt designed to be pasted into a
# fresh Claude Code session. The session will read the CLAUDE.md harness files
# automatically — these prompts provide MODULE-SPECIFIC context that the
# harness doesn't cover.
#
# IMPORTANT: Run phases in order. Each phase depends on the prior phase's output.
#
# MODULE 5 OVERVIEW:
# Bulk ordering lets managers and admins create large orders on behalf of
# multiple employees at once. Unlike Module 4's individual ordering (where an
# employee places an order for themselves), bulk orders are admin-initiated
# sessions that aggregate items across employees or across an entire sub-brand.
#
# Key differences from individual orders:
# - Created by managers/admins, NOT employees
# - Can target multiple employees in a single session
# - Grouped into a "bulk order session" with individual "bulk order items"
# - Follows its own status lifecycle (draft → submitted → approved → processing → shipped → delivered → cancelled)
# - Draft stage allows editing before submission (unlike individual orders which are immediate)
# - Ties into invoicing: bulk orders produce Reel48-assigned invoices (Flow 1 in CLAUDE.md)
# - Platform admins (reel48_admin) have cross-company visibility


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Database Migration — Bulk Orders & Bulk Order Items
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 5 Phase 1: the Alembic migration, SQLAlchemy models, and test
infrastructure updates for the bulk ordering system.

## Context

We are building Module 5 (Bulk Ordering System) of the Reel48+ enterprise apparel
platform. Modules 1-4 are complete:
- Module 1: Auth, Companies, Sub-Brands, Users (migration `001`)
- Module 2: Employee Profiles (migration `002`)
- Module 3: Products, Catalogs, Catalog-Products (migration `003`)
- Module 4: Orders, Order Line Items (migration `004`)

The current test suite has 265 passing tests. The branch is `main`.
Create a new branch `feature/module5-phase1-bulk-order-tables` from `main`
before starting.

## What to Build

### 1. Alembic migration: `backend/migrations/versions/005_create_module5_bulk_order_tables.py`

Create two tables in a single migration (same pattern as migration `004`):

**`bulk_orders` table (TenantBase shape):**
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL FK → companies.id
sub_brand_id            UUID        NULL FK → sub_brands.id
catalog_id              UUID        NOT NULL FK → catalogs.id     -- which catalog items are from
created_by              UUID        NOT NULL FK → users.id        -- manager/admin who created it
title                   VARCHAR(255) NOT NULL                     -- descriptive name ("Q3 2026 North Division Polos")
description             TEXT         NULL
order_number            VARCHAR(30)  NOT NULL UNIQUE              -- BLK-YYYYMMDD-XXXX format
status                  VARCHAR(20)  NOT NULL DEFAULT 'draft'
total_items             INTEGER      NOT NULL DEFAULT 0           -- count of bulk_order_items (denormalized)
total_amount            NUMERIC(10,2) NOT NULL DEFAULT 0          -- sum of all item line totals (denormalized)
submitted_at            TIMESTAMP WITH TIME ZONE NULL
approved_by             UUID         NULL FK → users.id
approved_at             TIMESTAMP WITH TIME ZONE NULL
cancelled_at            TIMESTAMP WITH TIME ZONE NULL
cancelled_by            UUID         NULL FK → users.id
notes                   TEXT         NULL
created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
```

CHECK constraints:
- `ck_bulk_orders_status_valid`: status IN ('draft', 'submitted', 'approved', 'processing', 'shipped', 'delivered', 'cancelled')
- `ck_bulk_orders_total_items_non_negative`: total_items >= 0
- `ck_bulk_orders_total_amount_non_negative`: total_amount >= 0

Indexes:
- `ix_bulk_orders_company_id` on (company_id)
- `ix_bulk_orders_sub_brand_id` on (sub_brand_id)
- `ix_bulk_orders_catalog_id` on (catalog_id)
- `ix_bulk_orders_created_by` on (created_by)
- `ix_bulk_orders_company_id_status` on (company_id, status)

RLS policies (both in same migration):
- `bulk_orders_company_isolation` — PERMISSIVE, standard company isolation pattern
- `bulk_orders_sub_brand_scoping` — RESTRICTIVE, standard sub-brand scoping pattern

**`bulk_order_items` table (TenantBase shape):**
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL FK → companies.id
sub_brand_id            UUID        NULL FK → sub_brands.id
bulk_order_id           UUID        NOT NULL FK → bulk_orders.id
employee_id             UUID        NULL FK → users.id            -- target employee (NULL = unassigned / general stock)
product_id              UUID        NOT NULL FK → products.id
product_name            VARCHAR(255) NOT NULL                     -- snapshot at add time
product_sku             VARCHAR(100) NOT NULL                     -- snapshot at add time
unit_price              NUMERIC(10,2) NOT NULL                    -- snapshot (catalog override or product price)
quantity                INTEGER      NOT NULL DEFAULT 1
size                    VARCHAR(20)  NULL
decoration              VARCHAR(255) NULL
line_total              NUMERIC(10,2) NOT NULL                    -- unit_price × quantity
notes                   TEXT         NULL                         -- per-item notes (e.g., "Rush delivery")
created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
```

CHECK constraints:
- `ck_bulk_order_items_quantity_positive`: quantity > 0
- `ck_bulk_order_items_unit_price_non_negative`: unit_price >= 0
- `ck_bulk_order_items_line_total_non_negative`: line_total >= 0

Indexes:
- `ix_bulk_order_items_company_id` on (company_id)
- `ix_bulk_order_items_sub_brand_id` on (sub_brand_id)
- `ix_bulk_order_items_bulk_order_id` on (bulk_order_id)
- `ix_bulk_order_items_employee_id` on (employee_id)
- `ix_bulk_order_items_product_id` on (product_id)

RLS policies:
- `bulk_order_items_company_isolation` — PERMISSIVE
- `bulk_order_items_sub_brand_scoping` — RESTRICTIVE

FK naming convention: `fk_{table}_{column}_{ref_table}` (e.g., `fk_bulk_orders_created_by_users`,
`fk_bulk_orders_catalog_id_catalogs`, `fk_bulk_order_items_bulk_order_id_bulk_orders`,
`fk_bulk_order_items_employee_id_users`, `fk_bulk_order_items_product_id_products`).

Downgrade: drop policies, disable RLS, drop indexes, drop tables (bulk_order_items first,
then bulk_orders — respect FK dependency order).

Follow the exact style of `backend/migrations/versions/004_create_module4_order_tables.py` —
use `sa.Column`, `UUID(as_uuid=True)`, `sa.ForeignKey(name=...)`, `sa.text("now()")` for
server_default timestamps, and `op.execute()` for RLS statements.

### 2. SQLAlchemy Models

**`backend/app/models/bulk_order.py`:**
```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class BulkOrder(TenantBase):
    """
    Bulk order session created by a manager/admin for multiple employees.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: bulk_orders_company_isolation + bulk_orders_sub_brand_scoping.
    """

    __tablename__ = "bulk_orders"

    catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogs.id", name="fk_bulk_orders_catalog_id_catalogs"),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_bulk_orders_created_by_users"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_number = Column(String(30), nullable=False, unique=True)
    status = Column(String(20), nullable=False, server_default="draft")
    total_items = Column(Integer, nullable=False, server_default="0")
    total_amount = Column(Numeric(10, 2), nullable=False, server_default="0")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_bulk_orders_approved_by_users"),
        nullable=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_bulk_orders_cancelled_by_users"),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
```

**`backend/app/models/bulk_order_item.py`:**
```python
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class BulkOrderItem(TenantBase):
    """
    Individual item within a bulk order session.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: bulk_order_items_company_isolation + bulk_order_items_sub_brand_scoping.
    """

    __tablename__ = "bulk_order_items"

    bulk_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bulk_orders.id", name="fk_bulk_order_items_bulk_order_id_bulk_orders"),
        nullable=False,
    )
    employee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_bulk_order_items_employee_id_users"),
        nullable=True,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", name="fk_bulk_order_items_product_id_products"),
        nullable=False,
    )
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, server_default="1")
    size = Column(String(20), nullable=True)
    decoration = Column(String(255), nullable=True)
    line_total = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)
```

### 3. Update `backend/app/models/__init__.py`

Add imports and `__all__` exports for `BulkOrder` and `BulkOrderItem`.
Follow the existing pattern — add to the import list and the `__all__` list.

### 4. Update test infrastructure: `backend/tests/conftest.py`

In the `setup_database` fixture, add `"bulk_orders"` and `"bulk_order_items"` to the
`tables` list that gets `GRANT SELECT, INSERT, UPDATE, DELETE ... TO reel48_app`.

### Verification

After building:
1. Run `cd backend && alembic upgrade head` against the test database to verify migration applies
2. Run `cd backend && python -m pytest tests/ -x` to confirm all 265 existing tests still pass
3. Verify `alembic downgrade -1` then `alembic upgrade head` works (reversibility)

### Do NOT Build Yet
- No schemas, services, or API endpoints in this phase
- No new test files — just verify existing tests pass

Commit message: `feat: add bulk_orders and bulk_order_items tables with RLS (Module 5 Phase 1)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Bulk Order Session CRUD (Create, List, Get, Update, Delete Draft)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 5 Phase 2: the bulk order session CRUD endpoints, service, schemas,
and tests.

## Context

Module 5 Phase 1 is complete — the `bulk_orders` and `bulk_order_items` tables exist
with RLS policies and SQLAlchemy models. We are on the appropriate branch from Phase 1.

Modules 1-4 provide:
- Auth with TenantContext (company_id, sub_brand_id from JWT)
- `require_manager` dependency that enforces `is_manager_or_above` (regional_manager,
  sub_brand_admin, corporate_admin, reel48_admin)
- Employee profiles with delivery addresses
- Products with status lifecycle (draft → submitted → approved → active → archived)
- Catalogs with payment_model (`self_service` or `invoice_after_close`) and buying windows
- CatalogProducts junction with optional price_override
- Individual orders with status lifecycle

Unlike individual orders (Module 4) which are placed and immediately submitted, bulk
orders follow a **draft workflow**:
1. Manager creates a bulk order session (draft status)
2. Manager adds/removes/edits items within the draft (Phase 3)
3. Manager submits the draft for approval (Phase 4)
4. Approval/processing/shipping/delivery follows (Phase 4)

This phase builds the session-level CRUD — creating, listing, viewing, updating,
and deleting draft bulk order sessions. Item management comes in Phase 3.

## What to Build

### 1. Pydantic Schemas: `backend/app/schemas/bulk_order.py`

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator


class BulkOrderCreate(BaseModel):
    """Create a new bulk order session (draft)."""
    catalog_id: UUID
    title: str
    description: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class BulkOrderUpdate(BaseModel):
    """Update a draft bulk order session. All fields optional for partial update."""
    title: str | None = None
    description: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty_if_provided(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip() if v is not None else v


class BulkOrderItemCreate(BaseModel):
    """Add an item to a bulk order session."""
    product_id: UUID
    employee_id: UUID | None = None     # NULL = unassigned / general stock
    quantity: int = 1
    size: str | None = None
    decoration: str | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v


class BulkOrderItemUpdate(BaseModel):
    """Update an item within a draft bulk order. All fields optional."""
    employee_id: UUID | None = None
    quantity: int | None = None
    size: str | None = None
    decoration: str | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive_if_provided(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v


class BulkOrderItemResponse(BaseModel):
    """Bulk order item in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bulk_order_id: UUID
    employee_id: UUID | None
    product_id: UUID
    product_name: str
    product_sku: str
    unit_price: float
    quantity: int
    size: str | None
    decoration: str | None
    line_total: float
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BulkOrderResponse(BaseModel):
    """Bulk order session in API responses (without items)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    catalog_id: UUID
    created_by: UUID
    title: str
    description: str | None
    order_number: str
    status: str
    total_items: int
    total_amount: float
    submitted_at: datetime | None
    approved_by: UUID | None
    approved_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BulkOrderWithItemsResponse(BulkOrderResponse):
    """Bulk order session with nested items for detail endpoints."""
    items: list[BulkOrderItemResponse] = []
```

### 2. Bulk Order Service: `backend/app/services/bulk_order_service.py`

Follow the pattern of `backend/app/services/order_service.py`.

**`create_bulk_order()` method — the core logic:**

```
Input: BulkOrderCreate data, company_id (UUID), sub_brand_id (UUID | None), created_by (UUID — local users.id)
Output: BulkOrder

Steps:
1. Validate catalog:
   a. Fetch catalog by catalog_id where company_id matches and deleted_at IS NULL
   b. Raise NotFoundError if not found
   c. Raise ForbiddenError if catalog.status != 'active'
   d. If catalog.payment_model == 'invoice_after_close':
      - Raise ValidationError if buying_window_opens_at is in the future ("Buying window is not open yet")
      - Raise ValidationError if buying_window_closes_at is in the past ("Buying window has closed")
2. Generate unique order number: BLK-YYYYMMDD-XXXX
   - Same collision-retry pattern as OrderService._generate_order_number()
   - Use secrets.token_hex(2).upper() for the random part
   - Check for uniqueness against bulk_orders table; retry up to 5 times
3. Create BulkOrder record with:
   - status='draft'
   - total_items=0
   - total_amount=0.00
   - submitted_at=None
4. flush() + refresh()
5. Return the BulkOrder
```

**`update_bulk_order()` method:**

```
Input: bulk_order_id (UUID), BulkOrderUpdate data, company_id (UUID)
Output: BulkOrder

Steps:
1. Fetch bulk order by id with company_id filter
2. Verify status == 'draft' — raise ForbiddenError if not ("Only draft bulk orders can be edited")
3. Apply non-None fields from data (title, description, notes)
4. flush() + refresh()
5. Return the BulkOrder
```

**`delete_bulk_order()` method:**

```
Input: bulk_order_id (UUID), company_id (UUID)
Output: None

Steps:
1. Fetch bulk order by id with company_id filter
2. Verify status == 'draft' — raise ForbiddenError if not ("Only draft bulk orders can be deleted")
3. Hard-delete all bulk_order_items belonging to this bulk_order_id
4. Hard-delete the bulk_order record
5. flush()
```

Note: Hard delete (not soft delete) because drafts haven't been submitted — they're
analogous to an unsaved document. This is the same pattern as deleting a draft catalog
in Module 3 (which also hard-deletes its catalog_products junction entries).

**`get_bulk_order()` method:**

```
Input: bulk_order_id (UUID), company_id (UUID | None = None)
Output: BulkOrder

Steps:
1. Select BulkOrder where id == bulk_order_id
2. If company_id is not None, add WHERE company_id == company_id
3. Execute, scalar_one_or_none()
4. Raise NotFoundError if None
5. Return
```

**`get_bulk_order_items()` method:**

```
Input: bulk_order_id (UUID)
Output: list[BulkOrderItem]

Steps:
1. Select BulkOrderItem where bulk_order_id matches
2. Order by created_at
3. Return list
```

**`list_bulk_orders()` method:**

```
Input: company_id (UUID), sub_brand_id (UUID | None), page, per_page, status_filter (str | None)
Output: tuple[list[BulkOrder], int]

Steps:
1. Build query with company_id filter
2. If sub_brand_id is not None, add sub_brand_id filter
3. If status_filter is not None, add status filter
4. Count total
5. Paginate, order by created_at desc
6. Return (bulk_orders, total)
```

**`_generate_bulk_order_number()` method:**

Same pattern as `OrderService._generate_order_number()` but with prefix `BLK-`:
- Format: `BLK-YYYYMMDD-XXXX` (e.g., `BLK-20260408-A1B2`)
- Use `secrets.token_hex(2).upper()` for the random part
- Check uniqueness against `BulkOrder.order_number`; retry up to 5 times
- Raise ValidationError on 5 consecutive collisions

**`_validate_catalog()` method:**

Duplicate the catalog validation from `OrderService._validate_catalog()` into
`BulkOrderService`. This keeps each service self-contained. The validation logic is:
1. Fetch Catalog by catalog_id where company_id matches and deleted_at IS NULL
2. Raise NotFoundError if not found
3. Raise ForbiddenError if status != 'active'
4. If payment_model == 'invoice_after_close':
   - Check buying_window_opens_at / buying_window_closes_at against `datetime.now(UTC)`
   - Raise ValidationError with descriptive message if outside window

**Important implementation details:**
- Import `from decimal import Decimal` — use `Decimal` for price arithmetic, not `float`
- `datetime.now(UTC)` for timestamp comparisons
- Follow the `flush() + refresh()` pattern from OrderService for MissingGreenlet prevention
- For delete: use `await self.db.execute(delete(BulkOrderItem).where(BulkOrderItem.bulk_order_id == bulk_order_id))`
  then `await self.db.execute(delete(BulkOrder).where(BulkOrder.id == bulk_order_id))` then `flush()`

### 3. API Endpoints: `backend/app/api/v1/bulk_orders.py`

```python
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_manager
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.bulk_order import (
    BulkOrderCreate,
    BulkOrderItemResponse,
    BulkOrderResponse,
    BulkOrderUpdate,
    BulkOrderWithItemsResponse,
)
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.bulk_order_service import BulkOrderService
from app.services.helpers import resolve_current_user_id

router = APIRouter(prefix="/bulk_orders", tags=["bulk-orders"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.post("/", response_model=ApiResponse[BulkOrderResponse], status_code=201)
async def create_bulk_order(
    data: BulkOrderCreate,
    context: TenantContext = Depends(require_manager),  # manager_or_above only
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Create a new draft bulk order session."""
    company_id = _require_company_id(context)
    created_by = await resolve_current_user_id(db, context.user_id)
    service = BulkOrderService(db)
    bulk_order = await service.create_bulk_order(
        data=data,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        created_by=created_by,
    )
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.get("/", response_model=ApiListResponse[BulkOrderResponse])
async def list_bulk_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[BulkOrderResponse]:
    """List bulk orders visible within the user's tenant scope."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_orders, total = await service.list_bulk_orders(
        company_id, context.sub_brand_id, page, per_page,
        status_filter=status,
    )
    return ApiListResponse(
        data=[BulkOrderResponse.model_validate(bo) for bo in bulk_orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{bulk_order_id}", response_model=ApiResponse[BulkOrderWithItemsResponse])
async def get_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderWithItemsResponse]:
    """Get bulk order detail with items."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.get_bulk_order(bulk_order_id, company_id)
    items = await service.get_bulk_order_items(bulk_order_id)
    response = BulkOrderWithItemsResponse.model_validate(bulk_order)
    response.items = [BulkOrderItemResponse.model_validate(item) for item in items]
    return ApiResponse(data=response)


@router.patch("/{bulk_order_id}", response_model=ApiResponse[BulkOrderResponse])
async def update_bulk_order(
    bulk_order_id: UUID,
    data: BulkOrderUpdate,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Update a draft bulk order session (title, description, notes)."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.update_bulk_order(bulk_order_id, data, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.delete("/{bulk_order_id}", status_code=204)
async def delete_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a draft bulk order and all its items. Hard delete (returns 204)."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    await service.delete_bulk_order(bulk_order_id, company_id)
```

### 4. Register in router: `backend/app/api/v1/router.py`

Add the bulk orders router:
```python
from app.api.v1.bulk_orders import router as bulk_orders_router
v1_router.include_router(bulk_orders_router)
```

### 5. Tests: `backend/tests/test_bulk_orders.py`

Write tests for bulk order session CRUD. You'll need test fixtures for:
- An active catalog with products (reuse the helper pattern from `test_orders.py`)
- Use existing `user_a1_manager` + `user_a1_manager_token` for creating bulk orders
- Use existing multi-tenant fixtures (company_a, company_b)

**Helper functions (define at top of test file):**

```python
async def _create_active_catalog_with_products(
    db: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    payment_model: str = "self_service",
    num_products: int = 2,
    price_overrides: list[float | None] | None = None,
    buying_window_opens_at=None,
    buying_window_closes_at=None,
) -> tuple:
    """Create an active catalog with active products for testing.

    Reuse the same pattern from test_orders.py. Create:
    - A catalog with status='active' and the given payment_model
    - num_products products with status='active', sizes=["S","M","L","XL"],
      decoration_options=["screen_print","embroidery"]
    - CatalogProduct junction entries, with optional price_overrides
    Return (catalog, products, catalog_products)
    """

async def _create_bulk_order_via_api(
    client: AsyncClient,
    token: str,
    catalog_id,
    title: str = "Test Bulk Order",
) -> dict:
    """Create a bulk order via API and return the response JSON data."""
    response = await client.post(
        "/api/v1/bulk_orders/",
        headers={"Authorization": f"Bearer {token}"},
        json={"catalog_id": str(catalog_id), "title": title},
    )
    assert response.status_code == 201
    return response.json()["data"]
```

**Tests to write (~15 tests):**

Functional:
1. `test_create_bulk_order_returns_201` — manager creates draft, verify fields: status='draft',
   total_items=0, total_amount=0, order_number matches `BLK-YYYYMMDD-XXXX` pattern
2. `test_create_bulk_order_validates_catalog_exists` — nonexistent catalog_id → 404
3. `test_create_bulk_order_validates_catalog_active` — draft/submitted catalog → 403
4. `test_create_bulk_order_validates_buying_window_closed` — invoice_after_close catalog with
   past close date → 422 (same pattern as individual order tests in test_orders.py)
5. `test_create_bulk_order_generates_order_number` — verify BLK-YYYYMMDD-XXXX regex pattern
6. `test_list_bulk_orders_paginated` — verify response has data array + meta with total/page/per_page
7. `test_list_bulk_orders_filter_by_status` — ?status=draft returns only drafts (create 2 orders,
   submit one via future Phase 4 or just verify draft filtering works with 1 order)
8. `test_get_bulk_order_detail` — returns bulk order with empty items list (items=[])
9. `test_update_draft_bulk_order` — update title/description/notes, verify changes persist
10. `test_update_non_draft_bulk_order_fails` — For this test, directly insert a bulk_order with
    status='submitted' via admin_db_session, then try to PATCH → 403
11. `test_delete_draft_bulk_order_returns_204` — hard delete, subsequent GET returns 404
12. `test_delete_non_draft_bulk_order_fails` — directly insert a submitted bulk_order, try DELETE → 403

Authorization:
13. `test_employee_cannot_create_bulk_order` — employee token → 403
14. `test_employee_cannot_list_bulk_orders` — employee token → 403

Isolation:
15. `test_company_b_cannot_see_company_a_bulk_orders` — Create a bulk order in Company A via
    Company A's manager. Create a Company B manager (inline user + token). List as Company B
    manager → empty results. GET the specific ID → 404.

**CRITICAL test patterns:**
- Always use trailing slashes on list URLs: `/api/v1/bulk_orders/`
- Use `user_a1_manager_token` (not `company_a_brand_a1_manager_token`) when the endpoint
  calls `resolve_current_user_id` — the token's cognito_sub must match a User record
- For testing update/delete on non-draft status: insert directly into the database via
  `admin_db_session` with `status='submitted'` rather than trying to invoke the submit
  endpoint (which is Phase 4)

Commit message: `feat: add bulk order session CRUD with draft workflow and 15 tests (Module 5 Phase 2)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Bulk Order Item Management (Add, Update, Remove Items)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 5 Phase 3: endpoints for managing items within a draft bulk order
session, including product/employee validation and automatic total recalculation.

## Context

Module 5 Phase 2 is complete — bulk order sessions can be created, listed, viewed,
updated, and deleted. Draft sessions exist but have no items yet. The service,
schemas, and routes are in place.

This phase adds the ability to add items to a draft, update existing items, remove
items, and automatically recalculate the session's `total_items` and `total_amount`
after each modification.

## What to Build

### 1. Add item management methods to `backend/app/services/bulk_order_service.py`

**`add_item()` method:**

```
Input: bulk_order_id (UUID), BulkOrderItemCreate data, company_id (UUID), sub_brand_id (UUID | None)
Output: BulkOrderItem

Steps:
1. Fetch bulk order by id + company_id filter
2. Verify status == 'draft' — raise ForbiddenError if not ("Can only add items to draft bulk orders")
3. Get the catalog_id from the bulk order
4. Validate product is in the catalog:
   a. Fetch CatalogProduct where catalog_id matches and product_id matches
   b. Raise NotFoundError("Product", product_id) if not in catalog
5. Validate product is active:
   a. Fetch Product by product_id where deleted_at IS NULL
   b. Raise NotFoundError if not found
   c. Raise ValidationError if product.status != 'active'
6. Resolve price — SAME PATTERN as Module 4 order placement:
   a. If CatalogProduct.price_override is not None, use it
   b. Else use Product.unit_price
   c. Convert to Decimal for arithmetic
7. Validate size (if provided and product.sizes is not empty):
   a. If size not in product.sizes → raise ValidationError
8. Validate decoration (if provided and product.decoration_options is not empty):
   a. If decoration not in product.decoration_options → raise ValidationError
9. If employee_id is provided, validate employee:
   a. Fetch User by employee_id where company_id matches
   b. Raise ValidationError("Employee not found in this company") if not found
   (Note: company_id match is sufficient — don't require sub_brand match because
   corporate admins may create cross-sub-brand bulk orders)
10. Calculate line_total = unit_price * quantity
11. Create BulkOrderItem record with all snapshotted data:
    - company_id, sub_brand_id from the bulk order
    - product_name=product.name, product_sku=product.sku (snapshot)
    - unit_price, quantity, size, decoration, line_total, notes, employee_id
12. flush() + refresh(item)
13. Recalculate bulk order totals (_recalculate_totals)
14. Return the BulkOrderItem
```

**`update_item()` method:**

```
Input: bulk_order_id (UUID), item_id (UUID), BulkOrderItemUpdate data, company_id (UUID)
Output: BulkOrderItem

Steps:
1. Fetch bulk order — verify draft status
2. Fetch BulkOrderItem by item_id where bulk_order_id matches
3. Raise NotFoundError if not found
4. If quantity is being changed:
   a. Calculate new line_total = existing unit_price * new quantity
   b. Update quantity and line_total
5. If size is being changed:
   a. Fetch the product (using item's product_id)
   b. Validate new size against product.sizes (same validation as add)
   c. Update size
6. If decoration is being changed:
   a. Fetch the product (using item's product_id)
   b. Validate new decoration against product.decoration_options
   c. Update decoration
7. If employee_id is being changed:
   a. If not None, validate employee exists in same company
   b. Update employee_id
8. If notes is being changed, update notes
9. flush() + refresh(item)
10. Recalculate bulk order totals
11. Return the BulkOrderItem

NOTE: The product_id CANNOT be changed — to change the product, the manager must
remove the item and add a new one. This preserves the price snapshot integrity.
```

**`remove_item()` method:**

```
Input: bulk_order_id (UUID), item_id (UUID), company_id (UUID)
Output: None

Steps:
1. Fetch bulk order — verify draft status
2. Fetch BulkOrderItem by item_id where bulk_order_id matches
3. Raise NotFoundError if not found
4. Hard-delete the item
5. flush()
6. Recalculate bulk order totals
```

**`_recalculate_totals()` method:**

```
Input: bulk_order_id (UUID)
Output: None (modifies bulk_order in-place)

Steps:
1. Query SUM(quantity) and SUM(line_total) from bulk_order_items WHERE bulk_order_id matches
   - Use func.coalesce(..., 0) to handle empty item sets
2. Fetch the bulk order
3. Set total_items = sum of quantities (or 0 if no items)
4. Set total_amount = sum of line_totals (or Decimal("0"))
5. flush() + refresh(bulk_order)
```

**Important implementation details:**
- Use `from sqlalchemy import delete, func` for delete operations and aggregation
- `Decimal` for all price arithmetic (not float)
- `_recalculate_totals()` is called after EVERY item add/update/remove operation
- The `total_items` field represents the total count of individual items (SUM of quantities),
  NOT the number of BulkOrderItem rows. For example, 3 BulkOrderItem rows with quantities
  [5, 10, 3] means total_items = 18.
- Employee validation checks `company_id` only (not sub_brand_id), to support corporate
  admin scenarios where the bulk order spans sub-brands

### 2. Add item management routes to `backend/app/api/v1/bulk_orders.py`

Add these endpoints to the existing router:

```python
@router.post(
    "/{bulk_order_id}/items/",
    response_model=ApiResponse[BulkOrderItemResponse],
    status_code=201,
)
async def add_item(
    bulk_order_id: UUID,
    data: BulkOrderItemCreate,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderItemResponse]:
    """Add an item to a draft bulk order."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    item = await service.add_item(
        bulk_order_id, data, company_id, context.sub_brand_id,
    )
    return ApiResponse(data=BulkOrderItemResponse.model_validate(item))


@router.patch(
    "/{bulk_order_id}/items/{item_id}",
    response_model=ApiResponse[BulkOrderItemResponse],
)
async def update_item(
    bulk_order_id: UUID,
    item_id: UUID,
    data: BulkOrderItemUpdate,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderItemResponse]:
    """Update an item within a draft bulk order."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    item = await service.update_item(bulk_order_id, item_id, data, company_id)
    return ApiResponse(data=BulkOrderItemResponse.model_validate(item))


@router.delete("/{bulk_order_id}/items/{item_id}", status_code=204)
async def remove_item(
    bulk_order_id: UUID,
    item_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove an item from a draft bulk order (hard delete, returns 204)."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    await service.remove_item(bulk_order_id, item_id, company_id)
```

You will also need to add `BulkOrderItemCreate` and `BulkOrderItemUpdate` to the
imports at the top of the route file.

### 3. Tests: Add to `backend/tests/test_bulk_orders.py`

**Item Management Tests (~14 tests):**

Functional:
1. `test_add_item_to_draft_bulk_order` — Add an item. Verify response contains:
   product_name and product_sku (snapshotted from product), unit_price (from product or
   catalog override), quantity, line_total = unit_price * quantity, employee_id=None.
   Verify the bulk order's total_items and total_amount are updated (GET the bulk order
   detail after adding).
2. `test_add_item_validates_product_in_catalog` — product_id exists in the products table
   but NOT in the catalog's catalog_products → 404
3. `test_add_item_validates_product_active` — product is in the catalog but has
   status='draft' → validation error (400/422)
4. `test_add_item_uses_catalog_price_override` — Set a price_override on the
   CatalogProduct (e.g., 19.99 vs product unit_price 29.99). Verify the item's
   unit_price and line_total use the override.
5. `test_add_item_with_employee_id` — Provide a valid employee_id (use `user_a1_employee`
   fixture). Verify the item's employee_id matches.
6. `test_add_item_with_invalid_employee_fails` — Provide an employee_id from Company B.
   Should return a validation error.
7. `test_add_item_validates_size` — Provide a size that's NOT in product.sizes
   (e.g., "XXXL" when sizes are ["S","M","L","XL"]) → validation error
8. `test_add_item_validates_decoration` — Provide a decoration NOT in
   product.decoration_options → validation error
9. `test_update_item_quantity_recalculates_totals` — Add an item (qty=2), then PATCH
   with quantity=5. Verify the item's line_total updated. GET the bulk order detail and
   verify total_items and total_amount reflect the new quantity.
10. `test_update_item_on_non_draft_fails` — Insert a submitted bulk_order with an item
    directly via admin_db_session. Try to PATCH the item → 403.
11. `test_remove_item_recalculates_totals` — Add 2 items, then DELETE one. Verify the
    bulk order's total_items and total_amount decreased to reflect only the remaining item.
12. `test_remove_item_returns_204` — Verify the response status code is 204 with no body.
    Subsequent GET of the bulk order shows the item is gone.

State:
13. `test_add_item_to_submitted_bulk_order_fails` — Insert a submitted bulk_order via
    admin_db_session. Try POST to add item → 403.
14. `test_bulk_order_totals_reflect_all_items` — Add 3 items with different quantities
    and prices. GET the bulk order detail and verify:
    - total_items = sum of all quantities
    - total_amount = sum of all line_totals
    - items array has 3 entries

**Test fixture notes:**
- Reuse the `_create_active_catalog_with_products` helper from Phase 2
- For employee validation tests, use `user_a1_employee` for valid employee and create a
  Company B user inline for invalid employee
- For non-draft status tests: insert directly into admin_db_session with status='submitted'
  (don't invoke the submit endpoint which is in Phase 4)
- For catalog price override tests, create catalog_products with specific price_override values

Commit message: `feat: add bulk order item management with validation and total recalculation and 14 tests (Module 5 Phase 3)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: Bulk Order Status Transitions (Submit, Approve, Process, Ship, Deliver, Cancel)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 5 Phase 4: status transition endpoints for the bulk order lifecycle.

## Context

Module 5 Phases 2-3 are complete:
- Bulk order sessions can be created, listed, viewed, updated, and deleted (Phase 2)
- Items can be added, updated, and removed from draft bulk orders (Phase 3)
- Totals are automatically recalculated on item changes
- All endpoints require `manager_or_above`

Now we need the status lifecycle to move bulk orders through the approval and
fulfillment workflow.

## Bulk Order Status Lifecycle

```
draft → submitted → approved → processing → shipped → delivered
draft → cancelled       (creator or manager_or_above)
submitted → cancelled   (manager_or_above only)
approved → cancelled    (manager_or_above only)
```

**Key differences from individual order lifecycle (Module 4):**
- Bulk orders start as `draft` (individual orders start as `pending` — no draft stage)
- The `draft → submitted` transition is explicit and requires at least one item
- Submit records `submitted_at` timestamp
- Submit "locks" the bulk order — no more item additions/updates/removals after submission
- Approve records `approved_by` and `approved_at` (individual order approve does not)
- Cancel from `approved` is allowed (individual orders allow cancel from `approved` too)
- `processing`, `shipped`, `delivered` cannot be cancelled (same as individual orders)

## What to Build

### 1. Add status transition methods to `backend/app/services/bulk_order_service.py`

**`submit_bulk_order()`:**

```python
async def submit_bulk_order(
    self, bulk_order_id: UUID, company_id: UUID,
) -> BulkOrder:
    """Submit a draft bulk order for approval.

    Guards:
    1. Must be in 'draft' status → ForbiddenError otherwise
    2. Must have at least one item → ValidationError("Cannot submit a bulk order with no items")
    3. Records submitted_at = datetime.now(UTC)
    4. Sets status = 'submitted'
    5. flush() + refresh()
    """
```

Implementation:
```python
bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
if bulk_order.status != "draft":
    raise ForbiddenError("Only draft bulk orders can be submitted")

# Check for at least one item
item_count = await self.db.scalar(
    select(func.count()).select_from(
        select(BulkOrderItem.id).where(
            BulkOrderItem.bulk_order_id == bulk_order_id
        ).subquery()
    )
)
if item_count == 0:
    raise ValidationError("Cannot submit a bulk order with no items")

bulk_order.status = "submitted"
bulk_order.submitted_at = datetime.now(UTC)
await self.db.flush()
await self.db.refresh(bulk_order)
return bulk_order
```

**`approve_bulk_order()`:**

```python
async def approve_bulk_order(
    self, bulk_order_id: UUID, company_id: UUID, approved_by: UUID,
) -> BulkOrder:
    """Approve a submitted bulk order.

    1. Must be in 'submitted' status → ForbiddenError otherwise
    2. Records approved_by and approved_at = datetime.now(UTC)
    3. Sets status = 'approved'
    """
```

Implementation:
```python
bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
if bulk_order.status != "submitted":
    raise ForbiddenError("Only submitted bulk orders can be approved")
bulk_order.status = "approved"
bulk_order.approved_by = approved_by
bulk_order.approved_at = datetime.now(UTC)
await self.db.flush()
await self.db.refresh(bulk_order)
return bulk_order
```

**`process_bulk_order()`:**

```python
async def process_bulk_order(self, bulk_order_id: UUID, company_id: UUID) -> BulkOrder:
    """Mark approved → processing."""
    bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
    if bulk_order.status != "approved":
        raise ForbiddenError("Only approved bulk orders can be marked as processing")
    bulk_order.status = "processing"
    await self.db.flush()
    await self.db.refresh(bulk_order)
    return bulk_order
```

**`ship_bulk_order()`:**

```python
async def ship_bulk_order(self, bulk_order_id: UUID, company_id: UUID) -> BulkOrder:
    """Mark processing → shipped."""
    bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
    if bulk_order.status != "processing":
        raise ForbiddenError("Only processing bulk orders can be shipped")
    bulk_order.status = "shipped"
    await self.db.flush()
    await self.db.refresh(bulk_order)
    return bulk_order
```

**`deliver_bulk_order()`:**

```python
async def deliver_bulk_order(self, bulk_order_id: UUID, company_id: UUID) -> BulkOrder:
    """Mark shipped → delivered."""
    bulk_order = await self.get_bulk_order(bulk_order_id, company_id)
    if bulk_order.status != "shipped":
        raise ForbiddenError("Only shipped bulk orders can be delivered")
    bulk_order.status = "delivered"
    await self.db.flush()
    await self.db.refresh(bulk_order)
    return bulk_order
```

**`cancel_bulk_order()`:**

```python
async def cancel_bulk_order(
    self, bulk_order_id: UUID, company_id: UUID,
    cancelled_by_user_id: UUID, is_manager_or_above: bool,
) -> BulkOrder:
    """Cancel a draft, submitted, or approved bulk order.

    Authorization:
    - draft: creator (bulk_order.created_by) or manager_or_above
    - submitted: manager_or_above only
    - approved: manager_or_above only
    - processing/shipped/delivered/cancelled: CANNOT cancel → ForbiddenError
    """
```

Implementation:
```python
bulk_order = await self.get_bulk_order(bulk_order_id, company_id)

if bulk_order.status == "draft":
    # Creator or manager can cancel drafts
    if not is_manager_or_above and bulk_order.created_by != cancelled_by_user_id:
        raise ForbiddenError("Only the creator or a manager can cancel this bulk order")
elif bulk_order.status in ("submitted", "approved"):
    if not is_manager_or_above:
        raise ForbiddenError("Only managers can cancel submitted or approved bulk orders")
else:
    raise ForbiddenError(f"Cannot cancel a bulk order with status '{bulk_order.status}'")

bulk_order.status = "cancelled"
bulk_order.cancelled_at = datetime.now(UTC)
bulk_order.cancelled_by = cancelled_by_user_id
await self.db.flush()
await self.db.refresh(bulk_order)
return bulk_order
```

### 2. Add transition routes to `backend/app/api/v1/bulk_orders.py`

Add these endpoints to the existing router. Follow the same pattern as
`backend/app/api/v1/orders.py` status transition endpoints:

```python
@router.post("/{bulk_order_id}/submit", response_model=ApiResponse[BulkOrderResponse])
async def submit_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Submit a draft bulk order for approval. Must have at least one item."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.submit_bulk_order(bulk_order_id, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/approve", response_model=ApiResponse[BulkOrderResponse])
async def approve_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Approve a submitted bulk order. Records approved_by."""
    company_id = _require_company_id(context)
    approved_by = await resolve_current_user_id(db, context.user_id)
    service = BulkOrderService(db)
    bulk_order = await service.approve_bulk_order(bulk_order_id, company_id, approved_by)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/process", response_model=ApiResponse[BulkOrderResponse])
async def process_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Mark an approved bulk order as processing."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.process_bulk_order(bulk_order_id, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/ship", response_model=ApiResponse[BulkOrderResponse])
async def ship_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Mark a processing bulk order as shipped."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.ship_bulk_order(bulk_order_id, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/deliver", response_model=ApiResponse[BulkOrderResponse])
async def deliver_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Mark a shipped bulk order as delivered."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.deliver_bulk_order(bulk_order_id, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/cancel", response_model=ApiResponse[BulkOrderResponse])
async def cancel_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Cancel a draft, submitted, or approved bulk order."""
    company_id = _require_company_id(context)
    cancelled_by = await resolve_current_user_id(db, context.user_id)
    service = BulkOrderService(db)
    bulk_order = await service.cancel_bulk_order(
        bulk_order_id, company_id, cancelled_by, context.is_manager_or_above,
    )
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))
```

### 3. Tests: Add to `backend/tests/test_bulk_orders.py`

You'll need a helper to create a bulk order with items (for submit tests):

```python
async def _create_bulk_order_with_items(
    client: AsyncClient,
    token: str,
    catalog_id,
    product_id,
    title: str = "Bulk Order With Items",
    num_items: int = 2,
) -> dict:
    """Create a bulk order via API, add items, return the bulk order data."""
    bo_data = await _create_bulk_order_via_api(client, token, catalog_id, title)
    for i in range(num_items):
        await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/items/",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": str(product_id), "quantity": i + 1},
        )
    return bo_data
```

**Status Transition Tests (~16 tests):**

Lifecycle (happy path):
1. `test_submit_draft_bulk_order` — Create a bulk order with items via API. POST /submit.
   Verify: status='submitted', submitted_at is not None (is a datetime string).
2. `test_submit_empty_bulk_order_fails` — Create a bulk order with NO items. POST /submit
   → 400/422 with error message about no items.
3. `test_submit_non_draft_fails` — Submit a bulk order, then try to submit again → 403.
4. `test_approve_submitted_bulk_order` — Submit, then POST /approve. Verify: status='approved',
   approved_by matches the manager's user ID, approved_at is not None.
5. `test_approve_non_submitted_fails` — Try to approve a draft bulk order → 403.
6. `test_process_approved_bulk_order` — Submit → approve → POST /process. Verify status='processing'.
7. `test_ship_processing_bulk_order` — Submit → approve → process → POST /ship. Verify status='shipped'.
8. `test_deliver_shipped_bulk_order` — Full lifecycle: submit → approve → process → ship →
   POST /deliver. Verify status='delivered'.

Cancel:
9. `test_cancel_draft_bulk_order` — POST /cancel on draft. Verify: status='cancelled',
   cancelled_at is not None, cancelled_by matches the user ID.
10. `test_cancel_submitted_bulk_order` — Submit, then cancel → status='cancelled'.
11. `test_cancel_approved_bulk_order` — Submit → approve → cancel → status='cancelled'.
12. `test_cancel_processing_bulk_order_fails` — Submit → approve → process → cancel → 403.
13. `test_cancel_delivered_bulk_order_fails` — Full lifecycle to delivered → cancel → 403.

Item locking after submit:
14. `test_cannot_add_item_after_submit` — Submit the bulk order, then try POST /items/ → 403.
15. `test_cannot_update_item_after_submit` — Submit, then PATCH an item → 403.
16. `test_cannot_remove_item_after_submit` — Submit, then DELETE an item → 403.

**Test helper for driving a bulk order through lifecycle states:**

For tests that need a bulk order in a specific state (e.g., approved, processing),
build up to that state through the API rather than direct DB insertion. This validates
the transitions actually work:

```python
async def _submit_bulk_order(client, token, bulk_order_id) -> dict:
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]

async def _approve_bulk_order(client, token, bulk_order_id) -> dict:
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]

# Similar for _process, _ship, _deliver
```

**Test fixture notes:**
- All transition endpoints use `require_manager`, so use `user_a1_manager_token`
- For the approve test, `resolve_current_user_id` is called — use `user_a1_manager_token`
  which has a matching User record
- For cancel tests, use `user_a1_manager_token` (which has `is_manager_or_above = True`)
- For item locking tests: create a bulk order with items, submit it, then attempt item
  operations and verify 403 responses

Commit message: `feat: add bulk order status transitions with submit guards and 16 tests (Module 5 Phase 4)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: Platform Admin Endpoints (Cross-Company Bulk Order Visibility)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 5 Phase 5: platform admin endpoints for cross-company bulk order
visibility, following the same pattern as `backend/app/api/v1/platform/orders.py`.

## Context

Module 5 Phases 2-4 are complete:
- Bulk order sessions have full CRUD (create, list, get, update, delete draft)
- Item management with validation and automatic total recalculation
- Full status lifecycle (draft → submitted → approved → processing → shipped → delivered)
- Cancel support (draft, submitted, approved → cancelled)
- Item locking after submit
- All tenant-scoped endpoints require `manager_or_above`

Now we need the reel48_admin cross-company view, matching the established pattern.

## What to Build

### 1. Add platform admin method to `backend/app/services/bulk_order_service.py`

```python
async def list_all_bulk_orders(
    self,
    page: int,
    per_page: int,
    status_filter: str | None = None,
    company_id_filter: UUID | None = None,
) -> tuple[list[BulkOrder], int]:
    """List bulk orders across ALL companies. For reel48_admin platform endpoints."""
    query = select(BulkOrder)
    if status_filter is not None:
        query = query.where(BulkOrder.status == status_filter)
    if company_id_filter is not None:
        query = query.where(BulkOrder.company_id == company_id_filter)

    total = await self.db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    query = query.order_by(BulkOrder.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await self.db.execute(query)
    return list(result.scalars().all()), total or 0
```

### 2. Create `backend/app/api/v1/platform/bulk_orders.py`

Follow the exact pattern of `backend/app/api/v1/platform/orders.py`:

```python
"""Platform admin endpoints for cross-company bulk order visibility.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.bulk_order import (
    BulkOrderItemResponse,
    BulkOrderResponse,
    BulkOrderWithItemsResponse,
)
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.bulk_order_service import BulkOrderService

router = APIRouter(prefix="/platform/bulk_orders", tags=["platform-bulk-orders"])


@router.get("/", response_model=ApiListResponse[BulkOrderResponse])
async def list_all_bulk_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    company_id: UUID | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[BulkOrderResponse]:
    """List ALL bulk orders across all companies."""
    service = BulkOrderService(db)
    bulk_orders, total = await service.list_all_bulk_orders(
        page, per_page,
        status_filter=status,
        company_id_filter=company_id,
    )
    return ApiListResponse(
        data=[BulkOrderResponse.model_validate(bo) for bo in bulk_orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{bulk_order_id}", response_model=ApiResponse[BulkOrderWithItemsResponse])
async def get_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderWithItemsResponse]:
    """Get any bulk order detail with items (cross-company)."""
    service = BulkOrderService(db)
    bulk_order = await service.get_bulk_order(bulk_order_id)  # No company_id filter
    items = await service.get_bulk_order_items(bulk_order_id)
    response = BulkOrderWithItemsResponse.model_validate(bulk_order)
    response.items = [BulkOrderItemResponse.model_validate(item) for item in items]
    return ApiResponse(data=response)
```

### 3. Update `backend/app/api/v1/router.py`

Add the platform bulk orders router:
```python
from app.api.v1.platform.bulk_orders import router as platform_bulk_orders_router
v1_router.include_router(platform_bulk_orders_router)
```

### 4. Tests: `backend/tests/test_platform_bulk_orders.py`

Create a new test file following the pattern of `backend/tests/test_platform_orders.py`.

You'll need helpers to create bulk orders in both Company A and Company B:

```python
async def _create_active_catalog(
    db: AsyncSession, company_id, sub_brand_id, created_by,
) -> Catalog:
    """Create an active catalog (same helper pattern as test_platform_orders.py)."""
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Platform Test Catalog {uuid4().hex[:6]}",
        slug=f"platform-cat-{uuid4().hex[:6]}",
        payment_model="self_service",
        status="active",
        created_by=created_by,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _create_product_in_catalog(
    db: AsyncSession, catalog, company_id, sub_brand_id, created_by,
) -> Product:
    """Create an active product and add it to the catalog."""
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Platform Product {uuid4().hex[:6]}",
        sku=f"PLAT-{uuid4().hex[:8].upper()}",
        unit_price=25.00,
        sizes=["M", "L"],
        decoration_options=[],
        image_urls=[],
        status="active",
        created_by=created_by,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)

    cp = CatalogProduct(
        catalog_id=catalog.id,
        product_id=product.id,
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        display_order=0,
    )
    db.add(cp)
    await db.flush()
    return product
```

For creating bulk orders via API, you'll need manager tokens for both companies.
Company A already has `user_a1_manager` + `user_a1_manager_token`. For Company B,
create a manager user inline using `create_test_token`:

```python
async def _create_company_b_manager(db, company_b):
    """Create a manager user in Company B with matching token."""
    company, brand_b1 = company_b
    user = User(
        company_id=company.id,
        sub_brand_id=brand_b1.id,
        cognito_sub=str(uuid4()),
        email=f"mgr-b-{uuid4().hex[:6]}@test.com",
        full_name="Manager B1",
        role="regional_manager",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    token = create_test_token(
        cognito_sub=user.cognito_sub,
        company_id=str(company.id),
        sub_brand_id=str(brand_b1.id),
        role="regional_manager",
    )
    return user, token
```

**Tests to write (~6 tests):**

1. `test_platform_list_bulk_orders_returns_all_companies` — Create a bulk order in
   Company A (via API as Company A's manager) and one in Company B (via API as Company
   B's manager). List as reel48_admin → both appear.
2. `test_platform_list_bulk_orders_filter_by_company` — ?company_id={company_a.id}
   returns only Company A's bulk orders.
3. `test_platform_list_bulk_orders_filter_by_status` — Create two bulk orders in Company A.
   Submit one via API. Filter by ?status=draft → only the draft one. Filter by
   ?status=submitted → only the submitted one.
4. `test_platform_get_bulk_order_detail` — reel48_admin can get any bulk order with items.
   Create a bulk order with items in Company A. GET as reel48_admin → returns the bulk
   order with items array populated.
5. `test_platform_bulk_orders_requires_reel48_admin` — Corporate admin token → 403.
6. `test_platform_bulk_orders_employee_gets_403` — Employee token → 403.

**Token notes:**
- Use `reel48_admin_user_token` for the platform admin endpoints (has a matching User record)
- Use `user_a_corporate_admin_token` for the 403 test (corporate admin, not platform admin)
- Use `user_a1_employee_token` for the employee 403 test

Commit message: `feat: add platform admin bulk order endpoints for cross-company visibility with 6 tests (Module 5 Phase 5)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: End-of-Module Harness Maintenance
# ═══════════════════════════════════════════════════════════════════════════════

Perform the end-of-module harness review for Module 5 (Bulk Ordering System).

## Context

Module 5 is complete. All phases (1-5) are built and tested:
- Phase 1: bulk_orders + bulk_order_items tables with RLS (migration 005)
- Phase 2: Bulk order session CRUD with draft workflow (~15 tests)
- Phase 3: Item management with validation and total recalculation (~14 tests)
- Phase 4: Status transitions with submit guard and item locking (~16 tests)
- Phase 5: Platform admin cross-company endpoints (~6 tests)

Run the full test suite first to confirm everything passes.

## What to Do

### Step 1: Run Full Test Suite

```bash
cd backend && python -m pytest tests/ -x -v
```

Record the total test count. All tests (existing 265 + new Module 5) must pass.

### Step 2: Update `backend/CLAUDE.md`

Add the following sections, following the existing pattern established by Module 3 and
Module 4 table schemas and lifecycle documentation already in `backend/CLAUDE.md`:

**Add Module 5 Table Schemas section** (after the existing Module 4 section):

Add these with the standard harness annotation:
```markdown
# --- ADDED 2026-04-XX during Module 5 Phase 6 ---
# Reason: Module 5 adds bulk_orders and bulk_order_items tables. Documenting them here
# for implementation consistency and FK references in future modules (Invoicing).
# Impact: Future modules know the bulk_orders/bulk_order_items shape for FK references.
```

Document both tables with all columns, constraints, indexes, and RLS policies.

**Add Bulk Order Status Lifecycle & Transitions section:**

```markdown
### Bulk Order Status Lifecycle & Transitions

# --- ADDED 2026-04-XX during Module 5 Phase 6 ---
# Reason: Bulk orders have a distinct lifecycle from individual orders (includes
# draft stage, submit guard, item locking). Documenting prevents confusion in
# future modules (Invoicing needs to know when a bulk order is ready for billing).
# Impact: Module 7 (Invoicing) knows bulk orders in 'delivered' or 'approved' status
# are eligible for invoice creation.

### Status Transitions
` ` `
draft → submitted → approved → processing → shipped → delivered
draft → cancelled       (creator or manager_or_above)
submitted → cancelled   (manager_or_above only)
approved → cancelled    (manager_or_above only)
` ` `

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

### Key Differences from Individual Orders (Module 4)
- Bulk orders start as `draft` (individual orders start as `pending`)
- Explicit `draft → submitted` transition with item guard
- Items are locked after submission (individual orders have no draft editing stage)
- `approved_by` and `approved_at` tracked on bulk orders (not on individual orders)
- Created by managers/admins (individual orders created by any authenticated user)
```

**Add Bulk Order Patterns section:**

Document:
- Draft workflow: create session → add items → submit (unlike individual orders)
- Total recalculation: `total_items` (SUM of quantities) and `total_amount` (SUM of
  line_totals) auto-updated on every item add/update/remove
- Employee assignment: items can target specific employees (via `employee_id`) or be
  unassigned (NULL = general stock). Employee validated at company level only.
- Order number format: `BLK-YYYYMMDD-XXXX` (same collision-retry pattern as `ORD-`)
- Price snapshotting: same pattern as individual orders (catalog override → product price)
- Hard delete for drafts (not soft delete) — drafts haven't been submitted

**Add to the "Which Base to Use" table:**
```
| `bulk_orders` | `TenantBase` | Scoped to company + sub-brand |
| `bulk_order_items` | `TenantBase` | Scoped to company + sub-brand |
```

### Step 3: End-of-Session Self-Audit

Answer the 5-question checklist from `CLAUDE.md`:

1. **New pattern introduced?** — Draft workflow (create → add items → submit), automatic
   total recalculation on item changes, item-level employee assignment, submit guard
   (must have items), post-submit item locking (no modifications), hard-delete for
   draft bulk orders
2. **Existing pattern violated?** — Check if any patterns from the harness were deviated from.
   Expected: No violations. The module follows the same service → route → test pattern,
   same RLS policies, same response format, same role checks as Modules 1-4.
3. **New decision made?** — Document non-obvious choices:
   - Hard delete for draft bulk orders (not soft delete) — drafts are ephemeral like
     unsaved documents. Same reasoning as draft catalog deletion in Module 3.
   - `employee_id` nullable on `bulk_order_items` — supports "general stock" orders
     where items aren't assigned to specific employees.
   - `total_items` = SUM(quantity), NOT count of rows. This means a bulk order with
     3 BulkOrderItem rows (quantities 5, 10, 3) has total_items=18.
   - Employee validation checks `company_id` only (not `sub_brand_id`) to support
     corporate admin cross-sub-brand bulk orders.
   - Catalog validation is duplicated in BulkOrderService (not extracted to a shared
     helper) to keep services self-contained. Could be refactored later if needed.
4. **Missing guidance discovered?** — Note any scenarios where judgment calls were needed.
   Consider whether a shared catalog validation helper should be documented for future
   modules, or if the duplication is acceptable.
5. **Prompt template needed?** — The draft-workflow pattern (create → add items → submit →
   approve) may recur in future contexts (e.g., Module 8 employee engagement could have
   "wishlists" or "reward requests"). Consider whether a `prompts/draft-workflow.md`
   template would be valuable, or if the pattern is too domain-specific.

### Step 4: Update `docs/harness-changelog.md`

Append a new entry at the TOP of the file (newest first):

```markdown
## 2026-04-XX — Module 5 Completion (Bulk Ordering System)

**Type:** End-of-module self-audit + harness review
**Module:** Module 5 — Bulk Ordering System (Phases 1-6)

### Self-Audit Checklist
- [x/blank] **New pattern?** → {what was added to backend/CLAUDE.md}
- [x/blank] **Pattern violated?** → {any deviations from harness patterns}
- [x/blank] **New decision?** → {non-obvious choices documented above}
- [x/blank] **Missing guidance?** → {gaps found and filled}
- [x/blank] **Reusable task?** → {prompt templates created, if any}
- [x] **Changelog updated?** → This entry

### Harness Files Updated
- **`backend/CLAUDE.md`** — Added Module 5 Table Schemas (bulk_orders, bulk_order_items),
  Bulk Order Status Lifecycle & Transitions, Bulk Order Patterns sections. Updated
  "Which Base to Use" table.

### Post-Module Pattern Consistency Review
- All {N} bulk order endpoints + 2 platform endpoints follow the established
  route → service → model pattern
- RLS policies follow the standard two-policy pattern (company isolation PERMISSIVE +
  sub-brand scoping RESTRICTIVE)
- All endpoints use TenantContext from JWT with defense-in-depth company_id filtering
- Status transitions use POST /{action} pattern (consistent with Module 4 orders)
- Tests cover functional, authorization, isolation, and state transition categories

### Session Metrics
- Tests before module: 265
- Tests after module: {count}
- New tests added: ~51
- Harness gaps found: {count}
```

### Step 5: Commit

Commit message: `chore: Module 5 harness review — add bulk order schemas, lifecycle docs, and changelog entry`
