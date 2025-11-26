# Tracking Integration

Edison can push task lifecycle events to external issue trackers without hardcoded identifiers. Everything is configured through YAML overlays so projects stay portable and auditable.

## Supported tracking systems

The core tracking adapter pattern is provider-agnostic. Edison ships templates and mappings that cover the most common trackers:

- Linear (workspace+team scoped)
- GitHub Issues (org or repository scoped)
- Jira (cloud and data center)
- Shortcut / Clubhouse
- Asana
- Generic webhook targets (for bespoke trackers)

Additional providers follow the same YAML-driven contract; nothing in code hardcodes tracker names or URLs.

## Configure tracking integration (YAML-driven)

1) Define tracker settings in your project overlay, e.g. `.edison/config/tracking.yml`:

   ```yaml
   tracking:
     system: linear               # linear | github | jira | shortcut | asana | webhook
     apiToken: ${LINEAR_TOKEN}    # never commit raw tokens; load via env expansion
     workspace: acme-workspace
     team: web
     projectKey: WEB              # e.g., Jira project key or GitHub repo name
     statusMap:
       todo: backlog
       in_progress: in-progress
       in_review: review
       done: done
   ```

2) If you need shared/org defaults, place them under `.edison/core/config/tracking.yml`; Edison merges defaults → org overrides → project overlay just like other configs.

3) Keep secrets out of YAML by referencing environment variables; Edison’s config loader already resolves `${VAR}` expansions.

4) Regenerate composed manifests or run the orchestrator; the tracking adapter reads the merged YAML and connects to the configured system. No code changes are required when switching providers.

## Task status sync

- Edison treats the task lifecycle (`todo → in_progress → in_review → done`) as the source of truth. Each transition triggers a status sync to the external tracker defined in `tracking.system`.
- Status names in trackers often differ. Use the `tracking.statusMap` YAML block to map Edison states to provider-specific labels or workflow states. Missing mappings fail fast so you don’t silently drift.
- When a task is created, Edison can optionally create the external issue; if an issue key/ID is already known, store it in the task metadata so updates target the existing record.
- Sync is idempotent: Edison updates titles, assignees, and status fields, but leaves tracker-specific custom fields untouched unless explicitly mapped in YAML.

## Extend to custom tracking systems

- Add a new provider module under `src/edison/integrations/tracking/` (e.g., `acmehub.py`) that implements the same adapter shape used by existing providers: `create_task`, `update_status`, `link_comment`, and `hydrate_metadata`.
- Register the provider name in `.edison/config/tracking.yml` under `tracking.system` and add any provider-specific keys under `tracking.providers.<name>` so configuration stays YAML-only.
- Reuse shared utilities (HTTP client wrappers, retry helpers, and auth loaders) instead of duplicating logic; all providers should depend on configuration, never hardcoded URLs or tokens.
- Document expected status values and required fields in the YAML schema to keep validation coherent across projects.

## Troubleshooting common issues

- Authentication failures: verify the `${VAR}` referenced in `apiToken` is exported in your shell and that the token scopes allow issue create/update.
- Status mismatch or no-op updates: ensure every Edison lifecycle state has a corresponding entry in `tracking.statusMap`; provider logs will call out unmapped states.
- Missing issue links: confirm the task metadata includes an external issue key when syncing to an existing record; otherwise enable auto-create in YAML.
- Rate limits: providers like GitHub and Linear throttle bursts. Tune retry/backoff in `tracking.providers.<name>.retry` and prefer batch updates where supported.
- 404 or project not found: double-check `workspace`, `team`, and `projectKey` values—these are always read from YAML overlays (.edison), never from code.

Keep configs in YAML, avoid hardcoded tracker IDs, and validate overlays before running the orchestrator to ensure status syncs remain reliable.
