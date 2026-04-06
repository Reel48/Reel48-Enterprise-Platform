# ADR-005: Amazon Cognito Over Third-Party Auth Providers

## Status
Accepted

## Date
2026-04-05

## Context
Reel48+ needs user authentication with support for custom claims (company_id,
sub_brand_id, role), enterprise SSO/SAML integration (post-launch), and
scalability to tens of thousands of users across multiple tenants.

We're already committed to AWS infrastructure (ECS, RDS, S3, SES, SQS), so an
AWS-native auth solution has integration advantages.

## Decision
We will use **Amazon Cognito** for authentication, with custom attributes for
multi-tenant context (`custom:company_id`, `custom:sub_brand_id`, `custom:role`).

Frontend integration uses **AWS Amplify** for token management and auth flows.
Backend integration uses **JWT validation** against Cognito's JWKS endpoint.

## Alternatives Considered

### Auth0
- **Pros:** Excellent developer experience. Rich feature set (social login,
  passwordless, MFA). Good documentation. Strong rule/hook system for custom claims.
- **Cons:** Additional vendor dependency and cost (~$0.07/user/month at scale).
  Adds latency for token validation (external service). Another dashboard to
  manage alongside AWS Console. Custom claims require Auth0-specific rules.
- **Why rejected:** Adding another vendor when Cognito meets our needs increases
  operational complexity. The team would need to learn both AWS and Auth0.

### Firebase Authentication
- **Pros:** Simple to set up. Good for mobile apps. Free tier is generous.
- **Cons:** Google ecosystem, not AWS — integration friction with our ECS/RDS
  infrastructure. Custom claims are harder to manage (requires Admin SDK).
  Less suitable for enterprise SSO requirements.
- **Why rejected:** Wrong ecosystem. Cross-cloud integration adds complexity.

### Self-hosted (Keycloak, Ory, etc.)
- **Pros:** Full control. No per-user costs. Highly customizable.
- **Cons:** Significant operational burden — we'd need to host, patch, backup,
  and scale the auth server ourselves. Security is hard to get right. A 2-person
  team cannot afford to maintain critical security infrastructure.
- **Why rejected:** Operational burden is incompatible with team size.

## Consequences

### Positive
- Native AWS integration — no cross-service auth complexity
- Managed service — Cognito handles scaling, uptime, security patches
- Custom attributes support our multi-tenant claims natively
- Built-in support for SAML/OIDC federation (enterprise SSO post-launch)
- Hosted UI available for rapid development (swap for custom UI later)
- AWS Amplify provides polished frontend auth flows

### Negative
- Cognito has a steeper learning curve than Auth0
- Custom attribute values are strings only (UUIDs stored as strings in claims)
- Cognito's hosted UI is functional but not beautiful (plan to replace with
  custom UI before enterprise launch)
- Some operations require Admin SDK (e.g., setting custom attributes on user creation)

### Risks
- Cognito with SSO/SAML can be complex to configure — allocate extra time in
  Module 1 for this
- Custom attribute immutability: some attributes can only be set at creation time.
  Plan the attribute schema carefully before creating the user pool.
- Cognito user pool migration is difficult — get the pool configuration right
  the first time

## References
- Amazon Cognito documentation: https://docs.aws.amazon.com/cognito/
- AWS Amplify Auth: https://docs.amplify.aws/lib/auth/getting-started/
