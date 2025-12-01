# Start New Session

## Pre-Session Checklist

Before beginning work:

1. ✅ Read your constitution: `.edison/_generated/constitutions/ORCHESTRATORS.md`
2. ✅ Load available agents: `.edison/_generated/AVAILABLE_AGENTS.md`
3. ✅ Load available validators: `.edison/_generated/AVAILABLE_VALIDATORS.md`
4. ✅ Confirm the human's request explicitly

## Session Initialization

Run the session start command:
```bash
edison session create --session-id <session-id>
```

This will:
- Create a new session ID
- Initialize the session directory
- Set up git worktree (if configured)
- Record session start time

## Intake Protocol

1. **Confirm Request**: Restate what the human is asking for
2. **Check Stale Work**: Close any work older than the configured threshold
3. **Shared QA Rule**: Leave QA briefs assigned to other sessions alone
4. **Reclaim Stale Tasks**: Tasks idle > threshold can be reclaimed
5. **Select Work**: Choose 1-5 tasks based on scope and dependencies

## Begin Work

After intake is complete:
```bash
edison session next
```

This provides guidance on the next action based on session state.

## Session Loop

Repeat until all tasks complete:
1. Claim task → `edison task claim <task-id>`
2. Implement following TDD and delegation rules
3. Mark ready → `edison task ready <task-id>`
4. Run validators → `edison qa validate <task-id>`
5. Address any rejections

## Session State Machine

Read the generated state machine reference in `.edison/_generated/STATE_MACHINE.md`.
Follow the allowed transitions for session, task, and QA domains defined there—do
not assume defaults. Use `edison session next` to stay aligned with the configured
state machine.

Valid state transitions:
- todo → wip → done → validated

Transition triggers:
- todo → wip: claim a task (`edison task claim <task-id>`)
- wip → done: mark ready after TDD green and evidence (`edison task ready <task-id>`)
- done → validated: run validators (`edison qa validate <task-id>`) and validators approve with no blockers

State diagram: See `.edison/_generated/STATE_MACHINE.md` for the canonical diagram (no embedded copies here).

## Constitution Reference

Your full orchestrator instructions are at: `.edison/_generated/constitutions/ORCHESTRATORS.md`

Re-read this constitution:
- At session start (now)
- After any context compaction
- When resuming after interruption
