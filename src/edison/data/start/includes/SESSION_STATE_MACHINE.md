## Session State Machine

Read the generated state machine reference: run `edison read STATE_MACHINE`.
Follow the allowed transitions for session, task, and QA domains defined there—do
not assume defaults. Use `edison session next` to stay aligned with the configured
state machine.

Valid task state transitions:
- todo → wip → done → validated

Transition triggers (high level):
- todo → wip: claim a task (`edison task claim <task-id>`)
- wip → done: mark done after TDD green and evidence
- done → validated: validate via the QA workflow (`edison qa validate …`)

Task states can also transition to blocked if blockers are encountered.

State diagram: run `edison read STATE_MACHINE` for the canonical diagram (no embedded copies here).
