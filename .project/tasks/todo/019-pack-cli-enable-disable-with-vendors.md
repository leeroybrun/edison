---
id: 019-pack-cli-enable-disable-with-vendors
title: "Feature: Pack CLI (list/show/enable/disable) + vendor deps + pack exports"
created_at: "2025-12-28T18:22:00Z"
updated_at: "2025-12-28T18:22:00Z"
tags:
  - edison-core
  - packs
  - vendors
  - cli
depends_on:
  - 015-vendors-core-and-cli
  - 017-vendor-adapters-marketplace-open-generic
  - 018-exports-projections-and-wiring
---

# Feature: Pack CLI (list/show/enable/disable) + vendor deps + pack exports

<!-- EXTENSIBLE: Summary -->
## Summary

Add an `edison pack` CLI domain and extend pack metadata/schema to support vendor dependencies and export rules at the pack level.

When enabling a pack via `edison pack enable <pack>`:
- automatically resolves pack dependencies
- installs/syncs vendors required by the resulting enabled pack set
- applies pack-defined export rules
- runs composition and adapter sync (configurable flags)

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add `edison pack` CLI domain:
  - `list` (available packs)
  - `show <pack>` (metadata/config/deps/vendor requirements/exports)
  - `enable <pack>` (updates `.edison/config/packs.yaml`, resolves deps, runs vendor sync + compose + sync)
  - `disable <pack>` (removes from active list, safe dependency checks)
- [ ] Extend pack schema (`pack.yml`) to allow vendor requirements and vendor exports:
  - vendors to install (with plugin/path selectors)
  - exports to expose first-class Edison entities
- [ ] Ensure vendor requirements are computed across the full enabled pack set (including required packs).
- [ ] Ensure enable/disable is deterministic and uses existing pack discovery/resolution logic.
- [ ] Tests for pack CLI enable:
  - modifies `.edison/config/packs.yaml` correctly
  - triggers vendor sync with expected vendors
  - triggers composition with exported entities present

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] `edison pack list` shows all available packs across bundled/user/project pack roots with:
  - name, version, triggers, description
- [ ] `edison pack show <pack>` shows:
  - pack.yml metadata
  - pack dependencies (`requiredPacks`)
  - vendor dependencies and export rules
- [ ] `edison pack enable <pack>`:
  - updates `.edison/config/packs.yaml` `packs.active`
  - resolves dependencies and enables required packs
  - installs/syncs required vendors
  - applies pack exports so exported vendor entities become first-class and appear after composition
  - supports `--no-vendors`, `--no-compose`, `--no-sync`, `--update-vendors`, `--dry-run`
- [ ] `edison pack disable <pack>` blocks if another enabled pack depends on it (unless `--force`).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### Pack schema changes

Update pack schema to allow:
- `vendors`: list of vendor dependency declarations
- `vendorExports`: list of export rules

Packs must remain portable:
- bundled packs can declare vendor dependencies (optional)
- project packs can declare vendor dependencies

**Example `pack.yml` additions (illustrative):**
```yaml
name: my-pack
version: 1.0.0
description: "Example pack that reuses upstream prompts"
triggers:
  filePatterns: ["**/*.py"]

vendors:
  - vendorId: wshobson-agents
    adapter: claude_marketplace
    select:
      plugins: ["python-development"]

vendorExports:
  - vendorId: wshobson-agents
    select:
      plugin: python-development
      type: agents
      names: ["python-pro"]
    export:
      asType: agents
      asName: "python-pro"
```

### Enable flow

Implement enable as:
1. Load current `.edison/config/packs.yaml`.
2. Compute target enabled pack set (pack + dependencies).
3. Write updated packs.yaml (project layer).
4. Run `edison vendor sync` (in-process call) to ensure required vendors are installed and exports applied.
5. Run `edison compose all` (or minimal subset) and platform sync as configured/flagged.

Do not reimplement pack dependency resolution; reuse existing pack registry/toposort logic.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# CLI
src/edison/cli/pack/__init__.py
src/edison/cli/pack/list.py
src/edison/cli/pack/show.py
src/edison/cli/pack/enable.py
src/edison/cli/pack/disable.py

# Pack metadata/schema
src/edison/data/schemas/config/pack.schema.yaml
src/edison/core/composition/packs/metadata.py
src/edison/core/composition/packs/validation.py
src/edison/core/composition/packs/registry.py

# Vendor integration hooks
src/edison/core/vendors/exports.py
src/edison/core/vendors/config.py

# Tests
tests/test_pack_cli_enable_with_vendors_*.py
```

<!-- /EXTENSIBLE: FilesToModify -->
