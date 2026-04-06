# ADR-003: Default Sub-Brand Auto-Creation

## Status
Accepted

## Date
2026-04-05

## Context
Reel48+'s sub-brand architecture supports companies with multiple subsidiary brands.
However, many companies — especially smaller ones — will have just one brand. We need
to decide how to handle companies that don't need multiple sub-brands.

The options are: make `sub_brand_id` optional (nullable everywhere with special-case
logic), or require every company to have at least one sub-brand by auto-creating a
default.

## Decision
When a new company is created, the system **automatically creates a default sub-brand**
for that company. This means every company always has at least one sub-brand, and all
data always has a valid `sub_brand_id`. Companies that need multiple sub-brands can
create additional ones; the default sub-brand serves as the "main" brand.

The default sub-brand has:
- `name`: Same as the company name
- `slug`: Derived from the company name
- `is_default`: `true` (flag to identify it as the auto-created default)

## Alternatives Considered

### Make sub_brand_id optional throughout the system
- **Pros:** Simpler initial data model. Companies don't need a sub-brand to get started.
- **Cons:** EVERY query, endpoint, and component that references sub_brand_id must handle
  the NULL case separately. This creates pervasive branching logic: "if sub_brand_id is
  not null, filter by it; otherwise, don't." With 8 modules, this branching adds up to
  hundreds of conditional paths. Claude Code would need to remember the NULL handling
  every time.
- **Why rejected:** The code complexity cost is much higher than creating one extra row
  in the sub_brands table per company.

### Require companies to explicitly create their first sub-brand
- **Pros:** No magic auto-creation. Company setup is fully manual and explicit.
- **Cons:** Bad onboarding UX — a small company that just wants to order shirts now has
  to learn about "sub-brands" before they can use the platform. Adds friction to the
  setup flow.
- **Why rejected:** Enterprise platforms should minimize onboarding friction. The default
  sub-brand provides a working setup out of the box while allowing advanced companies to
  expand later.

## Consequences

### Positive
- `sub_brand_id` is always populated on data rows → simpler queries everywhere
- No NULL-handling branching in application code
- Companies get a working setup immediately after creation
- RLS sub-brand policies work uniformly (no NULL special cases)
- Claude Code can assume `sub_brand_id` is always present, reducing error surface

### Negative
- An extra database row per company (negligible cost)
- Companies with a single brand see a "sub-brand" concept they may not need
  (mitigated by UI labeling: call it "Brand" in the UI, not "Sub-Brand")
- Default sub-brand should not be deletable (requires a business rule check)

### Risks
- Must ensure the default sub-brand creation is atomic with company creation
  (use a database transaction to create both in one operation)
- Must prevent deletion of the default sub-brand (check `is_default` flag before delete)

## References
- "Convention over configuration" — Ruby on Rails design philosophy
- Default tenant pattern in multi-tenant SaaS architectures
