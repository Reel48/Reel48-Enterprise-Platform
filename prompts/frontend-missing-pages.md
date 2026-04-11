# Prompt: Build Missing Frontend Pages

## Context

The Reel48+ platform is fully deployed to production:
- **Backend:** ECS Fargate at api.reel48plus.com (all 9 Alembic migrations applied)
- **Frontend:** Vercel at reel48plus.com (Next.js 14, App Router)
- **Auth:** Cognito user pool `us-east-1_kpQToGvpj`

The sidebar navigation (`frontend/src/components/layout/Sidebar.tsx`) links to pages
that don't have `page.tsx` files yet, causing 404 errors in production. The dashboard,
notifications, wishlist, onboarding, and analytics pages ARE built. The pages below
are NOT built and need to be created.

## Pages to Build (8 total)

### Group 1: Platform Admin Pages (reel48_admin only)

These live under `src/app/(platform)/platform/` and are protected by the
`(platform)/layout.tsx` which wraps in `<ProtectedRoute requiredRoles={['reel48_admin']}>`.

#### 1. `/platform/companies` — Companies Management
**File:** `src/app/(platform)/platform/companies/page.tsx`
**Backend endpoints:**
- `GET /api/v1/platform/companies/` — List all companies (paginated)
- `GET /api/v1/platform/companies/{company_id}` — Company detail
- `POST /api/v1/platform/companies/` — Create company
- `PATCH /api/v1/platform/companies/{company_id}` — Update company
- `POST /api/v1/platform/companies/{company_id}/deactivate` — Deactivate

**Requirements:**
- DataTable listing all client companies with columns: name, status, sub-brand count, created date
- Search/filter by name and status
- Pagination using Carbon `Pagination`
- "Create Company" button → modal with company name, contact info
- Row actions: View, Edit, Deactivate
- Click-through to company detail page (can be a modal or separate page)

#### 2. `/platform/catalogs` — Catalog Management
**File:** `src/app/(platform)/platform/catalogs/page.tsx`
**Backend endpoints:**
- `GET /api/v1/platform/catalogs/` — List all catalogs across companies
- `POST /api/v1/platform/catalogs/{catalog_id}/approve` — Approve catalog
- `POST /api/v1/platform/catalogs/{catalog_id}/reject` — Reject catalog
- `POST /api/v1/platform/catalogs/{catalog_id}/activate` — Activate catalog
- `POST /api/v1/platform/catalogs/{catalog_id}/close` — Close catalog

**Requirements:**
- DataTable listing catalogs with columns: name, company name, status, payment_model, product count, created date
- Filter by status (draft, submitted, approved, active, closed) and company
- Pagination
- Row actions: Approve, Reject, Activate, Close (based on current status)
- Status shown as Carbon `Tag` with appropriate colors

#### 3. `/platform/invoices` — Invoice Management
**File:** `src/app/(platform)/platform/invoices/page.tsx`
**Backend endpoints:**
- `GET /api/v1/platform/invoices/` — List all invoices across companies
- `GET /api/v1/platform/invoices/{invoice_id}` — Invoice detail
- `POST /api/v1/platform/invoices/` — Create draft invoice
- `POST /api/v1/platform/invoices/{invoice_id}/finalize` — Finalize
- `POST /api/v1/platform/invoices/{invoice_id}/send` — Send
- `POST /api/v1/platform/invoices/{invoice_id}/void` — Void

**Requirements:**
- DataTable listing invoices with columns: invoice number, company name, billing_flow, status, total amount, created date
- Filter by status (draft, finalized, sent, paid, payment_failed, voided), billing_flow, and company
- Pagination
- "Create Invoice" button → modal or form to create a draft invoice for a target company
- Row actions: Finalize, Send, Void (based on current status)
- Amount formatted as USD currency

---

### Group 2: Authenticated User Pages (all tenant roles)

These live under `src/app/(authenticated)/` and are protected by the
`(authenticated)/layout.tsx` which uses `<ProtectedRoute>` + `<MainLayout>`.

#### 4. `/catalog` — Catalog Browsing
**File:** `src/app/(authenticated)/catalog/page.tsx`
**Backend endpoints:**
- `GET /api/v1/catalogs/` — List catalogs (tenant-scoped, only active ones for employees)
- `GET /api/v1/catalogs/{catalog_id}` — Catalog detail
- `GET /api/v1/catalogs/{catalog_id}/products/` — Products in a catalog

**Requirements:**
- List active catalogs as clickable tiles/cards
- Click a catalog to see its products in a grid layout
- Use existing `ProductCard` component (`src/components/features/catalog/ProductCard.tsx`)
- Products should show name, SKU, price, image (via S3Image or next/image)
- "Add to Cart" or "Add to Wishlist" actions on product cards
- Search/filter products by name
- Pagination for products

#### 5. `/orders` — Orders List
**File:** `src/app/(authenticated)/orders/page.tsx`
**Backend endpoints:**
- `GET /api/v1/orders/my/` — List current user's orders (employees)
- `GET /api/v1/orders/` — List all orders in tenant scope (managers/admins)
- `GET /api/v1/orders/{order_id}` — Order detail

**Requirements:**
- DataTable with columns: order number, status, total amount, date, item count
- Filter by status (pending, approved, processing, shipped, delivered, cancelled)
- Pagination
- Role-aware: employees see only their orders (use `/my/`), managers+ see all orders
- Status shown as Carbon `Tag` with color coding (use the `statusColor()` helper from dashboard)
- Click row to view order detail (can link to `[id]/page.tsx` or show modal)
- Cancel action for pending orders

#### 6. `/profile` — Employee Profile
**File:** `src/app/(authenticated)/profile/page.tsx`
**Backend endpoints:**
- `GET /api/v1/profiles/me` — Get current user's profile
- `PUT /api/v1/profiles/me` — Update profile
- `POST /api/v1/profiles/me/photo` — Upload profile photo
- `DELETE /api/v1/profiles/me/photo` — Remove profile photo
- `POST /api/v1/profiles/me/complete-onboarding` — Mark onboarding complete

**Requirements:**
- Display and edit profile fields: full name, email, department, job title, shirt size, pant size, shoe size, delivery address
- Profile photo upload using the `useFileUpload()` hook from `src/hooks/useStorage.ts`
- Display photo using `S3Image` component from `src/components/ui/S3Image.tsx`
- Size selectors (shirt: XS-5XL, pants: 28-44, shoes: 6-15)
- Carbon form components: `TextInput`, `Dropdown` for sizes
- Save button with success/error notifications
- Profile completeness indicator (reuse the calculation from dashboard)

#### 7. `/bulk-orders` — Bulk Orders List
**File:** `src/app/(authenticated)/bulk-orders/page.tsx`
**Backend endpoints:**
- `GET /api/v1/bulk_orders/` — List bulk orders (tenant-scoped)
- `GET /api/v1/bulk_orders/{bulk_order_id}` — Bulk order detail
- `POST /api/v1/bulk_orders/` — Create bulk order
- `POST /api/v1/bulk_orders/{bulk_order_id}/submit` — Submit for approval
- `POST /api/v1/bulk_orders/{bulk_order_id}/approve` — Approve
- `POST /api/v1/bulk_orders/{bulk_order_id}/cancel` — Cancel

**Requirements:**
- DataTable with columns: bulk order name/ID, status, item count, total amount, created date, created by
- Filter by status (draft, submitted, approved, processing, shipped, delivered, cancelled)
- Pagination
- "Create Bulk Order" button (regional_manager+ only)
- Row actions based on status: Submit, Approve, Cancel
- Click-through to detail page showing line items

#### 8. `/admin/approvals` — Approval Queue
**File:** `src/app/(authenticated)/admin/approvals/page.tsx`
**Backend endpoints:**
- `GET /api/v1/approvals/pending/` — List pending approval requests
- `GET /api/v1/approvals/history/` — List completed approvals
- `GET /api/v1/approvals/{approval_request_id}` — Approval detail
- `POST /api/v1/approvals/{approval_request_id}/approve` — Approve
- `POST /api/v1/approvals/{approval_request_id}/reject` — Reject

**Requirements:**
- Two tabs: "Pending" and "History" using Carbon `Tabs`
- Pending tab: DataTable with columns: request type, requester, amount, submitted date
- History tab: DataTable with columns: request type, requester, decision, decided by, date
- Approve/Reject buttons on pending items (with confirmation modal)
- Reject requires a reason (TextArea in modal)
- Pagination on both tabs

---

## Patterns to Follow

### Reference Pages (already built — copy their patterns):
- **Dashboard** (`src/app/(authenticated)/dashboard/page.tsx`) — KPI cards, data hooks, formatters, Carbon Tile/ClickableTile
- **Notifications** (`src/app/(authenticated)/notifications/page.tsx`) — Pagination, Toggle filter, Tag
- **Wishlist** (`src/app/(authenticated)/wishlist/page.tsx`) — Grid cards, remove action, empty states
- **Analytics** (`src/app/(authenticated)/admin/analytics/page.tsx`) — Charts, date range filter, multiple data hooks
- **Platform Analytics** (`src/app/(platform)/platform/analytics/page.tsx`) — Platform admin data pattern

### API Client Pattern
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api/client';

// List hook
function useOrders(page: number, perPage: number, filters?: Record<string, string>) {
  return useQuery({
    queryKey: ['orders', page, perPage, filters],
    queryFn: async () => {
      const res = await api.get<Order[]>('/api/v1/orders/', {
        page: String(page),
        per_page: String(perPage),
        ...filters,
      });
      return { data: res.data, meta: res.meta as PaginationMeta };
    },
  });
}

// Mutation hook
function useApproveOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: string) => {
      return api.post(`/api/v1/orders/${orderId}/approve`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}
```

### Component Pattern
- Every page file must start with `'use client';`
- Use `export default function PageName()` (default export required by Next.js)
- Use Carbon components: `DataTable`, `Tile`, `Button`, `Tag`, `Pagination`, `Modal`, `Tabs`
- Use Tailwind for layout: `flex`, `grid`, `gap-*`, `items-center`
- Empty states: centered text with a link to a relevant action
- Loading states: Carbon `Loading` component or inline loading
- Error states: Carbon `InlineNotification` with `kind="error"`

### Existing Hooks & Components Available
- `useAuth()` from `@/lib/auth/hooks` — get current user + role
- `useFileUpload()` from `@/hooks/useStorage` — S3 upload flow
- `useDownloadUrl()` from `@/hooks/useStorage` — resolve S3 key to URL
- `<S3Image>` from `@/components/ui/S3Image` — display S3-backed images
- `<ProductCard>` from `@/components/features/catalog/ProductCard` — product display card
- `api` from `@/lib/api/client` — centralized API client (auto snake/camelCase transform)

### Types Available
- `@/types/api` — `ApiResponse`, `ApiListResponse`, `PaginationMeta`, `ApiError`
- `@/types/auth` — `UserRole`, `TenantContext`, `AuthUser`, `AuthState`
- `@/types/engagement` — `NotificationSummary`, `WishlistItem`
- `@/types/storage` — `UploadUrlResponse`, `DownloadUrlResponse`, `StorageCategory`
- `@/types/analytics` — analytics-specific types

### Status Color Helper (reuse across pages)
```typescript
function statusColor(status: string): 'teal' | 'blue' | 'purple' | 'gray' | 'green' | 'red' {
  switch (status) {
    case 'delivered': return 'green';
    case 'shipped': case 'processing': return 'blue';
    case 'approved': case 'active': return 'teal';
    case 'pending': case 'submitted': case 'draft': return 'purple';
    case 'cancelled': case 'rejected': case 'voided': return 'red';
    case 'paid': return 'green';
    case 'payment_failed': return 'red';
    default: return 'gray';
  }
}
```

## Build Order
Build in this order (each group can be parallelized):
1. **Profile page** (simplest, no DataTable needed)
2. **Orders page** (straightforward DataTable + status tags)
3. **Catalog page** (product grid, uses existing ProductCard)
4. **Approvals page** (tabs + approve/reject mutations)
5. **Bulk Orders page** (DataTable + status management)
6. **Platform Companies page** (DataTable + CRUD modal)
7. **Platform Catalogs page** (DataTable + approval actions)
8. **Platform Invoices page** (DataTable + invoice lifecycle actions)

## Post-Build Verification
After building all pages:
1. Run `npm run build` to verify no TypeScript errors
2. Check that all sidebar links resolve without 404
3. Test with the reel48_admin account (brayden@reel48.com) to verify platform pages
4. Deploy to Vercel and verify in production

## Notes
- The API client automatically transforms snake_case ↔ camelCase, so TypeScript types use camelCase
- New TypeScript types will likely be needed for orders, catalogs, bulk orders, approvals, invoices, companies, and profiles — create in `src/types/`
- Some pages may need new React Query hooks — create in `src/hooks/`
- Keep pages self-contained where possible (hooks defined in the page file is fine for simple cases, following the dashboard pattern)
