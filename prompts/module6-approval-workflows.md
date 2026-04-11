# Module 6: Approval Workflows — Phase-by-Phase Implementation Prompts
#
# Each phase below is a self-contained prompt designed to be pasted into a
# fresh Claude Code session. The session will read the CLAUDE.md harness files
# automatically — these prompts provide MODULE-SPECIFIC context that the
# harness doesn't cover.
#
# IMPORTANT: Run phases in order. Each phase depends on the prior phase's output.
#
# MODULE 6 OVERVIEW:
# Approval Workflows adds a unified approval tracking layer on top of the
# entity-specific status transitions already built in Modules 3-5. Currently,
# approve/reject actions exist as inline service methods (e.g.,
# ProductService.approve_product, OrderService.approve_order), but there is no
# audit trail, no unified approval queue, no notification system, and no
# configurable approval rules.
#
# Module 6 introduces:
# - An `approval_requests` table that tracks every approval decision with
#   actor, timestamp, comments, and decision history
# - A unified Approval Service that wraps existing entity-specific transitions
#   and records approval audit trails
# - Approval queue endpoints ("show me everything pending my approval")
# - Configurable approval rules (e.g., orders above $X require corporate_admin)
# - SES email notifications for approval events (submit, approve, reject)
# - Platform admin approval dashboard for cross-company visibility
#
# What ALREADY EXISTS (do not rebuild):
# - Product approve/reject/activate: ProductService + platform/products.py
# - Catalog approve/reject/activate/close: CatalogService + platform/catalogs.py
# - Order approve: OrderService + orders.py
# - Bulk order submit/approve: BulkOrderService + bulk_orders.py
# - All status transition logic, guards, and authorization checks
#
# Module 6 WRAPS these existing transitions — it does not replace them.
# The approval service calls the existing service methods and adds audit
# trail recording and notification dispatch on top.
#
# Approvable entity types:
# - `product`  — submitted → approved/rejected by reel48_admin
# - `catalog`  — submitted → approved/rejected by reel48_admin
# - `order`    — pending → approved by manager_or_above
# - `bulk_order` — submitted → approved by manager_or_above


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Database Migration — Approval Requests & Approval Rules
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 6 Phase 1: the Alembic migration, SQLAlchemy models, and test
infrastructure updates for the approval workflow system.

## Context

We are building Module 6 (Approval Workflows) of the Reel48+ enterprise apparel
platform. Modules 1-5 are complete:
- Module 1: Auth, Companies, Sub-Brands, Users (migration `001`)
- Module 2: Employee Profiles (migration `002`)
- Module 3: Products, Catalogs, Catalog-Products (migration `003`)
- Module 4: Orders, Order Line Items (migration `004`)
- Module 5: Bulk Orders, Bulk Order Items (migration `005`)

The current test suite has 316 passing tests. The branch is `main`.
Create a new branch `feature/module6-phase1-approval-tables` from `main`
before starting.

## What to Build

### 1. Alembic migration: `backend/migrations/versions/006_create_module6_approval_tables.py`

Create two tables in a single migration (same pattern as migrations `004` and `005`):

**`approval_requests` table (TenantBase shape):**
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL FK → companies.id
sub_brand_id            UUID        NULL FK → sub_brands.id
entity_type             VARCHAR(30)  NOT NULL         -- 'product', 'catalog', 'order', 'bulk_order'
entity_id               UUID         NOT NULL         -- FK to the specific entity (NOT a DB-level FK — polymorphic)
requested_by            UUID         NOT NULL FK → users.id  -- who submitted for approval
decided_by              UUID         NULL FK → users.id       -- who approved/rejected (NULL while pending)
status                  VARCHAR(20)  NOT NULL DEFAULT 'pending'  -- 'pending', 'approved', 'rejected'
decision_notes          TEXT         NULL              -- reviewer's comment on approve/reject
requested_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
decided_at              TIMESTAMP WITH TIME ZONE NULL
created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
```

CHECK constraints:
- `ck_approval_requests_entity_type_valid`: entity_type IN ('product', 'catalog', 'order', 'bulk_order')
- `ck_approval_requests_status_valid`: status IN ('pending', 'approved', 'rejected')

Indexes:
- `ix_approval_requests_company_id` on (company_id)
- `ix_approval_requests_sub_brand_id` on (sub_brand_id)
- `ix_approval_requests_entity_type_entity_id` on (entity_type, entity_id)
- `ix_approval_requests_status` on (status)
- `ix_approval_requests_company_id_status` on (company_id, status) — for approval queue queries
- `ix_approval_requests_requested_by` on (requested_by)
- `ix_approval_requests_decided_by` on (decided_by)

RLS policies (both in same migration):
- `approval_requests_company_isolation` — PERMISSIVE, standard company isolation pattern
- `approval_requests_sub_brand_scoping` — RESTRICTIVE, standard sub-brand scoping pattern

**`approval_rules` table (CompanyBase shape — company-level, no sub_brand_id):**
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL FK → companies.id
entity_type             VARCHAR(30)  NOT NULL         -- 'order', 'bulk_order' (products/catalogs always need reel48_admin)
rule_type               VARCHAR(30)  NOT NULL         -- 'amount_threshold'
threshold_amount        NUMERIC(10,2) NULL            -- e.g., 500.00 means orders over $500 need higher approval
required_role           VARCHAR(50)  NOT NULL         -- minimum role required (e.g., 'corporate_admin')
is_active               BOOLEAN      NOT NULL DEFAULT true
created_by              UUID         NOT NULL FK → users.id
created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
```

CHECK constraints:
- `ck_approval_rules_entity_type_valid`: entity_type IN ('order', 'bulk_order')
- `ck_approval_rules_rule_type_valid`: rule_type IN ('amount_threshold')
- `ck_approval_rules_required_role_valid`: required_role IN ('corporate_admin', 'sub_brand_admin', 'regional_manager')
- `ck_approval_rules_threshold_non_negative`: threshold_amount >= 0

Indexes:
- `ix_approval_rules_company_id` on (company_id)
- `ix_approval_rules_company_id_entity_type` on (company_id, entity_type) — for rule lookup

RLS policies:
- `approval_rules_company_isolation` — PERMISSIVE, standard company isolation pattern
- No sub-brand scoping (CompanyBase — rules are company-wide)

UNIQUE constraint: `(company_id, entity_type, rule_type)` — one rule per type per company.

### 2. SQLAlchemy models

**`backend/app/models/approval_request.py`:**
- Inherits from `TenantBase`
- All columns from the migration above
- No `deleted_at` (approval records are permanent audit trail — never soft-deleted)

**`backend/app/models/approval_rule.py`:**
- Inherits from `CompanyBase`
- All columns from the migration above

Update `backend/app/models/__init__.py` to import both new models.

### 3. Test infrastructure updates

In `backend/tests/conftest.py`:
- Add `approval_requests` and `approval_rules` to the `GRANT` list in `setup_database`
- No new fixtures needed in this phase (Phase 2 will create approval-specific fixtures)

### 4. Verify

- Run `alembic upgrade head` against the test database
- Run the full test suite to confirm no regressions (all 316 tests pass)
- Run `alembic downgrade -1` and then `alembic upgrade head` to verify reversibility

### Deliverables
- [ ] Migration file `006_create_module6_approval_tables.py` with tables + RLS + downgrade
- [ ] `approval_request.py` and `approval_rule.py` model files
- [ ] Updated `__init__.py` model imports
- [ ] Updated `conftest.py` grants
- [ ] All 316 existing tests still pass
- [ ] Commit on branch `feature/module6-phase1-approval-tables`


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Pydantic Schemas & Approval Service
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 6 Phase 2: the Pydantic request/response schemas and the unified
ApprovalService that wraps existing entity-specific transitions with audit trail
recording.

## Context

Phase 1 created the `approval_requests` and `approval_rules` tables. The existing
entity-specific approval methods (ProductService.approve_product, CatalogService.
approve_catalog, OrderService.approve_order, BulkOrderService.approve_bulk_order)
are fully functional. This phase creates a unified service layer on top.

Continue on branch `feature/module6-phase1-approval-tables` or create
`feature/module6-phase2-approval-service` from the Phase 1 branch.

## What to Build

### 1. Pydantic schemas: `backend/app/schemas/approval.py`

**Request schemas:**

```python
class ApprovalDecisionRequest(BaseModel):
    """Used for POST /approvals/{id}/approve and /reject."""
    decision_notes: str | None = None   # reviewer's comment

class ApprovalRuleCreate(BaseModel):
    """Used for POST /approval_rules/."""
    entity_type: str        # 'order' or 'bulk_order'
    rule_type: str          # 'amount_threshold'
    threshold_amount: float
    required_role: str      # 'corporate_admin', 'sub_brand_admin', 'regional_manager'

class ApprovalRuleUpdate(BaseModel):
    """Used for PATCH /approval_rules/{id}."""
    threshold_amount: float | None = None
    required_role: str | None = None
    is_active: bool | None = None
```

**Response schemas:**

```python
class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    entity_type: str
    entity_id: UUID
    requested_by: UUID
    decided_by: UUID | None
    status: str
    decision_notes: str | None
    requested_at: datetime
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime

class ApprovalQueueItem(BaseModel):
    """Extended response for queue endpoints — includes entity summary."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    status: str
    requested_by: UUID
    requested_at: datetime
    # Denormalized entity fields for queue display:
    entity_name: str          # product.name, catalog.name, order.order_number, bulk_order.title
    entity_amount: float | None  # order.total_amount, bulk_order.total_amount, None for products/catalogs

class ApprovalRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    entity_type: str
    rule_type: str
    threshold_amount: float | None
    required_role: str
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
```

### 2. Approval Service: `backend/app/services/approval_service.py`

The ApprovalService is the central orchestrator. It:
1. Creates `approval_requests` records when entities are submitted for approval
2. Processes approve/reject decisions by calling the existing entity service methods
   AND recording the decision in the `approval_requests` table
3. Evaluates `approval_rules` to determine if the acting user's role is sufficient
4. Provides queue queries (pending approvals filtered by role and scope)

**Key methods:**

```python
class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_submission(
        self,
        entity_type: str,
        entity_id: UUID,
        company_id: UUID,
        sub_brand_id: UUID | None,
        requested_by: UUID,
    ) -> ApprovalRequest:
        """Record that an entity has been submitted for approval.

        Called by existing submit endpoints (product submit, catalog submit,
        bulk order submit). Individual orders skip this — they go straight
        to 'pending' status at creation time, which IS their approval request.

        For orders, call record_submission at order creation time with the
        order's user_id as requested_by.
        """

    async def process_decision(
        self,
        approval_request_id: UUID,
        decided_by: UUID,
        decision: str,          # 'approved' or 'rejected'
        decision_notes: str | None,
        role: str,
        company_id: UUID | None,
    ) -> ApprovalRequest:
        """Process an approval decision.

        Steps:
        1. Load the approval_request, verify it's still pending
        2. Check approval rules — if the entity has an amount-threshold rule,
           verify the deciding user's role meets the required_role
        3. Call the appropriate entity service method:
           - product: approve_product() or reject_product()
           - catalog: approve_catalog() or reject_catalog()
           - order: approve_order()
           - bulk_order: approve_bulk_order()
        4. Update the approval_request with decided_by, decided_at, status, notes
        5. Return the updated approval_request
        """

    async def check_approval_rules(
        self,
        entity_type: str,
        entity_id: UUID,
        company_id: UUID,
        role: str,
    ) -> bool:
        """Check if the user's role satisfies any active approval rules.

        For products and catalogs: always requires reel48_admin (hardcoded,
        no configurable rules — these are platform-level approvals).

        For orders and bulk_orders: check the approval_rules table for the
        company. If an amount_threshold rule exists and the entity's total_amount
        exceeds it, the user must have at least the required_role.

        Role hierarchy for threshold checks:
        reel48_admin > corporate_admin > sub_brand_admin > regional_manager
        """

    async def list_pending(
        self,
        company_id: UUID | None,
        sub_brand_id: UUID | None,
        role: str,
        entity_type_filter: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ApprovalRequest], int]:
        """List pending approval requests visible to the current user.

        Visibility:
        - reel48_admin: all pending across all companies
        - corporate_admin: all pending in their company
        - sub_brand_admin: pending in their sub-brand
        - regional_manager: pending orders/bulk_orders in their sub-brand
          (NOT products/catalogs — those are reel48_admin only)

        Returns approval_requests joined with entity data for display.
        """

    async def list_history(
        self,
        company_id: UUID | None,
        sub_brand_id: UUID | None,
        entity_type_filter: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ApprovalRequest], int]:
        """List decided (approved/rejected) approval requests.
        Same visibility rules as list_pending."""

    async def get_approval_request(
        self, approval_request_id: UUID
    ) -> ApprovalRequest:
        """Get a single approval request by ID."""
```

**Approval Rules Management:**

```python
    async def create_rule(
        self,
        data: ApprovalRuleCreate,
        company_id: UUID,
        created_by: UUID,
    ) -> ApprovalRule:
        """Create an approval rule. One active rule per (company, entity_type, rule_type).
        If a duplicate exists, raise ConflictError."""

    async def update_rule(
        self,
        rule_id: UUID,
        data: ApprovalRuleUpdate,
        company_id: UUID,
    ) -> ApprovalRule:
        """Update an existing approval rule."""

    async def list_rules(
        self,
        company_id: UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ApprovalRule], int]:
        """List approval rules for a company."""

    async def deactivate_rule(
        self,
        rule_id: UUID,
        company_id: UUID,
    ) -> ApprovalRule:
        """Soft-deactivate a rule (is_active = false)."""
```

### 3. Integration hooks

The existing submit/approve endpoints in Modules 3-5 need to call the ApprovalService
to record submissions and process decisions. However, **do not modify those endpoints
in this phase** — Phase 3 will integrate the approval service into the existing
endpoints. In this phase, build the service methods so they can be called standalone.

### 4. Tests

Write tests in `backend/tests/test_approvals.py`:

**Functional tests:**
- Create an approval_request record and verify all fields
- Process an approval decision and verify status, decided_by, decided_at
- Process a rejection decision and verify status + notes
- Cannot approve/reject an already-decided request (returns 403)
- Create an approval rule with amount threshold
- Rule uniqueness: cannot create duplicate (company, entity_type, rule_type)
- Deactivate a rule

**Approval rules tests:**
- Order below threshold: regional_manager can approve
- Order above threshold with `required_role = corporate_admin`: regional_manager
  cannot approve (403), corporate_admin can
- No active rule: default behavior (manager_or_above for orders)
- Deactivated rule: treated as no rule (default behavior)

**Isolation tests:**
- Company A cannot see Company B's approval requests
- Company A cannot see Company B's approval rules
- Sub-brand A1 admin cannot see sub-brand A2's approval requests
- Corporate admin sees all sub-brands' approval requests

### Deliverables
- [ ] `backend/app/schemas/approval.py`
- [ ] `backend/app/services/approval_service.py`
- [ ] `backend/tests/test_approvals.py` with functional, rules, and isolation tests
- [ ] All existing 316 tests still pass + new tests pass
- [ ] Commit on branch


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Approval Queue & Decision Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 6 Phase 3: tenant-scoped approval queue endpoints and approval
decision endpoints.

## Context

Phase 2 created the ApprovalService with record_submission, process_decision,
check_approval_rules, list_pending, list_history, and rule management methods.
This phase exposes these through API endpoints and integrates the approval
service into the existing entity submit/approve flows.

Continue on the Phase 2 branch or create
`feature/module6-phase3-approval-endpoints` from the Phase 2 branch.

## What to Build

### 1. Tenant approval endpoints: `backend/app/api/v1/approvals.py`

**Approval Queue:**

```
GET /api/v1/approvals/pending/
```
- Lists all pending approval requests visible to the current user
- Query params: `entity_type` (optional filter), `page`, `per_page`
- Returns `ApprovalQueueItem` list (includes entity summary fields)
- Visibility rules (from ApprovalService.list_pending):
  - `reel48_admin`: all pending across all companies
  - `corporate_admin`: all pending in their company (all sub-brands)
  - `sub_brand_admin`: pending in their sub-brand (all entity types)
  - `regional_manager`: pending orders + bulk_orders in their sub-brand
    (NOT products/catalogs — those are reel48_admin-only approvals)
  - `employee`: 403 (employees don't approve anything)

```
GET /api/v1/approvals/history/
```
- Lists decided (approved + rejected) approval requests visible to the current user
- Query params: `entity_type`, `status` ('approved' or 'rejected'), `page`, `per_page`
- Same visibility rules as pending queue

```
GET /api/v1/approvals/{approval_request_id}
```
- Get a single approval request detail
- Must be within user's company/sub-brand scope (or reel48_admin)

**Approval Decisions:**

```
POST /api/v1/approvals/{approval_request_id}/approve
```
- Body: `ApprovalDecisionRequest` (optional `decision_notes`)
- Calls `ApprovalService.process_decision(decision='approved')`
- Internally calls the entity-specific approve method
- Returns the updated `ApprovalRequestResponse`
- Authorization: varies by entity_type (see rules below)

```
POST /api/v1/approvals/{approval_request_id}/reject
```
- Body: `ApprovalDecisionRequest` (optional `decision_notes`)
- Calls `ApprovalService.process_decision(decision='rejected')`
- Internally calls the entity-specific reject method
- Returns the updated `ApprovalRequestResponse`
- Authorization: same as approve

**Authorization by entity type:**
| Entity Type | Who Can Approve/Reject |
|------------|----------------------|
| `product` | `reel48_admin` only |
| `catalog` | `reel48_admin` only |
| `order` | `manager_or_above` (subject to approval rules) |
| `bulk_order` | `manager_or_above` (subject to approval rules) |

### 2. Approval rules endpoints: `backend/app/api/v1/approval_rules.py`

```
POST /api/v1/approval_rules/
```
- Create an approval rule for the current user's company
- Requires `corporate_admin` or above
- Body: `ApprovalRuleCreate`

```
GET /api/v1/approval_rules/
```
- List approval rules for the current user's company
- Requires `corporate_admin` or above
- Query params: `page`, `per_page`

```
PATCH /api/v1/approval_rules/{rule_id}
```
- Update a rule (threshold, required_role, is_active)
- Requires `corporate_admin` or above

```
DELETE /api/v1/approval_rules/{rule_id}
```
- Deactivate a rule (soft: `is_active = false`)
- Returns 200 with the deactivated rule
- Requires `corporate_admin` or above

### 3. Integration with existing submit endpoints

Modify the existing submit/creation flows to also create approval_requests:

**Product submit** (`POST /api/v1/products/{product_id}/submit`):
- After `ProductService.submit_product()` succeeds, call
  `ApprovalService.record_submission(entity_type='product', ...)`

**Catalog submit** (`POST /api/v1/catalogs/{catalog_id}/submit`):
- After `CatalogService.submit_catalog()` succeeds, call
  `ApprovalService.record_submission(entity_type='catalog', ...)`

**Bulk order submit** (`POST /api/v1/bulk_orders/{bulk_order_id}/submit`):
- After `BulkOrderService.submit_bulk_order()` succeeds, call
  `ApprovalService.record_submission(entity_type='bulk_order', ...)`

**Order creation** (`POST /api/v1/orders/`):
- After `OrderService.create_order()` succeeds, call
  `ApprovalService.record_submission(entity_type='order', ...)`
- Orders are submitted for approval at creation time (they start as 'pending')

**IMPORTANT:** The existing direct approve/reject platform endpoints
(`/api/v1/platform/products/{id}/approve`, etc.) should STILL WORK as-is.
They are the "direct" path. The unified `/api/v1/approvals/{id}/approve`
endpoint is the "queue-based" path. Both call the same underlying service
methods. If someone uses the direct path, also update the corresponding
approval_request record to 'approved'/'rejected'.

### 4. Register routes

Add `approvals.py` and `approval_rules.py` to `backend/app/api/v1/router.py`.

### 5. Tests

Add to `backend/tests/test_approvals.py`:

**Endpoint tests:**
- GET pending queue returns only pending items in user's scope
- GET history returns only decided items
- POST approve updates both the approval_request AND the entity status
- POST reject updates both and records notes
- Cannot approve/reject a non-pending request (409 Conflict)
- Employee gets 403 on all approval endpoints

**Integration tests:**
- Submitting a product creates an approval_request with entity_type='product'
- Creating an order creates an approval_request with entity_type='order'
- Approving via the direct platform endpoint also updates the approval_request
- Approving via the unified endpoint also updates the entity status

**Approval rules endpoint tests:**
- Create rule, list rules, update rule, deactivate rule
- Only corporate_admin can manage rules
- Sub-brand admin gets 403 on rule management
- Rule takes effect: regional_manager blocked on high-value order

**Isolation tests:**
- Company B cannot see Company A's approval queue
- Company B cannot manage Company A's rules

### Deliverables
- [ ] `backend/app/api/v1/approvals.py` (queue + decision endpoints)
- [ ] `backend/app/api/v1/approval_rules.py` (rule management endpoints)
- [ ] Updated router.py with new routes
- [ ] Modified submit/create endpoints to record approval_requests
- [ ] Direct platform approve/reject endpoints sync with approval_requests
- [ ] Tests for all new endpoints + integration + isolation
- [ ] All existing tests still pass
- [ ] Commit on branch


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: Platform Admin Approval Dashboard Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 6 Phase 4: platform admin endpoints for cross-company approval
visibility and management.

## Context

Phase 3 built the tenant-scoped approval queue and decision endpoints. Platform
admins (reel48_admin) already see all pending items via the tenant endpoints
(their company_id is None, so RLS bypass shows everything). However, they need
dedicated platform endpoints with cross-company filtering and summary statistics.

Continue on the Phase 3 branch or create
`feature/module6-phase4-platform-approvals` from the Phase 3 branch.

## What to Build

### 1. Platform approval endpoints: `backend/app/api/v1/platform/approvals.py`

```
GET /api/v1/platform/approvals/
```
- List ALL approval requests across all companies
- Query params: `status` (pending/approved/rejected), `entity_type`,
  `company_id` (optional filter), `page`, `per_page`
- Requires `reel48_admin`
- Uses `ApprovalService.list_all_approvals()` (new method — no company filter,
  optional filters by status/type/company)

```
GET /api/v1/platform/approvals/summary
```
- Returns approval statistics:
  ```json
  {
    "data": {
      "pending_count": 12,
      "by_entity_type": {
        "product": 3,
        "catalog": 2,
        "order": 5,
        "bulk_order": 2
      },
      "by_company": [
        {"company_id": "...", "company_name": "Acme Corp", "pending_count": 7},
        {"company_id": "...", "company_name": "Beta Inc", "pending_count": 5}
      ]
    }
  }
  ```
- Requires `reel48_admin`

```
GET /api/v1/platform/approvals/{approval_request_id}
```
- Get detail for any approval request (cross-company)
- Requires `reel48_admin`

```
POST /api/v1/platform/approvals/{approval_request_id}/approve
POST /api/v1/platform/approvals/{approval_request_id}/reject
```
- Platform-level approve/reject. Works the same as the tenant endpoint but
  explicitly for reel48_admin. This is mainly for products/catalogs where
  only reel48_admin can approve.
- Body: `ApprovalDecisionRequest`

### 2. Platform approval rules endpoints: `backend/app/api/v1/platform/approval_rules.py`

```
GET /api/v1/platform/approval_rules/
```
- List ALL approval rules across all companies
- Query params: `company_id` (optional filter), `entity_type`, `page`, `per_page`
- Requires `reel48_admin`

### 3. Add new service method

Add `list_all_approvals()` and `get_approval_summary()` to ApprovalService:

```python
async def list_all_approvals(
    self,
    status_filter: str | None = None,
    entity_type_filter: str | None = None,
    company_id_filter: UUID | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ApprovalRequest], int]:
    """List approval requests across ALL companies. For reel48_admin only."""

async def get_approval_summary(self) -> dict:
    """Aggregate pending approval counts by entity_type and company."""
```

### 4. Register routes

Add `platform/approvals.py` and `platform/approval_rules.py` to router.py.

### 5. Tests

**Platform endpoint tests:**
- List all approvals with and without filters
- Summary endpoint returns correct counts by type and company
- Approve/reject product via platform approval endpoint
- Non-reel48_admin gets 403 on all platform endpoints

**Cross-company visibility:**
- Platform list shows approvals from multiple companies
- Company filter narrows results correctly

### Deliverables
- [ ] `backend/app/api/v1/platform/approvals.py`
- [ ] `backend/app/api/v1/platform/approval_rules.py`
- [ ] Updated ApprovalService with list_all_approvals() and get_approval_summary()
- [ ] Updated router.py
- [ ] Tests for platform endpoints
- [ ] All existing tests still pass
- [ ] Commit on branch


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: Approval Notifications (SES Email)
# ═══════════════════════════════════════════════════════════════════════════════

Build Module 6 Phase 5: email notifications for approval events using Amazon SES.

## Context

Phases 1-4 built the approval tracking infrastructure and endpoints. This phase
adds email notifications so that relevant users are alerted when:
1. An entity is submitted for their approval (approver notification)
2. Their submission is approved or rejected (submitter notification)

Continue on the Phase 4 branch or create
`feature/module6-phase5-approval-notifications` from the Phase 4 branch.

## What to Build

### 1. Email Service: `backend/app/services/email_service.py`

This is the first SES integration in the project. Follow the External Service
Integration Pattern from `backend/CLAUDE.md` — wrap the boto3 SES client in a
service class with a FastAPI dependency factory.

```python
class EmailService:
    def __init__(self, client: Any, sender_email: str):
        self._client = client  # boto3 SES client
        self._sender_email = sender_email

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> str:
        """Send a single email via SES. Returns the SES message ID."""

    async def send_approval_needed_notification(
        self,
        to_email: str,
        entity_type: str,
        entity_name: str,
        submitted_by_name: str,
        approval_url: str,
    ) -> str:
        """Notify an approver that something needs their review."""

    async def send_approval_decision_notification(
        self,
        to_email: str,
        entity_type: str,
        entity_name: str,
        decision: str,            # 'approved' or 'rejected'
        decided_by_name: str,
        decision_notes: str | None,
    ) -> str:
        """Notify the submitter that their submission was approved/rejected."""

def get_email_service() -> EmailService:
    """FastAPI dependency factory."""
    import boto3
    client = boto3.client("ses", region_name=settings.SES_REGION)
    return EmailService(client, settings.SES_SENDER_EMAIL)
```

### 2. Notification dispatch in ApprovalService

Add notification dispatch to `record_submission()` and `process_decision()`:

**On submission (`record_submission`):**
- Determine who needs to approve:
  - For products/catalogs: find reel48_admin users (query users table for role='reel48_admin')
  - For orders/bulk_orders: find manager_or_above users in the same company/sub-brand
- Send `send_approval_needed_notification()` to each potential approver
- **Do not block on email failures** — log the error and continue. The approval
  request is created regardless of whether the notification succeeds.

**On decision (`process_decision`):**
- Look up the submitter's email (from `requested_by` user record)
- Send `send_approval_decision_notification()` with the decision + notes
- **Do not block on email failures** — same as above.

### 3. Email templates

Use simple HTML templates for emails. Store template strings as constants in
the email service module (no separate template files for now — keep it simple).

Templates needed:
- `APPROVAL_NEEDED_TEMPLATE` — "A {entity_type} needs your approval"
- `APPROVAL_DECISION_TEMPLATE` — "Your {entity_type} has been {approved/rejected}"

### 4. Configuration

Add to `backend/app/core/config.py`:
```python
SES_REGION: str = "us-east-1"
SES_SENDER_EMAIL: str = "noreply@reel48.com"
FRONTEND_BASE_URL: str = "https://app.reel48.com"  # for approval links
```

### 5. Mock service for tests

Create `MockEmailService` in `conftest.py` following the External Service Mock
Pattern from `.claude/rules/testing.md`:
- Records sent emails in a list for assertions
- Autouse fixture registers via `app.dependency_overrides`

### 6. Tests

**Functional tests:**
- Submitting a product triggers approval_needed notification
- Approving a request triggers decision notification to submitter
- Rejecting a request triggers decision notification with notes
- Email failure does not prevent the approval request from being created

**Integration tests:**
- Full flow: create product → submit → approval_needed email sent → approve →
  decision email sent
- Verify email recipients are correct (reel48_admin for products, managers for orders)

### Deliverables
- [ ] `backend/app/services/email_service.py` with SES integration
- [ ] Updated `ApprovalService` with notification dispatch
- [ ] `MockEmailService` in conftest.py
- [ ] Config additions for SES
- [ ] Tests for notification behavior
- [ ] All existing tests still pass
- [ ] Commit on branch


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: Harness Review & Module Completion
# ═══════════════════════════════════════════════════════════════════════════════

Run the Module 6 post-module harness review. This is a MANDATORY maintenance
step per the Harness Maintenance Protocol in the root CLAUDE.md.

## Context

Module 6 (Approval Workflows) is functionally complete after Phases 1-5. This
phase performs the end-of-module self-audit, updates harness files, and documents
all patterns introduced.

## What to Do

### 1. End-of-Session Self-Audit

Answer each question from the `harness-maintenance.md` checklist:

- **New pattern?** Expected additions:
  - Polymorphic entity reference pattern (`entity_type` + `entity_id` columns)
  - Unified approval queue with entity-type-aware authorization
  - Configurable approval rules (amount thresholds)
  - SES email notification pattern (External Service Integration Pattern applied to SES)
  - Cross-entity audit trail pattern (approval_requests spanning multiple tables)

- **Pattern violated?** Check if any Module 6 code deviates from established patterns.

- **New decision?** Consider whether the polymorphic entity_type pattern warrants an ADR.

- **Missing guidance?** Anything the harness didn't cover that Module 6 needed?

- **Reusable task?** Consider a `prompts/notification-service.md` template if the
  SES pattern will recur.

### 2. Update Harness Files

**`backend/CLAUDE.md`:**
- Add Module 6 Table Schemas section (approval_requests, approval_rules)
- Add Approval Workflow Patterns section documenting:
  - The unified approval queue model
  - How approval_requests wrap existing entity transitions
  - The polymorphic entity_type + entity_id pattern
  - Approval rules and threshold-based authorization
  - Notification dispatch pattern

**`.claude/rules/authentication.md`:**
- Update the Role-Based Access Matrix with approval-related permissions:
  - Manage approval rules: corporate_admin and above
  - View approval queue: manager_or_above (entity-type restrictions apply)
  - Approve/reject: depends on entity type

**`docs/harness-changelog.md`:**
- Add Module 6 completion entry with all harness files updated

### 3. Final Verification

- Run the FULL test suite — all tests must pass (original 316 + new Module 6 tests)
- Verify all new endpoints are registered in router.py
- Verify approval_requests and approval_rules tables have proper RLS policies

### 4. Module 6 Patterns Doc

Add to `docs/` a brief summary of Module 6's key patterns for reference by
Modules 7-8 (Invoicing depends on approval status; Analytics may query
approval metrics).

### Deliverables
- [ ] Updated `backend/CLAUDE.md` with Module 6 schemas and patterns
- [ ] Updated `.claude/rules/authentication.md` with approval permissions
- [ ] Updated `docs/harness-changelog.md` with Module 6 entry
- [ ] All tests pass
- [ ] Commit: `chore: Module 6 harness review — add approval workflow patterns docs and changelog entry`
