# Agent Workflow (Core)

1. **Claim & read** – Claim the task in the project tracker; open the paired QA brief. Confirm scope, dependencies, and acceptance criteria. If QA is missing, ping the orchestrator.
2. **Plan** – Identify affected files and risks. Create a small checklist for the change. Decide what tests you will write first.
3. **Context refresh** – For any post-training packages in scope, run Context7 (`resolve-library-id` → `get-library-docs`) and drop `context7-<pkg>.txt` markers in the round evidence directory.
4. **TDD loop** – RED → GREEN → REFACTOR for each behavior. Keep tests isolated and deterministic. Keep coverage ≥90% overall / 100% on new files.
5. **Automation** – Run the project automation suite (type-check, lint, test, build or equivalents). Capture outputs in evidence files.
6. **Document** – Update task file `Status Updates` + `Findings`. Link evidence paths. Note blockers and follow-ups.
7. **Implementation Report** – Fill out the report (see OUTPUT_FORMAT) with commands, Context7 packages, tests, and any follow-ups/delegations.
8. **Ready for validation** – Move QA to `todo/` when implementation is complete, automation is green, and the report + evidence are present. Do not self-validate if you implemented the work.
