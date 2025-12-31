---
id: 016-composition-external-mounts
title: "Feature: Composition external mounts (core → vendors → packs → overlay layers) + includes"
created_at: "2025-12-28T18:20:30Z"
updated_at: "2025-12-28T18:20:30Z"
tags:
  - edison-core
  - composition
  - vendors
  - templating
depends_on:
  - 015-vendors-core-and-cli
---

# Feature: Composition external mounts (core → vendors → packs → overlay layers) + includes

<!-- EXTENSIBLE: Summary -->
## Summary

Extend Edison’s composition discovery so that vendor mounts can participate in layering:
- **core → vendor mounts (external roots) → packs → overlay layers**

This must enable standard Edison includes (`{{include:...}}` / `{{include-section:...}}`) to reference exported vendor artifacts via normal content-type paths (no new template syntax).

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Edison’s current composition system discovers content across:
- core bundled data
- packs (bundled/user/project pack roots)
- overlay layers (company/user/project…)

We need to add vendor mounts as additional roots so that external ecosystems can be integrated without copying files into Edison’s own pack trees.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Extend composition path resolution to include vendor external roots per content type.
- [ ] Extend `LayerDiscovery` to scan vendor external roots deterministically and safely.
- [ ] Integrate vendor mounts into discovery order: core → vendors → packs → overlay layers.
- [ ] Keep existing merge semantics and overlays unchanged for existing content.
- [ ] Ensure `ComposedIncludeProvider` continues to work using standard `{{include:content_path/...}}` mapping.
- [ ] Add tests covering discovery precedence and include resolution.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] Given a vendor that exports a skill as `skills/testing/test-driven-development`, `edison compose skills` writes it under `.edison/_generated/skills/testing/test-driven-development/SKILL.md` (or equivalent configured output mapping).
- [ ] Pack-level wrapper files can include vendor-exported content using standard includes:
  - `{{include:skills/testing/test-driven-development}}` works.
- [ ] Vendor mounts do not change behavior for existing packs/projects with no vendor config.
- [ ] Discovery precedence is deterministic and documented:
  - core < vendors < packs < overlay layers
- [ ] Tests cover:
  - vendor content discovered when present
  - overlay layers still override as before
  - include provider resolves includes that target vendor-exported entities

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### Where to integrate vendors into composition

Existing discovery is implemented in:
- `src/edison/core/composition/core/discovery.py` (`LayerDiscovery`)
- `src/edison/core/composition/core/paths.py` (`CompositionPathResolver`)
- `src/edison/core/composition/registries/_base.py` (registry uses discovery)

Add a concept of “external roots” per content type:
- external roots come from vendor subsystem (task 015) and depend on the project lock file and export rules (task 018).
- discovery must treat external roots similarly to pack roots (scan for entities, prevent unsafe shadowing unless explicitly configured).

**Important implementation constraint:**
`ComposedIncludeProvider` resolves `{{include:...}}` by matching the include path against `composition.content_types.<type>.content_path`.
Therefore, vendor-exported entities must appear *within* existing Edison content types (e.g. `skills/...`, `agents/...`), not under a separate ad-hoc path scheme.

### Do not introduce new template syntax

Vendor content must be reachable via normal content-type include paths. This implies:
- exports map vendor artifacts into Edison’s content-type namespace (e.g. `skills/<...>`, `agents/<...>`, etc.)
- `ComposedIncludeProvider` already maps `content_path` to type, and composes entity_name. Ensure vendor-exported entities are discoverable via the registries so includes resolve naturally.

**Example desired include usage inside an Edison pack wrapper:**
```md
## Upstream reference
{{include:skills/testing/test-driven-development}}
```

### Safety / shadowing

By default, vendor-exported entities must not shadow existing Edison entities. If shadowing is allowed, it must be explicit (future: config flag).

### Tests

Add tests that set up a fake project structure with:
- `.edison/config/vendors.yaml`
- `.edison/config/vendors.lock.yaml`
- a vendor worktree with a small exported file under an external root
- run discovery and composition to verify ordering and include resolution

Additionally assert that the existing layer precedence remains intact:
- project overlays still override pack/core
- pack overlays still override vendor/core
- vendor does not override core unless explicitly exported to a shadowing key and shadowing is enabled

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Modify (composition core)
src/edison/core/composition/core/paths.py
src/edison/core/composition/core/discovery.py
src/edison/core/composition/registries/_base.py

# Modify (types manager / config)
src/edison/core/composition/registries/_types_manager.py
src/edison/core/config/domains/composition.py
src/edison/data/config/composition.yaml
src/edison/data/schemas/config/config.schema.yaml

# Tests
tests/test_composition_vendors_*.py
```

<!-- /EXTENSIBLE: FilesToModify -->
