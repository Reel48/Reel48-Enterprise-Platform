# Rule: Database Migrations

> ⚠ **SIMPLIFICATION IN PROGRESS** — this file has been stripped as part of the refactor
> documented at `~/.claude/plans/yes-please-write-the-memoized-karp.md`. Previous content
> described a two-dimensional tenant model (`company_id` + `sub_brand_id`), a RESTRICTIVE
> sub-brand RLS policy pattern, and Module 3–9 table schemas that are all being dropped.
> Do **not** reintroduce `sub_brand_id` on any new table. Do **not** write a
> `_sub_brand_scoping` policy. The model base `TenantBase` is being deleted; use
> `CompanyBase` or `GlobalBase` only.

# Activates for: **/migrations/**, **/models/**, **/*alembic*

## What Is Stable

### Every tenant-scoped table
- Include `company_id` (UUID, NOT NULL, FK → companies.id, indexed).
- Do NOT add `sub_brand_id`. Period.

### Every migration MUST be reversible
- Include both `upgrade()` and `downgrade()`.
- `downgrade()` drops policies before dropping the table.

### RLS is required on every tenant-scoped table
- Create the policy in the **same migration** as the table.
- Use `ALTER TABLE {t} ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`.

### Company-only RLS policy template (authoritative)
```sql
CREATE POLICY {table}_company_isolation ON {table}
    USING (
        current_setting('app.current_company_id', true) IS NULL
        OR current_setting('app.current_company_id', true) = ''
        OR company_id = current_setting('app.current_company_id')::uuid
    );
```
The empty-string branch is the `reel48_admin` bypass — platform admins have no `company_id`.

### Standard audit columns
- `created_at` DateTime, server_default=now(), NOT NULL
- `updated_at` DateTime, server_default=now(), onupdate=now(), NOT NULL

### Index strategy
- Always index `company_id` (RLS performance).
- Index FKs used in JOINs.

## What Is In Flux (TBD)

- Model base classes. Target: `GlobalBase` (companies only) and `CompanyBase` (everything else).
  `TenantBase` is being deleted in Session A.
- Full table schema catalog. Most of Modules 3–9 is being dropped. Session D will rewrite the
  surviving schema reference.

## Common Mistakes to Avoid
- ❌ Creating a table without RLS policies.
- ❌ Using raw SQL DDL instead of Alembic operations.
- ❌ Forgetting `FORCE ROW LEVEL SECURITY` (allows table owners to bypass RLS).
- ❌ Making `company_id` nullable.
- ❌ Reintroducing `sub_brand_id` on any new table.
