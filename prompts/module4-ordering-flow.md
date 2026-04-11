# Module 4: Ordering Flow — Phase-by-Phase Implementation Prompts
#
# Each phase below is a self-contained prompt designed to be pasted into a
# fresh Claude Code session. The session will read the CLAUDE.md harness files
# automatically — these prompts provide MODULE-SPECIFIC context that the
# harness doesn't cover.
#
# IMPORTANT: Run phases in order. Each phase depends on the prior phase's output.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Database Migration — Orders & Order Line Items
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 4 Phase 1: the Alembic migration, SQLAlchemy models, and test
infrastructure updates for the individual ordering flow.

## Context

We are building Module 4 (Ordering Flow) of the Reel48+ enterprise apparel platform.
Modules 1-3 are complete:
- Module 1: Auth, Companies, Sub-Brands, Users (migration `001`)
- Module 2: Employee Profiles (migration `002`)
- Module 3: Products, Catalogs, Catalog-Products (migration `003`)

The current test suite has 193+ passing tests. The branch is
`feature/module3-phase4-platform-admin`. Create a new branch
`feature/module4-phase1-order-tables` from `main` before starting.

## What to Build

### 1. Alembic migration: `backend/migrations/versions/004_create_module4_order_tables.py`

Create two tables in a single migration (same pattern as migration `003`):

**`orders` table (TenantBase shape):**
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL FK → companies.id
sub_brand_id            UUID        NULL FK → sub_brands.id
user_id                 UUID        NOT NULL FK → users.id        -- employee who placed the order
catalog_id              UUID        NOT NULL FK → catalogs.id     -- which catalog the order is from
order_number            VARCHAR(30) NOT NULL UNIQUE               -- e.g. "ORD-20260408-A1B2"
status                  VARCHAR(20) NOT NULL DEFAULT 'pending'
shipping_address_line1  VARCHAR(255) NULL
shipping_address_line2  VARCHAR(255) NULL
shipping_city           VARCHAR(100) NULL
shipping_state          VARCHAR(100) NULL
shipping_zip            VARCHAR(20)  NULL
shipping_country        VARCHAR(100) NULL
notes                   TEXT         NULL
subtotal                NUMERIC(10,2) NOT NULL DEFAULT 0
total_amount            NUMERIC(10,2) NOT NULL DEFAULT 0
cancelled_at            TIMESTAMP WITH TIME ZONE NULL
cancelled_by            UUID         NULL FK → users.id
created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
```

CHECK constraints:
- `ck_orders_status_valid`: status IN ('pending', 'approved', 'processing', 'shipped', 'delivered', 'cancelled')
- `ck_orders_subtotal_non_negative`: subtotal >= 0
- `ck_orders_total_amount_non_negative`: total_amount >= 0

Indexes:
- `ix_orders_company_id` on (company_id)
- `ix_orders_sub_brand_id` on (sub_brand_id)
- `ix_orders_user_id` on (user_id)
- `ix_orders_catalog_id` on (catalog_id)
- `ix_orders_company_id_status` on (company_id, status)

RLS policies (both in same migration):
- `orders_company_isolation` — PERMISSIVE, standard company isolation pattern
- `orders_sub_brand_scoping` — RESTRICTIVE, standard sub-brand scoping pattern

**`order_line_items` table (TenantBase shape):**
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL FK → companies.id
sub_brand_id            UUID        NULL FK → sub_brands.id
order_id                UUID        NOT NULL FK → orders.id
product_id              UUID        NOT NULL FK → products.id
product_name            VARCHAR(255) NOT NULL   -- snapshot at order time
product_sku             VARCHAR(100) NOT NULL   -- snapshot at order time
unit_price              NUMERIC(10,2) NOT NULL  -- price at order time
quantity                INTEGER      NOT NULL DEFAULT 1
size                    VARCHAR(20)  NULL
decoration              VARCHAR(255) NULL
line_total              NUMERIC(10,2) NOT NULL  -- unit_price * quantity
created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
```

CHECK constraints:
- `ck_order_line_items_quantity_positive`: quantity > 0
- `ck_order_line_items_unit_price_non_negative`: unit_price >= 0
- `ck_order_line_items_line_total_non_negative`: line_total >= 0

Indexes:
- `ix_order_line_items_company_id` on (company_id)
- `ix_order_line_items_sub_brand_id` on (sub_brand_id)
- `ix_order_line_items_order_id` on (order_id)
- `ix_order_line_items_product_id` on (product_id)

RLS policies:
- `order_line_items_company_isolation` — PERMISSIVE
- `order_line_items_sub_brand_scoping` — RESTRICTIVE

FK naming convention: `fk_{table}_{column}_{ref_table}` (e.g., `fk_orders_user_id_users`).

Downgrade: drop policies, disable RLS, drop indexes, drop tables (order_line_items first, then orders).

Follow the exact style of `backend/migrations/versions/003_create_module3_catalog_tables.py` — use `sa.Column`, `UUID(as_uuid=True)`, `sa.ForeignKey(name=...)`, `sa.text("now()")` for server_default timestamps, and `op.execute()` for RLS statements.

### 2. SQLAlchemy Models

**`backend/app/models/order.py`:**
```python
class Order(TenantBase):
    __tablename__ = "orders"
    # All columns from migration above. Follow the same style as Product model
    # in backend/app/models/product.py (Column imports, FK definitions, etc.)
```

**`backend/app/models/order_line_item.py`:**
```python
class OrderLineItem(TenantBase):
    __tablename__ = "order_line_items"
    # All columns from migration above.
```

### 3. Update `backend/app/models/__init__.py`

Add imports and `__all__` exports for `Order` and `OrderLineItem`.

### 4. Update test infrastructure: `backend/tests/conftest.py`

In the `setup_database` fixture, add `"orders"` and `"order_line_items"` to the
`tables` list that gets `GRANT SELECT, INSERT, UPDATE, DELETE ... TO reel48_app`.

### Verification

After building:
1. Run `cd backend && alembic upgrade head` against the test database to verify migration applies
2. Run `cd backend && python -m pytest tests/ -x` to confirm all 193+ existing tests still pass
3. Verify `alembic downgrade -1` then `alembic upgrade head` works (reversibility)

### Do NOT Build Yet
- No schemas, services, or API endpoints in this phase
- No new test files — just verify existing tests pass

Commit message: `feat: add orders and order_line_items tables with RLS (Module 4 Phase 1)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Order Placement (Create Order Endpoint)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 4 Phase 2: the order placement endpoint, service, schemas, and tests.

## Context

Module 4 Phase 1 is complete — the `orders` and `order_line_items` tables exist
with RLS policies and SQLAlchemy models. We are on branch
`feature/module4-phase1-order-tables` (or the appropriate branch from Phase 1).

Modules 1-3 provide:
- Auth with TenantContext (company_id, sub_brand_id from JWT)
- Employee profiles with delivery addresses
- Products with status lifecycle (draft → submitted → approved → active → archived)
- Catalogs with payment_model (`self_service` or `invoice_after_close`) and buying windows
- CatalogProducts junction with optional price_override

## What to Build

### 1. Pydantic Schemas: `backend/app/schemas/order.py`

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator

class OrderLineItemCreate(BaseModel):
    """What the client sends per line item when placing an order."""
    product_id: UUID
    quantity: int = 1
    size: str | None = None
    decoration: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v

class OrderCreate(BaseModel):
    """What the client sends to place an order."""
    catalog_id: UUID
    line_items: list[OrderLineItemCreate]
    notes: str | None = None
    # Shipping address: if omitted, copied from employee profile
    shipping_address_line1: str | None = None
    shipping_address_line2: str | None = None
    shipping_city: str | None = None
    shipping_state: str | None = None
    shipping_zip: str | None = None
    shipping_country: str | None = None

    @field_validator("line_items")
    @classmethod
    def must_have_items(cls, v: list) -> list:
        if not v:
            raise ValueError("Order must have at least one line item")
        return v

class OrderLineItemResponse(BaseModel):
    """Line item in API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    unit_price: float
    quantity: int
    size: str | None
    decoration: str | None
    line_total: float
    created_at: datetime
    updated_at: datetime

class OrderResponse(BaseModel):
    """Order in API responses (without line items)."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    user_id: UUID
    catalog_id: UUID
    order_number: str
    status: str
    shipping_address_line1: str | None
    shipping_address_line2: str | None
    shipping_city: str | None
    shipping_state: str | None
    shipping_zip: str | None
    shipping_country: str | None
    notes: str | None
    subtotal: float
    total_amount: float
    cancelled_at: datetime | None
    cancelled_by: UUID | None
    created_at: datetime
    updated_at: datetime

class OrderWithItemsResponse(OrderResponse):
    """Order with nested line items for detail endpoints."""
    line_items: list[OrderLineItemResponse] = []
```

### 2. Order Service: `backend/app/services/order_service.py`

Follow the pattern of `backend/app/services/product_service.py` and
`backend/app/services/catalog_service.py`.

**`create_order()` method — the core logic:**

```
Input: OrderCreate data, company_id (UUID), sub_brand_id (UUID | None), cognito_sub (str)
Output: tuple[Order, list[OrderLineItem]]

Steps:
1. Resolve the employee's local user_id from cognito_sub using resolve_current_user_id()
2. Validate catalog:
   a. Fetch catalog by catalog_id where company_id matches and deleted_at IS NULL
   b. Raise NotFoundError if not found
   c. Raise ForbiddenError if catalog.status != 'active'
   d. If catalog.payment_model == 'invoice_after_close':
      - Raise ValidationError if buying_window_opens_at is in the future ("Buying window is not open yet")
      - Raise ValidationError if buying_window_closes_at is in the past ("Buying window has closed")
3. For each line item in data.line_items:
   a. Fetch the CatalogProduct entry matching (catalog_id, product_id)
      - Raise NotFoundError("Product", product_id) if not in catalog
   b. Fetch the Product — must have status='active' and deleted_at IS NULL
      - Raise ValidationError if product is not active
   c. Resolve price: catalog_product.price_override if not None, else product.unit_price
   d. If line_item.size is provided and product.sizes is not empty:
      - Raise ValidationError if size not in product.sizes
   e. If line_item.decoration is provided and product.decoration_options is not empty:
      - Raise ValidationError if decoration not in product.decoration_options
   f. Calculate line_total = unit_price * quantity
   g. Collect snapshot: product_name=product.name, product_sku=product.sku
4. Resolve shipping address:
   - If data has any shipping address fields set (line1 not None), use the request values
   - Otherwise, look up EmployeeProfile by user_id and copy delivery_address_* fields
   - If no profile exists or profile has no address, leave fields as None
5. Generate order_number:
   - Format: "ORD-{YYYYMMDD}-{4 random hex chars uppercase}" e.g. "ORD-20260408-A1B2"
   - Use secrets.token_hex(2).upper() for the random part
   - Check for uniqueness in DB; retry up to 5 times on collision
6. Calculate subtotal = sum of all line_totals
7. total_amount = subtotal (no tax/shipping in initial build)
8. Create Order record with status='pending', all computed fields
9. Create OrderLineItem records for each line item
10. flush() + refresh(order) + refresh each line item
11. Return (order, line_items)
```

**Important implementation details:**
- Import `from decimal import Decimal` — use `Decimal` for price arithmetic, not `float`
- The catalog_product.price_override is `Numeric(10,2)` which SQLAlchemy returns as `Decimal`
- `datetime.now(UTC)` for timestamp comparisons (buying window)
- Use `select(CatalogProduct).where(CatalogProduct.catalog_id == ..., CatalogProduct.product_id == ...)` to check catalog membership
- Use `select(EmployeeProfile).where(EmployeeProfile.user_id == user_id)` for address lookup
- Follow the `flush() + refresh()` pattern from ProductService for MissingGreenlet prevention

### 3. API Endpoint: `backend/app/api/v1/orders.py`

For Phase 2, implement only the create endpoint:

```python
router = APIRouter(prefix="/orders", tags=["orders"])

def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id

@router.post("/", response_model=ApiResponse[OrderWithItemsResponse], status_code=201)
async def create_order(
    data: OrderCreate,
    context: TenantContext = Depends(get_tenant_context),  # All roles can order
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderWithItemsResponse]:
    company_id = _require_company_id(context)
    service = OrderService(db)
    order, line_items = await service.create_order(
        data=data,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        cognito_sub=context.user_id,
    )
    response = OrderWithItemsResponse.model_validate(order)
    response.line_items = [OrderLineItemResponse.model_validate(li) for li in line_items]
    return ApiResponse(data=response)
```

### 4. Update `backend/app/api/v1/router.py`

Add the orders router:
```python
from app.api.v1.orders import router as orders_router
v1_router.include_router(orders_router)
```

### 5. Tests: `backend/tests/test_orders.py`

Write tests for order creation. You'll need test fixtures for:
- An active catalog with products (create in each test or in fixtures)
- Use existing company_a, company_b, and user fixtures from conftest.py
- Create user fixtures that have matching `cognito_sub` in both the User record
  and the JWT token (use `user_a1_employee` + `user_a1_employee_token` fixtures)

**Helper function for test setup** (define at top of test file):
```python
async def _create_active_catalog_with_products(
    db: AsyncSession,
    company_id: UUID,
    sub_brand_id: UUID | None,
    created_by: UUID,
    payment_model: str = "self_service",
    num_products: int = 2,
) -> tuple[Catalog, list[Product], list[CatalogProduct]]:
    """Create an active catalog with active products for testing orders."""
    # Create products (status='active')
    # Create catalog (status='active')
    # Create catalog_products junction entries
    # Return (catalog, products, catalog_products)
```

**Tests to write (Phase 2 — ~20 tests):**

Functional:
1. `test_create_order_success` — employee places order with valid catalog/products → 201
2. `test_create_order_snapshots_product_details` — response contains product_name, product_sku from product at order time
3. `test_create_order_uses_catalog_price_override` — when catalog_product has price_override, order uses that price
4. `test_create_order_uses_product_price_when_no_override` — when no price_override, uses product.unit_price
5. `test_create_order_calculates_totals` — subtotal = sum(line_totals), total_amount = subtotal
6. `test_create_order_multiple_line_items` — order with 3 different products has correct line items and totals
7. `test_create_order_copies_shipping_from_profile` — when no address in request, copies from employee profile
8. `test_create_order_uses_explicit_shipping_address` — when address provided in request, uses it (not profile)
9. `test_create_order_generates_order_number` — order_number matches pattern "ORD-YYYYMMDD-XXXX"
10. `test_create_order_status_is_pending` — new orders have status='pending'
11. `test_create_order_with_size_and_decoration` — size and decoration fields are stored

Validation errors:
12. `test_create_order_empty_line_items_returns_422` — empty list → 422
13. `test_create_order_product_not_in_catalog_returns_404` — product exists but not in this catalog
14. `test_create_order_catalog_not_active_returns_403` — draft/submitted catalog → 403
15. `test_create_order_product_not_active_returns_422` — product in catalog but status=draft
16. `test_create_order_invalid_size_returns_422` — size not in product.sizes
17. `test_create_order_invalid_decoration_returns_422` — decoration not in product.decoration_options
18. `test_create_order_buying_window_closed_returns_422` — invoice_after_close catalog with past close date
19. `test_create_order_buying_window_not_open_returns_422` — invoice_after_close catalog with future open date

Authorization:
20. `test_create_order_reel48_admin_returns_403` — reel48_admin has no company_id
21. `test_create_order_employee_can_order` — employee role can place orders (201)

Isolation:
22. `test_create_order_cross_company_catalog_returns_404` — Company B employee cannot order from Company A's catalog

**CRITICAL test patterns:**
- Always use trailing slashes on list URLs: `/api/v1/orders/`
- Use `user_a1_employee_token` (not `company_a_brand_a1_employee_token`) when the
  endpoint calls `resolve_current_user_id` — the token's cognito_sub must match a User record
- Create an EmployeeProfile for the test user when testing address copying
- For buying window tests, set dates relative to `datetime.now(UTC)`:
  - Window open: `opens_at = now - 1 day`, `closes_at = now + 1 day`
  - Window closed: `opens_at = now - 2 days`, `closes_at = now - 1 day`
  - Window not yet open: `opens_at = now + 1 day`, `closes_at = now + 2 days`

Commit message: `feat: add order placement endpoint with catalog/product validation and 22 tests (Module 4 Phase 2)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Order Retrieval (List & Get Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 4 Phase 3: list and get order endpoints with role-based visibility.

## Context

Module 4 Phases 1-2 are complete:
- `orders` and `order_line_items` tables exist with RLS
- `POST /api/v1/orders/` creates orders (with catalog/product validation, price snapshots)
- OrderService has `create_order()` method
- ~22 tests passing for order creation

## What to Build

### 1. Add Service Methods to `backend/app/services/order_service.py`

Add these methods to the existing `OrderService` class:

**`list_orders()`** — For managers/admins who see all orders in their scope:
```python
async def list_orders(
    self,
    company_id: UUID,
    sub_brand_id: UUID | None,  # None for corporate_admin (sees all sub-brands)
    page: int,
    per_page: int,
    status_filter: str | None = None,
    catalog_id_filter: UUID | None = None,
) -> tuple[list[Order], int]:
    # Build query: filter by company_id, optionally sub_brand_id
    # Optionally filter by status and catalog_id
    # Paginate and return (orders, total)
```

**`list_my_orders()`** — For employees who see only their own:
```python
async def list_my_orders(
    self,
    user_id: UUID,  # the local users.id (not cognito_sub)
    company_id: UUID,
    page: int,
    per_page: int,
    status_filter: str | None = None,
) -> tuple[list[Order], int]:
    # Same as list_orders but adds: Order.user_id == user_id
```

**`get_order()`** — Get a single order:
```python
async def get_order(
    self,
    order_id: UUID,
    company_id: UUID | None = None,  # None for platform admin
) -> Order:
    # Fetch by ID, with optional company_id filter
    # Raise NotFoundError if not found
```

**`get_order_line_items()`** — Get line items for an order:
```python
async def get_order_line_items(
    self,
    order_id: UUID,
) -> list[OrderLineItem]:
    # Select all OrderLineItem where order_id matches
    # Order by created_at
```

### 2. Add Endpoints to `backend/app/api/v1/orders.py`

Add these endpoints to the existing orders router:

**`GET /api/v1/orders/`** — List orders with role-based visibility:
```python
@router.get("/", response_model=ApiListResponse[OrderResponse])
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    catalog_id: UUID | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[OrderResponse]:
    company_id = _require_company_id(context)
    service = OrderService(db)

    if context.is_manager_or_above:
        # Managers and admins see all orders in their company/sub-brand scope
        orders, total = await service.list_orders(
            company_id, context.sub_brand_id, page, per_page,
            status_filter=status, catalog_id_filter=catalog_id,
        )
    else:
        # Employees see only their own orders
        user_id = await resolve_current_user_id(db, context.user_id)
        orders, total = await service.list_my_orders(
            user_id, company_id, page, per_page, status_filter=status,
        )

    return ApiListResponse(
        data=[OrderResponse.model_validate(o) for o in orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )
```

**`GET /api/v1/orders/my/`** — Explicit "my orders" endpoint (always returns only the authenticated user's orders regardless of role):
```python
@router.get("/my/", response_model=ApiListResponse[OrderResponse])
async def list_my_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[OrderResponse]:
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = OrderService(db)
    orders, total = await service.list_my_orders(
        user_id, company_id, page, per_page, status_filter=status,
    )
    return ApiListResponse(
        data=[OrderResponse.model_validate(o) for o in orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )
```

**IMPORTANT:** Define the `/my/` route BEFORE the `/{order_id}` route in the file,
otherwise FastAPI will try to parse "my" as a UUID and return a 422 error.

**`GET /api/v1/orders/{order_id}`** — Get order detail with line items:
```python
@router.get("/{order_id}", response_model=ApiResponse[OrderWithItemsResponse])
async def get_order(
    order_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderWithItemsResponse]:
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.get_order(order_id, company_id)

    # Employees can only see their own orders
    if not context.is_manager_or_above:
        user_id = await resolve_current_user_id(db, context.user_id)
        if order.user_id != user_id:
            raise NotFoundError("Order", str(order_id))

    line_items = await service.get_order_line_items(order_id)
    response = OrderWithItemsResponse.model_validate(order)
    response.line_items = [OrderLineItemResponse.model_validate(li) for li in line_items]
    return ApiResponse(data=response)
```

### 3. Tests: Add to `backend/tests/test_orders.py`

Add tests for the list and get endpoints. You'll need to create orders first
(either via the API or by directly inserting via the admin_db_session).

**Helper to create an order via API** (for test setup):
```python
async def _place_test_order(
    client: AsyncClient,
    token: str,
    catalog_id: UUID,
    product_id: UUID,
    quantity: int = 1,
) -> dict:
    """Place a test order and return the response JSON."""
    response = await client.post(
        "/api/v1/orders/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "catalog_id": str(catalog_id),
            "line_items": [{"product_id": str(product_id), "quantity": quantity}],
        },
    )
    assert response.status_code == 201
    return response.json()["data"]
```

**Tests to write (~14 tests):**

Functional:
1. `test_list_orders_returns_paginated_results` — list endpoint returns data + meta with total
2. `test_get_order_returns_detail_with_line_items` — get endpoint returns order + line_items array
3. `test_list_orders_filter_by_status` — ?status=pending returns only pending orders
4. `test_list_orders_filter_by_catalog_id` — ?catalog_id=... returns only that catalog's orders
5. `test_list_my_orders_returns_only_own_orders` — /my/ endpoint scoped to authenticated user

Role-based visibility:
6. `test_list_orders_employee_sees_only_own` — employee sees only orders they placed
7. `test_get_order_employee_can_see_own` — employee can get their own order detail
8. `test_get_order_employee_cannot_see_others` — employee gets 404 for another employee's order
9. `test_list_orders_manager_sees_sub_brand` — regional_manager sees all orders in their sub-brand
10. `test_list_orders_sub_brand_admin_sees_sub_brand` — sub_brand_admin sees all sub-brand orders
11. `test_list_orders_corporate_admin_sees_all_sub_brands` — corporate_admin sees all orders across sub-brands

Isolation:
12. `test_list_orders_company_b_cannot_see_company_a` — cross-company isolation
13. `test_list_orders_brand_a2_cannot_see_brand_a1` — cross-sub-brand isolation within same company
14. `test_get_order_company_b_returns_404` — Company B gets 404 for Company A's order

**Test fixture considerations:**
- For role-based tests, you need a `regional_manager` user + token. Use the existing
  `company_a_brand_a1_manager_token` fixture, but you'll also need a User record with
  matching cognito_sub for it (create a `user_a1_manager` fixture if one doesn't exist)
- For the "employee sees only own" test: create two different employee users in the
  same sub-brand, place orders as each, verify each only sees their own

Commit message: `feat: add order list/get endpoints with role-based visibility and 14 tests (Module 4 Phase 3)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: Order Status Transitions (Cancel, Approve, Process, Ship, Deliver)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 4 Phase 4: order status transition endpoints with authorization.

## Context

Module 4 Phases 1-3 are complete:
- Orders + line items tables with RLS
- `POST /api/v1/orders/` — create order
- `GET /api/v1/orders/` — list orders (role-scoped)
- `GET /api/v1/orders/my/` — list my orders
- `GET /api/v1/orders/{order_id}` — get order detail with line items
- ~36 tests passing

## What to Build

### 1. Add Service Methods to `backend/app/services/order_service.py`

**Status transition rules:**
```
pending   → approved      (manager_or_above only)
pending   → cancelled     (order owner OR manager_or_above)
approved  → processing    (manager_or_above only)
approved  → cancelled     (manager_or_above only — employee CANNOT cancel after approval)
processing → shipped      (manager_or_above only)
shipped   → delivered     (manager_or_above only)
```

Any other transition (e.g., shipped → pending, cancelled → anything) is INVALID → raise ForbiddenError.

**Methods to add:**

```python
async def cancel_order(
    self,
    order_id: UUID,
    company_id: UUID,
    cancelled_by_user_id: UUID,  # local users.id
    is_manager_or_above: bool,
) -> Order:
    order = await self.get_order(order_id, company_id)

    if order.status == "pending":
        # Both owner and manager can cancel pending orders
        if not is_manager_or_above and order.user_id != cancelled_by_user_id:
            raise NotFoundError("Order", str(order_id))  # 404 not 403 (don't reveal existence)
    elif order.status == "approved":
        # Only manager can cancel approved orders
        if not is_manager_or_above:
            raise ForbiddenError("Only managers can cancel approved orders")
    else:
        raise ForbiddenError(f"Cannot cancel an order with status '{order.status}'")

    order.status = "cancelled"
    order.cancelled_at = datetime.now(UTC)
    order.cancelled_by = cancelled_by_user_id
    await self.db.flush()
    await self.db.refresh(order)
    return order

async def approve_order(
    self, order_id: UUID, company_id: UUID
) -> Order:
    order = await self.get_order(order_id, company_id)
    if order.status != "pending":
        raise ForbiddenError("Only pending orders can be approved")
    order.status = "approved"
    await self.db.flush()
    await self.db.refresh(order)
    return order

async def process_order(
    self, order_id: UUID, company_id: UUID
) -> Order:
    order = await self.get_order(order_id, company_id)
    if order.status != "approved":
        raise ForbiddenError("Only approved orders can be marked as processing")
    order.status = "processing"
    await self.db.flush()
    await self.db.refresh(order)
    return order

async def ship_order(
    self, order_id: UUID, company_id: UUID
) -> Order:
    order = await self.get_order(order_id, company_id)
    if order.status != "processing":
        raise ForbiddenError("Only processing orders can be shipped")
    order.status = "shipped"
    await self.db.flush()
    await self.db.refresh(order)
    return order

async def deliver_order(
    self, order_id: UUID, company_id: UUID
) -> Order:
    order = await self.get_order(order_id, company_id)
    if order.status != "shipped":
        raise ForbiddenError("Only shipped orders can be delivered")
    order.status = "delivered"
    await self.db.flush()
    await self.db.refresh(order)
    return order
```

### 2. Add Endpoints to `backend/app/api/v1/orders.py`

All status transition endpoints use POST and return the updated order.

```python
@router.post("/{order_id}/cancel", response_model=ApiResponse[OrderResponse])
async def cancel_order(
    order_id: UUID,
    context: TenantContext = Depends(get_tenant_context),  # Any role can attempt
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    """Cancel a pending order. Employees can cancel their own; managers can cancel any."""
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = OrderService(db)
    order = await service.cancel_order(
        order_id, company_id, user_id, context.is_manager_or_above,
    )
    return ApiResponse(data=OrderResponse.model_validate(order))

@router.post("/{order_id}/approve", response_model=ApiResponse[OrderResponse])
async def approve_order(
    order_id: UUID,
    context: TenantContext = Depends(require_manager),  # manager_or_above
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.approve_order(order_id, company_id)
    return ApiResponse(data=OrderResponse.model_validate(order))

@router.post("/{order_id}/process", response_model=ApiResponse[OrderResponse])
async def process_order(
    order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.process_order(order_id, company_id)
    return ApiResponse(data=OrderResponse.model_validate(order))

@router.post("/{order_id}/ship", response_model=ApiResponse[OrderResponse])
async def ship_order(
    order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.ship_order(order_id, company_id)
    return ApiResponse(data=OrderResponse.model_validate(order))

@router.post("/{order_id}/deliver", response_model=ApiResponse[OrderResponse])
async def deliver_order(
    order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.deliver_order(order_id, company_id)
    return ApiResponse(data=OrderResponse.model_validate(order))
```

### 3. Tests: Add to `backend/tests/test_orders.py`

**Tests to write (~12 tests):**

Functional:
1. `test_cancel_pending_order_as_employee` — employee cancels own pending order → 200, status=cancelled
2. `test_cancel_sets_cancelled_at_and_cancelled_by` — verify cancelled_at and cancelled_by are set
3. `test_approve_pending_order_as_manager` — manager approves pending → 200, status=approved
4. `test_full_lifecycle_pending_to_delivered` — pending → approved → processing → shipped → delivered (manager drives all transitions)

Authorization:
5. `test_employee_cannot_cancel_others_order` — employee tries to cancel another employee's order → 404
6. `test_employee_cannot_cancel_approved_order` — employee's own order, but already approved → 403
7. `test_employee_cannot_approve_order` — employee calls /approve → 403
8. `test_employee_cannot_process_ship_deliver` — employee calls /process, /ship, /deliver → 403
9. `test_manager_can_cancel_approved_order` — manager cancels an approved order → 200

Invalid transitions:
10. `test_cannot_approve_already_approved_order` — approved → approved → 403
11. `test_cannot_ship_pending_order` — must be processing first → 403
12. `test_cannot_transition_cancelled_order` — cancelled → any transition → 403

**Token/user fixture notes:**
- For manager tests, you need a User record + token with `role=regional_manager` for the same
  company/sub-brand. If `user_a1_manager` + `user_a1_manager_token` fixtures don't exist in
  conftest.py, create them following the pattern of `user_a1_admin` + `user_a1_admin_token`
- For the "employee cannot cancel other's order" test: create a second employee user in
  the same sub-brand, place an order as user 1, try to cancel as user 2

Commit message: `feat: add order status transitions (cancel/approve/process/ship/deliver) with 12 tests (Module 4 Phase 4)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: Platform Admin Order Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 4 Phase 5: cross-company order visibility for reel48_admin.

## Context

Module 4 Phases 1-4 are complete:
- Full order lifecycle: create, list, get, cancel, approve, process, ship, deliver
- Role-based visibility: employees see own, managers/admins see sub-brand scope
- ~48 tests passing

The platform admin endpoint pattern is established in:
- `backend/app/api/v1/platform/products.py` — cross-company product list + approval actions
- `backend/app/api/v1/platform/catalogs.py` — cross-company catalog list + approval actions

## What to Build

### 1. Add Service Method to `backend/app/services/order_service.py`

```python
async def list_all_orders(
    self,
    page: int,
    per_page: int,
    status_filter: str | None = None,
    company_id_filter: UUID | None = None,
    catalog_id_filter: UUID | None = None,
) -> tuple[list[Order], int]:
    """List orders across ALL companies. For reel48_admin platform endpoints."""
    query = select(Order)
    if status_filter is not None:
        query = query.where(Order.status == status_filter)
    if company_id_filter is not None:
        query = query.where(Order.company_id == company_id_filter)
    if catalog_id_filter is not None:
        query = query.where(Order.catalog_id == catalog_id_filter)

    total = await self.db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await self.db.execute(query)
    return list(result.scalars().all()), total or 0
```

### 2. Create `backend/app/api/v1/platform/orders.py`

Follow the exact pattern of `backend/app/api/v1/platform/products.py`:

```python
"""Platform admin endpoints for cross-company order visibility.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.order import OrderResponse, OrderWithItemsResponse, OrderLineItemResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/platform/orders", tags=["platform-orders"])

@router.get("/", response_model=ApiListResponse[OrderResponse])
async def list_all_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    company_id: UUID | None = Query(None),
    catalog_id: UUID | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[OrderResponse]:
    """List ALL orders across all companies."""
    service = OrderService(db)
    orders, total = await service.list_all_orders(
        page, per_page,
        status_filter=status,
        company_id_filter=company_id,
        catalog_id_filter=catalog_id,
    )
    return ApiListResponse(
        data=[OrderResponse.model_validate(o) for o in orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )

@router.get("/{order_id}", response_model=ApiResponse[OrderWithItemsResponse])
async def get_order(
    order_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderWithItemsResponse]:
    """Get any order detail with line items (cross-company)."""
    service = OrderService(db)
    order = await service.get_order(order_id)  # No company_id filter
    line_items = await service.get_order_line_items(order_id)
    response = OrderWithItemsResponse.model_validate(order)
    response.line_items = [OrderLineItemResponse.model_validate(li) for li in line_items]
    return ApiResponse(data=response)
```

### 3. Update `backend/app/api/v1/router.py`

Add the platform orders router:
```python
from app.api.v1.platform.orders import router as platform_orders_router
v1_router.include_router(platform_orders_router)
```

### 4. Tests: `backend/tests/test_platform_orders.py`

Create a new test file (following the pattern of `backend/tests/test_platform_catalog.py`).

**Tests to write (~6 tests):**

1. `test_platform_list_orders_returns_all_companies` — reel48_admin sees orders from both Company A and Company B
2. `test_platform_list_orders_filter_by_company` — ?company_id=... returns only that company's orders
3. `test_platform_list_orders_filter_by_status` — ?status=pending returns only pending orders
4. `test_platform_get_order_detail` — reel48_admin can get any order with line items
5. `test_platform_orders_requires_reel48_admin` — corporate_admin gets 403 on platform endpoints
6. `test_platform_orders_employee_gets_403` — employee gets 403 on platform endpoints

**Fixture notes:**
- Use `reel48_admin_user_token` (not `reel48_admin_token`) — the platform list endpoint
  doesn't need `resolve_current_user_id`, but using the user token is consistent
- Actually, `reel48_admin_token` is fine here since these endpoints only call
  `require_reel48_admin` and don't resolve user IDs. Use whichever is simpler.
- Create orders in Company A and Company B by using each company's employee user + token
  to call `POST /api/v1/orders/`

Commit message: `feat: add platform admin order endpoints for cross-company visibility with 6 tests (Module 4 Phase 5)`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: End-of-Module Harness Maintenance
# ═══════════════════════════════════════════════════════════════════════════════

Perform the end-of-module harness review for Module 4 (Ordering Flow).

## Context

Module 4 is complete. All phases (1-5) are built and tested:
- Phase 1: orders + order_line_items tables with RLS
- Phase 2: Order placement with catalog/product validation, price snapshots
- Phase 3: List/get with role-based visibility
- Phase 4: Status transitions (cancel, approve, process, ship, deliver)
- Phase 5: Platform admin cross-company endpoints

Total new tests: ~54. Run the full test suite first to confirm everything passes.

## What to Do

### Step 1: Run Full Test Suite

```bash
cd backend && python -m pytest tests/ -x -v
```

Record the total test count. All tests (existing + new) must pass.

### Step 2: Update `backend/CLAUDE.md`

Add the following sections (follow the existing pattern — see Module 2 and Module 3
table schemas already documented there):

**Add Module 4 Table Schemas section:**
- `orders` table schema (all columns, constraints, indexes)
- `order_line_items` table schema (all columns, constraints, indexes)
- RLS policies for both tables

**Add Order Status Lifecycle & Transitions section:**
```
pending → approved → processing → shipped → delivered
pending → cancelled (employee own + manager)
approved → cancelled (manager only)
```
Document who can perform each transition and the authorization rules.

**Add Order Placement Patterns section:**
- Price snapshotting: catalog_product.price_override → product.unit_price fallback
- Shipping address resolution: explicit request > employee profile > null
- Order number format: "ORD-YYYYMMDD-XXXX"
- Catalog validation: must be active, buying window enforcement for invoice_after_close

**Add to the "Which Base to Use" table:**
```
| `orders` | `TenantBase` | Scoped to company + sub-brand |
| `order_line_items` | `TenantBase` | Scoped to company + sub-brand |
```

### Step 3: End-of-Session Self-Audit

Answer the 5-question checklist from `CLAUDE.md`:

1. **New pattern introduced?** — Order number generation, price snapshotting at order time,
   shipping address resolution from profile, status transition enforcement, role-based
   list visibility (employees see own vs managers see all)
2. **Existing pattern violated?** — Check if any patterns from the harness were deviated from
3. **New decision made?** — Document any non-obvious choices (e.g., no soft delete on orders,
   cancelled as a status not a deletion)
4. **Missing guidance discovered?** — Note any scenarios where you had to make judgment calls
5. **Prompt template needed?** — If the ordering pattern will recur (it will for bulk orders
   in Module 5)

### Step 4: Update `docs/harness-changelog.md`

Append a new entry at the TOP of the file (newest first), following the existing format:

```markdown
## 2026-04-XX — Module 4 Completion (Ordering Flow)

**Type:** End-of-module self-audit + harness review
**Module:** Module 4 — Ordering Flow (Phases 1-5)

### Self-Audit Checklist
- [x/blank] **New pattern?** → {what was added}
- [x/blank] **Pattern violated?** → {what was different}
- [x/blank] **New decision?** → {any ADRs needed}
- [x/blank] **Missing guidance?** → {gaps found}
- [x/blank] **Reusable task?** → {prompt templates created}
- [x] **Changelog updated?** → This entry

### Harness Files Updated
- **`backend/CLAUDE.md`** — {list sections added/updated}
- **Other files** — {if any}

### Session Metrics
- **Tests written:** {count}
- **Total test suite:** {count} passed, 0 failed
- **Mistakes caught by harness:** {count}
- **Gaps found:** {count}
```

### Step 5: Verify No Missing Grants

Double-check that `conftest.py` `setup_database` fixture has grants for ALL tables:
```python
tables = [
    "companies", "sub_brands", "users", "invites",
    "org_codes", "employee_profiles",
    "products", "catalogs", "catalog_products",
    "orders", "order_line_items",  # ← Module 4
]
```

### Step 6: Consider a Prompt Template for Ordering Patterns

Module 5 (Bulk Ordering) will follow a similar pattern: create order → validate catalog →
snapshot prices → status lifecycle. Consider creating `prompts/ordering-pattern.md` if
the pattern is reusable. This is optional — only create it if it will save significant
time in Module 5.

Commit message: `chore: Module 4 harness review — add order schemas, lifecycle docs, and changelog entry`
