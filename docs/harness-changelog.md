# Harness Changelog
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This is the HARNESS CHANGELOG — a chronological log of every change       ║
# ║  made to the development harness (CLAUDE.md files, rule files, ADRs,       ║
# ║  and prompt templates).                                                    ║
# ║                                                                            ║
# ║  WHY DOES IT EXIST?                                                        ║
# ║                                                                            ║
# ║  The changelog serves three critical purposes:                             ║
# ║                                                                            ║
# ║  1. AUDIT TRAIL: Proves that harness reviews are actually happening.       ║
# ║     If there's no changelog entry after a module, the review was skipped.  ║
# ║                                                                            ║
# ║  2. KNOWLEDGE CAPTURE: Records WHY each change was made. Six months from   ║
# ║     now, you'll wonder "why does this rule exist?" The changelog tells     ║
# ║     you which module, which session, and which mistake prompted it.        ║
# ║                                                                            ║
# ║  3. TREND TRACKING: Over time, the changelog reveals whether the harness   ║
# ║     is improving. Fewer reactive updates per module = the harness is       ║
# ║     maturing. More gaps found = the project is hitting new territory.      ║
# ║                                                                            ║
# ║  HOW TO USE:                                                               ║
# ║  Append a new entry at the TOP of the log (newest first) after every       ║
# ║  session audit, post-module review, or reactive update. Follow the         ║
# ║  format shown in the initial entry below.                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

---

## 2026-04-06 — Rule File Frontmatter Fix (Pre-Stage 1)

**Type:** Reactive update
**Author:** Claude Code

### Changes Made
- **File:** All 6 rule files in `.claude/rules/`
  - **Change:** Added YAML frontmatter with `globs:` patterns for conditional activation
  - **Reason:** Rule files used comment-based activation patterns (`# Activates for: ...`) which Claude Code does not parse. Without proper `globs:` frontmatter, all rules load in every session regardless of which files are being edited, wasting context and diluting focused guidance.
  - **Impact:** Rules now activate only when Claude Code works on matching file paths (e.g., `database-migrations.md` only loads when editing files in `**/migrations/**` or `**/models/**`).

- **File:** `Reel48+ Harness Companion Guide.docx`
  - **Change:** Updated Section 3.1 to explain YAML frontmatter requirement for rule file activation.
  - **Reason:** The guide described rule activation conceptually but did not mention the required frontmatter format.
  - **Impact:** Team members understand that rule files require `globs:` frontmatter, not just descriptive comments.

### Glob patterns applied
| Rule File | Globs |
|-----------|-------|
| `database-migrations.md` | `**/migrations/**,**/models/**,**/*alembic*` |
| `api-endpoints.md` | `**/api/**,**/routes/**,**/endpoints/**` |
| `authentication.md` | `**/auth/**,**/security/**,**/middleware/auth*,**/login*,**/cognito*` |
| `testing.md` | `**/tests/**,**/test_*,**/*_test.py,**/*.test.ts,**/*.spec.ts` |
| `s3-storage.md` | `**/storage/**,**/upload*,**/s3*,**/assets/**,**/media/**` |
| `harness-maintenance.md` | `**/CLAUDE.md,**/.claude/**,**/docs/adr/**,**/prompts/**` |

---

## 2026-04-06 — Repo Structure Fix (Pre-Stage 1)

**Type:** Reactive update
**Author:** Claude Code

### Changes Made
- **File:** All harness files (CLAUDE.md, .claude/rules/*, backend/CLAUDE.md, frontend/CLAUDE.md, docs/*, prompts/*)
  - **Change:** Moved from `outputs/` subdirectory to the repository root
  - **Reason:** Claude Code auto-discovers CLAUDE.md and .claude/rules/ relative to the repo root. Files nested under `outputs/` would not be loaded automatically at session start.
  - **Impact:** Harness now activates correctly — CLAUDE.md loads every session, rule files trigger on matching file paths, and directory-level CLAUDE.md files load when working in backend/ or frontend/.

- **File:** `.gitignore`
  - **Change:** Updated `.claude/` ignore rule to use `.claude/*` with `!.claude/rules/` exception
  - **Reason:** The original `.claude/` rule ignored the entire directory including rule files. The new pattern ignores session data while tracking rule files in git.
  - **Impact:** Rule files are now version-controlled while session data remains excluded.

- **File:** `Reel48+ Harness Companion Guide.docx`
  - **Change:** Updated version to v2.1. Revised Section 9 (Getting Started Checklist) steps 1–2 to reflect that harness files are already at the repo root, not requiring a manual copy step.
  - **Reason:** The guide's setup instructions referenced the old workflow of copying files into a repo. Files now ship in the correct location.
  - **Impact:** New team members following the guide will not encounter misleading setup instructions.

### Notes
- No harness guidance content was changed — only file locations and documentation references.
- The `outputs/` directory has been removed entirely.

---

## 2026-04-06 — Initial Harness Creation (Pre-Stage 1)

**Type:** Initial setup
**Author:** Harness Owner

### Files Created
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Root harness — project-wide conventions, stack, multi-tenancy, API patterns |
| `frontend/CLAUDE.md` | Frontend conventions — Next.js, Cognito, components, state management |
| `backend/CLAUDE.md` | Backend conventions — FastAPI, SQLAlchemy, auth middleware, testing |
| `.claude/rules/database-migrations.md` | Rule: RLS policies, indexes, reversible migrations |
| `.claude/rules/api-endpoints.md` | Rule: tenant context from JWT, response format, role checks |
| `.claude/rules/authentication.md` | Rule: Cognito, JWT validation, invite flow, role hierarchy |
| `.claude/rules/testing.md` | Rule: three test categories, factories, coverage targets |
| `.claude/rules/s3-storage.md` | Rule: tenant-scoped paths, pre-signed URLs, upload validation |
| `.claude/rules/harness-maintenance.md` | Rule: self-audit, post-module review, changelog protocol |
| `docs/adr/TEMPLATE.md` | ADR template for future decisions |
| `docs/adr/001-shared-database-multi-tenancy.md` | Decision: shared DB over separate databases/schemas |
| `docs/adr/002-rls-over-application-isolation.md` | Decision: RLS over app-layer-only isolation |
| `docs/adr/003-default-sub-brand-pattern.md` | Decision: auto-create default sub-brand per company |
| `docs/adr/004-rest-before-graphql.md` | Decision: REST-first API design |
| `docs/adr/005-cognito-over-third-party-auth.md` | Decision: Cognito over Auth0/self-hosted |
| `prompts/crud-endpoint.md` | Template: building complete CRUD APIs |
| `prompts/new-table-migration.md` | Template: creating tables with RLS |
| `prompts/react-component.md` | Template: building React components |
| `prompts/test-suite.md` | Template: comprehensive test suites |
| `prompts/harness-review.md` | Template: post-module harness review |
| `docs/harness-changelog.md` | This file — change audit trail |

### Decisions Made
- Harness structure follows the Specification → Harness → Output model from the Build Process Plan
- All CLAUDE.md files include rich inline comments explaining WHY each section exists
- Rule files use file-path-based activation patterns
- ADRs document the 5 key architectural decisions from the Technical Architecture doc
- Harness maintenance protocol embedded directly in root CLAUDE.md so Claude Code reads it every session
- Three maintenance triggers defined: end-of-session audit, post-module review, reactive updates

### Baseline Metrics
- Total harness files: 21
- Total lines of guidance: ~2,800
- Modules completed: 0 (pre-build)
- Known gaps: None yet (first session hasn't happened)

### Next Steps
- Run pilot session (Week 3 of Stage 1) to validate the harness
- Adjust based on pilot results and log changes here
- Begin Stage 2 infrastructure provisioning using the harness

---

<!--
TEMPLATE FOR NEW ENTRIES (copy and fill in):

## {YYYY-MM-DD} — {Module Name / Session Description}

**Type:** {Session audit | Post-module review | Reactive update}
**Author:** {Name or role}
**Module:** {Module number and name, if applicable}

### Changes Made
- **File:** {path}
  - **Change:** {what was added/modified/removed}
  - **Reason:** {what prompted the change}
  - **Impact:** {what this prevents or enables}

### Gaps Identified
- {Description of gap and which upcoming module it affects}

### Metrics
- Mistakes caught by harness this session: {N}
- Mistakes NOT caught (harness gaps): {N}
- First-attempt acceptance rate: {%}

### Notes
{Any additional observations or context}

-->
