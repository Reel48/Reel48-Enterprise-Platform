# Frontend CRUD Session 3: Order Creation Flow (Cart + Checkout)
#
# PREREQUISITE: Sessions 1–2 complete (products and catalogs manageable).
# GOAL: Wire the "Add to Cart" button and build a checkout flow so employees
# can place orders from the catalog.


---
---

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 3: Cart & Checkout
# ═══════════════════════════════════════════════════════════════════════════════

Build the cart system and checkout flow so users can add products from the catalog
to a cart, configure size/decoration options, and place an order.

## Context

The catalog browsing page exists at `/catalog` with product cards that have an
"Add to Cart" button, but it's currently a TODO no-op:
```typescript
// In frontend/src/app/(authenticated)/catalog/page.tsx, line ~228:
onAddToCart={() => {
  // TODO: Add to cart implementation when ordering flow is wired up
}}
```

The backend `POST /api/v1/orders/` endpoint is fully built and tested. It accepts
a catalog ID, line items with product/size/decoration/quantity, and optional shipping
address (falls back to the employee profile address).

## What Already Exists

### Backend Order Creation API:
```
POST /api/v1/orders/
Body (snake_case — API client transforms from camelCase):
{
  catalogId: UUID,
  lineItems: [
    { productId: UUID, quantity: number, size?: string, decoration?: string }
  ],
  notes?: string,
  shippingAddressLine1?: string,
  shippingAddressLine2?: string,
  shippingCity?: string,
  shippingState?: string,
  shippingZip?: string,
  shippingCountry?: string
}

Response: OrderWithItems (order + nested lineItems)
```

**Validation rules (enforced by backend):**
- Catalog must be `active` status
- For `invoice_after_close` catalogs: buying window must be open
- Each product must exist in the catalog and be `active`
- Size (if provided) must be in the product's `sizes` list
- Decoration (if provided) must be in the product's `decorationOptions` list
- At least 1 line item required
- Quantity must be > 0

### Backend Profile API (for shipping address):
```
GET /api/v1/profiles/me → EmployeeProfile with delivery_address_* fields
```

### Frontend Code:
- `frontend/src/app/(authenticated)/catalog/page.tsx` — Catalog browsing with ProductCard components
- `frontend/src/components/features/catalog/ProductCard.tsx` — Product card with `onAddToCart` prop
- `frontend/src/types/orders.ts` — `Order`, `OrderWithItems`, `OrderLineItem`, `OrderStatus` types
- `frontend/src/types/catalogs.ts` — `Catalog`, `CatalogProduct` types
- `frontend/src/app/(authenticated)/orders/page.tsx` — Order list page (already has cancel mutation)
- `frontend/src/app/(authenticated)/orders/[id]/page.tsx` — Order detail page (read-only)

### ProductCard Props:
```typescript
interface ProductCardProps {
  product: ProductCardProduct;  // { id, name, sku, unitPrice, imageUrls?, sizes?, status? }
  catalogId?: string;
  isWishlisted?: boolean;
  wishlistItemId?: string;
  onAddToCart?: (productId: string) => void;
  showWishlist?: boolean;
}
```

## What to Build

### 1. Cart State — `frontend/src/lib/cart/CartContext.tsx`

Create a React Context + useReducer for cart state management:

```typescript
interface CartItem {
  productId: string;
  productName: string;
  sku: string;
  unitPrice: number;
  quantity: number;
  size: string | null;
  decoration: string | null;
  imageUrl: string | null;  // first image for display
}

interface CartState {
  catalogId: string | null;
  catalogName: string | null;
  items: CartItem[];
}
```

**Cart Rules:**
- All items in the cart must be from the same catalog (single catalog per cart)
- If the user adds from a different catalog, show a warning: "Your cart has items from a different catalog. Adding this will clear your cart."
- Persist to `localStorage` so the cart survives page refreshes (but NOT across sessions/logouts)
- Clear cart on logout

**Actions:**
- `addItem(catalogId, catalogName, item)` — Add or increment quantity if same product+size+decoration
- `updateQuantity(index, quantity)` — Update item quantity
- `removeItem(index)` — Remove item
- `clearCart()` — Clear all items

**Exports:**
- `CartProvider` — Context provider component
- `useCart()` — Hook to access cart state and actions
- `useCartCount()` — Hook returning total item count (for header badge)

### 2. Add-to-Cart Modal — modify `frontend/src/app/(authenticated)/catalog/page.tsx`

When `onAddToCart` is triggered on a ProductCard:

1. Open a Carbon `Modal` with:
   - Product name and price displayed
   - Size `Dropdown` (populated from `product.sizes[]`, optional if no sizes)
   - Decoration `Dropdown` (populated from `product.decorationOptions[]`, optional if no options)
   - Quantity `NumberInput` (min 1, default 1)
   - "Add to Cart" primary button
2. On submit: call `cart.addItem()` with the selected options
3. Show a `ToastNotification` confirming the item was added

**The modal needs access to the full product data** (sizes, decorationOptions).
The catalog page already fetches products via `GET /api/v1/catalogs/{id}/products/`.
The `CatalogProduct` type includes `sizes: string[]` — verify this is available.

### 3. Cart Header Badge — modify `frontend/src/components/layout/Header.tsx`

Add a cart icon with item count badge in the header:
- Use Carbon `ShoppingCart` icon (already imported in some pages)
- Show a small count badge if `cartCount > 0`
- Click navigates to `/orders/new` (checkout page)
- Only show for authenticated users (not on login/register pages)

### 4. Checkout Page — `frontend/src/app/(authenticated)/orders/new/page.tsx`

**Page Layout:**
- Breadcrumb: Orders > New Order
- Cart summary section:
  - List of cart items (product name, size, decoration, quantity, line total)
  - Subtotal calculation
  - "Edit" link per item (opens quantity/size/decoration edit inline or modal)
  - "Remove" button per item
- Shipping address section:
  - Pre-fill from profile (`GET /api/v1/profiles/me`)
  - Editable fields: addressLine1, addressLine2, city, state, zip, country
  - "Use profile address" button to reset to profile address
- Notes field (`TextArea`, optional)
- Order summary with total
- "Place Order" button (primary, calls `POST /api/v1/orders/`)

**On Submit:**
1. Build the `OrderCreate` payload from cart state + shipping address + notes
2. Call `POST /api/v1/orders/` via `api.post()`
3. On success:
   - Clear the cart
   - Show success toast
   - Navigate to `/orders/{newOrder.id}` (order detail page)
4. On error:
   - Show error notification with the backend error message
   - Common errors: catalog not active, buying window closed, product not in catalog

**Empty Cart State:**
- If cart is empty, show an empty state message with a link to `/catalog`

### 5. Provider Integration

Wrap the app with `CartProvider`. Add it to the providers in:
- `frontend/src/app/(authenticated)/layout.tsx` — inside the authenticated layout

The cart should only exist within the authenticated context (not on login/register pages).

### 6. Order Creation Hook — colocate or add to a shared hooks file

```typescript
function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: OrderCreatePayload) => {
      const res = await api.post<OrderWithItems>('/api/v1/orders/', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}
```

## Important Notes

- The cart is CLIENT-SIDE ONLY — there is no backend cart API. The backend receives the complete order in a single POST.
- Products in the cart should store the `unitPrice` at the time of adding. The actual price charged is determined by the backend (catalog price_override > product price), so the cart price is an estimate.
- For `localStorage` persistence, serialize the cart state to JSON. On hydration, read from localStorage. Use `useEffect` to avoid SSR mismatches.
- The `ProductCard` component already renders an "Add to Cart" button. You just need to wire the `onAddToCart` callback to open the modal.
- Be careful with the catalog page's data flow — it renders `ProductCard` inside a catalog browsing flow where the `catalogId` is available.

## Do NOT Build
- Do NOT build order status actions (approve, ship, etc.) — that's Session 4
- Do NOT modify the order detail page — that's Session 4
- Do NOT build any backend changes — all APIs exist
