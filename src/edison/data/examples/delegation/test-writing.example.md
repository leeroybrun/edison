# Test Writing Delegation (test-engineer)

## When to delegate
- Coverage gaps exist around critical paths, regressions, or recently delivered features.
- You need tests built with strict TDD and real integrations (no mocks/stubs).
- Configuration of environments/fixtures should come from YAML, not inline constants.
- Existing tests are flaky, duplicated, or tied to legacy behaviors that need cleanup.

## Delegation prompt template
```
You are test-engineer. Expand tests for <feature/component>.
Context: <bug/feature description, recent regressions>. Constraints: strict TDD, no mocks, config from YAML (<config path>), remove legacy/duplicated tests, reuse shared fixtures/helpers.
Acceptance: <behaviors to cover, edge cases, performance or a11y checks>.
Deliverables: tests + minimal supporting data/fixtures + updates to coverage docs. Run full suite/impacted subset.
Report: scenarios covered, tests run/results, flaky risks, gaps for follow-up.
```

## Expected deliverables
- New tests demonstrating RED→GREEN flow, covering happy paths, edge cases, and failure modes.
- Use of shared fixtures/utilities; redundant or brittle tests removed or refactored.
- YAML-driven configuration/fixtures where applicable; no hardcoded secrets or values.
- Documented rationale for scenarios covered and remaining risks.
- Evidence of executed test commands with results.

## Verification checklist
- Tests run cleanly and deterministically; no mocks; relies on real components/adapters.
- Coverage meaningfully increases on the targeted areas; duplicates eliminated.
- Config/fixtures sourced from YAML; secrets handled via existing config mechanisms.
- Flaky behaviors addressed or documented; cleanup leaves no legacy files.
- CI/local commands documented for rerun; contributors can replicate easily.
