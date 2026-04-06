# ADR-002: Row-Level Security Over Application-Layer Isolation

## Status
Accepted

## Date
2026-04-05

## Context
Given the shared-database approach (ADR-001), we need to decide HOW to enforce tenant
isolation. The two options are: enforce it purely in application code (adding
`WHERE company_id = X` to every query) or enforce it at the database level using
PostgreSQL's Row-Level Security (RLS) feature.

Reel48+ has an additional complication: dual-dimension isolation. Every query needs
to respect both `company_id` (which company) AND `sub_brand_id` (which subsidiary
brand). A missed filter on either dimension is a security vulnerability.

## Decision
We will use **PostgreSQL Row-Level Security (RLS)** as the primary isolation mechanism,
with **application-layer filtering as defense-in-depth** (belt AND suspenders). Both
layers enforce isolation; either one alone would prevent data leakage.

RLS policies are defined per-table and reference PostgreSQL session variables
(`app.current_company_id` and `app.current_sub_brand_id`) that the auth middleware
sets on every request.

## Alternatives Considered

### Application-layer isolation only
- **Pros:** Database-agnostic. Simple to understand — just add WHERE clauses.
  Works with any ORM.
- **Cons:** A single missed WHERE clause is a data breach. With dual-dimension
  isolation (company + sub-brand), the risk doubles. Code review must catch every
  instance. Claude Code might forget the filter in complex queries, joins, or
  subqueries. No safety net at the database level.
- **Why rejected:** The risk is too high for a platform handling enterprise data.
  With 8 modules, dozens of endpoints, and AI-generated code, the probability of
  at least one missed filter approaches certainty over time.

### ORM-level middleware (automatic query rewriting)
- **Pros:** Transparently adds `WHERE company_id = X` to every query. Works without
  developer awareness.
- **Cons:** Complex to implement correctly for all query types (joins, subqueries,
  raw SQL, aggregations). Hard to debug when it misfires. Doesn't protect against
  raw SQL queries. Fragile across ORM upgrades.
- **Why rejected:** Too fragile and hard to verify correctness. RLS operates at a
  lower level (database engine) where coverage is guaranteed.

## Consequences

### Positive
- Database-level enforcement: impossible to bypass in application code
- Works on ALL queries, including raw SQL, ORM queries, and admin tools
- Dual-dimension isolation (company + sub-brand) handled uniformly
- Defense-in-depth: application-layer filters provide a second check
- Auditable: RLS policies are defined in migrations and version-controlled

### Negative
- PostgreSQL-specific (acceptable trade-off per ADR-001)
- Requires setting session variables on every request (small performance overhead)
- Debugging is harder when RLS silently filters rows (solved with logging)
- `FORCE ROW LEVEL SECURITY` must be set to prevent table owners from bypassing

### Risks
- Forgetting to set session variables means RLS can't filter → auth middleware
  must ALWAYS set them, and tests must verify this
- Performance impact on large tables if isolation columns aren't indexed →
  mandatory indexing on `company_id` and `sub_brand_id`

## References
- PostgreSQL RLS: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- `current_setting()` function: https://www.postgresql.org/docs/current/functions-admin.html
