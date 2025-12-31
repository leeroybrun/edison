---
id: 018-exports-projections-and-wiring
title: "Feature: Vendor exports/projections + rosters/registries + recursive adapter sync"
created_at: "2025-12-28T18:21:30Z"
updated_at: "2025-12-28T18:21:30Z"
tags:
  - edison-core
  - vendors
  - composition
  - rosters
  - adapters
depends_on:
  - 015-vendors-core-and-cli
  - 016-composition-external-mounts
  - 017-vendor-adapters-marketplace-open-generic
---

# Feature: Vendor exports/projections + rosters/registries + recursive adapter sync

<!-- EXTENSIBLE: Summary -->
## Summary

Implement explicit **exports/projections** that map mounted vendor artifacts into first-class Edison entities, and ensure exported entities are fully “wired”:
- written by composition
- synced by platform adapters
- included in rosters and registries used for delegation and QA selection

Critical: vendor mounts alone do not create first-class Edison entities. Only exports do.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add export rules in project config (and later pack config):
  - choose vendor items (by logical id or by path/glob)
  - map to Edison content type (agents/validators/skills/commands_md/hooks/etc)
  - map to an Edison entity key (flat name or arbitrary subpath)
- [ ] Implement export resolution producing a deterministic “export manifest” used by:
  - vendor mount integration
  - composition discovery
- [ ] Make exported entities discoverable by composition registries (so `write_type` writes them).
- [ ] Update rosters/registries to reflect exported vendor items as first-class.
- [ ] Update Claude/Cursor/Codex adapters to sync nested paths recursively (preserve relative paths).
- [ ] Add tests for:
  - export selection and aliasing
  - no-shadowing enforcement
  - roster includes exported vendor items
  - adapter sync includes exported nested files

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] Exporting a vendor skill as `skills/testing/test-driven-development`:
  - `edison compose skills` writes it to `.edison/_generated/skills/testing/test-driven-development/SKILL.md`
  - `AVAILABLE_SKILLS.md` includes it as a first-class skill
  - Claude adapter sync writes it under `.claude/skills/testing/test-driven-development/SKILL.md` (or configured equivalent)
- [ ] Exporting a vendor agent as `agents/python-pro`:
  - `edison compose agents` writes it to `.edison/_generated/agents/python-pro.md`
  - `AVAILABLE_AGENTS.md` includes it
- [ ] Export rules can selectively export some skills/commands/agents but not others.
- [ ] Exports can map between types (e.g., export a vendor prompt as a validator) if configured.
- [ ] Shadowing is prevented by default:
  - exporting to an existing entity key fails with a clear error unless an explicit override flag/config is present.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### Export rules

Add export configuration (project-level first; pack-level in task 019) under `.edison/config/vendors.yaml` or a dedicated `.edison/config/exports.yaml`:
- vendor id
- selector (plugin name, or path patterns, or marketplace logical identifiers)
- output mapping:
  - `as_type`: Edison content type
  - `as_name`: entity key (supports subpaths)

**Export model (recommended):**
Exports are the only mechanism that makes vendor content “first-class” Edison entities.
Mounts alone are an internal inventory to enable discovery and includes.

**Example export configuration (illustrative):**
```yaml
vendors:
  exports:
    - vendorId: superpowers
      select:
        type: skills
        paths:
          - "skills/test-driven-development/SKILL.md"
      export:
        asType: skills
        asName: "testing/test-driven-development"  # subpaths supported

    - vendorId: wshobson-agents
      select:
        type: agents
        plugin: python-development
        names:
          - "python-pro"  # logical IDs derived by adapter
      export:
        asType: agents
        asName: "python-pro"
```

### “Virtual alias” discovery

Implement exports by producing alias keys that resolve to vendor file paths at discovery time (no copy/materialize).
This ensures:
- `ComposableRegistry.list_names()` includes exported entity keys
- `write_type()` writes exported entities like native ones

**Conflict semantics (must be explicit):**
- If `asType/asName` matches an existing Edison entity key, export must fail by default.
- Allow shadowing only if:
  - a config flag exists (e.g. `vendors.exports.allowShadowing: true` or per-export flag), AND
  - the export explicitly opts in (`allowShadowing: true`).

### Rosters/registries

Current roster generators read agent metadata via `AgentRegistry` which scans core+pack dirs directly.
To support vendor-exported entities, refactor registries/rosters to enumerate via composition discovery:
- for each entity in composed `agents`, parse frontmatter from its source path (or composed output if necessary)
- similarly for validators and skills

Add new roster generator(s) if needed:
- `AVAILABLE_SKILLS.md` (first-class skill roster)

**Important: “first-class” means:**
- registries used by orchestration should list exported entities exactly as if they were Edison-native
- rosters should not need a separate “vendor roster”; exported items appear in the same tables

### Adapter sync

Ensure adapters sync nested exports:
- Claude adapter sync should use `rglob("*.md")` (agents) and `rglob("SKILL.md")` (skills) and preserve subpaths.
- Cursor/Codex adapters should use similar recursive sync patterns where relevant.

**Do not sync mounts that were not exported.**
Adapters should only sync from `.edison/_generated/...` outputs, which by definition only contain exported (and native) entities.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Vendors exports
src/edison/core/vendors/exports.py
src/edison/core/vendors/config.py
src/edison/core/vendors/lock.py

# Composition integration points
src/edison/core/composition/core/discovery.py
src/edison/core/composition/core/paths.py

# Registries/rosters
src/edison/core/registries/agents.py
src/edison/core/composition/generators/available_agents.py
src/edison/core/composition/generators/available_skills.py (new)
src/edison/data/generators/AVAILABLE_SKILLS.md (new template)
src/edison/data/config/composition.yaml (add skills type and generator)

# Adapters
src/edison/core/adapters/platforms/claude.py
src/edison/core/adapters/platforms/cursor.py
src/edison/core/adapters/platforms/codex.py

# Tests
tests/test_vendor_exports_*.py
tests/test_rosters_vendor_exports_*.py
tests/test_adapter_sync_vendor_exports_*.py
```

<!-- /EXTENSIBLE: FilesToModify -->
