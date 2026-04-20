# ADR-007: Controlled Self-Registration via Org Code

> ⚠ **PARTIALLY SUPERSEDED** — the org-code self-registration concept stands. However,
> the **two-step flow with sub-brand selection** described in this ADR is being collapsed
> to a **single-step flow** (org code + email + name + password on one form). Sub-brand
> selection is removed per ADR-009 (pending). Users registered via org code are assigned
> `role = employee` at the company level. See
> `~/.claude/plans/yes-please-write-the-memoized-karp.md`.

#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  This ADR documents the decision to add a controlled self-registration     ║
# ║  path alongside the existing invite flow. Self-registration uses a         ║
# ║  company-level org code to authenticate the registrant's affiliation,      ║
# ║  and lets them choose their sub-brand during a two-step registration       ║
# ║  flow. They are assigned the employee role by default.                     ║
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
- The existing invite flow must continue to work unchanged
- The solution must fit within Cognito's custom attribute model

## Decision
Add **org-code-based self-registration** as a second onboarding path alongside
invites. A `corporate_admin` generates a reusable, company-level org code (an
8-character alphanumeric string). Registration is a **two-step flow**:

1. **Step 1:** Employee enters the org code. The system validates the code and
   returns the company name and list of sub-brands for that company.
2. **Step 2:** Employee selects their sub-brand from the list, enters their
   name/email/password, and submits. The system creates the user with:

- **`company_id`** — resolved from the org code
- **`sub_brand_id`** — chosen by the employee from the company's sub-brands
  (defaults to the default sub-brand if only one exists)
- **`role`** — `employee` (the lowest-privilege role)

Self-registered users are immediately active. Admins can later promote their
role. Sub-brand names are intentionally visible to registrants — employees need
to know which sub-brand they belong to in order to self-select correctly.

**Key design choices:**
- Org codes are **per-company** (not per-sub-brand) — one code, employee picks their sub-brand
- **Two-step registration** — org code validated first, then sub-brands shown
- Sub-brand list is ONLY revealed after a valid org code is entered (not publicly enumerable)
- Only **one active code per company** at a time (generating a new one deactivates the old)
- Codes are **reusable** (not single-use) — designed for bulk onboarding
- **No expiry** for MVP — admin can deactivate at any time
- **No approval queue** — employee role is already minimal-privilege
- The registration endpoints are **unauthenticated** (second exception alongside Stripe webhooks), secured by org code validation + rate limiting

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
- **Pros:** Users land directly in the correct sub-brand automatically; no selection step
- **Cons:** More codes for admins to manage and distribute; employees may receive the
  wrong code; admins must generate/revoke codes per sub-brand instead of per company
- **Why rejected:** A single company-level code with a sub-brand selection step during
  registration achieves the same outcome (employee lands in the correct sub-brand)
  with simpler admin management (one code instead of many).

### Default Sub-Brand Only (No User Choice)
- **Pros:** Simplest implementation; no sub-brand names exposed during registration
- **Cons:** Admins must manually reassign every self-registered user from the default
  sub-brand to their correct sub-brand; creates admin bottleneck for companies with
  multiple sub-brands; defeats the self-service benefit of self-registration
- **Why rejected:** The admin reassignment burden scales poorly. Letting employees
  choose their sub-brand during registration eliminates this bottleneck while keeping
  the flow simple (the sub-brand list is only shown after a valid org code is entered).

## Consequences

### Positive
- Large companies can onboard hundreds of employees without admin-per-employee effort
- Employees self-serve and self-select their sub-brand, reducing admin workload
- No admin bottleneck for sub-brand assignment — employees choose during registration
- The invite flow remains available for targeted onboarding (specific sub-brand, specific role)
- Org codes are revocable — admin can cut off self-registration instantly
- Self-registered users have minimal privileges by default, limiting blast radius

### Negative
- Sub-brand names are visible to anyone with a valid org code (mitigated: code is
  required first, and sub-brand names are not sensitive internal data)
- Two unauthenticated endpoints are needed (org code validation + registration),
  increasing the unauthenticated attack surface
- Org codes can be shared beyond the intended audience (e.g., posted on social media)
- Employees may select the wrong sub-brand (can be corrected by admin reassignment)
- A `registration_method` column must be added to the users table to distinguish
  invite-registered from self-registered users

### Risks
- **Org code leaking outside the company:** Mitigated by admin revocability (deactivate
  and generate a new code). The employee role's minimal privileges limit damage from
  unauthorized registrations. Admins can deactivate suspicious accounts.
- **Brute-force code guessing:** Mitigated by rate limiting (5 attempts per IP per
  15-minute window via Redis) and a large keyspace (30^8 ≈ 656 billion combinations
  using a 30-character alphabet that excludes ambiguous characters 0/O, 1/I/L).
- **Information disclosure:** The org code validation endpoint returns sub-brand names
  after a valid code is entered. This is acceptable because: (a) the org code itself
  is the gatekeeper, (b) sub-brand names are not sensitive secrets, and (c) the
  endpoint is rate-limited. Failed code validation still returns a generic error.
- **Employee selects wrong sub-brand:** Mitigated by admin ability to reassign users
  between sub-brands. For companies with a single sub-brand, the selection step is
  skipped (auto-assigned to the only available sub-brand).

## References
- ADR-003: Default Sub-Brand Pattern (guarantees every company has a default sub-brand)
- ADR-005: Cognito over Third-Party Auth (custom attributes carry tenant context)
- `.claude/rules/authentication.md` — Employee Invite Flow (the existing onboarding path)
