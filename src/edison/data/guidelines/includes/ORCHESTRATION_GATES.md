# Orchestration Gates - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: orchestrator-session-long -->
## Orchestrator Session Gates (Full)

### Delegation-First Orchestration
- Orchestrators MUST delegate implementation work to specialized agents.
- Do not implement features directly; break work into tasks and delegate.
- Track progress via task status and session state.
- Validate agent outputs before accepting.

### Session Tracking Requirements
- Use `edison session status` to understand current session state.
- Keep track of in-flight tasks and their status.
- Record delegation decisions in session logs.
- Update task status as work progresses.

### Worktree Discipline
- All session work must happen in the session worktree.
- Never modify the primary checkout during session work.
- Use Edison worktree commands for branch/worktree lifecycle.
- Verify worktree path before starting work.

### Task State Management
- Tasks flow: todo -> wip -> done -> validated.
- Only claim tasks that are ready (unblocked).
- Mark tasks done only when implementation is complete.
- Blocked tasks must document the blocker.
<!-- /section: orchestrator-session-long -->

<!-- section: start-bootstrap -->
## Bootstrap Gates (Minimal)

- Verify session exists before starting work.
- Check worktree is active and accessible.
- Delegate to agents; do not implement directly.
<!-- /section: start-bootstrap -->
