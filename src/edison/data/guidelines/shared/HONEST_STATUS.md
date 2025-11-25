# Honest Status (Condensed, Mandatory)

> **Extended Version:** For detailed status reporting rules, evidence expectations, and examples, see [Extended Honest Status Guide](../../guides/extended/HONEST_STATUS.md)

See extended guide: .edison/core/guides/extended/HONEST_STATUS.md

## Honesty Checklist
- [ ] Status entries are factual, timestamped, and live inside the task/QA files.
- [ ] Failures and blockers are logged immediately (include new task IDs when spawning follow-ups).
- [ ] Clear distinction between `todo`, `wip`, `done`, and `validated` directories—files only move forward when criteria are truly met.

## Rules
- Default state for every task file is **NOT complete**. Treat everything in `todo`, `wip`, or `done` as unfinished until validators sign off.
- Only mark a task `validated` after: implementation complete, automated checks passed, QA brief approved by all blocking validators, and evidence links exist.

## Reporting
- Use the `Status Updates` + `Findings` sections in the task file for implementation progress.
- Use the QA file for validator outcomes, evidence links, and follow-up recommendations.
- When validators request new work, create a new numbered task (e.g., `123.1-security-hardening.md`) and reference it from both the original task and QA notes.

Phase docs and the master plan are retired; the directories under `.project/tasks/` and `.project/qa/` are now the single source of truth.
