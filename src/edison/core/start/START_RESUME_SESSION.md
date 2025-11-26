# Resume Session

## Session Recovery

You are resuming session: `{{session_id}}`

Run the resume command:
```bash
edison session resume {{session_id}}
```

## Recovery Checklist

1. ✅ Re-read your constitution: `constitutions/ORCHESTRATORS.md`
2. ✅ Check session state: `edison session status`
3. ✅ Review in-progress tasks: `edison tasks list --status=wip`
4. ✅ Check for blocked tasks: `edison tasks list --status=blocked`

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

- Tasks marked WIP remain yours
- QA briefs in progress remain assigned
- Validators may need re-running if state is unclear

## Constitution Reference

Re-read your full instructions at: `constitutions/ORCHESTRATORS.md`
