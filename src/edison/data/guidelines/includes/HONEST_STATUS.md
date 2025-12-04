# Honest Status - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- SECTION: agent-rules -->
## Honest Status (Agents)

### Core Rule
Default state for every task file is **NOT complete**. Report EXACT state, not hopeful state.

### NEVER Mark Complete When
- [ ] TODOs remain in code
- [ ] Tests are failing
- [ ] Tests are skipped (`.skip()`, `.todo()`)
- [ ] Build is broken
- [ ] Type errors exist
- [ ] Lint errors exist
- [ ] Evidence is missing
- [ ] Any blockers exist

### Status Rules
- Status entries are factual and timestamped
- Failures and blockers are logged immediately
- Include new task IDs when spawning follow-ups
- Use `blocked` status when genuinely blocked

### Directory Semantics
| Directory | Meaning |
|-----------|---------|
| `todo/` | Not started |
| `wip/` | In progress |
| `done/` | Implementation complete, awaiting validation |
| `validated/` | All validators approved |

Files only move forward when criteria are truly met.

### Reporting
- Use `Status Updates` + `Findings` sections in task file for progress
- Use QA file for validator outcomes and evidence links
- When validators request new work, create new numbered task
<!-- /SECTION: agent-rules -->

<!-- SECTION: orchestrator-verify -->
## Status Verification (Orchestrators)

### Before Accepting Work
- [ ] Verify status matches reality (not just claimed status)
- [ ] Check for hidden blockers
- [ ] Verify evidence files actually exist
- [ ] Confirm automation outputs are current

### Status Validation Checks
1. **If claimed "complete"**:
   - All tests actually pass?
   - Build succeeds?
   - No TODOs in changed files?
   - Evidence directory populated?

2. **If claimed "ready for validation"**:
   - Implementation report exists?
   - Automation evidence files present?
   - QA brief paired?

3. **If claimed "blocked"**:
   - Blocker documented?
   - Follow-up task created?
   - Reasonable escalation path?

### Red Flags
🚩 **Investigate immediately:**
- Status changed without new commits
- "Complete" with no evidence files
- Multiple quick status changes
- Skipped tests in "complete" task
<!-- /SECTION: orchestrator-verify -->
