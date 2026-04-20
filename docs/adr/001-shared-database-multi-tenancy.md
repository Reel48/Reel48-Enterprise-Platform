# ADR-001: Shared-Database Multi-Tenancy

> ⚠ **PARTIALLY SUPERSEDED** — the shared-database + RLS decision still stands. However,
> the **two-dimensional tenant model** (`company_id` + `sub_brand_id`) described in parts
> of this ADR is being collapsed to a single dimension (`company_id` only). The sub-brand
> portions of this ADR are superseded by ADR-009 (pending, to be authored in Session D).
> See `~/.claude/plans/yes-please-write-the-memoized-karp.md`.

## Status
Accepted (with sub-brand portions superseded by ADR-009)

## Date
2026-04-05

## Context
Reel48+ is a multi-tenant platform where multiple companies use the same application.
We need to decide how to isolate each company's data. The three common approaches are:
separate databases per tenant, separate schemas per tenant, and shared database with
row-level isolation.

With a 2-3 person team building an MVP over 19 weeks, operational complexity matters.
We also need to support sub-brand isolation WITHIN a tenant, adding a second dimension
of data separation.

## Decision
We will use a **shared-database** approach where all tenants' data lives in the same
PostgreSQL tables, isolated by `company_id` and `sub_brand_id` columns on every row,
enforced by PostgreSQL Row-Level Security (RLS) policies.

## Alternatives Considered

### Database-per-tenant
- **Pros:** Strongest isolation guarantees. Easy to reason about (each tenant is a
  separate world). Simple backup/restore per tenant.
- **Cons:** Operational nightmare at scale — managing dozens of database instances,
  running migrations on each one, connection pool management. Our 2-person team
  cannot maintain this. Sub-brand isolation would require additional logic within
  each tenant database.
- **Why rejected:** Operational overhead is incompatible with team size. We'd spend
  more time managing infrastructure than building features.

### Schema-per-tenant
- **Pros:** Better isolation than shared tables. Single database instance. Per-tenant
  schema customization possible.
- **Cons:** Migrations must run per schema (slow with many tenants). Connection pool
  management is complex. Cross-tenant queries (for platform analytics) require
  querying every schema. Sub-brand isolation still needs additional logic.
- **Why rejected:** Migration complexity grows linearly with tenant count. Cross-tenant
  analytics (which corporate admins need) become expensive.

### Shared database with application-layer isolation (no RLS)
- **Pros:** Simple to implement initially. No PostgreSQL-specific features needed.
- **Cons:** Every query must include `WHERE company_id = ...`. A single forgotten
  filter is a data breach. No database-level enforcement. See ADR-002 for why
  we chose RLS over this approach.
- **Why rejected:** Too risky. Application-layer-only isolation depends on every
  developer (and every Claude Code session) remembering to add the filter. RLS
  provides a safety net.

## Consequences

### Positive
- Single database to manage — simpler operations, backups, and monitoring
- Migrations run once and apply to all tenants
- Cross-tenant analytics queries are straightforward (with proper auth)
- Sub-brand isolation uses the same pattern (just add a `sub_brand_id` column)
- RLS provides database-level enforcement as a safety net

### Negative
- "Noisy neighbor" risk — one tenant with heavy queries could affect others
  (mitigated by connection pooling and query timeouts)
- Must be disciplined about always including `company_id` in indexes (RLS
  performance depends on indexed columns)
- Schema changes affect all tenants simultaneously (no canary deployments per tenant)

### Risks
- RLS misconfiguration could expose data across tenants (mitigated by mandatory
  isolation tests in every module)
- PostgreSQL-specific — harder to migrate to a different database later (acceptable
  risk; PostgreSQL is mature and well-supported)

## References
- PostgreSQL RLS documentation: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- "Multi-tenant SaaS patterns" — AWS Well-Architected Framework
