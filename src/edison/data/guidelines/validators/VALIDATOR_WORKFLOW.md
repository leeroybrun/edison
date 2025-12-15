# Validator Workflow (Core)

<!-- section: workflow -->
1. **Intake** – Open the QA brief and bundle manifest; confirm the task/QA state matches the manifest. If QA is missing or duplicated, halt and notify the orchestrator.
2. **Load context** – Read the implementation report, evidence files, and git diff. Note the automation outputs and Context7 markers for post-training packages.
3. **Prepare checks** – Map changed files to required validators; verify your validator role/model matches the config. Set up any local services the QA specifies.
4. **Execute** – Run the prescribed commands/tests. Capture output to evidence files under the current `round-<N>/` directory.
5. **Findings** – Document issues with severity, category, location, and recommended fix. Note any follow-up tasks needed and whether they are blocking.
6. **Verdict** – Choose `approve` if all blocking issues are resolved, `reject` if blocking issues remain, or `blocked` if you could not complete validation. Never self-approve when evidence is missing.
7. **Report** – Write the validator report (`validator-<id>-report.md`, see OUTPUT_FORMAT) and update the QA brief with findings, evidence links, and verdict. Include the model you used.
8. **Handoff** – If rejected or blocked, ensure the QA returns to `waiting/` and follow-ups are created. If approved, signal readiness for bundle approval.
<!-- /section: workflow -->
