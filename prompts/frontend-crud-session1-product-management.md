# Frontend CRUD Session 1: Product Management UI
#
# This prompt is designed for a fresh Claude Code session. The CLAUDE.md harness
# files load automatically — this prompt provides session-specific context.
#
# PREREQUISITE: Modules 1–9 backend complete. All backend APIs exist.
# GOAL: Add product CRUD to the frontend so admins can create, edit, delete,
# and submit products for approval.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 1: Product Management Page
# ═══════════════════════════════════════════════════════════════════════════════

Build a product management page at `/catalog/manage` where sub-brand admins,
corporate admins, and reel48_admins can create, edit, delete, and submit products.

## Context

The backend has full product CRUD APIs but the frontend has NO admin product UI.
The `/catalog` page is a read-only employee browsing experience. Admins currently
have no way to create or manage products from the site.

## What Already Exists

### Backend APIs (all tested and working):
- `POST /api/v1/products/` — Create product (admin only)
- `GET /api/v1/products/` — List products (admins see all statuses, employees see active only)
- `GET /api/v1/products/{id}` — Get product detail
- `PATCH /api/v1/products/{id}` — Update product (draft only)
- `DELETE /api/v1/products/{id}` — Soft-delete product (draft only)
- `POST /api/v1/products/{id}/submit` — Submit for approval (draft → submitted)
- `POST /api/v1/products/{id}/images` — Add image (body: `{ s3_key: string }`)
- `DELETE /api/v1/products/{id}/images/{index}` — Remove image by 0-based index

### Backend Schemas (Pydantic — the API client transforms snake_case ↔ camelCase):
```
ProductCreate: { name, description?, sku, unitPrice, sizes[], decorationOptions[], imageUrls[] }
ProductUpdate: { name?, description?, sku?, unitPrice?, sizes?, decorationOptions?, imageUrls? }
ProductResponse: { id, companyId, subBrandId, name, description, sku, unitPrice, sizes[], decorationOptions[], imageUrls[], status, approvedBy, approvedAt, createdBy, deletedAt, createdAt, updatedAt }
```

### Product Status Lifecycle:
```
draft → submitted → approved → active → archived
```
- Only `draft` products can be edited, deleted, or submitted
- Admins see all statuses; employees see only `active`

### Frontend Patterns to Follow:
- `frontend/src/app/(authenticated)/admin/brands/page.tsx` — DataTable + Create modal pattern
- `frontend/src/app/(authenticated)/admin/users/page.tsx` — Tabbed page with colocated `_hooks.ts` and `_types.ts`
- `frontend/src/hooks/useStorage.ts` — `useFileUpload()` hook for S3 image uploads
- `frontend/src/components/ui/S3Image.tsx` — Component to display S3-backed images
- `frontend/src/components/ui/StatusTag.tsx` — Status badge component
- `frontend/src/lib/api/client.ts` — API client (auto transforms snake_case ↔ camelCase)

### Existing Types (DO NOT duplicate):
- `frontend/src/types/catalogs.ts` — Has `CatalogProduct` type with product fields
- `frontend/src/components/features/catalog/ProductCard.tsx` — Has `ProductCardProduct` interface

## What to Build

### 1. Product Types — `frontend/src/types/products.ts`

Create a comprehensive Product type matching `ProductResponse`:
```typescript
export type ProductStatus = 'draft' | 'submitted' | 'approved' | 'active' | 'archived';

export interface Product {
  id: string;
  companyId: string;
  subBrandId: string | null;
  name: string;
  description: string | null;
  sku: string;
  unitPrice: number;
  sizes: string[];
  decorationOptions: string[];
  imageUrls: string[];
  status: ProductStatus;
  approvedBy: string | null;
  approvedAt: string | null;
  createdBy: string;
  deletedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProductCreate {
  name: string;
  description?: string;
  sku: string;
  unitPrice: number;
  sizes?: string[];
  decorationOptions?: string[];
}

export interface ProductUpdate {
  name?: string;
  description?: string;
  sku?: string;
  unitPrice?: number;
  sizes?: string[];
  decorationOptions?: string[];
}
```

### 2. Product Management Hooks — `frontend/src/app/(authenticated)/catalog/manage/_hooks.ts`

Create React Query hooks following the `admin/users/_hooks.ts` pattern:
- `useProducts(page, perPage, status?)` — `GET /api/v1/products/` with status filter
- `useCreateProduct()` — `POST /api/v1/products/`
- `useUpdateProduct()` — `PATCH /api/v1/products/{id}`
- `useDeleteProduct()` — `DELETE /api/v1/products/{id}`
- `useSubmitProduct()` — `POST /api/v1/products/{id}/submit`
- `useAddProductImage()` — `POST /api/v1/products/{id}/images`
- `useRemoveProductImage()` — `DELETE /api/v1/products/{id}/images/{index}`

All mutations should invalidate `['products']` queries on success.

### 3. Product Management Page — `frontend/src/app/(authenticated)/catalog/manage/page.tsx`

Build using the same Carbon DataTable + Modal pattern as `admin/brands/page.tsx`:

**Page Layout:**
- Page header with icon + "Product Management" title
- Status filter dropdown (All, Draft, Submitted, Approved, Active, Archived)
- "Create Product" button (top-right, Carbon `Button` with `Add` icon)
- DataTable with columns: Name, SKU, Price, Status, Created, Actions
- Pagination
- Toast notifications for mutation feedback

**DataTable Row Actions (per product):**
- "Edit" button — opens Edit modal (only for `draft` status, disabled otherwise)
- "Delete" button — soft-deletes with confirmation (only for `draft` status)
- "Submit" button — submits for approval (only for `draft` status)
- Use Carbon `OverflowMenu` or inline `Button` components for actions

**Create Product Modal (Carbon `Modal`):**
- Fields:
  - Name (`TextInput`, required)
  - SKU (`TextInput`, required)
  - Unit Price (`NumberInput`, required, min 0)
  - Description (`TextArea`, optional)
  - Sizes (`TextInput` with tag-style entry or comma-separated, optional)
  - Decoration Options (`TextInput` with tag-style entry, optional)
- Submit calls `useCreateProduct()`
- On success: close modal, show success toast, invalidate query

**Edit Product Modal (same form, pre-populated):**
- Only opens for `draft` products
- Submit calls `useUpdateProduct()`

**Image Management (within Edit modal or separate section):**
- Display current images using `S3Image` component
- "Upload Image" button using `useFileUpload()` from `hooks/useStorage.ts`
  - Category: `'products'`
  - On upload success, call `useAddProductImage()` with the returned `s3Key`
- "Remove" button per image calls `useRemoveProductImage()` with the image index

### 4. Sidebar Update — `frontend/src/components/layout/Sidebar.tsx`

Add a "Manage Products" nav item for admin roles. Insert it after "Catalog" in the
`subBrandAdminNav` array:
```typescript
{ label: 'Manage Products', href: '/catalog/manage', icon: Catalog },
```
This will cascade to `corporateAdminNav` since it spreads `subBrandAdminNav`.

### 5. Role Gating

- The page should check that the user has an admin role (`sub_brand_admin`, `corporate_admin`, or `reel48_admin`)
- If a non-admin navigates to `/catalog/manage`, redirect to `/catalog`
- Use `useAuth()` to check `user?.tenantContext.role`

## Important Implementation Notes

- Use `'use client'` directive since the page imports Carbon components
- Follow the `getHeaderProps`/`getRowProps` key destructuring pattern from the Carbon design system rule (destructure `key` out of spread to avoid TS errors)
- Format prices using `Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })`
- Format dates using the same `formatDate()` helper pattern used in other pages
- The API client (`api.get`, `api.post`, etc.) auto-transforms keys between camelCase (frontend) and snake_case (backend)
- For sizes and decoration options input, a simple approach is a `TextInput` where users type comma-separated values, which get split into an array on submit

## Do NOT Build
- Do NOT modify the existing `/catalog` page (employee browsing) in this session
- Do NOT build catalog management (that's Session 2)
- Do NOT add cart functionality (that's Session 3)
- Do NOT build frontend tests in this session — focus on the UI
