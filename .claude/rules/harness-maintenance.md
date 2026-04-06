# Rule: Harness Maintenance
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  WHAT IS THIS FILE?                                                        ║
# ║                                                                            ║
# ║  This rule activates when Claude Code is working on ANY harness file:      ║
# ║  CLAUDE.md files, rule files, ADRs, or prompt templates. It enforces       ║
# ║  the maintenance protocol that keeps the harness accurate and current.     ║
# ║                                                                            ║
# ║  WHY THIS RULE?                                                            ║
# ║                                                                            ║
# ║  The harness only works if it reflects reality. An outdated CLAUDE.md      ║
# ║  that tells Claude Code to use Pattern A when the codebase has evolved     ║
# ║  to Pattern B produces code that conflicts with what already exists.       ║
# ║  This rule ensures that every harness edit follows proper process:         ║
# ║  annotated with dates and reasoning, logged in the changelog, and          ║
# ║  consistent with the rest of the harness.                                  ║
# ║                                                                            ║
# ║  CRITICAL: This rule also serves as a SESSION-END REMINDER. At the end    ║
# ║  of every coding session, Claude Code should perform the End-of-Session   ║
# ║  Self-Audit defined in the root CLAUDE.md. This rule file reinforces      ║
# ║  that requirement.                                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Activates for: **/CLAUDE.md, **/.claude/**, **/docs/adr/**, **/prompts/**

## Session-End Self-Audit Checklist

At the END of every Claude Code session (before final commit), answer these:

- [ ] **New pattern?** → Add to relevant CLAUDE.md or create rule file
- [ ] **Pattern violated?** → Update harness to reflect the correct pattern
- [ ] **New decision?** → Write an ADR in docs/adr/
- [ ] **Missing guidance?** → Add to appropriate CLAUDE.md or rule file
- [ ] **Reusable task?** → Create a prompt template in prompts/
- [ ] **Changelog updated?** → Append entry to docs/harness-changelog.md

If the answer to ALL questions is "no changes needed," still log that in the
changelog. The log proves the review happened.

## Rules for Editing Harness Files

### 1. Always annotate additions with date and reason
```markdown
# --- ADDED {YYYY-MM-DD} after {Module X / Session Y} ---
# Reason: {What went wrong or what was learned}
# Impact: {What this update prevents in future sessions}
{The new guidance}
```

### 2. Never remove guidance without replacement
If a rule is wrong, REPLACE it with the correct guidance. Don't leave a gap.
Comment out the old rule with a note explaining why it was superseded:

```markdown
# --- SUPERSEDED {YYYY-MM-DD} ---
# Original: {old guidance}
# Replaced by: {new guidance}
# Reason: {why the original was wrong or insufficient}
```

### 3. Keep harness updates in the same commit as code changes
If you change a pattern in the code, the harness update that reflects that
change MUST be in the same commit. This keeps code and documentation in sync
in the Git history.

### 4. Always update the changelog
Every harness modification gets an entry in `docs/harness-changelog.md`.
Format:
```markdown
## {YYYY-MM-DD} — {Module Name or Session Description}
- **File changed:** {path to file}
- **Change:** {what was added/modified/removed}
- **Reason:** {what prompted the change}
- **Impact:** {what this prevents or enables going forward}
```

### 5. Cross-reference related files
If a change in one harness file affects guidance in another, update BOTH.
For example, if you add a new role to the auth rule, also update:
- Root CLAUDE.md (role model table)
- Backend CLAUDE.md (TenantContext model)
- Frontend CLAUDE.md (UserRole type)
- .claude/rules/authentication.md (role hierarchy and access matrix)

## Post-Module Review Protocol

After completing each module (Modules 1–8), run a dedicated review session:

### Step 1: Pattern Consistency Scan
Review all endpoints, models, and components created in the module. Check:
- Do they all follow the patterns in CLAUDE.md?
- Are naming conventions consistent?
- Do all tables have RLS policies?
- Do all endpoints use TenantContext from JWT?

### Step 2: Rule Effectiveness Review
For each rule file:
- Did it activate when expected?
- Did it prevent the mistakes it was designed to prevent?
- Were there mistakes it should have caught but didn't?

### Step 3: ADR Currency Check
For each existing ADR:
- Is the decision still valid?
- Did implementation reveal any consequences not listed?
- Should the "Risks" section be updated?

### Step 4: Cross-Module Alignment
Compare the completed module's implementation against previous modules:
- Are the same patterns used consistently?
- If a pattern was improved, was the improvement back-ported to earlier modules?
- Are there any implicit conventions that should be made explicit in the harness?

### Step 5: Gap Analysis
Identify scenarios the harness didn't cover:
- What questions came up that had no harness guidance?
- What defaults did Claude Code assume that should be explicitly documented?
- What new patterns emerged that should be templated?

### Step 6: Commit the Review
Commit all changes with the message:
`chore: post-module-{N} harness review — {summary of changes}`

## Harness Health Metrics

Track these in the changelog to measure harness effectiveness over time:

| Metric | What It Measures | Goal |
|--------|-----------------|------|
| Mistakes per module | Times Claude Code output violated a harness rule | Decreasing |
| Harness gaps per module | Scenarios with no harness guidance | Decreasing |
| Rules added per module | New rules created from lessons learned | Stabilizing (fewer needed over time) |
| First-attempt acceptance rate | % of Claude Code output accepted without iteration | Increasing |

## Common Mistakes to Avoid
- ❌ Treating harness maintenance as optional ("we'll update it later")
- ❌ Updating code patterns without updating the harness to match
- ❌ Adding guidance to the wrong file (project-wide rule in a directory CLAUDE.md)
- ❌ Writing vague guidance ("use good naming") instead of specific patterns
- ❌ Skipping the changelog entry (breaks the audit trail)
- ❌ Making a harness change in a separate PR from the code change it relates to
