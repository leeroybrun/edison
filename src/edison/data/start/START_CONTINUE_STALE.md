# START_CONTINUE_STALE

You are reclaiming stale tasks as an **ORCHESTRATOR**.

{{include:start/includes/WORKTREE_CONFINEMENT.md}}
{{include-section:guidelines/includes/EXECUTION_WRAPPER.md#principles}}

## Immediate Actions

1. **Load Constitution**
   Run: `edison read ORCHESTRATOR --type constitutions`

2. **Find Stale Tasks**
   Run: `edison session stale --list`
   (Tasks idle >4 hours)

3. **Present Stale Tasks**
   For each stale task, show:
   - Task ID and title
   - Last activity timestamp
   - Current progress/status
   - Any blockers noted

4. **Reclaim with User Approval**
   For each task user wants to continue:
   Run: `edison task reclaim <task-id>`

5. **Continue Work**
   Resume task workflow from current state.

{{include:start/includes/SESSION_STATE_MACHINE.md}}

## Key Commands
```bash
edison session stale --list  # List stale tasks
edison task reclaim <id>     # Reclaim stale task
edison session resume <id>   # Resume stale session
```
