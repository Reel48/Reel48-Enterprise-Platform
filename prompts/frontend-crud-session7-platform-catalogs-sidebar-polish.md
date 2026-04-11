# Frontend CRUD Session 7: Platform Catalog Creation + Sidebar Polish
#
# PREREQUISITE: Sessions 1–2 complete (tenant catalog management working).
# GOAL: Add "Create Catalog" to the platform catalogs page and do a final
# sidebar navigation audit.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 7: Platform Catalog Creation + Sidebar Polish
# ═══════════════════════════════════════════════════════════════════════════════

This session has two parts:
- **Part A:** Add catalog creation to the platform admin catalogs page
- **Part B:** Final sidebar navigation audit to ensure all pages are reachable

## Part A: Platform Catalog Creation

### Context

The platform catalogs page at `/platform/catalogs` lists all catalogs across all
companies and has action buttons for approve, reject, activate, and close. However,
there is NO way for a `reel48_admin` to create a new catalog for a client company.
The backend `POST /api/v1/platform/catalogs/` endpoint supports this.

### What Already Exists

#### Backend API:
```
POST /api/v1/platform/catalogs/
Body: {
  companyId: UUID,           — Target client company (required, since reel48_admin has no company)
  subBrandId?: UUID,         — Target sub-brand within the company (optional)
  name: string,
  description?: string,
  paymentModel: 'self_service' | 'invoice_after_close',
  buyingWindowOpensAt?: datetime,    — Required for invoice_after_close
  buyingWindowClosesAt?: datetime    — Required for invoice_after_close
}

Response: ApiResponse[CatalogResponse]
```

**Existing platform endpoints also used:**
```
GET /api/v1/platform/companies/       — List all companies (for the company selector)
GET /api/v1/platform/companies/{id}   — Company detail (includes sub-brands if needed)
```

#### Frontend:
- `frontend/src/app/(platform)/platform/catalogs/page.tsx` — Platform catalog list with status filter, approve/reject/activate/close actions
- `frontend/src/types/catalogs.ts` — `Catalog`, `CatalogStatus`, `PaymentModel` types

### What to Build

#### 1. Company List Hook

Add a hook to fetch companies for the dropdown:

```typescript
function usePlatformCompanies() {
  return useQuery({
    queryKey: ['platform-companies'],
    queryFn: async () => {
      const res = await api.get<Company[]>('/api/v1/platform/companies/', {
        per_page: '100',  // Reasonable max for dropdown
      });
      return res.data;
    },
  });
}
```

#### 2. Create Catalog Mutation

```typescript
function useCreatePlatformCatalog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PlatformCatalogCreate) => {
      const res = await api.post<Catalog>('/api/v1/platform/catalogs/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform-catalogs'] });
    },
  });
}
```

#### 3. Create Catalog Modal

Add a "Create Catalog" button to the page header/toolbar area and a modal with:

- **Company** (`Dropdown`, required):
  - Populated from `usePlatformCompanies()`
  - Display company name, value is company ID
- **Name** (`TextInput`, required)
- **Description** (`TextArea`, optional)
- **Payment Model** (`Dropdown`, required):
  - "Self-Service" (`self_service`)
  - "Invoice After Close" (`invoice_after_close`)
- **Buying Window Opens** (`DatePicker` — shown ONLY when payment model is `invoice_after_close`)
- **Buying Window Closes** (`DatePicker` — shown ONLY when payment model is `invoice_after_close`)

**Conditional logic:**
- When `self_service` is selected: hide the date pickers
- When `invoice_after_close` is selected: show both date pickers, both required
- Validate that opens date is before closes date
- The backend enforces these rules too, but frontend validation improves UX

**On submit:**
- Build the payload with `companyId` from the selected company
- If `self_service`, do NOT send the date fields
- Call `useCreatePlatformCatalog()`
- On success: close modal, show success toast, refetch list

#### 4. Sub-Brand Selector (Optional Enhancement)

If the selected company has multiple sub-brands, optionally show a sub-brand dropdown.
This is NOT required by the backend (sub_brand_id is optional on catalog creation),
but it improves the UX for targeting a specific sub-brand.

If you include this:
- After a company is selected, fetch its sub-brands
- Show a `Dropdown` with "All Sub-Brands" as the default + individual sub-brand options
- Pass `subBrandId` in the request if a specific sub-brand is selected

---

## Part B: Sidebar Navigation Audit

### Context

Multiple pages have been added across Sessions 1–6. The sidebar needs to be audited
to ensure every page is reachable from the navigation.

### What to Verify

Check `frontend/src/components/layout/Sidebar.tsx` and confirm that ALL of these
pages have corresponding sidebar entries in the appropriate role-based nav arrays:

#### Employee Navigation (`employeeNav`):
- Dashboard → `/dashboard`
- Catalog → `/catalog`
- Orders → `/orders`
- Wishlist → `/wishlist`
- Notifications → `/notifications`
- Profile → `/profile`

#### Regional Manager Navigation (`regionalManagerNav` — extends employeeNav):
- Everything in employeeNav
- Bulk Orders → `/bulk-orders`
- Approvals → `/admin/approvals`

#### Sub-Brand Admin Navigation (`subBrandAdminNav` — extends regionalManagerNav):
- Everything in regionalManagerNav
- Manage Products → `/catalog/manage` (Session 1)
- Manage Catalogs → `/catalog/manage/catalogs` (Session 2)
- Invoices → `/invoices`

#### Corporate Admin Navigation (`corporateAdminNav` — extends subBrandAdminNav):
- Everything in subBrandAdminNav
- Users → `/admin/users`
- Sub-Brands → `/admin/brands`
- Approval Rules → `/admin/approval-rules` (Session 5)
- Analytics → `/admin/analytics`

#### Platform Admin Navigation (`platformAdminNav`):
- Platform Dashboard → `/platform/dashboard`
- Companies → `/platform/companies`
- Catalogs → `/platform/catalogs`
- Invoices → `/platform/invoices`
- Orders → `/platform/orders` (if this page exists)
- Bulk Orders → `/platform/bulk-orders` (if this page exists)
- Approvals → `/platform/approvals` (if this page exists)

### What to Fix

For any page that exists but is NOT in the sidebar:
1. Add the appropriate nav entry with a Carbon icon
2. Place it in the correct role-based nav array
3. Ensure the nav hierarchy cascades correctly (corporate extends sub-brand extends regional extends employee)

### Sidebar Icon Consistency

Use Carbon icons consistently:
- Dashboard → `Dashboard`
- Catalog/Products → `Catalog`
- Orders → `ShoppingCart`
- Bulk Orders → `ShoppingCartPlus` or `Box`
- Invoices → `Receipt`
- Users → `UserMultiple` or `Group`
- Sub-Brands → `Tag` or `Enterprise`
- Approval Rules → `Rule` or `Policy`
- Approvals → `CheckmarkOutline` or `TaskComplete`
- Analytics → `Analytics` or `ChartLineData`
- Notifications → `Notification`
- Wishlist → `Favorite`
- Profile → `UserAvatar`
- Settings → `Settings`

## Important Notes

- The platform catalog creation requires the company dropdown — this is the key
  difference from tenant catalog creation (Session 2) where the company comes from JWT
- Use Carbon `DatePicker` and `DatePickerInput` for the buying window dates
- The API client auto-transforms keys between camelCase and snake_case
- The sidebar component may use different nav array patterns — read the existing code first
- When adding sidebar entries, respect the existing icon import style and nav structure

## Do NOT Build

- Do NOT modify tenant-side catalog management (Session 2)
- Do NOT add platform invoice creation here (that already exists at `/platform/invoices`)
- Do NOT modify any backend code
