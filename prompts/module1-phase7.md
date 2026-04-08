# Module 1 Phase 7 Prompt — Registration Pages (Org Code + Invite)

Copy everything below the line and paste it as your first message in a new Claude Code session.

---

Continue with Module 1 Phase 7 per the harness. Phases 1–6 are complete on `main`.

- **Phase 1** scaffolded the backend (FastAPI app, config, base models, Alembic, health endpoint, test skeleton).
- **Phase 2** created the 5 identity models (Company, SubBrand, User, Invite, OrgCode) and a single Alembic migration with RLS policies for all 5 tables.
- **Phase 3** added the auth plumbing: JWT validation (`security.py`), TenantContext dataclass (`tenant.py`), `get_tenant_context` dependency with `SET LOCAL` session variables (`dependencies.py`), TenantContextMiddleware, rate limiter (`rate_limit.py`), and 28 tests (auth + RLS isolation).
- **Phase 4** added CRUD endpoints, Pydantic schemas, and the service layer for Companies, Sub-Brands, Users, Invites, and Org Codes (19 endpoints total). 93 tests passing.
- **Phase 5** added self-registration (`POST /api/v1/auth/register`), invite consumption (`POST /api/v1/auth/register-from-invite`), org code validation (`POST /api/v1/auth/validate-org-code`), CognitoService, and RegistrationService. 114 tests passing.
- **Phase 6** scaffolded the full Next.js 14 frontend: project config (TypeScript strict, Carbon + Tailwind, Vitest), Amplify v6 auth integration with Cognito JWT claim extraction, API client with snake/camel transforms and 401 retry, Carbon layout shell (Header, role-based Sidebar, MainLayout), login page, route groups for public/authenticated/platform, and 26 tests across 5 files.

**Phase 7 scope: Registration pages — self-registration via org code and invite-based registration.**

The backend endpoints already exist. This phase builds the two frontend registration flows that call them. The login page (`src/app/(public)/login/page.tsx`) already links to `/register` ("Don't have an account? Register with an org code") and `/invite` ("Have an invite? Register here").

### What to build

**1. Self-Registration Page** (`src/app/(public)/register/page.tsx`)

A **two-step form** that guides the employee through org code validation → registration.

**Step 1 — Org Code Validation:**
- Carbon `TextInput` for the org code (8-character uppercase alphanumeric)
- Carbon `Button` (kind="primary") labeled "Validate Code"
- On submit, call `POST /api/v1/auth/validate-org-code` with `{ "code": "<input>" }`
  - Use the API client from `src/lib/api/client.ts` — it handles snake/camel transforms
  - Note: This is an **unauthenticated** endpoint. The API client attaches a Bearer token by default (from `fetchAuthSession`). For unauthenticated calls, either:
    - (a) Add a raw `fetch` call that skips the auth header, OR
    - (b) Add an option to the API client to skip auth (e.g., `api.post<T>(url, body, { skipAuth: true })`)
  - Choose whichever approach is cleaner. The key constraint: these calls must NOT fail because there's no Amplify session.
- On success, the response contains `{ "company_name": "...", "sub_brands": [...] }`. Transition to Step 2.
- On failure, show a Carbon `InlineNotification` (kind="error") with a generic message: "Invalid registration code. Please check your code and try again."
- Show loading state on the button while the request is in flight.

**Step 2 — Registration Form (shown after successful org code validation):**
- Display the validated **company name** prominently (e.g., "Registering with Acme Corp")
- Carbon `Dropdown` for sub-brand selection:
  - Items come from the `sub_brands` array returned in Step 1
  - Pre-select the sub-brand where `is_default === true`
  - If the company has **only one sub-brand**, hide the dropdown entirely and auto-select it (the user doesn't need to see it)
  - Label: "Select your division" or "Select your sub-brand"
- Carbon `TextInput` for email (type="email", required)
- Carbon `TextInput` for full name (required)
- Carbon `TextInput` for password (type="password", required)
  - Add a helper text: "Password must be at least 8 characters"
- Carbon `TextInput` for password confirmation (type="password", required)
  - Client-side validation: passwords must match before submission
- Carbon `Button` (kind="primary") labeled "Create Account"
- On submit, call `POST /api/v1/auth/register` with:
  ```json
  {
    "code": "<org_code_from_step_1>",
    "sub_brand_id": "<selected_sub_brand_id>",
    "email": "<email>",
    "full_name": "<full_name>",
    "password": "<password>"
  }
  ```
- On success (201), show a **success state**: "Account created! Check your email to verify your account, then sign in." with a Carbon `Link` to `/login`.
- On failure, show a Carbon `InlineNotification` (kind="error") with a generic message: "Registration failed. Please try again." (backend returns generic errors to prevent enumeration)
- Show loading state on the button while the request is in flight.
- Include a "Back" link or button to return to Step 1 (to try a different code).
- Include a link to `/login` ("Already have an account? Sign in").

**2. Invite Registration Page** (`src/app/(public)/invite/page.tsx`)

A **single-step form** for employees who received an invite link. The invite token is entered manually (not extracted from URL params — the invite email contains a link to `/invite` and the employee pastes or carries the token).

Wait — actually, check the routing structure in `frontend/CLAUDE.md`. It shows `invite/[token]/page.tsx` (dynamic route). Let me clarify the approach:

- **Option A: Static page** (`/invite/page.tsx`) — Employee navigates to `/invite` and manually enters their invite token in a text field. Simpler to build.
- **Option B: Dynamic route** (`/invite/[token]/page.tsx`) — The invite email contains a link like `/invite/abc123def456...`. The token is extracted from the URL. The form pre-fills the token field (or hides it entirely). Better UX.

**Use Option B** (dynamic route with URL token) — this matches the harness routing structure and provides a better experience. But also provide a fallback: if someone navigates to `/invite` without a token, show a text input for the token.

Implementation:
- **`src/app/(public)/invite/[token]/page.tsx`** — Dynamic route. Extract `token` from `params`.
- Pre-fill the token (hidden or read-only field).
- Show:
  - Carbon `TextInput` for email (type="email", required)
  - Carbon `TextInput` for full name (required)
  - Carbon `TextInput` for password (type="password", required)
  - Carbon `TextInput` for password confirmation (type="password", required)
    - Client-side validation: passwords must match
  - Helper text: "Password must be at least 8 characters"
  - Carbon `Button` (kind="primary") labeled "Create Account"
- On submit, call `POST /api/v1/auth/register-from-invite` with:
  ```json
  {
    "token": "<token_from_url>",
    "email": "<email>",
    "full_name": "<full_name>",
    "password": "<password>"
  }
  ```
- On success (201), show the same success state as the org code flow: "Account created! Check your email to verify your account, then sign in." with a link to `/login`.
- On failure, show a Carbon `InlineNotification` (kind="error") with: "This invite link is invalid or has expired. Please contact your administrator." (generic — covers invalid token, expired token, consumed token, email mismatch).
- Show loading state on the button while the request is in flight.
- Include a link to `/login` ("Already have an account? Sign in").

Also create a simple **redirect page** at `src/app/(public)/invite/page.tsx` — since the login page links to `/invite` generically, this page should show a Carbon `TextInput` prompting the user to enter their invite token, then redirect to `/invite/{token}` on submit. Or it can inline the full form and use state instead of URL routing. Choose whichever approach is cleaner.

**3. Update API Client for Unauthenticated Requests** (`src/lib/api/client.ts`)

The registration endpoints are unauthenticated. The current API client always tries to attach a Bearer token via `fetchAuthSession()`. This will fail when there's no Amplify session (unauthenticated user on the registration page).

Add support for unauthenticated requests. Recommended approach — add a `skipAuth` option:

```typescript
interface FetchOptions {
  body?: unknown;
  params?: Record<string, string>;
  skipAuth?: boolean;  // NEW: skip Bearer token for unauthenticated endpoints
}
```

When `skipAuth: true`, skip the `fetchAuthSession()` call and send the request without an Authorization header.

Update the `api` object to pass this option through:
```typescript
export const api = {
  get: <T>(url: string, params?: Record<string, string>, options?: { skipAuth?: boolean }) => ...,
  post: <T>(url: string, body?: unknown, options?: { skipAuth?: boolean }) => ...,
  // etc.
};
```

**4. Update Login Page Link** (`src/app/(public)/login/page.tsx`)

The login page currently links to `/invite`. If you're using the dynamic route approach (`/invite/[token]`), update this link to point to `/invite` which will show the token input page. No change needed if `/invite/page.tsx` exists as a landing page.

### Cross-cutting requirements

1. **All components that import from `@carbon/react` must have `'use client'` directive.**
2. **Default exports for `page.tsx` files** in `src/app/`, named exports for components in `src/components/`.
3. **No raw hex colors** — use Carbon theme tokens or Tailwind color classes.
4. **Form validation:**
   - Org code field: required, should accept uppercase input (consider auto-uppercasing)
   - Email: required, type="email" for browser validation
   - Password: required, minimum 8 characters (client-side hint; Cognito enforces the real policy)
   - Password confirmation: must match password (validate on submit, not on blur — avoid premature error states)
5. **Error handling:** All API errors display as Carbon `InlineNotification` with `kind="error"`. Use generic messages (the backend intentionally returns generic errors to prevent enumeration).
6. **Loading states:** Use disabled button with loading text during submission (same pattern as the login page).
7. **Follow the login page pattern** (`src/app/(public)/login/page.tsx`) for visual layout, Carbon component usage, and state management. Keep a consistent look across all public auth pages.

### Tests

Create tests in `src/__tests__/` covering:

1. **`register-page.test.tsx`** — Self-registration via org code:
   - Step 1: Renders org code input and validate button
   - Step 1: Shows error notification on invalid org code
   - Step 1: On valid org code, shows company name and registration form (Step 2)
   - Step 2: Sub-brand dropdown is pre-selected to default sub-brand
   - Step 2: Sub-brand dropdown is hidden when only one sub-brand exists
   - Step 2: Shows password mismatch error when passwords don't match
   - Step 2: On successful registration, shows success message with link to login
   - Step 2: Shows error notification on registration failure
   - Has link to login page

2. **`invite-page.test.tsx`** — Invite registration:
   - Renders registration form with email, name, password fields
   - Shows error notification on invalid/expired invite token
   - On successful registration, shows success message with link to login
   - Shows password mismatch error when passwords don't match
   - Has link to login page

Mock the API client (or use MSW) for all API calls. Mock `next/navigation` for URL params and routing. Follow the existing test patterns in `src/__tests__/login-page.test.tsx`.

### Constraints

- Do NOT build email verification pages — Cognito handles email verification. After registration, users verify their email via Cognito's email, then come back and log in normally.
- Do NOT build password reset or forgot password pages — those are a future enhancement.
- Do NOT modify the backend — all endpoints already exist and are tested (114 backend tests passing).
- Do NOT add new dependencies — everything needed is already in `package.json` (Carbon, React, API client).
- Run `npm run lint` and `npm run type-check` after implementation.
- Run `npm run test:run` to verify ALL tests pass (existing 26 + new Phase 7 tests).
- Run `npm run build` to verify the production build succeeds.
