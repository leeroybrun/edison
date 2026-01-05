<!-- SECTION: embedded -->
## Context & Continuation

<!-- ANCHOR: cwam-guidance -->
### Context Window Management (CWAM)

Keep working methodically and protect context:
- Prefer small, deterministic steps over rushing.
- Avoid pasting large logs; summarize and reference artifacts by path.
- If approaching limits, follow the project's compaction/recovery guidance.
<!-- END ANCHOR: cwam-guidance -->

<!-- ANCHOR: continuation-guidance -->
### Continuation

Continue working until the Edison session is complete:
- Use the loop driver: `edison session next <session-id>`
- Keep validators independent from implementers.
- Do not stop early when work remains.
<!-- END ANCHOR: continuation-guidance -->
<!-- /SECTION: embedded -->
