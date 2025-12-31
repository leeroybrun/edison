---
id: 017-vendor-adapters-marketplace-open-generic
title: "Feature: Vendor adapters (Claude marketplace + open skills repo + generic mounts)"
created_at: "2025-12-28T18:21:00Z"
updated_at: "2025-12-28T18:21:00Z"
tags:
  - edison-core
  - vendors
  - adapters
  - claude
depends_on:
  - 015-vendors-core-and-cli
---

# Feature: Vendor adapters (Claude marketplace + open skills repo + generic mounts)

<!-- EXTENSIBLE: Summary -->
## Summary

Implement vendor adapters that can interpret external ecosystems and produce normalized mounts:
- **Claude marketplace adapter**: supports `.claude-plugin/marketplace.json` and multi-repo plugin sources
- **Open skills repo adapter**: supports Superpowers-like layouts (`skills/**/SKILL.md`, plus optional agents/commands/hooks)
- **Generic mounts adapter**: user-defined mounts for “any repo”

These adapters must integrate with vendor sync/lock so `edison vendor sync` can compute mounts consistently.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Implement adapter interface methods that:
  - validate vendor repo layout and config
  - return normalized mounts
- [ ] Claude marketplace adapter must:
  - parse `.claude-plugin/marketplace.json`
  - support selecting specific plugins (by name/version)
  - resolve plugin `source` entries that may point to other repos (GitHub or git URL)
  - normalize plugin roots (respect marketplace `metadata.pluginRoot` when present)
- [ ] Open skills adapter must:
  - discover skills under `skills/**/SKILL.md`
  - optionally discover agents (`agents/*.md`), commands (`commands/*.md`), hooks (`hooks/**`)
- [ ] Generic mounts adapter must:
  - accept a list of mount rules in vendors.yaml
  - support arbitrary content types/globs
- [ ] Add unit tests with fixtures derived from:
  - a minimal fake marketplace repo
  - a minimal fake open-skills repo
  - a minimal generic mount repo

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] With a vendor config for a local test marketplace repo:
  - `edison vendor sync` succeeds
  - `edison vendor show <id> --json` includes normalized mounts for selected plugins
- [ ] With a vendor config for a local open-skills repo:
  - mounts include `skills` entries pointing at `skills/**/SKILL.md`
- [ ] With a vendor config using generic mounts:
  - mounts exactly match the configured globs and content types
- [ ] Adapter outputs are deterministic (stable ordering) and validated.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### Adapter registry

Implement a registry that maps adapter IDs to adapter classes, e.g.:
- `claude_marketplace`
- `open_skills_repo`
- `generic_mounts`

Selection is driven by `.edison/config/vendors.yaml` per vendor.

### Claude marketplace specifics

The adapter must understand:
- marketplace file: `.claude-plugin/marketplace.json`
- plugin entries containing `name`, `source`, `commands`, `agents`, `skills`, etc.
- plugin `source` may be:
  - relative path (same repo)
  - GitHub repo (clone)
  - generic git URL (clone)

**Marketplace compliance requirement:**
The adapter must be schema-tolerant:
- ignore unknown keys (future marketplace versions)
- handle absent optional keys
- respect `metadata.pluginRoot` when present (plugin paths may be relative to it)

Important: a single marketplace vendor can require multiple checkouts (one per unique plugin source). The adapter should normalize this by producing mounts that include a `repo_ref` identifier so the vendor subsystem can ensure required checkouts exist and are pinned.

**Normalization recommendation:**
Represent “sub-repos” as vendor-internal checkouts:
- vendor id remains the marketplace id (e.g. `wshobson-agents`)
- plugin repo checkouts are stored under `.edison/vendors/<vendor_id>/repos/<repo_fingerprint>/worktree`
so that the lock file can pin each unique repo source independently.

### Tests

Prefer local repos in tests to avoid network dependency:
- create a temp “marketplace repo” with a minimal marketplace.json
- create a temp “plugin repo” referenced by the marketplace and assert mount resolution

Include at least these fixtures:
- plugin source as relative path
- plugin source as a separate repo reference
- selection filtering (only some plugins selected)

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create/Modify (vendors)
src/edison/core/vendors/adapters/claude_marketplace.py
src/edison/core/vendors/adapters/open_skills_repo.py
src/edison/core/vendors/adapters/generic_mounts.py
src/edison/core/vendors/adapters/registry.py

# Schemas/config defaults
src/edison/data/config/vendors.yaml
src/edison/data/schemas/config/vendors.schema.yaml

# Tests
tests/test_vendor_adapters_*.py
```

<!-- /EXTENSIBLE: FilesToModify -->
