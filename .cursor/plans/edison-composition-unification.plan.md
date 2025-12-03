````javascript
# Edison Composition Unification - Comprehensive Architecture

## Executive Summary

Consolidate all template processing into a single `TemplateEngine` with a dramatically simplified section system. This plan implements a unified 4-concept model, two-phase composition architecture, and eliminates 8+ redundant markers.

**Key Changes from Original Tasks:**

- Rename `CompositionPipeline` to `TemplateEngine`
- **UNIFIED SECTION SYSTEM** - Single `<!-- SECTION: name -->` syntax replaces anchors, placeholders, etc.
- **DRAMATICALLY SIMPLIFIED** - From 12+ markers down to 4 core concepts
- Two-phase composition (compose ALL files first, THEN process templates)
- Add prerequisite task WTPL-000 (syntax consolidation)
- Fix WUNI-004: RulesRegistry ALREADY extends BaseRegistry
- Reorder dependencies: WUNI-002 BEFORE WTPL-002
- Convention: `composed-additions` section for pack/project new content

---

## Part 1: The Simplified 4-Concept Section System

### Before vs After

| Before (12+ concepts) | After (4 concepts) |

|-----------------------|-------------------|

| `<!-- ANCHOR: name -->` | `<!-- SECTION: name -->` |

| `<!-- END ANCHOR: name -->` | `<!-- /SECTION: name -->` |

| `<!-- NEW_SECTION: name -->` | Just use `<!-- SECTION: name -->` |

| `<!-- APPEND -->` | Use `<!-- SECTION: composed-additions -->` |

| `{{SECTION:Name}}` placeholder | Use empty `<!-- SECTION: name -->` |

| `{{EXTENSIBLE_SECTIONS}}` | Not needed |

| `{{APPEND_SECTIONS}}` | Not needed |

| `{{include-anchor:path#name}}` | `{{include-section:path#name}}` |

### The 4 Core Concepts

| Concept | Syntax | Purpose |

|---------|--------|---------|

| **Define Section** | `<!-- SECTION: name -->...<!-- /SECTION: name -->` | Create named, extensible, extractable region |

| **Extend Section** | `<!-- EXTEND: name -->...<!-- /EXTEND -->` | Add content to existing section |

| **Include Section** | `{{include-section:path#name}}` | Embed section content from a file |

| **Reference Section** | `{{reference-section:path#name\|purpose}}` | Point to section without embedding |

### Complete Marker Reference

| Marker | Location | Purpose |

|--------|----------|---------|

| `<!-- SECTION: name -->` | Source files | Define section (extensible + extractable) |

| `<!-- /SECTION: name -->` | Source files | Close section |

| `<!-- EXTEND: name -->` | Overlays | Add content to existing section |

| `<!-- /EXTEND -->` | Overlays | Close extend |

| `{{include:path}}` | Templates | Embed entire file |

| `{{include-optional:path}}` | Templates | Embed file if exists |

| `{{include-section:path#name}}` | Templates | Embed section content |

| `{{reference-section:path#name\|purpose}}` | Templates | Point without embedding |

| `{{if:pack:name}}...{{/if}}` | Templates | Pack conditional |

| `{{if:config.path}}...{{/if}}` | Templates | Config conditional |

| `{{config.path.to.value}}` | Templates | Config variable |

| `{{source_layers}}` | Templates | Context variable |

| `{{timestamp}}` | Templates | Context variable |

| `{{PROJECT_EDISON_DIR}}` | Templates | Path variable |

### What Was Eliminated

| Removed | Reason |

|---------|--------|

| `<!-- ANCHOR: name -->` | Renamed to `<!-- SECTION: name -->` |

| `<!-- NEW_SECTION: name -->` | Just use `<!-- SECTION: name -->` directly |

| `<!-- APPEND -->` | Use named section `composed-additions` instead |

| `{{SECTION:Name}}` | Use empty `<!-- SECTION: name -->` block |

| `{{EXTENSIBLE_SECTIONS}}` | Not needed - include sections explicitly |

| `{{APPEND_SECTIONS}}` | Not needed - use `composed-additions` section |

| `{{include-anchor:path#name}}` | Renamed to `{{include-section:path#name}}` |

### Convention: `composed-additions` Section

For packs/projects to add NEW content, core templates include:

```markdown
<!-- SECTION: composed-additions -->
<!-- /SECTION: composed-additions -->
```

Packs extend it:

```markdown
<!-- EXTEND: composed-additions -->
## Pack-Specific Section
New content from pack
<!-- /EXTEND -->
```

---

## Part 2: Two-Phase Composition Architecture

### Why Two Phases?

| Single Phase (Current) | Two Phases (New) |

|------------------------|------------------|

| `{{include-section:VALIDATION.md#tdd}}` gets only CORE content | Gets FULLY COMPOSED content with pack extensions |

| Cross-file references miss pack/project overlays | All overlays included |

| Order-dependent, fragile | Clean separation of concerns |

### Phase 1: Layer Composition

Compose ALL source files first, merging sections from Core → Packs → Project:

```python
# Compose ALL entities and write intermediate files
for entity_type in ["guidelines", "agents", "validators", "constitutions"]:
    composer = LayeredComposer(repo_root, entity_type)
    for entity in composer.discover_all():
        content = composer.compose(entity, active_packs)
        # Sections merged, markers PRESERVED
        output = generated_dir / entity_type / f"{entity}.md"
        output.write_text(content)
```

**Result:** `_generated/` contains files with:

- All `<!-- EXTEND: name -->` content merged into sections
- Section markers (`<!-- SECTION: name -->`) preserved for extraction
- Ready for Phase 2 processing

### Phase 2: Template Processing

Process the composed files for includes, sections, variables:

```python
engine = TemplateEngine(config, repo_root)
engine.set_source_dir(generated_dir)  # Read from composed files!

for file in generated_dir.rglob("*.md"):
    content = file.read_text()
    # {{include-section:path#name}} extracts from COMPOSED files
    processed = engine.process(content)
    file.write_text(processed)  # Overwrite with final content
```

**Result:** `_generated/` contains final files with:

- All `{{include-section:}}` resolved to fully composed content
- All `{{include:}}` resolved
- All variables substituted
- Section markers stripped (configurable)

### Composition Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: Layer Composition                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CORE                     PACKS                    PROJECT               │
│  guidelines/              packs/vitest/            .edison/              │
│  VALIDATION.md            guidelines/              guidelines/           │
│                           VALIDATION.md            VALIDATION.md         │
│                                                                          │
│  <!-- SECTION: tdd -->    <!-- EXTEND: tdd -->    <!-- EXTEND: tdd -->  │
│  - Test first             - Use vitest            - Project rule        │
│  <!-- /SECTION: tdd -->   <!-- /EXTEND -->        <!-- /EXTEND -->      │
│                                                                          │
│                              ↓ LayeredComposer                          │
│                                                                          │
│  _generated/guidelines/VALIDATION.md (COMPOSED)                         │
│  <!-- SECTION: tdd -->                                                  │
│  - Test first                                                            │
│  - Use vitest              ← Pack extension merged                      │
│  - Project rule            ← Project extension merged                   │
│  <!-- /SECTION: tdd -->                                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         PHASE 2: Template Processing                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  _generated/agents/test-engineer.md                                      │
│                                                                          │
│  ## TDD Requirements                                                     │
│  {{include-section:guidelines/VALIDATION.md#tdd}}                       │
│                                                                          │
│                              ↓ TemplateEngine                           │
│                                                                          │
│  ## TDD Requirements                                                     │
│  - Test first                                                            │
│  - Use vitest              ← FULLY COMPOSED content!                    │
│  - Project rule            ← FULLY COMPOSED content!                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: TemplateEngine Architecture

### Transformation Pipeline (9 Steps)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TemplateEngine                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  1. INCLUDES             {{include:path}}                                │
│                          {{include-optional:path}}                       │
│     Recursive file inclusion (from composed files)                       │
│                                                                          │
│  2. SECTION EXTRACTION   {{include-section:path#name}}                  │
│     Extract content from composed sections                               │
│                                                                          │
│  3. CONDITIONALS         {{if:pack:name}}...{{/if}}                     │
│                          {{if:config.path}}...{{/if}}                   │
│     Conditional content based on packs or config                         │
│                                                                          │
│  4. LOOPS                {{#each collection}}...{{/each}}               │
│     Iterate over arrays from context                                     │
│                                                                          │
│  5. CONFIG VARS          {{config.path.to.value}}                       │
│     Substitute from YAML configuration                                   │
│                                                                          │
│  6. CONTEXT VARS         {{source_layers}}, {{timestamp}}, etc.         │
│     Substitute from runtime context                                      │
│                                                                          │
│  7. PATH VARS            {{PROJECT_EDISON_DIR}}                         │
│     Resolve path placeholders                                            │
│                                                                          │
│  8. REFERENCES           {{reference-section:path#name|purpose}}        │
│     Output pointers (no embedding)                                       │
│                                                                          │
│  9. VALIDATION           Check for unresolved {{...}}                   │
│     Report missing variables                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### File Structure

```
src/edison/core/composition/
├── engine.py                    # TemplateEngine (main entry point)
├── transformers/
│   ├── __init__.py
│   ├── base.py                  # ContentTransformer base class
│   ├── includes.py              # IncludeResolver + SectionExtractor
│   ├── conditionals.py          # ConditionalProcessor
│   ├── loops.py                 # LoopExpander
│   ├── variables.py             # ConfigVar, ContextVar, PathVar replacers
│   └── references.py            # ReferenceRenderer
├── core/
│   ├── base.py                  # CompositionBase (WUNI-001)
│   ├── composer.py              # LayeredComposer (updated for section extension)
│   ├── discovery.py             # LayerDiscovery
│   ├── sections.py              # SectionParser (simplified)
│   ├── paths.py                 # CompositionPathResolver
│   └── report.py                # CompositionReport
├── output/
│   ├── writer.py                # CompositionFileWriter (WUNI-002)
│   └── resolver.py              # OutputPathResolver (WUNI-003)
└── includes.py                  # Legacy, to be moved to transformers/
```

---

## Part 4: Task Corrections

### WTPL-001: Design TemplateEngine

| Issue | Original | Correction |

|-------|----------|------------|

| Name | `CompositionPipeline` | `TemplateEngine` |

| Steps | 6 | 9 |

| Markers | 12+ concepts | 4 core concepts |

| Architecture | Single-phase | Two-phase |

### WTPL-002: Implement TemplateEngine

| Issue | Original | Correction |

|-------|----------|------------|

| Name | `CompositionPipeline` | `TemplateEngine` |

| Location | `core/pipeline.py` | `engine.py` |

| Transformers | Inline methods | `transformers/` module |

| Section handling | Multiple marker types | Unified SECTION marker |

### WUNI-001: CompositionBase

| Issue | Original | Correction |

|-------|----------|------------|

| Location | `composition/base.py` | `composition/core/base.py` |

### WUNI-004: Registry Unification

| Issue | Original | Correction |

|-------|----------|------------|

| RulesRegistry | "Doesn't extend BaseRegistry" | **ALREADY EXTENDS** `BaseRegistry[Dict]` |

| Focus | Make RulesRegistry extend | GuidelineRegistry use LayeredComposer |

### WUNI-005: Adapter Unification

| Issue | Original | Correction |

|-------|----------|------------|

| ConfigMixin | "Not found" | **EXISTS** at `adapters/_config.py` |

---

## Part 5: Implementation Phases (Self-Contained)

This plan replaces the original 8 task files. Execute phases in order.

### Phase 1: Marker Migration and SectionParser Update

**Goal:** Migrate all markers from ANCHOR→SECTION, remove redundant markers, update SectionParser.

**Files to modify:**

```
src/edison/core/composition/core/sections.py    # SectionParser simplification
src/edison/data/**/*.md                         # All templates (ANCHOR→SECTION)
```

**Step 1.1:** Update `sections.py` - remove ANCHOR, NEW_SECTION, APPEND patterns

**Step 1.2:** Search/replace in `edison.data`: `<!-- ANCHOR:` → `<!-- SECTION:`

**Step 1.3:** Search/replace in `edison.data`: `<!-- END ANCHOR:` → `<!-- /SECTION:`

**Step 1.4:** Remove all `{{SECTION:Name}}`, `{{EXTENSIBLE_SECTIONS}}`, `{{APPEND_SECTIONS}}`

**Step 1.5:** Add `<!-- SECTION: composed-additions -->` to templates that need pack extensions

**Step 1.6:** Run tests, fix any breakages

### Phase 2: TemplateEngine Implementation

**Goal:** Create the unified TemplateEngine with transformers module.

**Files to create:**

```
src/edison/core/composition/engine.py
src/edison/core/composition/transformers/__init__.py
src/edison/core/composition/transformers/base.py
src/edison/core/composition/transformers/includes.py
src/edison/core/composition/transformers/conditionals.py
src/edison/core/composition/transformers/loops.py
src/edison/core/composition/transformers/variables.py
src/edison/core/composition/transformers/references.py
src/edison/core/composition/core/report.py
```

**Files to modify:**

```
src/edison/cli/compose/all.py    # Two-phase composition
```

**Step 2.1:** Create `transformers/base.py` with `ContentTransformer` base class

**Step 2.2:** Create individual transformers

**Step 2.3:** Create `engine.py` with `TemplateEngine` class

**Step 2.4:** Create `core/report.py` with `CompositionReport`

**Step 2.5:** Update `cli/compose/all.py` for two-phase composition

**Step 2.6:** Write tests for TemplateEngine

### Phase 3: Infrastructure Unification

**Goal:** Create shared base classes and utilities.

**Files to create:**

```
src/edison/core/composition/core/base.py       # CompositionBase
src/edison/core/composition/output/writer.py   # CompositionFileWriter
src/edison/core/composition/output/resolver.py # OutputPathResolver
```

**Step 3.1:** Create `CompositionBase` extracting common code from BaseRegistry + IDEComposerBase

**Step 3.2:** Create `CompositionFileWriter` with write_text, write_json, write_executable

**Step 3.3:** Create `OutputPathResolver` merging OutputConfigLoader + CompositionPathResolver

**Step 3.4:** Update imports across codebase

### Phase 4: Registry, Adapter, IDE Composer Unification

**Goal:** Apply unified patterns across all composers.

**Files to modify:**

```
src/edison/core/entity/registry.py                    # Extend CompositionBase
src/edison/core/composition/ide/base.py               # Extend CompositionBase
src/edison/core/composition/registries/guidelines.py  # Use LayeredComposer
src/edison/core/adapters/sync/*.py                    # Use ConfigMixin
src/edison/core/composition/ide/*.py                  # Use shared utilities
```

**Step 4.1:** Update BaseRegistry to extend CompositionBase

**Step 4.2:** Update IDEComposerBase to extend CompositionBase

**Step 4.3:** Update GuidelineRegistry to use LayeredComposer

**Step 4.4:** Update sync adapters to use ConfigMixin

**Step 4.5:** Add `_load_layered_config()` to IDEComposerBase

### Execution Order

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
   │           │           │           │
   ↓           ↓           ↓           ↓
  PR #1       PR #2       PR #3       PR #4
```

---

## Part 6: WTPL-000 - Syntax Consolidation (New Task)

### Problem

- Two pack conditional syntaxes: `{{include-if:has-pack(name):path}}` and `{{#if pack:name}}`
- Multiple section/anchor markers to migrate

### Solution

1. Unify pack conditionals to `{{if:pack:name}}...{{/if}}`
2. Migrate `<!-- ANCHOR: -->` to `<!-- SECTION: -->`
3. Remove `{{SECTION:Name}}`, `{{EXTENSIBLE_SECTIONS}}`, `{{APPEND_SECTIONS}}`
4. Update all templates in `edison.data`
5. Create migration guide

---

## Part 7: Implementation Details

### SectionParser (Simplified)

```python
class SectionParser:
    # Only two patterns needed!
    SECTION_PATTERN = re.compile(
        r'<!-- SECTION: (\w+) -->(.*?)<!-- /SECTION: \1 -->',
        re.DOTALL
    )
    EXTEND_PATTERN = re.compile(
        r'<!-- EXTEND: (\w+) -->(.*?)<!-- /EXTEND -->',
        re.DOTALL
    )
    
    def merge_extensions(self, content: str, extensions: Dict[str, List[str]]) -> str:
        """Merge EXTEND content into SECTION regions."""
        def replacer(match):
            section_name = match.group(1)
            section_content = match.group(2)
            if section_name in extensions:
                # Append extension content before closing marker
                extended = section_content.rstrip()
                for ext in extensions[section_name]:
                    extended += "\n" + ext
                return f"<!-- SECTION: {section_name} -->{extended}\n<!-- /SECTION: {section_name} -->"
            return match.group(0)
        return self.SECTION_PATTERN.sub(replacer, content)
```

### TemplateEngine Section Extraction

```python
class TemplateEngine:
    INCLUDE_SECTION_PATTERN = re.compile(r'\{\{include-section:([^#]+)#(\w+)\}\}')
    
    def _extract_section(self, file_path: str, section_name: str) -> str:
        """Extract section content from COMPOSED file."""
        composed_file = self.source_dir / file_path
        if not composed_file.exists():
            raise FileNotFoundError(f"Composed file not found: {composed_file}")
        
        content = composed_file.read_text()
        pattern = re.compile(
            rf'<!-- SECTION: {re.escape(section_name)} -->(.*?)<!-- /SECTION: {re.escape(section_name)} -->',
            re.DOTALL
        )
        match = pattern.search(content)
        if not match:
            raise ValueError(f"Section '{section_name}' not found in {file_path}")
        
        return match.group(1).strip()
    
    def _process_section_includes(self, content: str) -> str:
        """Process all {{include-section:path#name}} directives."""
        def replacer(match):
            file_path = match.group(1)
            section_name = match.group(2)
            return self._extract_section(file_path, section_name)
        return self.INCLUDE_SECTION_PATTERN.sub(replacer, content)
```

---

## Part 8: Duplication Elimination

| Area | Current | After | Savings |

|------|---------|-------|---------|

| Section markers | 8+ types | 2 types | ~50% complexity |

| Legacy variable replace | ~60 lines (4 files) | 0 | 60 |

| Pack conditionals | ~40 lines (2 syntaxes) | ~20 | 20 |

| YAML extension fallback | ~30 lines (5 files) | ~5 | 25 |

| Three-layer loading | ~60 lines (4 files) | ~15 | 45 |

| File writing patterns | ~50 lines (15 files) | 0 | 50 |

| **Total** | | | **~200+ lines** |

---

## Part 9: ConfigMixin Location

**Found at:** `src/edison/core/adapters/_config.py`

**Currently used by:**

- `CodexAdapter` (but duplicates `_load_config()`)
- `CursorPromptAdapter`

**Should be used by:**

- `ClaudeSync`
- `CursorSync`
- `ZenSync`

---

## Part 10: Example - Full Composition Flow

### Input Files

**Core:** `guidelines/shared/VALIDATION.md`

```markdown
# Validation Guidelines

<!-- SECTION: tdd-rules -->
- Write tests before implementation
- Tests must fail first (RED)
<!-- /SECTION: tdd-rules -->

<!-- SECTION: composed-additions -->
<!-- /SECTION: composed-additions -->
```

**Pack vitest:** `packs/vitest/guidelines/shared/VALIDATION.md`

```markdown
<!-- EXTEND: tdd-rules -->
- Use vitest for all tests
- Coverage must be > 80%
<!-- /EXTEND -->

<!-- EXTEND: composed-additions -->
## Vitest Configuration
- Use `describe` and `it` blocks
<!-- /EXTEND -->
```

**Agent:** `agents/test-engineer.md`

```markdown
# Test Engineer

## TDD Requirements
{{include-section:guidelines/shared/VALIDATION.md#tdd-rules}}

## Full Guidelines
{{include:guidelines/shared/VALIDATION.md}}

## References
{{reference-section:guidelines/shared/VALIDATION.md#tdd-rules|TDD rules for reference}}
```

### After Phase 1 (Layer Composition)

**`_generated/guidelines/shared/VALIDATION.md`:**

```markdown
# Validation Guidelines

<!-- SECTION: tdd-rules -->
- Write tests before implementation
- Tests must fail first (RED)
- Use vitest for all tests
- Coverage must be > 80%
<!-- /SECTION: tdd-rules -->

<!-- SECTION: composed-additions -->
## Vitest Configuration
- Use `describe` and `it` blocks
<!-- /SECTION: composed-additions -->
```

### After Phase 2 (Template Processing)

**`_generated/agents/test-engineer.md`:**

```markdown
# Test Engineer

## TDD Requirements
- Write tests before implementation
- Tests must fail first (RED)
- Use vitest for all tests
- Coverage must be > 80%

## Full Guidelines
# Validation Guidelines

- Write tests before implementation
- Tests must fail first (RED)
- Use vitest for all tests
- Coverage must be > 80%

## Vitest Configuration
- Use `describe` and `it` blocks

## References
- guidelines/shared/VALIDATION.md#tdd-rules: TDD rules for reference
```


---

## Part 11: CompositionBase Full Implementation (WUNI-001)

**Location:** `src/edison/core/composition/core/base.py`

**Purpose:** Extract shared functionality between `BaseRegistry` and `IDEComposerBase`.

### Full Class Implementation

```python
"""Shared base for layered content composition."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from edison.core.config import ConfigManager
from edison.core.config.domains import PacksConfig
from edison.core.utils.paths import PathResolver, get_project_config_dir


class CompositionBase(ABC):
    """Shared base for registries and IDE composers.

    Provides:
    - Unified path resolution (project_root, project_dir)
    - Config manager access (self.cfg_mgr, self.config)
    - Active packs discovery (get_active_packs())
    - YAML loading utilities (load_yaml_safe, merge_yaml)
    - Definition merging (merge_definitions)
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        config: Optional[Dict] = None,
    ) -> None:
        # Path resolution - UNIFIED
        self.project_root = project_root or PathResolver.resolve_project_root()
        self.project_dir = get_project_config_dir(self.project_root, create=False)

        # Config - UNIFIED
        self.cfg_mgr = ConfigManager(self.project_root)
        base_cfg = self.cfg_mgr.load_config(validate=False)
        self.config = self.cfg_mgr.deep_merge(base_cfg, config or {})

        # Active packs - UNIFIED (lazy)
        self._packs_config: Optional[PacksConfig] = None

        # Subclass-specific paths
        self._setup_composition_dirs()

    @abstractmethod
    def _setup_composition_dirs(self) -> None:
        """Setup core/packs directories. Override in subclasses.

        BaseRegistry implementation:
            self.core_dir = self.project_dir / "core"
            self.packs_dir = self.project_dir / "packs"

        IDEComposerBase implementation:
            self.core_dir = Path(get_data_path(""))
            self.bundled_packs_dir = Path(get_data_path("packs"))
            self.project_packs_dir = self.project_dir / "packs"
        """
        pass

    def get_active_packs(self) -> List[str]:
        """Get active packs list (cached)."""
        if self._packs_config is None:
            self._packs_config = PacksConfig(repo_root=self.project_root)
        return self._packs_config.active_packs

    def load_yaml_safe(self, path: Path) -> Dict[str, Any]:
        """Load YAML file, returning empty dict if not found."""
        if not path.exists():
            return {}
        return self.cfg_mgr.load_yaml(path) or {}

    def merge_yaml(
        self,
        base: Dict[str, Any],
        path: Path,
        key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Merge YAML file into base dict."""
        data = self.load_yaml_safe(path)
        if key:
            data = data.get(key, {}) or {}
        if not data:
            return base
        return self.cfg_mgr.deep_merge(base, data)

    def merge_definitions(
        self,
        merged: Dict[str, Dict[str, Any]],
        definitions: Any,
        key_getter: Callable[[Dict], str] = lambda d: d.get("id"),
    ) -> Dict[str, Dict[str, Any]]:
        """Generic merge for definitions by unique key."""
        if isinstance(definitions, dict):
            for def_key, def_dict in definitions.items():
                if not isinstance(def_dict, dict):
                    continue
                existing = merged.get(def_key, {})
                merged[def_key] = self.cfg_mgr.deep_merge(existing, def_dict)
            return merged

        if isinstance(definitions, list):
            for def_dict in definitions:
                if not isinstance(def_dict, dict):
                    continue
                def_key = key_getter(def_dict)
                if not def_key:
                    continue
                existing = merged.get(def_key, {})
                merged[def_key] = self.cfg_mgr.deep_merge(existing, def_dict)
            return merged

        return merged
```

### Migration: BaseRegistry

```python
# Before
class BaseRegistry(BaseEntityManager[T], Generic[T]):
    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()
        self.project_dir = get_project_config_dir(self.project_root, create=False)

# After
class BaseRegistry(CompositionBase, Generic[T]):
    def _setup_composition_dirs(self) -> None:
        self.core_dir = self.project_dir / "core"
        self.packs_dir = self.project_dir / "packs"
```

### Migration: IDEComposerBase

```python
# Before
class IDEComposerBase(ABC):
    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        self.cfg_mgr = ConfigManager(self.repo_root)
        # ... 20+ lines of initialization

# After
class IDEComposerBase(CompositionBase):
    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None):
        super().__init__(project_root=repo_root, config=config)
        # Alias for backward compatibility
        self.repo_root = self.project_root

    def _setup_composition_dirs(self) -> None:
        self.core_dir = Path(get_data_path(""))
        self.bundled_packs_dir = Path(get_data_path("packs"))
        self.project_packs_dir = self.project_dir / "packs"
        self.packs_dir = self.bundled_packs_dir  # backward compat
```

### Duplication Eliminated: ~90 lines

---

## Part 12: CompositionFileWriter Full Implementation (WUNI-002)

**Location:** `src/edison/core/composition/output/writer.py`

**Purpose:** Centralized file writing for all composition output.

### Full Class Implementation

```python
"""Unified file writing for Edison composition."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.io import ensure_directory, write_text_locked, write_json_atomic


@dataclass
class WriteResult:
    """Result of a write operation."""
    path: Path
    success: bool
    bytes_written: int = 0
    error: Optional[str] = None


class CompositionFileWriter:
    """Unified file writer for all composition output.

    Provides:
    - Automatic directory creation
    - Atomic writes (optional)
    - File tracking for reporting
    - Executable mode support
    - Consistent error handling

    Usage:
        writer = CompositionFileWriter()
        writer.write_text(path, content)
        writer.write_json(path, data)
        writer.write_executable(path, content)  # For hooks

        # Get summary
        print(f"Wrote {len(writer.files_written)} files")
    """

    def __init__(self, atomic: bool = False) -> None:
        self.atomic = atomic
        self.files_written: List[Path] = []
        self.errors: List[WriteResult] = []

    def write_text(
        self,
        path: Path,
        content: str,
        *,
        atomic: Optional[bool] = None,
        encoding: str = "utf-8",
    ) -> WriteResult:
        """Write text content to file."""
        try:
            ensure_directory(path.parent)
            use_atomic = atomic if atomic is not None else self.atomic

            if use_atomic:
                write_text_locked(path, content)
            else:
                path.write_text(content, encoding=encoding)

            result = WriteResult(
                path=path,
                success=True,
                bytes_written=len(content.encode(encoding)),
            )
            self.files_written.append(path)
            return result

        except Exception as e:
            result = WriteResult(path=path, success=False, error=str(e))
            self.errors.append(result)
            return result

    def write_json(
        self,
        path: Path,
        data: Dict[str, Any],
        *,
        indent: int = 2,
        atomic: bool = True,
    ) -> WriteResult:
        """Write JSON data to file."""
        try:
            ensure_directory(path.parent)

            if atomic:
                write_json_atomic(path, data, indent=indent)
            else:
                import json
                path.write_text(json.dumps(data, indent=indent), encoding="utf-8")

            result = WriteResult(path=path, success=True)
            self.files_written.append(path)
            return result

        except Exception as e:
            result = WriteResult(path=path, success=False, error=str(e))
            self.errors.append(result)
            return result

    def write_yaml(self, path: Path, data: Dict[str, Any]) -> WriteResult:
        """Write YAML data to file."""
        try:
            import yaml
            ensure_directory(path.parent)
            content = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
            path.write_text(content, encoding="utf-8")

            result = WriteResult(path=path, success=True, bytes_written=len(content))
            self.files_written.append(path)
            return result

        except Exception as e:
            result = WriteResult(path=path, success=False, error=str(e))
            self.errors.append(result)
            return result

    def write_executable(self, path: Path, content: str) -> WriteResult:
        """Write executable script (for hooks). Sets chmod +x."""
        result = self.write_text(path, content)
        if result.success:
            path.chmod(path.stat().st_mode | 0o111)
        return result

    def reset(self) -> None:
        """Reset tracking for new composition run."""
        self.files_written.clear()
        self.errors.clear()

    def summary(self) -> Dict[str, Any]:
        """Get summary of all writes."""
        return {
            "files_written": len(self.files_written),
            "errors": len(self.errors),
            "paths": [str(p) for p in self.files_written],
            "error_details": [{"path": str(e.path), "error": e.error} for e in self.errors],
        }
```

### Migration Pattern

**Before (scattered):**
```python
# rosters.py
ensure_directory(output_path.parent)
output_path.write_text(content, encoding="utf-8")

# hooks.py
ensure_directory(out_path.parent)
out_path.write_text(rendered, encoding="utf-8")
out_path.chmod(out_path.stat().st_mode | 0o111)

# rules.py
ensure_directory(out_path.parent)
write_json_atomic(out_path, rules_data, indent=2)
```

**After (unified):**
```python
writer = CompositionFileWriter()
writer.write_text(output_path, content)      # rosters
writer.write_executable(out_path, rendered)   # hooks
writer.write_json(out_path, rules_data)       # rules
```

---

## Part 13: OutputPathResolver Full Implementation (WUNI-003)

**Location:** `src/edison/core/composition/output/resolver.py`

```python
"""Unified output path resolution for Edison composition."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .core.paths import CompositionPathResolver
from ..utils.io import read_yaml
from ..utils.merge import deep_merge
from edison.data import get_data_path


class OutputPathResolver:
    """Unified path resolution combining base paths + output configuration."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self._path_resolver = CompositionPathResolver(repo_root)
        self.repo_root = self._path_resolver.repo_root
        self.project_dir = self._path_resolver.project_dir
        self.core_dir = self._path_resolver.core_dir
        self.packs_dir = self._path_resolver.packs_dir
        self._config: Optional[Dict[str, Any]] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load composition.yaml with core defaults + project overrides."""
        if self._config is not None:
            return self._config

        core_config_path = get_data_path("config", "composition.yaml")
        core_config = read_yaml(core_config_path, default={})

        project_config_path = self.project_dir / "composition.yaml"
        if project_config_path.exists():
            project_config = read_yaml(project_config_path, default={})
            self._config = deep_merge(core_config, project_config)
        else:
            self._config = core_config

        return self._config

    def resolve_template(self, template: str, target_path: Optional[Path] = None) -> Path:
        """Resolve path template with {{PROJECT_EDISON_DIR}} placeholder."""
        if "{{PROJECT_EDISON_DIR}}" in template:
            resolved = template.replace("{{PROJECT_EDISON_DIR}}", str(self.project_dir))
            path = Path(resolved)
            if not path.is_absolute():
                path = self.repo_root / path
            return path

        path = Path(template)
        if not path.is_absolute():
            path = self.repo_root / path
        return path

    def get_outputs_config(self) -> Dict[str, Any]:
        return self._load_config().get("outputs", {})

    def get_agents_dir(self) -> Optional[Path]:
        cfg = self.get_outputs_config().get("agents", {})
        if not cfg.get("enabled", True):
            return None
        output_path = cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/agents")
        return self.resolve_template(output_path)

    def get_validators_dir(self) -> Optional[Path]:
        cfg = self.get_outputs_config().get("validators", {})
        if not cfg.get("enabled", True):
            return None
        output_path = cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/validators")
        return self.resolve_template(output_path)

    def get_guidelines_dir(self) -> Optional[Path]:
        cfg = self.get_outputs_config().get("guidelines", {})
        if not cfg.get("enabled", True):
            return None
        output_path = cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/guidelines")
        return self.resolve_template(output_path)

    def get_constitution_path(self, role: str) -> Optional[Path]:
        cfg = self.get_outputs_config().get("constitutions", {})
        if not cfg.get("enabled", True):
            return None
        files = cfg.get("files", {})
        role_cfg = files.get(role, {})
        if not role_cfg.get("enabled", True):
            return None
        output_dir = self.resolve_template(
            cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/constitutions")
        )
        filename = role_cfg.get("filename", f"{role.upper()}.md")
        return output_dir / filename

    def get_client_path(self, client_name: str) -> Optional[Path]:
        cfg = self.get_outputs_config().get("clients", {}).get(client_name, {})
        if not cfg.get("enabled", False):
            return None
        output_dir = self.resolve_template(cfg.get("output_path", f".{client_name}"))
        filename = cfg.get("filename", f"{client_name.upper()}.md")
        return output_dir / filename
```

---

## Part 14: Registry Unification (WUNI-004)

### GuidelineRegistry Migration

```python
# Before (~80 lines manual discovery)
class GuidelineRegistry(BaseRegistry[Path]):
    def discover_core(self) -> Dict[str, Path]:
        result = {}
        for f in self.core_dir.rglob("*.md"):
            # Manual discovery
        return result

# After (uses LayeredComposer)
class GuidelineRegistry(BaseRegistry[LayerSource]):
    def __init__(self, project_root: Optional[Path] = None):
        super().__init__(project_root)
        self._composer = LayeredComposer(repo_root=self.project_root, content_type="guidelines")

    def discover_core(self) -> Dict[str, LayerSource]:
        return self._composer.discover_core()

    def discover_packs(self, packs: List[str]) -> Dict[str, LayerSource]:
        result = {}
        existing = set(self.discover_core().keys())
        for pack in packs:
            pack_new = self._composer.discover_pack_new(pack, existing)
            result.update(pack_new)
            existing.update(pack_new.keys())
        return result
```

### ConfigBasedRegistry

```python
class ConfigBasedRegistry(CompositionBase, Generic[T], ABC):
    """Base for registries that load from config, not files."""

    def discover_core(self) -> Dict[str, T]:
        return {}

    def discover_packs(self, packs: List[str]) -> Dict[str, T]:
        return {}

    def discover_project(self) -> Dict[str, T]:
        return {}

    @abstractmethod
    def _load_entities(self) -> Dict[str, T]:
        ...

    def get_all(self) -> List[T]:
        return list(self._load_entities().values())
```

### DRYAnalyzer Utility

```python
class DRYAnalyzer:
    """Shared DRY analysis utility."""

    def __init__(self, project_root: Path):
        cfg = ConfigManager(project_root).load_config(validate=False)
        dry_config = cfg.get("composition", {}).get("dryDetection", {})
        self.min_shingles = dry_config.get("minShingles", 2)
        self.shingle_size = dry_config.get("shingleSize", 12)

    def analyze(self, layers: Dict[str, str], min_shingles: Optional[int] = None) -> Dict:
        from edison.core.utils.text import dry_duplicate_report
        return dry_duplicate_report(layers, min_shingles=min_shingles or self.min_shingles, k=self.shingle_size)
```

---

## Part 15: Adapter Unification (WUNI-005)

### Enhanced SyncAdapter Base

```python
class SyncAdapter(ABC):
    """Enhanced base with lazy registries and unified path resolution."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self._path_resolver = OutputPathResolver(repo_root)
        self.repo_root = self._path_resolver.repo_root
        self._adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
        self._guideline_registry: Optional[GuidelineRegistry] = None
        self._rules_registry: Optional[RulesRegistry] = None

    @property
    def guideline_registry(self) -> GuidelineRegistry:
        if self._guideline_registry is None:
            self._guideline_registry = GuidelineRegistry(repo_root=self.repo_root)
        return self._guideline_registry

    @property
    def rules_registry(self) -> RulesRegistry:
        if self._rules_registry is None:
            self._rules_registry = RulesRegistry(project_root=self.repo_root)
        return self._rules_registry
```

### Consolidated ZenSync

Replace `zen/` directory (4 files) with single `zen.py`:

```python
class ZenSync(SyncAdapter):
    """Consolidated Zen MCP sync adapter."""

    def sync_all(self) -> Dict[str, Any]:
        result = {"roles": {}, "workflows": []}
        # Use base class registries (lazy)
        guidelines = self.guideline_registry
        rules = self.rules_registry
        # Sync logic...
        return result
```

**Files to DELETE:**
- `src/edison/core/adapters/sync/zen/discovery.py`
- `src/edison/core/adapters/sync/zen/composer.py`
- `src/edison/core/adapters/sync/zen/sync.py`
- `src/edison/core/adapters/sync/zen/client.py`
- `src/edison/core/adapters/sync/zen/__init__.py`

### Fix CodexAdapter

```python
# Before - reimplements ConfigMixin
class CodexAdapter(PromptAdapter):
    def _load_config(self) -> Dict:
        # Duplicate!

# After - use existing ConfigMixin
class CodexAdapter(PromptAdapter, ConfigMixin):
    pass  # ConfigMixin provides _load_config
```

---

## Part 16: IDE Composer Utilities (WUNI-006)

### Add to IDEComposerBase

```python
def _load_yaml_with_fallback(self, base_path: Path) -> Dict[str, Any]:
    """Load YAML, trying .yaml then .yml extension."""
    yaml_path = base_path.with_suffix('.yaml')
    if yaml_path.exists():
        return self._load_yaml_safe(yaml_path)
    yml_path = base_path.with_suffix('.yml')
    if yml_path.exists():
        return self._load_yaml_safe(yml_path)
    return {}

def _load_layered_config(
    self,
    config_name: str,
    *,
    core_subpath: str = "config",
    pack_subpath: str = "config",
    project_subpath: str = "config",
    key_path: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Load config from core -> packs -> project with merging."""
    merged = {}
    
    # Core layer
    core_file = self.core_dir / core_subpath / config_name
    merged = self._extract_and_merge(merged, self._load_yaml_with_fallback(core_file), key_path)
    
    # Pack layers
    for pack in self._active_packs():
        pack_file = self.bundled_packs_dir / pack / pack_subpath / config_name
        merged = self._extract_and_merge(merged, self._load_yaml_with_fallback(pack_file), key_path)
    
    # Project layer
    project_file = self.project_dir / project_subpath / config_name
    merged = self._extract_and_merge(merged, self._load_yaml_with_fallback(project_file), key_path)
    
    return merged

def _merge_with_handlers(self, base: Dict, overlay: Dict, handlers: Dict[str, Callable]) -> Dict:
    """Deep merge with custom handlers for specific keys."""
    result = dict(base)
    for key, value in (overlay or {}).items():
        if key in handlers:
            result[key] = handlers[key](result.get(key), value)
        elif isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = self._merge_with_handlers(result[key], value, handlers)
        else:
            result[key] = value
    return result
```

### Migration Examples

**HookComposer (30 lines -> 2 lines):**
```python
# Before
def load_definitions(self):
    merged = {}
    core_file = self._bundled_config_dir / "hooks.yaml"
    merged = self._merge_from_file(merged, core_file)
    for pack in self._active_packs():
        pack_file = self.packs_dir / pack / "config" / "hooks.yml"
        merged = self._merge_from_file(merged, pack_file)
    project_file = self.project_dir / "config" / "hooks.yml"
    merged = self._merge_from_file(merged, project_file)
    return self._dicts_to_defs(merged)

# After
def load_definitions(self):
    return self._dicts_to_defs(self._load_layered_config("hooks"))
```

---

## Part 17: CompositionReport

**Location:** `src/edison/core/composition/core/report.py`

```python
@dataclass
class CompositionReport:
    files_written: List[Path] = field(default_factory=list)
    variables_substituted: Set[str] = field(default_factory=set)
    variables_missing: Set[str] = field(default_factory=set)
    includes_resolved: Set[str] = field(default_factory=set)
    sections_processed: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def record_file(self, path: Path) -> None:
        self.files_written.append(path)

    def record_variable(self, var_path: str, resolved: bool) -> None:
        (self.variables_substituted if resolved else self.variables_missing).add(var_path)

    def has_unresolved(self) -> bool:
        return len(self.variables_missing) > 0

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def summary(self) -> str:
        lines = [
            f"Files written: {len(self.files_written)}",
            f"Variables substituted: {len(self.variables_substituted)}",
        ]
        if self.variables_missing:
            lines.append(f"Missing variables: {sorted(self.variables_missing)}")
        if self.warnings:
            lines.extend([f"  - {w}" for w in self.warnings])
        if self.errors:
            lines.extend([f"  ERROR: {e}" for e in self.errors])
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_written": [str(p) for p in self.files_written],
            "variables_substituted": sorted(self.variables_substituted),
            "variables_missing": sorted(self.variables_missing),
            "success": not self.has_errors(),
        }
```

---

## Part 18: TemplateEngine

**Location:** `src/edison/core/composition/engine.py`

```python
class TemplateEngine:
    """Unified template engine - 9-step transformation pipeline."""

    INCLUDE_PATTERN = re.compile(r'\{\{include:([^}]+)\}\}')
    INCLUDE_OPTIONAL_PATTERN = re.compile(r'\{\{include-optional:([^}]+)\}\}')
    INCLUDE_SECTION_PATTERN = re.compile(r'\{\{include-section:([^#]+)#([^}]+)\}\}')
    CONDITIONAL_PACK_PATTERN = re.compile(r'\{\{if:pack:([^}]+)\}\}(.*?)\{\{/if\}\}', re.DOTALL)
    CONFIG_PATTERN = re.compile(r'\{\{config\.([a-zA-Z_][a-zA-Z0-9_.]*)\}\}')
    CONTEXT_PATTERN = re.compile(r'\{\{(source_layers|timestamp|version)\}\}')
    PATH_PATTERN = re.compile(r'\{\{PROJECT_EDISON_DIR\}\}')
    REFERENCE_PATTERN = re.compile(r'\{\{reference-section:([^#]+)#([^|]+)\|([^}]+)\}\}')

    def __init__(self, config: ConfigManager, project_root: Path):
        self._config = config
        self._project_root = project_root
        self._source_dir: Optional[Path] = None
        self._report = CompositionReport()
        self._writer = CompositionFileWriter(atomic=True)
        self._context: Dict[str, Any] = {}
        self._active_packs: List[str] = []

    def set_source_dir(self, path: Path) -> None:
        self._source_dir = path

    def set_context(self, **kwargs) -> None:
        self._context.update(kwargs)

    def set_active_packs(self, packs: List[str]) -> None:
        self._active_packs = packs

    def process(self, content: str) -> str:
        """Apply all 9 transformations in order."""
        content = self._resolve_includes(content)           # 1
        content = self._process_section_includes(content)   # 2
        content = self._process_conditionals(content)       # 3
        content = self._process_loops(content)              # 4
        content = self._substitute_config_vars(content)     # 5
        content = self._substitute_context_vars(content)    # 6
        content = self._resolve_path_vars(content)          # 7
        content = self._process_references(content)         # 8
        self._validate_unresolved(content)                  # 9
        return content

    def _extract_section(self, file_path: str, section_name: str) -> str:
        """Extract section from composed file."""
        content = (self._source_dir / file_path).read_text()
        pattern = re.compile(
            rf'<!-- SECTION: {re.escape(section_name)} -->(.*?)<!-- /SECTION: {re.escape(section_name)} -->',
            re.DOTALL
        )
        match = pattern.search(content)
        if not match:
            raise ValueError(f"Section '{section_name}' not found in {file_path}")
        return match.group(1).strip()

    # ... remaining transformation methods as detailed in Part 18 above
```

---

## Part 19: Complete File Lists

### Files to CREATE
```
src/edison/core/composition/engine.py
src/edison/core/composition/transformers/__init__.py
src/edison/core/composition/transformers/base.py
src/edison/core/composition/transformers/includes.py
src/edison/core/composition/transformers/conditionals.py
src/edison/core/composition/transformers/loops.py
src/edison/core/composition/transformers/variables.py
src/edison/core/composition/transformers/references.py
src/edison/core/composition/core/base.py
src/edison/core/composition/core/report.py
src/edison/core/composition/output/writer.py
src/edison/core/composition/output/resolver.py
src/edison/core/composition/registries/config_based.py
src/edison/core/composition/analysis/dry.py
src/edison/core/adapters/sync/zen.py
```

### Files to MODIFY
```
src/edison/core/composition/core/sections.py
src/edison/core/entity/registry.py
src/edison/core/composition/ide/base.py
src/edison/core/composition/ide/hooks.py
src/edison/core/composition/ide/commands.py
src/edison/core/composition/ide/settings.py
src/edison/core/composition/ide/coderabbit.py
src/edison/core/composition/registries/guidelines.py
src/edison/core/composition/registries/validators.py
src/edison/core/adapters/sync/base.py
src/edison/core/adapters/sync/claude.py
src/edison/core/adapters/sync/cursor.py
src/edison/core/adapters/prompt/codex.py
src/edison/cli/compose/all.py
src/edison/data/**/*.md
```

### Files to DELETE
```
src/edison/core/adapters/sync/zen/discovery.py
src/edison/core/adapters/sync/zen/composer.py
src/edison/core/adapters/sync/zen/sync.py
src/edison/core/adapters/sync/zen/client.py
src/edison/core/adapters/sync/zen/__init__.py
```

---

## Part 20: Verification Checklists

### Phase 1: Marker Migration
- [ ] SectionParser simplified to SECTION/EXTEND only
- [ ] All `<!-- ANCHOR:` -> `<!-- SECTION:`
- [ ] All `<!-- END ANCHOR:` -> `<!-- /SECTION:`
- [ ] All `{{SECTION:Name}}`, `{{EXTENSIBLE_SECTIONS}}`, `{{APPEND_SECTIONS}}` removed
- [ ] `composed-additions` sections added where needed
- [ ] Tests pass

### Phase 2: TemplateEngine
- [ ] CompositionFileWriter created
- [ ] CompositionReport created
- [ ] All transformers created
- [ ] TemplateEngine created with 9-step pipeline
- [ ] cli/compose/all.py updated for two-phase composition
- [ ] Tests pass

### Phase 3: Infrastructure
- [ ] CompositionBase created
- [ ] OutputPathResolver created
- [ ] BaseRegistry extends CompositionBase
- [ ] IDEComposerBase extends CompositionBase
- [ ] ~90 lines duplication eliminated
- [ ] Tests pass

### Phase 4: Unification
- [ ] GuidelineRegistry uses LayeredComposer
- [ ] _load_layered_config added to IDEComposerBase
- [ ] IDE composers migrated
- [ ] ZenSync consolidated (4 files -> 1)
- [ ] CodexAdapter uses ConfigMixin
- [ ] Zen directory deleted
- [ ] ~200+ lines duplication eliminated
- [ ] All tests pass

---

## Part 21: Success Criteria

1. **Single TemplateEngine** handles ALL template processing
2. **4-concept section system** replaces 12+ markers
3. **Two-phase composition** ensures cross-file references get fully composed content
4. **CompositionBase** eliminates ~90 lines of duplication
5. **CompositionFileWriter** centralizes all file I/O
6. **OutputPathResolver** single source of truth for paths
7. **~200+ lines** of duplication eliminated total
8. **All tests pass**
9. **`edison compose all`** produces fully processed output

---

## Appendix: Current 18 Write Points (from WTPL-001)

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

All 18 to be migrated to use `TemplateEngine.write()` or `TemplateEngine.write_json()`.



---

## Appendix B: Error Hierarchy (from WUNI-004)

**Location:** `src/edison/core/composition/core/errors.py`

```python
"""Unified error hierarchy for Edison composition."""
from __future__ import annotations


class CompositionError(RuntimeError):
    """Base error for all composition operations."""
    pass


class EntityNotFoundError(CompositionError):
    """Entity not found in registry."""
    
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(f"{entity_type} '{entity_id}' not found")
        self.entity_type = entity_type
        self.entity_id = entity_id


class SectionNotFoundError(CompositionError):
    """Section not found in source file."""
    
    def __init__(self, section_name: str, file_path: str):
        super().__init__(f"Section '{section_name}' not found in {file_path}")
        self.section_name = section_name
        self.file_path = file_path


class IncludeNotFoundError(CompositionError):
    """Include file not found in any layer."""
    
    def __init__(self, include_path: str, searched_paths: list):
        paths_str = "\n  - ".join(str(p) for p in searched_paths)
        super().__init__(f"Include not found: {include_path}\nSearched:\n  - {paths_str}")
        self.include_path = include_path
        self.searched_paths = searched_paths


class CompositionValidationError(CompositionError):
    """Error in composition validation (unresolved patterns, etc.)."""
    
    def __init__(self, message: str, unresolved: list = None):
        super().__init__(message)
        self.unresolved = unresolved or []


class ConfigVariableNotFoundError(CompositionError):
    """Config variable path not found in configuration."""
    
    def __init__(self, var_path: str):
        super().__init__(f"Config variable not found: {{{{config.{var_path}}}}}")
        self.var_path = var_path
```

---

## Appendix C: resolve_single_include() Helper (from WTPL-002)

**Location:** Add to `src/edison/core/composition/includes.py`

```python
def resolve_single_include(
    include_path: str,
    project_root: Path,
    config: "ConfigManager",
) -> str:
    """Resolve a single include path to its content.

    This function is used by TemplateEngine for include resolution.
    It searches the three-layer hierarchy: project → packs → core.

    Args:
        include_path: Relative path from {{include:path}}
        project_root: Project root directory
        config: ConfigManager for pack resolution

    Returns:
        Content of the included file

    Raises:
        IncludeNotFoundError: If file not found in any layer
    """
    from edison.data import get_data_path
    from edison.core.composition.core.errors import IncludeNotFoundError

    # Search order: project → packs (reverse) → core
    search_paths = []

    # 1. Project layer
    project_file = project_root / ".edison" / include_path
    search_paths.append(project_file)

    # 2. Pack layers (in reverse order for precedence)
    active_packs = config.get("packs.active", []) or []
    for pack in reversed(active_packs):
        pack_file = project_root / ".edison" / "packs" / pack / include_path
        search_paths.append(pack_file)
        # Also check bundled packs
        bundled_pack_file = Path(get_data_path("packs")) / pack / include_path
        search_paths.append(bundled_pack_file)

    # 3. Core layer (bundled data)
    core_file = Path(get_data_path(include_path))
    search_paths.append(core_file)

    # Find first existing file
    for path in search_paths:
        if path.exists():
            return path.read_text(encoding="utf-8")

    raise IncludeNotFoundError(include_path, search_paths)
```

---

## Appendix D: Enhanced PromptAdapter Base (from WUNI-005)

**Location:** `src/edison/core/adapters/base.py`

```python
class PromptAdapter(ABC):
    """Enhanced base class for prompt adapters.

    Provides:
    - Template method patterns for writing
    - Consistent file listing
    - Post-processing hooks
    - Integrated CompositionFileWriter
    """

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        self.generated_root = generated_root.resolve()
        self.repo_root = repo_root.resolve() if repo_root else self.generated_root.parents[1]

        from edison.core.composition.output import CompositionFileWriter
        self._writer = CompositionFileWriter()

    # --- Template Methods for Writing ---

    def write_agents(
        self,
        output_dir: Path,
        pattern: str = "{name}.md",
    ) -> List[Path]:
        """Write all agents to output directory.
        
        Uses template method pattern - subclasses implement render_agent().
        """
        from edison.core.utils.io import ensure_directory
        ensure_directory(output_dir)

        written = []
        for agent_name in self.list_agents():
            content = self.render_agent(agent_name)
            formatted = self._format_agent_file(agent_name, content)
            filename = pattern.format(name=agent_name)
            path = output_dir / filename
            self._writer.write_text(path, formatted)
            written.append(path)
        return written

    def write_validators(
        self,
        output_dir: Path,
        pattern: str = "{name}.md",
    ) -> List[Path]:
        """Write all validators to output directory."""
        from edison.core.utils.io import ensure_directory
        ensure_directory(output_dir)

        written = []
        for validator_name in self.list_validators():
            content = self.render_validator(validator_name)
            formatted = self._format_validator_file(validator_name, content)
            filename = pattern.format(name=validator_name)
            path = output_dir / filename
            self._writer.write_text(path, formatted)
            written.append(path)
        return written

    # --- Hooks for Subclasses ---

    def _format_agent_file(self, name: str, content: str) -> str:
        """Hook for formatting agent file. Override in subclasses."""
        return self._post_process_agent(name, content)

    def _format_validator_file(self, name: str, content: str) -> str:
        """Hook for formatting validator file. Override in subclasses."""
        return self._post_process_validator(name, content)

    def _post_process_agent(self, name: str, content: str) -> str:
        """Post-process agent content. Override for client-specific formatting."""
        return content

    def _post_process_validator(self, name: str, content: str) -> str:
        """Post-process validator content. Override for client-specific formatting."""
        return content

    # --- Abstract Methods (implement in subclasses) ---

    @abstractmethod
    def list_agents(self) -> List[str]:
        """List available agent names."""
        ...

    @abstractmethod
    def list_validators(self) -> List[str]:
        """List available validator names."""
        ...

    @abstractmethod
    def render_agent(self, name: str) -> str:
        """Render agent content by name."""
        ...

    @abstractmethod
    def render_validator(self, name: str) -> str:
        """Render validator content by name."""
        ...

    # --- Utility Methods ---

    def get_writer_summary(self) -> Dict[str, Any]:
        """Get summary of all files written by this adapter."""
        return self._writer.summary()
```

---

## Appendix E: CLI compose/all.py Two-Phase Update

**Location:** `src/edison/cli/compose/all.py`

### Key Changes for Two-Phase Composition

```python
def main(args) -> int:
    """Main composition entry point with two-phase architecture."""
    from edison.core.config import ConfigManager
    from edison.core.composition import LayeredComposer, TemplateEngine
    from edison.core.composition.output import CompositionFileWriter
    from edison.core.utils.paths import get_project_config_dir
    
    repo_root = Path(args.repo_root) if args.repo_root else find_project_root()
    cfg_mgr = ConfigManager(repo_root)
    config = cfg_mgr.load_config(validate=False)
    
    active_packs = config.get("packs", {}).get("active", []) or []
    generated_dir = get_project_config_dir(repo_root) / "_generated"
    
    # =========================================
    # PHASE 1: Layer Composition
    # =========================================
    # Compose ALL entities first, merging sections from Core → Packs → Project
    # Section markers are PRESERVED for Phase 2 extraction
    
    for entity_type in ["guidelines", "agents", "validators"]:
        composer = LayeredComposer(repo_root, entity_type)
        output_dir = generated_dir / entity_type
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for entity_id in composer.discover_all():
            # Compose with section merging (EXTEND merged into SECTION)
            composed_content = composer.compose(entity_id, active_packs)
            # Write intermediate file (markers preserved)
            (output_dir / f"{entity_id}.md").write_text(composed_content)
    
    # Compose constitutions
    compose_constitutions(cfg_mgr, generated_dir, active_packs)
    
    # =========================================
    # PHASE 2: Template Processing
    # =========================================
    # Process composed files for includes, sections, variables
    # {{include-section:path#name}} now extracts from COMPOSED files
    
    engine = TemplateEngine(cfg_mgr, repo_root)
    engine.set_source_dir(generated_dir)  # Read from composed files!
    engine.set_active_packs(active_packs)
    engine.set_context(
        source_layers=" + ".join(["core"] + active_packs + ["project"]),
        timestamp=datetime.now().isoformat(),
        version=__version__,
    )
    
    # Process all generated files
    for md_file in generated_dir.rglob("*.md"):
        content = md_file.read_text()
        processed = engine.process(content)
        md_file.write_text(processed)
    
    # =========================================
    # Report
    # =========================================
    report = engine.get_report()
    
    if report.has_unresolved():
        console.print(f"[yellow]Warning: Unresolved variables[/yellow]")
        console.print(report.summary())
    
    if report.has_errors():
        console.print(f"[red]Errors during composition[/red]")
        for error in report.errors:
            console.print(f"  - {error}")
        return 1
    
    console.print(f"[green]Composed {len(report.files_written)} files[/green]")
    return 0
```

---

## Appendix F: Tests Structure

### Test Files to Create

```
tests/unit/composition/
├── test_engine.py           # TemplateEngine tests
├── test_writer.py           # CompositionFileWriter tests
├── test_resolver.py         # OutputPathResolver tests
├── test_base.py             # CompositionBase tests
├── test_report.py           # CompositionReport tests
├── core/
│   ├── test_sections.py     # Updated SectionParser tests
│   └── test_errors.py       # Error hierarchy tests
├── transformers/
│   ├── test_includes.py     # Include transformer tests
│   ├── test_conditionals.py # Conditional transformer tests
│   ├── test_loops.py        # Loop transformer tests
│   ├── test_variables.py    # Variable transformer tests
│   └── test_references.py   # Reference transformer tests
└── output/
    ├── test_writer.py       # File writer tests
    └── test_resolver.py     # Path resolver tests
```

### Key Test Cases for TemplateEngine

```python
class TestTemplateEngine:
    """Tests for TemplateEngine."""

    def test_process_include(self, tmp_path):
        """Test {{include:path}} resolution."""
        
    def test_process_include_optional_missing(self, tmp_path):
        """Test {{include-optional:path}} returns empty for missing file."""
        
    def test_process_section_include(self, tmp_path):
        """Test {{include-section:path#name}} extraction."""
        
    def test_process_pack_conditional_active(self, tmp_path):
        """Test {{if:pack:name}} includes content when pack active."""
        
    def test_process_pack_conditional_inactive(self, tmp_path):
        """Test {{if:pack:name}} excludes content when pack inactive."""
        
    def test_process_config_variable(self, tmp_path):
        """Test {{config.path}} substitution."""
        
    def test_process_config_variable_missing(self, tmp_path):
        """Test missing config var is tracked in report."""
        
    def test_process_context_variable(self, tmp_path):
        """Test {{source_layers}} substitution from context."""
        
    def test_process_path_variable(self, tmp_path):
        """Test {{PROJECT_EDISON_DIR}} resolution."""
        
    def test_process_reference(self, tmp_path):
        """Test {{reference-section:path#name|purpose}} output."""
        
    def test_transformation_order(self, tmp_path):
        """Test transformations happen in correct order."""
        
    def test_two_phase_integration(self, tmp_path):
        """Test Phase 1 compose + Phase 2 process flow."""
```

### Key Test Cases for SectionParser

```python
class TestSectionParser:
    """Tests for simplified SectionParser."""

    def test_parse_section(self):
        """Test <!-- SECTION: name --> parsing."""
        
    def test_parse_extend(self):
        """Test <!-- EXTEND: name --> parsing."""
        
    def test_merge_single_extension(self):
        """Test merging one EXTEND into SECTION."""
        
    def test_merge_multiple_extensions(self):
        """Test merging multiple EXTENDs into same SECTION."""
        
    def test_merge_preserves_markers(self):
        """Test section markers preserved after merge."""
        
    def test_composed_additions_convention(self):
        """Test composed-additions section for new content."""
```
````