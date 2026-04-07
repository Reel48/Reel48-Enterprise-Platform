---
globs: "**/migrations/**,**/models/**,**/*alembic*"
---

# Rule: Database Migrations
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This is a RULE FILE. Unlike CLAUDE.md files (which are always loaded),    ║
# ║  rule files activate based on FILE PATH PATTERNS. This rule activates      ║
# ║  when Claude Code is working on files matching:                            ║
# ║                                                                            ║
# ║     **/migrations/**                                                       ║
# ║     **/models/**                                                           ║
# ║     **/*alembic*                                                           ║
# ║                                                                            ║
# ║  WHY RULE FILES?                                                           ║
# ║                                                                            ║
# ║  CLAUDE.md files contain general guidance. Rule files contain SPECIFIC,    ║
# ║  domain-targeted rules that only matter in certain contexts. This keeps    ║
# ║  the main CLAUDE.md focused and avoids overwhelming Claude Code with       ║
# ║  irrelevant details when it's working on unrelated files.                  ║
# ║                                                                            ║
# ║  Think of it like a checklist a pilot runs before takeoff — you don't      ║
# ║  need the engine checklist when you're taxiing, but you absolutely need    ║
# ║  it before you take off. Rule files are the checklists that appear         ║
# ║  exactly when they're needed.                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Activates for: **/migrations/**, **/models/**, **/*alembic*

## Mandatory Requirements for Every Migration

### 1. Every tenant-scoped table MUST include isolation columns
- `company_id` (UUID, NOT NULL, foreign key to `companies.id`, indexed)
- `sub_brand_id` (UUID, nullable, foreign key to `sub_brands.id`, indexed)
- Only tables that are truly global (e.g., the `companies` table itself) may omit these

### 2. RLS policies MUST be created in the SAME migration as the table
- Never create a table in one migration and add RLS in another
- This eliminates any window where the table exists without isolation
- Both company isolation AND sub-brand scoping policies are required

### 3. Every migration MUST be reversible
- Include both `upgrade()` and `downgrade()` functions
- `downgrade()` must drop policies before dropping the table
- Test the downgrade path — don't just write it and hope

### 4. Migration naming convention
- Format: `{action}_{entity}_{detail}`
- Examples: `create_products_table`, `add_decoration_options_to_products`, `create_rls_policy_for_orders`

### 5. Always include standard audit columns
- `created_at` (DateTime, server_default=now(), NOT NULL)
- `updated_at` (DateTime, server_default=now(), onupdate=now(), NOT NULL)

### 6. Index strategy
- Always index `company_id` and `sub_brand_id` (RLS performance depends on this)
- Index foreign keys used in JOIN operations
- Add composite indexes for common query patterns (e.g., `company_id + status`)

## Special Cases: Identity & Company-Level Tables

# --- ADDED 2026-04-06 during pre-build harness review ---
# Reason: Only the org_codes exception was documented. companies and sub_brands
# tables have different RLS shapes than standard tenant-scoped tables.
# Impact: Claude Code applies the correct RLS pattern for every Module 1 table.

### `companies` Table (GlobalBase — no tenant FK columns)
The `companies` table IS the tenant identity — it has no `company_id` FK or `sub_brand_id`.
RLS isolates rows by matching the row's own `id` against the session variable:

```sql
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies FORCE ROW LEVEL SECURITY;

-- reel48_admin sees all companies (empty string bypass).
-- Tenant users see only their own company (id matches their company_id).
CREATE POLICY companies_isolation ON companies
    USING (
        current_setting('app.current_company_id', true) IS NULL
        OR current_setting('app.current_company_id', true) = ''
        OR id = current_setting('app.current_company_id')::uuid
    );
```
No sub-brand scoping policy (companies have no sub_brand_id column).

### `sub_brands` Table (CompanyBase — company_id only)
The `sub_brands` table has `company_id` but no `sub_brand_id` (it IS the sub-brand).
RLS uses company isolation only — sub-brand-level filtering is handled by the application
layer when needed (e.g., listing sub-brands visible to a sub_brand_admin).

```sql
ALTER TABLE sub_brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE sub_brands FORCE ROW LEVEL SECURITY;

CREATE POLICY sub_brands_company_isolation ON sub_brands
    USING (
        current_setting('app.current_company_id', true) IS NULL
        OR current_setting('app.current_company_id', true) = ''
        OR company_id = current_setting('app.current_company_id')::uuid
    );
```
No sub-brand scoping policy. A `corporate_admin` (sub_brand_id=NULL) sees all sub-brands
in their company. A `sub_brand_admin` also sees all sub-brands in their company via RLS,
but the application layer filters to show only their assigned sub-brand where appropriate.

### `org_codes` Table
# --- ADDED 2026-04-06 after ADR-007 ---
# Reason: org_codes has company_id but no sub_brand_id (codes are company-level).
# Impact: Claude Code knows this table follows a slightly different RLS pattern.

The `org_codes` table stores company-level registration codes. It has `company_id` but
**no `sub_brand_id`** (org codes are per-company, not per-sub-brand). RLS handling:
- **Company isolation policy: YES** — needed for admin management endpoints where a
  `corporate_admin` should only see their own company's codes.
- **Sub-brand scoping policy: NO** — there is no `sub_brand_id` column to scope on.
- **Public lookup:** The `POST /api/v1/auth/register` endpoint queries this table without
  tenant context (unauthenticated). This lookup uses a direct `WHERE code = :code` query
  and does not go through the RLS-scoped session.

### `invites` Table (CompanyBase — company_id only)
# --- ADDED 2026-04-06 during pre-production harness review ---
# Reason: invites uses CompanyBase (company_id only) with an explicit target_sub_brand_id FK.
# Impact: Claude Code applies company-only isolation, not the standard two-policy pattern.

The `invites` table has `company_id` but **no `sub_brand_id`** column. The sub-brand the
invitee will join is stored as `target_sub_brand_id` (an explicit FK, not the standard
TenantBase `sub_brand_id`). RLS handling:
- **Company isolation policy: YES** — admins should only see invites for their own company.
- **Sub-brand scoping policy: NO** — there is no `sub_brand_id` column to scope on.
  Sub-brand-level filtering (e.g., a `sub_brand_admin` seeing only their own brand's
  invites) is handled in the application layer by filtering on `target_sub_brand_id`.

## Circular Foreign Key Dependencies

# --- ADDED 2026-04-07 after Module 1 Phase 2 ---
# Reason: org_codes.created_by → users and users.org_code_id → org_codes created a
# circular FK that had no documented resolution pattern.
# Impact: Future modules with cross-table FK cycles know the standard approach.

When two tables reference each other (e.g., `org_codes.created_by → users` and
`users.org_code_id → org_codes`), resolve the cycle by **deferring one FK constraint**:

1. Create Table A **without** the FK constraint on the cross-referencing column
   (define the column as a plain UUID, no `ForeignKey`)
2. Create Table B with its FK to Table A
3. Add the deferred FK via `op.create_foreign_key()` after both tables exist
4. In the downgrade, drop the deferred FK **before** dropping Table B

```python
# Example from Module 1: org_codes ↔ users

# upgrade():
#   1. Create org_codes with created_by as plain UUID (no FK)
#   2. Create users with org_code_id FK → org_codes
#   3. op.create_foreign_key("fk_org_codes_created_by_users", "org_codes", "users", ...)

# downgrade():
#   1. op.drop_constraint("fk_org_codes_created_by_users", "org_codes")
#   2. Drop users table
#   3. Drop org_codes table
```

## Common Mistakes to Avoid
- ❌ Creating a table without RLS policies
- ❌ Using raw SQL DDL instead of Alembic operations
- ❌ Forgetting `FORCE ROW LEVEL SECURITY` (allows table owners to bypass RLS)
- ❌ Making `company_id` nullable (every tenant row MUST have a company)
- ❌ Forgetting the downgrade function
- ❌ Using `op.execute()` for table creation (use `op.create_table()` for proper tracking)

## RLS Policy Template
```sql
-- Always include BOTH policies for every tenant-scoped table:

-- Policy 1: Company isolation (required)
-- NOTE: The IS NULL / empty-string checks allow reel48_admin (platform operator)
-- to bypass company isolation. The auth middleware sets company_id to '' for this role.
CREATE POLICY {table}_company_isolation ON {table}
    USING (
        current_setting('app.current_company_id', true) IS NULL
        OR current_setting('app.current_company_id', true) = ''
        OR company_id = current_setting('app.current_company_id')::uuid
    );

-- Policy 2: Sub-brand scoping (required for tables with sub_brand_id)
-- CRITICAL: Must use AS RESTRICTIVE so it is ANDed with company isolation.
-- Without RESTRICTIVE, PostgreSQL combines multiple PERMISSIVE policies with OR,
-- meaning a row passing company_isolation would be visible even if sub_brand_scoping
-- should have excluded it.
CREATE POLICY {table}_sub_brand_scoping ON {table} AS RESTRICTIVE
    USING (
        current_setting('app.current_sub_brand_id', true) IS NULL
        OR current_setting('app.current_sub_brand_id', true) = ''
        OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
    );
```

## RESTRICTIVE vs PERMISSIVE RLS Policies

# --- ADDED 2026-04-07 after Module 1 Phase 4 ---
# Reason: Sub-brand scoping was failing because PostgreSQL combines multiple
# PERMISSIVE policies with OR. A row passing company_isolation was visible even
# when sub_brand_scoping should have filtered it out. This was a data leakage bug.
# Impact: All future sub-brand scoping policies use AS RESTRICTIVE to enforce AND logic.

PostgreSQL has two policy enforcement modes:
- **PERMISSIVE** (default): Multiple PERMISSIVE policies on the same table are combined
  with **OR**. A row is visible if ANY PERMISSIVE policy passes.
- **RESTRICTIVE**: Combined with **AND** against the PERMISSIVE result. A row must pass
  ALL RESTRICTIVE policies AND at least one PERMISSIVE policy.

For Reel48+ tables with both company isolation and sub-brand scoping:
- `{table}_company_isolation` → **PERMISSIVE** (default). This is the primary isolation.
- `{table}_sub_brand_scoping` → **RESTRICTIVE**. This narrows within the company.

This ensures both conditions must pass: the user must be in the correct company **AND**
the correct sub-brand (or have an empty sub_brand_id for corporate/reel48 admins).
