Edison Packs (v2)

Purpose
- Encapsulate tech‑stack knowledge (validators, guidelines, examples)
- Keep Edison core generic; project rules live in `.edison/`

Layout
```
.edison/packs/
  _template/
    pack.yml                 # required manifest
    validators/
      overlays/              # validator context overlays
    guidelines/              # guides referenced via includes
    examples/                # examples referenced from docs
  <pack-name>/
    pack.yml
    validators/
      overlays/
        codex.md             # required: codex validator overlay
        claude.md            # optional: claude-specific overlay
        gemini.md            # optional: gemini-specific overlay
      <role>.md              # pack-provided validator specs
    guidelines/
    examples/
```

Unified Naming Convention
- Directory provides context - no suffixes needed
- Core templates: `.edison/core/<type>/<name>.md`
- Pack overlays: `.edison/packs/<pack>/<type>/overlays/<name>.md`
- Project overlays: `.edison/<type>/overlays/<name>.md`

pack.yml (schema: `.edison/core/schemas/pack.schema.json`)
```yaml
pack:
  id: typescript
  name: TypeScript
  version: 1.0.0

triggers:
  filePatterns:
    - "**/*.ts"
    - "**/*.tsx"

provides:
  guidelines:
    - guidelines/strict-mode.md
    - guidelines/type-safety.md
  validators: []  # discovered by convention from validators/overlays/
  examples:
    - examples/strict-types.ts
```

Principles
- SOLID/DRY: one source per rule; reference via includes, no duplication
- Separation: core vs. packs vs. project overlays
- Fail‑fast: invalid packs are rejected at discovery/validation time
- Unified naming: directory structure provides context, no suffixes

Authoring Steps
1) Copy `_template` → `<pack-name>` and edit `pack.yml`
2) Keep names kebab‑case; use SemVer for `version`
3) Create `validators/overlays/codex.md` (required)
4) Add guidelines and examples as needed
5) Run `edison-config --validate` to verify
