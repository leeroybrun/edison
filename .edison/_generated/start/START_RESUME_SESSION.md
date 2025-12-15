# Resume Session

## Session Recovery

You are resuming session: `{{session_id}}`

Check session status:
```bash
edison session status {{session_id}}
```

Then resume work by running:
```bash
edison session next {{session_id}}
```

## Recovery Checklist

1. ✅ Re-read your constitution: `.edison/_generated/constitutions/ORCHESTRATOR.md`
2. ✅ Check session state: `edison session status`
3. ✅ Review in-progress tasks: `edison task list --status=wip`
4. ✅ Check for blocked tasks: `edison task list --status=blocked`

## State Assessment

The session may have been interrupted due to:
- Context compaction
- System restart
- Manual pause
- Error recovery

## Resume Protocol

1. **Load Context**: Read all task documents for in-progress work
2. **Check Dependencies**: Verify no blocking tasks have new issues
3. **Continue Work**: Pick up where you left off

```bash
edison session next
```

## Recovery Notes

- Tasks marked wip remain yours
- QA briefs in progress remain assigned
- Validators may need re-running if state is unclear

## Session State Machine

Read the generated state machine reference in `.edison/_generated/STATE_MACHINE.md`.
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

State diagram: See `.edison/_generated/STATE_MACHINE.md` for the canonical diagram (no embedded copies here).

## Constitution Reference

Re-read your full instructions at: `.edison/_generated/constitutions/ORCHESTRATOR.md`