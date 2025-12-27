---
name: Edison Composition Unification - Comprehensive Architecture
overview: ""
todos:
  - id: d0364b43-0158-465b-b1f1-2c542793f171
    content: "Phase 0.1: Create ConditionEvaluator class with 8 condition functions (has-pack, config, config-eq, env, file-exists, not, and, or) in transformers/conditionals.py"
    status: pending
  - id: d041a6f7-06b2-4248-a59f-e971ecfb5f87
    content: "Phase 0.2: Migrate all Handlebars-style block conditionals {{#if pack:name}} to {{if:has-pack(name)}} in src/edison/data/**/*.md"
    status: pending
  - id: 71389138-63b3-4669-a5d2-f21d946d8990
    content: "Phase 0.3: Migrate all ANCHOR markers to SECTION markers (<!-- ANCHOR: --> → <!-- SECTION: -->) in src/edison/data/**/*.md"
    status: pending
  - id: f5a8913b-8aa3-429b-bc6a-fa78a86d36e8
    content: "Phase 0.4: Remove all deprecated placeholders ({{SECTION:Name}}, {{EXTENSIBLE_SECTIONS}}, {{APPEND_SECTIONS}}) from templates"
    status: pending
  - id: 52546694-6299-40b7-b71a-f9b5bef6a360
    content: "Phase 0.5: Add <!-- SECTION: composed-additions --> empty sections to core templates that need pack extensions"
    status: pending
  - id: 2bb6c042-eb0a-4fd4-9fa3-d01776191a60
    content: "Phase 0.6: Write comprehensive tests for ConditionEvaluator (all 8 functions + nested + errors)"
    status: pending
  - id: bcaf9179-8123-42ac-aa3c-550bb37c76b7
    content: "Phase 0.7: Verify Phase 0 - grep confirms no ANCHOR: or {{#if pack: patterns remain, all tests pass"
    status: pending
  - id: dbe35256-db29-49b6-86b2-1ef89ce3aa1b
    content: "Phase 1.1: Simplify SectionParser to only SECTION_PATTERN and EXTEND_PATTERN (remove ANCHOR, NEW_SECTION, APPEND handling)"
    status: pending
  - id: b95c0d4c-f04d-431b-b74e-8b35ee44aa72
    content: "Phase 1.2: Implement merge_extensions() method in SectionParser to merge EXTEND content into SECTION regions"
    status: pending
  - id: daea386d-fa65-4594-b768-6f72089f8c80
    content: "Phase 1.3: Update all {{include-anchor:path#name}} to {{include-section:path#name}} across codebase"
    status: pending
  - id: fc8e8bbc-aef5-490b-b362-44eaff5989f3
    content: "Phase 1.4: Write tests for SectionParser (parse_section, parse_extend, merge_single/multiple_extensions, preserves_markers)"
    status: pending
  - id: deae5f63-f814-49ee-97ff-047faee43efe
    content: "Phase 1.5: Verify Phase 1 - all SectionParser tests pass, no legacy patterns remain"
    status: pending
  - id: c84c5a45-c9c9-4b4a-a7c3-ebeed356c8b0
    content: "Phase 2.1: Create transformers/base.py with ContentTransformer abstract base class"
    status: pending
  - id: 1e92b0a7-d985-4f0d-8041-f80d101fb838
    content: "Phase 2.2: Create transformers/includes.py (IncludeResolver + SectionExtractor)"
    status: pending
  - id: 5e032363-dcff-4baa-a684-6965cf2e6a26
    content: "Phase 2.3: Extend transformers/conditionals.py with ConditionalProcessor transformer"
    status: pending
  - id: b29dc5f9-4a04-41f1-b62b-827195694faf
    content: "Phase 2.4: Create transformers/loops.py (LoopExpander for {{#each collection}})"
    status: pending
  - id: a577f5b2-4871-42d1-b7ab-9c230653a9d6
    content: "Phase 2.5: Create transformers/variables.py (ConfigVar, ContextVar, PathVar replacers)"
    status: pending
  - id: d3adf4d4-401f-4872-a403-dffd4cf94806
    content: "Phase 2.6: Create transformers/references.py (ReferenceRenderer for {{reference-section:}})"
    status: pending
  - id: f4e45248-4e7a-4cb0-ab42-b757d07d5c2c
    content: "Phase 2.7: Create core/report.py with CompositionReport dataclass"
    status: pending
  - id: 80b3fd39-0c20-4b92-a8ac-d574ab2ad479
    content: "Phase 2.8: Create engine.py with TemplateEngine class implementing 9-step transformation pipeline"
    status: pending
  - id: 54c8f340-ccc0-4ecd-a343-70b37913f619
    content: "Phase 2.9: Add resolve_single_include() helper function to includes.py for 3-layer search"
    status: pending
  - id: 0e68523b-459b-4f0a-b7d3-85bc4e1d223d
    content: "Phase 2.10: Update cli/compose/all.py for two-phase composition (Phase 1: LayeredComposer, Phase 2: TemplateEngine)"
    status: pending
  - id: f710995c-cf1d-4ce0-b761-f58e56f946e0
    content: "Phase 2.11: Write tests for TemplateEngine (all 9 transformations + two-phase integration)"
    status: pending
  - id: a1f14ec3-f863-4bed-a630-aca5f94b332e
    content: "Phase 2.12: Write tests for each individual transformer module"
    status: pending
  - id: 93f61f6e-0beb-4c36-ba0f-f20876cc2dcc
    content: "Phase 2.13: Verify Phase 2 - TemplateEngine processes all markers, two-phase works end-to-end"
    status: pending
  - id: 3d944255-6950-4f6a-91a5-830d8e986871
    content: "Phase 3.1: Create core/base.py with CompositionBase class (extract from BaseRegistry + IDEComposerBase)"
    status: pending
  - id: 523cc621-3c52-481a-80c5-2fe35ac4410b
    content: "Phase 3.2: Create output/writer.py with CompositionFileWriter (write_text, write_json, write_yaml, write_executable)"
    status: pending
  - id: 4cbf8c76-05c9-462b-8dfb-d36fb362d094
    content: "Phase 3.3: Create output/resolver.py with OutputPathResolver (merge OutputConfigLoader + CompositionPathResolver)"
    status: pending
  - id: f0cdda71-42b9-42e4-b8c0-e86049585ed7
    content: "Phase 3.4: Create core/errors.py with unified error hierarchy (12 error classes)"
    status: pending
  - id: 1a6d9f24-5b2b-412f-883e-0d1b50967e95
    content: "Phase 3.5: Create core/metadata.py with MetadataExtractor for unified frontmatter parsing"
    status: pending
  - id: 0ece0996-a03f-41a9-851d-beaf0029a97f
    content: "Phase 3.6: Write tests for all Phase 3 infrastructure (base, writer, resolver, errors, metadata)"
    status: pending
  - id: 24c823c0-9a5c-4646-9f77-553cc62b479b
    content: "Phase 3.7: Verify Phase 3 - ~90 lines duplication eliminated, all infrastructure tests pass"
    status: pending
  - id: 82816ce4-69d0-46f8-84b7-2a4d80722581
    content: "Phase 4.1: Update BaseRegistry to extend CompositionBase, implement _setup_composition_dirs()"
    status: pending
  - id: 56602a84-2823-40c6-8370-91b3047263c5
    content: "Phase 4.2: Update IDEComposerBase to extend CompositionBase, implement _setup_composition_dirs()"
    status: pending
  - id: 0a4bcce7-f4dd-4d35-af5c-9c486606745f
    content: "Phase 4.3: Update GuidelineRegistry to use LayeredComposer and LayerDiscovery"
    status: pending
  - id: a781d0fb-52cd-4cd0-8af6-1f3fb871d30c
    content: "Phase 4.4: Update FilePatternRegistry to use CompositionPathResolver"
    status: pending
  - id: 7508a04b-db81-42f8-87e1-eedccd59cec4
    content: "Phase 4.5: Update JsonSchemaComposer to use CompositionFileWriter"
    status: pending
  - id: 12191ba7-f971-4a39-b20e-fcf61bf2e022
    content: "Phase 4.6: Add _load_yaml_with_fallback(), _load_layered_config(), _merge_with_handlers() to IDEComposerBase"
    status: pending
  - id: 802e9f54-2ba8-4d2e-92e0-acfcad93a24c
    content: "Phase 4.7: Migrate IDE composers (hooks, commands, settings, coderabbit) to use _load_layered_config()"
    status: pending
  - id: 625e6338-9d67-4183-876e-63e5cc888676
    content: "Phase 4.8: Consolidate ZenSync - create zen.py, delete 5 files in zen/ directory"
    status: pending
  - id: f89a1a62-af5c-4a67-8e9e-8f78ac42f822
    content: "Phase 4.9: Consolidate PromptAdapter base classes - enhance adapters/base.py, delete prompt/base.py"
    status: pending
  - id: e9d8a122-a011-4ad5-a616-0bccb550aa17
    content: "Phase 4.10: Fix CodexAdapter to use ConfigMixin instead of duplicate _load_config()"
    status: pending
  - id: 80be3ff5-0438-4228-9842-8a26b0b40107
    content: "Phase 4.11: Update ClaudeSync and CursorSync adapters to use ConfigMixin"
    status: pending
  - id: 62ca3039-f190-46fa-86a0-a5a985be6330
    content: "Phase 4.12: Update all registries to use unified error hierarchy from core/errors.py"
    status: pending
  - id: c9bb37f6-e20c-4c32-b9ff-615929a70694
    content: "Phase 4.13: Final verification - all tests pass, ~200+ lines eliminated, edison compose all works"
    status: pending
---

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

| `{{include-if:CONDITION:path}}` | Templates | Conditional file include |

| `{{if:CONDITION}}...{{/if}}` | Templates | Conditional block |

| `{{if:CONDITION}}...{{else}}...{{/if}}` | Templates | Conditional if-else block |

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
│  3. CONDITIONALS         {{include-if:CONDITION:path}}                  │
│                          {{if:CONDITION}}...{{else}}...{{/if}}          │
│     Function-based conditions: has-pack(), config(), env(), etc.         │
│                                                                          │
│  4. LOOPS                {{#each collection}}...{{/each}}               │
│                          (Handlebars-style for constitutions)            │
│     Iterate over arrays from context (mandatoryReads, optionalReads)     │
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

### Phase 0: Syntax Consolidation (WTPL-000) - PREREQUISITE

**Goal:** Unify all template syntax before main implementation.

**Changes:**

1. **Keep** `{{include-if:CONDITION:path}}` for conditional file inclusion
2. **Unify** block conditionals to `{{if:CONDITION}}...{{/if}}` with function-based conditions
3. **Add** `{{else}}` support for if-else blocks
4. **Migrate** `<!-- ANCHOR: -->` to `<!-- SECTION: -->`
5. **Remove** deprecated: `{{SECTION:Name}}`, `{{EXTENSIBLE_SECTIONS}}`, `{{APPEND_SECTIONS}}`
6. **Update** all templates in `edison.data`
7. **Create** migration guide for existing projects

**Condition Functions to Implement:**

- `has-pack(name)` - Check if pack is active
- `config(path)` - Check config value truthy
- `config-eq(path, value)` - Config equals value
- `env(name)` - Environment variable set
- `file-exists(path)` - File exists in project
- `not(expr)`, `and(expr1, expr2)`, `or(expr1, expr2)` - Logical operators

**Files to modify:**

```
src/edison/data/**/*.md                     # All templates
src/edison/core/composition/transformers/conditionals.py  # ConditionEvaluator
```

**Verification:**

- Run `grep -r "ANCHOR:" src/edison/data` should return 0 results
- Run `grep -r "{{#if pack:" src/edison/data` should return 0 results (old Handlebars syntax)

---

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

**Step 4.3:** Update GuidelineRegistry to use LayeredComposer and LayerDiscovery

**Step 4.4:** Update FilePatternRegistry to use CompositionPathResolver (currently uses PathResolver)

**Step 4.5:** Update JsonSchemaComposer to use CompositionFileWriter

**Step 4.6:** Update sync adapters to use ConfigMixin

**Step 4.7:** Add `_load_layered_config()` to IDEComposerBase

**Step 4.8:** Consolidate PromptAdapter base classes (adapters/base.py + adapters/prompt/base.py → single file)

### Execution Order

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
   │           │           │           │           │
   ↓           ↓           ↓           ↓           ↓
  PR #0       PR #1       PR #2       PR #3       PR #4
(Syntax)   (Markers)  (Engine)   (Infra)    (Unify)
```

**Phase Dependencies:**

- Phase 0 (WTPL-000): No dependencies - can start immediately
- Phase 1: Depends on Phase 0 (syntax consolidated before marker migration)
- Phase 2: Depends on Phase 1 (markers unified before engine implementation)
- Phase 3: Depends on Phase 2 (engine exists before infrastructure extraction)
- Phase 4: Depends on Phase 3 (base classes exist before registry/adapter migration)

---

## Part 6: Unified Condition Expression System

### Problem

Multiple competing syntaxes for conditionals:

- `{{include-if:has-pack(name):path}}` - function-based, file inclusion
- `{{#if pack:name}}...{{/if}}` - block-based, Handlebars style
- `{{if:pack:name}}...{{/if}}` - simplified block syntax

### Solution: Function-Based Condition Expressions

Implement a unified condition expression system with functions:

#### Directive Types

| Directive | Syntax | Purpose |

|-----------|--------|---------|

| **Conditional Include** | `{{include-if:CONDITION:path}}` | Include file if condition true |

| **Conditional Block** | `{{if:CONDITION}}...{{/if}}` | Include content block if condition true |

| **Conditional Else** | `{{if:CONDITION}}...{{else}}...{{/if}}` | If-else blocks |

#### Condition Functions

| Function | Example | Returns | Purpose |

|----------|---------|---------|---------|

| `has-pack(name)` | `has-pack(python)` | bool | Check if pack is active |

| `config(path)` | `config(features.auth)` | bool (truthy) | Check config value exists and truthy |

| `config-eq(path, value)` | `config-eq(project.type, api)` | bool | Config equals value |

| `env(name)` | `env(CI)` | bool | Check environment variable set |

| `file-exists(path)` | `file-exists(.eslintrc)` | bool | Check file exists in project |

| `not(expr)` | `not(has-pack(legacy))` | bool | Negate condition |

| `and(expr1, expr2)` | `and(has-pack(python), config(strict))` | bool | Both conditions true |

| `or(expr1, expr2)` | `or(has-pack(vitest), has-pack(jest))` | bool | Either condition true |

#### Examples

```markdown
# Conditional file inclusion
{{include-if:has-pack(python):guidelines/PYTHON.md}}
{{include-if:config(features.auth):guidelines/AUTH.md}}
{{include-if:and(has-pack(python), config(strict)):guidelines/STRICT_PYTHON.md}}

# Conditional blocks
{{if:has-pack(vitest)}}
## Vitest Configuration
Use `describe` and `it` blocks for test organization.
{{/if}}

{{if:config-eq(project.type, api)}}
## API Guidelines
Follow REST conventions.
{{else}}
## General Guidelines
Follow standard patterns.
{{/if}}

# Negation
{{if:not(has-pack(legacy))}}
Use modern patterns only.
{{/if}}

# Complex conditions
{{include-if:or(has-pack(vitest), has-pack(jest)):guidelines/TESTING.md}}
```

#### Implementation

```python
class ConditionEvaluator:
    """Evaluate condition expressions."""

    FUNCTION_PATTERN = re.compile(r'^(\w+(?:-\w+)*)\(([^)]*)\)$')

    def __init__(self, context: "CompositionContext"):
        self.context = context
        self.functions = {
            "has-pack": self._has_pack,
            "config": self._config_truthy,
            "config-eq": self._config_eq,
            "env": self._env,
            "file-exists": self._file_exists,
            "not": self._not,
            "and": self._and,
            "or": self._or,
        }

    def evaluate(self, expr: str) -> bool:
        """Evaluate a condition expression."""
        expr = expr.strip()
        match = self.FUNCTION_PATTERN.match(expr)
        if not match:
            raise ValueError(f"Invalid condition expression: {expr}")

        func_name = match.group(1)
        args_str = match.group(2)

        if func_name not in self.functions:
            raise ValueError(f"Unknown condition function: {func_name}")

        args = self._parse_args(args_str)
        return self.functions[func_name](*args)

    def _has_pack(self, pack_name: str) -> bool:
        return pack_name in self.context.active_packs

    def _config_truthy(self, path: str) -> bool:
        value = self.context.get_config(path)
        return bool(value)

    def _config_eq(self, path: str, expected: str) -> bool:
        value = self.context.get_config(path)
        return str(value) == expected

    def _env(self, name: str) -> bool:
        return bool(os.environ.get(name))

    def _file_exists(self, path: str) -> bool:
        return (self.context.project_root / path).exists()

    def _not(self, expr: str) -> bool:
        return not self.evaluate(expr)

    def _and(self, expr1: str, expr2: str) -> bool:
        return self.evaluate(expr1) and self.evaluate(expr2)

    def _or(self, expr1: str, expr2: str) -> bool:
        return self.evaluate(expr1) or self.evaluate(expr2)
```

---

## Part 6b: WTPL-000 - Syntax Consolidation Details

### Changes Required

1. **Keep** `{{include-if:CONDITION:path}}` - clearer for file inclusion
2. **Unify** block conditionals to `{{if:CONDITION}}...{{/if}}`
3. **Add** `{{else}}` support for if blocks
4. **Migrate** `<!-- ANCHOR: -->` to `<!-- SECTION: -->`
5. **Remove** deprecated: `{{SECTION:Name}}`, `{{EXTENSIBLE_SECTIONS}}`, `{{APPEND_SECTIONS}}`
6. **Update** all templates in `edison.data`
7. **Create** migration guide for existing projects

### Migration Examples

**Before:**

```markdown
{{#if pack:python}}
Python content
{{/if}}
```

**After:**

```markdown
{{if:has-pack(python)}}
Python content
{{/if}}
```

**Before:**

```markdown
{{include-if:has-pack(vitest):path}}
```

**After:** (unchanged - this syntax is good!)

```markdown
{{include-if:has-pack(vitest):path}}
```

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
src/edison/core/composition/core/errors.py            # Unified error hierarchy
src/edison/core/composition/core/metadata.py          # MetadataExtractor for frontmatter
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
src/edison/core/composition/registries/agents.py              # Use unified errors
src/edison/core/composition/registries/guidelines.py          # Use LayerDiscovery
src/edison/core/composition/registries/validators.py
src/edison/core/composition/registries/file_patterns.py       # Use CompositionPathResolver
src/edison/core/composition/registries/schemas.py             # Use CompositionFileWriter
src/edison/core/composition/registries/documents.py           # Document as good pattern
src/edison/core/composition/registries/constitutions.py       # TemplateEngine integration
src/edison/core/composition/registries/rules.py               # Unified errors
src/edison/core/adapters/base.py                               # Consolidate with prompt/base.py
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
src/edison/core/adapters/prompt/base.py                # Consolidated into adapters/base.py
```

---

## Part 20: Verification Checklists

### Phase 0: Syntax Consolidation (WTPL-000)

- [ ] `{{include-if:CONDITION:path}}` syntax retained (clearer for file inclusion)
- [ ] Block conditionals unified to `{{if:CONDITION}}...{{/if}}` with function syntax
- [ ] `{{else}}` support added for if-else blocks
- [ ] ConditionEvaluator implemented with 8 functions (has-pack, config, config-eq, env, file-exists, not, and, or)
- [ ] All `<!-- ANCHOR:` → `<!-- SECTION:`
- [ ] All deprecated placeholders removed
- [ ] Migration guide created
- [ ] Tests pass for all condition functions

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

- [ ] GuidelineRegistry uses LayeredComposer and LayerDiscovery
- [ ] FilePatternRegistry uses CompositionPathResolver
- [ ] JsonSchemaComposer uses CompositionFileWriter
- [ ] _load_layered_config added to IDEComposerBase
- [ ] IDE composers migrated (HookComposer, CommandComposer, SettingsComposer, CodeRabbitComposer)
- [ ] ZenSync consolidated (5 files -> 1)
- [ ] PromptAdapter base classes consolidated (2 files -> 1)
- [ ] CodexAdapter uses ConfigMixin
- [ ] Zen directory deleted
- [ ] Unified error hierarchy adopted across all registries
- [ ] MetadataExtractor used for frontmatter parsing
- [ ] ~200+ lines duplication eliminated
- [ ] All tests pass

---

## Part 21: Success Criteria

1. **Single TemplateEngine** handles ALL template processing (9-step pipeline)
2. **4-concept section system** replaces 12+ markers (SECTION, EXTEND, include-section, reference-section)
3. **Two-phase composition** ensures cross-file references get fully composed content
4. **CompositionBase** eliminates ~90 lines of duplication (BaseRegistry + IDEComposerBase)
5. **CompositionFileWriter** centralizes all file I/O (18 write points migrated)
6. **OutputPathResolver** single source of truth for paths (merges OutputConfigLoader + CompositionPathResolver)
7. **Unified error hierarchy** with `CompositionError` base class and 10+ specific errors
8. **MetadataExtractor** unified frontmatter parsing across all content types
9. **4 composition modes documented** and all flowing through TemplateEngine Phase 2
10. **~200+ lines** of duplication eliminated total
11. **All tests pass** (unit, integration, e2e)
12. **`edison compose all`** produces fully processed output with comprehensive report

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


class AgentNotFoundError(EntityNotFoundError):
    """Agent not found in registry."""

    def __init__(self, agent_id: str):
        super().__init__("agent", agent_id)


class AgentTemplateError(CompositionError):
    """Error in agent template processing."""

    def __init__(self, agent_id: str, reason: str):
        super().__init__(f"Agent template error for '{agent_id}': {reason}")
        self.agent_id = agent_id
        self.reason = reason


class ValidatorNotFoundError(EntityNotFoundError):
    """Validator not found in registry."""

    def __init__(self, validator_id: str):
        super().__init__("validator", validator_id)


class DocumentTemplateNotFoundError(EntityNotFoundError):
    """Document template not found."""

    def __init__(self, template_id: str):
        super().__init__("document_template", template_id)


class AnchorNotFoundError(CompositionError):
    """Anchor not found in guideline file."""

    def __init__(self, anchor_name: str, file_path: str):
        super().__init__(f"Anchor '{anchor_name}' not found in {file_path}")
        self.anchor_name = anchor_name
        self.file_path = file_path


class RulesCompositionError(CompositionError):
    """Error during rules composition."""

    def __init__(self, rule_id: str, reason: str):
        super().__init__(f"Rules composition error for '{rule_id}': {reason}")
        self.rule_id = rule_id
        self.reason = reason
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

### Key Test Cases for ConditionEvaluator

```python
class TestConditionEvaluator:
    """Tests for function-based condition evaluation."""

    def test_has_pack_active(self, context_with_packs):
        """Test has-pack(python) returns True when python pack active."""

    def test_has_pack_inactive(self, context_without_packs):
        """Test has-pack(python) returns False when python pack not active."""

    def test_config_truthy(self, context_with_config):
        """Test config(features.auth) returns True for truthy value."""

    def test_config_falsy(self, context_with_config):
        """Test config(features.disabled) returns False for falsy value."""

    def test_config_eq_match(self, context_with_config):
        """Test config-eq(project.type, api) matches."""

    def test_config_eq_no_match(self, context_with_config):
        """Test config-eq(project.type, web) doesn't match."""

    def test_env_set(self, monkeypatch):
        """Test env(CI) returns True when CI env var set."""

    def test_env_not_set(self):
        """Test env(NONEXISTENT) returns False."""

    def test_file_exists_true(self, tmp_path):
        """Test file-exists(.eslintrc) when file exists."""

    def test_file_exists_false(self, tmp_path):
        """Test file-exists(.eslintrc) when file doesn't exist."""

    def test_not_operator(self, context_with_packs):
        """Test not(has-pack(legacy)) negates result."""

    def test_and_both_true(self, context_with_packs):
        """Test and(has-pack(python), has-pack(vitest)) both true."""

    def test_and_one_false(self, context_with_packs):
        """Test and(has-pack(python), has-pack(legacy)) one false."""

    def test_or_one_true(self, context_with_packs):
        """Test or(has-pack(vitest), has-pack(jest)) one true."""

    def test_or_both_false(self, context_without_packs):
        """Test or(has-pack(vitest), has-pack(jest)) both false."""

    def test_nested_conditions(self, context_with_packs):
        """Test and(has-pack(python), not(has-pack(legacy))) nested."""

    def test_invalid_function_raises(self, context):
        """Test unknown function raises ValueError."""
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

    def test_process_include_if_true(self, tmp_path):
        """Test {{include-if:has-pack(python):path}} includes when true."""

    def test_process_include_if_false(self, tmp_path):
        """Test {{include-if:has-pack(legacy):path}} skips when false."""

    def test_process_if_block_true(self, tmp_path):
        """Test {{if:has-pack(python)}}...{{/if}} includes content."""

    def test_process_if_block_false(self, tmp_path):
        """Test {{if:has-pack(legacy)}}...{{/if}} excludes content."""

    def test_process_if_else_true_branch(self, tmp_path):
        """Test {{if:COND}}A{{else}}B{{/if}} returns A when true."""

    def test_process_if_else_false_branch(self, tmp_path):
        """Test {{if:COND}}A{{else}}B{{/if}} returns B when false."""

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

---

## Appendix G: Composition Modes Documentation

The codebase currently has 4 distinct composition modes that need to be understood:

### Mode 1: Section-Based Composition (Agents, Validators, Documents)

Uses `LayeredComposer` with `SectionParser`:

- `<!-- SECTION: name -->...<!-- /SECTION: name -->` defines sections
- `<!-- EXTEND: name -->...<!-- /EXTEND -->` extends sections
- Sections are merged in layer order: Core → Packs → Project

**Used by:** `AgentRegistry`, `ValidatorRegistry`, `DocumentTemplateRegistry`

### Mode 2: Concatenate + Dedupe (Guidelines)

Direct file concatenation with DRY detection:

- Files from all layers concatenated
- Shingle-based deduplication (configurable)
- No section markers, just raw content

**Used by:** `GuidelineRegistry`

**NOTE:** Should migrate to use `LayerDiscovery` for consistent discovery patterns

### Mode 3: YAML Merge (Rules, FilePatterns, Schemas)

YAML deep-merge across layers:

- Core YAML → Pack YAML → Project YAML
- Uses `deep_merge()` from ConfigManager
- Key-based override

**Used by:** `RulesRegistry`, `FilePatternRegistry`, `JsonSchemaComposer`

### Mode 4: Template Rendering (Constitutions)

Handlebars-style templates with:

- `{{#each collection}}...{{/each}}` loops
- `{{variable}}` substitution
- Direct string replacement

**Used by:** `constitutions.py` (functional module)

**NOTE:** Should integrate with unified `TemplateEngine`

### Unification Strategy

After this refactoring, all modes should flow through `TemplateEngine`:

1. **Layer composition** (Phase 1) handles mode-specific merging
2. **Template processing** (Phase 2) handles all `{{...}}` patterns uniformly

---

## Appendix H: MetadataExtractor

**Location:** `src/edison/core/composition/core/metadata.py`

**Purpose:** Unified frontmatter/metadata extraction for all content types.

```python
"""Unified metadata extraction for Edison content."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


@dataclass
class ContentMetadata:
    """Extracted metadata from content file."""
    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = None
    dependencies: list[str] = None
    raw: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
        if self.raw is None:
            self.raw = {}


class MetadataExtractor:
    """Extract metadata from content files.

    Handles:
    - YAML frontmatter (--- ... ---)
    - HTML comment frontmatter (<!-- FRONTMATTER ... -->)
    - Inline metadata (first H1, description paragraphs)
    """

    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL
    )
    HTML_FRONTMATTER_PATTERN = re.compile(
        r'^<!--\s*FRONTMATTER\s*\n(.*?)\n\s*-->\s*\n',
        re.DOTALL
    )

    def extract(self, content: str, default_name: str = "unknown") -> Tuple[ContentMetadata, str]:
        """Extract metadata and return (metadata, remaining_content)."""
        metadata_dict = {}
        remaining = content

        # Try YAML frontmatter first
        match = self.FRONTMATTER_PATTERN.match(content)
        if match:
            try:
                metadata_dict = yaml.safe_load(match.group(1)) or {}
                remaining = content[match.end():]
            except yaml.YAMLError:
                pass

        # Try HTML comment frontmatter
        if not metadata_dict:
            match = self.HTML_FRONTMATTER_PATTERN.match(content)
            if match:
                try:
                    metadata_dict = yaml.safe_load(match.group(1)) or {}
                    remaining = content[match.end():]
                except yaml.YAMLError:
                    pass

        # Extract title from first H1 if not in frontmatter
        if "title" not in metadata_dict:
            title_match = re.search(r'^#\s+(.+)$', remaining, re.MULTILINE)
            if title_match:
                metadata_dict["title"] = title_match.group(1).strip()

        return ContentMetadata(
            name=metadata_dict.get("name", default_name),
            title=metadata_dict.get("title"),
            description=metadata_dict.get("description"),
            category=metadata_dict.get("category"),
            tags=metadata_dict.get("tags", []),
            dependencies=metadata_dict.get("dependencies", []),
            raw=metadata_dict,
        ), remaining

    def extract_from_file(self, path: Path) -> Tuple[ContentMetadata, str]:
        """Extract metadata from a file."""
        content = path.read_text(encoding="utf-8")
        default_name = path.stem
        return self.extract(content, default_name)
```

**Usage:**

```python
extractor = MetadataExtractor()

# From string
metadata, content = extractor.extract(raw_content, "my-agent")

# From file
metadata, content = extractor.extract_from_file(Path("agents/test-engineer.md"))

# Access metadata
print(metadata.title)       # "Test Engineer"
print(metadata.category)    # "development"
print(metadata.tags)        # ["testing", "tdd"]
```

# Edison Composition Unification - Implementation Plan

## Overview

This plan implements a unified template processing system with:

- **4-concept section system** replacing 12+ markers
- **Two-phase composition** (compose ALL files, THEN process templates)
- **9-step TemplateEngine** transformation pipeline
- **~200+ lines** duplication elimination

## Phase Dependencies

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4
(Syntax)  (Markers)  (Engine)  (Infra)   (Unify)
```

---

## Phase 0: Syntax Consolidation (WTPL-000)

**Goal:** Unify all template syntax before main implementation.

### 0.1 Implement ConditionEvaluator

**File:** `src/edison/core/composition/transformers/conditionals.py`

Create `ConditionEvaluator` class with 8 condition functions:

- `has-pack(name)` - Check if pack is active
- `config(path)` - Check config value truthy
- `config-eq(path, value)` - Config equals value
- `env(name)` - Environment variable set
- `file-exists(path)` - File exists in project
- `not(expr)` - Negate condition
- `and(expr1, expr2)` - Both conditions true
- `or(expr1, expr2)` - Either condition true

### 0.2 Migrate Block Conditionals in Templates

**Files:** `src/edison/data/**/*.md`

Transform all Handlebars-style conditionals:

```
{{#if pack:python}} → {{if:has-pack(python)}}
{{/if}}            → {{/if}}
```

### 0.3 Migrate ANCHOR to SECTION Markers

**Files:** `src/edison/data/**/*.md`

Transform all anchor markers:

```
<!-- ANCHOR: name -->     → <!-- SECTION: name -->
<!-- END ANCHOR: name --> → <!-- /SECTION: name -->
```

### 0.4 Remove Deprecated Placeholders

**Files:** `src/edison/data/**/*.md`

Remove all occurrences of:

- `{{SECTION:Name}}`
- `{{EXTENSIBLE_SECTIONS}}`
- `{{APPEND_SECTIONS}}`

### 0.5 Add composed-additions Sections

**Files:** Core templates that need pack extensions

Add empty sections where packs should inject content:

```markdown
<!-- SECTION: composed-additions -->
<!-- /SECTION: composed-additions -->
```

### 0.6 Write Tests for ConditionEvaluator

**File:** `tests/unit/composition/transformers/test_conditionals.py`

Test all 8 condition functions + nested conditions + error cases.

### 0.7 Verification

- `grep -r "ANCHOR:" src/edison/data` returns 0 results
- `grep -r "{{#if pack:" src/edison/data` returns 0 results
- All condition function tests pass

---

## Phase 1: Marker Migration and SectionParser Update

**Goal:** Simplify SectionParser to handle only SECTION/EXTEND markers.

### 1.1 Update SectionParser

**File:** `src/edison/core/composition/core/sections.py`

Simplify to only two patterns:

```python
SECTION_PATTERN = re.compile(
    r'<!-- SECTION: (\w+) -->(.*?)<!-- /SECTION: \1 -->',
    re.DOTALL
)
EXTEND_PATTERN = re.compile(
    r'<!-- EXTEND: (\w+) -->(.*?)<!-- /EXTEND -->',
    re.DOTALL
)
```

Remove handling for:

- `<!-- ANCHOR: -->` / `<!-- END ANCHOR: -->`
- `<!-- NEW_SECTION: -->`
- `<!-- APPEND -->`

### 1.2 Implement merge_extensions Method

**File:** `src/edison/core/composition/core/sections.py`

Add `merge_extensions(content, extensions)` method that merges EXTEND content into SECTION regions.

### 1.3 Update include-anchor to include-section

**Files:** All files using `{{include-anchor:path#name}}`

Transform to `{{include-section:path#name}}`.

### 1.4 Write Tests for SectionParser

**File:** `tests/unit/composition/core/test_sections.py`

Test:

- `parse_section()` - SECTION marker parsing
- `parse_extend()` - EXTEND marker parsing
- `merge_single_extension()` - One EXTEND into SECTION
- `merge_multiple_extensions()` - Multiple EXTENDs
- `merge_preserves_markers()` - Markers preserved after merge
- `composed_additions_convention()` - New content section

### 1.5 Verification

- All SectionParser tests pass
- No legacy marker patterns in codebase
- Existing composition still works

---

## Phase 2: TemplateEngine Implementation

**Goal:** Create unified TemplateEngine with 9-step transformation pipeline.

### 2.1 Create Transformers Base

**File:** `src/edison/core/composition/transformers/base.py`

```python
class ContentTransformer(ABC):
    @abstractmethod
    def transform(self, content: str, context: "CompositionContext") -> str: ...
```

### 2.2 Create Individual Transformers

**Files:**

- `src/edison/core/composition/transformers/__init__.py`
- `src/edison/core/composition/transformers/includes.py` (IncludeResolver + SectionExtractor)
- `src/edison/core/composition/transformers/conditionals.py` (ConditionalProcessor - extend existing)
- `src/edison/core/composition/transformers/loops.py` (LoopExpander for `{{#each}}`)
- `src/edison/core/composition/transformers/variables.py` (ConfigVar, ContextVar, PathVar)
- `src/edison/core/composition/transformers/references.py` (ReferenceRenderer)

### 2.3 Create CompositionReport

**File:** `src/edison/core/composition/core/report.py`

Dataclass tracking:

- `files_written: List[Path]`
- `variables_substituted: Set[str]`
- `variables_missing: Set[str]`
- `includes_resolved: Set[str]`
- `sections_processed: Set[str]`
- `warnings: List[str]`
- `errors: List[str]`

### 2.4 Create TemplateEngine

**File:** `src/edison/core/composition/engine.py`

9-step transformation pipeline:

1. INCLUDES - `{{include:path}}`, `{{include-optional:path}}`
2. SECTION EXTRACTION - `{{include-section:path#name}}`
3. CONDITIONALS - `{{include-if:COND:path}}`, `{{if:COND}}...{{/if}}`
4. LOOPS - `{{#each collection}}...{{/each}}`
5. CONFIG VARS - `{{config.path.to.value}}`
6. CONTEXT VARS - `{{source_layers}}`, `{{timestamp}}`
7. PATH VARS - `{{PROJECT_EDISON_DIR}}`
8. REFERENCES - `{{reference-section:path#name|purpose}}`
9. VALIDATION - Check for unresolved `{{...}}`

### 2.5 Add resolve_single_include Helper

**File:** `src/edison/core/composition/includes.py`

Add helper function for TemplateEngine include resolution with 3-layer search.

### 2.6 Update CLI for Two-Phase Composition

**File:** `src/edison/cli/compose/all.py`

Implement two-phase flow:

- **Phase 1:** LayeredComposer composes ALL entities, writes to `_generated/`
- **Phase 2:** TemplateEngine processes `_generated/` files

### 2.7 Write Tests for TemplateEngine

**File:** `tests/unit/composition/test_engine.py`

Test all 9 transformation steps + two-phase integration.

### 2.8 Write Tests for Each Transformer

**Files:**

- `tests/unit/composition/transformers/test_includes.py`
- `tests/unit/composition/transformers/test_loops.py`
- `tests/unit/composition/transformers/test_variables.py`
- `tests/unit/composition/transformers/test_references.py`

### 2.9 Verification

- TemplateEngine processes all marker types
- Two-phase composition works end-to-end
- `{{include-section:}}` extracts from COMPOSED files
- All tests pass

---

## Phase 3: Infrastructure Unification

**Goal:** Create shared base classes and utilities.

### 3.1 Create CompositionBase

**File:** `src/edison/core/composition/core/base.py`

Extract common code from BaseRegistry + IDEComposerBase:

- Unified path resolution (`project_root`, `project_dir`)
- Config manager access (`cfg_mgr`, `config`)
- Active packs discovery (`get_active_packs()`)
- YAML loading utilities (`load_yaml_safe`, `merge_yaml`)
- Definition merging (`merge_definitions`)

### 3.2 Create CompositionFileWriter

**File:** `src/edison/core/composition/output/writer.py`

Centralized file writing:

- `write_text(path, content)` - Text files
- `write_json(path, data)` - JSON files with atomic write
- `write_yaml(path, data)` - YAML files
- `write_executable(path, content)` - Scripts with chmod +x
- File tracking for reporting

### 3.3 Create OutputPathResolver

**File:** `src/edison/core/composition/output/resolver.py`

Merge `OutputConfigLoader` + `CompositionPathResolver`:

- `resolve_template()` - Resolve `{{PROJECT_EDISON_DIR}}`
- `get_agents_dir()`, `get_validators_dir()`, `get_guidelines_dir()`
- `get_constitution_path(role)`, `get_client_path(client_name)`

### 3.4 Create Unified Error Hierarchy

**File:** `src/edison/core/composition/core/errors.py`

Error classes:

- `CompositionError` (base)
- `EntityNotFoundError`, `SectionNotFoundError`, `IncludeNotFoundError`
- `CompositionValidationError`, `ConfigVariableNotFoundError`
- `AgentNotFoundError`, `AgentTemplateError`, `ValidatorNotFoundError`
- `DocumentTemplateNotFoundError`, `AnchorNotFoundError`, `RulesCompositionError`

### 3.5 Create MetadataExtractor

**File:** `src/edison/core/composition/core/metadata.py`

Unified frontmatter parsing:

- YAML frontmatter (`--- ... ---`)
- HTML comment frontmatter (`<!-- FRONTMATTER ... -->`)
- Inline metadata (H1 title, description)

### 3.6 Write Tests for Infrastructure

**Files:**

- `tests/unit/composition/test_base.py`
- `tests/unit/composition/output/test_writer.py`
- `tests/unit/composition/output/test_resolver.py`
- `tests/unit/composition/core/test_errors.py`
- `tests/unit/composition/core/test_metadata.py`

### 3.7 Verification

- CompositionBase eliminates ~90 lines duplication
- CompositionFileWriter handles all 18 write points
- All tests pass

---

## Phase 4: Registry, Adapter, IDE Composer Unification

**Goal:** Apply unified patterns across all composers.

### 4.1 Update BaseRegistry to Extend CompositionBase

**File:** `src/edison/core/entity/registry.py`

```python
class BaseRegistry(CompositionBase, Generic[T]):
    def _setup_composition_dirs(self) -> None:
        self.core_dir = self.project_dir / "core"
        self.packs_dir = self.project_dir / "packs"
```

### 4.2 Update IDEComposerBase to Extend CompositionBase

**File:** `src/edison/core/composition/ide/base.py`

```python
class IDEComposerBase(CompositionBase):
    def _setup_composition_dirs(self) -> None:
        self.core_dir = Path(get_data_path(""))
        self.bundled_packs_dir = Path(get_data_path("packs"))
        self.project_packs_dir = self.project_dir / "packs"
```

### 4.3 Update GuidelineRegistry

**File:** `src/edison/core/composition/registries/guidelines.py`

Use `LayeredComposer` and `LayerDiscovery` instead of manual discovery.

### 4.4 Update FilePatternRegistry

**File:** `src/edison/core/composition/registries/file_patterns.py`

Use `CompositionPathResolver` instead of `PathResolver`.

### 4.5 Update JsonSchemaComposer

**File:** `src/edison/core/composition/registries/schemas.py`

Use `CompositionFileWriter` for output.

### 4.6 Add _load_layered_config to IDEComposerBase

**File:** `src/edison/core/composition/ide/base.py`

Add utility methods:

- `_load_yaml_with_fallback()` - Try .yaml then .yml
- `_load_layered_config()` - Core → Packs → Project merge
- `_merge_with_handlers()` - Custom key handlers

### 4.7 Migrate IDE Composers

**Files:**

- `src/edison/core/composition/ide/hooks.py` - Use `_load_layered_config()`
- `src/edison/core/composition/ide/commands.py` - Use `_load_layered_config()`
- `src/edison/core/composition/ide/settings.py` - Use `_load_layered_config()`
- `src/edison/core/composition/ide/coderabbit.py` - Use `_load_layered_config()`

### 4.8 Consolidate ZenSync

**Create:** `src/edison/core/adapters/sync/zen.py`

**Delete:**

- `src/edison/core/adapters/sync/zen/discovery.py`
- `src/edison/core/adapters/sync/zen/composer.py`
- `src/edison/core/adapters/sync/zen/sync.py`
- `src/edison/core/adapters/sync/zen/client.py`
- `src/edison/core/adapters/sync/zen/__init__.py`

### 4.9 Consolidate PromptAdapter Base Classes

**Modify:** `src/edison/core/adapters/base.py` - Enhanced with template methods

**Delete:** `src/edison/core/adapters/prompt/base.py` - Consolidate into adapters/base.py

### 4.10 Fix CodexAdapter to Use ConfigMixin

**File:** `src/edison/core/adapters/prompt/codex.py`

Remove duplicate `_load_config()`, extend `ConfigMixin`.

### 4.11 Update Sync Adapters to Use ConfigMixin

**Files:**

- `src/edison/core/adapters/sync/claude.py`
- `src/edison/core/adapters/sync/cursor.py`

### 4.12 Update All Registries to Use Unified Errors

**Files:**

- `src/edison/core/composition/registries/agents.py`
- `src/edison/core/composition/registries/validators.py`
- `src/edison/core/composition/registries/rules.py`
- `src/edison/core/composition/registries/documents.py`
- `src/edison/core/composition/registries/constitutions.py`

### 4.13 Verification

- GuidelineRegistry uses LayeredComposer
- FilePatternRegistry uses CompositionPathResolver
- IDE composers use `_load_layered_config()` (30 lines → 2 lines each)
- ZenSync consolidated (5 files → 1)
- PromptAdapter consolidated (2 files → 1)
- ~200+ lines duplication eliminated
- All tests pass

---

## Files Summary

### Files to CREATE (17)

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
src/edison/core/composition/core/errors.py
src/edison/core/composition/core/metadata.py
src/edison/core/composition/output/writer.py
src/edison/core/composition/output/resolver.py
src/edison/core/composition/registries/config_based.py
src/edison/core/composition/analysis/dry.py
src/edison/core/adapters/sync/zen.py
```

### Files to MODIFY (25+)

```
src/edison/core/composition/core/sections.py
src/edison/core/entity/registry.py
src/edison/core/composition/ide/base.py
src/edison/core/composition/ide/hooks.py
src/edison/core/composition/ide/commands.py
src/edison/core/composition/ide/settings.py
src/edison/core/composition/ide/coderabbit.py
src/edison/core/composition/registries/*.py (7 files)
src/edison/core/adapters/base.py
src/edison/core/adapters/sync/base.py
src/edison/core/adapters/sync/claude.py
src/edison/core/adapters/sync/cursor.py
src/edison/core/adapters/prompt/codex.py
src/edison/cli/compose/all.py
src/edison/data/**/*.md (all templates)
```

### Files to DELETE (6)

```
src/edison/core/adapters/sync/zen/discovery.py
src/edison/core/adapters/sync/zen/composer.py
src/edison/core/adapters/sync/zen/sync.py
src/edison/core/adapters/sync/zen/client.py
src/edison/core/adapters/sync/zen/__init__.py
src/edison/core/adapters/prompt/base.py
```

---

## Success Criteria

1. Single `TemplateEngine` handles ALL template processing (9-step pipeline)
2. 4-concept section system replaces 12+ markers
3. Two-phase composition ensures cross-file references get fully composed content
4. `CompositionBase` eliminates ~90 lines of duplication
5. `CompositionFileWriter` centralizes all file I/O (18 write points)
6. `OutputPathResolver` single source of truth for paths
7. Unified error hierarchy with `CompositionError` base class
8. `MetadataExtractor` unified frontmatter parsing
9. ~200+ lines total duplication eliminated
10. All tests pass (unit, integration, e2e)
11. `edison compose all` produces fully processed output