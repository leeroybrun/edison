# Orchestrator ⇄ Validator Runbook

> Purpose: step-by-step guide for orchestrators to launch validators, read results, and drive rejection/escalation loops without hardcoded rosters. The active validator list, models, and trigger patterns are always in the dynamic roster (run `edison read AVAILABLE_VALIDATORS`).

## 0. Preconditions
- Task is in `{{fn:task_state_dir("done")}}/`; QA brief is in `{{fn:qa_state_dir("wip")}}/` with the latest implementation evidence.
- Open the current roster: run `edison read AVAILABLE_VALIDATORS` (never assume counts or names).
- Work from the correct session worktree and log actions in the session Activity Log.

## 1. Trigger validators
1. Generate the manifest the validators will trust:
   ```bash
   edison qa bundle <task-id> [--session <session-id>]
   ```
   Paste the bundle snippet into the QA brief. Validators must reject if the bundle is missing or stale.
2. Determine the wave/trigger set from the roster (run `edison read AVAILABLE_VALIDATORS`). Specialized validators are driven by the triggers listed there; do not guess.
3. Launch validation for the next round (defaults to the next integer if `--round` is omitted):
   ```bash
   edison qa validate <task-id> [--session <session-id>] [--validators <id>...] [--blocking-only]
   ```
   - Use `--validators` only to re-run a failed subset; never to skip required blocking validators.
   - The command resolves triggered validators based on the bundle + roster; captures round number in the evidence tree.

## 2. Interpret validation results
- Evidence lives in `{{fn:evidence_root}}/<task-id>/round-<N>/`.
- Per-validator reports include `status` and `blocksOnFail`; treat any blocking failure as a hard reject.
- `{{config.validation.artifactPaths.bundleSummaryFile}}` is the canonical summary:
  - `approved=true` → QA may move toward `{{fn:semantic_states("qa","done,validated","pipe")}}`.
  - `approved=false` or missing → remain in `{{fn:semantic_state("qa","wip")}}` and start a new round.
- Record outcomes in the QA brief (round, validators run, decision, links to reports) before changing task/QA states.

## 3. Handle rejection cycles
- When any blocking validator rejects:
  - Task stays/returns to `{{fn:task_state_dir("wip")}}/`; QA back to `{{fn:qa_state_dir("waiting")}}/`.
  - Create follow-up tasks for every blocking issue; link them in QA and the session log.
  - Maintain round history: each re-run uses a new `round-<N>` directory; never overwrite prior evidence.
- Non-blocking issues still require follow-up tasks before promotion; keep them unlinked if policy forbids linking optional issues.
- Re-run only after fixes are merged into the session worktree and the bundle is regenerated.

## 4. Escalate when max rounds are exceeded
- The ceiling is configured via `validation.maxRounds` (default: {{config.validation.maxRounds}}; check `{{PROJECT_EDISON_DIR}}/config/*.yml` and pack/project overrides). Do **not** hardcode a number.
- If the upcoming round would exceed `validation.maxRounds`:
  1. Pause automation; do not start another validator run.
  2. Mark the QA round status as `blocked` with rationale.
  3. Escalate to the human QA owner/session lead with the bundle, rejection history, and proposed remediation plan.
  4. Open a blocker task (and link it) to capture the escalation decision and required changes.

## 5. Debug validator failures
- Confirm the roster and triggers: re-open `edison read AVAILABLE_VALIDATORS` and list validator specs via `edison list --type validators --format detail` (then `edison read <name> --type validators`).
- Rebuild the bundle and ensure validators are reading the current manifest.
- Check evidence paths for missing/partial reports; missing reports are treated as failures.
- Rerun a specific validator with `--validators <id> --round <N>` to reproduce without resetting other evidence.
- Verify configuration: `validation.dimensions` sum to 100 and `validation.maxRounds` is present in overlays.
- For model/tooling errors, capture stderr, attach it to the QA brief, and retry with the same round to keep history intact.

## 6. Common patterns and anti-patterns
- **Patterns:** run in waves (global → critical → specialized), attach the bundle to QA, keep per-round directories immutable, and log every validator decision in the session Activity Log.
- **Anti-patterns:** hardcoding validator counts/names, skipping the bundle step, rerunning in the same round and overwriting evidence, promoting QA without `{{config.validation.artifactPaths.bundleSummaryFile}}`, or ignoring specialized validators that triggers require.
