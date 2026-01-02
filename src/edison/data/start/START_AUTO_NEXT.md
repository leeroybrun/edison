# START_AUTO_NEXT

You are auto-starting work as an **ORCHESTRATOR**.

{{include:start/includes/WORKTREE_CONFINEMENT.md}}
{{include-section:guidelines/includes/EXECUTION_WRAPPER.md#principles}}

## Immediate Actions

1. **Load Constitution**
   Run: `edison read ORCHESTRATOR --type constitutions`

2. **Plan Work Waves (Parallelizable Tasks)**
   Run: `edison task waves`

{{include:start/includes/TASK_PLANNING.md}}

3. **Create Session and Claim**
   Run: `edison session create [--session-id <id>]`
   Run: `edison task claim <task-id>` for each selected task

4. **Begin Work**
   Start implementation immediately.
   Delegate to sub-agents as needed.

{{include:start/includes/EVIDENCE_COMMANDS.md}}

## Selection Priority
1. P1 (Critical) tasks first
2. Tasks with no blockers
3. Tasks matching available agents
4. Smaller tasks for quick wins

{{include:start/includes/SESSION_STATE_MACHINE.md}}

## Key Commands
```bash
edison task waves            # Plan parallelizable waves (todo tasks)
edison session create [--session-id <id>]  # Create a session record (ID auto-infers if omitted)
edison task claim <id>       # Claim tasks
edison session context      # Print current session state and context
edison session next      # Print next recommended actions
```
