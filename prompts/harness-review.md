# Prompt Template: Post-Module Harness Review
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS?                                                             ║
# ║                                                                            ║
# ║  Use this prompt template AFTER completing each module (Modules 1–8) to    ║
# ║  run a dedicated harness review session. This is the deeper review that    ║
# ║  catches patterns the per-session audits might miss.                       ║
# ║                                                                            ║
# ║  WHY?                                                                      ║
# ║                                                                            ║
# ║  Individual sessions can miss the big picture. A module might be built     ║
# ║  across 5-10 sessions, and subtle drift can accumulate. This review        ║
# ║  catches drift before it compounds into the next module.                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

## Template

```
Run a post-module harness review for Module {N}: {MODULE_NAME}.

This module was built across approximately {X} sessions and includes the
following key files:

### Backend Files Created/Modified
- {list models, routes, services, migrations}

### Frontend Files Created/Modified
- {list pages, components, hooks}

### Review Tasks

#### 1. Pattern Consistency Scan
Review every file created in this module and verify:
- All SQLAlchemy models inherit from TenantBase
- All tables have RLS policies in their migrations
- All API endpoints use TenantContext from JWT (never accept tenant IDs as params)
- All endpoints return the standard { data, meta, errors } format
- All list endpoints have pagination
- All role checks are explicit (not relying solely on RLS)
- Naming is consistent: snake_case tables/columns, plural resource URLs
- All service methods include defense-in-depth tenant filtering

Report any violations found.

#### 2. Harness Gap Analysis
For each file in the module, identify:
- Were there any decisions made that had NO harness guidance?
- Were there any harness rules that were ambiguous or incomplete?
- Were there any NEW patterns established that aren't yet in the harness?

List each gap and propose the harness update to fill it.

#### 3. Rule File Effectiveness
For each rule file (.claude/rules/*.md), report:
- Did it activate during this module's development?
- Did it prevent any mistakes?
- Were there mistakes it SHOULD have caught but didn't?
- Should any rules be added, modified, or removed?

#### 4. ADR Check
Review all existing ADRs (docs/adr/001-006) and report:
- Were any decisions effectively reversed during implementation?
- Did implementation reveal new consequences to document?
- Should a new ADR be written for any decision made in this module?

#### 5. Cross-Module Alignment (if Module > 1)
Compare this module's patterns with previously completed modules:
- Are the same patterns used? List any inconsistencies.
- Were any patterns IMPROVED in this module? If so, should the improvement
  be back-ported to earlier modules?

#### 6. Harness Updates
Based on findings from steps 1-5, make the following harness updates:
- Update relevant CLAUDE.md files with new/corrected patterns
- Update or create rule files as needed
- Write new ADRs if architectural decisions were made
- Create new prompt templates if reusable task patterns emerged

#### 7. Changelog Entry
Append a detailed entry to docs/harness-changelog.md covering:
- Module name and completion date
- All harness files modified
- Summary of what changed and why
- Gaps identified for upcoming modules
- Harness health metrics update

### Acceptance Criteria
- [ ] Every file in the module has been reviewed for pattern compliance
- [ ] All harness gaps identified and filled
- [ ] Rule file effectiveness assessed
- [ ] ADRs verified for accuracy
- [ ] Cross-module alignment verified (if applicable)
- [ ] All harness updates committed
- [ ] Changelog entry committed
```
