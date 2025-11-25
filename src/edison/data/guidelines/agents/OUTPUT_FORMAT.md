# Implementation Report Format (Core)

Produce a JSON file per round under the task's evidence directory (e.g., `.project/qa/validation-evidence/<task-id>/round-<N>/implementation-report.json`).

```json
{
  "taskId": "<id>",
  "round": 1,
  "owner": "<name>",
  "model": "<llm or agent>",
  "startedAt": "<iso8601>",
  "completedAt": "<iso8601>",
  "summary": "Short description of what changed",
  "changes": [
    { "path": "<file>", "summary": "what you changed" }
  ],
  "tests": {
    "added": ["<new test names>", "..."],
    "updated": ["..."],
    "evidence": ["command-test.txt", "coverage-summary.txt"]
  },
  "automation": {
    "typeCheck": "command-type-check.txt",
    "lint": "command-lint.txt",
    "test": "command-test.txt",
    "build": "command-build.txt"
  },
  "context7": ["<package1>", "<package2>"] ,
  "delegations": [
    { "to": "<agent|role>", "model": "<model>", "scope": "<what was delegated>", "result": "<summary>" }
  ],
  "followUps": [
    { "id": "<task-id>", "reason": "<why>", "blocking": true }
  ],
  "blockers": ["<remaining issues>"]
}
```

**Rules**
- Keep filenames stable across rounds; append new rounds instead of overwriting.
- If no automation step applies, record `"n/a"` with justification.
- Ensure `context7` lists every post-training package you queried (one marker file per package).
