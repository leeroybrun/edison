---
id: 015-vendors-core-and-cli
title: "Feature: Vendor sources (config + lock + checkout + vendor CLI)"
created_at: "2025-12-28T18:20:00Z"
updated_at: "2025-12-28T18:20:00Z"
tags:
  - edison-core
  - vendors
  - cli
  - config
depends_on: []
related:
  - 016-composition-external-mounts
---

# Feature: Vendor sources (config + lock + checkout + vendor CLI)

<!-- EXTENSIBLE: Summary -->
## Summary

Implement a first-class “vendor sources” subsystem in Edison:
- project config for vendors
- deterministic lock file pinned to commit SHAs
- hybrid checkout strategy: shared bare mirror cache + project-scoped worktree
- a vendor adapter interface (mount discovery)
- `edison vendor` CLI commands to manage vendors (list/show/sync/update/gc)

This task does **not** yet integrate vendors into composition discovery. That is handled by task `016-composition-external-mounts`.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Edison needs to reuse external ecosystems (skills/agents/commands/prompt libraries) without copying their content into Edison core. To do that safely we need:
- deterministic pinning (lock file)
- standardized local checkout locations
- an adapter system to interpret different vendor repo layouts
- CLI commands so developers can install/update vendors required by enabled packs

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add project vendor config at `.edison/config/vendors.yaml`.
- [ ] Add deterministic lock file at `.edison/config/vendors.lock.yaml` containing resolved commit SHAs.
- [ ] Implement hybrid checkout:
  - shared bare mirror cache under `~/.edison/vendors-cache/git/...`
  - per-project worktree under `.edison/vendors/<vendor_id>/worktree` pinned to the lock SHA
- [ ] Define a vendor adapter interface that can return normalized “mounts” (but do not wire mounts into composition yet).
- [ ] Add `edison vendor` CLI domain: `list`, `show`, `sync`, `update`, `gc`.
- [ ] Add tests for config parsing, lock generation, and deterministic checkout behavior (mock only at system boundaries; git/network may be simulated with local repos in tests).

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] `edison vendor sync`:
  - reads `.edison/config/vendors.yaml`
  - installs missing vendors
  - resolves a commit SHA (pin) for each vendor
  - writes/updates `.edison/config/vendors.lock.yaml`
  - checks out `.edison/vendors/<vendor_id>/worktree` at the pinned SHA
  - outputs a deterministic summary in human mode and `--json` mode
- [ ] `edison vendor list` shows vendor id + pinned SHA (if locked) + local checkout status.
- [ ] `edison vendor show <vendor_id>` prints the resolved checkout path and lock details.
- [ ] `edison vendor update [<vendor_id>]` updates the lock to the latest allowed ref (policy-driven; default policy is “no update unless explicitly invoked”).
- [ ] `edison vendor gc` removes unused vendor worktrees that are not referenced by the current lock (safe; requires confirmation unless `--force`).
- [ ] Unit tests cover:
  - parsing vendors.yaml
  - lock file write determinism
  - checkout pins to a specific commit SHA

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### Config files

1) `.edison/config/vendors.yaml` (project-authored)
- Defines vendor sources and adapter settings.
- Must be schema-validated via Edison config schema system.

**Example `vendors.yaml` (illustrative; schema-driven, not hardcoded in code):**
```yaml
vendors:
  cache:
    mode: shared   # shared | project_only | off
    sharedDir: "~/.edison/vendors-cache"
  checkout:
    dir: ".edison/vendors"

  sources:
    - id: wshobson-agents
      kind: git
      url: "https://github.com/wshobson/agents.git"
      ref: "main" # lock resolves this to a commit SHA
      adapter:
        id: claude_marketplace
        config:
          selectPlugins:
            - python-development
            - backend-development

    - id: superpowers
      kind: git
      url: "https://github.com/obra/superpowers.git"
      ref: "v4.0.3"
      adapter:
        id: open_skills_repo
        config:
          includeAgents: true
          includeCommands: true
          includeHooks: true

    - id: my-prompts
      kind: local_path
      path: "../some-repo"
      adapter:
        id: generic_mounts
        config:
          mounts:
            - asType: skills
              baseDir: "skills"
              filePattern: "SKILL.md"
            - asType: agents
              baseDir: "prompts/agents"
              filePattern: "*.md"
```

2) `.edison/config/vendors.lock.yaml` (Edison-managed)
- Records resolved SHAs and any derived metadata required for deterministic builds.
- Must be stable and deterministic (sorted keys, stable ordering).

**Example lock shape (illustrative):**
```yaml
vendorsLockVersion: 1
generatedAt: "2025-12-28T18:20:00Z"
sources:
  - id: superpowers
    resolved:
      url: "https://github.com/obra/superpowers.git"
      sha: "abc123..."
      fetchedAt: "2025-12-28T18:20:10Z"
    checkouts:
      worktreePath: ".edison/vendors/superpowers/worktree"
      cachePath: "~/.edison/vendors-cache/git/<fingerprint>.git"
```

### Checkout strategy (hybrid)

Recommended implementation:
- Global bare mirror cache:
  - `~/.edison/vendors-cache/git/<fingerprint>.git`
- Project worktree:
  - `.edison/vendors/<vendor_id>/worktree`

Flow:
1. Ensure bare mirror exists (clone/fetch).
2. Ensure per-project worktree exists and is checked out at pinned SHA.
3. Do not auto-update unless `vendor update` is invoked.

**Notes on “fingerprint”:**
- Must be derived deterministically from the vendor URL (and any auth-stripped normalization) so cache reuse works across projects.
- Must not embed secrets.

### Adapter interface (v1)

Define `VendorAdapter` with a method like:
- `discover_mounts(checkout_path: Path, config: VendorConfig) -> list[VendorMount]`

Mounts are normalized metadata only at this stage (used by later tasks):
- content_type (string)
- base_dir (path inside repo)
- file_pattern / globs
- key_prefix (namespace base)
- optional exclusions

Do not integrate mounts into composition discovery in this task.

### CLI

Create a new CLI domain folder:
- `src/edison/cli/vendor/` with command modules:
  - `list.py`, `show.py`, `sync.py`, `update.py`, `gc.py`

Follow existing Edison CLI patterns:
- consistent `--json`, `--dry-run`, `--force` semantics
- never hardcode paths; use Edison path resolvers (`get_project_config_dir`, `get_user_config_dir`) and config

### Tests

Use local temporary git repos to test deterministic pinning without network dependency:
- create a temp git repo in test, commit a file, use that as a vendor source (local_path or file:// url)
- verify lock pins to SHA and worktree matches SHA

Also test that:
- running `edison vendor sync` twice is idempotent (no lock churn; no repeated fetch unless required)
- lock ordering is stable

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create (core)
src/edison/core/vendors/__init__.py
src/edison/core/vendors/config.py
src/edison/core/vendors/lock.py
src/edison/core/vendors/checkout.py
src/edison/core/vendors/adapters/__init__.py
src/edison/core/vendors/adapters/base.py

# Create (cli)
src/edison/cli/vendor/__init__.py
src/edison/cli/vendor/list.py
src/edison/cli/vendor/show.py
src/edison/cli/vendor/sync.py
src/edison/cli/vendor/update.py
src/edison/cli/vendor/gc.py

# Schemas/config
src/edison/data/schemas/config/vendors.schema.yaml
src/edison/data/config/vendors.yaml (core defaults, minimal)

# Tests
tests/test_vendors_*.py
```

<!-- /EXTENSIBLE: FilesToModify -->

<!-- EXTENSIBLE: VerificationChecklist -->
## Verification Checklist

- [ ] `pytest -q` passes
- [ ] `edison vendor sync` creates/updates `.edison/config/vendors.lock.yaml`
- [ ] `edison vendor list` shows status deterministically

<!-- /EXTENSIBLE: VerificationChecklist -->


<!-- EXTENSIBLE: Notes -->
## Notes

This task intentionally stops at “vendor checkout + lock + adapter interface”. Composition integration is in task `016-composition-external-mounts`.

<!-- /EXTENSIBLE: Notes -->
