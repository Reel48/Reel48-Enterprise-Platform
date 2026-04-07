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
- **IBM Carbon** (`@carbon/react`) as the primary design system — use Carbon
  components for all standard UI elements (buttons, inputs, modals, data tables,
  dropdowns, notifications, tabs, etc.). See ADR-008 for the full rationale.
- **Tailwind CSS** as a utility layer for layout (`flex`, `grid`, `gap-*`),
  spacing between components, and custom styles where Carbon has no equivalent.
  Do NOT use Tailwind classes to override Carbon component internals.
- **SCSS** for Carbon theme customization only (`src/styles/carbon-theme.scss`).
  No standalone CSS modules or styled-components.
- **No inline style objects** except as a last resort with a justifying comment.
- **Package manager:** npm (not yarn, not pnpm)

### Next.js Configuration for Carbon SCSS

# --- ADDED 2026-04-07 during Carbon harness gap review ---
# Reason: Carbon requires SCSS compilation with specific config. Without this,
#   `npm run dev` fails immediately on SCSS import resolution.
# Impact: Prevents build failures during frontend scaffolding.

Carbon v11 requires **Dart Sass** (the `sass` npm package, NOT `node-sass`) for its
`@use` module system. Configure Next.js to resolve Carbon's SCSS imports:

**`next.config.mjs`:**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  sassOptions: {
    quietDeps: true,
  },
};

export default nextConfig;
```

**Required devDependency:**
```json
{
  "devDependencies": {
    "sass": "^1.33.0"
  }
}
```

**Key points:**
- Use `sass` (Dart Sass), NOT `node-sass` — `node-sass` does not support `@use`
- `quietDeps: true` suppresses Dart Sass deprecation warnings from Carbon's internal
  SCSS (Carbon still uses some patterns that newer Sass versions warn about)
- `includePaths: ['node_modules']` is NOT needed — Next.js resolves `node_modules`
  automatically for Sass `@use` imports
- Carbon v11 uses `@use` / `@forward` (Sass modules), NOT `@import` (deprecated)
- The tilde prefix (`~`) is NOT needed with `@use` — it is a webpack legacy pattern
- Components that import from `@carbon/react` must use the `'use client'` directive
  (Carbon React components are client components with state and event handlers)


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

### Carbon Component Usage

# --- ADDED 2026-04-06 after ADR-008 ---
# Reason: IBM Carbon adopted as primary design system, replacing custom UI primitives.
# Impact: Claude Code imports standard components from @carbon/react instead of building them.

Standard UI elements come from `@carbon/react`, not from custom implementations.
Common imports:

```typescript
import {
  Button, TextInput, NumberInput, Dropdown, ComboBox,
  Modal, DataTable, Table, TableHead, TableRow, TableCell, TableBody,
  TableHeader, TableContainer, TableToolbar, TableToolbarContent,
  Tabs, TabList, Tab, TabPanels, TabPanel,
  Tag, InlineNotification, ToastNotification,
  Breadcrumb, BreadcrumbItem, Loading, Pagination,
  SideNav, SideNavItems, SideNavLink, SideNavMenu, SideNavMenuItem,
  Grid, Column, Theme,
} from '@carbon/react';
```

Feature components in `src/components/features/` use these Carbon components
directly. There is no intermediate wrapper layer.

### Component Locations
```
src/
├── styles/
│   └── carbon-theme.scss     # Carbon SCSS variable overrides (brand colors, tokens)
├── components/
│   ├── ui/                    # Reel48+-specific reusable compositions
│   │   ├── TenantBadge.tsx    #   Built FROM Carbon primitives (Tag, etc.)
│   │   ├── EmptyState.tsx     #   For scenarios Carbon doesn't cover
│   │   ├── PageHeader.tsx     #   Consistent page header with breadcrumbs
│   │   └── StatusIndicator.tsx#   Order/invoice/approval status display
│   │                          #
│   │   NOTE: Do NOT create wrappers for Carbon components here.
│   │   Import directly from @carbon/react. This directory is for
│   │   COMPOSITE components that combine multiple Carbon primitives
│   │   with Reel48+ domain logic.
│   │
│   ├── layout/                # App shell components
│   │   ├── Sidebar.tsx        #   (uses Carbon SideNav)
│   │   ├── Header.tsx         #   (uses Carbon Header/HeaderNavigation)
│   │   └── MainLayout.tsx     #   (uses Carbon Grid + Theme provider)
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
- **`'use client'` directive:** Any component file that imports from `@carbon/react`
  MUST include `'use client'` at the top. Carbon React components use state and event
  handlers internally, making them client components. The root layout that imports
  global SCSS does NOT need this (SCSS is processed at build time).
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


## Styling Rules (Carbon + Tailwind)

# --- SUPERSEDED 2026-04-06 after ADR-008 ---
# Original: Tailwind-only styling rules with cva/clsx for component variants.
# Replaced by: Carbon-first approach with Tailwind as utility layer.
# Reason: IBM Carbon adopted as primary design system for enterprise-grade
#   components, accessibility, and design token theming. See ADR-008.

### Hierarchy: When to Use What
1. **Carbon components first.** If Carbon has a component for the UI element
   (button, input, modal, table, dropdown, notification, etc.), use it.
   Do NOT recreate these in Tailwind.
2. **Carbon props for variants.** Carbon components have built-in variant props
   (e.g., `<Button kind="primary">`, `<Button kind="danger">`). Use these
   instead of custom variant logic. cva/clsx are NOT needed.
3. **Tailwind for layout.** Use Tailwind utilities for page layout, spacing
   between components, and responsive adjustments:
   - `<div className="flex gap-4 items-center">` (layout between Carbon components)
   - `<div className="grid grid-cols-3 gap-6 mt-8">` (page grid)
   - Do NOT use: `<button className="bg-blue-500 text-white px-4 py-2">` (use Carbon Button)
4. **Carbon theme for brand customization.** Brand colors, typography scale, and
   spacing tokens are set in `src/styles/carbon-theme.scss`. Tailwind's
   `tailwind.config.ts` should reference Carbon's token values where possible
   to prevent divergence.

### Theming

# --- UPDATED 2026-04-07 — Color scheme finalized ---
# Reason: Brand color (#292c2f) and full palette defined. Replaced placeholder
#   token values with finalized Reel48+ colors. Teal interactive replaces IBM blue.
# Impact: Claude Code generates all components with the correct brand colors from
#   the first module forward. No placeholder values remain.

- **Carbon version:** Reel48+ uses `@carbon/react` v1.x (**Carbon v11**). Use v11
  token names only. Do NOT use v10 token names like `$interactive-01` or `$ui-background`.
  See `.claude/rules/carbon-design-system.md` for the full v10 → v11 token mapping.
- **Theme file:** `src/styles/carbon-theme.scss` — the **single source of truth** for
  all Reel48+ colors. Contains Carbon token overrides AND CSS custom properties for
  the accent palette. All color values originate here.
- **Theme provider:** Use Carbon's `<Theme theme="g10">` for the content area. Wrap
  the sidebar/header in `<Theme theme="g100">` for the dark brand zone.
- **Dark mode:** Not in initial scope. The sidebar uses g100 for the dark brand
  surface; the main content uses g10.

#### Brand Color System Overview

| Role | Color | Hex | Notes |
|------|-------|-----|-------|
| Brand anchor | Charcoal 900 | `#292c2f` | Header, sidebar, dark surfaces |
| Primary interactive | Teal 700 | `#0a6b6b` | Buttons, links, focus (5.07:1 vs white) |
| Interactive hover | Teal 600 | `#0d8a8a` | Hover state for interactive elements |
| Interactive on dark | Teal 400 | `#3db8b8` | Active nav on charcoal (6.8:1 contrast) |
| Info | Teal 600 | `#0d8a8a` | Info notifications (replaces Carbon default blue) |
| Error | Red 60 | `#da1e28` | Carbon default |
| Success | Green 60 | `#198038` | Carbon default |
| Warning | Yellow 30 | `#f1c21b` | Carbon default |

#### Accent Palette (Charts, Badges, Categories)
Defined as CSS custom properties in `carbon-theme.scss` and bridged into Tailwind:

| Tailwind Class | Name | Hex | Usage |
|---------------|------|-----|-------|
| `accent-amethyst` | Amethyst | `#6929c4` | Premium, featured |
| `accent-azure` | Azure | `#1192e8` | Active status |
| `accent-evergreen` | Evergreen | `#005d5d` | Approved variant |
| `accent-garnet` | Garnet | `#9f1853` | Urgent, high-priority |
| `accent-coral` | Coral | `#fa4d56` | Overdue |
| `accent-oxblood` | Oxblood | `#570408` | Rejected, cancelled |
| `accent-navy` | Navy | `#002d9c` | Processing |
| `accent-rose` | Rose | `#ee538b` | Promotional, seasonal |
| `accent-saffron` | Saffron | `#b28600` | Pending review |
| `accent-midnight-teal` | Midnight Teal | `#022b30` | Deep brand accent |

#### Theme SCSS Reference

The theme file lives at `src/styles/carbon-theme.scss`. Key structure:

```scss
// IMPORTANT: @use ... with () must appear BEFORE @use '@carbon/react'.
@use '@carbon/react/scss/themes';
@use '@carbon/react/scss/theme' with (
  $fallback: themes.$g10,
  $theme: (
    background-brand: #292c2f,    // Brand charcoal
    background-inverse: #292c2f,
    interactive: #0a6b6b,         // Teal primary
    link-primary: #0a6b6b,
    focus: #0a6b6b,
    support-info: #0d8a8a,        // Brand-aligned teal
    // ... full overrides in the actual file
  )
);

@use '@carbon/react';

:root {
  --r48-accent-amethyst: #6929c4;
  --r48-charcoal-900: #292c2f;
  --r48-teal-400: #3db8b8;
  // ... full palette in the actual file
}
```

**Global stylesheet import order** (e.g., `src/app/globals.scss`):
```scss
// 1. Carbon theme and component styles FIRST
@use '../styles/carbon-theme';

// 2. Tailwind directives AFTER Carbon
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Note on `$fallback` vs `map-merge`:** Do NOT use `map-merge(themes.$g10, (...))`
to merge theme overrides. Carbon v11's `@use ... with ($fallback, $theme)` pattern
is the canonical approach. The `$fallback` sets the base theme; `$theme` contains
only the tokens you want to override.

#### Color Usage Patterns

**Header & Sidebar** (wrapped in `<Theme theme="g100">`):
- Background: `#292c2f` (Charcoal 900)
- Active nav indicator: `#3db8b8` (Teal 400)
- Hover state: `#353a3f` (Charcoal 800)
- Dividers: `#4a5056` (Charcoal 700)
- Text: `#ffffff` (white)

**Buttons** (Carbon `<Button>` with theme-overridden interactive color):
- Primary: teal `#0a6b6b` background, white text
- Secondary: transparent with teal border/text
- Danger: `#da1e28` (Carbon `kind="danger"`)
- Ghost: transparent, teal text on hover

**Status Badges** (Carbon `<Tag>` component):
- Approved: green background tint + `#198038` text
- Pending: saffron background tint + `#b28600` text
- Urgent: garnet background tint + `#9f1853` text
- Overdue: coral background tint + `#da1e28` text
- Processing: azure background tint + `#1192e8` text
- Draft: gray background + `#525252` text
- Premium: amethyst background tint + `#6929c4` text

**Data Tables**:
- Selected row: `#e0f5f5` (Teal 50) — subtle brand-aligned highlight
- Row hover: `#e8e8e8` (layer-hover-01)

**Charts** (use accent palette in this order for max differentiation):
Amethyst → Azure → Evergreen → Garnet → Coral → Navy → Rose → Saffron

### Responsive Design

# --- UPDATED 2026-04-07 during Carbon harness gap review ---
# Reason: Original guidance was ambiguous on where Carbon Grid ends and Tailwind begins.
# Impact: Claude Code makes consistent layout decisions without guessing.

- **Page-level layout:** Use Carbon's `<Grid>` and `<Column>` components for the
  outermost page structure — the 2-column, 3-column, or full-width layout of a page.
- **Content-area layout:** Use Tailwind `flex`, `grid`, `gap` for arranging items
  WITHIN a Carbon `<Column>` — laying out cards in a grid, spacing form fields,
  aligning action buttons.
- **Decision rule:** If you are defining the top-level column breakpoints of a page,
  use Carbon Grid. If you are arranging content inside a content area, use Tailwind.
- **Responsive breakpoints:** Use Tailwind breakpoints (`sm:`, `md:`, `lg:`) for
  fine-grained responsive adjustments within Carbon Columns.
- The main app layout should work on tablets (768px+); full mobile support
  is a post-launch enhancement.

### Tailwind-Carbon Token Alignment

# --- UPDATED 2026-04-07 — Finalized with actual color scheme ---
# Reason: Color scheme defined. Replaced placeholder example with actual config reference.
# Impact: Claude Code uses the real tailwind.config.ts, no guessing at color values.

The Tailwind config (`tailwind.config.ts`) bridges Carbon tokens and the Reel48+ accent
palette via CSS custom properties. **All color values originate in `carbon-theme.scss`** —
Tailwind references `var(--cds-...)` and `var(--r48-...)` variables, never raw hex.

Three color groups are available in Tailwind:
1. **Carbon bridges** — `interactive`, `bg-page`, `text-primary`, `support-error`, etc.
2. **Charcoal/teal scales** — `charcoal-900` through `charcoal-500`, `teal-900` through `teal-50`
3. **Accent palette** — `accent-amethyst`, `accent-garnet`, `accent-saffron`, etc.

See `tailwind.config.ts` for the full mapping. The key principle: never
define raw hex colors in Tailwind config that duplicate or diverge from Carbon tokens.

### What NOT to Do
- Do NOT use Tailwind classes to style Carbon component internals (e.g.,
  adding `className="text-red-500"` to a Carbon `<TextInput>`). Use Carbon's
  props (`invalid`, `warn`) or theme tokens instead.
- Do NOT create `Button.tsx`, `Input.tsx`, `Modal.tsx`, or `DataTable.tsx`
  in `src/components/ui/`. These come from `@carbon/react`.
- Do NOT use `cva` or `clsx` for component variants. Carbon handles variants
  via props (`kind`, `size`, `type`).
- Do NOT use `dark:` Tailwind variants (dark mode is out of scope).
- Do NOT use arbitrary Tailwind values like `text-[#3B82F6]` when a Carbon
  theme token or Tailwind named token exists.


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
