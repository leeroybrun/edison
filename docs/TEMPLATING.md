# Edison Templating & Composition (Unified)

This document is the single source of truth for Edison’s unified composition/templating system. It covers what can be composed, where to place source files, how layering works, and the full templating syntax (includes, variables, conditionals, loops, references, functions).

## 1) What is Composed & Layered

Content types (all markdown unless noted):
- agents
- validators
- guidelines (merge_same_name concat + optional dedupe)
- constitutions
- documents/templates
- rosters (AVAILABLE_AGENTS.md, AVAILABLE_VALIDATORS.md)
- clients (e.g., claude.md)
- state machine docs (generated markdown)

Layer order (always): **core → packs → user → project** (later wins). Subfolders are preserved in outputs when `preserve_structure` is enabled for that type.

Source locations (markdown types):
- Core: `edison.data/{type}/...`
- Packs: `edison.data/packs/{pack}/{type}/...` and `~/.edison/packs/{pack}/{type}/...` and `.edison/packs/{pack}/{type}/...`
- User: `~/.edison/{type}/...`
- Project: `.edison/{type}/...`

User config directory:
- Default is `~/.edison` (from bundled `paths.user_config_dir`)
- Override with `EDISON_paths__user_config_dir` (absolute path or relative to home)

Config layering (YAML):
- Core defaults: `edison.data/config/*.yaml`
- Pack config: `.../packs/{pack}/config/*.yaml` (bundled + user + project packs)
- User config: `~/.edison/config/*.yaml`
- Project config: `.edison/config/*.yaml`
- Project-local config: `.edison/config.local/*.yaml` (uncommitted; per-user per-project)
- Environment overrides: `EDISON_*`

Pack portability:
- `packs.portability.userOnly: warn|error|off` controls behavior when a project activates a pack that only exists in `~/.edison/packs/`.
- `packs.portability.missing: warn|error|off` controls behavior when `packs.active` references a pack that does not exist in any pack root (bundled/user/project).

Overlays vs new files (non-guidelines):
- New content: place at the root of the type directory (e.g., `.edison/agents/api.md`).
- Overrides/overlays: place in an `overlays/` subfolder (e.g., `.edison/agents/overlays/api.md`).
- Guidelines use merge_same_name (concat + dedupe) so they do not use overlays; just place same-name files in each layer root.

Generated outputs:
- `_generated/{type}/...` (agents, validators, guidelines, constitutions, docs, rosters, clients)
- Client-specific outputs resolved by `OutputConfigLoader` from `composition.yaml`.

Guidelines special: `merge_same_name=True` → files with the same name across layers are concatenated (no overlays), then optional DRY dedupe.

## 2) Section & Merge Semantics

Markers (HTML comments):
- Section: `<!-- SECTION: name -->...<!-- /SECTION: name -->`
- Extend:  `<!-- EXTEND: name -->...<!-- /EXTEND: name -->`

Behavior:
- Section merge (default) for all markdown types except guidelines.
- Guidelines: concat-by-name (merge_same_name) + optional dedupe; project_overrides can drop project layer if False.
- DRY dedupe: shingle-based; config via `composition.defaults.dedupe` (shingle_size, min_shingles, threshold) and per-type `composition.content_types.<type>.dedupe`.

## 3) Templating Pipeline (order matters)

1. Section/EXTEND merge (MarkdownCompositionStrategy)
2. Includes
   - `{{include:path/to/file.md}}`
   - `{{include-section:path#section}}`
3. Conditionals
   - `{{if:condition}}...{{/if}}`
   - `{{include-if:condition:path}}`
   - If/else blocks: `{{if:condition}}...{{else}}...{{/if}}`
   - Available condition functions:
     - `has-pack(name)`
     - `config(path)` (truthy)
     - `config-eq(path,value)` (string compare)
     - `env(NAME)`
     - `file-exists(path)` (relative to project_root)
     - `not(expr)`, `and(a,b)`, `or(a,b)`
4. Loops
   - `{{#each collection}}...{{/each}}`
   - Access item properties with `{{this.property}}`
   - Loop index: `{{@index}}`
   - Inline conditionals: `{{#if this.prop}}...{{else}}...{{/if}}`
   - Last item check: `{{#unless @last}}...{{/unless}}`
5. Functions
   - `{{fn:name arg1 arg2}}` (recommended shorthand)
   - `{{function:name("arg")}}` (legacy/explicit form)
6. Variables
   - Config vars: `{{config.key}}`, `{{project.key}}`
   - Context vars: `{{source_layers}}`, `{{timestamp}}`, `{{version}}`, and any custom context vars
   - Path vars: `{{PROJECT_EDISON_DIR}}`, `{{PROJECT_ROOT}}`, `{{REPO_ROOT}}`
7. References
   - `{{reference-section:path#name|purpose}}`
8. Validation
   - Unresolved `{{...}}` markers are reported; section markers stripped

All stages are YAML-configurable; no hardcoded paths.

## 4) Functions Extension (custom Python)

Where to place:
- `functions/` under core, packs, or project.
- Load order: core → active packs → project (later overrides earlier).

Requirements:
- Functions return `str`.
- Args are passed as strings; parse internally if needed.

Layering for Python functions (same precedence model):
- Core → bundled packs → user packs → project packs → user → project (later wins)

Example `functions/tasks.py`:
```python
def task_states(state: str | None = None) -> str:
    states = ["todo", "wip", "done", "validated"]
    if state is None:
        return ", ".join(states)
    return state if state in states else "unknown"
```
Usage:
```
Current state: {{fn:task_states current_state}}
All states: {{fn:task_states}}
```

## 5) Configuration (composition.yaml)

Key knobs:
- `outputs`: per-content-type output paths, filename patterns, preserve_structure
- `defaults.dedupe`: `shingle_size`, `min_shingles`, `threshold`
- `composition.guidelines.mergeSameName`: true (concat + dedupe) vs overlays (false, legacy)
- `functions`: enable/disable loading; optional allowlist/denylist per layer (if configured)

Output resolution: All output paths (agents, validators, guidelines, constitutions, rosters, clients, state machine) are resolved by `OutputConfigLoader`—no hardcoded paths.

## 6) Examples

### Agent with sections and pack override
Core (`edison.data/agents/api.md`):
```
<!-- SECTION: role -->
You are an API builder.
<!-- /SECTION: role -->
```
Pack (`edison.data/packs/nextjs/agents/api.md`):
```
<!-- EXTEND: role -->
You optimize for Next.js APIs.
<!-- /EXTEND: role -->
```
Result: role section merges core + pack; project can extend further.

### Guideline merge_same_name
Core `guidelines/SECURITY.md`, Pack `packs/cloud/guidelines/SECURITY.md`, Project `.edison/guidelines/SECURITY.md` are concatenated (core → pack → project) then deduped.

### Roster template snippet
`data/rosters/AVAILABLE_AGENTS.md`:
```
## Agent Roster
| Agent | Model |
|-------|-------|
{{#each agents}}| {{this.name}} | {{this.model}} |
{{/each}}
Generated: {{timestamp}}
```

### Function usage
```
Allowed states: {{fn:task_states}}
Current: {{fn:task_states current_state}}
```

## 7) Where to put files (by type)
- Agents: `edison.data/agents/`, `edison.data/packs/{pack}/agents/`, `.edison/agents/`
- Validators: `.../validators/`
- Guidelines: `.../guidelines/` (merge_same_name)
- Constitutions: `.../constitutions/`
- Documents/templates: `.../documents/`
- Rosters: `data/rosters/AVAILABLE_*.md` (composable templates)
- Functions: `functions/` in core/packs/project

## 8) Guarantees
- One strategy for markdown, one layered config loader for YAML.
- No legacy modes or IDE-specific composers; adapters use platform components.
- 100% YAML-configurable; zero hardcoded paths.
- Layer order and template pipeline are deterministic and documented above.

_Last updated: 2025-12-04 (unified composition config)_


## 9) Context Variables

Context variables flow through the composition pipeline via `CompositionContext.context_vars`. They are merged with built-in defaults and made available to both simple variable substitution (`{{var}}`) and loop expansion (`{{#each collection}}`).

### Built-in Context Variables (always available)

All registries automatically provide these built-in context variables via `ComposableRegistry.get_context_vars()`:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{name}}` | Entity name being composed | `agents`, `test-engineer` |
| `{{content_type}}` | Content type | `constitutions`, `agents` |
| `{{source_layers}}` | Composition layers | `core + pack(react) + pack(nextjs)` |
| `{{timestamp}}` | ISO timestamp (UTC) | `2025-12-04T13:24:50Z` |
| `{{generated_date}}` | Alias for timestamp | `2025-12-04T13:24:50Z` |
| `{{version}}` | Edison version from config | `1.0.0` |
| `{{template}}` | Source template path | `constitutions/agents.md` |
| `{{output_dir}}` | Output directory (relative) | `.edison/_generated/constitutions` |
| `{{output_path}}` | Full output path (relative) | `.edison/_generated/constitutions/AGENTS.md` |
| `{{PROJECT_EDISON_DIR}}` | Project .edison directory (relative) | `.edison` |

All paths are **relative to project root** for portability.

### Registry-Specific Context Variables

Registries can extend the built-in variables with custom context:

**Constitutions** (`ConstitutionRegistry`):
- `mandatoryReads` - List of mandatory read items (for `{{#each mandatoryReads}}`)
- `optionalReads` - List of optional read items (for `{{#each optionalReads}}`)
- `rules` - List of rules for role (for `{{#each rules}}`)

**Rosters** (`AgentRosterGenerator`, `ValidatorRosterGenerator`):
- `agents` / `validators` - List of entities (for `{{#each agents}}`)
- `generated_header` - Header content

**State Machine** (`StateMachineGenerator`):
- `domains` - State machine domains (for `{{#each domains}}`)
- `mermaid_diagram` - Generated Mermaid diagram

### Custom Context Variables

Registries extend `get_context_vars()` to provide custom variables:

```python
class MyRegistry(ComposableRegistry[str]):
    def get_context_vars(self, name: str, packs: List[str]) -> Dict[str, Any]:
        # Get built-in context (name, timestamp, output_path, etc.)
        context = super().get_context_vars(name, packs)
        
        # Add custom variables
        context["items"] = [{"name": "a"}, {"name": "b"}]  # For {{#each items}}
        context["custom_flag"] = "enabled"  # For {{custom_flag}}
        
        return context
```

These flow through `MarkdownCompositionStrategy` → `TemplateEngine` → transformers.

### Architecture: Config-Driven Composition

All registries use `CompositionConfig` (via `comp_config` property) for typed configuration access:

```
composition.yaml (under composition: key)
       ↓
CompositionConfig (typed domain config)
       ↓
ComposableRegistry.comp_config (lazy property)
       ↓
get_strategy_config(), _resolve_output_paths(), etc.
```

This ensures all composition configuration is properly namespaced under `composition:` in the merged config.

## 10) Additional Details

- Includes resolution order: project → active packs (project packs then bundled packs) → core. Missing include is an error.
- Built-in variables: PROJECT_ROOT, REPO_ROOT, PROJECT_EDISON_DIR, PROJECT_CONFIG_DIR, timestamp; config access via {{config.path}}.
- Preserve structure: when preserve_structure is true for a type (e.g., guidelines by default), subfolders under the content type are kept in outputs. Configurable per type in composition.yaml outputs.*.preserve_structure.
- Errors are fail-fast: missing include/section, unknown condition function, or bad expression raises during composition.
- Dedupe config: composition.defaults.dedupe (shingle_size, min_shingles, threshold) and composition.content_types.<type>.dedupe; guidelines use dedupe by default.
- Overlays apply only when merge_same_name is false (non-guidelines).
- Functions precedence: core → active packs → project; functions live in functions/ directories; later overrides earlier.
- Context vars type: string values for `{{var}}` substitution; list/dict values for `{{#each}}` loops.
