# Module 8: Analytics Dashboard — Phase-by-Phase Implementation Prompts
#
# Each phase below is a self-contained prompt designed to be pasted into a
# fresh Claude Code session. The session will read the CLAUDE.md harness files
# automatically — these prompts provide MODULE-SPECIFIC context that the
# harness doesn't cover.
#
# IMPORTANT: Run phases in order. Each phase depends on the prior phase's output.
#
# MODULE 8 OVERVIEW:
# The Analytics Dashboard gives stakeholders at every level actionable visibility
# into apparel program performance. Unlike Modules 1-7 which focused on
# transactional workflows (creating orders, managing catalogs, processing
# invoices), Module 8 is READ-ONLY — it queries existing data across Modules
# 3-7 and surfaces aggregated metrics, trends, and breakdowns.
#
# Analytics is scoped by the same tenant isolation model as everything else:
# - `reel48_admin` sees platform-wide metrics across ALL companies
# - `corporate_admin` sees aggregate metrics across all sub-brands in their company
# - `sub_brand_admin` sees metrics for their sub-brand only
# - `regional_manager` sees metrics for their sub-brand only
# - `employee` has NO access to analytics endpoints
#
# Key architectural points:
# - NO new database tables or migrations. Module 8 queries existing tables only.
# - RLS automatically scopes all queries to the user's tenant context.
# - Aggregation queries use SQLAlchemy `func` (SUM, COUNT, AVG, etc.) —
#   not raw SQL except where SQLAlchemy cannot express the query.
# - Date range filtering is standard on all analytics endpoints.
# - Platform admin analytics live under `/api/v1/platform/analytics/`.
# - Client analytics live under `/api/v1/analytics/`.
# - Frontend uses IBM Carbon DataTable for tabular breakdowns and a lightweight
#   charting library for visualizations.
#
# What ALREADY EXISTS (do not rebuild):
# - Orders (Module 4): orders + order_line_items tables with status, totals, sizes
# - Bulk Orders (Module 5): bulk_orders + bulk_order_items with status, totals
# - Catalogs (Module 3): catalogs + catalog_products + products with pricing
# - Invoices (Module 7): invoices with billing_flow, status, total_amount, paid_at
# - Employee Profiles (Module 2): employee_profiles with sizing, department, location
# - Users (Module 1): users with role, company_id, sub_brand_id
# - Approval Requests (Module 6): approval_requests with entity_type, status, timing
# - All tenant isolation infrastructure (RLS, TenantContext, auth middleware)
# - Frontend shell: Sidebar, Header, MainLayout, ProtectedRoute, auth context
# - IBM Carbon design system with Reel48+ theme (teal interactive, charcoal brand)
#
# What Module 8 BUILDS:
# - AnalyticsService (aggregation queries across orders, invoices, products)
# - Client analytics endpoints (tenant-scoped, role-gated)
# - Platform analytics endpoints (cross-company, reel48_admin only)
# - Frontend analytics dashboard page with role-aware content
# - Frontend platform analytics page with cross-company overview
# - Comprehensive tests (functional, isolation, authorization)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Analytics Service — Core Aggregation Queries
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 8 Phase 1: the AnalyticsService with core aggregation methods that
query across existing tables. No new migrations. No new API endpoints yet — just
the service layer and its unit tests.

## Context

We are building Module 8 (Analytics Dashboard) of the Reel48+ enterprise apparel
platform. Modules 1-7 are complete:
- Module 1: Auth, Companies, Sub-Brands, Users (migration `001`)
- Module 2: Employee Profiles (migration `002`)
- Module 3: Products, Catalogs, Catalog-Products (migration `003`)
- Module 4: Orders, Order Line Items (migration `004`)
- Module 5: Bulk Orders, Bulk Order Items (migration `005`)
- Module 6: Approval Requests, Approval Rules (migration `006`)
- Module 7: Invoices (migration `007`)

The current test suite has 442 passing tests. The branch is `main`.
Create a new branch `feature/module8-phase1-analytics-service` from `main`
before starting.

## What to Build

### 1. Analytics Service: `backend/app/services/analytics_service.py`

Create an `AnalyticsService` class following the same pattern as other services
(takes `db: AsyncSession` in constructor). All methods accept date range parameters
(`start_date: date | None`, `end_date: date | None`) to allow time-bounded queries.

**CRITICAL: No new tables.** All queries use existing models: `Order`, `OrderLineItem`,
`BulkOrder`, `BulkOrderItem`, `Invoice`, `Product`, `Catalog`, `User`,
`EmployeeProfile`, `ApprovalRequest`.

**CRITICAL: RLS handles tenant scoping.** The service does NOT manually filter by
`company_id` or `sub_brand_id` in queries — RLS policies on every table already
enforce this based on the PostgreSQL session variables set by `get_tenant_context`.
However, for defense-in-depth, include `company_id` filters in queries where
practical (per the api-endpoints rule).

Implement these methods:

#### Spend Analytics
```python
async def get_spend_summary(
    self, start_date: date | None = None, end_date: date | None = None
) -> dict:
    """
    Returns total spend, order count, average order value, and period-over-period
    change. Queries the `orders` table (individual) and `bulk_orders` table.
    Only counts orders with status in ('approved', 'processing', 'shipped', 'delivered').
    Returns:
    {
        "total_spend": Decimal,
        "order_count": int,
        "average_order_value": Decimal,
        "individual_order_spend": Decimal,
        "bulk_order_spend": Decimal,
    }
    """
```

```python
async def get_spend_by_sub_brand(
    self, start_date: date | None = None, end_date: date | None = None
) -> list[dict]:
    """
    Spend broken down by sub-brand. Useful for corporate_admin and reel48_admin.
    Joins orders → sub_brands to get sub-brand name.
    Returns: [{"sub_brand_id": UUID, "sub_brand_name": str, "total_spend": Decimal, "order_count": int}, ...]
    """
```

```python
async def get_spend_over_time(
    self,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = "month",  # "day", "week", "month"
) -> list[dict]:
    """
    Spend aggregated into time buckets for trend charting.
    Uses date_trunc() on orders.created_at.
    Returns: [{"period": str, "total_spend": Decimal, "order_count": int}, ...]
    """
```

#### Order Analytics
```python
async def get_order_status_breakdown(
    self, start_date: date | None = None, end_date: date | None = None
) -> list[dict]:
    """
    Count of orders by status (pending, approved, processing, shipped, etc.).
    Includes both individual orders and bulk orders as separate categories.
    Returns: [{"status": str, "count": int, "order_type": "individual"|"bulk"}, ...]
    """
```

```python
async def get_top_products(
    self,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Most ordered products by quantity across individual and bulk orders.
    Queries order_line_items and bulk_order_items, groups by product_id.
    Returns: [{"product_id": UUID, "product_name": str, "product_sku": str,
               "total_quantity": int, "total_revenue": Decimal}, ...]
    """
```

#### Size Distribution Analytics
```python
async def get_size_distribution(
    self, start_date: date | None = None, end_date: date | None = None
) -> list[dict]:
    """
    Distribution of ordered sizes across all line items.
    Queries order_line_items.size and bulk_order_items.size.
    Returns: [{"size": str, "count": int, "percentage": float}, ...]
    """
```

#### Invoice Analytics
```python
async def get_invoice_summary(
    self, start_date: date | None = None, end_date: date | None = None
) -> dict:
    """
    Invoice totals by status and billing flow.
    Returns:
    {
        "total_invoiced": Decimal,
        "total_paid": Decimal,
        "total_outstanding": Decimal,  # finalized + sent but not paid
        "invoice_count": int,
        "by_status": [{"status": str, "count": int, "total": Decimal}, ...],
        "by_billing_flow": [{"billing_flow": str, "count": int, "total": Decimal}, ...],
    }
    """
```

#### Approval Analytics
```python
async def get_approval_metrics(
    self, start_date: date | None = None, end_date: date | None = None
) -> dict:
    """
    Approval request metrics: pending count, average approval time, approval rate.
    Returns:
    {
        "pending_count": int,
        "approved_count": int,
        "rejected_count": int,
        "approval_rate": float,  # approved / (approved + rejected)
        "avg_approval_time_hours": float | None,  # decided_at - requested_at average
    }
    """
```

#### Platform-Level Analytics (reel48_admin only)
```python
async def get_platform_overview(self) -> dict:
    """
    Cross-company platform metrics. Called when RLS session vars are set to empty
    string (reel48_admin context), so all companies are visible.
    Returns:
    {
        "total_companies": int,
        "total_sub_brands": int,
        "total_users": int,
        "total_orders": int,
        "total_revenue": Decimal,  # sum of all paid invoices
        "active_catalogs": int,  # catalogs with status 'active'
    }
    """
```

```python
async def get_revenue_by_company(
    self, start_date: date | None = None, end_date: date | None = None
) -> list[dict]:
    """
    Revenue breakdown by company (from paid invoices).
    Returns: [{"company_id": UUID, "company_name": str, "total_revenue": Decimal,
               "invoice_count": int}, ...]
    """
```

### 2. Date range helper

Add a private helper method to the service that builds the date range WHERE clause:

```python
def _apply_date_range(
    self,
    query,
    date_column,
    start_date: date | None,
    end_date: date | None,
):
    """Applies optional date range filtering to a SQLAlchemy query."""
    if start_date:
        query = query.where(date_column >= start_date)
    if end_date:
        query = query.where(date_column <= end_date)
    return query
```

### 3. Pydantic schemas: `backend/app/schemas/analytics.py`

Create response schemas for the analytics endpoints. These do NOT need request
schemas (analytics is read-only — query params handle filtering).

- **`SpendSummaryResponse`** — Matches `get_spend_summary()` return shape
- **`SubBrandSpendResponse`** — Single item in the sub-brand spend breakdown
- **`SpendOverTimeResponse`** — Single time-bucket entry
- **`OrderStatusBreakdownResponse`** — Single status group entry
- **`TopProductResponse`** — Single product ranking entry
- **`SizeDistributionResponse`** — Single size entry
- **`InvoiceSummaryResponse`** — Matches `get_invoice_summary()` return shape
- **`ApprovalMetricsResponse`** — Matches `get_approval_metrics()` return shape
- **`PlatformOverviewResponse`** — Matches `get_platform_overview()` return shape
- **`CompanyRevenueResponse`** — Single company revenue entry

All Decimal fields should use `float` in the Pydantic schema (JSON doesn't support
Decimal natively). Use `ConfigDict(from_attributes=True)` where applicable.

### 4. Tests: `backend/tests/test_analytics.py`

Write tests for the AnalyticsService. Since this service only reads data, tests
focus on:

**Test setup:** Create test data across Company A (Brand A1, A2) and Company B
(Brand B1) with orders, invoices, and bulk orders in various statuses.

**Functional tests:**
- `test_spend_summary_calculates_totals` — Verify correct aggregation of order amounts
- `test_spend_summary_excludes_cancelled_orders` — Cancelled/pending orders excluded from spend
- `test_spend_summary_with_date_range` — Date filtering works correctly
- `test_spend_by_sub_brand_groups_correctly` — Breakdowns match per-brand totals
- `test_spend_over_time_monthly_buckets` — Time series returns correct period labels
- `test_top_products_ranked_by_quantity` — Most ordered products appear first
- `test_size_distribution_includes_bulk_and_individual` — Both order types counted
- `test_invoice_summary_totals` — Invoice amounts by status sum correctly
- `test_invoice_summary_outstanding_calculation` — Outstanding = finalized + sent (not paid/voided)
- `test_approval_metrics_approval_rate` — Rate calculation is correct
- `test_approval_metrics_avg_time` — Average time calculation handles NULL decided_at
- `test_platform_overview_counts` — All entity counts correct (reel48_admin context)
- `test_revenue_by_company_correct` — Revenue attributed to correct companies

**Isolation tests (CRITICAL):**
- `test_spend_summary_company_isolation` — Company A's analytics do NOT include Company B's orders
- `test_spend_by_sub_brand_isolation` — Sub-brand admin sees only their brand's data
- `test_invoice_summary_company_isolation` — Company B's invoices not visible to Company A
- `test_platform_overview_sees_all_companies` — reel48_admin context returns all data

**Important:** Isolation tests use the non-superuser `db_session` fixture with manual
`SET LOCAL` session variables (see testing.md rule for the pattern). Functional tests
can use the `admin_db_session` or call the service directly.

## Verification

Before committing:
1. Run `cd backend && python -m pytest tests/test_analytics.py -v` — all tests pass
2. Run `cd backend && python -m pytest` — full suite still passes (442 + new tests)
3. No new migration files created (Module 8 has no schema changes)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Client Analytics API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 8 Phase 2: tenant-scoped analytics API endpoints for client company
users (corporate_admin, sub_brand_admin, regional_manager). Employees do NOT
have access to analytics.

## Context

We are building Module 8 (Analytics Dashboard). Phase 1 is complete:
- AnalyticsService with all aggregation methods
- Pydantic response schemas for analytics data
- Tests verifying aggregation logic and tenant isolation

The branch is `main`. Create a new branch `feature/module8-phase2-client-analytics-api`
from `main` before starting.

## What to Build

### 1. Client analytics routes: `backend/app/api/v1/analytics.py`

Create the analytics router with the following endpoints. ALL endpoints:
- Require authentication via `get_tenant_context`
- Require `regional_manager` role or above (employees excluded)
- Accept optional query params: `start_date` (date), `end_date` (date)
- Return the standard `ApiResponse[T]` wrapper
- RLS automatically scopes data to the user's company/sub-brand

```
GET /api/v1/analytics/spend/summary
    → Returns SpendSummaryResponse
    → Accessible to: regional_manager, sub_brand_admin, corporate_admin

GET /api/v1/analytics/spend/by-sub-brand
    → Returns list[SubBrandSpendResponse]
    → Accessible to: corporate_admin only (needs cross-brand view)
    → sub_brand_admin and regional_manager get 403

GET /api/v1/analytics/spend/over-time
    → Returns list[SpendOverTimeResponse]
    → Accepts additional query param: granularity (day|week|month, default=month)
    → Accessible to: regional_manager, sub_brand_admin, corporate_admin

GET /api/v1/analytics/orders/status-breakdown
    → Returns list[OrderStatusBreakdownResponse]
    → Accessible to: regional_manager, sub_brand_admin, corporate_admin

GET /api/v1/analytics/orders/top-products
    → Returns list[TopProductResponse]
    → Accepts additional query param: limit (int, default=10, max=50)
    → Accessible to: regional_manager, sub_brand_admin, corporate_admin

GET /api/v1/analytics/orders/size-distribution
    → Returns list[SizeDistributionResponse]
    → Accessible to: regional_manager, sub_brand_admin, corporate_admin

GET /api/v1/analytics/invoices/summary
    → Returns InvoiceSummaryResponse
    → Accessible to: corporate_admin only (invoices are company-level)
    → sub_brand_admin can see if their sub_brand_id matches (per CLAUDE.md access matrix)

GET /api/v1/analytics/approvals/metrics
    → Returns ApprovalMetricsResponse
    → Accessible to: regional_manager, sub_brand_admin, corporate_admin
```

### 2. Role check helpers

Use explicit role checks consistent with the auth rule's access matrix:

```python
def require_manager_or_above(context: TenantContext):
    """regional_manager, sub_brand_admin, corporate_admin, reel48_admin"""
    if context.role == "employee":
        raise HTTPException(status_code=403, detail="Analytics access requires manager role or above")

def require_corporate_admin_or_above(context: TenantContext):
    """corporate_admin, reel48_admin"""
    if context.role not in ("corporate_admin", "reel48_admin"):
        raise HTTPException(status_code=403, detail="This analytics view requires corporate admin access")
```

### 3. Register the router

Add the analytics router to `backend/app/api/v1/router.py`.

### 4. Tests: add to `backend/tests/test_analytics.py`

Add API-level tests (using the `client` fixture) to the existing analytics test file.

**Functional tests:**
- `test_spend_summary_endpoint_returns_200` — Valid request with corporate_admin token
- `test_spend_over_time_with_granularity_param` — `?granularity=week` works
- `test_top_products_with_limit_param` — `?limit=5` returns at most 5 items
- `test_date_range_filtering_via_query_params` — `?start_date=2026-01-01&end_date=2026-03-31`
- `test_invoice_summary_endpoint` — Returns correct structure

**Authorization tests (CRITICAL):**
- `test_employee_gets_403_on_all_analytics` — Employee token → 403 on every endpoint
- `test_unauthenticated_gets_401` — No token → 401
- `test_sub_brand_admin_cannot_see_spend_by_sub_brand` — 403 (corporate_admin only)
- `test_sub_brand_admin_cannot_see_invoice_summary` — 403 (or scoped to their brand)
- `test_regional_manager_can_see_spend_summary` — 200
- `test_corporate_admin_can_see_all_endpoints` — 200 on every endpoint

**Isolation tests:**
- `test_company_b_admin_sees_zero_for_company_a_orders` — Company B analytics exclude A's data
- `test_sub_brand_a1_admin_sees_only_a1_data` — Brand-scoped analytics

## Verification

Before committing:
1. Run `cd backend && python -m pytest tests/test_analytics.py -v` — all tests pass
2. Run `cd backend && python -m pytest` — full suite still passes
3. Verify endpoints appear in the OpenAPI docs (run the app and check `/docs`)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Platform Analytics API Endpoints (reel48_admin)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 8 Phase 3: cross-company analytics endpoints for the Reel48 platform
admin. These endpoints live under `/api/v1/platform/analytics/` and are restricted
to the `reel48_admin` role.

## Context

We are building Module 8 (Analytics Dashboard). Phases 1-2 are complete:
- AnalyticsService with all aggregation methods (Phase 1)
- Client analytics endpoints at `/api/v1/analytics/` (Phase 2)

The branch is `main`. Create a new branch `feature/module8-phase3-platform-analytics-api`
from `main` before starting.

## What to Build

### 1. Platform analytics routes: `backend/app/api/v1/platform/analytics.py`

Follow the same pattern as other platform endpoints (e.g., `platform/invoices.py`).
Use `require_reel48_admin` for access control.

```
GET /api/v1/platform/analytics/overview
    → Returns PlatformOverviewResponse
    → Cross-company totals: companies, sub-brands, users, orders, revenue, active catalogs

GET /api/v1/platform/analytics/revenue/by-company
    → Returns list[CompanyRevenueResponse]
    → Accepts optional: start_date, end_date
    → Revenue from paid invoices grouped by company

GET /api/v1/platform/analytics/revenue/over-time
    → Returns list[SpendOverTimeResponse] (same schema, different data scope)
    → Accepts optional: start_date, end_date, granularity
    → Platform-wide revenue trend

GET /api/v1/platform/analytics/orders/status-breakdown
    → Returns list[OrderStatusBreakdownResponse]
    → Cross-company order status counts

GET /api/v1/platform/analytics/orders/top-products
    → Returns list[TopProductResponse]
    → Cross-company top products by quantity

GET /api/v1/platform/analytics/invoices/summary
    → Returns InvoiceSummaryResponse
    → Cross-company invoice totals by status and billing flow

GET /api/v1/platform/analytics/approvals/metrics
    → Returns ApprovalMetricsResponse
    → Cross-company approval metrics
```

### 2. Register the router

Add the platform analytics router to `backend/app/api/v1/router.py`.

### 3. Tests: add to `backend/tests/test_analytics.py`

**Functional tests:**
- `test_platform_overview_returns_correct_counts` — All entity counts match seeded data
- `test_platform_revenue_by_company_lists_all_companies` — Both Company A and B appear
- `test_platform_revenue_over_time` — Time series includes all companies' invoices
- `test_platform_order_breakdown_cross_company` — Counts span all companies
- `test_platform_top_products_cross_company` — Products from all companies ranked together
- `test_platform_invoice_summary_cross_company` — All invoices included

**Authorization tests (CRITICAL):**
- `test_corporate_admin_gets_403_on_platform_analytics` — Only reel48_admin can access
- `test_sub_brand_admin_gets_403_on_platform_analytics`
- `test_employee_gets_403_on_platform_analytics`
- `test_reel48_admin_gets_200_on_all_platform_endpoints`

## Verification

Before committing:
1. Run `cd backend && python -m pytest tests/test_analytics.py -v` — all tests pass
2. Run `cd backend && python -m pytest` — full suite still passes


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: Frontend — Client Analytics Dashboard Page
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 8 Phase 4: the client-facing analytics dashboard page using IBM
Carbon components, with role-aware content rendering.

## Context

We are building Module 8 (Analytics Dashboard). Phases 1-3 (backend) are complete:
- AnalyticsService with aggregation queries
- Client analytics endpoints at `/api/v1/analytics/`
- Platform analytics endpoints at `/api/v1/platform/analytics/`

The branch is `main`. Create a new branch `feature/module8-phase4-client-analytics-ui`
from `main` before starting.

## What to Build

### 1. Analytics page: `frontend/src/app/(authenticated)/admin/analytics/page.tsx`

This page already has a route slot per the frontend CLAUDE.md routing structure.
Build the analytics dashboard page.

**Page structure:**
- Page header with "Analytics" title and date range picker
- Carbon `DatePicker` with `DatePickerInput` for start/end date selection
- Default date range: last 30 days
- Content sections vary by role (see below)

**Role-based content:**

For `corporate_admin`:
- **Spend Summary** — KPI cards (total spend, order count, avg order value)
  using Carbon `Tile` components in a Tailwind grid layout
- **Spend by Sub-Brand** — Carbon `DataTable` with sub-brand name, spend, order count
- **Spend Over Time** — Line chart (see charting note below)
- **Top Products** — Carbon `DataTable` with product name, SKU, quantity, revenue
- **Order Status Breakdown** — Carbon `DataTable` or inline stats
- **Invoice Summary** — KPI cards for invoiced/paid/outstanding totals
- **Approval Metrics** — KPI cards for pending/approved/rejected counts + approval rate

For `sub_brand_admin` and `regional_manager`:
- Same as corporate_admin EXCEPT:
  - No "Spend by Sub-Brand" section (they only see their own brand)
  - No "Invoice Summary" section (sub_brand_admin sees their brand; regional_manager
    may have limited invoice visibility — check the auth matrix)

For `employee`:
- Redirect to `/dashboard` or show "Access Denied" message with Carbon
  `InlineNotification` (kind="error")

### 2. Analytics feature components: `frontend/src/components/features/analytics/`

Create focused, composable components:

**`SpendKPICards.tsx`:**
- Accepts `SpendSummary` data
- Renders 3-4 Carbon `Tile` components in a `flex gap-6` layout
- Shows total spend, order count, average order value
- Formats currency with `Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })`

**`SpendBySubBrandTable.tsx`:**
- Carbon `DataTable` with sortable columns: Sub-Brand, Total Spend, Order Count
- Empty state with Carbon `InlineNotification` or custom `EmptyState` component

**`TopProductsTable.tsx`:**
- Carbon `DataTable` with columns: Rank, Product Name, SKU, Quantity, Revenue
- Accepts `limit` prop to control how many rows to show

**`OrderStatusBreakdown.tsx`:**
- Carbon `DataTable` or `StructuredList` showing status → count
- Separate sections for individual orders and bulk orders

**`InvoiceSummaryCards.tsx`:**
- KPI cards for Total Invoiced, Total Paid, Total Outstanding
- Uses Carbon `Tile` with teal accent for paid, yellow for outstanding

**`ApprovalMetricsCards.tsx`:**
- KPI cards: Pending, Approved, Rejected, Approval Rate
- Approval rate formatted as percentage

**`SpendOverTimeChart.tsx`:**
- **Charting approach:** Use `@carbon/charts-react` (Carbon's official charting library
  built on D3). This integrates seamlessly with Carbon's theme tokens.
  - If `@carbon/charts-react` is not yet installed, add it: `npm install @carbon/charts-react d3`
  - Use `LineChart` from `@carbon/charts-react` for the spend-over-time trend
  - Apply Reel48+ teal (`#0a6b6b`) as the primary chart color
  - Wrap in `next/dynamic` with `ssr: false` (D3/charts require browser APIs)
- **Fallback:** If `@carbon/charts-react` proves problematic with Next.js 14,
  use `recharts` instead (widely used, SSR-friendly). Do NOT use Chart.js.

**`DateRangeFilter.tsx`:**
- Carbon `DatePicker` with `datePickerType="range"` and two `DatePickerInput` fields
- Manages start/end date state
- Calls `onDateChange(startDate, endDate)` callback when dates change
- Defaults to last 30 days

### 3. API client hooks: `frontend/src/hooks/useAnalytics.ts`

Create custom hooks for fetching analytics data:

```typescript
export function useSpendSummary(startDate?: string, endDate?: string) { ... }
export function useSpendBySubBrand(startDate?: string, endDate?: string) { ... }
export function useSpendOverTime(startDate?: string, endDate?: string, granularity?: string) { ... }
export function useTopProducts(startDate?: string, endDate?: string, limit?: number) { ... }
export function useOrderStatusBreakdown(startDate?: string, endDate?: string) { ... }
export function useSizeDistribution(startDate?: string, endDate?: string) { ... }
export function useInvoiceSummary(startDate?: string, endDate?: string) { ... }
export function useApprovalMetrics(startDate?: string, endDate?: string) { ... }
```

Each hook:
- Uses the project's existing API client pattern (check `frontend/src/lib/` for
  the established `apiClient` or `fetchWithAuth` helper)
- Handles loading, error, and data states
- Accepts date range params and refetches when they change
- Returns `{ data, isLoading, error }`

### 4. Size Distribution component: `SizeDistribution.tsx`
- Carbon `DataTable` showing size → count → percentage
- Sorted by count descending
- Useful for inventory planning insights

## Verification

Before committing:
1. Run `cd frontend && npm run build` — no TypeScript errors
2. Run `cd frontend && npm run lint` — no ESLint errors
3. Visual review: run `npm run dev` and navigate to the analytics page
4. Verify date range picker updates all data sections
5. Verify role-based content hiding works (test with different role tokens)


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: Frontend — Platform Analytics Dashboard Page
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 8 Phase 5: the platform-level analytics dashboard for `reel48_admin`
users, showing cross-company metrics and revenue breakdowns.

## Context

We are building Module 8 (Analytics Dashboard). Phases 1-4 are complete:
- Backend analytics service and all API endpoints (Phases 1-3)
- Client analytics dashboard page with role-aware content (Phase 4)

The branch is `main`. Create a new branch `feature/module8-phase5-platform-analytics-ui`
from `main` before starting.

## What to Build

### 1. Platform analytics page: `frontend/src/app/(platform)/platform/analytics/page.tsx`

This page is accessible only to `reel48_admin` users. It shows cross-company
platform metrics.

**Page structure:**
- Page header: "Platform Analytics" with date range picker
- **Platform Overview** section — KPI cards in a grid:
  - Total Companies, Total Sub-Brands, Total Users
  - Total Orders, Total Revenue, Active Catalogs
- **Revenue by Company** — Carbon `DataTable` with sortable columns:
  Company Name, Total Revenue, Invoice Count
  Clicking a company row could deep-link to that company's detail (stretch goal)
- **Revenue Over Time** — Line chart using same `SpendOverTimeChart` component
  from Phase 4 (pass platform data instead of client data)
- **Order Status Breakdown** — Reuse `OrderStatusBreakdown` from Phase 4
  with cross-company data
- **Top Products (Platform-Wide)** — Reuse `TopProductsTable` from Phase 4
- **Invoice Summary (Platform-Wide)** — Reuse `InvoiceSummaryCards` from Phase 4
- **Approval Metrics (Platform-Wide)** — Reuse `ApprovalMetricsCards` from Phase 4

### 2. Platform analytics hooks: `frontend/src/hooks/usePlatformAnalytics.ts`

Create hooks that call the `/api/v1/platform/analytics/` endpoints:

```typescript
export function usePlatformOverview() { ... }
export function useRevenueByCompany(startDate?: string, endDate?: string) { ... }
export function usePlatformRevenueOverTime(startDate?: string, endDate?: string, granularity?: string) { ... }
export function usePlatformOrderBreakdown(startDate?: string, endDate?: string) { ... }
export function usePlatformTopProducts(startDate?: string, endDate?: string) { ... }
export function usePlatformInvoiceSummary(startDate?: string, endDate?: string) { ... }
export function usePlatformApprovalMetrics(startDate?: string, endDate?: string) { ... }
```

### 3. Platform-specific components: `frontend/src/components/features/analytics/`

**`PlatformOverviewCards.tsx`:**
- 6 KPI cards in a 2×3 or 3×2 grid
- Uses Carbon `Tile` with icon from `@carbon/react/icons` in each tile
  (e.g., `Enterprise` for companies, `UserMultiple` for users, `ShoppingCart` for orders)

**`RevenueByCompanyTable.tsx`:**
- Carbon `DataTable` with columns: Company Name, Revenue, Invoice Count
- Sortable by revenue (descending default)
- Empty state if no revenue data

### 4. Sidebar navigation update

Update the sidebar (`frontend/src/components/layout/Sidebar.tsx`) to include the
analytics link:
- For authenticated users (manager+): Add "Analytics" link under the admin section
  pointing to `/admin/analytics`
- For platform users: Add "Analytics" link pointing to `/platform/analytics`
- Use the `Analytics` icon from `@carbon/react/icons`

## Verification

Before committing:
1. Run `cd frontend && npm run build` — no TypeScript errors
2. Run `cd frontend && npm run lint` — no ESLint errors
3. Visual review: platform analytics page shows cross-company data
4. Verify only reel48_admin can access the platform analytics page
5. Verify sidebar shows analytics link for appropriate roles


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: Frontend Tests & End-to-End Verification
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 8 Phase 6: frontend component tests, integration verification,
and the end-of-module harness review.

## Context

We are building Module 8 (Analytics Dashboard). Phases 1-5 are complete:
- Backend: AnalyticsService, client + platform API endpoints, tests
- Frontend: Client analytics page, platform analytics page, all components

The branch is `main`. Create a new branch `feature/module8-phase6-frontend-tests`
from `main` before starting.

## What to Build

### 1. Frontend component tests

Using Vitest + React Testing Library, write tests for the analytics components.

**`__tests__/analytics/SpendKPICards.test.tsx`:**
- Renders correctly with valid data (shows formatted currency)
- Handles zero values gracefully
- Handles loading state

**`__tests__/analytics/TopProductsTable.test.tsx`:**
- Renders product rows with correct rank ordering
- Shows empty state when no products
- Respects limit prop

**`__tests__/analytics/DateRangeFilter.test.tsx`:**
- Renders two date inputs
- Calls onDateChange when dates are selected
- Shows default date range (last 30 days)

**`__tests__/analytics/AnalyticsPage.test.tsx`:**
- Role-based rendering: corporate_admin sees all sections
- Role-based rendering: sub_brand_admin does NOT see "Spend by Sub-Brand"
- Role-based rendering: employee sees access denied notification
- Loading states shown while data fetches
- API client hooks are called with correct date range params

**`__tests__/analytics/PlatformAnalyticsPage.test.tsx`:**
- Renders platform overview cards
- Shows revenue by company table
- Uses correct platform API hooks

### 2. MSW handlers for analytics endpoints

Add MSW (Mock Service Worker) handlers for the analytics API endpoints so
frontend tests can run without a backend:

```typescript
// In the existing MSW handler setup file
rest.get('/api/v1/analytics/spend/summary', (req, res, ctx) => {
  return res(ctx.json({
    data: {
      total_spend: 25000.00,
      order_count: 150,
      average_order_value: 166.67,
      individual_order_spend: 15000.00,
      bulk_order_spend: 10000.00,
    },
    meta: {},
    errors: [],
  }));
});
// ... handlers for each endpoint
```

### 3. Run full test suites

- `cd backend && python -m pytest` — all backend tests pass
- `cd frontend && npm test` — all frontend tests pass
- `cd frontend && npm run build` — production build succeeds

### 4. End-of-Module Harness Review (TRIGGER 2)

Per the harness maintenance protocol, perform the post-module review:

#### Pattern Consistency Scan
Review all Module 8 code for consistency with Modules 1-7:
- Do all endpoints follow the route → service → model pattern?
- Are response formats consistent (`ApiResponse[T]`)?
- Are URL conventions consistent (snake_case, plural, versioned)?
- Are role checks explicit and match the auth matrix?

#### Rule Effectiveness Review
For each rule file, note:
- Did it activate when expected?
- Were there gaps the rule should have covered but didn't?

#### Gap Analysis
Identify any new patterns or conventions introduced in Module 8:
- Was a charting library decision needed? → If so, write ADR-009
- Were there any query patterns not covered by the harness?
- Did any date handling patterns emerge that should be standardized?

#### Harness Updates
Update any harness files that need new guidance based on Module 8 learnings.
Annotate additions with the standard format:
```markdown
# --- ADDED {YYYY-MM-DD} after Module 8 ---
# Reason: {what was learned}
# Impact: {what this prevents in future sessions}
```

#### Changelog Entry
Append to `docs/harness-changelog.md`:
```markdown
## {YYYY-MM-DD} — Module 8 Post-Module Harness Review (TRIGGER 2)

**Type:** Post-module harness review (Trigger 2)
**Module:** Module 8 — Analytics Dashboard (Complete)

### Pattern Consistency Scan
{findings}

### Rule Effectiveness Review
{findings}

### ADR Currency Check
{findings}

### Cross-Module Alignment
{findings}

### Gap Analysis
{findings}

### Harness Files Updated
{list of files updated or "no updates needed" with justification}
```

## Verification

Before final commit:
1. All backend tests pass
2. All frontend tests pass
3. Frontend builds without errors
4. Harness changelog updated
5. Any new patterns documented in the appropriate harness files
