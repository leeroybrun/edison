<!-- TaskID: 2401-wtpl-001-template-variable-design -->
<!-- Priority: 2401 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: design -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave5-sequential -->
<!-- EstimatedHours: 4 -->
<!-- DependsOn: Wave 4 -->
<!-- BlocksTask: 2402-wtpl-002 -->

# WTPL-001: Design Unified Composition Pipeline

## Summary
Design a unified `CompositionPipeline` class that centralizes ALL template processing in Edison. This replaces the current scattered approach (18 different write points, 5 template mechanisms) with a single pipeline that handles includes, sections, config variables, and legacy variables in the correct order.

## Problem Statement

### Current Problems
1. **18 scattered write points** - Each composer writes independently with no common processing
2. **5 different template mechanisms** - Inconsistent handling across composers:
   - Section-based (`{{SECTION:Name}}`) - Agents, Validators only
   - Include system (`{{include:path}}`) - Manual calls
   - Handlebars loops (`{{#each}}`) - Constitutions only
   - Simple replace (`{{source_layers}}`) - Rosters only
   - Jinja2 (`{{ var }}`) - Hooks only
3. **No unified variable substitution** - 42+ hardcoded values can't be externalized
4. **Inconsistent transformation order** - Some apply includes, some don't
5. **No unified reporting** - Can't see missing variables across all files

### Current Write Points (18 total)
| Location | Content Type | Line |
|----------|--------------|------|
| `cli/compose/all.py` | Agents | 185 |
| `cli/compose/all.py` | Guidelines | 207 |
| `cli/compose/all.py` | Validators | 226 |
| `cli/compose/all.py` | Start Prompts | 277, 289 |
| `registries/constitutions.py` | Constitutions | 320 |
| `registries/rosters.py` | Available Agents | 57 |
| `registries/rosters.py` | Available Validators | 121 |
| `registries/rosters.py` | Canonical Entry | 257 |
| `registries/rules.py` | Rules JSON | 445 |
| `registries/schemas.py` | JSON Schemas | 116 |
| `output/state_machine.py` | State Machine | 222 |
| `ide/hooks.py` | Hooks | 107 |
| `ide/settings.py` | Settings | 160 |
| `ide/commands.py` | Commands | 189 |
| `includes.py` | Cache | 221, 232 |

## Objectives
- [ ] Design `CompositionPipeline` class architecture
- [ ] Define transformation order (includes → sections → config → legacy)
- [ ] Define template variable syntax (`{{config.path}}`)
- [ ] Document integration with existing infrastructure
- [ ] Specify unified error/missing variable reporting

## Proposed Architecture

### Unified Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CompositionPipeline                              │
│                                                                     │
│  Single entry point for ALL template processing                     │
│                                                                     │
│  Transformation Order (MUST be this order):                         │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 1. INCLUDES      {{include:path/to/file}}                 │     │
│  │    - Recursive resolution (max depth: 3)                  │     │
│  │    - Must happen FIRST (included content has variables)   │     │
│  └───────────────────────────────────────────────────────────┘     │
│                              ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 2. SECTIONS      {{SECTION:Name}}, {{#each collection}}   │     │
│  │    - Only for content types that use sections             │     │
│  │    - Handled by existing SectionComposer                  │     │
│  └───────────────────────────────────────────────────────────┘     │
│                              ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 3. CONFIG VARS   {{config.project.name}}                  │     │
│  │    - Uses ConfigManager.get() for resolution              │     │
│  │    - Tracks missing variables                             │     │
│  └───────────────────────────────────────────────────────────┘     │
│                              ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 4. LEGACY VARS   {{source_layers}}, {{timestamp}}, etc.   │     │
│  │    - Metadata variables for provenance                    │     │
│  │    - Passed via context dict                              │     │
│  └───────────────────────────────────────────────────────────┘     │
│                              ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 5. VALIDATION    Check for unresolved {{...}} patterns    │     │
│  │    - Warn on missing config vars                          │     │
│  │    - Track all unresolved for report                      │     │
│  └───────────────────────────────────────────────────────────┘     │
│                              ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 6. WRITE         Safe atomic write to disk                │     │
│  │    - Uses write_text_locked() for safety                  │     │
│  │    - Creates parent directories                           │     │
│  └───────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Class Design

```python
class CompositionPipeline:
    """Unified composition pipeline for all template processing."""

    def __init__(self, config: ConfigManager, project_root: Path):
        self.config = config
        self.project_root = project_root
        self._report = CompositionReport()
        self._context: Dict[str, Any] = {}  # Legacy vars like source_layers

    def set_context(self, **kwargs) -> None:
        """Set legacy context variables (source_layers, timestamp, etc.)."""

    def process(self, content: str, content_type: str = "generic") -> str:
        """Apply all transformations in correct order. Returns processed content."""

    def write(self, path: Path, content: str, content_type: str = "generic") -> None:
        """Process content and write to file."""

    def write_json(self, path: Path, data: Dict, indent: int = 2) -> None:
        """Write JSON data (for schemas, rules, settings)."""

    def get_report(self) -> CompositionReport:
        """Get unified report of all processing."""


class CompositionReport:
    """Tracks all composition activity for unified reporting."""

    files_written: List[Path]
    variables_substituted: Set[str]
    variables_missing: Set[str]
    includes_resolved: Set[str]
    warnings: List[str]

    def has_unresolved(self) -> bool: ...
    def summary(self) -> str: ...
```

## Template Variable Syntax

### Config Variables (NEW)
```
{{config.namespace.path.to.value}}
```

The `config.` prefix is required to:
1. Avoid collision with existing patterns
2. Clearly indicate config lookup
3. Make grep/search easy

Examples:
- `{{config.project.name}}` → "wilson-leadgen"
- `{{config.project.database.tablePrefix}}` → "dashboard_"
- `{{config.context7.packages.prisma}}` → "/prisma/prisma"

### Reserved Patterns (DO NOT TOUCH)
```
{{SECTION:*}}           # Section markers
{{EXTENSIBLE_SECTIONS}} # Section placeholders
{{APPEND_SECTIONS}}     # Section placeholders
{{include:*}}           # File includes
{{#each *}}...{{/each}} # Handlebars loops
{{source_layers}}       # Legacy provenance
{{timestamp}}           # Legacy timestamp
{{version}}             # Legacy version
{{template_name}}       # Legacy template
{{PROJECT_EDISON_DIR}}  # Path placeholder
```

### Pattern Matching Order
```python
# Process in this order to avoid conflicts:
INCLUDE_PATTERN = r'\{\{include:([^}]+)\}\}'          # Step 1
SECTION_PATTERN = r'\{\{SECTION:([^}]+)\}\}'          # Step 2
EACH_PATTERN = r'\{\{#each ([^}]+)\}\}'               # Step 2
CONFIG_PATTERN = r'\{\{config\.([a-zA-Z_][a-zA-Z0-9_.]*)\}\}'  # Step 3
LEGACY_PATTERN = r'\{\{(source_layers|timestamp|version|template_name)\}\}'  # Step 4
```

## Integration with Existing Infrastructure

### Uses Existing Code (NO DUPLICATION)
| Need | Existing Code | Location |
|------|---------------|----------|
| Config loading | `ConfigManager` | `core/config/manager.py` |
| Config access | `ConfigManager.get(path)` | `core/config/manager.py` |
| Deep merge | `deep_merge()` | `core/utils/merge.py` |
| Include resolution | `resolve_includes()` | `core/composition/includes.py` |
| Section parsing | `SectionParser` | `core/composition/core/sections.py` |
| Safe writes | `write_text_locked()` | `core/utils/io/core.py` |
| JSON writes | `write_json_atomic()` | `core/utils/io/json.py` |

### Composer Integration
Each composer will receive the pipeline and use it for output:

```python
# Before (scattered)
output_file.write_text(content, encoding="utf-8")

# After (unified)
pipeline.write(output_file, content, "agent")
```

## Config File Organization

### Project Config Example
Location: `.edison/config/project.yml`

```yaml
project:
  name: wilson-leadgen
  packageManager: pnpm

  paths:
    api: apps/api
    dashboard: apps/dashboard

  database:
    tablePrefix: dashboard_

  api:
    prefix: /api/v1/dashboard

  auth:
    provider: better-auth
    roles: [ADMIN, OPERATOR, VIEWER]

  models:
    primary:
      name: Lead
      pluralName: leads

context7:
  packages:
    prisma: /prisma/prisma
    nextjs: /vercel/next.js
```

### Resolution Order (Existing ConfigManager)
1. Core defaults (`edison.data/config/*.yaml`)
2. Pack configs (`.edison/packs/{pack}/config/*.yml`)
3. Project config (`.edison/config/*.yml`)
4. Environment variables (`EDISON_*`)

## Verification Checklist
- [ ] Pipeline class design documented
- [ ] Transformation order specified (includes → sections → config → legacy)
- [ ] Config variable syntax defined (`{{config.path}}`)
- [ ] All reserved patterns documented
- [ ] Integration with existing code identified (no duplication)
- [ ] Unified reporting design specified
- [ ] Example project config provided

## Success Criteria
A complete specification that:
1. Defines single `CompositionPipeline` class
2. Specifies transformation order
3. Documents integration with ALL 18 write points
4. Uses existing infrastructure (ConfigManager, includes, sections)
5. Provides unified error reporting

## File Locations

**Pipeline lives in `composition/core/` (NOT top-level composition/):**
```
src/edison/core/composition/core/pipeline.py   # CompositionPipeline class
src/edison/core/composition/core/report.py     # CompositionReport class
```

**Rationale for `core/` location:**
1. `core/` is the foundation layer - pipeline uses these tools
2. Registries import from `core/` - clear dependency flow
3. Avoids polluting top-level `composition/` with more files
4. Matches existing pattern (composer.py, sections.py are in core/)

**Dependency flow:**
```
composition/core/pipeline.py
├── uses core/sections.py (SectionParser)
├── uses core/paths.py (CompositionPathResolver)
├── uses ../includes.py (resolve_includes)
├── uses config/manager.py (ConfigManager)
└── uses utils/io (write_text_locked)

composition/registries/* → imports from core/pipeline.py
composition/ide/* → imports from core/pipeline.py
adapters/* → imports from core/pipeline.py
```

## Related Files
- `src/edison/core/config/manager.py` - ConfigManager
- `src/edison/core/composition/includes.py` - Include resolution
- `src/edison/core/composition/core/sections.py` - Section handling
- `src/edison/core/composition/core/paths.py` - Path resolution (SINGLE SOURCE OF TRUTH)
- `src/edison/core/composition/core/composer.py` - LayeredComposer
- `src/edison/core/utils/io/` - Write utilities
- `src/edison/cli/compose/all.py` - Main composition entry point
