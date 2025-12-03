<!-- 37e49df7-55c0-46d3-a20a-81761327d236 e0ee0318-a12e-46d5-8515-f7ac4010553e -->
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

### To-dos

- [ ] Update WUNI-004: RulesRegistry ALREADY extends BaseRegistry - task is outdated
- [ ] Reorder: WUNI-002 (FileWriter) should come BEFORE WTPL-002 (Pipeline)
- [ ] Add documentation: Explain relationship between CompositionPipeline and existing LayeredComposer
- [ ] Move CompositionBase location from composition/base.py to composition/core/base.py
- [ ] WUNI-005: Either create ConfigMixin or remove references to it