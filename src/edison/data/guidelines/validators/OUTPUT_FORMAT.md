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
  "followUps": [
    { "id": "<task-id>", "title": "<short>", "blocking": true }
  ],
  "blockedBy": ["<missing evidence or env>"]
}
```

**Rules**
- Record the exact model used; it must match the validator config.
- Keep prior rounds intact; create a new report file per round.
- If `verdict` is `blocked`, list the missing inputs precisely so the orchestrator can unblock you.
