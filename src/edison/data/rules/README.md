# Edison Core Rules

Core rule files governing Edison behaviors, gates, and policy checks.

- `registry.json` – canonical machine-readable registry used by the `scripts/rules` CLI for anchored extraction.
- `registry.yml` – YAML view (version `2.0.0`) derived from the JSON registry, used for proactive context queries.

Helper scripts (run from project root):

- `python .edison/core/scripts/rules_migrate_registry_paths.py` – repair legacy `.edison/*` source paths and verify all rule files exist.
- `python .edison/core/scripts/rules_json_to_yaml_migration.py` – regenerate `registry.yml` from `registry.json`.
- `python .edison/core/scripts/rules_verify_anchors.py` – verify that all fragment anchors in `registry.yml` exist in guideline files.

CLI entrypoint:

- `.edison/core/scripts/rules` – list/show/locate rules by ID, and `show-for-context <transition|task-type|guidance> <value>` to surface applicable rules before acting.

Task-type rules:

- `task_types/*.yaml` – YAML-backed task type definitions (applies when, validation criteria, delegation guidance, and definition of done) for orchestrator/sub-agent routing and QA checks.
- `file_patterns/*.yaml` – File pattern trigger rules that map glob patterns to validator(s) with rationale for why the pattern matters.
