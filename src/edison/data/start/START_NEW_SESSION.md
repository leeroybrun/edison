# START_NEW_SESSION

You are starting a fresh work session as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATORS.md`

2. **Load Mandatory Reads**
   See constitution for mandatory file list.

3. **Display Status**
   Run: `edison session status`
   Run: `edison task status`

4. **Report to User**
   Present:
   - Current session status (if any)
   - Tasks in progress (if any)
   - Ready tasks available
   - Any stale items requiring attention

5. **Await Direction**
   Ask user:
   - "What would you like to work on?"
   - Present options based on status

## DO NOT automatically:
- Claim tasks without user approval
- Continue stale work without asking
- Make assumptions about priority

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
edison session start         # Start new session
edison session status        # Check session status
edison task ready            # List ready tasks
edison task claim <id>       # Claim a task
```
