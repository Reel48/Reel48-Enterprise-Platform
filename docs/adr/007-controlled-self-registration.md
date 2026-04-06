# ADR-007: Controlled Self-Registration via Org Code
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  This ADR documents the decision to add a controlled self-registration     ║
# ║  path alongside the existing invite flow. Self-registration uses a         ║
# ║  company-level org code to authenticate the registrant's affiliation,      ║
# ║  assigns them to the default sub-brand as an employee, and relies on       ║
# ║  admin action for promotion or sub-brand reassignment.                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

## Status
Accepted

## Date
2026-04-06

## Context
Reel48+ currently requires admin-created invites for every new employee. Each
invite targets a specific sub-brand and generates a single-use, time-limited
token sent via email. This works well for controlled onboarding but creates
significant friction for large companies onboarding hundreds of employees:

1. An admin must create an individual invite for each employee
2. Invites expire after 72 hours, requiring re-creation if missed
3. The admin must know each employee's email and target sub-brand upfront
4. Batch onboarding is tedious — no self-service path exists

Enterprise clients with 500–10,000+ employees need a faster onboarding path
that still maintains tenant isolation and security guarantees.

**Constraints:**
- Every new user MUST have a valid `company_id` and `sub_brand_id` from the
  moment of creation (RLS depends on this)
- Self-registration must not expose internal company structure (sub-brand names)
  to unauthenticated users
- The existing invite flow must continue to work unchanged
- The solution must fit within Cognito's custom attribute model

## Decision
Add **org-code-based self-registration** as a second onboarding path alongside
invites. A `corporate_admin` generates a reusable, company-level org code (an
8-character alphanumeric string). Employees enter this code during registration
and are automatically assigned:

- **`company_id`** — resolved from the org code
- **`sub_brand_id`** — the company's default sub-brand (guaranteed to exist per ADR-003)
- **`role`** — `employee` (the lowest-privilege role)

Self-registered users are immediately active. Admins can later promote their
role or reassign them to a different sub-brand.

**Key design choices:**
- Org codes are **per-company** (not per-sub-brand) to avoid exposing internal structure
- Only **one active code per company** at a time (generating a new one deactivates the old)
- Codes are **reusable** (not single-use) — designed for bulk onboarding
- **No expiry** for MVP — admin can deactivate at any time
- **No approval queue** — employee role is already minimal-privilege
- The registration endpoint is **unauthenticated** (second exception alongside Stripe webhooks), secured by org code validation + rate limiting

## Alternatives Considered

### Open Self-Registration with Email Domain Verification
- **Pros:** No code to share; employees register with their corporate email and the
  system matches the domain to a company
- **Cons:** Email domains are not reliable company identifiers (shared domains like
  gmail.com, contractors with different domains); easily spoofable; doesn't work for
  companies with multiple email domains; no sub-brand assignment mechanism
- **Why rejected:** Email domain matching is unreliable for enterprise clients with
  complex email setups. An org code provides explicit, admin-controlled company
  affiliation without relying on email infrastructure.

### Batch Invite Upload (CSV)
- **Pros:** Admin uploads a spreadsheet of employee emails; system sends invites in bulk
- **Cons:** Still requires the admin to collect every employee's email upfront; admin
  must decide sub-brand assignment per employee before they've even registered;
  doesn't solve the core friction of admin-per-employee involvement
- **Why rejected:** Reduces per-invite effort but doesn't eliminate the fundamental
  bottleneck: admin must act for each employee. Self-registration shifts onboarding
  effort to the employee, which scales better.

### Per-Sub-Brand Org Codes
- **Pros:** Users land directly in the correct sub-brand; no admin reassignment needed
- **Cons:** Exposes internal sub-brand structure to unauthenticated users (the code
  implicitly reveals "this company has sub-brands X, Y, Z"); more codes for admins
  to manage; employees may join the wrong sub-brand if given the wrong code
- **Why rejected:** For MVP, the default-sub-brand approach is simpler and avoids
  information leakage. Admins can sort users into sub-brands post-registration.
  Per-sub-brand codes can be added later if needed.

## Consequences

### Positive
- Large companies can onboard hundreds of employees without admin-per-employee effort
- Employees self-serve, reducing admin workload and onboarding time
- The invite flow remains available for targeted onboarding (specific sub-brand, specific role)
- Org codes are revocable — admin can cut off self-registration instantly
- Self-registered users have minimal privileges by default, limiting blast radius

### Negative
- Admins must manually reassign self-registered users from the default sub-brand
  to their correct sub-brand (if the company has multiple sub-brands)
- The `POST /api/v1/auth/register` endpoint is the second unauthenticated exception
  (after Stripe webhooks), increasing the unauthenticated attack surface
- Org codes can be shared beyond the intended audience (e.g., posted on social media)
- A `registration_method` column must be added to the users table to distinguish
  invite-registered from self-registered users

### Risks
- **Org code leaking outside the company:** Mitigated by admin revocability (deactivate
  and generate a new code). The employee role's minimal privileges limit damage from
  unauthorized registrations. Admins can deactivate suspicious accounts.
- **Brute-force code guessing:** Mitigated by rate limiting (5 attempts per IP per
  15-minute window via Redis) and a large keyspace (30^8 ≈ 656 billion combinations
  using a 30-character alphabet that excludes ambiguous characters 0/O, 1/I/L).
- **Information disclosure:** Mitigated by returning generic error messages on failed
  registration (no distinction between invalid code, inactive code, or duplicate email).
- **Default sub-brand accumulation:** Companies with many sub-brands may accumulate
  large numbers of users in the default sub-brand awaiting reassignment. Mitigated by
  admin visibility: the user management page shows `registration_method` as a filter,
  making it easy to identify and reassign self-registered users.

## References
- ADR-003: Default Sub-Brand Pattern (guarantees every company has a default sub-brand)
- ADR-005: Cognito over Third-Party Auth (custom attributes carry tenant context)
- `.claude/rules/authentication.md` — Employee Invite Flow (the existing onboarding path)
