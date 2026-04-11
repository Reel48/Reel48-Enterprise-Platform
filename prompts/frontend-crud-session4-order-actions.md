# Frontend CRUD Session 4: Order Status Actions
#
# PREREQUISITE: Sessions 1–3 complete (products, catalogs, and cart/checkout working).
# GOAL: Add role-aware status transition buttons so managers can advance orders
# through the lifecycle: approve, process, ship, deliver.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 4: Order Status Actions
# ═══════════════════════════════════════════════════════════════════════════════

Add role-aware action buttons to the order detail and order list pages so
managers and admins can advance orders through their lifecycle.

## Context

The order list page (`/orders`) and order detail page (`/orders/[id]`) exist and
are functional for viewing orders. The list page has a cancel mutation, and the
detail page has a "Cancel Order" button for pending orders. However, there are
NO buttons for approve, process, ship, or deliver — managers currently cannot
advance orders through the fulfillment pipeline.

The backend has all status transition endpoints fully built and tested.

## What Already Exists

### Backend Order Status Transition APIs:
```
POST /api/v1/orders/{order_id}/approve   — Requires manager_or_above
POST /api/v1/orders/{order_id}/process   — Requires manager_or_above
POST /api/v1/orders/{order_id}/ship      — Requires manager_or_above
POST /api/v1/orders/{order_id}/deliver   — Requires manager_or_above
POST /api/v1/orders/{order_id}/cancel    — Owner or manager_or_above

Response: ApiResponse[OrderResponse] (updated order object)
```

No request body is needed for any of these endpoints — they are simple POST actions.

### Order Status Lifecycle:
```
pending → approved → processing → shipped → delivered
pending → cancelled        (owner or manager_or_above)
approved → cancelled       (manager_or_above only)
```
- Processing, shipped, and delivered orders CANNOT be cancelled
- Cancelled and delivered are terminal states

### Frontend Code:
- `frontend/src/app/(authenticated)/orders/page.tsx` — Order list with DataTable, status filter, cancel mutation
- `frontend/src/app/(authenticated)/orders/[id]/page.tsx` — Order detail with cancel button (pending only)
- `frontend/src/types/orders.ts` — `Order`, `OrderWithItems`, `OrderLineItem`, `OrderStatus` types
- `frontend/src/types/auth.ts` — `UserRole` type
- `frontend/src/lib/auth/hooks.ts` — `useAuth()` hook providing `user.tenantContext.role`

### Existing Patterns in the Orders Pages:
The list page already has:
- `MANAGER_AND_ABOVE` role array: `['reel48_admin', 'corporate_admin', 'sub_brand_admin', 'regional_manager']`
- `useCancelOrder()` mutation hook
- Role check: `const isManager = MANAGER_AND_ABOVE.includes(role)`

The detail page already has:
- `useCancelOrder()` mutation hook
- Cancel button shown only when `order.status === 'pending'`

## What to Build

### 1. Status Transition Hooks — add to existing pages (colocated)

Add mutation hooks for each status transition. These follow the same pattern as
the existing `useCancelOrder()`:

```typescript
function useApproveOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (orderId: string) => {
      const res = await api.post<Order>(`/api/v1/orders/${orderId}/approve`);
      return res.data;
    },
    onSuccess: (_data, orderId) => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

// Same pattern for: useProcessOrder, useShipOrder, useDeliverOrder
```

You can colocate these hooks in each page file (they're already doing this for
`useCancelOrder`), or extract them to a shared `_hooks.ts` file in the orders directory.

### 2. Order Detail Page Actions — modify `frontend/src/app/(authenticated)/orders/[id]/page.tsx`

**Replace the existing cancel-only button section** with a full action bar that shows
role-appropriate buttons based on the order's current status:

**Action Button Logic:**
| Order Status | Employee Sees | Manager+ Sees |
|-------------|---------------|---------------|
| `pending` | Cancel | Approve, Cancel |
| `approved` | *(nothing)* | Process, Cancel |
| `processing` | *(nothing)* | Ship |
| `shipped` | *(nothing)* | Deliver |
| `delivered` | *(nothing)* | *(nothing — terminal)* |
| `cancelled` | *(nothing)* | *(nothing — terminal)* |

**Implementation:**
- Use `useAuth()` to check the user's role
- Show a `Button kind="primary"` for the forward-progress action (Approve, Process, Ship, Deliver)
- Show a `Button kind="danger--ghost"` for Cancel (when available)
- Add a confirmation step for **Approve** and **Cancel** actions:
  - Use a Carbon `Modal` with a brief confirmation message
  - "Are you sure you want to approve this order?" / "Are you sure you want to cancel this order?"
  - Primary button confirms, secondary button cancels the modal
- Process, Ship, and Deliver can be direct actions without confirmation (they're less destructive)
- Show a `ToastNotification` on success with the action result
- Disable buttons while mutations are pending (`isPending`)
- On success, the `useOrder` query is invalidated and the page refreshes with the new status

**Visual Layout:**
Place the action buttons in the existing header area (next to the current Cancel button).
Use a `flex gap-3` layout for multiple buttons.

### 3. Order List Page Quick Actions — modify `frontend/src/app/(authenticated)/orders/page.tsx`

Add quick-action buttons in the Actions column of the DataTable for managers:

**For each row, show the next available action based on status:**
- `pending` → "Approve" button (small, primary) + "Cancel" button (small, danger--ghost)
- `approved` → "Process" button (small, primary)
- `processing` → "Ship" button (small, primary)
- `shipped` → "Deliver" button (small, primary)
- `delivered` / `cancelled` → No action buttons

**Implementation:**
- Only show action buttons if `isManager` is true
- For employees: keep the existing cancel button for pending orders only
- Use `Button size="sm"` for compact table row buttons
- Use the same mutation hooks as the detail page
- Quick actions in the list do NOT need confirmation modals (too disruptive for list views)
- Show toast notifications on success/error

**Update the Actions column rendering:**
Currently the actions column shows a cancel button. Replace/extend this to show
the appropriate action button based on status and role.

### 4. Toast Notification Pattern

Add a toast state to both pages for mutation feedback:

```typescript
const [toast, setToast] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

// In mutation callbacks:
onSuccess: () => {
  setToast({ kind: 'success', message: 'Order approved successfully' });
  setTimeout(() => setToast(null), 3000);
},
onError: () => {
  setToast({ kind: 'error', message: 'Failed to approve order' });
  setTimeout(() => setToast(null), 3000);
},
```

Render the toast at the top of the page:
```typescript
{toast && (
  <ToastNotification
    kind={toast.kind}
    title={toast.kind === 'success' ? 'Success' : 'Error'}
    subtitle={toast.message}
    onClose={() => setToast(null)}
    timeout={3000}
  />
)}
```

## Important Notes

- The order detail page already invalidates `['order', orderId]` in the cancel
  mutation — follow the same pattern for all new mutations
- Employees should NEVER see approve/process/ship/deliver buttons, even if the
  backend would reject their request with 403
- The `useAuth()` hook returns `user?.tenantContext.role` — use this for role checks
- The backend approve endpoint also syncs with the approval_requests table if an
  approval record exists — this is transparent to the frontend
- Keep the existing `useCancelOrder()` hooks — don't duplicate them, reuse them

## Do NOT Build

- Do NOT modify the order creation flow (Session 3)
- Do NOT build bulk order actions (those are already working)
- Do NOT build approval queue UI (Session 5)
- Do NOT add notes/comments to status transitions (backend doesn't accept them
  on status endpoints, only on cancel via the approval system)
