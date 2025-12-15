# START_NEW_SESSION

You are starting a fresh work session as an **ORCHESTRATOR**.

## Immediate Actions

1. **Load Constitution**
   Read: `.edison/_generated/constitutions/ORCHESTRATOR.md`

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

{{include:start/includes/SESSION_STATE_MACHINE.md}}

## Key Commands
```bash
edison session create [--session-id <id>]  # Create a new session record (optional worktree; ID auto-infers if omitted)
edison session status        # Check session status
edison task ready            # List ready tasks
edison task claim <id>       # Claim a task
```
