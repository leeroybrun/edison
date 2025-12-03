# START_CONTINUE_STALE

You are reclaiming stale tasks as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATORS.md`

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
edison session stale --list  # List stale tasks
edison task reclaim <id>     # Reclaim stale task
edison session resume <id>   # Resume stale session
```
