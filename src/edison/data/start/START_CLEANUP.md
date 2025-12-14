# START_CLEANUP

You are cleaning up the project as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATOR.md`

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

## Session State Machine

Read the generated state machine reference in `.edison/_generated/STATE_MACHINE.md`.
Follow the allowed transitions for session, task, and QA domains defined there—do
not assume defaults. Use `edison session next` to stay aligned with the configured
state machine.

Valid task state transitions:
- todo → wip → done → validated

Transition triggers:
- todo → wip: claim a task (`edison task claim <task-id>`)
- wip → done: mark done after TDD green and evidence
- done → validated: run validators (`edison qa validate <task-id>`)

Task states can also transition to blocked if blockers are encountered.

State diagram: See `.edison/_generated/STATE_MACHINE.md` for the canonical diagram (no embedded copies here).

## Key Commands
```bash
edison task reset <id>       # Move task back to todo
edison session archive <id>  # Archive stale session
edison project cleanup       # Full cleanup (if implemented)
```
