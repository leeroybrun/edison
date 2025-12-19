# Edison Core Rules

Core rule files governing Edison behaviors, gates, and policy checks.

- `registry.yml` – canonical YAML registry (version `2.0.0`) used for proactive context queries and anchored rule extraction.

Helper scripts (run from project root):

- `edison rules migrate` – repair legacy `<project-config-dir>/*` source paths (e.g. `.edison/*`) and verify all rule files exist.
- `edison rules verify-anchors` – verify that all fragment anchors in `registry.yml` exist in guideline files.

CLI entrypoint:

- `edison rules` – list/show/locate rules by ID, and `show-for-context <transition|task-type|guidance> <value>` to surface applicable rules before acting.

Task-type rules:

- `task_types/*.yaml` – YAML-backed task type definitions (applies when, validation criteria, delegation guidance, and definition of done) for orchestrator/sub-agent routing and QA checks.
- `file_patterns/*.yaml` – **Core-only, generic** file pattern trigger rules that map glob patterns to validator(s) with rationale for why the pattern matters.
- Pack-specific file pattern rules live at `packs/<pack>/rules/file_patterns/*.yaml` and are loaded only when that pack is active.
