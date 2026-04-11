# Frontend CRUD Session 5: Approval Rules + Sub-Brand Edit/Delete
#
# PREREQUISITE: Sessions 1–4 complete (products, catalogs, ordering, and order actions).
# GOAL: Build the approval rules management page and add edit/delete to the
# existing sub-brands page.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 5: Approval Rules + Sub-Brand Edit/Delete
# ═══════════════════════════════════════════════════════════════════════════════

This session has two independent parts:
- **Part A:** Build a new Approval Rules management page
- **Part B:** Add Edit and Delete capabilities to the existing Sub-Brands page

## Part A: Approval Rules Management

### Context

The backend has full CRUD for approval rules, but there is NO frontend page for
managing them. Approval rules define when orders/bulk orders above a certain dollar
threshold require higher-level approval.

### What Already Exists

#### Backend APIs (all tested and working):
```
POST   /api/v1/approval_rules/       — Create rule (corporate_admin+)
GET    /api/v1/approval_rules/       — List rules (corporate_admin+), paginated with filters
PATCH  /api/v1/approval_rules/{id}   — Update rule (corporate_admin+)
DELETE /api/v1/approval_rules/{id}   — Soft-delete/deactivate rule (corporate_admin+)
```

#### Backend Schemas:
```
ApprovalRuleCreate: {
  entityType: 'order' | 'bulk_order',
  ruleType: 'amount_threshold',
  thresholdAmount: number (>= 0),
  requiredRole: 'corporate_admin' | 'sub_brand_admin' | 'regional_manager'
}

ApprovalRuleUpdate: {
  thresholdAmount?: number,
  requiredRole?: string,
  isActive?: boolean
}

ApprovalRuleResponse: {
  id, companyId, entityType, ruleType, thresholdAmount, requiredRole,
  isActive, createdBy, createdAt, updatedAt
}
```

**Business Rules:**
- `entityType` options: `order`, `bulk_order`
- `ruleType` is always `amount_threshold` (only type currently)
- `requiredRole` determines the minimum role needed to approve when the threshold is exceeded
- Only `corporate_admin` and `reel48_admin` can manage rules
- One rule per `(company_id, entity_type, rule_type)` — UNIQUE constraint
- Rules apply company-wide (no sub-brand scoping on approval_rules)

#### Frontend:
- `frontend/src/app/(authenticated)/admin/approvals/page.tsx` — Approval queue page (view/approve/reject pending requests). This is NOT the rules page.
- `frontend/src/app/(authenticated)/admin/brands/page.tsx` — Reference pattern for DataTable + Create modal
- `frontend/src/components/layout/Sidebar.tsx` — Navigation structure

### What to Build

#### 1. Approval Rules Hooks — `frontend/src/app/(authenticated)/admin/approval-rules/_hooks.ts`

- `useApprovalRules(page, perPage)` — `GET /api/v1/approval_rules/`
- `useCreateApprovalRule()` — `POST /api/v1/approval_rules/`
- `useUpdateApprovalRule()` — `PATCH /api/v1/approval_rules/{id}`
- `useDeleteApprovalRule()` — `DELETE /api/v1/approval_rules/{id}`

All mutations should invalidate `['approval-rules']` queries on success.

#### 2. Approval Rules Page — `frontend/src/app/(authenticated)/admin/approval-rules/page.tsx`

**Page Layout (DataTable + Modal pattern):**
- Page header: "Approval Rules" with appropriate icon
- "Create Rule" button (top-right)
- DataTable columns: Entity Type, Threshold Amount, Required Role, Active, Created, Actions
- Pagination

**Create Rule Modal:**
- Entity Type (`Dropdown`: "Order" / "Bulk Order", required)
- Threshold Amount (`NumberInput`, required, min 0, formatted as currency)
- Required Role (`Dropdown`: "Corporate Admin" / "Sub-Brand Admin" / "Regional Manager", required)
- Validation: all fields required
- Note: `ruleType` is always `amount_threshold` — send it automatically, don't show to user

**Edit Rule Modal:**
- Same form, pre-populated
- Only `thresholdAmount`, `requiredRole`, and `isActive` are editable
- `entityType` and `ruleType` are NOT editable after creation (show as read-only text)
- Add an `isActive` toggle (`Toggle` component)

**Row Actions:**
- "Edit" button → opens edit modal
- "Deactivate"/"Activate" toggle button → calls `PATCH` with `{ isActive: false/true }`
- "Delete" button → soft-delete with confirmation modal

**Display formatting:**
- `entityType`: `order` → "Order", `bulk_order` → "Bulk Order"
- `requiredRole`: `corporate_admin` → "Corporate Admin", `sub_brand_admin` → "Sub-Brand Admin", `regional_manager` → "Regional Manager"
- `thresholdAmount`: Currency format (`$500.00`)
- `isActive`: Green "Active" / Gray "Inactive" tag

#### 3. Navigation

Add sidebar entry for corporate_admin+ roles:
```typescript
{ label: 'Approval Rules', href: '/admin/approval-rules', icon: Rule },
```

Place it near the existing "Approvals" link in the admin navigation section.
Use the Carbon `Rule` or `Policy` icon.

---

## Part B: Sub-Brand Edit/Delete

### Context

The sub-brands management page at `/admin/brands` currently has a "Create Sub-Brand"
modal and a list of sub-brands, but there is NO way to edit or delete a sub-brand.

### What Already Exists

#### Backend APIs:
```
PATCH  /api/v1/sub_brands/{id}  — Update sub-brand (name, is_active)
DELETE /api/v1/sub_brands/{id}  — Soft-delete (non-default brands only)
```

#### Backend Schemas:
```
SubBrandUpdate: { name?: string, isActive?: boolean }
```

#### Frontend:
- `frontend/src/app/(authenticated)/admin/brands/page.tsx` — DataTable with Create modal
- Already has `useCreateSubBrand()` hook pattern

### What to Build

#### 1. Add Hooks

Add to the existing brands page (or extract to a `_hooks.ts` file):

- `useUpdateSubBrand()` — `PATCH /api/v1/sub_brands/{id}` with `{ name }` body
- `useDeleteSubBrand()` — `DELETE /api/v1/sub_brands/{id}`

Both should invalidate `['sub-brands']` queries on success.

#### 2. Edit Sub-Brand Modal

- Same form as Create (just a name `TextInput`), pre-populated with current name
- Submit calls `useUpdateSubBrand()`
- On success: close modal, show success toast

#### 3. Delete Sub-Brand

- "Delete" button in the actions column (only for non-default sub-brands)
- Confirmation modal: "Are you sure you want to delete {brand name}? This cannot be undone."
- Submit calls `useDeleteSubBrand()`
- The default sub-brand (`is_default === true`) should NOT show a delete button
- On success: show success toast, refetch list

#### 4. Row Actions Update

Update the DataTable actions column to show:
- "Edit" button for all sub-brands
- "Delete" button for non-default sub-brands only
- Keep any existing "Deactivate" functionality

## Important Notes

- The brands page uses the Carbon DataTable + Modal pattern — follow the existing style
- The approval rules page should follow the exact same Carbon DataTable + Modal pattern
- Approval rules are company-wide (no sub-brand scoping), so the API doesn't accept or return `sub_brand_id`
- The API client auto-transforms keys: send `entityType` (camelCase) and it becomes `entity_type` (snake_case) on the backend
- Role-gate both pages: approval rules requires `corporate_admin` or above, brands page already has role gating

## Do NOT Build

- Do NOT modify the approval queue page (already working at `/admin/approvals`)
- Do NOT build new approval request creation (that's triggered automatically by the backend)
- Do NOT modify any backend code
