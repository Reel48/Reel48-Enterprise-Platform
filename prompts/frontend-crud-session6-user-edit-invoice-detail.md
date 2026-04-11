# Frontend CRUD Session 6: User Management Enhancement + Invoice Detail
#
# PREREQUISITE: Sessions 1–4 complete. Independent of Session 5.
# GOAL: Add user role/sub-brand editing, and build the tenant invoice detail page.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 6: User Edit + Tenant Invoice Detail
# ═══════════════════════════════════════════════════════════════════════════════

This session has two independent parts:
- **Part A:** Add role and sub-brand editing to the Users management page
- **Part B:** Build the tenant-facing invoice detail page

## Part A: User Management Enhancement

### Context

The admin users page at `/admin/users` lists users and supports deactivation, but
there is NO way to edit a user's role or reassign them to a different sub-brand.
The backend `PATCH /api/v1/users/{id}` endpoint supports both operations.

### What Already Exists

#### Backend API:
```
PATCH /api/v1/users/{id}
Body: {
  fullName?: string,
  role?: string,        — 'corporate_admin' | 'sub_brand_admin' | 'regional_manager' | 'employee'
  subBrandId?: UUID,    — reassign to a different sub-brand
  isActive?: boolean
}

Response: UserResponse { id, companyId, subBrandId, email, fullName, role, registrationMethod, isActive, companyName, createdAt, updatedAt }
```

**Business Rules:**
- Only `corporate_admin` and `reel48_admin` can edit users
- Cannot change a user's email (immutable, tied to Cognito)
- `role` change also updates the user's Cognito custom attributes (backend handles this)
- `subBrandId` reassignment updates both the database and Cognito
- Setting `subBrandId` to null makes the user a company-wide user (for corporate_admin role)

#### Frontend:
- `frontend/src/app/(authenticated)/admin/users/page.tsx` — Tabbed page (Users, Invites, Org Code)
- `frontend/src/app/(authenticated)/admin/users/_hooks.ts` — Hooks for users, invites, org codes
- `frontend/src/app/(authenticated)/admin/users/_types.ts` — User, Invite, OrgCode types

The Users tab currently shows a DataTable with columns for name, email, role, sub-brand,
status, and an actions column with a deactivate/reactivate button.

### What to Build

#### 1. Add `useUpdateUser` Hook — modify `_hooks.ts`

```typescript
function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, data }: { userId: string; data: UserUpdatePayload }) => {
      const res = await api.patch<User>(`/api/v1/users/${userId}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
```

#### 2. Edit User Modal

Add an "Edit" button to each user row in the DataTable that opens a modal with:

- **Full Name** (`TextInput`, pre-populated, editable)
- **Email** (displayed as read-only text — not editable)
- **Role** (`Dropdown` with options):
  - "Employee" (`employee`)
  - "Regional Manager" (`regional_manager`)
  - "Sub-Brand Admin" (`sub_brand_admin`)
  - "Corporate Admin" (`corporate_admin`)
  - Note: `reel48_admin` should NOT appear as an option (platform admin is set internally)
- **Sub-Brand** (`Dropdown`, fetched from `GET /api/v1/sub_brands/`):
  - Shows list of active sub-brands in the company
  - For `corporate_admin` role: show "All Sub-Brands (Company-wide)" option that sets `subBrandId` to null
  - For other roles: sub-brand is required
- **Active** (`Toggle`, current state)

**Conditional logic:**
- When the user selects "Corporate Admin" as the role, the sub-brand dropdown should
  show "All Sub-Brands (Company-wide)" as selected and be disabled (corporate admins
  have null sub_brand_id)
- When switching FROM corporate_admin to another role, require a sub-brand selection

**On submit:**
- Only send fields that have actually changed (compare against original values)
- Call `useUpdateUser()` with the changed fields
- On success: close modal, show success toast

#### 3. Sub-Brand Dropdown Data

The edit modal needs a list of sub-brands. Either:
- Reuse an existing `useSubBrands()` hook if one exists in `_hooks.ts`
- Or create one: `GET /api/v1/sub_brands/` returns the list

#### 4. Update Row Actions

The existing actions column has a deactivate button. Add an "Edit" button
alongside it (before the deactivate button):
- Use a `Button kind="ghost" size="sm"` with an Edit icon
- Or use an `OverflowMenu` with "Edit" and "Deactivate" menu items

---

## Part B: Tenant Invoice Detail Page

### Context

The invoices list page at `/invoices` exists and shows a DataTable of invoices with
status, amount, billing flow, and date columns. However, clicking an invoice row has
nowhere to go — there is NO detail page. The backend `GET /api/v1/invoices/{id}`
endpoint returns full invoice details.

### What Already Exists

#### Backend APIs:
```
GET /api/v1/invoices/{id}
Response: InvoiceResponse {
  id, companyId, subBrandId, orderId, bulkOrderId, catalogId,
  stripeInvoiceId, stripeInvoiceUrl, stripePdfUrl, invoiceNumber,
  billingFlow, status, totalAmount, currency, dueDate,
  buyingWindowClosesAt, createdBy, paidAt, createdAt, updatedAt
}

GET /api/v1/invoices/{id}/pdf
Response: { url: string }  — Stripe-hosted PDF URL
```

#### Frontend:
- `frontend/src/app/(authenticated)/invoices/page.tsx` — Invoice list page with DataTable
- `frontend/src/types/invoices.ts` — `Invoice`, `InvoiceStatus` types

### What to Build

#### 1. Invoice Detail Page — `frontend/src/app/(authenticated)/invoices/[id]/page.tsx`

**Page Layout:**
- Breadcrumb: Invoices > {Invoice Number or "Invoice"}
- Header with invoice number, status tag, and billing flow tag
- Summary tiles section (3-4 tiles in a grid)
- Detail section
- Action links section

**Summary Tiles (Carbon `Tile` components):**
- **Total Amount** — formatted as currency
- **Status** — with color-coded `StatusTag`
- **Billing Flow** — "Assigned" / "Self-Service" / "Post-Window"
- **Due Date** — formatted date, or "—" if not set

**Detail Section (Carbon `Tile` or `StructuredList`):**
- Invoice Number (from Stripe, may be null for drafts)
- Created date
- Paid date (if applicable)
- Currency
- Related Order link (if `orderId` is set → link to `/orders/{orderId}`)
- Related Bulk Order link (if `bulkOrderId` is set → link to `/bulk-orders/{bulkOrderId}`)
- Buying Window Closes At (if `buyingWindowClosesAt` is set, for post-window invoices)

**Action Links:**
- "View on Stripe" button → opens `stripeInvoiceUrl` in a new tab (if available)
- "Download PDF" button → calls `GET /api/v1/invoices/{id}/pdf`, opens the returned URL in a new tab
- Both buttons should be disabled if the URL is not available (draft invoices may not have them)

**Status Color Mapping** (reuse from the list page):
- `paid` → green
- `sent` → blue
- `finalized` → teal
- `draft` → purple
- `payment_failed` / `voided` → red

**Billing Flow Display:**
- `assigned` → "Assigned"
- `self_service` → "Self-Service"
- `post_window` → "Post-Window"

#### 2. Link from Invoice List

Update the invoice list page to make invoice rows clickable:
- Add a link in the invoice number or a "View" action button
- Navigate to `/invoices/{id}`

#### 3. Data Hook

```typescript
function useInvoice(invoiceId: string) {
  return useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: async () => {
      const res = await api.get<Invoice>(`/api/v1/invoices/${invoiceId}`);
      return res.data;
    },
  });
}

function useInvoicePdf(invoiceId: string) {
  return useMutation({
    mutationFn: async () => {
      const res = await api.get<{ url: string }>(`/api/v1/invoices/${invoiceId}/pdf`);
      return res.data;
    },
  });
}
```

## Important Notes

- The User edit modal must handle the corporate_admin ↔ sub-brand relationship correctly:
  corporate_admin gets `subBrandId: null`, other roles require a sub-brand
- The invoice detail page is READ-ONLY for tenant users — no create/edit/send/void actions
  (those are reel48_admin-only platform operations)
- Invoice amounts are stored in dollars (not cents) in the database — no conversion needed
- The `stripeInvoiceUrl` and `stripePdfUrl` may be null for draft invoices
- Use the same `formatPrice()` and `formatDate()` helpers that exist in other pages
- The invoice types in `frontend/src/types/invoices.ts` should already have all needed fields

## Do NOT Build

- Do NOT add invoice creation/editing (that's reel48_admin-only, done from platform pages)
- Do NOT modify the platform invoice pages
- Do NOT build user creation (that's done via invites, which already work)
- Do NOT modify any backend code
