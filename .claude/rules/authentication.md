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
- `custom:company_id` (String) — The user's company. Always set.
- `custom:sub_brand_id` (String) — The user's sub-brand. NULL for corporate_admin.
- `custom:role` (String) — One of: `corporate_admin`, `sub_brand_admin`, `regional_manager`, `employee`

### Token Validation Rules
1. Validate the JWT signature against Cognito's JWKS endpoint
2. Verify the token hasn't expired (`exp` claim)
3. Verify the audience (`aud`) matches our app client ID
4. Verify the issuer (`iss`) matches our user pool URL
5. Extract custom claims ONLY after all validation passes
6. Cache the JWKS keys (refresh every 24 hours or on signature failure)

## Role Hierarchy

```
corporate_admin          → Full access across ALL sub-brands within their company
  └── sub_brand_admin    → Full access within ONE sub-brand
       └── regional_manager  → Can manage orders and bulk orders within their sub-brand
            └── employee      → Can manage their own profile and place orders
```

### Role-Based Access Matrix
| Action                    | corporate_admin | sub_brand_admin | regional_manager | employee |
|--------------------------|:-:|:-:|:-:|:-:|
| Manage sub-brands        | ✅ | ❌ | ❌ | ❌ |
| Manage users (all brands)| ✅ | ❌ | ❌ | ❌ |
| Manage users (own brand) | ✅ | ✅ | ❌ | ❌ |
| Manage catalog (master)  | ✅ | ❌ | ❌ | ❌ |
| Manage catalog (brand)   | ✅ | ✅ | ❌ | ❌ |
| Create bulk orders       | ✅ | ✅ | ✅ | ❌ |
| Approve orders           | ✅ | ✅ | ✅ | ❌ |
| Place individual orders  | ✅ | ✅ | ✅ | ✅ |
| Manage own profile       | ✅ | ✅ | ✅ | ✅ |
| View analytics (all)     | ✅ | ❌ | ❌ | ❌ |
| View analytics (brand)   | ✅ | ✅ | ❌ | ❌ |

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
- ❌ Allowing employees to self-register without an invite (bypasses sub-brand assignment)
- ❌ Not setting `sub_brand_id = NULL` for corporate admin users
- ❌ Forgetting to set PostgreSQL session variables after token validation
