---
globs: "**/auth/**,**/security/**,**/middleware/auth*,**/login*,**/cognito*,**/register*,**/org_code*"
---

# Rule: Authentication & Authorization
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This rule activates when Claude Code is working on auth-related files.    ║
# ║  It governs Cognito integration, JWT handling, role-based access, and      ║
# ║  the invite flow that onboards employees into specific sub-brands.         ║
# ║                                                                            ║
# ║  WHY THIS RULE?                                                            ║
# ║                                                                            ║
# ║  Authentication is the FOUNDATION of the entire security model. The JWT    ║
# ║  token is where tenant context originates — if token handling is wrong,    ║
# ║  every endpoint downstream is compromised. This rule ensures Claude Code   ║
# ║  never takes shortcuts with auth.                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Activates for: **/auth/**, **/security/**, **/middleware/auth**, **/login**, **/cognito**

## Cognito Configuration

### Custom Attributes in the User Pool
These custom attributes carry tenant context in every JWT token:
- `custom:company_id` (String) — The user's company. NULL for `reel48_admin` (cross-company access).
- `custom:sub_brand_id` (String) — The user's sub-brand. NULL for `corporate_admin` and `reel48_admin`.
- `custom:role` (String) — One of: `reel48_admin`, `corporate_admin`, `sub_brand_admin`, `regional_manager`, `employee`

### Token Validation Rules
1. Validate the JWT signature against Cognito's JWKS endpoint
2. Verify the token hasn't expired (`exp` claim)
3. Verify the audience (`aud`) matches our app client ID
4. Verify the issuer (`iss`) matches our user pool URL
5. Extract custom claims ONLY after all validation passes
6. Cache the JWKS keys (refresh every 24 hours or on signature failure)

## Role Hierarchy

```
reel48_admin                 → PLATFORM OPERATOR. Full access across ALL companies.
                               Manages catalogs, pricing, product approvals, invoicing.
  └── corporate_admin        → Full access across ALL sub-brands within their company
       └── sub_brand_admin   → Full access within ONE sub-brand
            └── regional_manager  → Can manage orders and bulk orders within their sub-brand
                 └── employee      → Can manage their own profile and place orders
```

### Role-Based Access Matrix
| Action                         | reel48_admin | corporate_admin | sub_brand_admin | regional_manager | employee |
|-------------------------------|:-:|:-:|:-:|:-:|:-:|
| Manage ALL client companies    | ✅ | ❌ | ❌ | ❌ | ❌ |
| Create/price/approve catalogs  | ✅ | ❌ | ❌ | ❌ | ❌ |
| Create/send invoices to clients| ✅ | ❌ | ❌ | ❌ | ❌ |
| View invoices (all companies)  | ✅ | ❌ | ❌ | ❌ | ❌ |
| View invoices (own company)    | ✅ | ✅ | ❌ | ❌ | ❌ |
| View invoices (own brand)      | ✅ | ✅ | ✅ | ✅ | ❌ |
| Manage sub-brands              | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage users (all brands)      | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage users (own brand)       | ✅ | ✅ | ✅ | ❌ | ❌ |
| Manage catalog (brand)         | ✅ | ✅ | ✅ | ❌ | ❌ |
| Create bulk orders             | ✅ | ✅ | ✅ | ✅ | ❌ |
| Approve orders                 | ✅ | ✅ | ✅ | ✅ | ❌ |
| View approval queue            | ✅ | ✅ | ✅ | ✅ | ❌ |
| Approve/reject (products/catalogs) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Approve/reject (orders/bulk)   | ✅ | ✅ | ✅ | ✅ | ❌ |
| Manage approval rules          | ✅ | ✅ | ❌ | ❌ | ❌ |
| Place individual orders        | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage own profile             | ✅ | ✅ | ✅ | ✅ | ✅ |
| View analytics (all companies) | ✅ | ❌ | ❌ | ❌ | ❌ |
| View analytics (own company)   | ✅ | ✅ | ❌ | ❌ | ❌ |
| View analytics (own brand)     | ✅ | ✅ | ✅ | ❌ | ❌ |
| Generate/manage org codes      | ✅ | ✅ | ❌ | ❌ | ❌ |

## Employee Onboarding Flows

Reel48+ supports **two** onboarding paths. Both guarantee a valid `company_id` and
`sub_brand_id` from the moment the user is created, preserving RLS integrity.

### Flow 1: Admin Invite (Targeted Onboarding)

## Employee Invite Flow

### How It Works
1. An admin (corporate or sub-brand) creates an invite for a specific sub-brand
2. The system generates a unique invite token and sends an email via SES
3. The employee clicks the link, which opens the registration page with the
   invite token pre-filled
4. On registration, the system:
   a. Creates the Cognito user with the correct `custom:company_id`, `custom:sub_brand_id`, and `custom:role`
   b. Creates the employee profile record in the database
   c. Marks the invite as consumed (single-use)

### Critical Rules for Invites
- Invite tokens MUST be single-use and time-limited (72-hour expiry)
- The `sub_brand_id` is set during invite creation and CANNOT be changed by the employee
- The `company_id` is inherited from the inviting admin
- Invites carry the role (defaults to `employee` unless the admin specifies otherwise)

### Flow 2: Self-Registration via Org Code (Bulk Onboarding)

# --- ADDED 2026-04-06 after ADR-007 ---
# Reason: Invite-only onboarding creates friction for large companies (500+ employees).
# Impact: Claude Code now knows there are TWO onboarding paths and generates the
# self-registration endpoint correctly (unauthenticated, rate-limited, org-code-validated).

#### What Is an Org Code?
An org code is a reusable, company-level registration code that maps to a single company.
- **Format:** 8-character uppercase alphanumeric (30-char alphabet excluding ambiguous
  characters: 0/O, 1/I/L). Example: `REEL7K3M`
- **Scope:** Per-company (NOT per-sub-brand). One active code per company at a time.
- **Stored in:** `org_codes` table with `company_id`, `code`, `is_active`, `created_by`
- **Created by:** `corporate_admin` or `reel48_admin`
- **Reusable:** Not consumed on use (unlike invite tokens). Designed for many employees.
- **Revocable:** Admin can deactivate instantly. Does not affect existing users.

#### How Self-Registration Works (Two-Step Flow)
1. A `corporate_admin` generates an org code for their company
2. The code is shared with employees (email, intranet, printed materials, etc.)
3. **Step 1 — Validate org code:** Employee navigates to `/register` and enters
   their **org code**. The frontend calls `POST /api/v1/auth/validate-org-code`.
   On success, the system returns the **company name** and **list of sub-brands**
   for that company. On failure, a generic error is shown.
4. **Step 2 — Complete registration:** The form expands to show a sub-brand
   dropdown (pre-selected to the default sub-brand), plus **email**, **full name**,
   and **password** fields. The employee selects their sub-brand and submits.
   If the company has only one sub-brand, the dropdown is hidden and that sub-brand
   is auto-selected.
5. On registration (`POST /api/v1/auth/register`), the system:
   a. Validates the org code again (re-checks `is_active = true`)
   b. Resolves the `company_id` from the org code
   c. Validates the submitted `sub_brand_id` belongs to the resolved company
   d. Creates the Cognito user with `custom:company_id`, `custom:sub_brand_id`
      (employee's choice), and `custom:role = employee`
   e. Creates the user record in the database with `registration_method = 'self_registration'`
   f. Cognito sends an email verification message
6. User verifies email, then logs in normally — JWT contains the same custom claims
   as an invite-registered user

#### Critical Rules for Self-Registration
- Self-registered users are ALWAYS assigned `role = employee` (the lowest privilege)
- Self-registered users **choose their own sub-brand** from the company's sub-brand
  list during registration. The sub-brand list is only shown after a valid org code
  is entered (not publicly enumerable). The default sub-brand is pre-selected.
- The submitted `sub_brand_id` MUST be validated server-side: confirm it belongs to
  the company resolved from the org code. Never trust the frontend's sub-brand selection
  without verification.
- Both registration endpoints (`POST /api/v1/auth/validate-org-code` and
  `POST /api/v1/auth/register`) are **unauthenticated** — these are endpoint exceptions
  alongside the Stripe webhook. They do NOT use `get_tenant_context`. Security comes
  from org code validation + rate limiting.
- **Rate limiting:** 5 attempts per IP per 15-minute window (via Redis/ElastiCache).
  Applied to BOTH endpoints. Return HTTP 429 when exceeded.
- **No enumeration on failure:** Failed org code validation returns a generic error
  regardless of cause (invalid code, inactive code). Failed registration returns
  a generic error regardless of cause (bad code, duplicate email, invalid sub-brand).
- **Email verification:** Required via Cognito before the account is fully functional
- Admins can later **promote** the user's role or **reassign** them to a different
  sub-brand (requires updating both the `users` table and Cognito custom attributes)
- Only **one active org code per company** at a time. Generating a new code
  automatically deactivates the previous one.

#### Org Code Management Endpoints
- `POST /api/v1/org_codes` — Generate new org code (deactivates previous). Requires `corporate_admin`.
- `GET /api/v1/org_codes/current` — View current active code. Requires `corporate_admin`.
- `DELETE /api/v1/org_codes/{id}` — Deactivate a code. Requires `corporate_admin`.

## Frontend Auth Patterns

### Token Storage
- Amplify handles token storage automatically (in-memory + secure refresh)
- NEVER store tokens in localStorage (XSS vulnerability)
- NEVER store tokens in cookies without httpOnly + secure flags

### Token Refresh
- Amplify handles automatic token refresh before expiry
- If a 401 is received, attempt one token refresh before logging out
- If refresh fails, redirect to `/login` and clear all auth state

### Auth State Provider
```typescript
// Wrap the entire app in an AuthProvider that:
// 1. Checks auth state on mount
// 2. Provides TenantContext to all children
// 3. Handles automatic token refresh
// 4. Exposes login, logout, and isAuthenticated

<AuthProvider>
  <App />
</AuthProvider>
```

## Common Mistakes to Avoid
- ❌ Storing JWT tokens in localStorage
- ❌ Not validating token signatures (just decoding without verification)
- ❌ Trusting the `role` from the frontend without server-side verification
- ❌ Allowing employees to self-register without a valid org code or invite token (bypasses company and sub-brand assignment)
- ❌ Not setting `sub_brand_id = NULL` for corporate admin users
- ❌ Forgetting to set PostgreSQL session variables after token validation
