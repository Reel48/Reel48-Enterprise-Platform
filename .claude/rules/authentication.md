# Rule: Authentication & Authorization

> ⚠ **SIMPLIFICATION IN PROGRESS** — this file has been stripped down as part of the simplification
> refactor documented at `~/.claude/plans/yes-please-write-the-memoized-karp.md`. The previous
> content described a 5-role model with sub-brand scoping and two-step self-registration. That
> architecture is being removed. This file contains only the rules that are still true today and
> will be rewritten authoritatively in Session D of the plan. Do **not** reintroduce sub-brand
> concepts, `sub_brand_admin` / `regional_manager` roles, or a sub-brand selection step in
> registration. When in doubt, consult the plan.

# Activates for: **/auth/**, **/security/**, **/middleware/auth**, **/login**, **/cognito**

## What Is Stable (use these rules now)

### Cognito JWT Validation (unchanged)
1. Validate the JWT signature against Cognito's JWKS endpoint.
2. Verify the token hasn't expired (`exp`).
3. Verify the audience (`aud`) matches the app client ID.
4. Verify the issuer (`iss`) matches the user pool URL.
5. Extract custom claims ONLY after all validation passes.
6. Cache the JWKS keys (refresh every 24 hours or on signature failure).

### Token Storage (unchanged)
- Amplify handles token storage automatically (in-memory + secure refresh).
- NEVER store tokens in `localStorage` (XSS vulnerability).
- NEVER store tokens in cookies without `httpOnly` + `secure` flags.

### Token Refresh (unchanged)
- Amplify handles automatic token refresh before expiry.
- If a 401 is received, attempt one token refresh before logging out.
- If refresh fails, redirect to `/login` and clear all auth state.

### Auth State Provider (unchanged)
Wrap the app in an `<AuthProvider>` that checks auth state, provides TenantContext, handles refresh, and exposes login/logout/isAuthenticated.

## What Is In Flux (TBD — do not guess)

- **Role model.** Target is 4 roles: `reel48_admin`, `company_admin`, `manager`, `employee`.
  Sessions A and B implement the collapse. Session D documents the final matrix.
- **Registration flow.** Target is single-step: user enters org code + email + name + password on
  one form. No sub-brand selection. Session B implements it; Session D documents it.
- **Custom Cognito attributes.** `custom:sub_brand_id` still exists in the user pool but is ignored
  by the backend after Session A. `custom:company_id` and `custom:role` remain authoritative.

## Common Mistakes to Avoid (still true)
- ❌ Storing JWT tokens in localStorage.
- ❌ Decoding tokens without validating the signature.
- ❌ Trusting the `role` claim without server-side verification.
- ❌ Allowing self-registration without a valid org code (bypasses company assignment).
