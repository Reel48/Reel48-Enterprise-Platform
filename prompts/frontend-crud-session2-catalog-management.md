# Frontend CRUD Session 2: Catalog Management UI
#
# PREREQUISITE: Session 1 (Product Management) complete.
# GOAL: Add catalog CRUD so admins can create catalogs, add/remove products,
# and submit catalogs for approval.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 2: Catalog Management
# ═══════════════════════════════════════════════════════════════════════════════

Build catalog management functionality so tenant admins can create, edit, delete,
and populate catalogs with products, then submit them for platform approval.

## Context

The backend has full catalog CRUD + product junction APIs. The frontend currently
has NO admin catalog UI — the `/catalog` page is read-only for browsing active
catalogs. Products can now be managed (Session 1), but there's no way to group
them into catalogs.

## What Already Exists

### Backend APIs (all tested and working):
- `POST /api/v1/catalogs/` — Create catalog (admin only)
- `GET /api/v1/catalogs/` — List catalogs (admins see all statuses)
- `GET /api/v1/catalogs/{id}` — Get catalog detail
- `PATCH /api/v1/catalogs/{id}` — Update catalog (draft only)
- `DELETE /api/v1/catalogs/{id}` — Soft-delete catalog (draft only)
- `POST /api/v1/catalogs/{id}/submit` — Submit for approval (requires ≥1 product)
- `POST /api/v1/catalogs/{id}/products/` — Add product to catalog (body: `{ productId, displayOrder?, priceOverride? }`)
- `DELETE /api/v1/catalogs/{id}/products/{productId}` — Remove product from catalog
- `GET /api/v1/catalogs/{id}/products/` — List products in a catalog

### Backend Schemas:
```
CatalogCreate: { name, description?, paymentModel: 'self_service' | 'invoice_after_close', buyingWindowOpensAt?, buyingWindowClosesAt? }
CatalogUpdate: { name?, description?, buyingWindowOpensAt?, buyingWindowClosesAt? }
CatalogResponse: { id, companyId, subBrandId, name, description, slug, paymentModel, status, buyingWindowOpensAt, buyingWindowClosesAt, approvedBy, approvedAt, createdBy, deletedAt, createdAt, updatedAt }
CatalogProductAdd: { productId, displayOrder?, priceOverride? }
CatalogProductResponse: { id, catalogId, productId, displayOrder, priceOverride, companyId, subBrandId, createdAt, updatedAt }
```

### Catalog Status Lifecycle:
```
draft → submitted → approved → active → closed → archived
```
- Only `draft` catalogs can be edited, deleted, or have products added/removed
- Submit requires at least 1 product (backend returns 422 if empty)
- `invoice_after_close` requires `buyingWindowOpensAt` and `buyingWindowClosesAt`
- `self_service` must NOT have buying window dates

### Existing Frontend Code:
- `frontend/src/types/catalogs.ts` — `Catalog`, `CatalogProduct`, `CatalogStatus`, `PaymentModel` types already exist
- `frontend/src/app/(authenticated)/catalog/page.tsx` — Employee catalog browsing (READ ONLY — do not modify)
- `frontend/src/app/(authenticated)/catalog/manage/page.tsx` — Product management from Session 1
- `frontend/src/types/products.ts` — Product types from Session 1
- `frontend/src/components/ui/StatusTag.tsx` — Status badge component

## What to Build

### 1. Catalog Management Hooks — `frontend/src/app/(authenticated)/catalog/manage/catalogs/_hooks.ts`

- `useCatalogs(page, perPage, status?)` — `GET /api/v1/catalogs/` with status filter
- `useCreateCatalog()` — `POST /api/v1/catalogs/`
- `useUpdateCatalog()` — `PATCH /api/v1/catalogs/{id}`
- `useDeleteCatalog()` — `DELETE /api/v1/catalogs/{id}`
- `useSubmitCatalog()` — `POST /api/v1/catalogs/{id}/submit`
- `useCatalogProducts(catalogId)` — `GET /api/v1/catalogs/{id}/products/`
- `useAddCatalogProduct()` — `POST /api/v1/catalogs/{id}/products/`
- `useRemoveCatalogProduct()` — `DELETE /api/v1/catalogs/{id}/products/{productId}`

### 2. Catalog List Page — `frontend/src/app/(authenticated)/catalog/manage/catalogs/page.tsx`

**Page Layout (same DataTable + Modal pattern as brands page):**
- Page header: "Catalog Management" with Catalog icon
- Status filter dropdown
- "Create Catalog" button
- DataTable columns: Name, Payment Model, Status, Buying Window, Created, Actions
- Pagination

**Create Catalog Modal:**
- Name (`TextInput`, required)
- Description (`TextArea`, optional)
- Payment Model (`Dropdown`: "Self-Service" / "Invoice After Close", required)
- Buying Window Opens (`DatePicker` — shown only when payment model is `invoice_after_close`)
- Buying Window Closes (`DatePicker` — shown only when payment model is `invoice_after_close`)
- Validation: if `invoice_after_close`, both dates required and opens < closes

**Row Actions:**
- "Manage" link → navigates to `/catalog/manage/catalogs/{id}` (detail page)
- "Edit" button → opens edit modal (draft only)
- "Delete" button → soft-delete with confirmation (draft only)
- "Submit" button → submit for approval (draft only)

### 3. Catalog Detail Page — `frontend/src/app/(authenticated)/catalog/manage/catalogs/[id]/page.tsx`

This is the key page where admins populate catalogs with products.

**Page Layout:**
- Breadcrumb: Products → Catalogs → {Catalog Name}
- Catalog info summary (name, status, payment model, dates)
- Edit button (draft only) → opens edit modal
- Status action buttons (Submit for Approval — draft only, with confirmation)

**Products in Catalog Section:**
- DataTable listing products currently in the catalog
- Columns: Product Name, SKU, Price (with override indicator), Display Order, Actions
- "Remove" button per row (draft catalogs only)

**Add Product Section (draft catalogs only):**
- Search/select products using a Carbon `ComboBox` or `FilterableMultiSelect`
  - Fetch available products via `GET /api/v1/products/?status=active` (or `approved`)
  - Filter out products already in the catalog
- On select: open a small modal/inline form for:
  - Display Order (`NumberInput`, default 0)
  - Price Override (`NumberInput`, optional — blank means use product's base price)
- Submit calls `useAddCatalogProduct()`

### 4. Navigation

Add a link from the product management page to catalog management:
- Option A: Add a "Catalogs" link in the page header area or as a tab
- Option B: Add "Manage Catalogs" to the sidebar for admin roles

The sidebar entry should go in `subBrandAdminNav` (cascades to corporate_admin):
```typescript
{ label: 'Manage Catalogs', href: '/catalog/manage/catalogs', icon: Catalog },
```

### 5. Payment Model Display

When displaying the payment model:
- `self_service` → "Self-Service"
- `invoice_after_close` → "Invoice After Close"
- For `invoice_after_close` catalogs, show the buying window dates in the table
- Use `formatDate()` helper for date formatting

## Important Notes

- The `CatalogCreate` backend schema validates that `invoice_after_close` catalogs MUST have both window dates, and `self_service` catalogs must NOT have window dates. Show/hide the date pickers based on the selected payment model.
- When showing the "Submit" action, warn the user if the catalog has 0 products (the backend will reject it anyway with 422, but a frontend guard improves UX)
- Price in the catalog products table should show the override price if set, otherwise the product's base price with "(base)" indicator
- Use Carbon `DatePicker` and `DatePickerInput` for the buying window date fields
- The API client auto-transforms keys, so send `paymentModel` (camelCase) and it becomes `payment_model` (snake_case) on the backend

## Do NOT Build
- Do NOT modify the employee-facing `/catalog` browsing page
- Do NOT build the cart or ordering flow (Session 3)
- Do NOT build platform-side catalog creation (Session 7)
