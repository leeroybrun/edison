<!-- 37e49df7-55c0-46d3-a20a-81761327d236 e0ee0318-a12e-46d5-8515-f7ac4010553e -->
# Edison Composition Unification - Comprehensive Architecture

## Executive Summary

Consolidate all template processing into a single `TemplateEngine` with unified concepts. Anchors and Sections are merged into one extensible/extractable system. This plan corrects outdated task information, establishes proper dependency ordering, and implements a two-phase composition architecture.

**Key Changes from Original Tasks:**

- Rename `CompositionPipeline` to `TemplateEngine`
- **UNIFY Anchors and Sections** - Anchors are now extensible via EXTEND
- Implement two-phase composition (compose ALL files first, THEN process templates)
- Add prerequisite task WTPL-000 (syntax consolidation)
- Fix WUNI-004: RulesRegistry ALREADY extends BaseRegistry
- Reorder dependencies: WUNI-002 BEFORE WTPL-002
- Add `{{reference:path|purpose}}` and `{{include-anchor:path#name}}` directives

---

## Part 1: Unified Marker System

### Key Insight: Anchors ARE Sections

**Before (Duplicated):** Required both anchor AND section markers:

```markdown
<!-- ANCHOR: tdd-rules -->
{{SECTION:tdd-rules}}
<!-- END ANCHOR: tdd-rules -->
```

**After (Unified):** `<!-- ANCHOR: name -->` is BOTH extractable AND extensible:

```markdown
<!-- ANCHOR: tdd-rules -->
Content here
<!-- END ANCHOR: tdd-rules -->
```

Pack overlay extends directly:

```markdown
<!-- EXTEND: tdd-rules -->
Additional content from pack
<!-- /EXTEND -->
```

### Unified Concept Table

| Concept | Syntax | Purpose | Extensible? | Extractable? |

|---------|--------|---------|-------------|--------------|

| **Anchors** | `<!-- ANCHOR: name -->` | Named content regions | Yes (via EXTEND) | Yes (via include-anchor) |

| **Sections** | `{{SECTION:Name}}` | Inline placeholders | Yes (via EXTEND) | No |

| **Includes** | `{{include:path}}` | Embed entire file | N/A | N/A |

| **References** | `{{reference:path\|purpose}}` | Point without embedding | N/A | N/A |

### Complete Marker Reference

| Marker | Location | Purpose |

|--------|----------|---------|

| `<!-- ANCHOR: name -->` | Source files | Define extractable + extensible region |

| `<!-- END ANCHOR: name -->` | Source files | Close anchor |

| `<!-- EXTEND: name -->` | Overlays | Extend anchor OR section |

| `<!-- /EXTEND -->` | Overlays | Close extend |

| `<!-- NEW_SECTION: name -->` | Overlays | Define new extensible section |

| `<!-- /NEW_SECTION -->` | Overlays | Close new section |

| `<!-- APPEND -->` | Overlays | Catch-all content |

| `<!-- /APPEND -->` | Overlays | Close append |

| `{{SECTION:Name}}` | Templates | Placeholder for section content |

| `{{EXTENSIBLE_SECTIONS}}` | Templates | All NEW_SECTION content |

| `{{APPEND_SECTIONS}}` | Templates | All APPEND content |

| `{{include:path}}` | Templates | Embed entire file |

| `{{include-optional:path}}` | Templates | Embed file if exists |

| `{{include-anchor:path#name}}` | Templates | Embed anchor content |

| `{{reference:path\|purpose}}` | Templates | Output path pointer (no embed) |

| `{{if:pack:name}}...{{/if}}` | Templates | Pack conditional |

| `{{if:config.path}}...{{/if}}` | Templates | Config conditional |

| `{{config.path.to.value}}` | Templates | Config variable |

| `{{source_layers}}` | Templates | Context variable |

| `{{timestamp}}` | Templates | Context variable |

| `{{PROJECT_EDISON_DIR}}` | Templates | Path variable |

---

## Part 2: Two-Phase Composition Architecture

### Why Two Phases?

| Single Phase (Current) | Two Phases (New) |

|------------------------|------------------|

| `{{include-anchor:VALIDATION.md#tdd}}` gets only CORE content | Gets FULLY COMPOSED content with pack extensions |

| Cross-file references miss pack/project overlays | All overlays included |

| Order-dependent, fragile | Clean separation of concerns |

### Phase 1: Layer Composition

Compose ALL source files first, merging sections/anchors from Core → Packs → Project:

```python
# Compose ALL entities and write intermediate files
for entity_type in ["guidelines", "agents", "validators", "constitutions"]:
    composer = LayeredComposer(repo_root, entity_type)
    for entity in composer.discover_all():
        content = composer.compose(entity, active_packs)
        # Sections/anchors are merged, markers PRESERVED
        output = generated_dir / entity_type / f"{entity}.md"
        output.write_text(content)
```

**Result:** `_generated/` contains files with:

- All `<!-- EXTEND: name -->` content merged into anchors/sections
- Anchor markers (`<!-- ANCHOR: name -->`) preserved for extraction
- Ready for Phase 2 processing

### Phase 2: Template Processing

Process the composed files for includes, anchors, variables:

```python
engine = TemplateEngine(config, repo_root)
engine.set_source_dir(generated_dir)  # Read from composed files!

for file in generated_dir.rglob("*.md"):
    content = file.read_text()
    # {{include-anchor:path#name}} extracts from COMPOSED files
    processed = engine.process(content)
    file.write_text(processed)  # Overwrite with final content
```

**Result:** `_generated/` contains final files with:

- All `{{include-anchor:}}` resolved to fully composed content
- All `{{include:}}` resolved
- All variables substituted
- Anchor markers optionally stripped (configurable)

### Composition Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: Layer Composition                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CORE                    PACKS                    PROJECT                │
│  guidelines/             packs/vitest/            .edison/               │
│  VALIDATION.md           guidelines/              guidelines/            │
│                          VALIDATION.md            VALIDATION.md          │
│                                                                          │
│  <!-- ANCHOR: tdd -->    <!-- EXTEND: tdd -->    <!-- EXTEND: tdd -->   │
│  - Test first            - Use vitest            - Project rule         │
│  <!-- END ANCHOR -->     <!-- /EXTEND -->        <!-- /EXTEND -->       │
│                                                                          │
│                              ↓ LayeredComposer                          │
│                                                                          │
│  _generated/guidelines/VALIDATION.md (COMPOSED)                         │
│  <!-- ANCHOR: tdd -->                                                   │
│  - Test first                                                            │
│  - Use vitest              ← Pack extension merged                      │
│  - Project rule            ← Project extension merged                   │
│  <!-- END ANCHOR: tdd -->                                               │
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
│  {{include-anchor:guidelines/VALIDATION.md#tdd}}                        │
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

### Transformation Pipeline (10 Steps)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TemplateEngine                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  1. INCLUDES             {{include:path}}                                │
│                          {{include-optional:path}}                       │
│     Recursive file inclusion (from composed files)                       │
│                                                                          │
│  2. ANCHOR EXTRACTION    {{include-anchor:path#name}}                   │
│     Extract content from composed anchors                                │
│                                                                          │
│  3. SECTION PLACEHOLDERS {{SECTION:Name}}                               │
│                          {{EXTENSIBLE_SECTIONS}}                        │
│                          {{APPEND_SECTIONS}}                            │
│     Replace any remaining placeholders                                   │
│                                                                          │
│  4. CONDITIONALS         {{if:pack:name}}...{{/if}}                     │
│                          {{if:config.path}}...{{/if}}                   │
│     Conditional content based on packs or config                         │
│                                                                          │
│  5. LOOPS                {{#each collection}}...{{/each}}               │
│     Iterate over arrays from context                                     │
│                                                                          │
│  6. CONFIG VARS          {{config.path.to.value}}                       │
│     Substitute from YAML configuration                                   │
│                                                                          │
│  7. CONTEXT VARS         {{source_layers}}, {{timestamp}}, etc.         │
│     Substitute from runtime context                                      │
│                                                                          │
│  8. PATH VARS            {{PROJECT_EDISON_DIR}}                         │
│     Resolve path placeholders                                            │
│                                                                          │
│  9. REFERENCES           {{reference:path|purpose}}                     │
│     Output pointers (no embedding)                                       │
│                                                                          │
│ 10. VALIDATION           Check for unresolved {{...}}                   │
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
│   ├── includes.py              # IncludeResolver + AnchorExtractor (unified)
│   ├── sections.py              # SectionProcessor
│   ├── conditionals.py          # ConditionalProcessor
│   ├── loops.py                 # LoopExpander
│   ├── variables.py             # ConfigVar, ContextVar, PathVar replacers
│   └── references.py            # ReferenceRenderer
├── core/
│   ├── base.py                  # CompositionBase (WUNI-001)
│   ├── composer.py              # LayeredComposer (updated for anchor extension)
│   ├── discovery.py             # LayerDiscovery
│   ├── sections.py              # SectionParser (updated for anchor extension)
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

| Steps | 6 | 10 |

| Anchor/Section | Separate | Unified - anchors extensible via EXTEND |

| Architecture | Single-phase | Two-phase |

### WTPL-002: Implement TemplateEngine

| Issue | Original | Correction |

|-------|----------|------------|

| Name | `CompositionPipeline` | `TemplateEngine` |

| Location | `core/pipeline.py` | `engine.py` |

| Transformers | Inline methods | `transformers/` module |

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

## Part 5: Updated Dependency Order

```
WTPL-000 (Syntax Consolidation)          ← Unify pack conditional syntax
    ↓
WUNI-002 (FileWriter)                    ← File writer BEFORE engine
    ↓
WTPL-001 (Design)                        ← TemplateEngine + unified anchors/sections
    ↓
WTPL-002 (Implementation)                ← Implement with two-phase architecture
    ↓
WUNI-001 (CompositionBase)               ← Shared base class
    ↓
WUNI-003 (OutputPathResolver)            ← Unified path resolution
    ↓
┌─────────┬─────────┬─────────┐
│ WUNI-004│ WUNI-005│ WUNI-006│          ← Parallel
└─────────┴─────────┴─────────┘
```

---

## Part 6: WTPL-000 - Syntax Consolidation (New Task)

### Problem

Two competing syntaxes for pack conditionals:

- `{{include-if:has-pack(name):path}}`
- `{{#if pack:name}}...{{/if}}`

### Solution

1. Deprecate `{{include-if:has-pack(name):path}}`
2. Unify to `{{if:pack:name}}...{{/if}}`
3. Update all templates in `edison.data`
4. Create migration guide

---

## Part 7: Implementation Details

### SectionParser Updates (for Anchor Extension)

```python
class SectionParser:
    # Existing patterns
    EXTEND_PATTERN = re.compile(r'<!-- EXTEND: (\w+) -->(.*?)<!-- /EXTEND -->')
    
    # NEW: Recognize anchors as extensible sections
    ANCHOR_PATTERN = re.compile(r'<!-- ANCHOR: (\w+) -->(.*?)<!-- END ANCHOR: \1 -->')
    
    def merge_extension_into_anchor(self, content: str, extensions: Dict[str, str]) -> str:
        """Merge EXTEND content into ANCHOR regions."""
        def replacer(match):
            anchor_name = match.group(1)
            anchor_content = match.group(2)
            if anchor_name in extensions:
                # Insert extension content BEFORE the end marker
                extended = anchor_content.rstrip() + "\n" + extensions[anchor_name]
                return f"<!-- ANCHOR: {anchor_name} -->{extended}\n<!-- END ANCHOR: {anchor_name} -->"
            return match.group(0)
        return self.ANCHOR_PATTERN.sub(replacer, content)
```

### TemplateEngine Anchor Extraction

```python
class TemplateEngine:
    def _extract_anchor(self, file_path: Path, anchor_name: str) -> str:
        """Extract anchor content from COMPOSED file."""
        # Read from composed files directory
        composed_file = self.source_dir / file_path
        if not composed_file.exists():
            raise FileNotFoundError(f"Composed file not found: {composed_file}")
        
        content = composed_file.read_text()
        pattern = re.compile(
            rf'<!-- ANCHOR: {re.escape(anchor_name)} -->(.*?)<!-- END ANCHOR: {re.escape(anchor_name)} -->',
            re.DOTALL
        )
        match = pattern.search(content)
        if not match:
            raise ValueError(f"Anchor '{anchor_name}' not found in {file_path}")
        
        return match.group(1).strip()
```

---

## Part 8: Duplication Elimination

| Area | Current | After | Savings |

|------|---------|-------|---------|

| Anchor + Section markers | Both needed | Unified | ~20 lines per file |

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

<!-- ANCHOR: tdd-rules -->
- Write tests before implementation
- Tests must fail first (RED)
<!-- END ANCHOR: tdd-rules -->

{{SECTION:PackRules}}
```

**Pack vitest:** `packs/vitest/guidelines/shared/VALIDATION.md`

```markdown
<!-- EXTEND: tdd-rules -->
- Use vitest for all tests
- Coverage must be > 80%
<!-- /EXTEND -->

<!-- EXTEND: PackRules -->
## Vitest Configuration
- Use `describe` and `it` blocks
<!-- /EXTEND -->
```

**Agent:** `agents/test-engineer.md`

```markdown
# Test Engineer

## TDD Requirements
{{include-anchor:guidelines/shared/VALIDATION.md#tdd-rules}}

## Full Guidelines
{{include:guidelines/shared/VALIDATION.md}}
```

### After Phase 1 (Layer Composition)

**`_generated/guidelines/shared/VALIDATION.md`:**

```markdown
# Validation Guidelines

<!-- ANCHOR: tdd-rules -->
- Write tests before implementation
- Tests must fail first (RED)
- Use vitest for all tests
- Coverage must be > 80%
<!-- END ANCHOR: tdd-rules -->

## Vitest Configuration
- Use `describe` and `it` blocks
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
```

### To-dos

- [ ] Update WUNI-004: RulesRegistry ALREADY extends BaseRegistry - task is outdated
- [ ] Reorder: WUNI-002 (FileWriter) should come BEFORE WTPL-002 (Pipeline)
- [ ] Add documentation: Explain relationship between CompositionPipeline and existing LayeredComposer
- [ ] Move CompositionBase location from composition/base.py to composition/core/base.py
- [ ] WUNI-005: Either create ConfigMixin or remove references to it