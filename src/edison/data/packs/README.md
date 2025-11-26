Edison Packs (v2)

Purpose
- Encapsulate tech‑stack knowledge (validators, guidelines, examples)
- Keep Edison core generic; project rules live in `.edison/`

Layout
```
.edison/packs/
  _template/
    pack.yml                 # required manifest
    validators/              # optional context files for validators
    guidelines/              # optional guides referenced via includes
    examples/                # optional examples referenced from docs
  <pack-name>/
    pack.yml
    validators/
    guidelines/
    examples/
```

pack.yml (schema: `.edison/core/schemas/pack.schema.json`)
```
name: typescript
version: 1.0.0
description: TypeScript strict mode patterns and type safety
category: language
tags: [typescript, safety]
triggers:
  filePatterns: ["**/*.ts", "**/*.tsx"]
dependencies: []
validators:
  - codex-context.md
  - claude-context.md
  - gemini-context.md
guidelines:
  - strict-mode.md
  - type-safety.md
  - advanced-types.md
examples:
  - strict-types.ts
  - strict-config.json
  - type-patterns.ts
```

Principles
- SOLID/DRY: one source per rule; reference via includes, no duplication
- Separation: core vs. packs vs. project overlays
- Fail‑fast: invalid packs are rejected at discovery/validation time

Authoring Steps
1) Copy `_template` → `<pack-name>` and edit `pack.yml`
2) Keep names kebab‑case; use SemVer for `version`
3) Add files listed in `validators/guidelines/examples`
4) Run `edison-config --validate` to verify
