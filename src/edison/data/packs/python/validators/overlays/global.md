# global overlay for Python pack

<!-- extend: tech-stack -->
## Python Validation Context

### Evidence + Commands (for reference)

Automation evidence is captured by the orchestrator via `edison evidence capture` into the current evidence round.

- Prefer **reviewing existing evidence files** over re-running commands.
- If evidence is missing/stale, **reject** and ask the orchestrator to re-run capture.
- If you are explicitly instructed to reproduce locally, use the repo-configured CI commands and write output to the evidence files shown below.

```bash
{{fn:ci_command("type-check")}} > {{fn:evidence_file("type-check")}} 2>&1
{{fn:ci_command("lint")}} > {{fn:evidence_file("lint")}} 2>&1 || true
{{fn:ci_command("test")}} > {{fn:evidence_file("test")}} 2>&1
{{fn:ci_command("build")}} > {{fn:evidence_file("build")}} 2>&1 || echo "No build configured"
```

### Type Safety

- `{{fn:ci_command("type-check")}}` must pass with zero errors.
- No `Any`/`# type: ignore` without justification.

### Testing

- `{{fn:ci_command("test")}}` must pass.
- Follow the core **NO MOCKS** policy (mock only system boundaries).
<!-- /extend -->

