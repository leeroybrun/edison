# Validator Guidelines (Core)

- Stay independent from implementation: do not validate work you implemented or reviewed.
- Load the QA brief, bundle manifest, implementation report, evidence, and git diff before judging.
- Refresh Context7 for any post-training packages in scope; add markers if missing.
- Follow the validator roster and model bindings from the project config; do not substitute models.
- Run required automation or reproduction steps exactly as listed; capture outputs in evidence.
- Record clear findings with severity, category, location, and recommendation; link evidence files.
- Verdicts are `approve`, `reject`, or `blocked`. If blocked, state what is missing and stop.
- Update the QA brief with findings and verdict; store the validator report JSON in the round evidence directory.