# Tracking (Agents/Validators/Orchestrators) - Include-Only File
<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

Edison uses *evidence reports* as the durable source of truth for “who did what, when”.

Tracking metadata lives in:
- Implementation report `tracking.*` (per task round)
- Validator report `tracking.*` (per task round + validator)

The UI can derive “active” vs “historical” by combining:
- Report status (`completionStatus=partial`, `verdict=pending`) and timestamps
- Best-effort PID liveness (local only)

<!-- section: agent-tracking -->
## agent-tracking

Agents MUST stamp tracking at the beginning and end of implementation.

```bash
# Start (mandatory)
edison session track start --task <task-id> --type implementation --model <model> [--run-id <uuid>] [--process-id <pid>] [--continuation-id <id>]

# End (mandatory)
edison session track complete --task <task-id>
```

Notes:
- `--model` should be the execution backend (e.g. `codex`, `claude`, `human`).
- If you have a resumable conversation/session identifier (e.g. Codex session id / Zen continuation id),
  pass it via `--continuation-id` so the orchestrator/UI can correlate runs and resume reliably.
<!-- /section: agent-tracking -->

<!-- section: validator-tracking -->
## validator-tracking

Validators MUST stamp tracking at the beginning and end of validation.

```bash
edison session track start --task <task-id> --type validation --validator <validator-id> --model <model> [--run-id <uuid>] [--process-id <pid>] [--continuation-id <id>]
edison session track heartbeat --task <task-id>
edison session track complete --task <task-id> --validator <validator-id> [--run-id <uuid>] [--process-id <pid>]
```
<!-- /section: validator-tracking -->

<!-- section: orchestrator-monitoring -->
## orchestrator-monitoring

Orchestrators can monitor tracking runs:

```bash
edison session track active
edison session track active --json

# Process index (computed from append-only JSONL process events)
edison session track processes --json
```

`active` returns tracking records derived from evidence reports, including:
- `runId` (stable UUID)
- `processId` (PID)
- `model`
- `startedAt` / `lastActive`
- `continuationId` (when provided)
- `isRunning` (best-effort local liveness; `null` when hostname is not local)
- `isStale` (computed from `lastActive` and `orchestration.tracking.activeStaleSeconds`)
<!-- /section: orchestrator-monitoring -->
