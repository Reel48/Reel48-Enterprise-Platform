# ADR-004: REST-First API Design

## Status
Accepted

## Date
2026-04-05

## Context
We need to decide on the API style for the Reel48+ platform. The main options are
REST, GraphQL, and gRPC. The choice affects frontend-backend coupling, caching,
tooling, developer experience, and Claude Code's ability to generate correct endpoints.

Our team is 2-3 developers, and we need to ship an MVP in 19 weeks. Time-to-production
is a critical factor.

## Decision
We will use **RESTful APIs** for the initial build. GraphQL may be evaluated post-launch
if frontend data-fetching patterns indicate clear benefits (e.g., excessive
over-fetching or too many round trips).

## Alternatives Considered

### GraphQL
- **Pros:** Flexible queries — frontend fetches exactly the data it needs. Single
  endpoint reduces API surface area. Strong typing with SDL. Great for complex,
  nested data (products with decoration options, sizes, brand assets).
- **Cons:** Steeper learning curve for a small team. More complex server implementation
  (resolvers, dataloader patterns for N+1). Caching is harder (no HTTP caching by
  default). Authorization must be implemented at the resolver level, complicating the
  multi-tenancy pattern. Claude Code generates less reliable GraphQL resolvers compared
  to REST endpoints.
- **Why rejected:** The implementation complexity is not justified for an MVP. Our data
  model is relatively straightforward (CRUD operations on well-defined entities). The
  team's time is better spent building features than debugging resolver authorization.

### gRPC
- **Pros:** High performance. Strong typing with Protocol Buffers. Great for
  service-to-service communication.
- **Cons:** Not browser-native (requires a proxy). Tooling is more complex. Overkill
  for a monolithic backend serving a web frontend.
- **Why rejected:** We have a single backend serving a single frontend. gRPC's
  advantages (performance, strong contracts) don't justify the complexity for this
  use case.

## Consequences

### Positive
- Simple, well-understood pattern — fast to develop and debug
- HTTP caching works naturally (GET requests are cacheable)
- Claude Code generates high-quality REST endpoints consistently
- Rich ecosystem of tools (Swagger/OpenAPI, Postman, curl)
- Multi-tenancy middleware integrates cleanly with REST routing

### Negative
- Over-fetching: some endpoints may return more data than the frontend needs
  (mitigated with sparse field selection: `?fields=id,name,price`)
- Multiple round trips for complex pages (mitigated with aggregate endpoints
  like `/api/v1/dashboard`)
- Adding new fields requires endpoint versioning consideration

### Risks
- If the frontend's data needs become very complex (deeply nested, highly variable
  per view), we may need to reconsider GraphQL post-launch

## References
- OpenAPI Specification: https://swagger.io/specification/
- "REST vs GraphQL" decision framework — Thoughtworks Technology Radar
