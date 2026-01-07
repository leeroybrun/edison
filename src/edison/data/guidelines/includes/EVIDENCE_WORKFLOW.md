# Evidence Workflow - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: principles -->
## Evidence Principles

Evidence files prove commands passed. They must show `exitCode: 0`.

**Commands:**
```bash
edison qa round <task-id> --new             # Initialize round (BEFORE implementing)
edison evidence capture <task-id>           # Capture required evidence for this task's preset (config-driven)
edison evidence capture <task-id> --only <name>     # Capture a specific configured CI command
# (Alias supported: --command <name>)
edison evidence show <task-id> --command <name>     # View output for debugging/review
edison evidence status <task-id>            # Check what's missing
```

**Required evidence is configuration-driven** (resolved from the task’s validation preset). Use `edison evidence status <task-id>` to see exactly what is required and what is missing for the current round.
<!-- /section: principles -->

<!-- section: agent-execution -->
## Evidence Workflow (Agents)

**Workflow:**
1. `edison qa round <task-id> --new` - Initialize BEFORE implementing
2. Implement with TDD (RED-GREEN-REFACTOR)
3. Run command → Fix failures → Capture when passing:
   ```bash
   edison evidence capture <task-id>
   ```
4. `edison evidence status <task-id>` - Verify all evidence captured
5. `edison task done <task-id>` - Mark complete (preferred; `task ready <task-id>` is deprecated)

**Critical:** Evidence must show `exitCode: 0` before you proceed to guarded transitions.
Do not skip commands. Do not fabricate evidence. If you capture a failing run, fix and re-capture.
<!-- /section: agent-execution -->

<!-- section: validator-check -->
## Evidence Verification (Validators)

**Check:**
- All evidence files present (`edison evidence status <task-id>`)
- All show `exitCode: 0`
- Outputs look real (not empty/fabricated)
- Implementation report exists

**Reject if:**
- Missing evidence files
- Any `exitCode: != 0`
- Evidence looks fabricated
<!-- /section: validator-check -->

<!-- section: orchestrator-verify -->
## Evidence Orchestration

**Before delegating:** Remind agent to run `edison qa round --new` first.

**After agent returns:**
```bash
edison evidence status <task-id>  # Verify completeness
```
- All commands must show `exitCode: 0`
- If missing: have agent run commands and capture

**If `task done` fails:** Agent must fix issues, not bypass.
<!-- /section: orchestrator-verify -->

<!-- section: context7-bypass -->
## Context7 Bypass

`--skip-context7` bypasses Context7 checks for **verified false positives only**.

```bash
edison task done <task-id> --skip-context7 --skip-context7-reason "verified false positive: <why>"
```

Use ONLY when detection is wrong. Never use to skip required evidence.
<!-- /section: context7-bypass -->
