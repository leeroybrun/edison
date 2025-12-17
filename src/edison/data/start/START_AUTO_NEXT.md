# START_AUTO_NEXT

You are auto-starting work as an **ORCHESTRATOR**.

{{include:start/includes/WORKTREE_CONFINEMENT.md}}

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATOR.md`

2. **Find Ready Tasks**
   Run: `edison task ready --json`

3. **Analyze Parallelization**
   Identify tasks that can run in parallel:
   - No dependencies on each other
   - Different file scopes
   - Different agent types

4. **Create Session and Claim**
   Run: `edison session create [--session-id <id>]`
   Run: `edison task claim <task-id>` for each selected task

5. **Begin Work**
   Start implementation immediately.
   Delegate to sub-agents as needed.

## Selection Priority
1. P1 (Critical) tasks first
2. Tasks with no blockers
3. Tasks matching available agents
4. Smaller tasks for quick wins

{{include:start/includes/SESSION_STATE_MACHINE.md}}

## Key Commands
```bash
edison task ready --json     # Get ready tasks as JSON
edison session create [--session-id <id>]  # Create a session record (ID auto-infers if omitted)
edison task claim <id>       # Claim tasks
```
