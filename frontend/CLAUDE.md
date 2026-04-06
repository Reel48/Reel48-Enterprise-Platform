# Reel48+ Frontend — CLAUDE.md
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This is the FRONTEND-SPECIFIC CLAUDE.md. Claude Code reads it             ║
# ║  automatically whenever it's working on files inside the /frontend         ║
# ║  directory. It supplements the root CLAUDE.md with Next.js, TypeScript,    ║
# ║  and React-specific conventions.                                           ║
# ║                                                                            ║
# ║  WHY A SEPARATE FILE?                                                      ║
# ║                                                                            ║
# ║  The root CLAUDE.md covers project-wide concerns (multi-tenancy, API       ║
# ║  contracts, database patterns). But the frontend has its own ecosystem     ║
# ║  of conventions — component structure, routing patterns, state management, ║
# ║  auth integration — that would bloat the root file if included there.      ║
# ║  Directory-level CLAUDE.md files let you scope guidance to where it's      ║
# ║  relevant, keeping context focused and effective.                          ║
# ║                                                                            ║
# ║  Claude Code reads BOTH the root CLAUDE.md AND this file when working      ║
# ║  in /frontend, so you get the full picture without repeating yourself.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


## Framework & Configuration

# --- WHY THIS SECTION EXISTS ---
# Locks in the exact Next.js patterns to use. Next.js has two routing systems
# (Pages Router and App Router) and Claude Code might default to the older one.
# This ensures consistency.

- **Next.js 14+** with the **App Router** (NOT Pages Router)
- **TypeScript** in strict mode — no `any` types except as a last resort with a
  justifying comment
- **Tailwind CSS** for all styling — no CSS modules, no styled-components, no
  inline style objects
- **Package manager:** npm (not yarn, not pnpm)


## Authentication with Cognito

# --- WHY THIS SECTION EXISTS ---
# Auth integration is where most frontend bugs hide. Cognito via AWS Amplify
# has specific patterns that must be followed consistently. If Claude Code
# implements auth differently in different components, you'll get inconsistent
# login states, token refresh failures, and broken protected routes.

### Setup
Use **AWS Amplify** (`@aws-amplify/auth`) for Cognito integration. Configure in
`src/lib/auth/config.ts`:

```typescript
// WHY: Centralizing Amplify config ensures every component uses the same
// Cognito settings. If these were scattered across files, a pool ID change
// would require hunting down every reference.
import { Amplify } from 'aws-amplify';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
    }
  }
});
```

### Extracting Tenant Context from Tokens
The JWT token contains custom claims: `custom:company_id`, `custom:sub_brand_id`,
and `custom:role`. Extract these in the auth context provider:

```typescript
// WHY: This type ensures we never accidentally treat the role as a freeform
// string. TypeScript will catch any typo in role names at compile time.
type UserRole = 'reel48_admin' | 'corporate_admin' | 'sub_brand_admin' | 'regional_manager' | 'employee';

interface TenantContext {
  companyId: string | null;   // null for reel48_admin (cross-company platform operator)
  subBrandId: string | null;  // null for corporate_admin and reel48_admin
  role: UserRole;
  userId: string;
}
```

### Self-Registration Note
# --- ADDED 2026-04-06 after ADR-007 ---
# Reason: Self-registration via org code added as second onboarding path.
# Impact: Claude Code knows the register page exists and that post-login behavior is identical.

The `/register` page uses a **two-step flow** for self-registration:

1. **Step 1:** Employee enters their org code. Frontend calls
   `POST /api/v1/auth/validate-org-code`. On success, the company name and sub-brand
   list are returned.
2. **Step 2:** The form expands to show a **sub-brand dropdown** (pre-selected to the
   default sub-brand), plus email, full name, and password fields. If the company has
   only one sub-brand, the dropdown is hidden and that sub-brand is auto-selected.
   On submit, frontend calls `POST /api/v1/auth/register` with the org code,
   selected `sub_brand_id`, and user details.

After registration and email verification, self-registered users log in and receive the
same JWT with the same custom claims (`custom:company_id`, `custom:sub_brand_id`,
`custom:role`) as invite-registered users. **The frontend does not need to distinguish
between the two registration methods after login** — the TenantContext shape is identical.

### Protected Routes
Use a `<ProtectedRoute>` wrapper component that:
1. Checks authentication state
2. Redirects unauthenticated users to `/login`
3. Optionally checks role requirements (e.g., only `corporate_admin` can access `/admin/brands`)
4. Provides `TenantContext` via React Context to all child components

```typescript
// WHY: Centralizing route protection prevents the mistake of having some pages
// check auth and others not. Every page inside the authenticated area uses this
// wrapper, so there's exactly one place to update if the auth flow changes.
<ProtectedRoute requiredRoles={['corporate_admin', 'sub_brand_admin']}>
  <CatalogManagement />
</ProtectedRoute>
```


## Component Architecture

# --- WHY THIS SECTION EXISTS ---
# A consistent component structure means Claude Code knows exactly where to
# create new components and how to organize them. Without this, components
# end up in random locations with inconsistent naming and structure.

### Component Locations
```
src/
├── components/
│   ├── ui/                    # Generic, reusable UI primitives
│   │   ├── Button.tsx         #   (buttons, inputs, modals, cards)
│   │   ├── Input.tsx          #   These have NO business logic
│   │   ├── Modal.tsx          #   and NO awareness of Reel48+ domain
│   │   └── DataTable.tsx
│   ├── layout/                # App shell components
│   │   ├── Sidebar.tsx        #   (navigation, header, footer)
│   │   ├── Header.tsx
│   │   └── MainLayout.tsx
│   └── features/              # Feature-specific components
│       ├── auth/              #   Grouped by domain module
│       │   ├── LoginForm.tsx
│       │   └── RoleGuard.tsx
│       ├── profiles/
│       │   ├── ProfileForm.tsx
│       │   └── SizeSelector.tsx
│       ├── catalog/
│       │   ├── ProductCard.tsx
│       │   └── CatalogGrid.tsx
│       ├── orders/
│       │   ├── OrderSummary.tsx
│       │   └── CartDrawer.tsx
│       ├── invoices/
│       │   ├── InvoiceTable.tsx
│       │   ├── InvoiceDetail.tsx
│       │   └── CreateInvoiceForm.tsx
│       └── analytics/
│           ├── SpendChart.tsx
│           └── SizeDistribution.tsx
```

### Component Conventions
- **One component per file.** The filename matches the component name (PascalCase).
- **Functional components only.** No class components.
- **Props type defined inline or as a named interface** above the component:
  ```typescript
  // WHY: Named interfaces make props self-documenting and reusable.
  // Inline types are fine for simple components with 1-2 props.
  interface ProductCardProps {
    product: Product;
    onAddToCart: (productId: string) => void;
    showPrice?: boolean;  // Optional props use ?
  }

  export function ProductCard({ product, onAddToCart, showPrice = true }: ProductCardProps) {
    // ...
  }
  ```
- **Default exports for page components** (in `src/app/`), **named exports for
  everything else** (in `src/components/`).
  ```typescript
  // WHY: Next.js App Router requires default exports for page.tsx files.
  // Named exports everywhere else enable better tree-shaking and make
  // imports explicit about what they're pulling in.
  ```


## Routing Structure (App Router)

# --- WHY THIS SECTION EXISTS ---
# The App Router file-based routing needs careful planning for a multi-role
# platform. Different roles see different dashboards and have access to
# different sections. This structure ensures Claude Code generates routes
# that match the role model.

```
src/app/
├── (public)/                  # Unauthenticated routes (no layout wrapper)
│   ├── login/page.tsx
│   ├── register/page.tsx          # Self-registration via org code (ADR-007)
│   └── invite/[token]/page.tsx    # Employee invite acceptance
├── (authenticated)/           # Protected routes (auth layout wrapper)
│   ├── layout.tsx             # Wraps all auth routes with ProtectedRoute + Sidebar
│   ├── dashboard/page.tsx     # Role-aware dashboard (shows different content per role)
│   ├── profile/page.tsx       # Employee profile management
│   ├── catalog/
│   │   ├── page.tsx           # Browse catalog (employee view)
│   │   └── manage/page.tsx    # Manage catalog (admin view)
│   ├── orders/
│   │   ├── page.tsx           # Order history
│   │   ├── new/page.tsx       # New order flow
│   │   └── [id]/page.tsx      # Order detail
│   ├── bulk-orders/
│   │   ├── page.tsx           # Bulk order sessions list
│   │   ├── new/page.tsx       # Create bulk order session
│   │   └── [id]/page.tsx      # Bulk order session detail + dashboard
│   ├── invoices/
│   │   ├── page.tsx           # Invoice list (corporate_admin: company-wide, sub_brand_admin/regional_manager: brand-scoped)
│   │   └── [id]/page.tsx      # Invoice detail with PDF download
│   ├── admin/
│   │   ├── users/page.tsx     # User management (admin only)
│   │   ├── brands/page.tsx    # Sub-brand management (corporate_admin only)
│   │   ├── approvals/page.tsx # Approval queue
│   │   └── analytics/page.tsx # Analytics dashboard
│   └── settings/page.tsx      # Account settings
├── (platform)/                # Reel48 admin routes (reel48_admin only)
│   ├── layout.tsx             # Platform admin layout with reel48_admin guard
│   ├── dashboard/page.tsx     # Platform overview (all companies, revenue)
│   ├── companies/
│   │   ├── page.tsx           # All client companies list
│   │   └── [id]/page.tsx      # Company detail and management
│   ├── catalogs/
│   │   ├── page.tsx           # All catalogs across companies
│   │   ├── new/page.tsx       # Create catalog for a client company
│   │   └── [id]/
│   │       ├── page.tsx       # Catalog detail (products, pricing, approval)
│   │       └── approve/page.tsx  # Review and approve catalog
│   └── invoices/
│       ├── page.tsx           # All invoices across companies
│       ├── new/page.tsx       # Create invoice for a client company
│       └── [id]/page.tsx      # Invoice detail and management
```


## State Management

# --- WHY THIS SECTION EXISTS ---
# State management is where React apps get messy fast. This section prevents
# Claude Code from introducing a state management library (Redux, Zustand, etc.)
# when React's built-in tools are sufficient for Reel48+'s needs.

- **Server state:** Use React Query (TanStack Query) for all API data fetching,
  caching, and mutations. This handles loading states, error states, cache
  invalidation, and optimistic updates.
- **Client state:** Use React Context + useReducer for app-wide state that doesn't
  come from the API (auth state, UI preferences, sidebar open/close).
- **Form state:** Use React Hook Form for complex forms (profile editing, product
  management). Use controlled components for simple forms.
- **NO Redux, Zustand, Jotai, etc.** React Query + Context covers our needs.
  Adding another state library creates confusion about where state should live.


## API Client

# --- WHY THIS SECTION EXISTS ---
# A centralized API client ensures every request automatically includes the
# auth token and handles errors consistently. Without this, Claude Code might
# create fetch calls with different patterns in different components.

### API Naming Convention
# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: Backend uses snake_case (Python), frontend uses camelCase (TypeScript).
# Impact: Prevents confusion during API integration about key naming.

The backend API returns JSON with **snake_case** keys (`company_id`, `sub_brand_id`).
The frontend API client should transform these to **camelCase** (`companyId`, `subBrandId`)
when parsing responses, and transform back to snake_case when sending requests. Use a
utility like a custom `fetch` wrapper or a library that handles key transformation
automatically. The `TenantContext` interface above uses camelCase — this is intentional.

Create a centralized API client in `src/lib/api/client.ts` that:
1. Automatically attaches the Cognito JWT token to every request
2. Handles token refresh when a 401 is received
3. Parses responses into the standard `{ data, meta, errors }` format
4. Throws typed errors that components can catch and display

```typescript
// WHY: Every API call goes through this client, so auth token attachment
// and error handling happen in exactly one place. If we need to change
// how tokens are sent (e.g., from header to cookie), we change one file.
export const api = {
  get: <T>(url: string, params?: Record<string, string>) => fetchWithAuth<T>('GET', url, { params }),
  post: <T>(url: string, body: unknown) => fetchWithAuth<T>('POST', url, { body }),
  put: <T>(url: string, body: unknown) => fetchWithAuth<T>('PUT', url, { body }),
  patch: <T>(url: string, body: unknown) => fetchWithAuth<T>('PATCH', url, { body }),
  delete: <T>(url: string) => fetchWithAuth<T>('DELETE', url),
};
```


## Styling Rules (Tailwind)

# --- WHY THIS SECTION EXISTS ---
# Tailwind keeps styles co-located with components, but it needs conventions
# to prevent inconsistency. Without these rules, Claude Code might use
# different spacing scales, color values, or responsive patterns in different
# components.

- **Use the design system tokens** defined in `tailwind.config.ts` (brand colors,
  spacing scale, typography). Don't use arbitrary values like `text-[#3B82F6]` when
  a named token exists.
- **Responsive design:** Mobile-first. Use `sm:`, `md:`, `lg:` breakpoints.
  The main app layout should work on tablets (768px+); full mobile support
  is a post-launch enhancement.
- **Dark mode:** Not in initial scope. Don't add `dark:` variants.
- **Component variants:** Use `clsx` or `cva` (class-variance-authority) for
  components with multiple visual states (e.g., Button with primary/secondary/danger).


## Testing Approach

# --- WHY THIS SECTION EXISTS ---
# Frontend tests should verify that the UI works from the user's perspective,
# not that internal implementation details are correct. This guides Claude Code
# to write tests that remain stable across refactors.

- **Framework:** Vitest + React Testing Library
- **Philosophy:** Test what the user sees and does, not implementation details.
  - ✅ `screen.getByRole('button', { name: 'Add to Cart' })`
  - ❌ `wrapper.find('.add-to-cart-btn')`
- **API mocking:** Use MSW (Mock Service Worker) to mock API responses at the
  network level. This tests the full component lifecycle including API integration.
- **Tenant-aware tests:** Test that components correctly display or hide content
  based on the user's role and sub-brand scope.

```typescript
// WHY: MSW intercepts at the network level, so your component code doesn't
// need to know it's being tested. This means tests exercise the real API
// client, auth token handling, and error handling — not mocked versions.
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

const server = setupServer(
  http.get('/api/v1/products', () => {
    return HttpResponse.json({
      data: [mockProduct],
      meta: { page: 1, per_page: 20, total: 1 },
      errors: []
    });
  })
);
```


## Environment Variables

# --- WHY THIS SECTION EXISTS ---
# Next.js has specific rules about environment variables (NEXT_PUBLIC_ prefix
# for client-side access). If Claude Code creates an env var without the prefix,
# it will be undefined in the browser and cause hard-to-debug errors.

All client-side environment variables MUST use the `NEXT_PUBLIC_` prefix:

```env
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Cognito
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_xxxxx
NEXT_PUBLIC_COGNITO_CLIENT_ID=xxxxx

# Feature flags (if needed)
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

Server-only variables (used in API routes or server components) do NOT need the prefix.


## Performance Guidelines

# --- WHY THIS SECTION EXISTS ---
# Enterprise apps with many products and users need to be fast. These guidelines
# prevent Claude Code from generating components that work in development but
# are slow in production with real data volumes.

- **Images:** Always use `next/image` for automatic optimization and lazy loading.
- **Lists:** Virtualize any list that could exceed 50 items (use `@tanstack/react-virtual`).
- **Code splitting:** Use `next/dynamic` for heavy components not needed on initial load
  (e.g., analytics charts, rich text editors).
- **Data fetching:** Prefer server components for initial data loads. Use client
  components with React Query for interactive data that changes frequently.
