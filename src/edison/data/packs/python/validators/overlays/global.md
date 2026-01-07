# global overlay for Python pack

<!-- extend: tech-stack -->
## Python Validation Context

### Evidence + Commands (for reference)

Automation evidence is captured via `edison evidence capture` into **repo-state snapshots** keyed by a git fingerprint.

- Evidence requirements are **preset-driven**. Do not assume lint/build/type-check are required unless the preset requires them.
- Prefer **reviewing existing evidence outputs** over re-running commands.
- If required evidence is missing/stale, **reject** and ask the orchestrator to run `edison evidence capture` (avoid `--only` unless targeting specific missing commands).
- Use `edison evidence status <task>` (or the QA preflight checklist output) to see which command evidence files are required for the current preset and where they live.

Do not instruct implementers to manually create `command-*.txt` files; evidence must be produced by Edison’s trusted runners.

### Type Safety

- When required by the preset, type-check evidence must pass with zero errors.
- No `Any`/`# type: ignore` without justification.

### Testing

- When required by the preset, test evidence must pass.
- Follow the core **NO MOCKS** policy (mock only system boundaries).
<!-- /extend -->
