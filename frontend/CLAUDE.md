# Reel48+ Frontend — CLAUDE.md

> ⚠ **SIMPLIFICATION IN PROGRESS** — see `~/.claude/plans/yes-please-write-the-memoized-karp.md`.
> Stale content has been removed: the two-step self-registration flow, 5-role authentication
> examples, and routing tables for catalog/orders/bulk-orders/wishlist/invoices/approvals/brands
> pages. Those pages are being deleted in Session B. This file will be rewritten authoritatively
> in Session D. Until then, do **not** reintroduce a sub-brand dropdown in registration, the
> `sub_brand_admin` / `regional_manager` role strings, or routes under `/catalog`, `/orders`,
> `/bulk-orders`, `/wishlist`, `/invoices`, `/admin/approvals`, `/admin/approval-rules`, or
> `/admin/brands`.


## Framework & Configuration

- **Next.js 14+** with the **App Router** (NOT Pages Router).
- **TypeScript** in strict mode — no `any` except as a last resort with justifying comment.
- **IBM Carbon** (`@carbon/react`) as the primary design system. See
  [.claude/rules/carbon-design-system.md](.claude/rules/carbon-design-system.md).
- **Tailwind CSS** as a utility layer for layout + spacing only; never to override Carbon
  component internals.
- **SCSS** for Carbon theme customization only (`src/styles/carbon-theme.scss`).
- **Package manager:** npm.

### Next.js Configuration for Carbon SCSS
Carbon v11 requires **Dart Sass** (`sass` package, NOT `node-sass`). Next.js config:

```javascript
// next.config.mjs
const nextConfig = {
  reactStrictMode: true,
  sassOptions: { quietDeps: true },
};
export default nextConfig;
```

Any component file that imports from `@carbon/react` must include `'use client'` at the top.


## Authentication with Cognito

### Setup (stable)
Use **AWS Amplify v6**. Configure in `src/lib/auth/config.ts`:

```typescript
import { Amplify } from 'aws-amplify';

export function configureAmplify() {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
        userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '',
      },
    },
  });
}
```

### Amplify v6 Auth API (stable)
```typescript
import {
  getCurrentUser,      // throws if no session
  fetchAuthSession,    // returns { tokens?: { idToken?, accessToken? } }
  signIn,
  signOut,
} from 'aws-amplify/auth';
```
- `getCurrentUser()` **throws** when no user is signed in (wrap in try/catch).
- `fetchAuthSession({ forceRefresh: true })` forces token refresh.
- Custom claims are on `idToken.payload` (bracket notation: `payload['custom:company_id']`).
- The Bearer token for API calls is `idToken` (not `accessToken`) because the backend
  validates custom claims from the ID token.

### Tenant Context (target shape — company only)
```typescript
type UserRole = 'reel48_admin' | 'company_admin' | 'manager' | 'employee';

interface TenantContext {
  companyId: string | null;  // null for reel48_admin
  role: UserRole;
  userId: string;
}
```

Do NOT read `custom:sub_brand_id` from the JWT. It still exists in Cognito but the backend
ignores it; the frontend should too.

### Registration Flow (target — single step)
The `/register` page is a **single-step** form:
- Employee enters org code + email + full name + password on one form.
- Frontend calls `POST /api/v1/auth/register` with all fields.
- No sub-brand dropdown. No two-step validation. No per-company sub-brand list.

The two-step flow (validate-org-code first, then show sub-brand dropdown) is being removed
in Session B.

### Protected Routes (stable)
Use `<ProtectedRoute requiredRoles={['company_admin']}>` to gate access. The wrapper:
1. Checks authentication state.
2. Redirects unauthenticated users to `/login`.
3. Optionally checks role requirements.
4. Provides `TenantContext` via React Context.


## Component Architecture

### Carbon-first
Standard UI elements come from `@carbon/react`, not from custom implementations. See
[.claude/rules/carbon-design-system.md](.claude/rules/carbon-design-system.md) for the
full component selection guidance.

### Component Locations (target — actual inventory TBD after Session B)
```
src/
├── styles/
│   └── carbon-theme.scss
├── components/
│   ├── ui/                    # Reel48+-specific reusable compositions
│   │   ├── StatusTag.tsx
│   │   └── S3Image.tsx
│   ├── layout/                # App shell
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── MainLayout.tsx
│   ├── features/              # Feature-specific components
│   │   ├── auth/
│   │   │   └── ProtectedRoute.tsx
│   │   ├── engagement/
│   │   │   ├── NotificationBell.tsx
│   │   │   └── OnboardingWizard.tsx
│   │   └── analytics/         # Minimal after Session B (user/company counts only)
│   └── ErrorBoundary.tsx
```

**Being removed in Session B:** `components/features/catalog/`, most components in
`components/features/analytics/` (all widgets tied to invoice/order/catalog/approval data).

### Conventions (stable)
- `'use client'` on any file importing from `@carbon/react`.
- One component per file, filename PascalCase matching component name.
- Functional components only (exception: `ErrorBoundary`).
- Props as named interface above the component.
- Default exports for page.tsx files, named exports elsewhere.


## Routing Structure — TBD

The current App Router tree will be significantly trimmed in Session B. Surviving routes:

```
src/app/
├── (public)/
│   ├── login/
│   ├── register/                     # single-step form (Session B)
│   └── invite/[token]/
├── (authenticated)/
│   ├── dashboard/
│   ├── profile/
│   ├── notifications/
│   ├── products/                     # Shopify placeholder
│   ├── settings/
│   └── admin/
│       ├── users/
│       └── analytics/                # minimal
└── (platform)/
    └── platform/
        ├── dashboard/
        ├── companies/
        └── analytics/
```

**Being removed in Session B:** `/catalog`, `/orders`, `/bulk-orders`, `/wishlist`,
`/invoices`, `/admin/approvals`, `/admin/approval-rules`, `/admin/brands`,
`/platform/catalogs`, `/platform/invoices`.

### Route Group Collision Rule (stable)
Next.js route groups (parenthesized directory names) do NOT affect the URL. Two route
groups with pages at the same relative path will collide. The `(platform)` group nests
all pages under a `platform/` directory to avoid colliding with `(authenticated)/dashboard`.


## State Management (stable)

- **Server state:** React Query (TanStack Query).
- **Client state:** React Context + useReducer.
- **Form state:** React Hook Form for complex forms; controlled components for simple ones.
- **No Redux/Zustand/Jotai.**


## API Client (stable)

Centralized in `src/lib/api/client.ts`. Attaches the Cognito JWT to every request. Handles
token refresh on 401. Parses responses into the `{ data, meta, errors }` format. Transforms
snake_case (backend) ↔ camelCase (frontend) automatically.

### Unauthenticated calls (`skipAuth: true`)
Pass `{ skipAuth: true }` for unauthenticated endpoints (registration, org-code validation).
Skips `fetchAuthSession()` entirely so the call doesn't fail when no session exists.


## S3 File Upload Pattern (stable)

Two-step pre-signed URL pattern:
1. `POST /api/v1/storage/upload-url` → returns `{ uploadUrl, s3Key }`.
2. `fetch(uploadUrl, { method: 'PUT', body: file })` uploads directly to S3.
3. Save the `s3Key` in the database via a subsequent API call.

Hooks (`src/hooks/useStorage.ts`): `useFileUpload()`, `useDownloadUrl()`.
Display: `<S3Image s3Key="..." alt="..." width={200} />`.


## Styling (Carbon + Tailwind)

- Carbon components for UI elements (Button, TextInput, Modal, DataTable, etc.).
- Carbon props for variants (`kind`, `size`, `type`, `invalid`, `warn`).
- Tailwind for layout between components (`flex`, `gap-*`, `grid`).
- Carbon `<Grid>` + `<Column>` for page-level layout.
- Theme customization in `src/styles/carbon-theme.scss` (Reel48+ color tokens).
- Carbon v11 token names only. See
  [.claude/rules/carbon-design-system.md](.claude/rules/carbon-design-system.md).


## Testing (stable)

- Vitest + React Testing Library.
- MSW for network-level API mocking.
- `matchMedia` and `ResizeObserver` polyfills in `src/__tests__/setup.ts` (required by Carbon).
- Mock `aws-amplify/auth` and `next/navigation` at module level with `vi.mock()`.
- For pages that render Carbon charts, also `vi.mock('@carbon/charts-react', ...)`.

Target roles in tests: `reel48_admin`, `company_admin`, `manager`, `employee`. Do NOT add
fixtures for `sub_brand_admin` or `regional_manager`.


## Environment Variables

Client-side vars MUST use `NEXT_PUBLIC_` prefix:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_xxxxx
NEXT_PUBLIC_COGNITO_CLIENT_ID=xxxxx
```

Do NOT add Stripe-related env vars. Stripe is being removed.


## Performance (stable)

- `next/image` for images.
- Virtualize lists over 50 items (`@tanstack/react-virtual`).
- `next/dynamic` for heavy components not needed initially.
- Prefer server components for initial data loads; client components + React Query for
  interactive data.
