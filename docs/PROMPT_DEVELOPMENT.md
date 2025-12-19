# Edison Prompt Development Guide

This document defines the critical principles, patterns, and rules for developing agents, validators, orchestrators, constitutions, guidelines, and packs in the Edison framework. These principles ensure context-efficiency, maintainability, and fail-safe composition.

---

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [Architecture Overview](#2-architecture-overview)
3. [File Organization](#3-file-organization)
4. [Templating System Usage](#4-templating-system-usage)
5. [Role-Specific Content Allocation](#5-role-specific-content-allocation)
6. [Constitution Design](#6-constitution-design)
7. [Agent Prompt Design](#7-agent-prompt-design)
8. [Validator Prompt Design](#8-validator-prompt-design)
9. [Pack Development](#9-pack-development)
10. [Guidelines Structure](#10-guidelines-structure)
11. [Anti-Patterns to Avoid](#11-anti-patterns-to-avoid)
12. [Quality Checklist](#12-quality-checklist)

---

## 1. Core Principles

### 1.1 Single Source of Truth (CANONICAL)

Every rule, guideline, or instruction exists in exactly ONE canonical source file. All other files reference or include from that source.

**Rule**: If you need to change a rule, you change it in ONE place, and it propagates everywhere via the composition system.

```
GOOD:
- TDD principles defined in: guidelines/includes/TDD.md
- All agents/validators/orchestrators include relevant sections

BAD:
- TDD principles copied into 15 different files
- Each copy slightly different
- Changes require updating all 15 files
```

### 1.2 No Double-Loading

Content appears in context exactly ONCE. Never include content that is also listed as a mandatory read.

```
ANTI-PATTERN (FORBIDDEN):
---
mandatoryReads:
  - shared/TDD.md
---

## TDD Protocol
{{include:shared/TDD.md}}  # <-- DOUBLE-LOADED!
```

```
CORRECT:
# Either embed via include (recommended):
{{include-section:guidelines/includes/TDD.md#agent-execution}}

# OR reference for on-demand reading (not both):
See: `guidelines/shared/TDD.md` for extended patterns.
```

### 1.3 Role-Specific Loading

Each role (agent/validator/orchestrator) loads ONLY content relevant to their function:

- **Agents**: HOW to implement (TDD execution, code patterns)
- **Validators**: HOW to verify (compliance checks, what to flag)
- **Orchestrators**: HOW to coordinate (delegation, verification, wave orchestration)

**Rule**: Content for other roles MUST NOT be loaded.

### 1.4 Technology-Agnostic Core

Core agents/validators contain ZERO technology-specific content. All technology patterns come from packs via the EXTEND mechanism.

```
GOOD (Core agent):
## Tools
<!-- SECTION: tools -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tools -->

GOOD (Pack overlay):
<!-- EXTEND: tools -->
### Python Testing (pytest)
pytest tests/ -v
<!-- /EXTEND -->
```

```
BAD (Core agent with technology content):
## Testing Tools
- pytest tests/ -v          # <-- Python-specific!
- npm test                   # <-- Node-specific!
```

### 1.5 Includes Folder Pattern

Files that exist ONLY for `{{include-section:...}}` live in `guidelines/includes/`. These are NEVER read directly by LLMs.

```
guidelines/
├── includes/            # NEVER read directly (section-only)
│   ├── TDD.md          # Has sections: principles, agent-execution, validator-check, orchestrator-verify
│   ├── NO_MOCKS.md     # Has sections: philosophy, agent-impl, validator-flags
│   └── ...
├── shared/              # Can be read directly (optional deep-dives)
└── agents/              # Role-specific files
```

### 1.6 Constitution Embedding

Constitutions are EMBEDDED in agent/validator prompts via `{{include:}}`. This ensures:

- Single re-read target: "Re-read your agent file on compact" = everything
- No risk of forgetting constitution
- Automatic propagation of constitution changes

```
# agents/test-engineer.md
{{include:constitutions/agents.md}}

## Test Engineer Role
[Agent-specific content]
```

### 1.7 Dynamic Content via Functions

NEVER hardcode dynamic content (state machine states, rosters, versions). Use template functions.

```
GOOD:
Valid task states: {{fn:task_states}}

BAD:
Valid task states: todo, wip, done, validated  # <-- Hardcoded!
```

---

## 2. Architecture Overview

### 2.1 Composition Layer Order

Content is composed in strict order: **core → packs → project** (later wins).

```
Layer Priority:
1. Core (edison/data/*)           # Default/baseline
2. Packs (packs/{pack}/*)         # Technology-specific
3. Project (.edison/*)            # Project-specific overrides
```

### 2.2 Content Types

| Type | Merge Strategy | Overlays |
|------|----------------|----------|
| Agents | Section merge | Yes (`overlays/`) |
| Validators | Section merge | Yes (`overlays/`) |
| Guidelines | Concat + dedupe | No (merge_same_name) |
| Constitutions | Section merge | Yes |
| Rosters | Template | N/A |

### 2.3 Templating Pipeline Order

Templates are processed in this strict order:

1. **Section/EXTEND merge** (MarkdownCompositionStrategy)
2. **Includes** (`{{include:}}`, `{{include-section:}}`)
3. **Variables** (`{{config.key}}`, `{{PROJECT_ROOT}}`)
4. **Conditionals** (`{{if:condition}}`)
5. **Loops** (`{{#each collection}}`)
6. **References** (`{{reference-section:}}`)
7. **Functions** (`{{fn:name args}}`)

---

## 3. File Organization

### 3.1 Directory Structure

```
data/
├── agents/                          # Core agent prompts
│   ├── test-engineer.md            # Technology-agnostic
│   ├── feature-implementer.md
│   └── ...
│
├── validators/                      # Core validator prompts
│   ├── global.md                   # Technology-agnostic
│   ├── critical/security.md
│   └── ...
│
├── constitutions/                   # Role constitutions (include-only)
│   ├── agents.md                   # Embedded in all agents
│   ├── validators.md               # Embedded in all validators
│   └── orchestrator.md             # Embedded in orchestrator
│
├── guidelines/
│   ├── includes/                    # NEVER read directly
│   │   ├── TDD.md                  # Role sections
│   │   ├── NO_MOCKS.md
│   │   └── ...
│   ├── agents/                      # Agent-readable
│   │   ├── MANDATORY_WORKFLOW.md
│   │   └── OUTPUT_FORMAT.md
│   ├── validators/                  # Validator-readable
│   │   └── VALIDATOR_WORKFLOW.md
│   ├── orchestrators/               # Orchestrator-readable
│   │   └── SESSION_WORKFLOW.md
│   └── shared/                      # Optional deep-dives (all roles)
│       ├── QUALITY_PATTERNS.md
│       └── GIT_WORKFLOW.md
│
├── packs/
│   └── {pack}/
│       ├── agents/overlays/         # EXTEND core agents
│       ├── validators/overlays/     # EXTEND core validators
│       └── guidelines/              # Pack-specific guidelines
│
└── functions/                       # Template functions
    ├── state_machine.py
    └── tasks_states.py
```

### 3.2 Naming Conventions

| File Type | Convention | Example |
|-----------|------------|---------|
| Agent | `kebab-case.md` | `test-engineer.md` |
| Validator | `kebab-case.md` | `global.md`, `security.md` |
| Guideline | `SCREAMING_SNAKE.md` | `TDD.md`, `NO_MOCKS.md` |
| Constitution | `role.md` | `agents.md` |
| Pack overlay | Same as target | `overlays/test-engineer.md` |

---

## 4. Templating System Usage

### 4.1 Includes

**Full file include** (rarely needed):
```
{{include:path/to/file.md}}
```

**Section include** (preferred):
```
{{include-section:guidelines/includes/TDD.md#agent-execution}}
```

**Resolution order**: project → packs → core

### 4.2 Sections

Define named sections that can be included or extended:

```markdown
<!-- SECTION: principles -->
## TDD Principles
- RED: Write failing test first
- GREEN: Minimal implementation
- REFACTOR: Clean up
<!-- /SECTION: principles -->

<!-- SECTION: agent-execution -->
## TDD Execution (Agents)
[Agent-specific TDD execution details]
<!-- /SECTION: agent-execution -->
```

### 4.3 Extend (Pack Overlays)

Packs use EXTEND to inject content into core sections:

```markdown
<!-- EXTEND: tools -->
### Python Testing (pytest)
pytest tests/ -v --tb=short
<!-- /EXTEND -->
```

**Rule**: Pack overlays should ONLY use EXTEND, never redefine entire sections.

### 4.4 Conditionals

Available condition functions:
- `has-pack(name)` - Check if pack is active
- `config(path)` - Check config value is truthy
- `config-eq(path,value)` - Check config value equals
- `file-exists(path)` - Check file exists
- `not(expr)`, `and(a,b)`, `or(a,b)` - Logical operators

```markdown
{{if:has-pack(python)}}
### Python-Specific
{{include-section:packs/python/guidelines/TESTING.md#pytest}}
{{/if}}
```

**IMPORTANT**: Avoid pack conditionals in core files. Prefer pack overlays with EXTEND.

### 4.5 Loops

For dynamic rosters and lists:

```markdown
{{#each agents}}
| {{this.name}} | {{this.model}} |
{{/each}}
```

### 4.6 Functions

Define in `functions/` directory:

```python
# functions/state_machine.py
def task_states() -> str:
    """Return task states from config."""
    # Load from state-machine.yaml, not hardcoded
    return ", ".join(["todo", "wip", "done", "validated"])
```

Usage:
```markdown
Valid states: {{fn:task_states}}
```

### 4.7 Variables

Built-in variables:
- `{{PROJECT_ROOT}}` - Project root path
- `{{REPO_ROOT}}` - Repository root
- `{{timestamp}}` - Generation timestamp
- `{{config.path.to.value}}` - Config access

---

## 5. Role-Specific Content Allocation

### 5.1 Content Matrix

| Content | Agent | Validator | Orchestrator |
|---------|:-----:|:---------:|:------------:|
| TDD Principles | X | X | X |
| TDD Execution (how to DO TDD) | X | | |
| TDD Compliance (how to CHECK TDD) | | X | |
| TDD Verification (how to VERIFY) | | | X |
| NO MOCKS Philosophy | X | X | |
| NO MOCKS Implementation | X | | |
| NO MOCKS Validation Flags | | X | |
| Context7 Workflow | X | X | X |
| Context7 Evidence Creation | X | | |
| Context7 Evidence Validation | | X | |
| Claim-Implement-Ready | X | | |
| Validation Waves | | | X |
| Verdict Rules | | X | |
| Delegation Rules | | | X |
| Session Management | | | X |

### 5.2 Includes File Section Pattern

Each includes file MUST have role-specific sections:

```markdown
# guidelines/includes/TDD.md

<!-- SECTION: principles -->
## TDD Principles (All Roles)
[Universal TDD principles]
<!-- /SECTION: principles -->

<!-- SECTION: agent-execution -->
## TDD Execution (Agents Only)
[How agents execute TDD]
<!-- /SECTION: agent-execution -->

<!-- SECTION: validator-check -->
## TDD Compliance (Validators Only)
[How validators check TDD compliance]
<!-- /SECTION: validator-check -->

<!-- SECTION: orchestrator-verify -->
## TDD Verification (Orchestrators Only)
[How orchestrators verify TDD was followed]
<!-- /SECTION: orchestrator-verify -->
```

---

## 6. Constitution Design

### 6.1 Constitution Purpose

Constitutions contain:
- Role definition (who you are)
- Critical rules (MUST follow)
- Core workflows (how to operate)
- Quality standards (what to ensure)

### 6.2 Constitution Template

```markdown
# {Role} Constitution

**Re-read this file (your prompt) on every compact and task start.**

## Role Definition
You are a {ROLE} in Edison. You {primary responsibility}.

## Core Principles (CRITICAL)
{{include-section:guidelines/includes/TDD.md#principles}}
{{include-section:guidelines/includes/NO_MOCKS.md#philosophy}}
{{include-section:guidelines/includes/QUALITY.md#principles}}

## {Role}-Specific Workflow
{{include-section:guidelines/includes/TDD.md#{role}-section}}

## Context7 Knowledge Refresh
{{include-section:guidelines/includes/CONTEXT7.md#workflow}}
{{include-section:guidelines/includes/CONTEXT7.md#{role}-section}}

## Mandatory Workflow
{{include-section:guidelines/{role}s/MANDATORY_WORKFLOW.md#workflow}}

## Output Format
See: `guidelines/{role}s/OUTPUT_FORMAT.md`

## Optional Deep-Dive References
- `guidelines/shared/QUALITY_PATTERNS.md` - Extended examples
- `guidelines/shared/GIT_WORKFLOW.md` - Git conventions
```

### 6.3 Constitution Rules

1. **No technology content** - Constitution is technology-agnostic
2. **Include, don't copy** - Use `{{include-section:}}` for all shared content
3. **Role-appropriate sections only** - Only include sections for this role
4. **Single re-read instruction** - "Re-read this file" covers everything
5. **Optional reads at bottom** - Deep-dives as references, not mandatory

---

## 7. Agent Prompt Design

### 7.1 Agent Template

```markdown
---
name: {agent-name}
description: "{Brief description}"
model: {model}
---

# {Agent Name}

## Constitution (Re-read on compact)
{{include:constitutions/agents.md}}

## Role
[2-3 bullet points defining this agent's specialty]

## Tools
<!-- SECTION: tools -->
<!-- Base tools - pack overlays extend here -->
<!-- /SECTION: tools -->

## Guidelines
<!-- SECTION: guidelines -->
<!-- Base guidelines - pack overlays extend here -->
<!-- /SECTION: guidelines -->

## {Agent}-Specific Workflow
[Workflow specific to this agent type]

## Constraints
[Agent-specific constraints and boundaries]
```

### 7.2 Agent Rules

1. **Constitution embedded** - First content is `{{include:constitutions/agents.md}}`
2. **No generic content** - TDD, NO MOCKS, etc. come from constitution
3. **No technology content** - Packs inject via EXTEND
4. **SECTION placeholders** - Empty sections for pack extension
5. **Role-specific only** - Only content unique to this agent type

---

## 8. Validator Prompt Design

### 8.1 Validator Template

```markdown
# {Validator Name}

## Constitution (Re-read on compact)
{{include:constitutions/validators.md}}

## Mission
[What this validator checks]

## Scope
**Triggers**: `{file patterns}`
**Blocks**: {YES/NO}

## Checklist
<!-- SECTION: checklist -->
[Validation checklist items]
<!-- /SECTION: checklist -->

## Tech Stack Checks
<!-- SECTION: tech-checks -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tech-checks -->
```

### 8.2 Validator Rules

1. **Constitution embedded** - Always include validators.md
2. **Clear triggers** - File patterns that activate this validator
3. **Blocking status** - Whether failures block merge
4. **Generic checklist** - Technology-agnostic checks
5. **Tech section for packs** - Empty section for pack-specific checks

---

## 9. Pack Development

### 9.1 Pack Structure

```
packs/{pack}/
├── pack.yaml              # Pack metadata
├── agents/
│   └── overlays/          # EXTEND core agents
│       └── test-engineer.md
├── validators/
│   └── overlays/          # EXTEND core validators
│       └── global.md
├── guidelines/
│   ├── {pack}/            # Pack-specific guidelines (agent-readable references)
│   └── includes/{pack}/   # Pack include-only sources (for {{include-section:...}})
│       └── TESTING.md
└── functions/             # Pack-specific functions
    └── {pack}_helpers.py
```

### 9.2 Pack Overlay Pattern

```markdown
---
name: test-engineer
pack: {pack}
overlay_type: extend
---

<!-- EXTEND: tools -->
### {Pack} Testing
{pack-specific commands}
<!-- /EXTEND -->

<!-- EXTEND: guidelines -->
### {Pack} Patterns
{{include-section:packs/{pack}/guidelines/includes/{pack}/TESTING.md#patterns}}
<!-- /EXTEND -->
```

### 9.3 Pack Rules

1. **EXTEND only** - Never redefine, only extend sections
2. **No generic content** - No TDD/NO_MOCKS explanations
3. **Technology-specific only** - Commands, syntax, patterns for this tech
4. **Section markers** - Guidelines use SECTION for overlay references
5. **Include from pack guidelines** - Complex patterns in pack guidelines, included in overlays

### 9.4 What Goes in Packs vs Core

| Content Type | Core | Pack |
|--------------|:----:|:----:|
| TDD philosophy | X | |
| pytest commands | | X |
| NO MOCKS rule | X | |
| vi.mock patterns | | X |
| Test isolation concept | X | |
| tmp_path usage | | X |
| Type safety principles | X | |
| mypy configuration | | X |

---

## 10. Guidelines Structure

### 10.1 Includes Guidelines

Files in `guidelines/includes/` are section-only sources:

```markdown
# guidelines/includes/{TOPIC}.md

<!-- SECTION: principles -->
## {Topic} Principles (All Roles)
[Universal principles]
<!-- /SECTION: principles -->

<!-- SECTION: agent-{action} -->
## {Topic} for Agents
[Agent-specific guidance]
<!-- /SECTION: agent-{action} -->

<!-- SECTION: validator-{action} -->
## {Topic} for Validators
[Validator-specific checks]
<!-- /SECTION: validator-{action} -->

<!-- SECTION: orchestrator-{action} -->
## {Topic} for Orchestrators
[Orchestrator-specific verification]
<!-- /SECTION: orchestrator-{action} -->
```

### 10.2 Shared Guidelines

Files in `guidelines/shared/` are optional deep-dives:

- **Purpose**: Extended examples, patterns, reference material
- **Loading**: On-demand (not mandatory reads)
- **Content**: Detailed patterns too long for constitution embedding

### 10.3 Role-Specific Guidelines

Files in `guidelines/{role}s/`:

- **Purpose**: Role-specific workflows and formats
- **Loading**: Referenced from constitution
- **Content**: MANDATORY_WORKFLOW, OUTPUT_FORMAT, etc.

---

## 11. Anti-Patterns to Avoid

### 11.1 Double-Loading (CRITICAL)

```markdown
# FORBIDDEN
mandatoryReads:
  - shared/TDD.md

## TDD
{{include:shared/TDD.md}}
```

### 11.2 Technology in Core

```markdown
# FORBIDDEN (in core agent)
## Testing
- Run `pytest tests/` for Python    # <-- Technology-specific!
- Run `pnpm test` for JavaScript    # <-- Technology-specific!
```

### 11.3 Hardcoded Dynamic Content

```markdown
# FORBIDDEN
Valid states: todo, wip, done, validated   # <-- Hardcoded!

# CORRECT
Valid states: {{fn:task_states}}
```

### 11.4 Pack Conditionals in Core

```markdown
# AVOID in core files
{{if:has-pack(python)}}
## Python Testing
...
{{/if}}

# PREFER: Let packs EXTEND sections instead
```

### 11.5 Generic Content in Packs

```markdown
# FORBIDDEN (in pack guideline)
## TDD Principles
- RED: Write failing test first    # <-- Generic, belongs in core!
- GREEN: Implement
- REFACTOR: Clean up

# CORRECT
## pytest-Specific Patterns
- Use `@pytest.mark.parametrize`   # <-- Technology-specific
- Use `tmp_path` fixture           # <-- Technology-specific
```

### 11.6 Copying Instead of Including

```markdown
# FORBIDDEN
## NO MOCKS Policy
[50 lines copied from guidelines/includes/NO_MOCKS.md]

# CORRECT
{{include-section:guidelines/includes/NO_MOCKS.md#philosophy}}
```

### 11.7 Wrong-Role Content

```markdown
# FORBIDDEN (in agent prompt)
## Validator Wave Orchestration    # <-- Orchestrator-only!
[Details about how to run validation waves]

# FORBIDDEN (in validator prompt)
## Claim-Implement-Ready Workflow  # <-- Agent-only!
```

### 11.8 Constitution/Prompt Separation

```markdown
# OLD PATTERN (AVOID)
# Constitution is separate file
# Agent told to "re-read constitution AND agent file"

# NEW PATTERN (CORRECT)
# Constitution embedded in agent file
{{include:constitutions/agents.md}}
# Single instruction: "re-read your agent file"
```

---

## 12. Quality Checklist

### 12.1 Before Creating/Modifying Any Prompt

- [ ] Is this content technology-agnostic (for core) or technology-specific (for pack)?
- [ ] Does this content already exist in a canonical source?
- [ ] Am I including the correct role-specific section?
- [ ] Have I avoided double-loading?
- [ ] Are SECTION markers present for pack extension?

### 12.2 For Agent Prompts

- [ ] Constitution is embedded via `{{include:constitutions/agents.md}}`
- [ ] No generic TDD/NO_MOCKS content (in constitution)
- [ ] No technology-specific content (in pack overlays)
- [ ] SECTION: tools placeholder exists
- [ ] SECTION: guidelines placeholder exists
- [ ] Only agent-specific workflow/constraints remain

### 12.3 For Validator Prompts

- [ ] Constitution is embedded via `{{include:constitutions/validators.md}}`
- [ ] Clear triggers defined
- [ ] Blocking status specified
- [ ] SECTION: checklist defined
- [ ] SECTION: tech-checks placeholder for packs

### 12.4 For Pack Overlays

- [ ] Only uses EXTEND (no section redefinition)
- [ ] No generic principles (those are in core)
- [ ] Only technology-specific commands/patterns
- [ ] Includes from pack guidelines where appropriate

### 12.5 For Guidelines

- [ ] Includes files have all role sections
- [ ] Shared files are truly shared (all roles benefit)
- [ ] No duplicated content across files
- [ ] Sections are properly marked

### 12.6 For Constitution Changes

- [ ] Change propagates to all agents/validators automatically
- [ ] No mandatory reads for embedded content
- [ ] Optional reads at bottom for deep-dives
- [ ] Single re-read instruction works

### 12.7 Final Validation

After composition, verify:
- [ ] `edison compose all` succeeds
- [ ] No broken includes/sections
- [ ] Context sizes reduced (not increased)
- [ ] No duplicate content in composed output
- [ ] Each role loads only their content

---

## Summary: The Golden Rules

1. **One Truth**: Every rule lives in ONE canonical file
2. **Never Double**: Content is either included OR referenced, never both
3. **Role-Specific**: Load ONLY content relevant to the role
4. **Core is Generic**: Zero technology content in core
5. **Packs Extend**: Packs use EXTEND, never redefine
6. **Constitution Embedded**: Constitution inside prompts, not separate
7. **Functions for Dynamic**: No hardcoded states/rosters/versions
8. **Includes are Private**: `guidelines/includes/` files are never read directly
9. **Single Re-Read**: "Re-read your file" gives everything
10. **Compose to Verify**: Always run `edison compose all` to validate

---

_This document is the canonical source for Edison prompt development principles._
_Last updated: 2025-12-04_
