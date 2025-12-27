# START_CLEANUP

You are cleaning up the project as an **ORCHESTRATOR**.

{{include:start/includes/WORKTREE_CONFINEMENT.md}}

## Immediate Actions

1. **Load Constitution**
   Run: `edison read ORCHESTRATOR --type constitutions`

2. **Identify Stale Items**
   Run: `edison session stale --list`
   Run: `edison task stale --list`

3. **Present Cleanup Plan**
   Show user:
   - Stale sessions to archive
   - Stale tasks to move back to todo
   - QA items requiring attention

4. **Execute with Approval**
   For each stale task:
   ```bash
   edison task reset <task-id> --reason="Stale: moved back to todo"
   ```

   For each stale session:
   ```bash
   edison session archive <session-id>
   ```

5. **Report Results**
   Summarize:
   - Tasks reset
   - Sessions archived
   - Any items needing manual attention

## DO NOT delete any work
- Always preserve history
- Add notes to reset tasks
- Archive, never delete sessions

{{include:start/includes/SESSION_STATE_MACHINE.md}}

## Key Commands
```bash
edison task reset <id>       # Move task back to todo
edison session archive <id>  # Archive stale session
edison project cleanup       # Full cleanup (if implemented)
```
