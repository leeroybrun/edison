# Ephemeral Summaries Policy - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: principles -->
- Do **not** create ad-hoc summary/report/status files.
- Task + QA files under `{{fn:tasks_root}}/` and `{{fn:qa_root}}/` are the only approved tracking artifacts.
- Track progress in tasks/QA and git history (do not create parallel documents):
  - Task directories ({{fn:state_names("task")}}) – implementation status + delegation logs.
  - QA directories ({{fn:state_names("qa")}}) – validator assignments, findings, verdicts, evidence links.
    - `qa/waiting/` = QA created, waiting for task to reach `done/`
    - `qa/todo/` = Ready to validate NOW (task is in `done/`)
  - Git history – commits tied to task IDs (mention ID in commit body when useful).
- Validation artefacts belong under `{{fn:evidence_root}}/<task-id>/round-<N>/` and must be referenced from the QA document.
- Archive/analysis files go under `docs/archive/` only when explicitly requested.
- Before marking work complete, ensure there are no stray `*_SUMMARY.md` / `*_ANALYSIS.md` files or similar; delete unapproved summaries and rely on the canonical directories.
<!-- /section: principles -->
