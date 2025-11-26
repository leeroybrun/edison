# Validation Report Format (Core)

Store one JSON report per validator per round under `.project/qa/validation-evidence/<task-id>/round-<N>/`.

```json
{
  "taskId": "<id>",
  "round": 1,
  "validator": "<role>",
  "model": "<model>",
  "verdict": "approve|reject|blocked",
  "summary": "Short headline",
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "category": "security|performance|correctness|ux|testing|docs|other",
      "location": "<file:line> or <area>",
      "description": "What is wrong",
      "recommendation": "What to do",
      "blocking": true
    }
  ],
  "evidence": ["command-test.txt", "screenshot-login.png"],
  "suggestedFollowups": [
    {
      "title": "<short task title>",
      "description": "<detailed task description>",
      "type": "bug|enhancement|refactor|test|docs",
      "severity": "critical|high|medium|low",
      "blocking": false,
      "claimNow": false,
      "parentId": "<parent task id>",
      "files": ["src/path/file.py", "..."],
      "suggestedSlug": "t034-followup",
      "suggestedWave": 1
    }
  ],
  "blockedBy": ["<missing evidence or env>"]
}
```

**Follow-up fields**
- `title` (required): short headline for the task.
- `description` (required): concrete work to do.
- `type`: classify as `bug`, `enhancement`, `refactor`, `test`, or `docs`.
- `severity` (required): `critical`, `high`, `medium`, or `low`.
- `blocking`: mark `true` if the parent task should be blocked until resolved (default `false`).
- `claimNow`: set `true` to auto-claim the follow-up after creation (default `false`).
- `parentId`: parent task ID when creating subtasks.
- `files`: array of affected file paths for traceability.
- `suggestedSlug`: slug to use when generating the new task filename.
- `suggestedWave`: recommended execution wave (1-5) to preserve ordering.

**Rules**
- Record the exact model used; it must match the validator config.
- Keep prior rounds intact; create a new report file per round.
- If `verdict` is `blocked`, list the missing inputs precisely so the orchestrator can unblock you.
