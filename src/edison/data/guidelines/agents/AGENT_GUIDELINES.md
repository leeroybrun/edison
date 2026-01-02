# Agent Guidelines (Core)

- Own the implementation end-to-end for the task you claim; clarify scope before coding.
- Practice TDD (RED → GREEN → REFACTOR) and keep evidence (fail/pass output + coverage).
- Refresh Context7 for every package listed as post-training in the validator config; store markers.
- Keep task status honest in the task file; log blockers immediately and propose follow-ups with IDs.
- Run configured automation for the task’s validation preset (`edison evidence capture <task-id>`), then review outputs.
- Produce an Implementation Report for every round; include commands run, evidence paths, follow-ups, and delegation notes (if you delegated sub-work).
- Avoid silent shortcuts: no skipping tests, no untracked edits, no bypassing hooks or guards.
- Ask for clarification early when requirements or acceptance criteria are ambiguous.
