# START_AUTO_NEXT

You are auto-starting work as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATORS.md`

2. **Find Ready Tasks**
   Run: `edison task ready --json`

3. **Analyze Parallelization**
   Identify tasks that can run in parallel:
   - No dependencies on each other
   - Different file scopes
   - Different agent types

4. **Create Session and Claim**
   Run: `edison session start --auto`
   Run: `edison task claim <task-id>` for each selected task

5. **Begin Work**
   Start implementation immediately.
   Delegate to sub-agents as needed.

## Selection Priority
1. P1 (Critical) tasks first
2. Tasks with no blockers
3. Tasks matching available agents
4. Smaller tasks for quick wins

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
edison task ready --json     # Get ready tasks as JSON
edison session start --auto  # Start session with auto-select
edison task claim <id>       # Claim tasks
```
