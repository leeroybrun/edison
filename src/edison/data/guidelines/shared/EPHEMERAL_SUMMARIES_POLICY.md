# Ephemeral Summaries Policy (Condensed, Mandatory)

## Default
- Do **not** create ad-hoc summary/report/status files.
- Task + QA files under `.project/tasks/` and `.project/qa/` are the only approved tracking artifacts.

## Track Here Instead
- Task file directories (`todo`, `wip`, `blocked`, `done`, `validated`) – implementation status + delegation logs.
- QA directories (`waiting`, `todo`, `wip`, `done`, `validated`) – validator assignments, findings, verdicts, evidence links.
  - **`qa/waiting/`** = QA created, waiting for task to reach `done/`
  - **`qa/todo/`** = Ready to validate NOW (task is in `done/`)
- Git history – commits tied to task IDs (mention ID in commit body when useful).

## Exceptions
- Validation artefacts stored under `.project/qa/validation-evidence/task-XXX/`, but they must be referenced from the QA document (legacy evidence remains in `docs/project/validation-evidence/`).
- Archive/analysis files go under `docs/archive/` only when explicitly requested.

## Enforcement
- Before marking work complete, ensure there are no stray `*_SUMMARY.md` / `*_ANALYSIS.md` files or similar
- Delete unapproved summaries, note the cleanup in the relevant task file, and rely on the canonical directories instead.
