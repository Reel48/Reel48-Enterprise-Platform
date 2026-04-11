# Module 9: Employee Engagement — Phase-by-Phase Implementation Prompts
#
# Each phase below is a self-contained prompt designed to be pasted into a
# fresh Claude Code session. The session will read the CLAUDE.md harness files
# automatically — these prompts provide MODULE-SPECIFIC context that the
# harness doesn't cover.
#
# IMPORTANT: Run phases in order. Each phase depends on the prior phase's output.
#
# MODULE 9 OVERVIEW:
# Employee Engagement drives adoption and participation in the apparel program.
# While Modules 1-8 built the transactional backbone (auth, profiles, catalogs,
# ordering, invoicing, analytics), Module 9 focuses on the EMPLOYEE EXPERIENCE:
# making the platform feel personal, keeping employees informed, and reducing
# friction in the apparel journey.
#
# This module adds three core capabilities:
# 1. **Notifications & Announcements** — Admins can broadcast announcements
#    (new catalogs, buying window reminders, company-wide messages) to employees.
#    Employees see a notification feed with read/unread tracking.
# 2. **Wishlists / Favorites** — Employees can save products they're interested
#    in for later purchase. This drives repeat visits and catalog engagement.
# 3. **Enhanced Employee Dashboard** — The stub dashboard (from Module 1) becomes
#    a personalized hub: profile completeness nudge, recent orders, active
#    catalogs, unread notifications, and wishlist highlights.
#
# Engagement is scoped by the same tenant isolation model as everything else:
# - `reel48_admin` can see/manage notifications across all companies
# - `corporate_admin` can create company-wide announcements
# - `sub_brand_admin` can create sub-brand-scoped announcements
# - `regional_manager` has read-only access to notifications
# - `employee` sees notifications targeted to them (company-wide, sub-brand, or individual)
#   and manages their own wishlist
#
# Key architectural points:
# - TWO new database tables: `notifications`, `wishlists` (+ migration 009)
# - Notification read tracking via a JSONB `read_by` array on the notification
#   record (not a separate junction table — simpler for the expected scale)
# - Wishlists are per-user, per-product (unique constraint)
# - All new tables follow TenantBase (company_id + sub_brand_id) with standard RLS
# - Employee dashboard is a frontend-only enhancement querying existing endpoints
#   plus the new notification and wishlist endpoints
# - Profile completeness is calculated client-side from the existing profile data
#   (no new backend endpoint needed — reuse GET /api/v1/profiles/me)
#
# What ALREADY EXISTS (do not rebuild):
# - Employee Profiles (Module 2): employee_profiles table with sizing, department,
#   delivery address, onboarding_complete flag, PUT /profiles/me upsert
# - Products & Catalogs (Module 3): products, catalogs, catalog_products tables
#   with status lifecycle and buying windows
# - Orders (Module 4): orders + order_line_items with GET /orders/my/ endpoint
# - Users (Module 1): users table with role, company_id, sub_brand_id
# - All tenant isolation infrastructure (RLS, TenantContext, auth middleware)
# - Frontend shell: Sidebar, Header, MainLayout, ProtectedRoute, auth context
# - IBM Carbon design system with Reel48+ theme (teal interactive, charcoal brand)
# - Stub dashboard page at frontend/src/app/(authenticated)/dashboard/page.tsx
#
# What Module 9 BUILDS:
# - `notifications` table with RLS policies (migration 009)
# - `wishlists` table with RLS policies (migration 009)
# - NotificationService (create, list, mark read, admin management)
# - WishlistService (add, remove, list)
# - Notification API endpoints (admin create/manage + employee feed)
# - Wishlist API endpoints (employee CRUD)
# - Enhanced employee dashboard frontend (KPIs, notifications, wishlists, profile nudge)
# - Onboarding completion wizard (profile completeness + guided setup)
# - Comprehensive tests (functional, isolation, authorization)


---
---

# ===============================================================================
# PHASE 1: Database Migration — Notifications & Wishlists Tables
# ===============================================================================

Build Module 9 Phase 1: the Alembic migration, SQLAlchemy models, Pydantic schemas,
and test infrastructure updates for the employee engagement system.

## Context

We are building Module 9 (Employee Engagement) of the Reel48+ enterprise apparel
platform. Modules 1-8 are complete:
- Module 1: Auth, Companies, Sub-Brands, Users (migration `001`)
- Module 2: Employee Profiles (migration `002`)
- Module 3: Products, Catalogs, Catalog-Products (migration `003`)
- Module 4: Orders, Order Line Items (migration `004`)
- Module 5: Bulk Orders, Bulk Order Items (migration `005`)
- Module 6: Approval Requests, Approval Rules (migration `006`)
- Module 7: Invoices (migration `007`)
- Module 8: Analytics (no migration — read-only queries)

The branch is `main`. Create a new branch `feature/module9-phase1-engagement-tables`
from `main` before starting.

## What to Build

### 1. Alembic Migration: `009_create_notifications_and_wishlists_tables.py`

Create migration `009` with two tables. Both tables follow TenantBase with standard
RLS (company isolation PERMISSIVE + sub-brand scoping RESTRICTIVE).

#### `notifications` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK -> companies, indexed)
sub_brand_id            UUID        NULL (FK -> sub_brands, indexed)
title                   VARCHAR(255) NOT NULL
body                    TEXT         NOT NULL
notification_type       VARCHAR(30)  NOT NULL
                        -- 'announcement' (admin broadcast)
                        -- 'catalog_available' (new catalog went active)
                        -- 'buying_window_reminder' (window closing soon)
                        -- 'order_update' (order status changed)
target_scope            VARCHAR(20)  NOT NULL DEFAULT 'sub_brand'
                        -- 'company' (all employees in the company)
                        -- 'sub_brand' (all employees in the sub-brand)
                        -- 'individual' (single user, set target_user_id)
target_user_id          UUID         NULL (FK -> users)
                        -- Set only when target_scope = 'individual'
read_by                 JSONB        NOT NULL DEFAULT '[]'
                        -- Array of user ID strings who have read this notification
                        -- e.g., ["uuid1", "uuid2"]
                        -- Simpler than a junction table at expected scale (<1000 reads/notification)
link_url                VARCHAR(500) NULL
                        -- Optional deep link (e.g., "/catalogs/abc-123", "/orders/my")
expires_at              TIMESTAMP    NULL
                        -- Auto-hide after this time (NULL = never expires)
created_by              UUID         NOT NULL (FK -> users)
is_active               BOOLEAN      NOT NULL DEFAULT true
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
CHECK constraints: `notification_type` IN valid values, `target_scope` IN valid values.
Composite index: `(company_id, is_active, created_at DESC)` for the notification feed query.
Index on `target_user_id` for individual notification lookups.

#### `wishlists` Table (TenantBase)
```
id                      UUID        PRIMARY KEY
company_id              UUID        NOT NULL (FK -> companies, indexed)
sub_brand_id            UUID        NULL (FK -> sub_brands, indexed)
user_id                 UUID         NOT NULL (FK -> users)
product_id              UUID         NOT NULL (FK -> products)
catalog_id              UUID         NULL (FK -> catalogs)
                        -- Optional: which catalog context the product was saved from
notes                   TEXT         NULL
                        -- Optional personal note ("need size L", "for spring event")
created_at              TIMESTAMP    NOT NULL
updated_at              TIMESTAMP    NOT NULL
```
UNIQUE constraint: `(user_id, product_id)` — one wishlist entry per user per product.
Composite index: `(user_id, created_at DESC)` for the user's wishlist feed.

#### RLS Policies
Both tables get the standard two-policy pattern:
- `{table}_company_isolation` (PERMISSIVE) — company_id match or reel48_admin bypass
- `{table}_sub_brand_scoping` (RESTRICTIVE) — sub_brand_id match or corporate/reel48 bypass

### 2. SQLAlchemy Models

#### `backend/app/models/notification.py`
```python
class Notification(TenantBase):
    __tablename__ = "notifications"
    # ... all columns from the schema above
```

#### `backend/app/models/wishlist.py`
```python
class Wishlist(TenantBase):
    __tablename__ = "wishlists"
    # ... all columns from the schema above
```

Update `backend/app/models/__init__.py` to export both new models.

### 3. Pydantic Schemas

#### `backend/app/schemas/notification.py`
- `NotificationCreate` — title, body, notification_type, target_scope, target_user_id
  (optional), link_url (optional), expires_at (optional)
- `NotificationResponse` — all fields + computed `is_read` field (based on whether
  the requesting user's ID is in the `read_by` array)
- `NotificationListResponse` — standard paginated list with unread_count in meta

#### `backend/app/schemas/wishlist.py`
- `WishlistCreate` — product_id, catalog_id (optional), notes (optional)
- `WishlistResponse` — all fields + nested product name/sku/image for display
- `WishlistListResponse` — standard paginated list

### 4. Test Infrastructure Updates

Update `backend/tests/conftest.py`:
- Add `GRANT SELECT, INSERT, UPDATE, DELETE ON notifications TO reel48_app`
- Add `GRANT SELECT, INSERT, UPDATE, DELETE ON wishlists TO reel48_app`

### 5. Verification

After implementation:
- Run `alembic upgrade head` against the test database
- Verify both tables exist with correct columns, constraints, and indexes
- Verify RLS policies are created (query `pg_policies`)
- Run the existing test suite to ensure no regressions
- Commit with message: `feat: add notifications and wishlists tables (Module 9 Phase 1)`


---
---

# ===============================================================================
# PHASE 2: Notification Service & API Endpoints
# ===============================================================================

Build Module 9 Phase 2: the NotificationService and API endpoints for creating,
listing, and managing notifications.

## Context

We are building Module 9 (Employee Engagement) of the Reel48+ enterprise apparel
platform. Phase 1 is complete — the `notifications` and `wishlists` tables exist
with RLS policies.

The branch is the latest Module 9 branch. Create a new branch
`feature/module9-phase2-notification-service` from the current state.

## What to Build

### 1. NotificationService: `backend/app/services/notification_service.py`

Create a `NotificationService` class following the same pattern as other services
(takes `db: AsyncSession` in constructor).

#### Methods

```python
async def create_notification(
    self,
    company_id: UUID,
    sub_brand_id: UUID | None,
    data: NotificationCreate,
    created_by: UUID,
) -> Notification:
    """
    Create a notification/announcement.
    - company-scope notifications: sub_brand_id should be None on the notification
      record (visible to all sub-brands via RLS)
    - sub_brand-scope: sub_brand_id set to the creator's sub-brand
    - individual: sub_brand_id set, target_user_id set
    Validates target_user_id exists and belongs to the same company if target_scope='individual'.
    """
```

```python
async def list_notifications_for_user(
    self,
    user_id: UUID,
    company_id: UUID,
    sub_brand_id: UUID | None,
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
) -> tuple[list[Notification], int, int]:
    """
    List notifications visible to the given user.
    Filters: is_active=True, not expired, AND one of:
      - target_scope='company' (company-wide)
      - target_scope='sub_brand' AND sub_brand_id matches
      - target_scope='individual' AND target_user_id matches
    Returns: (notifications, total_count, unread_count)
    The unread_count is the total number of unread notifications (not just this page).
    Order by created_at DESC (newest first).
    """
```

```python
async def mark_as_read(
    self,
    notification_id: UUID,
    user_id: str,
) -> Notification:
    """
    Add user_id to the read_by JSONB array if not already present.
    Uses PostgreSQL JSONB || operator or SQLAlchemy func to append.
    Idempotent — calling twice for the same user has no effect.
    """
```

```python
async def mark_all_as_read(
    self,
    user_id: str,
    company_id: UUID,
    sub_brand_id: UUID | None,
) -> int:
    """
    Mark all unread notifications as read for the given user.
    Returns the count of newly marked notifications.
    Uses a bulk UPDATE with JSONB array append.
    """
```

```python
async def list_notifications_admin(
    self,
    company_id: UUID,
    sub_brand_id: UUID | None,
    page: int = 1,
    per_page: int = 20,
    notification_type: str | None = None,
) -> tuple[list[Notification], int]:
    """
    Admin view: list all notifications created within the company/sub-brand scope.
    Unlike the employee feed, this shows all notifications (including expired and
    inactive) for management purposes. Supports filtering by notification_type.
    """
```

```python
async def deactivate_notification(
    self,
    notification_id: UUID,
    company_id: UUID,
) -> Notification:
    """
    Soft-deactivate a notification (set is_active=False).
    Does not hard-delete — preserves audit trail.
    """
```

### 2. API Endpoints

#### Employee Notification Feed: `backend/app/api/v1/notifications.py`

Router prefix: `/api/v1/notifications`

- `GET /` — List notifications for the authenticated employee. Supports `?unread_only=true`
  and standard pagination. Returns `unread_count` in the `meta` object alongside
  pagination fields. All authenticated roles can access.

- `POST /{notification_id}/read` — Mark a single notification as read. Returns the
  updated notification. All authenticated roles.

- `POST /read-all` — Mark all unread notifications as read. Returns `{"marked_count": N}`
  in the data field. All authenticated roles.

#### Admin Notification Management: `backend/app/api/v1/notifications.py` (same file)

- `POST /` — Create a new notification/announcement. Requires `is_admin` (sub_brand_admin
  or above). Sub-brand admins can only create sub_brand-scope or individual-scope
  notifications within their sub-brand. Corporate admins can create company-scope.
  reel48_admin can create any scope.

- `GET /admin/` — List all notifications for management. Requires `is_admin`. Supports
  `?notification_type=` filter.

- `DELETE /{notification_id}` — Deactivate a notification (soft-delete via is_active=False).
  Requires `is_admin`. Returns 200 with the deactivated notification.

#### Register routes in `backend/app/api/v1/router.py`.

### 3. Role-Based Authorization Rules

| Action | reel48_admin | corporate_admin | sub_brand_admin | regional_manager | employee |
|--------|:-:|:-:|:-:|:-:|:-:|
| Create notification (company scope) | Y | Y | N | N | N |
| Create notification (sub_brand scope) | Y | Y | Y | N | N |
| Create notification (individual scope) | Y | Y | Y | N | N |
| View notification feed | Y | Y | Y | Y | Y |
| Mark as read | Y | Y | Y | Y | Y |
| Admin list notifications | Y | Y | Y | N | N |
| Deactivate notification | Y | Y | Y (own sub-brand only) | N | N |

### 4. Tests: `backend/tests/test_notifications.py`

Write comprehensive tests covering:

**Functional tests:**
- Create a company-scope announcement, verify it appears in employee feed
- Create a sub-brand-scope announcement, verify scoping
- Create an individual notification, verify only target user sees it
- Mark notification as read, verify read_by updated
- Mark all as read, verify count returned
- Filter feed by unread_only=true
- Expired notifications do not appear in feed
- Deactivated notifications do not appear in feed
- Admin list shows all notifications including expired/inactive
- Pagination works correctly

**Isolation tests:**
- Company B cannot see Company A's notifications
- Sub-Brand A2 employee cannot see Sub-Brand A1's sub-brand-scope notifications
- Corporate admin sees all sub-brand notifications in their company

**Authorization tests:**
- Employee cannot create notifications (403)
- Regional manager cannot create notifications (403)
- Sub-brand admin cannot create company-scope notifications (403)
- Unauthenticated request returns 401

### 5. Verification

After implementation:
- All new tests pass
- Existing test suite has no regressions
- Commit: `feat: add notification service and API endpoints (Module 9 Phase 2)`


---
---

# ===============================================================================
# PHASE 3: Wishlist Service & API Endpoints
# ===============================================================================

Build Module 9 Phase 3: the WishlistService and API endpoints for employee
product wishlists/favorites.

## Context

We are building Module 9 (Employee Engagement) of the Reel48+ enterprise apparel
platform. Phase 1 (tables) and Phase 2 (notifications) are complete.

Create a new branch `feature/module9-phase3-wishlist-service` from the current state.

## What to Build

### 1. WishlistService: `backend/app/services/wishlist_service.py`

Create a `WishlistService` class following the same pattern as other services.

#### Methods

```python
async def add_to_wishlist(
    self,
    user_id: UUID,
    company_id: UUID,
    sub_brand_id: UUID | None,
    data: WishlistCreate,
) -> Wishlist:
    """
    Add a product to the user's wishlist.
    Validates:
    - Product exists and belongs to the same company
    - Product is active (status='active')
    - Not already in the user's wishlist (UNIQUE constraint on user_id+product_id)
    If catalog_id is provided, validates the catalog exists and contains the product.
    Returns the created wishlist entry with product details.
    """
```

```python
async def remove_from_wishlist(
    self,
    wishlist_id: UUID,
    user_id: UUID,
) -> None:
    """
    Remove a product from the user's wishlist. Hard delete.
    Validates the wishlist entry belongs to the requesting user.
    """
```

```python
async def list_wishlist(
    self,
    user_id: UUID,
    company_id: UUID,
    sub_brand_id: UUID | None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Wishlist], int]:
    """
    List the user's wishlist with product details.
    Joins wishlists -> products to include product name, SKU, unit_price, image_urls, status.
    Orders by created_at DESC (most recently added first).
    Includes a flag indicating if the product is still active/purchasable.
    """
```

```python
async def check_wishlist(
    self,
    user_id: UUID,
    product_ids: list[UUID],
) -> dict[UUID, bool]:
    """
    Check if multiple products are in the user's wishlist.
    Returns a dict mapping product_id -> is_wishlisted.
    Used by the frontend to show filled/unfilled heart icons on product cards.
    """
```

### 2. API Endpoints: `backend/app/api/v1/wishlists.py`

Router prefix: `/api/v1/wishlists`

- `GET /` — List the authenticated user's wishlist with product details. Standard
  pagination. All authenticated roles.

- `POST /` — Add a product to the wishlist. Accepts `WishlistCreate` body.
  All authenticated roles. Returns 201.

- `DELETE /{wishlist_id}` — Remove a product from the wishlist. Hard delete.
  Returns 204 No Content. Only the owning user can delete.

- `POST /check` — Check if products are wishlisted. Accepts `{"product_ids": [UUID, ...]}`
  in body. Returns `{"data": {"uuid1": true, "uuid2": false}}`. All authenticated roles.
  This is POST (not GET) because the product_ids list could be large.

#### Register routes in `backend/app/api/v1/router.py`.

### 3. Wishlist Response with Product Details

The `WishlistResponse` schema should include nested product information so the
frontend can render the wishlist without additional API calls:

```python
class WishlistResponse(BaseModel):
    id: UUID
    product_id: UUID
    catalog_id: UUID | None
    product_name: str        # from joined product
    product_sku: str         # from joined product
    product_unit_price: float  # from joined product
    product_image_url: str | None  # first image from product.image_urls
    product_status: str      # from joined product (active, archived, etc.)
    is_purchasable: bool     # True if product is active
    notes: str | None
    created_at: datetime
```

### 4. Tests: `backend/tests/test_wishlists.py`

**Functional tests:**
- Add a product to wishlist, verify 201 and response includes product details
- Add duplicate product returns 409 Conflict
- Add non-existent product returns 404
- Add archived/draft product returns 403 (only active products can be wishlisted)
- Remove from wishlist, verify 204
- Remove another user's wishlist entry returns 404
- List wishlist returns products with details, newest first
- Check endpoint returns correct true/false for each product_id
- Pagination works correctly

**Isolation tests:**
- Company B cannot see Company A's wishlists
- User in Sub-Brand A2 cannot see Sub-Brand A1 user's wishlists
- Cannot add a product from another company to wishlist

**Authorization tests:**
- All roles can manage their own wishlist
- Unauthenticated request returns 401

### 5. Verification

After implementation:
- All new tests pass
- Existing test suite has no regressions
- Commit: `feat: add wishlist service and API endpoints (Module 9 Phase 3)`


---
---

# ===============================================================================
# PHASE 4: Enhanced Employee Dashboard — Frontend
# ===============================================================================

Build Module 9 Phase 4: the enhanced employee dashboard frontend that transforms
the stub dashboard into a personalized engagement hub.

## Context

We are building Module 9 (Employee Engagement) of the Reel48+ enterprise apparel
platform. Phases 1-3 are complete — notification and wishlist backend APIs are live.

Create a new branch `feature/module9-phase4-employee-dashboard` from the current state.

## What to Build

### 1. API Hooks: `frontend/src/hooks/useEngagement.ts`

Create React Query hooks for the new engagement endpoints:

```typescript
// Notifications
export function useNotifications(params?: { unreadOnly?: boolean; page?: number }) { ... }
export function useMarkNotificationRead() { ... }  // mutation
export function useMarkAllNotificationsRead() { ... }  // mutation
export function useUnreadNotificationCount() { ... }  // derived from useNotifications meta

// Wishlists
export function useWishlist(params?: { page?: number }) { ... }
export function useAddToWishlist() { ... }  // mutation
export function useRemoveFromWishlist() { ... }  // mutation
export function useCheckWishlist(productIds: string[]) { ... }
```

### 2. Notification Bell Component: `frontend/src/components/features/engagement/NotificationBell.tsx`

A header-integrated notification indicator:
- Shows a Carbon `Notification` icon in the header
- Displays an unread count badge (red dot with number) when > 0
- On click, opens a dropdown/panel showing recent notifications
- Each notification shows title, timestamp, and read/unread state
- "Mark all as read" action at the top of the dropdown
- Clicking a notification with a `link_url` navigates to that URL
- Uses Carbon `OverflowMenu` pattern or a custom popover with Carbon styling

### 3. Notification Feed Page: `frontend/src/app/(authenticated)/notifications/page.tsx`

A full-page notification feed for viewing all notifications:
- Lists all notifications with pagination
- Filter toggle: "All" / "Unread"
- Each notification card shows: type icon, title, body preview, timestamp, read state
- Click to expand the full body or navigate to link_url
- "Mark all as read" button at the top
- Empty state when no notifications

### 4. Enhanced Dashboard: `frontend/src/app/(authenticated)/dashboard/page.tsx`

Replace the stub dashboard with a personalized engagement hub. The layout varies
by role:

#### Employee Dashboard (role = 'employee')
Use a card-based layout with Carbon `Tile` components and Tailwind grid:

**Row 1: Welcome + Profile Completeness**
- Welcome message with user's name
- Profile completeness indicator (progress bar or percentage)
  - Calculate from existing profile fields: shirt_size, pant_size, shoe_size,
    delivery_address_line1, department, job_title
  - If `onboarding_complete = false`, show a prominent "Complete Your Profile" CTA
    linking to `/profile` or triggering the onboarding wizard (Phase 5)

**Row 2: Quick Stats (KPI Cards)**
- "My Orders" count (from GET /api/v1/orders/my/ total)
- "Active Catalogs" count (from GET /api/v1/catalogs/ with status=active)
- "Wishlist Items" count (from GET /api/v1/wishlists/ total)
- "Unread Notifications" count (from notification hook)

**Row 3: Recent Activity**
- Left card: "Recent Orders" — last 3-5 orders with status badges (from /orders/my/)
- Right card: "Unread Notifications" — last 3-5 unread notifications with a
  "View All" link to /notifications

**Row 4: Wishlist Highlights**
- Horizontal scrollable row of wishlisted products (product card format)
- "View Full Wishlist" link
- If empty: "Browse catalogs to start your wishlist" with a link to catalogs

#### Manager/Admin Dashboard (role = regional_manager or above)
Show the employee dashboard content PLUS:
- "Team Overview" card: count of employees, pending approvals
- "Announcements" card: recent notifications created by the admin
- Link to the full analytics page

Use the existing analytics hooks from Module 8 for any aggregate data.

### 5. Sidebar Navigation Updates

Update `frontend/src/components/layout/Sidebar.tsx`:
- Add "Notifications" link (all roles) with unread badge count
- Add "Wishlist" link (all roles)
- Group under an "Engagement" section or add to the existing navigation

### 6. Wishlist Page: `frontend/src/app/(authenticated)/wishlist/page.tsx`

A dedicated page for managing the wishlist:
- Grid of wishlisted products using Carbon `Tile` components
- Each product tile shows: image, name, SKU, price, "Remove" button
- Products that are no longer active show a "No longer available" badge
- Notes field displayed on each card (editable inline if possible, or via modal)
- Empty state: "Your wishlist is empty — browse catalogs to find products you love"
- Link to catalogs page

### 7. Component Design Rules

- Follow Carbon design system conventions (see `.claude/rules/carbon-design-system.md`)
- Use Carbon `Tile`, `Tag`, `Button`, `InlineNotification`, `DataTable` components
- Use Tailwind for layout grid (`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4`)
- Use `'use client'` directive on all component files that import Carbon
- Use the Reel48+ color tokens (teal interactive, charcoal brand)
- Follow the frontend CLAUDE.md conventions for hooks, API client, and auth patterns
- Notification type icons: use Carbon icons matching the type
  (e.g., `Catalog` for catalog_available, `ShoppingCart` for order_update,
  `Bullhorn`/`Notification` for announcement)

### 8. Verification

After implementation:
- Dashboard renders correctly for employee role
- Dashboard renders correctly for admin/manager roles
- Notification bell shows unread count and dropdown works
- Notification feed page lists and filters notifications
- Wishlist page renders and allows removal
- Navigation links work
- No TypeScript errors, no ESLint warnings
- Commit: `feat: add enhanced employee dashboard and engagement UI (Module 9 Phase 4)`


---
---

# ===============================================================================
# PHASE 5: Onboarding Wizard & Wishlist Integration
# ===============================================================================

Build Module 9 Phase 5: the guided onboarding wizard for profile completion and
wishlist heart icons on product/catalog pages.

## Context

We are building Module 9 (Employee Engagement) of the Reel48+ enterprise apparel
platform. Phases 1-4 are complete — backend APIs and the dashboard frontend are built.

Create a new branch `feature/module9-phase5-onboarding-wishlist-ui` from the current state.

## What to Build

### 1. Onboarding Wizard: `frontend/src/components/features/engagement/OnboardingWizard.tsx`

A multi-step guided flow for new employees to complete their profile. Shown when
`onboarding_complete = false` on the employee's profile.

**Trigger:** On the dashboard, if `onboarding_complete` is false, show a prominent
banner or modal prompting the user to complete onboarding. Can also be accessed
directly via `/onboarding` route.

**Steps (using Carbon `ProgressIndicator` + `ProgressStep`):**

1. **Welcome** — Brief welcome message explaining the apparel program.
   "Welcome to [Company Name]'s apparel program! Let's get you set up."

2. **Sizing Information** — Shirt size, pant size, shoe size dropdowns.
   Use Carbon `Dropdown` components with standard size options.
   Pre-fill if the profile already has values.

3. **Delivery Address** — Address form fields (line1, line2, city, state, zip, country).
   Use Carbon `TextInput` components in a form layout.
   Pre-fill from existing profile data.

4. **Department & Role** — Department and job title fields.
   Use Carbon `TextInput` or `Dropdown` for department.

5. **Complete** — Summary of entered data with a "Finish Setup" button.
   On submit: call `PUT /api/v1/profiles/me` with all data.
   Then call `PATCH /api/v1/profiles/{id}` (admin endpoint) or a new dedicated
   endpoint to set `onboarding_complete = true`.

**Design:**
- Use Carbon `ProgressIndicator` for step visualization
- "Next" / "Back" / "Skip" buttons at the bottom of each step
- Allow skipping individual steps (sizing, address) — they're optional
- The wizard saves progress on each "Next" (calls PUT /profiles/me)
- On the final "Finish Setup", set `onboarding_complete = true`

**Implementation note on `onboarding_complete`:** The `PUT /profiles/me` endpoint
uses `EmployeeProfileCreate` schema which does NOT include `onboarding_complete`
(it's an admin-only field). Options:
- **Option A (recommended):** Add a dedicated `POST /api/v1/profiles/me/complete-onboarding`
  endpoint that sets `onboarding_complete = true`. This is the cleanest approach —
  employees can mark their own onboarding as complete but cannot set it to false.
- **Option B:** Include `onboarding_complete` in the `PUT /me` schema. Less secure
  since employees could set it to false.

Go with Option A.

### 2. Complete Onboarding Endpoint: `backend/app/api/v1/employee_profiles.py`

Add a new endpoint to the existing employee_profiles router:

```python
@router.post("/me/complete-onboarding", response_model=ApiResponse[EmployeeProfileResponse])
async def complete_onboarding(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[EmployeeProfileResponse]:
    """
    Mark the authenticated user's onboarding as complete.
    Sets onboarding_complete=True on their profile.
    If no profile exists, creates one with onboarding_complete=True.
    Idempotent — calling when already complete is a no-op (returns 200).
    """
```

### 3. Wishlist Heart Icon on Product Cards

Integrate the wishlist "heart" icon into existing product display contexts:

- If there are product card/tile components in `frontend/src/components/features/catalog/`,
  add a heart icon (Carbon `FavoriteFilled` / `Favorite` icon) that toggles wishlist state
- Use the `useCheckWishlist` hook to batch-check which products are wishlisted
- Use `useAddToWishlist` / `useRemoveFromWishlist` mutations on click
- Heart is filled (teal) when wishlisted, outline when not
- Show a brief Carbon `ToastNotification` on add/remove: "Added to wishlist" / "Removed from wishlist"
- If no product card components exist yet, create a `ProductCard.tsx` in
  `frontend/src/components/features/catalog/` that can be reused across catalog
  browsing and wishlist pages

### 4. Onboarding Route: `frontend/src/app/(authenticated)/onboarding/page.tsx`

A dedicated page that renders the `OnboardingWizard` component.
- Protected route (any authenticated role)
- On completion, redirects to `/dashboard`
- If `onboarding_complete` is already true, redirect to `/dashboard` immediately

### 5. Dashboard Integration

Update the dashboard (from Phase 4) to show the onboarding prompt:
- If `onboarding_complete = false`: Show a prominent banner at the top of the
  dashboard with "Complete Your Profile" CTA linking to `/onboarding`
- Use Carbon `ActionableNotification` with kind="info" for the banner

### 6. Tests

**Backend tests (add to existing test files):**
- `POST /profiles/me/complete-onboarding` sets `onboarding_complete = true`
- Calling complete-onboarding when already complete returns 200 (idempotent)
- Calling complete-onboarding without an existing profile creates one
- Unauthenticated request returns 401

**Frontend tests:**
- OnboardingWizard renders all steps
- Navigation between steps works
- Wishlist heart icon toggles correctly
- Dashboard shows onboarding banner when `onboarding_complete = false`

### 7. Verification

After implementation:
- Onboarding wizard works end-to-end
- Heart icons appear on product displays
- Dashboard integrates onboarding prompt
- All tests pass
- Commit: `feat: add onboarding wizard and wishlist UI integration (Module 9 Phase 5)`


---
---

# ===============================================================================
# PHASE 6: Comprehensive Tests & Harness Review
# ===============================================================================

Build Module 9 Phase 6: comprehensive test coverage, frontend tests, and the
mandatory post-module harness review.

## Context

We are building Module 9 (Employee Engagement) of the Reel48+ enterprise apparel
platform. Phases 1-5 are complete — all backend and frontend features are built.

Create a new branch `feature/module9-phase6-tests-harness-review` from the current state.

## What to Build

### 1. Backend Test Coverage Audit

Review all Module 9 test files and ensure coverage for:

**Notification tests (`test_notifications.py`):**
- [ ] Create each notification type (announcement, catalog_available, buying_window_reminder, order_update)
- [ ] Company-scope notification visible to all employees in company
- [ ] Sub-brand-scope notification visible only to sub-brand employees
- [ ] Individual notification visible only to target user
- [ ] Expired notifications excluded from feed
- [ ] Deactivated notifications excluded from feed
- [ ] Mark as read is idempotent
- [ ] Mark all as read returns correct count
- [ ] Unread-only filter works
- [ ] Admin list includes expired/inactive
- [ ] Company isolation (Company B cannot see Company A notifications)
- [ ] Sub-brand isolation (Brand A2 cannot see Brand A1 notifications)
- [ ] Corporate admin sees all sub-brand notifications
- [ ] Employee cannot create notifications
- [ ] Regional manager cannot create notifications
- [ ] Sub-brand admin cannot create company-scope notifications
- [ ] reel48_admin can create any scope

**Wishlist tests (`test_wishlists.py`):**
- [ ] Add product to wishlist (201)
- [ ] Duplicate add returns 409
- [ ] Add inactive product returns 403
- [ ] Add product from another company returns 404
- [ ] Remove from wishlist (204)
- [ ] Remove another user's item returns 404
- [ ] List shows product details and pagination
- [ ] Check endpoint returns correct boolean map
- [ ] Company isolation
- [ ] Sub-brand isolation

**Onboarding tests:**
- [ ] Complete onboarding endpoint sets flag to true
- [ ] Idempotent — calling twice is fine
- [ ] Creates profile if none exists

### 2. Frontend Test Coverage

Create/update frontend tests following the patterns in `.claude/rules/testing.md`:

**`frontend/src/__tests__/dashboard.test.tsx`:**
- Dashboard renders employee view with KPI cards
- Dashboard shows onboarding banner when onboarding_complete=false
- Dashboard hides onboarding banner when onboarding_complete=true
- Dashboard renders manager view with team overview section
- Notification bell shows unread count

**`frontend/src/__tests__/notifications.test.tsx`:**
- Notification feed page renders notification list
- Unread filter toggle works
- Mark all as read button calls API

**`frontend/src/__tests__/wishlist.test.tsx`:**
- Wishlist page renders product cards
- Remove button calls API
- Empty state shown when no items

**`frontend/src/__tests__/onboarding.test.tsx`:**
- Wizard renders all progress steps
- Can navigate forward and back
- Complete button submits profile data
- Redirects to dashboard on completion

Remember: Mock `@carbon/charts-react` if used, add ResizeObserver polyfill in
setup.ts (per the testing rule). Mock API calls with appropriate patterns.

### 3. RLS Isolation Tests

Add or verify RLS isolation tests using the `db_session` (non-superuser) fixture:

```python
# Pattern from testing.md — use real UUIDs, not empty strings
async def test_notification_company_isolation(db_session, admin_db_session, ...):
    # Seed notifications for Company A and Company B via admin_db_session
    # Query as Company A via db_session with SET LOCAL
    # Verify Company B's notifications are not visible
```

### 4. Post-Module Harness Review (TRIGGER 2)

Run the mandatory post-module harness review per `docs/harness-changelog.md` conventions.

**Step 1: Pattern Consistency Scan**
- Do all Module 9 endpoints follow the route -> service -> model pattern?
- Are response formats consistent with ApiResponse[T]?
- Do all frontend components follow Carbon conventions?
- Are naming conventions consistent (snake_case backend, camelCase frontend)?

**Step 2: Rule Effectiveness Review**
- Did the testing.md rule guide test creation correctly?
- Did the carbon-design-system.md rule guide component creation correctly?
- Were any rules insufficient or missing?

**Step 3: ADR Currency Check**
- Are all existing ADRs still accurate?
- Does Module 9 require a new ADR? (Unlikely unless a non-obvious decision was made)

**Step 4: Cross-Module Alignment**
- Do notifications follow the same soft-delete pattern as other entities?
- Do wishlists follow the hard-delete pattern for transient data?
- Is the onboarding endpoint consistent with the PUT /me upsert pattern?

**Step 5: Harness Updates**
Update harness files as needed:
- Add notification/wishlist table schemas to `backend/CLAUDE.md` Module 9 section
- Update authentication.md role-based access matrix with notification permissions
- Add any new patterns discovered during Module 9 to relevant rule files
- Update `docs/harness-changelog.md` with the review summary

**Step 6: Commit**
Commit all test additions and harness updates:
`test: add comprehensive engagement tests and complete Module 9 harness review`

### 5. Final Verification

- Run the full backend test suite — all tests pass
- Run the full frontend test suite — all tests pass
- No TypeScript errors
- No ESLint warnings
- Review the git log to ensure all Module 9 commits are clean and well-messaged
