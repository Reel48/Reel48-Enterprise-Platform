# Module 1 Phase 6 Prompt — Next.js App Shell, Amplify Auth, Carbon Layout, Login Page, API Client

Copy everything below the line and paste it as your first message in a new Claude Code session.

---

Continue with Module 1 Phase 6 per the harness. Phases 1–5 are complete on `main`.

- **Phase 1** scaffolded the backend (FastAPI app, config, base models, Alembic, health endpoint, test skeleton).
- **Phase 2** created the 5 identity models (Company, SubBrand, User, Invite, OrgCode) and a single Alembic migration with RLS policies for all 5 tables.
- **Phase 3** added the auth plumbing: JWT validation (`security.py`), TenantContext dataclass (`tenant.py`), `get_tenant_context` dependency with `SET LOCAL` session variables (`dependencies.py`), TenantContextMiddleware, rate limiter (`rate_limit.py`), and 28 tests (auth + RLS isolation).
- **Phase 4** added CRUD endpoints, Pydantic schemas, and the service layer for Companies, Sub-Brands, Users, Invites, and Org Codes (19 endpoints total). 93 tests passing.
- **Phase 5** added self-registration (`POST /api/v1/auth/register`), invite consumption (`POST /api/v1/auth/register-from-invite`), org code validation (`POST /api/v1/auth/validate-org-code`), CognitoService, and RegistrationService. 114 tests passing.

**Phase 6 scope: Frontend application shell — Next.js project setup, Amplify auth integration, Carbon layout (sidebar + header), login page, and API client.**

The frontend directory already has 3 files: `CLAUDE.md` (comprehensive conventions), `tailwind.config.ts` (full color token config), and `src/styles/carbon-theme.scss` (Carbon theme overrides + CSS custom properties). Everything else needs to be created.

### What to build (in this order)

**1. Project Initialization**

- **`package.json`** — Initialize with `npm init`. Install:
  - **Core:** `next@14`, `react@18`, `react-dom@18`
  - **Design system:** `@carbon/react`, `@carbon/icons-react`
  - **Auth:** `aws-amplify`
  - **Data fetching:** `@tanstack/react-query`
  - **Forms:** `react-hook-form`
  - **Dev dependencies:** `typescript`, `@types/react`, `@types/react-dom`, `@types/node`, `sass`, `tailwindcss`, `postcss`, `autoprefixer`, `eslint`, `eslint-config-next`, `prettier`, `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@vitejs/plugin-react`, `jsdom`, `msw`
  - **Scripts:** `dev`, `build`, `start`, `lint`, `type-check` (`tsc --noEmit`), `test` (`vitest`), `test:run` (`vitest run`)
- **`tsconfig.json`** — Strict mode, `@/*` path alias mapping to `./src/*`, ES2020 target, module `esnext`, JSX `preserve`
- **`next.config.mjs`** — `reactStrictMode: true`, `sassOptions: { quietDeps: true }`
- **`postcss.config.mjs`** — Tailwind + autoprefixer plugins
- **`.env.example`** — Template with all `NEXT_PUBLIC_` variables:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_COGNITO_USER_POOL_ID=
  NEXT_PUBLIC_COGNITO_CLIENT_ID=
  ```
- **`.env.local`** — Copy of `.env.example` with `http://localhost:8000` as default API URL. Add to `.gitignore` if not already there.

**2. Global Styles & Layout Shell**

- **`src/app/globals.scss`** — Import order: Carbon theme first, then Tailwind directives.
  ```scss
  @use '../styles/carbon-theme';
  @tailwind base;
  @tailwind components;
  @tailwind utilities;
  ```
- **`src/app/layout.tsx`** — Root layout (server component). Imports `globals.scss`. Sets `<html lang="en">` and basic `<body>` structure. Wraps children in the `Providers` component (see below).
- **`src/app/page.tsx`** — Root page. Redirects to `/login` (unauthenticated) or `/dashboard` (authenticated) based on auth state.

**3. TypeScript Types**

- **`src/types/auth.ts`** — Core auth types:
  ```typescript
  export type UserRole = 'reel48_admin' | 'corporate_admin' | 'sub_brand_admin' | 'regional_manager' | 'employee';

  export interface TenantContext {
    userId: string;
    companyId: string | null;
    subBrandId: string | null;
    role: UserRole;
  }

  export interface AuthUser {
    email: string;
    fullName: string;
    tenantContext: TenantContext;
  }
  ```
- **`src/types/api.ts`** — Standard API response types:
  ```typescript
  export interface ApiResponse<T> {
    data: T;
    meta: Record<string, unknown>;
    errors: ApiError[];
  }

  export interface ApiListResponse<T> {
    data: T[];
    meta: PaginationMeta;
    errors: ApiError[];
  }

  export interface PaginationMeta {
    page: number;
    perPage: number;
    total: number;
  }

  export interface ApiError {
    code: string;
    message: string;
    field?: string;
  }
  ```

**4. API Client**

- **`src/lib/api/client.ts`** — Centralized fetch wrapper:
  - Reads `NEXT_PUBLIC_API_URL` for base URL
  - Attaches Cognito JWT token from Amplify's `fetchAuthSession()` on every request
  - Handles 401 by attempting one token refresh, then redirecting to `/login` on failure
  - Transforms response keys from `snake_case` to `camelCase` (responses) and `camelCase` to `snake_case` (requests)
  - Exports `api.get<T>()`, `api.post<T>()`, `api.patch<T>()`, `api.delete<T>()`
  - Parses all responses into `ApiResponse<T>` or `ApiListResponse<T>` format
  - Throws a typed `ApiError` on non-2xx responses
- **`src/lib/api/transform.ts`** — Utility functions for `snakeToCamel()` and `camelToSnake()` key transformation (deep/recursive for nested objects and arrays)

**5. Auth Infrastructure**

- **`src/lib/auth/config.ts`** — Amplify configuration. Calls `Amplify.configure()` with Cognito user pool settings from env vars.
- **`src/lib/auth/context.tsx`** — `AuthProvider` context:
  - Checks auth state on mount via Amplify's `getCurrentUser()` / `fetchAuthSession()`
  - Extracts `custom:company_id`, `custom:sub_brand_id`, `custom:role` from the JWT ID token payload
  - Provides `AuthContext` with: `user: AuthUser | null`, `isAuthenticated: boolean`, `isLoading: boolean`, `signIn(email, password)`, `signOut()`, `refreshSession()`
  - Handles automatic token refresh
  - Clears state and redirects to `/login` on auth failure
- **`src/lib/auth/hooks.ts`** — Custom hooks:
  - `useAuth()` — Returns the AuthContext (throws if used outside AuthProvider)
  - `useTenantContext()` — Returns `TenantContext` from the authenticated user (throws if not authenticated)
  - `useRequireAuth()` — Redirects to `/login` if not authenticated (for page-level guards)
  - `useHasRole(roles: UserRole[])` — Returns boolean for role checking
- **`src/components/features/auth/ProtectedRoute.tsx`** — Client component wrapper:
  - Shows Carbon `<Loading>` while auth state is being checked
  - Redirects to `/login` if not authenticated
  - If `requiredRoles` prop is provided, shows a 403 page or redirects if the user's role doesn't match
  - Renders children when authenticated and authorized

**6. Providers Component**

- **`src/app/providers.tsx`** — Client component (`'use client'`) that wraps the app with:
  - `AuthProvider` (from auth context)
  - `QueryClientProvider` (from React Query — create a `QueryClient` with sensible defaults: `staleTime: 5 * 60 * 1000`, `retry: 1`)
  - Calls `configureAmplify()` on module load (not inside a component render)

**7. Layout Components**

- **`src/components/layout/Header.tsx`** — Carbon `Header` component:
  - Displays "Reel48+" logo/text on the left
  - Shows the current user's name and role on the right
  - Includes a user menu (Carbon `HeaderGlobalAction` + `OverflowMenu`) with: Profile, Settings, Sign Out
  - Wrapped in `<Theme theme="g100">` for the dark brand surface
  - Background color: `#292c2f` (Charcoal 900)
- **`src/components/layout/Sidebar.tsx`** — Carbon `SideNav` component:
  - Navigation items change based on user role:
    - **`employee`**: Dashboard, Catalog, Orders, Profile
    - **`regional_manager`**: + Bulk Orders, Approvals
    - **`sub_brand_admin`**: + Users, Brand Settings
    - **`corporate_admin`**: + All Sub-Brands, Analytics, Invoices
    - **`reel48_admin`**: Platform Dashboard, Companies, Catalogs, Invoices (completely different nav)
  - Active item highlighted with Teal 400 (`#3db8b8`)
  - Hover state: Charcoal 800 (`#353a3f`)
  - Wrapped in `<Theme theme="g100">` for the dark brand surface
  - Background color: `#292c2f` (Charcoal 900)
- **`src/components/layout/MainLayout.tsx`** — Combines Header + Sidebar + content area:
  - Header fixed at top
  - Sidebar on the left (Carbon's standard `SideNav` positioning)
  - Content area fills remaining space with `<Theme theme="g10">` (light theme)
  - Content area has appropriate padding (`p-6` or Carbon spacing)

**8. Public Route Group & Login Page**

- **`src/app/(public)/layout.tsx`** — Minimal layout for unauthenticated pages. No sidebar or header. Centered content. Light background. If user is already authenticated, redirect to `/dashboard`.
- **`src/app/(public)/login/page.tsx`** — Login page:
  - Centered card layout with the Reel48+ logo/name at top
  - Carbon `TextInput` for email
  - Carbon `PasswordInput` for password (or `TextInput` with type="password")
  - Carbon `Button` (primary, kind="primary") for "Sign In"
  - Carbon `InlineNotification` for error messages (kind="error")
  - Loading state on the button during sign-in (Carbon `InlineLoading` or button loading prop)
  - Link to `/register` ("Don't have an account? Register with an org code")
  - Link to invite registration ("Have an invite? Register here") pointing to `/invite`
  - On successful login, redirect to `/dashboard`
  - Uses `useAuth().signIn()` — delegates to Amplify

**9. Authenticated Route Group**

- **`src/app/(authenticated)/layout.tsx`** — Wraps all authenticated pages with:
  - `<ProtectedRoute>` — redirects to `/login` if not authenticated
  - `<MainLayout>` — renders Header + Sidebar + content area
- **`src/app/(authenticated)/dashboard/page.tsx`** — Placeholder dashboard page:
  - Shows "Welcome, {user.fullName}" heading
  - Shows user's role and company/sub-brand context as Carbon `Tag` components
  - Placeholder content: "Dashboard coming in Module 2+"
  - This is a minimal page to verify the full auth flow works end-to-end

**10. Platform Route Group (Stub)**

- **`src/app/(platform)/layout.tsx`** — Wraps platform admin pages with:
  - `<ProtectedRoute requiredRoles={['reel48_admin']}>` — restricts to platform admins
  - A platform-specific layout (can reuse MainLayout with different sidebar items)
- **`src/app/(platform)/dashboard/page.tsx`** — Placeholder: "Platform Admin Dashboard — Coming Soon"

### Cross-cutting requirements

1. **All components that import from `@carbon/react` must have `'use client'` directive.**
2. **No raw hex colors in component files** — use Carbon theme tokens, Tailwind color classes (which reference CSS custom properties), or the named token values from the theme.
3. **Named exports for components**, default exports for `page.tsx` files only.
4. **One component per file**, filename matches component name (PascalCase).
5. **Case transformation** — the API client handles `snake_case` ↔ `camelCase` automatically. Frontend code always uses `camelCase`.
6. **Error boundaries** — add a basic error boundary at the app level to catch and display unhandled errors gracefully.

### Tests

Create tests in `src/__tests__/` covering:

1. **`auth-context.test.tsx`** — AuthProvider renders children when authenticated, redirects when not, extracts tenant context from token correctly
2. **`api-client.test.ts`** — API client attaches auth token, transforms keys correctly, handles 401 with retry
3. **`login-page.test.tsx`** — Login form renders, shows error on invalid credentials, redirects on success
4. **`protected-route.test.tsx`** — Shows loading state, redirects unauthenticated users, blocks unauthorized roles
5. **`sidebar.test.tsx`** — Renders correct nav items based on user role (test all 5 roles)

Use MSW for API mocking. Mock Amplify's auth functions (`getCurrentUser`, `fetchAuthSession`, `signIn`, `signOut`) at the module level.

### Constraints

- Do NOT build the registration pages in this phase — those are Phase 7.
- Do NOT build any feature pages (catalog, orders, etc.) — those are later modules. Only build the dashboard placeholder.
- Do NOT use Redux, Zustand, or Jotai — React Query + Context is the state management approach.
- Do NOT create wrapper components for Carbon primitives (no `Button.tsx`, `Input.tsx`, etc.).
- Do NOT use `@import` for SCSS — use `@use` (Dart Sass module system).
- Do NOT use Carbon v10 token names (`$interactive-01`, `$ui-background`, etc.).
- Run `npm run lint` and `npm run type-check` after implementation.
- Run `npm run test:run` to verify all tests pass.
