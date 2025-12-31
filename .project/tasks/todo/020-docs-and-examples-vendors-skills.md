---
id: 020-docs-and-examples-vendors-skills
title: "Docs: Vendors + skills + pack enable workflow (marketplaces + superpowers + generic repos)"
created_at: "2025-12-28T18:22:30Z"
updated_at: "2025-12-28T18:22:30Z"
tags:
  - edison-core
  - docs
  - vendors
  - skills
depends_on:
  - 019-pack-cli-enable-disable-with-vendors
---

# Docs: Vendors + skills + pack enable workflow (marketplaces + superpowers + generic repos)

<!-- EXTENSIBLE: Summary -->
## Summary

Add end-user documentation for the new vendor + skills + pack enable system, including real examples:
- importing selected plugins from a Claude marketplace repo
- importing Superpowers-style skill repos
- importing arbitrary repos via generic mounts
- exporting vendor items into first-class Edison agents/skills/commands/validators
- using standard Edison `{{include:...}}` to wrap vendor content in Edison-specific glue

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add docs that explain:
  - vendor config and lock files
  - `edison vendor` commands
  - `edison pack enable` flow and flags
  - exports vs mounts, and why exports are required for first-class inclusion
  - how includes work with exported entities
- [ ] Provide copy/paste examples for:
  1) Claude marketplace vendor (selecting a plugin subset)
  2) Superpowers-style vendor
  3) Generic mounts vendor
- [ ] Provide a “best practices” section:
  - keep exports curated
  - avoid shadowing core Edison entities
  - prefer Edison wrappers for enforcing Edison-specific workflow requirements

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] A developer with no prior Edison knowledge can follow the docs to:
  - enable a pack
  - install required vendors
  - export a vendor skill and see it appear in rosters
  - include that exported vendor skill content inside an Edison-authored wrapper
- [ ] Docs explicitly state determinism and locking semantics.
- [ ] Docs explain compatibility with Claude plugin marketplaces (including plugin sources in other repos).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
docs/VENDORS.md (new)
docs/SKILLS.md (new or extend existing)
docs/PACKS.md (new or extend existing)
README.md (add short pointers)
```

<!-- /EXTENSIBLE: FilesToModify -->

