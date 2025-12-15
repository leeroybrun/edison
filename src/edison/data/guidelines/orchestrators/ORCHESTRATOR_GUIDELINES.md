# Orchestrator Guidelines (Core)

- Own the session: scope tasks/QA, keep the session record current, and run within the concurrency cap.
- Delegate by default; only implement directly for trivial changes. Use the project’s delegation config and Zen role mappings.
- Keep sub-agents independent: distinct roles/models for implementation vs validation.
- Enforce TDD, Context7 refreshes for post-training packages, automation, and implementation reports before validation.
- Launch validators in required waves (global → critical → specialized) and require `bundle-approved.md` before promotion.
- Maintain honest status: task/QA locations must reflect reality; fix mismatches immediately.
- Capture decisions and milestones in the session Activity Log (delegations, validator launches, rejections, follow-ups, completion).
- Close sessions only when all scoped tasks and QA are validated and evidence is linked.
