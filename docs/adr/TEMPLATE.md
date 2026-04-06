# ADR-{NUMBER}: {TITLE}
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT ARE ADRs?                                                            ║
# ║                                                                            ║
# ║  Architectural Decision Records document the KEY DECISIONS that shape      ║
# ║  the platform. They capture not just WHAT was decided, but WHY — and       ║
# ║  what alternatives were considered and rejected.                           ║
# ║                                                                            ║
# ║  WHY DO THEY MATTER FOR THE HARNESS?                                       ║
# ║                                                                            ║
# ║  Claude Code can read these to understand the REASONING behind the         ║
# ║  architecture. Without ADRs, Claude might suggest a perfectly reasonable   ║
# ║  alternative approach (like schema-per-tenant) that you've already         ║
# ║  evaluated and rejected for good reasons. ADRs prevent relitigating        ║
# ║  settled decisions and ensure Claude Code works WITH your architecture     ║
# ║  rather than against it.                                                   ║
# ║                                                                            ║
# ║  WHEN TO WRITE A NEW ADR:                                                  ║
# ║  Whenever you make a decision that would be expensive to reverse later     ║
# ║  (technology choice, data model pattern, security approach, etc.).         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

## Status
{Proposed | Accepted | Deprecated | Superseded by ADR-XXX}

## Date
{YYYY-MM-DD}

## Context
{What is the problem or question that prompted this decision? What constraints exist?}

## Decision
{What did we decide? Be specific about the pattern, technology, or approach chosen.}

## Alternatives Considered
### {Alternative 1}
- **Pros:** ...
- **Cons:** ...
- **Why rejected:** ...

### {Alternative 2}
- **Pros:** ...
- **Cons:** ...
- **Why rejected:** ...

## Consequences
### Positive
- ...

### Negative
- ...

### Risks
- ...

## References
- {Links to relevant documentation, articles, or discussions}
