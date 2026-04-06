# Prompt Template: New Table Migration
#
# Use this template when you need Claude Code to create a new database table
# with the full Reel48+ multi-tenancy pattern (Alembic migration + RLS policies).

## Template

```
Create an Alembic migration to add the {TABLE_NAME} table.

### Table Schema
- id: UUID, primary key, auto-generated
- company_id: UUID, FK to companies.id, NOT NULL, indexed
- sub_brand_id: UUID, FK to sub_brands.id, {nullable or NOT NULL}, indexed
- {additional columns with types and constraints}
- created_at: DateTime, server default now()
- updated_at: DateTime, server default now(), on update now()

### Indexes
- ix_{table}_company_id on company_id
- ix_{table}_sub_brand_id on sub_brand_id
- {additional indexes for common query patterns}

### RLS Policies (in the same migration)
1. Enable RLS and Force RLS
2. Company isolation policy: filter by app.current_company_id
3. Sub-brand scoping policy: filter by app.current_sub_brand_id (NULL = see all)

### Migration Requirements
- Migration message format: create_{table_name}_table
- Must include both upgrade() and downgrade()
- downgrade() drops policies before dropping table
- Follow the pattern in existing migrations at migrations/versions/

### Acceptance Criteria
- [ ] Table includes company_id and sub_brand_id
- [ ] RLS policies are in the SAME migration (not a separate one)
- [ ] FORCE ROW LEVEL SECURITY is set
- [ ] Downgrade properly reverses everything
- [ ] All foreign keys are correctly defined
- [ ] Indexes on company_id, sub_brand_id, and any frequently queried columns
```
