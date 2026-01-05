# START_RALPH_LOOP

You are enabling **Ralph Loop** (hard continuation) for this session.

Ralph Loop is an opt-in mode that keeps your session alive across context compactions. When enabled, Edison will inject a continuation prompt after each completion to drive you back into work until session completion criteria are met.

## When to Use Ralph Loop

- Long-running tasks that will span multiple context windows
- Multi-step implementations requiring sustained focus
- Sessions where you want automatic continuation without manual re-prompts

## How to Enable

1. **Identify your session ID**
   ```bash
   edison session status
   ```

2. **Enable hard continuation**
   ```bash
   edison session continuation set <session-id> --mode hard
   ```

   Optional budget overrides:
   ```bash
   edison session continuation set <session-id> --mode hard --max-iterations 20
   edison session continuation set <session-id> --mode hard --stop-on-blocked
   ```

3. **Verify configuration**
   ```bash
   edison session continuation show <session-id>
   ```

## Working in Ralph Loop

Once enabled, follow the standard Edison workflow:

```bash
edison session next <session-id>
```

This command surfaces your next actions. Complete them, and the loop driver will inject continuation prompts until:
- All session tasks are completed
- A blocking issue is encountered (if `--stop-on-blocked` is set)
- The iteration budget is exhausted

## Key Points

- **Edison-native**: Use `edison session next` for guidance, not ad-hoc markers
- **Session completion**: Work is "done" when Edison's completion criteria are met
- **Budget awareness**: Check your iteration budget with `edison session continuation show`

{{include:start/includes/SESSION_STATE_MACHINE.md}}

## Related Commands

```bash
edison session next <session-id>        # Get next recommended actions
edison session continuation show <sid>  # Check continuation settings
edison session continuation set <sid> --mode off  # Disable Ralph Loop
```
