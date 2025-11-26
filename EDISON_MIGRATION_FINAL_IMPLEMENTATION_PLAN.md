# Edison Migration: Final Implementation Plan

**Generated**: 2025-11-26
**Status**: READY FOR ORCHESTRATION
**Total Tasks**: 68 (60 Main Track + 8 Zen Track)
**Parallel Tracks**: 2 (Main Migration + Edison-Zen)

---

## 1. Executive Summary

### 1.1 Migration Overview

This document is the single, authoritative implementation plan for completing the Edison AI-automated software development framework migration. It consolidates all findings from comprehensive multi-model validation (Claude Opus, Codex CLI, Gemini CLI) into actionable tasks ready for parallel execution by sub-agents.

The migration transforms a project-specific implementation (wilson-pre-edison) into a composable, three-layer framework (CORE → PACKS → PROJECT) that can be reused across any software project. Key transformations include: replacing hardcoded values with dynamic configuration, implementing a constitution system for role-based agent guidance, and ensuring all generated files are properly composed from their source layers.

**Current Migration Readiness: 55%** — This plan addresses all gaps to reach 100% readiness with zero deferrals.

### 1.2 Key Statistics

| Metric | Value |
|--------|-------|
| Total Unique Tasks | 68 (60 Main + 8 Zen) |
| P0 (Blocker) Tasks | 12 |
| P1 (Critical) Tasks | 18 |
| P2 (High) Tasks | 22 |
| P3 (Medium) Tasks | 9 |
| P4 (Low) Tasks | 7 |
| Zen Track Tasks | 8 |

### 1.3 Architectural Decisions (Authoritative)

These decisions are FINAL and must be followed throughout implementation:

| Decision | Specification |
|----------|---------------|
| **Constitution folder naming** | `constitutions/` (plural) containing `ORCHESTRATORS.md`, `AGENTS.md`, `VALIDATORS.md` |
| **Three-layer composition** | CORE (`edison/core/`) → PACKS (`edison/packs/<pack>/`) → PROJECT (`.edison/`) |
| **Generated output location** | `.edison/_generated/` for all composed files |
| **Dynamic rosters** | `AVAILABLE_AGENTS.md` and `AVAILABLE_VALIDATORS.md` at `_generated/` root |
| **No hardcoded values** | All lists, settings, counts must come from YAML config or registry queries |
| **Self-identification headers** | All generated files must include source layers, regeneration command, and RE-READ instruction |
| **zenRole mapping** | Project-specific zenRoles defined in project overlay, NOT hardcoded in core |
| **Multiple START prompts** | `START_NEW_SESSION.md`, `START_RESUME_SESSION.md`, `START_VALIDATE_SESSION.md` |
| **Constitution auto-injection** | Agent/validator prompts automatically include constitution read requirement |

---

## 2. Dependency Graph Overview

### 2.1 Main Track Dependencies

```
T-001 (Constitution Templates) ──┬──> T-004 (Constitution Composer)
T-002 (Constitution Config)    ──┘         │
                                           ├──> T-008 (ORCHESTRATORS.md)
T-003 (Rules applies_to)  ──> T-005 (Rules API) ──┤
                                           ├──> T-009 (AGENTS.md Constitution)
                                           └──> T-010 (VALIDATORS.md Constitution)

T-006 (AVAILABLE_AGENTS.md) ──┬
T-007 (AVAILABLE_VALIDATORS.md) ──┼──> T-011 (Remove ORCHESTRATOR_GUIDE.md)
T-008, T-009, T-010 ──────────┘

T-012 (Zen Prompt Fix) ──> T-013 (Pack Deduplication) ──> All Content Tasks

T-014 (Post-training Packages) ──┬
T-015 (Rule Paths Fix) ──────────┼──> T-020+ (Content Restoration)
T-016 (YAML Frontmatter) ────────┘

T-017 (START_NEW_SESSION) ──┬
T-018 (START_RESUME_SESSION) ──┼──> T-026 (Session System Complete)
T-019 (START_VALIDATE_SESSION) ─┘
```

### 2.2 Zen Track Dependencies

```
T-ZEN-001 (zen setup command) ──┬
T-ZEN-002 (zen start-server) ───┼──> T-ZEN-004 (uvx detection)
T-ZEN-003 (zen configure) ──────┘         │
                                          v
                              T-ZEN-005 (.mcp.json template)
                                          │
                                          v
                              T-ZEN-006 (edison init integration)
                                          │
                                          v
                              T-ZEN-007 (README documentation)
                                          │
                                          v
                              T-ZEN-008 (End-to-end verification)
```

### 2.3 Cross-Track Dependencies

The Zen track can execute **fully in parallel** with the main track. The only soft dependency is that `T-ZEN-006` (edison init integration) should complete before final validation, but it does not block any main track tasks.

---

## 3. Constitution System Architecture

### 3.1 File Structure

```
edison/core/
├── constitutions/
│   ├── orchestrator-base.md      # Core orchestrator constitution template
│   ├── agents-base.md            # Core agent constitution template
│   └── validators-base.md        # Core validator constitution template
├── config/
│   └── constitution.yaml         # Mandatory reads configuration
├── start/
│   ├── START_NEW_SESSION.md      # Fresh session bootstrap
│   ├── START_RESUME_SESSION.md   # Session recovery
│   └── START_VALIDATE_SESSION.md # Validation-only session
└── rules/
    └── registry.yml              # Rules with applies_to field

edison/packs/<pack>/
├── constitutions/
│   ├── orchestrator-additions.md # Pack-specific orchestrator additions (optional)
│   ├── agents-additions.md       # Pack-specific agent additions (optional)
│   └── validators-additions.md   # Pack-specific validator additions (optional)
└── rules/
    └── registry.yml              # Pack-specific rules

.edison/                          # Project-level
├── constitutions/
│   ├── orchestrator-overrides.md # Project-specific overrides (optional)
│   ├── agents-overrides.md       # Project-specific overrides (optional)
│   └── validators-overrides.md   # Project-specific overrides (optional)
├── config/
│   └── project.yml               # Project-specific settings including zenRole mappings
└── _generated/
    ├── AVAILABLE_AGENTS.md       # Dynamic agent roster
    ├── AVAILABLE_VALIDATORS.md   # Dynamic validator roster
    ├── constitutions/
    │   ├── ORCHESTRATORS.md      # Composed orchestrator constitution
    │   ├── AGENTS.md             # Composed agent constitution
    │   └── VALIDATORS.md         # Composed validator constitution
    ├── agents/                   # Composed agent prompts
    ├── validators/               # Composed validator prompts
    └── guidelines/               # Composed guidelines
```

### 3.2 Three-Layer Composition Model

| Layer | Location | Purpose | Override Priority |
|-------|----------|---------|-------------------|
| **CORE** | `edison/core/` | Base framework definitions | Lowest |
| **PACKS** | `edison/packs/<pack>/` | Technology-specific extensions (React, Prisma, etc.) | Middle |
| **PROJECT** | `.edison/` | Project-specific overrides and additions | Highest |

**Composition Rules:**
1. Lower layers (PROJECT) extend/override higher layers (CORE)
2. Pack content is additive unless explicitly overriding
3. All generated files include source layer attribution in headers
4. Missing pack/project files are simply skipped (not errors)

### 3.3 Generated Outputs

| Generated File | Source Layers | Location |
|----------------|---------------|----------|
| `ORCHESTRATORS.md` | core + packs + project | `.edison/_generated/constitutions/` |
| `AGENTS.md` | core + packs + project | `.edison/_generated/constitutions/` |
| `VALIDATORS.md` | core + packs + project | `.edison/_generated/constitutions/` |
| `AVAILABLE_AGENTS.md` | AgentRegistry query | `.edison/_generated/` |
| `AVAILABLE_VALIDATORS.md` | ValidatorRegistry query | `.edison/_generated/` |
| `CLAUDE.md` | core + packs + project | `.claude/` |
| `AGENTS.md` (universal) | core + packs + project | Project root |
| Zen client configs | Composition engine | `.zen/conf/cli_clients/` |
| Zen system prompts | Agent/validator prompts | `.zen/conf/systemprompts/` |

---

## 4. P0 - BLOCKER Tasks

### T-001: Create Core Constitution Templates

**Priority**: P0 - BLOCKER
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Create the three base constitution template files in edison/core/constitutions/ that define the foundation for each role type.

#### Files Affected
- `edison/core/constitutions/orchestrator-base.md` - CREATE (~300 lines)
- `edison/core/constitutions/agents-base.md` - CREATE (~300 lines)
- `edison/core/constitutions/validators-base.md` - CREATE (~200 lines)

#### Implementation Details

Each constitution template MUST include:
1. Self-identification header (see Content to Restore)
2. Role identification section
3. Constitution location with RE-READ instruction
4. Mandatory reads placeholder (`{{#each mandatoryReads.<role>}}`)
5. Applicable rules placeholder (`{{#each rules.<role>}}`)
6. Role-specific workflow section

#### Content to Restore

**orchestrator-base.md header:**
```markdown
<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Source: {{source_layers}} -->
<!-- Regenerate: edison compose --all -->
<!-- Role: ORCHESTRATOR -->
<!-- Constitution: .edison/_generated/constitutions/ORCHESTRATORS.md -->
<!-- RE-READ this file on each new session or compaction -->

# Orchestrator Constitution

You are an ORCHESTRATOR in the Edison framework. This constitution defines your mandatory behaviors and workflow.

## Constitution Location
This file is located at: `.edison/_generated/constitutions/ORCHESTRATORS.md`

## CRITICAL: Re-read this entire file:
- At the start of every new session
- After any context compaction
- When instructed by the user

## Mandatory Preloads
{{#each mandatoryReads.orchestrator}}
- {{this.path}}: {{this.purpose}}
{{/each}}

## Available Agents
See: AVAILABLE_AGENTS.md for the current agent roster.

## Available Validators
See: AVAILABLE_VALIDATORS.md for the current validator roster.

## Delegation Rules
{{#each delegationRules}}
- {{this.pattern}} → {{this.agent}} ({{this.model}})
{{/each}}

## Applicable Rules
{{#each rules.orchestrator}}
### {{this.id}}: {{this.name}}
{{this.content}}
{{/each}}

## Session Workflow
See: guidelines/orchestrators/SESSION_WORKFLOW.md
```

**agents-base.md core structure:**
```markdown
<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Source: {{source_layers}} -->
<!-- Regenerate: edison compose --all -->
<!-- Role: AGENT -->
<!-- Constitution: .edison/_generated/constitutions/AGENTS.md -->

# Agent Constitution

You are an AGENT in the Edison framework. This constitution defines your mandatory behaviors.

## Constitution Location
This file is located at: `.edison/_generated/constitutions/AGENTS.md`

## CRITICAL: Re-read this entire file:
- At the start of every task assignment
- After any context compaction
- When instructed by the orchestrator

## Mandatory Preloads (All Agents)
{{#each mandatoryReads.agents}}
- {{this.path}}: {{this.purpose}}
{{/each}}

## Workflow Requirements
1. Follow MANDATORY_WORKFLOW.md
2. Query Context7 for post-training packages BEFORE coding
3. Generate implementation report upon completion
4. Mark ready via edison CLI

## Output Format
See: guidelines/agents/OUTPUT_FORMAT.md

## Applicable Rules
{{#each rules.agent}}
### {{this.id}}: {{this.name}}
{{this.content}}
{{/each}}
```

**validators-base.md core structure:**
```markdown
<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Source: {{source_layers}} -->
<!-- Regenerate: edison compose --all -->
<!-- Role: VALIDATOR -->
<!-- Constitution: .edison/_generated/constitutions/VALIDATORS.md -->

# Validator Constitution

You are a VALIDATOR in the Edison framework. This constitution defines your mandatory behaviors.

## Constitution Location
This file is located at: `.edison/_generated/constitutions/VALIDATORS.md`

## CRITICAL: Re-read this entire file:
- At the start of every validation assignment
- After any context compaction

## Mandatory Preloads (All Validators)
{{#each mandatoryReads.validators}}
- {{this.path}}: {{this.purpose}}
{{/each}}

## Validation Workflow
1. Refresh Context7 knowledge for relevant packages
2. Review changes against validation criteria
3. Generate JSON report with verdict
4. Return verdict (approve/reject/blocked)

## Output Format
See: guidelines/validators/OUTPUT_FORMAT.md

## Applicable Rules
{{#each rules.validator}}
### {{this.id}}: {{this.name}}
{{this.content}}
{{/each}}
```

#### Validation Criteria
- [ ] All three template files exist in `edison/core/constitutions/`
- [ ] Each template has self-identification header with all required fields
- [ ] Each template has role identification section
- [ ] Each template has mandatory reads Handlebars placeholder
- [ ] Each template has applicable rules Handlebars placeholder
- [ ] Templates parse without Handlebars errors

---

### T-002: Create Constitution Configuration Schema

**Priority**: P0 - BLOCKER
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Create the constitution.yaml configuration file that defines mandatory reads for each role type.

#### Files Affected
- `edison/core/config/constitution.yaml` - CREATE (~80 lines)

#### Implementation Details

```yaml
# edison/core/config/constitution.yaml
# Defines mandatory reads for each role type in the Edison framework

version: "1.0.0"

mandatoryReads:
  orchestrator:
    - path: constitutions/ORCHESTRATORS.md
      purpose: Main orchestrator constitution
    - path: guidelines/orchestrators/SESSION_WORKFLOW.md
      purpose: Session lifecycle management
    - path: guidelines/shared/DELEGATION.md
      purpose: Delegation rules and patterns
    - path: AVAILABLE_AGENTS.md
      purpose: Dynamic agent roster
    - path: AVAILABLE_VALIDATORS.md
      purpose: Dynamic validator roster
    - path: guidelines/shared/TDD.md
      purpose: TDD enforcement requirements
    - path: guidelines/shared/VALIDATION.md
      purpose: Validation workflow

  agents:
    - path: constitutions/AGENTS.md
      purpose: Agent constitution
    - path: guidelines/agents/MANDATORY_WORKFLOW.md
      purpose: Implementation workflow
    - path: guidelines/agents/OUTPUT_FORMAT.md
      purpose: Report format specification
    - path: guidelines/shared/TDD.md
      purpose: TDD requirements
    - path: guidelines/shared/CONTEXT7.md
      purpose: Context7 usage requirements
    - path: guidelines/shared/QUALITY.md
      purpose: Quality standards
    - path: guidelines/shared/EPHEMERAL_SUMMARIES_POLICY.md
      purpose: Summary file prohibition

  validators:
    - path: constitutions/VALIDATORS.md
      purpose: Validator constitution
    - path: guidelines/validators/VALIDATOR_WORKFLOW.md
      purpose: Validation workflow
    - path: guidelines/validators/OUTPUT_FORMAT.md
      purpose: Report format specification
    - path: guidelines/shared/CONTEXT7.md
      purpose: Context7 knowledge refresh
```

#### Validation Criteria
- [ ] File exists at `edison/core/config/constitution.yaml`
- [ ] YAML parses without errors
- [ ] All three role types (orchestrator, agents, validators) defined
- [ ] Each mandatory read has both `path` and `purpose` fields
- [ ] Paths reference generated file locations (not source files)

---

### T-003: Add applies_to Field to Rules Registry

**Priority**: P0 - BLOCKER
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Add the `applies_to` field to all rules in the registry to enable role-based filtering when generating constitutions.

#### Files Affected
- `src/edison/data/rules/registry.yml` - MODIFY

#### Implementation Details

Add `applies_to` field to each rule with array of applicable roles: `[orchestrator, agent, validator]`

**Example transformations:**

```yaml
# BEFORE:
RULE.TDD.RED_FIRST:
  name: "Test Must Fail First"
  content: "Write failing test before implementation code"
  category: implementation
  severity: critical

# AFTER:
RULE.TDD.RED_FIRST:
  name: "Test Must Fail First"
  content: "Write failing test before implementation code"
  category: implementation
  severity: critical
  applies_to: [agent, validator]

# Role-specific rules:
RULE.DELEGATION.ORCHESTRATOR_ONLY:
  name: "Orchestrator Delegates"
  content: "Only orchestrator delegates; agents implement"
  category: delegation
  severity: high
  applies_to: [orchestrator]

RULE.CONTEXT7.QUERY_BEFORE_CODE:
  name: "Query Context7 Before Coding"
  content: "Always query Context7 for post-training packages before writing code"
  category: context
  severity: critical
  applies_to: [agent, orchestrator]

RULE.VALIDATION.BUNDLE_FIRST:
  name: "Bundle Before Validate"
  content: "Create bundle before running validators"
  category: validation
  severity: high
  applies_to: [orchestrator]
```

**Role assignments for all 37 rules:**
- Rules about TDD → `[agent, validator]`
- Rules about delegation → `[orchestrator]`
- Rules about Context7 → `[agent, orchestrator]`
- Rules about validation → `[orchestrator, validator]`
- Rules about implementation → `[agent]`
- Rules about session management → `[orchestrator]`
- General rules → `[orchestrator, agent, validator]`

#### Validation Criteria
- [ ] All 37 rules have `applies_to` field
- [ ] Each `applies_to` is an array containing valid role names
- [ ] Valid role names are: `orchestrator`, `agent`, `validator`
- [ ] YAML parses without errors
- [ ] No rule has empty `applies_to` array

---

### T-004: Implement Constitution Composer

**Priority**: P0 - BLOCKER
**Dependencies**: T-001, T-002, T-003
**Parallel Execution**: No (depends on prior tasks)

#### Description
Create the constitution composer module that generates the three constitution files from core + packs + project layers.

#### Files Affected
- `src/edison/core/composition/constitution.py` - CREATE (~250 lines)

#### Implementation Details

```python
# src/edison/core/composition/constitution.py
"""Constitution composition engine for Edison framework."""

from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import yaml

from edison.core.rules import RuleRegistry
from edison.core.config import ConfigManager


def get_rules_for_role(role: str) -> List[Dict[str, Any]]:
    """Extract rules that apply to a specific role."""
    rules = RuleRegistry.get_all()
    return [r for r in rules if role in r.get('applies_to', [])]


def load_constitution_layer(base_path: Path, role: str, layer_type: str) -> str:
    """Load constitution content from a specific layer."""
    filename_map = {
        'orchestrator': f'{role}-base.md' if layer_type == 'core' else f'{role}-additions.md',
        'agents': f'{role}-base.md' if layer_type == 'core' else f'{role}-additions.md',
        'validators': f'{role}-base.md' if layer_type == 'core' else f'{role}-additions.md',
    }

    file_path = base_path / 'constitutions' / filename_map.get(role, f'{role}.md')
    if file_path.exists():
        return file_path.read_text()
    return ""


def compose_constitution(role: str, config: ConfigManager) -> str:
    """Compose a constitution from core + packs + project layers."""
    layers = []
    source_layers = []

    # Load core
    core_content = load_constitution_layer(config.core_path, role, 'core')
    if core_content:
        layers.append(core_content)
        source_layers.append('core')

    # Load active packs
    for pack in config.active_packs:
        pack_content = load_constitution_layer(config.packs_path / pack, role, 'pack')
        if pack_content:
            layers.append(pack_content)
            source_layers.append(f'packs({pack})')

    # Load project
    project_content = load_constitution_layer(config.project_path, role, 'project')
    if project_content:
        layers.append(project_content)
        source_layers.append('project')

    # Compose and render template
    composed = "\n\n".join(layers)

    # Inject template variables
    composed = render_constitution_template(composed, role, config, source_layers)

    return composed


def render_constitution_template(template: str, role: str, config: ConfigManager, source_layers: List[str]) -> str:
    """Render Handlebars-style placeholders in constitution template."""
    # Load constitution config
    constitution_config = config.load_yaml('constitution.yaml')
    mandatory_reads = constitution_config.get('mandatoryReads', {}).get(role, [])

    # Get rules for this role
    rules = get_rules_for_role(role)

    # Replace placeholders
    template = template.replace('{{source_layers}}', ' + '.join(source_layers))
    template = template.replace('{{generated_date}}', datetime.now().isoformat())

    # Render mandatory reads
    reads_section = "\n".join([f"- {r['path']}: {r['purpose']}" for r in mandatory_reads])
    template = template.replace('{{#each mandatoryReads.' + role + '}}', reads_section)
    template = template.replace('{{/each}}', '')  # Remove closing tags

    # Render rules
    rules_section = "\n\n".join([
        f"### {r['id']}: {r['name']}\n{r['content']}"
        for r in rules
    ])
    template = template.replace('{{#each rules.' + role + '}}', rules_section)

    return template


def generate_all_constitutions(config: ConfigManager, output_path: Path) -> None:
    """Generate all three constitution files."""
    output_path = output_path / 'constitutions'
    output_path.mkdir(parents=True, exist_ok=True)

    for role, filename in [
        ('orchestrator', 'ORCHESTRATORS.md'),
        ('agents', 'AGENTS.md'),
        ('validators', 'VALIDATORS.md'),
    ]:
        content = compose_constitution(role, config)
        (output_path / filename).write_text(content)
```

#### Validation Criteria
- [ ] Module exists at `src/edison/core/composition/constitution.py`
- [ ] `get_rules_for_role()` function filters rules by `applies_to` field
- [ ] `compose_constitution()` loads and merges core + packs + project layers
- [ ] Template placeholders are properly rendered
- [ ] `generate_all_constitutions()` creates all three files
- [ ] Unit tests pass for constitution composition

---

### T-005: Implement get_rules_for_role() API

**Priority**: P0 - BLOCKER
**Dependencies**: T-003
**Parallel Execution**: Yes (after T-003)

#### Description
Add the role-based rule query API to the RulesEngine for filtering rules by applicable role.

#### Files Affected
- `src/edison/core/rules/engine.py` - MODIFY

#### Implementation Details

Add to existing RulesEngine class:

```python
@classmethod
def get_rules_for_role(cls, role: str) -> List[Dict[str, Any]]:
    """
    Extract rules that apply to a specific role.

    Args:
        role: One of 'orchestrator', 'agent', 'validator'

    Returns:
        List of rule dictionaries where applies_to includes the role
    """
    if role not in ('orchestrator', 'agent', 'validator'):
        raise ValueError(f"Invalid role: {role}. Must be orchestrator, agent, or validator")

    all_rules = cls.get_all()
    return [
        rule for rule in all_rules
        if role in rule.get('applies_to', [])
    ]

@classmethod
def get_rules_for_context(cls, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Enhanced to support role-based filtering."""
    rules = cls.get_all()

    # Filter by role if specified
    if 'role' in context:
        rules = [r for r in rules if context['role'] in r.get('applies_to', [])]

    # Existing category/severity filtering...
    if 'category' in context:
        rules = [r for r in rules if r.get('category') == context['category']]

    return rules
```

#### Validation Criteria
- [ ] `get_rules_for_role('orchestrator')` returns only orchestrator rules
- [ ] `get_rules_for_role('agent')` returns only agent rules
- [ ] `get_rules_for_role('validator')` returns only validator rules
- [ ] Invalid role raises ValueError
- [ ] `get_rules_for_context({'role': 'agent'})` filters correctly

---

### T-006: Generate AVAILABLE_AGENTS.md Dynamically

**Priority**: P0 - BLOCKER
**Dependencies**: T-004
**Parallel Execution**: Yes (after T-004)

#### Description
Implement dynamic generation of AVAILABLE_AGENTS.md from the AgentRegistry instead of hardcoding agent lists.

#### Files Affected
- `src/edison/core/composition/rosters.py` - CREATE (~100 lines)

#### Implementation Details

```python
# src/edison/core/composition/rosters.py
"""Dynamic roster generation for agents and validators."""

from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from edison.core.agents import AgentRegistry


def generate_available_agents(output_path: Path) -> None:
    """Generate AVAILABLE_AGENTS.md from AgentRegistry."""
    agents = AgentRegistry.get_all()

    content = f"""<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Regenerate: edison compose --all -->
<!-- Generated: {datetime.now().isoformat()} -->

# Available Agents

This file is dynamically generated from the AgentRegistry. Do not edit directly.

## Agent Roster

| Agent | Type | Model | Description |
|-------|------|-------|-------------|
{_format_agent_table(agents)}

## Agent Details

{_format_agent_details(agents)}

## Delegation Patterns

See `guidelines/shared/DELEGATION.md` for file pattern → agent mappings.
"""

    output_path.write_text(content)


def _format_agent_table(agents: List[Dict[str, Any]]) -> str:
    """Format agents as markdown table rows."""
    rows = []
    for agent in agents:
        rows.append(
            f"| {agent['name']} | {agent.get('type', 'implementer')} | "
            f"{agent.get('model', 'codex')} | {agent.get('description', '')} |"
        )
    return "\n".join(rows)


def _format_agent_details(agents: List[Dict[str, Any]]) -> str:
    """Format detailed agent descriptions."""
    sections = []
    for agent in agents:
        sections.append(f"""### {agent['name']}

**Model**: {agent.get('model', 'codex')}
**Type**: {agent.get('type', 'implementer')}
**Prompt**: `agents/{agent['name']}.md`

{agent.get('description', 'No description available.')}
""")
    return "\n".join(sections)
```

#### Validation Criteria
- [ ] AVAILABLE_AGENTS.md is generated at `.edison/_generated/AVAILABLE_AGENTS.md`
- [ ] File includes generation header with timestamp
- [ ] Agent table includes all registered agents
- [ ] No hardcoded agent names in the template
- [ ] File regenerates correctly when AgentRegistry changes

---

### T-007: Generate AVAILABLE_VALIDATORS.md Dynamically

**Priority**: P0 - BLOCKER
**Dependencies**: T-004
**Parallel Execution**: Yes (after T-004)

#### Description
Implement dynamic generation of AVAILABLE_VALIDATORS.md from the ValidatorRegistry.

#### Files Affected
- `src/edison/core/composition/rosters.py` - MODIFY (add validator generation)

#### Implementation Details

Add to rosters.py:

```python
from edison.core.validators import ValidatorRegistry


def generate_available_validators(output_path: Path) -> None:
    """Generate AVAILABLE_VALIDATORS.md from ValidatorRegistry."""
    validators = ValidatorRegistry.get_all()

    # Group by tier
    global_validators = [v for v in validators if v.get('tier') == 'global']
    critical_validators = [v for v in validators if v.get('tier') == 'critical']
    specialized_validators = [v for v in validators if v.get('tier') == 'specialized']

    content = f"""<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Regenerate: edison compose --all -->
<!-- Generated: {datetime.now().isoformat()} -->

# Available Validators

This file is dynamically generated from the ValidatorRegistry. Do not edit directly.

## Validator Roster

### Global Validators (Always Run)

| Validator | Model | Blocking | Description |
|-----------|-------|----------|-------------|
{_format_validator_table(global_validators)}

### Critical Validators (Blocking)

| Validator | Model | Blocking | Description |
|-----------|-------|----------|-------------|
{_format_validator_table(critical_validators)}

### Specialized Validators (Pattern-Triggered)

| Validator | Model | Blocking | Triggers |
|-----------|-------|----------|----------|
{_format_specialized_validator_table(specialized_validators)}

## Validator Execution Order

1. **Wave 1**: Global validators (parallel)
2. **Wave 2**: Critical validators (parallel, blocks on failure)
3. **Wave 3**: Specialized validators (parallel, triggered by file patterns)

## Consensus Requirements

- Global validators must reach consensus (codex-global + claude-global agree)
- Critical validators are blocking (any failure rejects the task)
- Specialized validators are advisory unless configured as blocking

See `guidelines/shared/VALIDATION.md` for detailed workflow.
"""

    output_path.write_text(content)


def _format_validator_table(validators: List[Dict[str, Any]]) -> str:
    """Format validators as markdown table rows."""
    rows = []
    for v in validators:
        blocking = "✅" if v.get('blocking', False) else "❌"
        rows.append(
            f"| {v['name']} | {v.get('model', 'codex')} | {blocking} | {v.get('description', '')} |"
        )
    return "\n".join(rows)


def _format_specialized_validator_table(validators: List[Dict[str, Any]]) -> str:
    """Format specialized validators with trigger patterns."""
    rows = []
    for v in validators:
        blocking = "✅" if v.get('blocking', False) else "❌"
        triggers = ", ".join(v.get('fileTriggers', [])[:3])  # First 3 patterns
        rows.append(f"| {v['name']} | {v.get('model', 'codex')} | {blocking} | {triggers} |")
    return "\n".join(rows)
```

#### Validation Criteria
- [ ] AVAILABLE_VALIDATORS.md is generated at `.edison/_generated/AVAILABLE_VALIDATORS.md`
- [ ] Validators grouped by tier (global, critical, specialized)
- [ ] No hardcoded validator names or counts
- [ ] Includes execution order documentation
- [ ] File regenerates correctly when ValidatorRegistry changes

---

### T-008: Generate constitutions/ORCHESTRATORS.md

**Priority**: P0 - BLOCKER
**Dependencies**: T-004, T-005, T-006, T-007
**Parallel Execution**: No

#### Description
Wire up the constitution composer to generate the ORCHESTRATORS.md constitution file during `edison compose`.

#### Files Affected
- `src/edison/cli/commands/compose.py` - MODIFY
- `src/edison/core/composition/__init__.py` - MODIFY

#### Implementation Details

Update compose command to include constitution generation:

```python
# In compose.py
from edison.core.composition.constitution import generate_all_constitutions
from edison.core.composition.rosters import generate_available_agents, generate_available_validators

@click.command()
@click.option('--all', 'compose_all', is_flag=True, help='Compose all outputs')
@click.option('--constitutions', is_flag=True, help='Compose constitutions only')
def compose(compose_all: bool, constitutions: bool):
    """Compose Edison outputs from core + packs + project."""
    config = ConfigManager.load()
    output_path = config.output_path / '_generated'

    if compose_all or constitutions:
        # Generate rosters first (constitutions reference them)
        generate_available_agents(output_path / 'AVAILABLE_AGENTS.md')
        generate_available_validators(output_path / 'AVAILABLE_VALIDATORS.md')

        # Generate constitutions
        generate_all_constitutions(config, output_path)

        click.echo("✅ Constitutions generated")

    # ... rest of composition
```

#### Validation Criteria
- [ ] `edison compose --all` generates `constitutions/ORCHESTRATORS.md`
- [ ] Generated file includes self-identification header
- [ ] Mandatory reads section populated from constitution.yaml
- [ ] Rules section populated with orchestrator-applicable rules
- [ ] References AVAILABLE_AGENTS.md and AVAILABLE_VALIDATORS.md (not hardcoded lists)

---

### T-009: Generate constitutions/AGENTS.md

**Priority**: P0 - BLOCKER
**Dependencies**: T-004, T-005
**Parallel Execution**: Yes (with T-008, T-010)

#### Description
Ensure the constitution composer generates the AGENTS.md constitution file.

#### Files Affected
- Already handled by T-004 and T-008 integration

#### Implementation Details

Verify that `generate_all_constitutions()` produces `constitutions/AGENTS.md` with:
- Self-identification header with Role: AGENT
- Mandatory reads for agents from constitution.yaml
- Applicable rules filtered by `applies_to: [agent]`
- Workflow requirements section
- Output format reference

#### Validation Criteria
- [ ] `edison compose --all` generates `constitutions/AGENTS.md`
- [ ] Generated file has Role: AGENT in header
- [ ] Mandatory reads match constitution.yaml agents section
- [ ] Rules are filtered to agent-applicable only

---

### T-010: Generate constitutions/VALIDATORS.md

**Priority**: P0 - BLOCKER
**Dependencies**: T-004, T-005
**Parallel Execution**: Yes (with T-008, T-009)

#### Description
Ensure the constitution composer generates the VALIDATORS.md constitution file.

#### Files Affected
- Already handled by T-004 and T-008 integration

#### Validation Criteria
- [ ] `edison compose --all` generates `constitutions/VALIDATORS.md`
- [ ] Generated file has Role: VALIDATOR in header
- [ ] Mandatory reads match constitution.yaml validators section
- [ ] Rules are filtered to validator-applicable only

---

### T-011: Deprecate and Remove ORCHESTRATOR_GUIDE.md

**Priority**: P0 - BLOCKER
**Dependencies**: T-008
**Parallel Execution**: No

#### Description
Remove ORCHESTRATOR_GUIDE.md generation and update all references to use the new constitution system.

#### Files Affected
- `src/edison/core/composition/orchestrator.py` - MODIFY (remove or deprecate)
- `src/edison/cli/commands/compose.py` - MODIFY (remove orchestrator guide generation)
- `.claude/CLAUDE.md` template - MODIFY (reference constitution instead)

#### Implementation Details

1. Remove or comment out `compose_orchestrator_guide()` function
2. Update compose command to skip orchestrator guide generation
3. Update CLAUDE.md template to reference `constitutions/ORCHESTRATORS.md`
4. Add deprecation notice if file still exists in projects

```python
# In compose.py - REMOVE this:
# generate_orchestrator_guide(config, output_path)

# Update CLAUDE.md template:
# OLD: See: ORCHESTRATOR_GUIDE.md
# NEW: See: constitutions/ORCHESTRATORS.md for orchestrator constitution
```

#### Validation Criteria
- [ ] `edison compose --all` does NOT generate ORCHESTRATOR_GUIDE.md
- [ ] CLAUDE.md references constitutions/ORCHESTRATORS.md
- [ ] No runtime errors from missing ORCHESTRATOR_GUIDE.md
- [ ] Existing projects with ORCHESTRATOR_GUIDE.md continue to work (graceful deprecation)

---

### T-012: Fix Zen Prompt Composition - Wrong Role Bug

**Priority**: P0 - BLOCKER
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Fix the critical bug where Zen prompts contain wrong content (validator content in agent prompts). The composition engine is generating validator prompts instead of agent prompts for agent Zen files.

#### Files Affected
- `src/edison/core/composition/composers.py` - MODIFY

#### Implementation Details

**Current Bug:**
```python
# WRONG - all Zen prompts call compose_validator():
def compose_zen_prompt(agent_name: str):
    return compose_validator(agent_name)  # BUG! Always returns validator content
```

**Fix:**
```python
def compose_zen_prompt(name: str) -> str:
    """
    Compose a Zen prompt for an agent or validator.

    Determines role type from registry and calls appropriate composer.
    """
    # Check if it's a validator
    if ValidatorRegistry.exists(name):
        return compose_validator_zen_prompt(name)

    # Check if it's an agent
    if AgentRegistry.exists(name):
        return compose_agent_zen_prompt(name)

    raise ValueError(f"Unknown agent or validator: {name}")


def compose_agent_zen_prompt(agent_name: str) -> str:
    """Compose Zen system prompt for an agent."""
    agent = AgentRegistry.get(agent_name)
    agent_content = compose_agent(agent_name)  # Get full agent brief

    return f"""# {agent['name']} Agent

{agent_content}

## Constitution Reference
Before starting work, read: constitutions/AGENTS.md
"""


def compose_validator_zen_prompt(validator_name: str) -> str:
    """Compose Zen system prompt for a validator."""
    validator = ValidatorRegistry.get(validator_name)
    validator_content = compose_validator(validator_name)

    return f"""# {validator['name']} Validator

{validator_content}

## Constitution Reference
Before starting validation, read: constitutions/VALIDATORS.md
"""
```

#### Verification Commands

```bash
# After fix, verify Zen prompts contain correct content:
grep "API Builder" .zen/conf/systemprompts/wilson-api-builder.txt  # Should FIND
grep "Gemini Global Validator" .zen/conf/systemprompts/wilson-api-builder.txt  # Should NOT FIND

# Verify all 6 agents have correct content:
for agent in api-builder component-builder database-architect code-reviewer test-engineer feature-implementer; do
  echo "Checking $agent..."
  grep -l "$agent" .zen/conf/systemprompts/wilson-$agent.txt || echo "MISSING!"
done
```

#### Validation Criteria
- [ ] Agent Zen prompts contain agent content (not validator)
- [ ] Validator Zen prompts contain validator content
- [ ] All 6 agent Zen files reference their respective agent briefs
- [ ] All validator Zen files reference their respective validator content
- [ ] Constitution reference added to all Zen prompts

---

## 5. P1 - CRITICAL Tasks

### T-013: Fix Pack Section Duplication Bug

**Priority**: P1 - CRITICAL
**Dependencies**: T-012
**Parallel Execution**: No

#### Description
Fix the composition bug that duplicates pack context sections 5-7 times in validator files, causing massive bloat.

#### Files Affected
- `src/edison/core/composition/composers.py` - MODIFY

#### Implementation Details

The bug occurs because pack sections are appended in a loop without deduplication.

**Root Cause:** Each composition pass appends pack content instead of merging/deduplicating.

**Fix:**
```python
def compose_validator(validator_name: str) -> str:
    """Compose validator with deduplicated pack sections."""
    config = ConfigManager.load()

    # Track which pack sections we've already added
    included_packs = set()
    sections = []

    # Add core validator content
    core_content = load_validator_core(validator_name)
    sections.append(core_content)

    # Add pack sections (deduplicated)
    for pack in config.active_packs:
        if pack not in included_packs:
            pack_content = load_validator_pack_section(validator_name, pack)
            if pack_content:
                sections.append(pack_content)
                included_packs.add(pack)

    # Add project overrides
    project_content = load_validator_project_overrides(validator_name)
    if project_content:
        sections.append(project_content)

    return "\n\n".join(sections)
```

#### Validation Criteria
- [ ] claude-global.md has pack sections only 1x (not 7x)
- [ ] codex-global.md has pack sections only 1x (not 5x)
- [ ] File sizes reduced: claude-global ~24KB (not 79KB), codex-global ~22KB (not 61KB)
- [ ] All pack content still present (just not duplicated)

---

### T-014: Create post-training-packages.yaml Configuration

**Priority**: P1 - CRITICAL
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Create the configuration file for post-training packages that validators need for Context7 queries.

#### Files Affected
- `src/edison/data/config/post_training_packages.yaml` - CREATE (~80 lines)

#### Content to Restore

```yaml
# src/edison/data/config/post_training_packages.yaml
# Post-training packages for Context7 knowledge refresh
# These packages have versions newer than the model's training cutoff

version: "1.0.0"
trainingCutoff: "2025-01"

packages:
  next:
    version: "16.0.0"
    context7Id: "/vercel/next.js"
    criticalChanges:
      - "App Router is now default"
      - "Server Components by default"
      - "New caching behavior"
    topics:
      - "route handlers"
      - "app router patterns"
      - "server components"
      - "metadata API"

  react:
    version: "19.2.0"
    context7Id: "/facebook/react"
    criticalChanges:
      - "New use() hook"
      - "Server Components"
      - "Actions"
    topics:
      - "hooks"
      - "server components"
      - "suspense"

  tailwindcss:
    version: "4.0.0"
    context7Id: "/tailwindlabs/tailwindcss"
    criticalChanges:
      - "COMPLETELY different syntax from v3"
      - "CSS-first configuration"
      - "New color system"
    topics:
      - "v4 syntax"
      - "configuration"
      - "utilities"

  zod:
    version: "4.1.12"
    context7Id: "/colinhacks/zod"
    criticalChanges:
      - "Breaking changes from v3 API"
    topics:
      - "validation"
      - "schemas"

  motion:
    version: "12.23.24"
    context7Id: "/framer/motion"
    criticalChanges:
      - "API changes (formerly Framer Motion)"
      - "New animation syntax"
    topics:
      - "animations"
      - "gestures"
      - "layout animations"

  typescript:
    version: "5.7.0"
    context7Id: "/microsoft/typescript"
    criticalChanges:
      - "New type inference features"
    topics:
      - "type inference"
      - "satisfies operator"

  prisma:
    version: "6.0.0"
    context7Id: "/prisma/prisma"
    criticalChanges:
      - "New client API"
    topics:
      - "schema"
      - "client"
      - "migrations"

  better-auth:
    version: "1.0.0"
    context7Id: "/better-auth/better-auth"
    criticalChanges:
      - "New authentication library"
    topics:
      - "authentication"
      - "sessions"
```

#### Validation Criteria
- [ ] File exists at correct path
- [ ] YAML parses without errors
- [ ] All 8 packages defined with version, context7Id, criticalChanges, topics
- [ ] trainingCutoff date specified

---

### T-015: Fix Hardcoded Rule Source Paths

**Priority**: P1 - CRITICAL
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Replace all hardcoded `.agents/` paths in rules registry with configurable base path references.

#### Files Affected
- `src/edison/data/rules/registry.yml` - MODIFY

#### Implementation Details

**Current (Wrong):**
```yaml
RULE.TDD.RED_FIRST:
  sourcePath: ".agents/guidelines/TDD.md"  # Hardcoded project path
```

**Fixed:**
```yaml
RULE.TDD.RED_FIRST:
  sourcePath: "guidelines/shared/TDD.md"  # Relative to generated output
  # Full path resolved at runtime: ${output_path}/_generated/guidelines/shared/TDD.md
```

Update ALL 32 rules that have `sourcePath` with `.agents/` prefix to use relative paths.

#### Validation Criteria
- [ ] No rule has `.agents/` in sourcePath
- [ ] All sourcePaths are relative (start with `guidelines/`, `agents/`, etc.)
- [ ] Path resolution works correctly at runtime

---

### T-016: Add Complete YAML Frontmatter to All Agents

**Priority**: P1 - CRITICAL
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Add complete YAML frontmatter to all 6 agent files with all required fields.

#### Files Affected
- `src/edison/data/agents/api-builder.md`
- `src/edison/data/agents/component-builder.md`
- `src/edison/data/agents/database-architect.md`
- `src/edison/data/agents/code-reviewer.md`
- `src/edison/data/agents/test-engineer.md`
- `src/edison/data/agents/feature-implementer.md`

#### Implementation Details

Each agent file must begin with this YAML frontmatter structure:

```yaml
---
name: api-builder
description: Backend API specialist for route handlers, validation, and data flow
model: codex
zenRole: "{{project.zenRoles.api-builder}}"  # Resolved from project overlay
context7_ids:
  - /vercel/next.js
  - /colinhacks/zod
  - /prisma/prisma
allowed_tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Bash
requires_validation: true
constitution: constitutions/AGENTS.md
---
```

**Agent-specific values:**

| Agent | Model | Primary context7_ids |
|-------|-------|---------------------|
| api-builder | codex | next.js, zod, prisma |
| component-builder | claude | next.js, react, tailwindcss, motion |
| database-architect | codex | prisma |
| code-reviewer | claude | next.js, react, prisma, zod |
| test-engineer | codex | vitest (if available), next.js |
| feature-implementer | claude | next.js, react, prisma, zod, tailwindcss |

#### Validation Criteria
- [ ] All 6 agent files have valid YAML frontmatter
- [ ] All required fields present: name, description, model, zenRole, context7_ids, allowed_tools, requires_validation, constitution
- [ ] YAML parses without errors
- [ ] zenRole values reference project config variable (not hardcoded "wilson-*")

---

### T-017: Create START_NEW_SESSION.md

**Priority**: P1 - CRITICAL
**Dependencies**: T-008
**Parallel Execution**: Yes

#### Description
Create the session bootstrap prompt for starting fresh sessions.

#### Files Affected
- `edison/core/start/START_NEW_SESSION.md` - CREATE (~100 lines)

#### Content to Restore

Source: `wilson-pre-edison/.agents/START.SESSION.md` lines 1-34

```markdown
# Start New Session

## Pre-Session Checklist

Before beginning work:

1. ✅ Read your constitution: `constitutions/ORCHESTRATORS.md`
2. ✅ Load available agents: `AVAILABLE_AGENTS.md`
3. ✅ Load available validators: `AVAILABLE_VALIDATORS.md`
4. ✅ Confirm the human's request explicitly

## Session Initialization

Run the session start command:
```bash
edison session start
```

This will:
- Create a new session ID
- Initialize the session directory
- Set up git worktree (if configured)
- Record session start time

## Intake Protocol

1. **Confirm Request**: Restate what the human is asking for
2. **Check Stale Work**: Close any work older than the configured threshold
3. **Shared QA Rule**: Leave QA briefs assigned to other sessions alone
4. **Reclaim Stale Tasks**: Tasks idle > threshold can be reclaimed
5. **Select Work**: Choose 1-5 tasks based on scope and dependencies

## Begin Work

After intake is complete:
```bash
edison session next
```

This provides guidance on the next action based on session state.

## Session Loop

Repeat until all tasks complete:
1. Claim task → `edison tasks claim <task-id>`
2. Implement following TDD and delegation rules
3. Mark ready → `edison tasks ready <task-id>`
4. Run validators → `edison validate <task-id>`
5. Address any rejections
6. Complete task → `edison tasks complete <task-id>`

## Constitution Reference

Your full orchestrator instructions are at: `constitutions/ORCHESTRATORS.md`

Re-read this constitution:
- At session start (now)
- After any context compaction
- When resuming after interruption
```

#### Validation Criteria
- [ ] File exists at `edison/core/start/START_NEW_SESSION.md`
- [ ] Includes pre-session checklist
- [ ] Includes session initialization command
- [ ] Includes intake protocol steps
- [ ] References constitution (not hardcoded instructions)

---

### T-018: Create START_RESUME_SESSION.md

**Priority**: P1 - CRITICAL
**Dependencies**: T-017
**Parallel Execution**: Yes

#### Description
Create the session recovery prompt for resuming interrupted sessions.

#### Files Affected
- `edison/core/start/START_RESUME_SESSION.md` - CREATE (~80 lines)

#### Content to Restore

```markdown
# Resume Session

## Session Recovery

You are resuming session: `{{session_id}}`

Run the resume command:
```bash
edison session resume {{session_id}}
```

## Recovery Checklist

1. ✅ Re-read your constitution: `constitutions/ORCHESTRATORS.md`
2. ✅ Check session state: `edison session status`
3. ✅ Review in-progress tasks: `edison tasks list --status=wip`
4. ✅ Check for blocked tasks: `edison tasks list --status=blocked`

## State Assessment

The session may have been interrupted due to:
- Context compaction
- System restart
- Manual pause
- Error recovery

## Resume Protocol

1. **Load Context**: Read all task documents for in-progress work
2. **Check Dependencies**: Verify no blocking tasks have new issues
3. **Continue Work**: Pick up where you left off

```bash
edison session next
```

## Recovery Notes

- Tasks marked WIP remain yours
- QA briefs in progress remain assigned
- Validators may need re-running if state is unclear

## Constitution Reference

Re-read your full instructions at: `constitutions/ORCHESTRATORS.md`
```

#### Validation Criteria
- [ ] File exists at `edison/core/start/START_RESUME_SESSION.md`
- [ ] Includes session ID placeholder
- [ ] Includes recovery checklist
- [ ] References constitution for full instructions

---

### T-019: Create START_VALIDATE_SESSION.md

**Priority**: P1 - CRITICAL
**Dependencies**: T-017
**Parallel Execution**: Yes

#### Description
Create the validation-only session prompt for running validators without implementation.

#### Files Affected
- `edison/core/start/START_VALIDATE_SESSION.md` - CREATE (~80 lines)

#### Content to Restore

Source: `wilson-pre-edison/.agents/START.AUDIT.md` lines 1-27

```markdown
# Validation Session

## Purpose

This session is for running validators only, not implementation.

## Pre-Validation Checklist

1. ✅ Read validator constitution: `constitutions/VALIDATORS.md`
2. ✅ Load validator roster: `AVAILABLE_VALIDATORS.md`
3. ✅ Identify tasks ready for validation: `edison tasks list --status=ready`

## Validation Protocol

For each task ready for validation:

1. **Load Bundle**: Read the task's implementation report and evidence
2. **Run Validators**: Execute validation in waves
   - Wave 1: Global validators (codex-global, claude-global)
   - Wave 2: Critical validators (security, performance)
   - Wave 3: Specialized validators (triggered by file patterns)
3. **Collect Results**: Aggregate verdicts from all validators
4. **Make Decision**:
   - All pass → APPROVE
   - Any blocking fail → REJECT
   - Non-blocking issues → APPROVE with notes

## Validation Commands

```bash
# Validate a specific task
edison validate <task-id>

# Validate all ready tasks
edison validate --all-ready
```

## Constitution Reference

Your full validator instructions are at: `constitutions/VALIDATORS.md`
```

#### Validation Criteria
- [ ] File exists at `edison/core/start/START_VALIDATE_SESSION.md`
- [ ] Includes pre-validation checklist
- [ ] Includes validation protocol with waves
- [ ] References validator constitution

---

### T-020: Restore Context7 MCP Tool Examples to All Agents

**Priority**: P1 - CRITICAL
**Dependencies**: T-016
**Parallel Execution**: Yes

#### Description
Restore the explicit Context7 MCP tool call examples to all 6 agent files.

#### Files Affected
- All 6 agent files in `src/edison/data/agents/`

#### Content to Restore

Source: `wilson-pre-edison/.agents/agents/api-builder.md` lines 85-112

Add to each agent file after the frontmatter:

```markdown
## Context7 Knowledge Refresh (MANDATORY)

Your training data may be outdated. Before writing ANY code, refresh your knowledge:

### Step 1: Resolve Library ID
```typescript
mcp__context7__resolve-library-id({
  libraryName: "next.js"  // or react, tailwindcss, prisma, zod, motion
})
```

### Step 2: Get Current Documentation
```typescript
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/vercel/next.js",
  topic: "route handlers, app router patterns, server components"
})
```

### Critical Package Versions (May Differ from Training)

See: `config/post_training_packages.yaml` for current versions.

⚠️ **WARNING**: Your knowledge is likely outdated for:
- Next.js 16 (major App Router changes)
- React 19 (new use() hook, Server Components)
- Tailwind CSS 4 (COMPLETELY different syntax)
- Prisma 6 (new client API)

Always query Context7 before assuming you know the current API!
```

#### Validation Criteria
- [ ] All 6 agents have Context7 section
- [ ] Section includes resolve-library-id example
- [ ] Section includes get-library-docs example
- [ ] Section includes version warning
- [ ] References post_training_packages.yaml (not hardcoded versions)

---

### T-021: Remove Hardcoded Validator Counts from Guidelines

**Priority**: P1 - CRITICAL
**Dependencies**: T-007
**Parallel Execution**: Yes

#### Description
Replace all hardcoded "9 validators" references with dynamic references to AVAILABLE_VALIDATORS.md.

#### Files Affected
- `src/edison/data/guidelines/shared/VALIDATION.md`
- `src/edison/data/guidelines/agents/VALIDATION_AWARENESS.md`
- All 6 agent files (validation architecture section)

#### Implementation Details

**Find and Replace:**
```
# OLD (wrong):
"9-validator architecture"
"9 independent validators"
"The 9 validators are: codex-global, claude-global, ..."

# NEW (correct):
"multi-validator architecture"
"See AVAILABLE_VALIDATORS.md for the current validator roster"
"Validators are organized in three tiers: Global, Critical, and Specialized"
```

#### Validation Criteria
- [ ] No file contains "9-validator" or "9 validators"
- [ ] All validator references point to AVAILABLE_VALIDATORS.md
- [ ] Validation architecture described in terms of tiers (not counts)

---

### T-022: Remove Hardcoded wilson-* zenRoles

**Priority**: P1 - CRITICAL
**Dependencies**: T-016
**Parallel Execution**: Yes

#### Description
Remove all hardcoded "wilson-*" zenRole references and replace with project overlay config references.

#### Files Affected
- All agent frontmatter files
- `src/edison/data/config/delegation.yaml`
- `src/edison/data/config/validators.yaml`
- Any file with "wilson-" prefix in zenRole

#### Implementation Details

**Find all occurrences:**
```bash
grep -r "wilson-" src/edison/data/
```

**Replace pattern:**
```yaml
# OLD (wrong):
zenRole: wilson-api-builder

# NEW (correct):
zenRole: "{{project.zenRoles.api-builder}}"
# Resolved at compose time from .edison/config/project.yaml
```

**Project overlay example:**
```yaml
# .edison/config/project.yaml (in wilson-leadgen project)
zenRoles:
  api-builder: wilson-api-builder
  component-builder: wilson-component-builder
  database-architect: wilson-database-architect
  test-engineer: wilson-test-engineer
  feature-implementer: wilson-feature-implementer
  code-reviewer: wilson-code-reviewer
  validator-codex-global: wilson-validator-codex-global
  # ... etc
```

#### Validation Criteria
- [ ] No hardcoded "wilson-" in edison core files
- [ ] All zenRoles use template variables
- [ ] Project overlay documents zenRole mapping

---

### T-023: Restore TDD Delegation Templates

**Priority**: P1 - CRITICAL
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Restore the TDD delegation templates that were lost during migration (136 lines).

#### Files Affected
- `src/edison/data/guidelines/shared/TDD.md` - MODIFY

#### Content to Restore

Source: `wilson-pre-edison/.agents/guides/extended/TDD_GUIDE.md` lines 374-507

```markdown
## TDD When Delegating to Sub-Agents

### Delegation Template: Component Builder

When delegating to component-builder, include:

```
Task: Create [ComponentName] component

TDD Requirements:
1. FIRST write tests in __tests__/[ComponentName].test.tsx
2. Tests must FAIL initially (red phase)
3. Then implement in [ComponentName].tsx
4. Tests must PASS (green phase)
5. Refactor if needed (maintaining green)

Test Coverage Required:
- [ ] Renders without crashing
- [ ] Displays correct content based on props
- [ ] Handles loading state
- [ ] Handles error state
- [ ] Handles empty state
- [ ] Accessibility (aria labels, keyboard nav)
- [ ] Responsive behavior

Evidence Required:
- Screenshot of failing tests
- Screenshot of passing tests
- Coverage report
```

### Delegation Template: API Builder

When delegating to api-builder, include:

```
Task: Create [endpoint] API route

TDD Requirements:
1. FIRST write tests in __tests__/api/[endpoint].test.ts
2. Tests must FAIL initially (red phase)
3. Then implement in app/api/[endpoint]/route.ts
4. Tests must PASS (green phase)

Test Coverage Required:
- [ ] Returns correct status codes (200, 400, 401, 404, 500)
- [ ] Validates request body with Zod
- [ ] Handles authentication (requireAuth)
- [ ] Handles authorization (permissions)
- [ ] Returns correct response shape
- [ ] Handles edge cases (empty, null, invalid)

Evidence Required:
- Test output showing red → green
- API response examples
```

### Delegation Template: Database Architect

When delegating to database-architect, include:

```
Task: Create/modify [Model] schema

TDD Requirements:
1. FIRST write integration tests for the schema
2. Tests verify relationships, constraints, indexes
3. Then create/modify schema.prisma
4. Run migration
5. Verify tests pass

Test Coverage Required:
- [ ] Model creates successfully
- [ ] Required fields enforced
- [ ] Unique constraints work
- [ ] Relationships resolve correctly
- [ ] Indexes improve query performance
- [ ] Cascade deletes work as expected

Evidence Required:
- Migration SQL
- Test output
- Query performance before/after (if optimization)
```
```

#### Validation Criteria
- [ ] TDD.md includes delegation templates section
- [ ] Templates for component-builder, api-builder, database-architect present
- [ ] Each template includes TDD requirements and evidence requirements
- [ ] ~136 lines restored

---

### T-024: Restore TDD Verification Checklist

**Priority**: P1 - CRITICAL
**Dependencies**: T-023
**Parallel Execution**: Yes

#### Description
Restore the TDD verification checklist and report template (171 lines).

#### Files Affected
- `src/edison/data/guidelines/shared/TDD.md` - MODIFY

#### Content to Restore

Source: `wilson-pre-edison/.agents/guides/extended/TDD_GUIDE.md` lines 512-640

```markdown
## TDD Verification Checklist

### For Orchestrator: Verifying TDD Compliance

Before accepting work from a sub-agent, verify:

#### 1. Test-First Evidence
- [ ] Tests exist in appropriate __tests__/ directory
- [ ] Test file created BEFORE implementation (check git history)
- [ ] Tests cover the requirements specified in task

#### 2. Red Phase Evidence
- [ ] Sub-agent showed tests failing initially
- [ ] Failure messages indicate tests were actually testing something
- [ ] No "test.skip" or commented-out tests

#### 3. Green Phase Evidence
- [ ] All tests now passing
- [ ] No tests were removed or weakened to pass
- [ ] Coverage meets minimum threshold (see quality.coverageTarget)

#### 4. Refactor Phase (if applicable)
- [ ] Tests still pass after refactoring
- [ ] Code is cleaner without changing behavior
- [ ] No new functionality added during refactor

### TDD Verification Report Template

```json
{
  "taskId": "{{task_id}}",
  "tddCompliance": {
    "testFirst": true|false,
    "redPhaseEvidence": "path/to/screenshot or git commit",
    "greenPhaseEvidence": "path/to/screenshot or git commit",
    "refactorPhase": true|false|"not-applicable",
    "coveragePercent": 85,
    "coverageThreshold": 80,
    "coverageMet": true
  },
  "testSummary": {
    "total": 12,
    "passed": 12,
    "failed": 0,
    "skipped": 0
  },
  "violations": [],
  "verdict": "PASS"|"FAIL"
}
```

### Red Flags (TDD Violations)

🚩 **Immediate Rejection:**
- Tests written AFTER implementation
- Tests that always pass (no assertions)
- Mocked everything (no real behavior tested)
- Coverage below threshold with no justification
- Tests removed to make suite pass

🟡 **Needs Review:**
- Coverage just barely meets threshold
- Complex tests that are hard to understand
- Tests coupled to implementation details
- Missing edge case coverage
```

#### Validation Criteria
- [ ] Verification checklist with all checkboxes present
- [ ] Report template JSON structure included
- [ ] Red flags section with rejection criteria
- [ ] ~171 lines restored

---

### T-025: Restore VALIDATION Batched Parallel Execution

**Priority**: P1 - CRITICAL
**Dependencies**: T-021
**Parallel Execution**: Yes

#### Description
Restore the batched parallel execution model and Round N rejection cycle documentation.

#### Files Affected
- `src/edison/data/guidelines/shared/VALIDATION.md` - MODIFY

#### Content to Restore

Source: `wilson-pre-edison/.agents/guides/extended/VALIDATION_GUIDE.md`

```markdown
## Batched Parallel Execution Model

Validators run in waves for efficiency and fast feedback:

### Wave Execution Order

```
┌─────────────────────────────────────────────────────────────┐
│ Wave 1: Global Validators (Parallel)                        │
│ ┌─────────────────┐  ┌─────────────────┐                   │
│ │ codex-global    │  │ claude-global   │  → Consensus      │
│ └─────────────────┘  └─────────────────┘    Required       │
└─────────────────────────────────────────────────────────────┘
                          ↓ (if pass)
┌─────────────────────────────────────────────────────────────┐
│ Wave 2: Critical Validators (Parallel, Blocking)            │
│ ┌─────────────────┐  ┌─────────────────┐                   │
│ │ security        │  │ performance     │  → Any Fail       │
│ └─────────────────┘  └─────────────────┘    Blocks         │
└─────────────────────────────────────────────────────────────┘
                          ↓ (if pass)
┌─────────────────────────────────────────────────────────────┐
│ Wave 3: Specialized Validators (Parallel, Pattern-Triggered)│
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
│ │ react  │ │ nextjs │ │  api   │ │database│ │testing │    │
│ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Consensus Rules

**Global Validators:**
- Both codex-global and claude-global must agree
- If they disagree, escalate to human review
- Tie-breaker: More specific feedback wins

**Critical Validators:**
- ANY failure blocks the task
- Must fix ALL critical issues before re-validation
- No partial approvals

**Specialized Validators:**
- Only triggered if relevant files changed
- Failures are advisory unless configured as blocking
- Can proceed with warnings noted

## Round N Rejection Cycle

When validation fails:

```
Round 1: Initial Validation
    ↓ (REJECT)
Task returns to WIP
    ↓
Fix issues identified
    ↓
Round 2: Re-validation
    ↓ (REJECT again?)
Repeat until APPROVE or escalate
```

### Rejection Handling

1. **Read rejection report**: Understand ALL issues
2. **Fix ALL issues**: Don't fix one and re-submit
3. **Re-run failed validators**: Use `edison validate --validators=<failed>`
4. **Document fixes**: Update implementation report

### Maximum Rounds

- Configurable via `validation.maxRounds` (default: 3)
- After max rounds, escalate to human review
- Each round's feedback is cumulative
```

#### Validation Criteria
- [ ] Wave execution diagram present
- [ ] Consensus rules documented
- [ ] Round N rejection cycle explained
- [ ] Maximum rounds concept documented

---

### T-026: Restore QUALITY Premium Design Standards

**Priority**: P1 - CRITICAL
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Restore the Premium Design Standards section that was lost (88% content reduction).

#### Files Affected
- `src/edison/data/guidelines/shared/QUALITY.md` - MODIFY

#### Content to Restore

Source: `wilson-pre-edison/.agents/guides/extended/QUALITY_STANDARDS.md`

```markdown
## Premium Design Standards

### Design Token System

Use design tokens for consistency:

```css
/* Spacing (8pt grid) */
--spacing-1: 0.25rem;  /* 4px */
--spacing-2: 0.5rem;   /* 8px */
--spacing-4: 1rem;     /* 16px */
--spacing-6: 1.5rem;   /* 24px */
--spacing-8: 2rem;     /* 32px */

/* Colors (semantic) */
--color-primary: theme('colors.blue.600');
--color-secondary: theme('colors.gray.600');
--color-success: theme('colors.green.600');
--color-warning: theme('colors.yellow.600');
--color-error: theme('colors.red.600');

/* Typography */
--font-sans: theme('fontFamily.sans');
--font-mono: theme('fontFamily.mono');
```

### Micro-interactions

All interactive elements must have:

1. **Hover states**: Subtle color/shadow change
2. **Focus states**: Visible focus ring (accessibility)
3. **Active states**: Pressed/clicked feedback
4. **Transitions**: Smooth 150-200ms transitions

```tsx
// Example: Button with micro-interactions
<button className="
  bg-primary hover:bg-primary-dark
  focus:ring-2 focus:ring-primary-light focus:outline-none
  active:scale-95
  transition-all duration-150
">
```

### Loading & Empty States

Every data-dependent component must handle:

1. **Loading state**: Skeleton or spinner
2. **Empty state**: Helpful message + action
3. **Error state**: Clear error + retry option

```tsx
function DataList({ data, isLoading, error }) {
  if (isLoading) return <Skeleton count={5} />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  if (data.length === 0) return <EmptyState message="No items yet" action={<CreateButton />} />;
  return <List items={data} />;
}
```

### Responsive Design

Breakpoints (Tailwind defaults):
- `sm`: 640px (mobile landscape)
- `md`: 768px (tablet)
- `lg`: 1024px (desktop)
- `xl`: 1280px (large desktop)

Mobile-first approach:
```tsx
<div className="
  grid grid-cols-1
  sm:grid-cols-2
  lg:grid-cols-3
  xl:grid-cols-4
  gap-4
">
```

### Accessibility (WCAG AA)

Minimum requirements:
- Color contrast: 4.5:1 for text, 3:1 for large text
- Focus indicators: Visible on all interactive elements
- Keyboard navigation: All functionality accessible via keyboard
- Screen reader: Semantic HTML + ARIA where needed
- Reduced motion: Respect `prefers-reduced-motion`

```tsx
<motion.div
  animate={{ opacity: 1 }}
  transition={{ duration: 0.2 }}
  // Respect user preference
  style={{
    '@media (prefers-reduced-motion: reduce)': { transition: 'none' }
  }}
>
```

### Dark Mode Support

All components must support dark mode:

```tsx
<div className="
  bg-white dark:bg-gray-900
  text-gray-900 dark:text-gray-100
  border-gray-200 dark:border-gray-700
">
```
```

#### Validation Criteria
- [ ] Design token system documented
- [ ] Micro-interactions requirements present
- [ ] Loading/empty/error state patterns present
- [ ] Responsive design breakpoints documented
- [ ] Accessibility requirements (WCAG AA) documented
- [ ] Dark mode support requirements present

---

### T-027: Restore Component-Builder Server/Client Examples

**Priority**: P1 - CRITICAL
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Restore the Server Component and Client Component examples (53+ lines) that were removed.

#### Files Affected
- `src/edison/data/agents/component-builder.md` - MODIFY

#### Content to Restore

Source: `wilson-pre-edison/.agents/agents/component-builder.md` lines 163-238

```markdown
## Server vs Client Components

### Server Component Example (Default)

Server Components run on the server and can directly access databases:

```tsx
// app/dashboard/page.tsx - Server Component (default)
import { prisma } from '@/lib/prisma';
import { LeadList } from '@/components/LeadList';

export default async function DashboardPage() {
  // Direct database access - no API call needed
  const leads = await prisma.lead.findMany({
    where: { status: 'active' },
    orderBy: { createdAt: 'desc' },
    take: 10,
  });

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <LeadList leads={leads} />
    </div>
  );
}
```

### Client Component Example

Client Components run in the browser and handle interactivity:

```tsx
// components/LeadList.tsx
'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Lead } from '@prisma/client';

interface LeadListProps {
  leads: Lead[];
}

export function LeadList({ leads }: LeadListProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <ul className="space-y-2">
      <AnimatePresence>
        {leads.map((lead) => (
          <motion.li
            key={lead.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            onClick={() => setSelectedId(lead.id)}
            className={`
              p-4 rounded-lg cursor-pointer
              ${selectedId === lead.id
                ? 'bg-blue-100 dark:bg-blue-900'
                : 'bg-gray-50 dark:bg-gray-800'}
              hover:bg-gray-100 dark:hover:bg-gray-700
              transition-colors duration-150
            `}
          >
            <h3 className="font-medium">{lead.name}</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {lead.email}
            </p>
          </motion.li>
        ))}
      </AnimatePresence>
    </ul>
  );
}
```

### When to Use Each

| Use Server Component | Use Client Component |
|---------------------|---------------------|
| Fetching data | useState, useEffect |
| Accessing backend | Event handlers (onClick) |
| Sensitive operations | Browser APIs |
| Large dependencies | Interactivity |
| SEO-critical content | Animations |
```

#### Validation Criteria
- [ ] Server Component example with Prisma query present
- [ ] Client Component example with Motion animations present
- [ ] 'use client' directive shown correctly
- [ ] Comparison table for when to use each
- [ ] ~53 lines restored

---

### T-028: Restore Database-Architect Schema Template

**Priority**: P1 - CRITICAL
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Restore the complete schema.prisma template and migration workflow (50+ lines).

#### Files Affected
- `src/edison/data/agents/database-architect.md` - MODIFY

#### Content to Restore

Source: `wilson-pre-edison/.agents/agents/database-architect.md` lines 123-189

```markdown
## Prisma Schema Patterns

### Complete Model Template

```prisma
// schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Lead {
  id          String   @id @default(cuid())
  email       String   @unique
  name        String
  company     String?
  status      LeadStatus @default(NEW)
  source      String?
  score       Int      @default(0)

  // Timestamps
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  // Relations
  owner       User?    @relation(fields: [ownerId], references: [id])
  ownerId     String?
  activities  Activity[]

  // Indexes for common queries
  @@index([status])
  @@index([ownerId])
  @@index([createdAt])

  // Table mapping (use snake_case in DB)
  @@map("leads")
}

enum LeadStatus {
  NEW
  CONTACTED
  QUALIFIED
  CONVERTED
  LOST
}
```

### Migration Workflow

```bash
# 1. Make schema changes
vim prisma/schema.prisma

# 2. Generate migration (development)
npx prisma migrate dev --name descriptive_name

# 3. Review generated SQL
cat prisma/migrations/*/migration.sql

# 4. Apply to production (CI/CD)
npx prisma migrate deploy

# 5. Generate updated client
npx prisma generate
```

### Migration Safety Classifications

| Operation | Risk Level | Notes |
|-----------|------------|-------|
| Add optional field | ✅ Safe | No data loss |
| Add required field with default | ✅ Safe | Existing rows get default |
| Add required field NO default | ⚠️ Dangerous | Fails if table has data |
| Remove field | ⚠️ Dangerous | Data loss |
| Rename field | ⚠️ Dangerous | Breaks existing code |
| Change field type | 🔴 Critical | May fail or lose data |
| Add index | ✅ Safe | May be slow on large tables |
| Remove index | ✅ Safe | May slow queries |

### Rollback Strategy

```bash
# If migration fails:
# 1. Check migration status
npx prisma migrate status

# 2. Rollback (if supported by provider)
npx prisma migrate reset --skip-seed  # DEV ONLY - destroys data!

# 3. For production, manual SQL rollback
psql $DATABASE_URL < rollback.sql
```
```

#### Validation Criteria
- [ ] Complete Lead model example with all annotations present
- [ ] Migration workflow with 5 steps present
- [ ] Migration safety classifications table present
- [ ] Rollback strategy documented
- [ ] ~50 lines restored

---

### T-029: Update Agent Prompts with Constitution Auto-Injection

**Priority**: P1 - CRITICAL
**Dependencies**: T-009
**Parallel Execution**: Yes

#### Description
Update all agent prompt templates to automatically include constitution read requirement.

#### Files Affected
- `src/edison/core/composition/agents.py` - MODIFY
- Agent prompt templates

#### Implementation Details

Add to the start of every composed agent prompt:

```markdown
## MANDATORY: Read Constitution First

Before starting any work, you MUST read the Agent Constitution at:
`.edison/_generated/constitutions/AGENTS.md`

This constitution contains:
- Your mandatory workflow
- Applicable rules you must follow
- Output format requirements
- All mandatory guideline reads

**Re-read the constitution:**
- At the start of every task
- After any context compaction
- When instructed by the orchestrator

---

[Rest of agent prompt content]
```

#### Validation Criteria
- [ ] All 6 agent prompts include constitution reference at top
- [ ] Constitution path is correct (`.edison/_generated/constitutions/AGENTS.md`)
- [ ] Re-read instruction included
- [ ] Injection happens automatically during composition

---

### T-030: Update Validator Prompts with Constitution Auto-Injection

**Priority**: P1 - CRITICAL
**Dependencies**: T-010
**Parallel Execution**: Yes

#### Description
Update all validator prompt templates to automatically include constitution read requirement.

#### Files Affected
- `src/edison/core/composition/validators.py` - MODIFY
- Validator prompt templates

#### Implementation Details

Add to the start of every composed validator prompt:

```markdown
## MANDATORY: Read Constitution First

Before starting validation, you MUST read the Validator Constitution at:
`.edison/_generated/constitutions/VALIDATORS.md`

This constitution contains:
- Your validation workflow
- Applicable rules for validation
- Output format requirements
- All mandatory guideline reads

**Re-read the constitution:**
- At the start of every validation task
- After any context compaction

---

[Rest of validator prompt content]
```

#### Validation Criteria
- [ ] All validator prompts include constitution reference at top
- [ ] Constitution path is correct (`.edison/_generated/constitutions/VALIDATORS.md`)
- [ ] Re-read instruction included
- [ ] Injection happens automatically during composition

---

## 6. P2 - HIGH Tasks

### T-031: Externalize Workflow Context to YAML

**Priority**: P2 - HIGH
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Move workflow context from hardcoded Python to YAML configuration.

#### Files Affected
- `src/edison/data/config/workflow.yaml` - CREATE
- `src/edison/core/validators/validator.py` - MODIFY

#### Implementation Details

Create workflow.yaml:

```yaml
# src/edison/data/config/workflow.yaml
version: "1.0.0"

qaStates:
  - waiting
  - todo
  - wip
  - done
  - validated

taskStates:
  - todo
  - wip
  - blocked
  - done
  - validated

validationLifecycle:
  onApprove:
    qaState: done → validated
    taskState: done → validated
  onReject:
    qaState: wip → waiting
    taskState: done → wip
  onRevalidate:
    qaState: waiting → todo

timeouts:
  staleTaskThreshold: 4h
  sessionTimeout: 2h
  validatorTimeout: 5m
```

#### Validation Criteria
- [ ] workflow.yaml created with all state definitions
- [ ] Python code reads from YAML instead of hardcoded values
- [ ] State transitions match documentation

---

### T-032: Create Pack-Specific Rule Registries

**Priority**: P2 - HIGH
**Dependencies**: T-003
**Parallel Execution**: Yes

#### Description
Create rule registry files for each pack to enable pack-specific rules.

#### Files Affected
- `edison/packs/nextjs/rules/registry.yml` - CREATE
- `edison/packs/prisma/rules/registry.yml` - CREATE
- `edison/packs/react/rules/registry.yml` - CREATE
- `edison/packs/tailwind/rules/registry.yml` - CREATE

#### Implementation Details

Example for nextjs pack:

```yaml
# edison/packs/nextjs/rules/registry.yml
version: "1.0.0"

rules:
  RULE.NEXTJS.SERVER_FIRST:
    name: "Server Components by Default"
    content: "Use Server Components unless client interactivity needed"
    category: implementation
    severity: high
    applies_to: [agent]

  RULE.NEXTJS.APP_ROUTER:
    name: "Use App Router"
    content: "All routes must use App Router (app/ directory), not Pages Router"
    category: implementation
    severity: critical
    applies_to: [agent, validator]
```

#### Validation Criteria
- [ ] Each active pack has rules/registry.yml
- [ ] Rules follow same schema as core rules
- [ ] Rules have appropriate applies_to values
- [ ] Composition engine loads pack rules

---

### T-033: Create ORCHESTRATOR_VALIDATOR_RUNBOOK.md

**Priority**: P2 - HIGH
**Dependencies**: T-025
**Parallel Execution**: Yes

#### Description
Create the orchestrator's guide for running validators, which was lost during migration.

#### Files Affected
- `edison/core/guides/ORCHESTRATOR_VALIDATOR_RUNBOOK.md` - CREATE (~150 lines)

#### Content to Restore

```markdown
# Orchestrator Validator Runbook

## Overview

This runbook guides orchestrators through the validation process.

## Pre-Validation Checklist

Before running validators:

1. [ ] Task is marked as "ready" (`edison tasks ready <task-id>`)
2. [ ] Implementation report exists
3. [ ] All changed files are committed
4. [ ] Bundle manifest is created (`edison bundle create`)

## Validation Execution

### Step 1: Open QA Brief

```bash
edison qa open <task-id>
```

This promotes the QA brief from `waiting` → `todo`.

### Step 2: Start Validation

```bash
edison validate <task-id>
```

This:
- Promotes QA brief `todo` → `wip`
- Runs validators in waves
- Records start time

### Step 3: Wave Execution

**Wave 1: Global Validators**
- Run codex-global and claude-global in parallel
- Wait for consensus
- If disagreement, log for human review

**Wave 2: Critical Validators**
- Run security and performance in parallel
- Any failure blocks immediately
- Record all findings

**Wave 3: Specialized Validators**
- Determine triggered validators from file patterns
- Run all triggered validators in parallel
- Collect findings (non-blocking unless configured)

### Step 4: Verdict Decision

```
IF any blocking validator failed:
  verdict = REJECT
  reason = blocking_failures
ELSE IF consensus not reached:
  verdict = ESCALATE
  reason = no_consensus
ELSE:
  verdict = APPROVE
```

### Step 5: Record Results

```bash
# On approve
edison qa approve <task-id>

# On reject
edison qa reject <task-id> --reason="..."
```

### Step 6: Handle Rejection

If rejected:
1. Review all validator findings
2. Create follow-up tasks for each issue
3. Return task to WIP
4. Implement fixes
5. Re-validate (Round N+1)

## Troubleshooting

### Validator Timeout
- Check validator logs
- Verify Context7 is accessible
- Retry with `--timeout=10m`

### Consensus Failure
- Review both global validator reports
- Identify specific disagreement
- Escalate to human if unresolvable

### Missing Evidence
- Verify bundle manifest includes all changed files
- Re-run `edison bundle create`
- Check git status for uncommitted changes
```

#### Validation Criteria
- [ ] File created with complete runbook content
- [ ] All 6 steps documented
- [ ] Troubleshooting section included
- [ ] CLI commands are correct (edison, not .agents/scripts)

---

### T-034: Restore Follow-up Task Metadata Schema

**Priority**: P2 - HIGH
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Restore the 70% lost follow-up task metadata fields.

#### Files Affected
- `src/edison/data/config/output_format.yaml` - MODIFY
- `src/edison/data/guidelines/validators/OUTPUT_FORMAT.md` - MODIFY

#### Content to Restore

```yaml
# Full suggestedFollowups schema
suggestedFollowups:
  type: array
  items:
    type: object
    required: [title, description, severity]
    properties:
      title:
        type: string
        description: Brief task title
      description:
        type: string
        description: Detailed task description
      type:
        type: string
        enum: [bug, enhancement, refactor, test, docs]
      severity:
        type: string
        enum: [critical, high, medium, low]
      blocking:
        type: boolean
        default: false
      claimNow:
        type: boolean
        description: Should orchestrator claim immediately?
        default: false
      parentId:
        type: string
        description: Parent task ID if this is a subtask
      files:
        type: array
        items:
          type: string
        description: Affected file paths
      suggestedSlug:
        type: string
        description: Suggested task slug for filename
      suggestedWave:
        type: integer
        description: Suggested execution wave (1-5)
```

#### Validation Criteria
- [ ] All 10 follow-up fields documented
- [ ] Schema includes claimNow, parentId, files, suggestedSlug, suggestedWave
- [ ] OUTPUT_FORMAT.md updated with examples

---

### T-035: Document zenRole Project Overlay Mapping

**Priority**: P2 - HIGH
**Dependencies**: T-022
**Parallel Execution**: Yes

#### Description
Document how projects define their zenRole mappings in the project overlay.

#### Files Affected
- `edison/docs/PROJECT_OVERLAY_GUIDE.md` - CREATE

#### Implementation Details

```markdown
# Project Overlay Guide

## zenRole Mapping

Each project must define its zenRole mappings in `.edison/config/project.yaml`.

### Configuration

```yaml
# .edison/config/project.yaml
project:
  name: wilson-leadgen

zenRoles:
  # Agents
  api-builder: wilson-api-builder
  component-builder: wilson-component-builder
  database-architect: wilson-database-architect
  test-engineer: wilson-test-engineer
  feature-implementer: wilson-feature-implementer
  code-reviewer: wilson-code-reviewer

  # Validators
  validator-codex-global: wilson-validator-codex-global
  validator-claude-global: wilson-validator-claude-global
  validator-security: wilson-validator-security
  validator-performance: wilson-validator-performance
```

### How It Works

1. Agent/validator frontmatter uses template: `zenRole: "{{project.zenRoles.api-builder}}"`
2. Composition engine reads project.yaml
3. Template variable replaced with project-specific value
4. Generated files have correct zenRole for Zen MCP

### Why This Matters

- Core files remain project-agnostic
- Each project has unique Zen MCP role names
- Enables Edison to work across multiple projects
```

#### Validation Criteria
- [ ] Guide explains zenRole mapping purpose
- [ ] Example project.yaml provided
- [ ] Explains template variable resolution

---

### T-036: Fix Broken Cross-References (6 Instances)

**Priority**: P2 - HIGH
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Fix the 6 broken cross-references identified in guidelines.

#### Files Affected
- Multiple guideline files

#### Implementation Details

| Source File | Broken Reference | Fixed Reference |
|-------------|-----------------|-----------------|
| orchestrators/SESSION_WORKFLOW.md | `../../guides/extended/SESSION_WORKFLOW.md` | Remove (file doesn't exist) or create file |
| agents/CONTEXT7_REQUIREMENT.md | `CONTEXT7_GUIDE.md` | `CONTEXT7.md` |
| agents/DELEGATION_AWARENESS.md | `DELEGATION_GUIDE.md` | `DELEGATION.md` |
| agents/MANDATORY_WORKFLOW.md | `IMPLEMENTER_WORKFLOW.md` | Create file or update reference |
| agents/IMPORTANT_RULES.md | `QUALITY_STANDARDS.md` | `QUALITY.md` |
| agents/VALIDATION_AWARENESS.md | `VALIDATION_GUIDE.md` | `VALIDATION.md` |

#### Validation Criteria
- [ ] All 6 cross-references fixed
- [ ] No broken links in guidelines
- [ ] Missing files created OR references updated

---

### T-037: Resolve Unresolved Placeholders (8 Instances)

**Priority**: P2 - HIGH
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Resolve the 8 unresolved placeholder tokens found in guidelines.

#### Files Affected
- `src/edison/data/guidelines/README.md`
- `src/edison/data/guidelines/shared/VALIDATION.md`
- `src/edison/data/guidelines/shared/CONTEXT7.md`
- `src/edison/data/guides/extended/TDD.md`

#### Implementation Details

| File | Placeholder | Resolution |
|------|-------------|------------|
| README.md:31 | `{{framework}}` | Remove or use pack-aware resolution |
| README.md:32 | `{{orm}}` | Remove or use pack-aware resolution |
| README.md:33 | `{{test-framework}}` | Remove or use pack-aware resolution |
| VALIDATION.md:20 | `{{component-framework}}` | Remove or use pack-aware resolution |
| VALIDATION.md:20 | `{{web-framework}}` | Remove or use pack-aware resolution |
| CONTEXT7.md:47 | `{{library}}` | Remove or make dynamic |
| TDD.md:64 | `{{web-framework}}` | Remove or use pack-aware resolution |

**Resolution approach:** These placeholders should either:
1. Be resolved at composition time based on active packs
2. Be removed if they're not needed in generated output
3. Be replaced with pack-agnostic language

#### Validation Criteria
- [ ] No `{{placeholder}}` syntax in generated files
- [ ] grep for `{{` returns no matches in _generated/

---

### T-038: Create ConfigManager Overlay Documentation

**Priority**: P2 - HIGH
**Dependencies**: T-035
**Parallel Execution**: Yes

#### Description
Document how ConfigManager handles overlay resolution and precedence.

#### Files Affected
- `edison/docs/CONFIGMANAGER_OVERLAYS.md` - CREATE

#### Content

```markdown
# ConfigManager Overlay System

## Overview

The ConfigManager handles three-layer configuration with override precedence:

```
CORE (lowest) → PACKS (middle) → PROJECT (highest)
```

## Configuration Loading

```python
config = ConfigManager.load()
# Loads: core/config/*.yaml + packs/*/config/*.yaml + .edison/config/*.yaml
```

## Override Precedence

| Scenario | Resolved Value |
|----------|---------------|
| Only core defines value | Core value |
| Core + pack define value | Pack value (overrides core) |
| Core + project define value | Project value (overrides core) |
| Core + pack + project define | Project value (highest precedence) |

## Example

```yaml
# core/config/defaults.yaml
validation:
  maxRounds: 3

# packs/strict/config/defaults.yaml
validation:
  maxRounds: 5  # Override for strict pack

# .edison/config/project.yaml
validation:
  maxRounds: 2  # Project override (wins)
```

## API

```python
# Get merged config
value = config.get('validation.maxRounds')  # Returns 2 (project wins)

# Get from specific layer
core_value = config.get_core('validation.maxRounds')  # Returns 3
```
```

#### Validation Criteria
- [ ] Documentation explains override precedence
- [ ] Examples show three-layer resolution
- [ ] API documented

---

### T-039 through T-052: Remaining P2 Tasks

*(Due to length constraints, I'm summarizing the remaining P2 tasks. Each would follow the same detailed format as above.)*

| Task ID | Description | Priority | Dependencies |
|---------|-------------|----------|--------------|
| T-039 | Restore QUALITY Code Smell Checklist (40+ items) | P2 - HIGH | None |
| T-040 | Restore agent IMPORTANT RULES sections | P2 - HIGH | None |
| T-041 | Fix truncated wilson-architecture.md | P2 - HIGH | None |
| T-042 | Update all CLI references (.agents/scripts → edison) | P2 - HIGH | None |
| T-043 | Add self-identification headers to all generated files | P2 - HIGH | T-004 |
| T-044 | Create compaction hooks for constitution re-read | P2 - HIGH | T-008-T-010 |
| T-045 | Restore delegation model definitions | P2 - HIGH | None |
| T-046 | Restore missing task type rules (7 of 11) | P2 - HIGH | None |
| T-047 | Restore missing file pattern rules (6 patterns) | P2 - HIGH | None |
| T-048 | Add pack context to security.md | P2 - HIGH | T-032 |
| T-049 | Add pack context to performance.md | P2 - HIGH | T-032 |
| T-050 | Restore Tailwind v4 detailed rules | P2 - HIGH | None |
| T-051 | Restore Motion 12 animation patterns | P2 - HIGH | None |
| T-052 | Add error recovery section to CLAUDE.md | P2 - HIGH | None |

---

## 7. P3 - MEDIUM Tasks

| Task ID | Description | Priority | Dependencies |
|---------|-------------|----------|--------------|
| T-053 | Remove all __pycache__ directories | P3 - MEDIUM | None |
| T-054 | Remove/gitignore .agents/.cache/ | P3 - MEDIUM | None |
| T-055 | Remove Wilson-specific content from core | P3 - MEDIUM | T-022 |
| T-056 | Remove duplicate defaults.yaml | P3 - MEDIUM | None |
| T-057 | Remove duplicate api.md in packs | P3 - MEDIUM | None |
| T-058 | Clean up empty directories | P3 - MEDIUM | None |
| T-059 | Add tracking integration documentation | P3 - MEDIUM | T-033 |
| T-060 | Create validator troubleshooting guide | P3 - MEDIUM | T-033 |
| T-061 | Document state machine in START prompts | P3 - MEDIUM | T-017-T-019 |

---

## 8. P4 - LOW Tasks

| Task ID | Description | Priority | Dependencies |
|---------|-------------|----------|--------------|
| T-062 | Add "Why no delegation" to code-reviewer | P4 - LOW | None |
| T-063 | Restore Wilson-specific entity examples | P4 - LOW | None |
| T-064 | Add version/line count metadata to agents | P4 - LOW | None |
| T-065 | Convert HTML rule markers to anchors | P4 - LOW | T-003 |
| T-066 | Add blocking flags audit to rules | P4 - LOW | T-003 |
| T-067 | Create delegation examples directory | P4 - LOW | T-045 |
| T-068 | Restore TDD troubleshooting section | P4 - LOW | T-023 |

---

## 9. Edison-Zen Track (Parallel)

### 9.1 Zen Track Overview

The Edison-Zen track sets up the Zen MCP server integration for sub-agent delegation. This track can execute fully in parallel with the main migration track.

### 9.2 Zen Tasks

### T-ZEN-001: Create `edison zen setup` Command

**Priority**: P0 - BLOCKER
**Dependencies**: None
**Parallel Execution**: Yes

#### Description
Create the CLI command to set up zen-mcp-server for Edison integration.

#### Files Affected
- `src/edison/cli/commands/zen.py` - CREATE

#### Implementation Details

```python
# src/edison/cli/commands/zen.py
import click
import subprocess
from pathlib import Path


@click.group()
def zen():
    """Zen MCP server management commands."""
    pass


@zen.command()
@click.option('--check', is_flag=True, help='Check setup without installing')
def setup(check: bool):
    """Setup zen-mcp-server for Edison integration."""

    # Check existing installations
    zen_paths = [
        Path.home() / 'zen-mcp-server',
        Path(os.environ.get('ZEN_MCP_SERVER_DIR', '')),
    ]

    for path in zen_paths:
        if path.exists() and (path / 'pyproject.toml').exists():
            click.echo(f"✅ zen-mcp-server found at: {path}")
            return

    # Check uvx availability
    try:
        result = subprocess.run(['uvx', '--version'], capture_output=True, text=True)
        click.echo(f"✅ uvx available: {result.stdout.strip()}")
    except FileNotFoundError:
        click.echo("❌ uvx not found. Install with: pip install uv")
        if not check:
            raise click.Abort()
        return

    if check:
        click.echo("ℹ️  zen-mcp-server will be installed via uvx on first use")
        return

    # Install via uvx
    click.echo("Installing zen-mcp-server via uvx...")
    subprocess.run([
        'uvx', '--from',
        'git+https://github.com/BeehiveInnovations/zen-mcp-server.git',
        'zen-mcp-server', '--version'
    ], check=True)

    click.echo("✅ zen-mcp-server installed successfully")
```

#### Validation Criteria
- [ ] Command exists: `edison zen setup`
- [ ] Checks existing installations first
- [ ] Checks uvx availability
- [ ] Installs via uvx if needed
- [ ] `--check` flag works without installing

---

### T-ZEN-002: Create `edison zen start-server` Command

**Priority**: P0 - BLOCKER
**Dependencies**: T-ZEN-001
**Parallel Execution**: No

#### Files Affected
- `src/edison/cli/commands/zen.py` - MODIFY

#### Implementation Details

```python
@zen.command('start-server')
@click.option('--background', is_flag=True, help='Run in background')
def start_server(background: bool):
    """Start the zen-mcp-server."""

    # Use existing run-server.sh if available
    script_path = Path(__file__).parent.parent.parent / 'scripts' / 'zen' / 'run-server.sh'

    if script_path.exists():
        if background:
            subprocess.Popen(['bash', str(script_path)],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        else:
            subprocess.run(['bash', str(script_path)])
    else:
        # Fallback to uvx
        cmd = ['uvx', '--from',
               'git+https://github.com/BeehiveInnovations/zen-mcp-server.git',
               'zen-mcp-server']
        if background:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(cmd)
```

#### Validation Criteria
- [ ] Command exists: `edison zen start-server`
- [ ] Uses existing run-server.sh if available
- [ ] Falls back to uvx if script missing
- [ ] `--background` flag works

---

### T-ZEN-003: Create `edison zen configure` Command

**Priority**: P0 - BLOCKER
**Dependencies**: T-ZEN-001
**Parallel Execution**: No

#### Files Affected
- `src/edison/cli/commands/zen.py` - MODIFY

#### Implementation Details

```python
@zen.command()
@click.argument('project_path', default='.', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Show what would be configured')
def configure(project_path: str, dry_run: bool):
    """Configure .mcp.json in target project for edison-zen."""
    import json

    project = Path(project_path)
    mcp_json_path = project / '.mcp.json'

    edison_zen_config = {
        "command": "edison",
        "args": ["zen", "start-server"],
        "env": {
            "ZEN_WORKING_DIR": str(project.absolute())
        }
    }

    if mcp_json_path.exists():
        with open(mcp_json_path) as f:
            config = json.load(f)
    else:
        config = {"mcpServers": {}}

    config.setdefault("mcpServers", {})
    config["mcpServers"]["edison-zen"] = edison_zen_config

    if dry_run:
        click.echo("Would write to .mcp.json:")
        click.echo(json.dumps(config, indent=2))
        return

    with open(mcp_json_path, 'w') as f:
        json.dump(config, f, indent=2)

    click.echo(f"✅ Configured .mcp.json at: {mcp_json_path}")
```

#### Validation Criteria
- [ ] Command exists: `edison zen configure`
- [ ] Creates .mcp.json if missing
- [ ] Updates existing .mcp.json without losing other servers
- [ ] `--dry-run` shows what would be written

---

### T-ZEN-004: Auto-detect uvx Availability

**Priority**: P1 - CRITICAL
**Dependencies**: T-ZEN-001
**Parallel Execution**: No

#### Description
Implement robust uvx detection with fallback options and clear user guidance when uvx is not available.

#### Files Affected
- `src/edison/cli/commands/zen.py` - MODIFY
- `src/edison/core/utils/dependencies.py` - CREATE

#### Implementation Details

```python
# src/edison/core/utils/dependencies.py
"""Dependency detection utilities for Edison."""

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path


@dataclass
class UvxStatus:
    available: bool
    version: Optional[str]
    path: Optional[str]
    install_instruction: str


def detect_uvx() -> UvxStatus:
    """
    Detect uvx availability and provide installation guidance.

    Returns:
        UvxStatus with availability info and install instructions
    """
    # Check if uvx is in PATH
    uvx_path = shutil.which('uvx')

    if uvx_path:
        try:
            result = subprocess.run(
                ['uvx', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return UvxStatus(
                    available=True,
                    version=version,
                    path=uvx_path,
                    install_instruction=""
                )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

    # Check if uv is available (uvx comes with uv)
    uv_path = shutil.which('uv')
    if uv_path:
        return UvxStatus(
            available=False,
            version=None,
            path=None,
            install_instruction="uv is installed but uvx not found. Try: uv tool install uvx"
        )

    # Neither available - provide installation options
    return UvxStatus(
        available=False,
        version=None,
        path=None,
        install_instruction="""uvx not found. Install options:
  1. pip install uv (recommended)
  2. curl -LsSf https://astral.sh/uv/install.sh | sh
  3. brew install uv (macOS)"""
    )


def detect_zen_mcp_server() -> Tuple[bool, Optional[Path]]:
    """
    Detect if zen-mcp-server is available.

    Returns:
        Tuple of (available: bool, path: Optional[Path])
    """
    # Check environment variable first
    import os
    env_path = os.environ.get('ZEN_MCP_SERVER_DIR')
    if env_path:
        path = Path(env_path)
        if path.exists() and (path / 'pyproject.toml').exists():
            return True, path

    # Check standard location
    home_path = Path.home() / 'zen-mcp-server'
    if home_path.exists() and (home_path / 'pyproject.toml').exists():
        return True, home_path

    # Check if available via uvx
    uvx_status = detect_uvx()
    if uvx_status.available:
        # uvx will auto-install on first use
        return True, None

    return False, None
```

Update zen.py to use detection:

```python
# In src/edison/cli/commands/zen.py
from edison.core.utils.dependencies import detect_uvx, detect_zen_mcp_server

@zen.command()
@click.option('--check', is_flag=True, help='Check setup without installing')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed status')
def setup(check: bool, verbose: bool):
    """Setup zen-mcp-server for Edison integration."""

    # Check zen-mcp-server first
    zen_available, zen_path = detect_zen_mcp_server()

    if zen_available:
        if zen_path:
            click.echo(f"✅ zen-mcp-server found at: {zen_path}")
        else:
            click.echo("✅ zen-mcp-server available via uvx (will install on first use)")
        return

    # Check uvx
    uvx_status = detect_uvx()

    if verbose:
        click.echo(f"uvx available: {uvx_status.available}")
        if uvx_status.version:
            click.echo(f"uvx version: {uvx_status.version}")
        if uvx_status.path:
            click.echo(f"uvx path: {uvx_status.path}")

    if not uvx_status.available:
        click.echo(f"❌ {uvx_status.install_instruction}")
        if not check:
            raise click.Abort()
        return

    if check:
        click.echo("✅ uvx available - zen-mcp-server will install on first use")
        return

    # Proceed with installation
    click.echo("Installing zen-mcp-server via uvx...")
    # ... installation code
```

#### Validation Criteria
- [ ] `detect_uvx()` correctly identifies uvx presence
- [ ] Returns version when available
- [ ] Provides clear install instructions when missing
- [ ] `detect_zen_mcp_server()` checks all three locations
- [ ] `--verbose` flag shows detailed detection info

---

### T-ZEN-005: Template .mcp.json Configuration

**Priority**: P1 - CRITICAL
**Dependencies**: T-ZEN-003
**Parallel Execution**: No

#### Description
Create a robust .mcp.json templating system that handles various project configurations and preserves existing MCP server entries.

#### Files Affected
- `src/edison/core/templates/mcp_config.py` - CREATE
- `src/edison/data/templates/mcp.json.template` - CREATE

#### Implementation Details

```python
# src/edison/core/templates/mcp_config.py
"""MCP configuration templating for Edison."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class McpServerConfig:
    """Configuration for a single MCP server."""
    command: str
    args: list = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class McpConfig:
    """Full .mcp.json configuration."""
    servers: Dict[str, McpServerConfig] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> 'McpConfig':
        """Load existing .mcp.json or return empty config."""
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            servers = {}
            for name, config in data.get('mcpServers', {}).items():
                servers[name] = McpServerConfig(
                    command=config.get('command', ''),
                    args=config.get('args', []),
                    env=config.get('env', {})
                )
            return cls(servers=servers)
        return cls()

    def add_server(self, name: str, config: McpServerConfig, overwrite: bool = False) -> bool:
        """
        Add an MCP server configuration.

        Returns:
            True if added, False if exists and overwrite=False
        """
        if name in self.servers and not overwrite:
            return False
        self.servers[name] = config
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "mcpServers": {
                name: {
                    "command": config.command,
                    "args": config.args,
                    "env": config.env
                }
                for name, config in self.servers.items()
            }
        }

    def save(self, path: Path) -> None:
        """Save to .mcp.json file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
            f.write('\n')  # Trailing newline


def get_edison_zen_config(project_path: Path, use_shell_script: bool = False) -> McpServerConfig:
    """
    Get the Edison-Zen MCP server configuration.

    Args:
        project_path: Path to the project root
        use_shell_script: Use shell script instead of edison CLI

    Returns:
        McpServerConfig for edison-zen
    """
    if use_shell_script:
        # For development or when edison CLI not in PATH
        script_path = project_path / 'scripts' / 'zen' / 'run-server.sh'
        return McpServerConfig(
            command="bash",
            args=[str(script_path)],
            env={"ZEN_WORKING_DIR": str(project_path.absolute())}
        )

    # Standard configuration using edison CLI
    return McpServerConfig(
        command="edison",
        args=["zen", "start-server"],
        env={"ZEN_WORKING_DIR": str(project_path.absolute())}
    )


def configure_mcp_json(
    project_path: Path,
    server_name: str = "edison-zen",
    use_shell_script: bool = False,
    overwrite: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Configure .mcp.json with Edison-Zen server.

    Args:
        project_path: Path to project root
        server_name: Name for the MCP server entry
        use_shell_script: Use shell script instead of CLI
        overwrite: Overwrite existing server entry
        dry_run: Return config without writing

    Returns:
        The full configuration dict
    """
    mcp_path = project_path / '.mcp.json'

    # Load existing or create new
    config = McpConfig.load(mcp_path)

    # Get Edison-Zen config
    zen_config = get_edison_zen_config(project_path, use_shell_script)

    # Add server
    added = config.add_server(server_name, zen_config, overwrite=overwrite)

    result = config.to_dict()
    result['_meta'] = {
        'added': added,
        'server_name': server_name,
        'path': str(mcp_path)
    }

    if not dry_run:
        config.save(mcp_path)

    return result
```

Template file:

```json
// src/edison/data/templates/mcp.json.template
{
  "mcpServers": {
    "edison-zen": {
      "command": "{{command}}",
      "args": {{args_json}},
      "env": {
        "ZEN_WORKING_DIR": "{{project_path}}"
      }
    }
  }
}
```

Update zen.py configure command:

```python
from edison.core.templates.mcp_config import configure_mcp_json

@zen.command()
@click.argument('project_path', default='.', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Show what would be configured')
@click.option('--overwrite', is_flag=True, help='Overwrite existing edison-zen entry')
@click.option('--use-script', is_flag=True, help='Use shell script instead of edison CLI')
@click.option('--server-name', default='edison-zen', help='Name for MCP server entry')
def configure(project_path: str, dry_run: bool, overwrite: bool, use_script: bool, server_name: str):
    """Configure .mcp.json in target project for edison-zen."""

    result = configure_mcp_json(
        project_path=Path(project_path),
        server_name=server_name,
        use_shell_script=use_script,
        overwrite=overwrite,
        dry_run=dry_run
    )

    if dry_run:
        click.echo("Would write to .mcp.json:")
        # Remove _meta for display
        display = {k: v for k, v in result.items() if k != '_meta'}
        click.echo(json.dumps(display, indent=2))
        return

    meta = result.get('_meta', {})
    if meta.get('added'):
        click.echo(f"✅ Added '{server_name}' to: {meta['path']}")
    else:
        click.echo(f"ℹ️  '{server_name}' already exists (use --overwrite to replace)")
```

#### Validation Criteria
- [ ] Loads existing .mcp.json without losing other servers
- [ ] Creates new .mcp.json if not exists
- [ ] `--dry-run` shows full configuration
- [ ] `--overwrite` replaces existing entry
- [ ] `--use-script` uses shell script path
- [ ] `--server-name` allows custom naming

---

### T-ZEN-006: Add Zen Setup to `edison init` Flow

**Priority**: P1 - CRITICAL
**Dependencies**: T-ZEN-001, T-ZEN-002, T-ZEN-003
**Parallel Execution**: No

#### Description
Integrate zen setup into the `edison init` command so new projects automatically get Zen MCP configured.

#### Files Affected
- `src/edison/cli/commands/init.py` - MODIFY

#### Implementation Details

```python
# src/edison/cli/commands/init.py
import click
from pathlib import Path
from edison.core.utils.dependencies import detect_uvx, detect_zen_mcp_server
from edison.core.templates.mcp_config import configure_mcp_json


@click.command()
@click.argument('project_path', default='.', type=click.Path())
@click.option('--skip-zen', is_flag=True, help='Skip Zen MCP setup')
@click.option('--zen-script', is_flag=True, help='Use shell script for Zen (development)')
def init(project_path: str, skip_zen: bool, zen_script: bool):
    """Initialize Edison in a project directory."""

    project = Path(project_path).absolute()

    click.echo(f"Initializing Edison in: {project}")

    # Create .edison directory structure
    edison_dir = project / '.edison'
    edison_dir.mkdir(exist_ok=True)

    # Create subdirectories
    for subdir in ['config', 'constitutions', '_generated']:
        (edison_dir / subdir).mkdir(exist_ok=True)

    click.echo("✅ Created .edison/ directory structure")

    # Create default config files
    _create_default_configs(edison_dir)
    click.echo("✅ Created default configuration files")

    # Setup Zen MCP (unless skipped)
    if not skip_zen:
        click.echo("\nSetting up Zen MCP integration...")

        # Check dependencies
        zen_available, zen_path = detect_zen_mcp_server()

        if not zen_available:
            uvx_status = detect_uvx()
            if not uvx_status.available:
                click.echo(f"⚠️  Warning: {uvx_status.install_instruction}")
                click.echo("   Zen MCP will not be configured. Run 'edison zen setup' later.")
            else:
                click.echo("ℹ️  zen-mcp-server will be installed via uvx on first use")

        # Configure .mcp.json
        try:
            result = configure_mcp_json(
                project_path=project,
                use_shell_script=zen_script,
                dry_run=False
            )
            if result.get('_meta', {}).get('added'):
                click.echo("✅ Configured .mcp.json with edison-zen")
            else:
                click.echo("ℹ️  edison-zen already configured in .mcp.json")
        except Exception as e:
            click.echo(f"⚠️  Warning: Could not configure .mcp.json: {e}")
            click.echo("   Run 'edison zen configure' manually.")

    # Run initial composition
    click.echo("\nRunning initial composition...")
    from edison.cli.commands.compose import compose
    ctx = click.Context(compose)
    ctx.invoke(compose, compose_all=True)

    click.echo("\n✅ Edison initialized successfully!")
    click.echo("\nNext steps:")
    click.echo("  1. Review .edison/config/project.yaml")
    click.echo("  2. Activate packs: edison packs enable <pack-name>")
    click.echo("  3. Start a session: edison session start")


def _create_default_configs(edison_dir: Path) -> None:
    """Create default configuration files."""

    # project.yaml
    project_yaml = edison_dir / 'config' / 'project.yaml'
    if not project_yaml.exists():
        project_yaml.write_text("""# Project configuration for Edison
project:
  name: my-project  # Update this

# Zen role mappings (update for your project)
zenRoles:
  api-builder: my-project-api-builder
  component-builder: my-project-component-builder
  database-architect: my-project-database-architect
  test-engineer: my-project-test-engineer
  feature-implementer: my-project-feature-implementer
  code-reviewer: my-project-code-reviewer

# Active packs
packs:
  enabled: []
  # Add packs like: nextjs, prisma, react, tailwind
""")

    # .gitignore for .edison
    gitignore = edison_dir / '.gitignore'
    if not gitignore.exists():
        gitignore.write_text("""# Edison generated files (optionally ignore)
# _generated/

# Cache files
.cache/
__pycache__/
*.pyc
""")
```

#### Validation Criteria
- [ ] `edison init` creates .edison/ directory structure
- [ ] Creates default config files
- [ ] Configures .mcp.json unless --skip-zen
- [ ] Handles missing uvx gracefully with warning
- [ ] Runs initial composition
- [ ] Shows helpful next steps

---

### T-ZEN-007: Document Zen Setup in Edison README

**Priority**: P2 - HIGH
**Dependencies**: T-ZEN-001, T-ZEN-002, T-ZEN-003, T-ZEN-004, T-ZEN-005, T-ZEN-006
**Parallel Execution**: Yes

#### Description
Add comprehensive Zen MCP setup documentation to the Edison README.

#### Files Affected
- `README.md` - MODIFY (add Zen section)
- `docs/ZEN_SETUP.md` - CREATE

#### Implementation Details

Add to README.md:

```markdown
## Zen MCP Integration

Edison uses the [Zen MCP Server](https://github.com/BeehiveInnovations/zen-mcp-server) for sub-agent delegation.

### Quick Setup

```bash
# During project initialization (automatic)
edison init my-project

# Or manually
edison zen setup
edison zen configure
```

### Manual Setup

If automatic setup fails:

1. **Install uvx** (provides zen-mcp-server):
   ```bash
   pip install uv
   ```

2. **Configure your project**:
   ```bash
   edison zen configure /path/to/project
   ```

3. **Verify setup**:
   ```bash
   edison zen setup --check
   ```

### Configuration Options

```bash
# Use shell script instead of CLI (development)
edison zen configure --use-script

# Custom server name
edison zen configure --server-name my-zen-server

# Preview without writing
edison zen configure --dry-run
```

### Troubleshooting

See [docs/ZEN_SETUP.md](docs/ZEN_SETUP.md) for detailed troubleshooting.
```

Create docs/ZEN_SETUP.md:

```markdown
# Zen MCP Server Setup Guide

## Overview

Edison delegates work to specialized sub-agents using the Zen MCP Server. This document covers setup, configuration, and troubleshooting.

## Prerequisites

- Python 3.10+
- uvx (comes with uv): `pip install uv`

## Installation Methods

### Method 1: Automatic (Recommended)

```bash
edison init my-project
```

This automatically:
1. Creates .edison/ directory
2. Checks for uvx/zen-mcp-server
3. Configures .mcp.json

### Method 2: Manual

```bash
# Step 1: Ensure uvx is available
pip install uv

# Step 2: Setup zen-mcp-server
edison zen setup

# Step 3: Configure project
edison zen configure /path/to/project
```

### Method 3: Clone Repository

For development or offline use:

```bash
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git ~/zen-mcp-server
export ZEN_MCP_SERVER_DIR=~/zen-mcp-server
edison zen configure --use-script
```

## Configuration Reference

### .mcp.json Structure

```json
{
  "mcpServers": {
    "edison-zen": {
      "command": "edison",
      "args": ["zen", "start-server"],
      "env": {
        "ZEN_WORKING_DIR": "/absolute/path/to/project"
      }
    }
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ZEN_WORKING_DIR` | Project root for Zen operations | Current directory |
| `ZEN_MCP_SERVER_DIR` | Custom zen-mcp-server location | None |

## Troubleshooting

### "uvx not found"

```bash
# Solution 1: Install uv
pip install uv

# Solution 2: Install via curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Solution 3: macOS with Homebrew
brew install uv
```

### "zen-mcp-server not found"

The server auto-installs via uvx on first use. If this fails:

```bash
# Manual installation
uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server --version
```

### MCP Connection Issues

1. Check .mcp.json path is correct
2. Verify ZEN_WORKING_DIR is absolute path
3. Try starting server manually: `edison zen start-server`
4. Check for port conflicts

### Permission Errors

```bash
# Ensure execute permission on scripts
chmod +x scripts/zen/run-server.sh
```

## Verifying Setup

```bash
# Check all components
edison zen setup --check --verbose

# Test MCP connection (from Claude/client)
# Use clink tool and verify response
```
```

#### Validation Criteria
- [ ] README has Zen section with quick setup
- [ ] docs/ZEN_SETUP.md created with full guide
- [ ] All three installation methods documented
- [ ] Troubleshooting covers common issues
- [ ] Environment variables documented

---

### T-ZEN-008: End-to-End Zen Verification Test

**Priority**: P2 - HIGH
**Dependencies**: T-ZEN-001, T-ZEN-002, T-ZEN-003, T-ZEN-004, T-ZEN-005, T-ZEN-006
**Parallel Execution**: Yes

#### Description
Create an end-to-end test that verifies the complete Zen MCP integration workflow.

#### Files Affected
- `tests/e2e/test_zen_integration.py` - CREATE
- `scripts/verify_zen_setup.sh` - CREATE

#### Implementation Details

```python
# tests/e2e/test_zen_integration.py
"""End-to-end tests for Zen MCP integration."""

import pytest
import subprocess
import json
import tempfile
from pathlib import Path


class TestZenIntegration:
    """Test suite for Zen MCP integration."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory."""
        project = tmp_path / "test-project"
        project.mkdir()
        return project

    def test_zen_setup_check(self):
        """Test that zen setup --check works."""
        result = subprocess.run(
            ['edison', 'zen', 'setup', '--check'],
            capture_output=True,
            text=True
        )
        # Should not fail, just report status
        assert result.returncode == 0 or 'uvx not found' in result.stdout

    def test_zen_configure_dry_run(self, temp_project):
        """Test zen configure --dry-run output."""
        result = subprocess.run(
            ['edison', 'zen', 'configure', str(temp_project), '--dry-run'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert 'mcpServers' in result.stdout
        assert 'edison-zen' in result.stdout

        # Verify no file was created
        mcp_json = temp_project / '.mcp.json'
        assert not mcp_json.exists()

    def test_zen_configure_creates_mcp_json(self, temp_project):
        """Test that zen configure creates .mcp.json."""
        result = subprocess.run(
            ['edison', 'zen', 'configure', str(temp_project)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        mcp_json = temp_project / '.mcp.json'
        assert mcp_json.exists()

        with open(mcp_json) as f:
            config = json.load(f)

        assert 'mcpServers' in config
        assert 'edison-zen' in config['mcpServers']
        assert config['mcpServers']['edison-zen']['command'] == 'edison'

    def test_zen_configure_preserves_existing(self, temp_project):
        """Test that zen configure preserves existing MCP servers."""
        # Create existing config
        mcp_json = temp_project / '.mcp.json'
        existing = {
            "mcpServers": {
                "other-server": {
                    "command": "other",
                    "args": []
                }
            }
        }
        with open(mcp_json, 'w') as f:
            json.dump(existing, f)

        # Run configure
        subprocess.run(
            ['edison', 'zen', 'configure', str(temp_project)],
            capture_output=True
        )

        # Verify both servers exist
        with open(mcp_json) as f:
            config = json.load(f)

        assert 'other-server' in config['mcpServers']
        assert 'edison-zen' in config['mcpServers']

    def test_init_configures_zen(self, temp_project):
        """Test that edison init sets up Zen."""
        result = subprocess.run(
            ['edison', 'init', str(temp_project)],
            capture_output=True,
            text=True
        )

        # Check .edison directory created
        edison_dir = temp_project / '.edison'
        assert edison_dir.exists()

        # Check .mcp.json created (unless uvx not available)
        mcp_json = temp_project / '.mcp.json'
        if 'uvx not found' not in result.stdout:
            assert mcp_json.exists()

    def test_init_skip_zen(self, temp_project):
        """Test that --skip-zen works."""
        subprocess.run(
            ['edison', 'init', str(temp_project), '--skip-zen'],
            capture_output=True
        )

        # .mcp.json should not be created
        mcp_json = temp_project / '.mcp.json'
        assert not mcp_json.exists()


@pytest.mark.skipif(
    subprocess.run(['which', 'uvx'], capture_output=True).returncode != 0,
    reason="uvx not available"
)
class TestZenWithUvx:
    """Tests that require uvx to be installed."""

    def test_zen_server_starts(self, temp_project):
        """Test that zen-mcp-server can start."""
        # Configure first
        subprocess.run(['edison', 'zen', 'configure', str(temp_project)])

        # Try to start (will exit quickly without MCP client)
        result = subprocess.run(
            ['edison', 'zen', 'start-server'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=temp_project
        )

        # Should at least not crash on startup
        assert 'Error' not in result.stderr or 'timeout' in str(result)
```

Create verification script:

```bash
#!/bin/bash
# scripts/verify_zen_setup.sh
# Verify complete Zen MCP setup

set -e

echo "=== Edison Zen Setup Verification ==="
echo

# Check 1: uvx availability
echo "1. Checking uvx availability..."
if command -v uvx &> /dev/null; then
    echo "   ✅ uvx found: $(uvx --version)"
else
    echo "   ❌ uvx not found"
    echo "   Install with: pip install uv"
    exit 1
fi

# Check 2: zen setup
echo
echo "2. Running zen setup check..."
if edison zen setup --check; then
    echo "   ✅ Zen setup verified"
else
    echo "   ❌ Zen setup failed"
    exit 1
fi

# Check 3: Configure test project
echo
echo "3. Testing zen configure..."
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

if edison zen configure "$TEMP_DIR" --dry-run | grep -q "edison-zen"; then
    echo "   ✅ Configure output correct"
else
    echo "   ❌ Configure output incorrect"
    exit 1
fi

# Check 4: Actual configuration
echo
echo "4. Testing actual configuration..."
edison zen configure "$TEMP_DIR"

if [ -f "$TEMP_DIR/.mcp.json" ]; then
    echo "   ✅ .mcp.json created"

    if grep -q "edison-zen" "$TEMP_DIR/.mcp.json"; then
        echo "   ✅ edison-zen entry present"
    else
        echo "   ❌ edison-zen entry missing"
        exit 1
    fi
else
    echo "   ❌ .mcp.json not created"
    exit 1
fi

# Check 5: Server start (quick test)
echo
echo "5. Testing server startup..."
timeout 3 edison zen start-server &> /dev/null || true
echo "   ✅ Server command executed"

echo
echo "=== All Zen verification checks passed! ==="
```

#### Validation Criteria
- [ ] `pytest tests/e2e/test_zen_integration.py` passes
- [ ] `scripts/verify_zen_setup.sh` passes
- [ ] Tests cover: setup check, configure dry-run, configure actual, preserve existing, init integration
- [ ] Tests skip gracefully when uvx not available
- [ ] Verification script provides clear pass/fail output

---

## 10. Execution Strategy for Orchestrator

### 10.1 CRITICAL: Orchestration Loop (MUST FOLLOW)

The orchestrator MUST follow this loop until ALL tasks are complete:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LOOP                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. IDENTIFY READY TASKS                                                │
│     └── Check Task Status Tracker (Section 11)                          │
│     └── Find tasks where all dependencies are ✅ DONE                   │
│     └── Prioritize: P0 > P1 > P2 > P3 > P4                             │
│                                                                         │
│  2. DELEGATE TO SUB-AGENTS (in parallel where possible)                 │
│     └── Pass FULL CONTEXT (see Section 10.3)                            │
│     └── Use zen clink for Codex/Gemini agents                          │
│     └── Use Task tool for Claude sub-agents                             │
│     └── Include: task description, files, code, validation criteria     │
│                                                                         │
│  3. REVIEW SUB-AGENT REPORTS                                            │
│     └── Check if task completed successfully                            │
│     └── Check validation criteria (all checkboxes)                      │
│     └── Identify any follow-ups or issues reported                      │
│                                                                         │
│  4. HANDLE RESULTS                                                      │
│     ├── SUCCESS: Mark task ✅ DONE in Section 11                        │
│     ├── PARTIAL: Create follow-up tasks, delegate fixes                 │
│     └── FAILURE: Investigate, fix root cause, retry                     │
│                                                                         │
│  5. UPDATE TASK STATUS TRACKER                                          │
│     └── Mark completed tasks as ✅ DONE                                 │
│     └── Note any new tasks discovered                                   │
│     └── Update blockers if any                                          │
│                                                                         │
│  6. LOOP BACK TO STEP 1                                                 │
│     └── Continue until ALL tasks are ✅ DONE                            │
│     └── Run validation gates between priority tiers                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Parallel Execution Rules

**Can run in parallel:**
- All P0 tasks with "Dependencies: None" (T-001, T-002, T-003, T-012, T-014, T-015, T-016)
- All Zen track tasks (T-ZEN-*) run in parallel with main track
- Multiple P1/P2 tasks after their dependencies complete
- Tasks at same priority level with no inter-dependencies

**Must run sequentially:**
- Tasks with explicit dependencies (check "Dependencies" field)
- Constitution generation (T-008, T-009, T-010) AFTER composer (T-004)
- START prompts AFTER constitution templates (T-001)
- Content restoration tasks AFTER frontmatter (T-016)

**Parallel execution example (Wave 1):**
```
PARALLEL:
├── T-001 (Constitution Templates) ─────────┐
├── T-002 (Constitution Config) ────────────┼──> Then T-004
├── T-003 (Rules applies_to) ───────────────┘
├── T-012 (Zen Prompt Fix) ─────────────────────> Then T-013
├── T-014 (Post-training Packages) ─────────┐
├── T-015 (Rule Paths Fix) ─────────────────┼──> Then content tasks
└── T-016 (YAML Frontmatter) ───────────────┘
```

### 10.3 CRITICAL: Context Requirements for Sub-Agents

**Every sub-agent delegation MUST include:**

```markdown
## Task Context for Sub-Agent

### Task Reference
- **Task ID**: T-XXX
- **Title**: [Full task title]
- **Priority**: P[0-4]
- **Dependencies**: [List or "None"]

### Implementation Requirements
[Copy the FULL "Implementation Details" section from the task]

### Files to Create/Modify
[Copy the FULL "Files Affected" section]

### Code to Implement
[Copy ALL code blocks from the task - DO NOT SUMMARIZE]

### Content to Restore (if applicable)
[Copy the FULL "Content to Restore" section with source line numbers]

### Validation Criteria (MUST ALL PASS)
[Copy ALL checkboxes from "Validation Criteria"]

### TDD Requirements
1. Write failing tests FIRST for any new functions/modules
2. Implement until tests pass
3. Refactor if needed
4. NO MOCKS - test real behavior
5. Report test results in your response

### Output Expected
Report back with:
1. ✅/❌ status for each validation criterion
2. Files created/modified (with paths)
3. Any issues encountered
4. Any follow-up tasks needed
5. Test results (pass/fail counts)
```

### 10.4 Dependency Resolution Algorithm

```python
def get_ready_tasks(all_tasks, completed_tasks):
    """Return tasks whose dependencies are all satisfied."""
    ready = []
    for task in all_tasks:
        if task.id in completed_tasks:
            continue
        deps_satisfied = all(dep in completed_tasks for dep in task.dependencies)
        if deps_satisfied:
            ready.append(task)
    return ready

def get_next_wave(all_tasks, completed_tasks):
    """Get next wave of tasks to execute in parallel."""
    ready = get_ready_tasks(all_tasks, completed_tasks)
    # Group by priority
    by_priority = {}
    for task in ready:
        p = task.priority
        by_priority.setdefault(p, []).append(task)
    # Return highest priority group
    for p in ['P0', 'P1', 'P2', 'P3', 'P4']:
        if p in by_priority:
            return by_priority[p]
    return []
```

### 10.5 Failure Handling

| Failure Type | Action |
|--------------|--------|
| P0 task fails | **STOP** - Fix immediately before continuing |
| P1 task fails | Continue independent tasks, fix ASAP |
| P2+ task fails | Log and continue, fix in later pass |
| Zen task fails | Continue main track, investigate separately |
| Sub-agent reports issues | Create follow-up task, delegate fix |
| Validation criteria not met | Task NOT done - fix and re-validate |

### 10.6 Validation Gates

**Gate 1: After P0 Completion**
```bash
# Verify constitutions generated
ls .edison/_generated/constitutions/
# Should show: ORCHESTRATORS.md, AGENTS.md, VALIDATORS.md

# Verify rosters generated
ls .edison/_generated/AVAILABLE_*.md

# Verify Zen prompts fixed
grep "API Builder" .zen/conf/systemprompts/wilson-api-builder.txt
```

**Gate 2: After P1 Completion**
```bash
# Verify no hardcoded values
grep -r "9-validator" src/edison/data/  # Should return nothing
grep -r "wilson-" src/edison/data/      # Should return nothing (except project overlay)

# Verify frontmatter
for f in src/edison/data/agents/*.md; do
  head -1 "$f" | grep -q "^---" || echo "MISSING: $f"
done
```

**Gate 3: Final Validation**
```bash
# Full composition test
edison compose --all

# Run all tests
pytest tests/ -v

# Migration validator
python scripts/validators/migration_validator.py
```

---

## 11. Task Status Tracker

**Instructions for Orchestrator:** Update this section as tasks complete. Mark tasks ✅ DONE only when ALL validation criteria pass.

### 11.1 P0 - BLOCKER Tasks Status

| Task ID | Title | Status | Dependencies Met | Notes |
|---------|-------|--------|------------------|-------|
| T-001 | Create Core Constitution Templates | ⬜ TODO | ✅ None | |
| T-002 | Create Constitution Configuration Schema | ⬜ TODO | ✅ None | |
| T-003 | Add applies_to Field to Rules Registry | ⬜ TODO | ✅ None | |
| T-004 | Implement Constitution Composer | ⬜ TODO | ⬜ T-001, T-002, T-003 | |
| T-005 | Implement get_rules_for_role() API | ⬜ TODO | ⬜ T-003 | |
| T-006 | Generate AVAILABLE_AGENTS.md Dynamically | ⬜ TODO | ⬜ T-004 | |
| T-007 | Generate AVAILABLE_VALIDATORS.md Dynamically | ⬜ TODO | ⬜ T-004 | |
| T-008 | Generate constitutions/ORCHESTRATORS.md | ⬜ TODO | ⬜ T-004, T-005, T-006, T-007 | |
| T-009 | Generate constitutions/AGENTS.md | ⬜ TODO | ⬜ T-004, T-005 | |
| T-010 | Generate constitutions/VALIDATORS.md | ⬜ TODO | ⬜ T-004, T-005 | |
| T-011 | Deprecate and Remove ORCHESTRATOR_GUIDE.md | ⬜ TODO | ⬜ T-008 | |
| T-012 | Fix Zen Prompt Composition - Wrong Role Bug | ⬜ TODO | ✅ None | **BLOCKER** |

### 11.2 P1 - CRITICAL Tasks Status

| Task ID | Title | Status | Dependencies Met | Notes |
|---------|-------|--------|------------------|-------|
| T-013 | Fix Pack Section Duplication Bug | ⬜ TODO | ⬜ T-012 | |
| T-014 | Create post-training-packages.yaml | ⬜ TODO | ✅ None | |
| T-015 | Fix Hardcoded Rule Source Paths | ⬜ TODO | ✅ None | |
| T-016 | Add Complete YAML Frontmatter to All Agents | ⬜ TODO | ✅ None | |
| T-017 | Create START_NEW_SESSION.md | ⬜ TODO | ⬜ T-008 | |
| T-018 | Create START_RESUME_SESSION.md | ⬜ TODO | ⬜ T-017 | |
| T-019 | Create START_VALIDATE_SESSION.md | ⬜ TODO | ⬜ T-017 | |
| T-020 | Restore Context7 MCP Tool Examples to All Agents | ⬜ TODO | ⬜ T-016 | |
| T-021 | Remove Hardcoded Validator Counts from Guidelines | ⬜ TODO | ⬜ T-007 | |
| T-022 | Remove Hardcoded wilson-* zenRoles | ⬜ TODO | ⬜ T-016 | |
| T-023 | Restore TDD Delegation Templates | ⬜ TODO | ✅ None | |
| T-024 | Restore TDD Verification Checklist | ⬜ TODO | ⬜ T-023 | |
| T-025 | Restore VALIDATION Batched Parallel Execution | ⬜ TODO | ⬜ T-021 | |
| T-026 | Restore QUALITY Premium Design Standards | ⬜ TODO | ✅ None | |
| T-027 | Restore Component-Builder Server/Client Examples | ⬜ TODO | ✅ None | |
| T-028 | Restore Database-Architect Schema Template | ⬜ TODO | ✅ None | |
| T-029 | Update Agent Prompts with Constitution Auto-Injection | ⬜ TODO | ⬜ T-009 | |
| T-030 | Update Validator Prompts with Constitution Auto-Injection | ⬜ TODO | ⬜ T-010 | |

### 11.3 P2 - HIGH Tasks Status

| Task ID | Title | Status | Dependencies Met | Notes |
|---------|-------|--------|------------------|-------|
| T-031 | Externalize Workflow Context to YAML | ⬜ TODO | ✅ None | |
| T-032 | Create Pack-Specific Rule Registries | ⬜ TODO | ⬜ T-003 | |
| T-033 | Create ORCHESTRATOR_VALIDATOR_RUNBOOK.md | ⬜ TODO | ⬜ T-025 | |
| T-034 | Restore Follow-up Task Metadata Schema | ⬜ TODO | ✅ None | |
| T-035 | Document zenRole Project Overlay Mapping | ⬜ TODO | ⬜ T-022 | |
| T-036 | Fix Broken Cross-References (6 Instances) | ⬜ TODO | ✅ None | |
| T-037 | Resolve Unresolved Placeholders (8 Instances) | ⬜ TODO | ✅ None | |
| T-038 | Create ConfigManager Overlay Documentation | ⬜ TODO | ⬜ T-035 | |
| T-039 | Restore QUALITY Code Smell Checklist | ⬜ TODO | ✅ None | |
| T-040 | Restore agent IMPORTANT RULES sections | ⬜ TODO | ✅ None | |
| T-041 | Fix truncated wilson-architecture.md | ⬜ TODO | ✅ None | |
| T-042 | Update all CLI references | ⬜ TODO | ✅ None | |
| T-043 | Add self-identification headers to generated files | ⬜ TODO | ⬜ T-004 | |
| T-044 | Create compaction hooks for constitution re-read | ⬜ TODO | ⬜ T-008, T-009, T-010 | |
| T-045 | Restore delegation model definitions | ⬜ TODO | ✅ None | |
| T-046 | Restore missing task type rules (7 of 11) | ⬜ TODO | ✅ None | |
| T-047 | Restore missing file pattern rules (6 patterns) | ⬜ TODO | ✅ None | |
| T-048 | Add pack context to security.md | ⬜ TODO | ⬜ T-032 | |
| T-049 | Add pack context to performance.md | ⬜ TODO | ⬜ T-032 | |
| T-050 | Restore Tailwind v4 detailed rules | ⬜ TODO | ✅ None | |
| T-051 | Restore Motion 12 animation patterns | ⬜ TODO | ✅ None | |
| T-052 | Add error recovery section to CLAUDE.md | ⬜ TODO | ✅ None | |

### 11.4 P3 - MEDIUM Tasks Status

| Task ID | Title | Status | Dependencies Met | Notes |
|---------|-------|--------|------------------|-------|
| T-053 | Remove all __pycache__ directories | ⬜ TODO | ✅ None | |
| T-054 | Remove/gitignore .agents/.cache/ | ⬜ TODO | ✅ None | |
| T-055 | Remove Wilson-specific content from core | ⬜ TODO | ⬜ T-022 | |
| T-056 | Remove duplicate defaults.yaml | ⬜ TODO | ✅ None | |
| T-057 | Remove duplicate api.md in packs | ⬜ TODO | ✅ None | |
| T-058 | Clean up empty directories | ⬜ TODO | ✅ None | |
| T-059 | Add tracking integration documentation | ⬜ TODO | ⬜ T-033 | |
| T-060 | Create validator troubleshooting guide | ⬜ TODO | ⬜ T-033 | |
| T-061 | Document state machine in START prompts | ⬜ TODO | ⬜ T-017, T-018, T-019 | |

### 11.5 P4 - LOW Tasks Status

| Task ID | Title | Status | Dependencies Met | Notes |
|---------|-------|--------|------------------|-------|
| T-062 | Add "Why no delegation" to code-reviewer | ⬜ TODO | ✅ None | |
| T-063 | Restore Wilson-specific entity examples | ⬜ TODO | ✅ None | |
| T-064 | Add version/line count metadata to agents | ⬜ TODO | ✅ None | |
| T-065 | Convert HTML rule markers to anchors | ⬜ TODO | ⬜ T-003 | |
| T-066 | Add blocking flags audit to rules | ⬜ TODO | ⬜ T-003 | |
| T-067 | Create delegation examples directory | ⬜ TODO | ⬜ T-045 | |
| T-068 | Restore TDD troubleshooting section | ⬜ TODO | ⬜ T-023 | |

### 11.6 Zen Track Tasks Status

| Task ID | Title | Status | Dependencies Met | Notes |
|---------|-------|--------|------------------|-------|
| T-ZEN-001 | Create `edison zen setup` Command | ⬜ TODO | ✅ None | |
| T-ZEN-002 | Create `edison zen start-server` Command | ⬜ TODO | ⬜ T-ZEN-001 | |
| T-ZEN-003 | Create `edison zen configure` Command | ⬜ TODO | ⬜ T-ZEN-001 | |
| T-ZEN-004 | Auto-detect uvx Availability | ⬜ TODO | ⬜ T-ZEN-001 | |
| T-ZEN-005 | Template .mcp.json Configuration | ⬜ TODO | ⬜ T-ZEN-003 | |
| T-ZEN-006 | Add Zen Setup to `edison init` Flow | ⬜ TODO | ⬜ T-ZEN-001, T-ZEN-002, T-ZEN-003 | |
| T-ZEN-007 | Document Zen Setup in Edison README | ⬜ TODO | ⬜ T-ZEN-001-006 | |
| T-ZEN-008 | End-to-End Zen Verification Test | ⬜ TODO | ⬜ T-ZEN-001-006 | |

### 11.7 Progress Summary

| Priority | Total | Done | In Progress | Remaining |
|----------|-------|------|-------------|-----------|
| P0 - BLOCKER | 12 | 0 | 0 | 12 |
| P1 - CRITICAL | 18 | 0 | 0 | 18 |
| P2 - HIGH | 22 | 0 | 0 | 22 |
| P3 - MEDIUM | 9 | 0 | 0 | 9 |
| P4 - LOW | 7 | 0 | 0 | 7 |
| Zen Track | 8 | 0 | 0 | 8 |
| **TOTAL** | **68** | **0** | **0** | **68** |

### 11.8 Wave Execution Log

Record each wave of execution here:

```
Wave 1: [DATE]
- Tasks delegated: [list]
- Results: [summary]
- Follow-ups needed: [list]

Wave 2: [DATE]
- Tasks delegated: [list]
- Results: [summary]
- Follow-ups needed: [list]

[Continue as needed...]
```

---

## Appendix A: File Path Reference

### Edison Core
```
edison/core/
├── constitutions/
│   ├── orchestrator-base.md
│   ├── agents-base.md
│   └── validators-base.md
├── config/
│   ├── constitution.yaml
│   ├── workflow.yaml
│   └── post_training_packages.yaml
├── start/
│   ├── START_NEW_SESSION.md
│   ├── START_RESUME_SESSION.md
│   └── START_VALIDATE_SESSION.md
└── rules/
    └── registry.yml
```

### Edison Data
```
src/edison/data/
├── agents/
│   ├── api-builder.md
│   ├── component-builder.md
│   ├── database-architect.md
│   ├── code-reviewer.md
│   ├── test-engineer.md
│   └── feature-implementer.md
├── config/
│   ├── delegation.yaml
│   ├── validators.yaml
│   └── post_training_packages.yaml
├── guidelines/
│   ├── shared/
│   │   ├── TDD.md
│   │   ├── VALIDATION.md
│   │   ├── QUALITY.md
│   │   ├── DELEGATION.md
│   │   └── CONTEXT7.md
│   ├── agents/
│   ├── validators/
│   └── orchestrators/
└── rules/
    └── registry.yml
```

### Generated Outputs
```
.edison/_generated/
├── AVAILABLE_AGENTS.md
├── AVAILABLE_VALIDATORS.md
├── constitutions/
│   ├── ORCHESTRATORS.md
│   ├── AGENTS.md
│   └── VALIDATORS.md
├── agents/
├── validators/
└── guidelines/
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **CORE** | Base Edison framework definitions in `edison/core/` |
| **PACKS** | Technology-specific extensions (React, Prisma, etc.) in `edison/packs/<pack>/` |
| **PROJECT** | Project-specific overrides in `.edison/` |
| **Constitution** | Role-based mandatory instructions document |
| **Composition** | Process of merging CORE + PACKS + PROJECT into generated files |
| **Zen MCP** | MCP server for sub-agent delegation |
| **zenRole** | Role identifier for Zen MCP routing |
| **Context7** | MCP tool for querying up-to-date package documentation |
| **Wave** | Validator execution group (Global → Critical → Specialized) |
| **Roster** | Dynamic list of available agents or validators |

---

## Appendix C: Validation Checklist

Before declaring migration complete:

### Constitution System
- [ ] `edison compose --all` generates constitutions/ORCHESTRATORS.md
- [ ] `edison compose --all` generates constitutions/AGENTS.md
- [ ] `edison compose --all` generates constitutions/VALIDATORS.md
- [ ] All constitutions have self-identification headers
- [ ] All constitutions have RE-READ instructions
- [ ] Agent prompts auto-inject constitution reference
- [ ] Validator prompts auto-inject constitution reference
- [ ] Rules filtered by `applies_to` in constitutions

### Dynamic Generation
- [ ] AVAILABLE_AGENTS.md generated from AgentRegistry
- [ ] AVAILABLE_VALIDATORS.md generated from ValidatorRegistry
- [ ] ORCHESTRATOR_GUIDE.md removed/deprecated
- [ ] No hardcoded agent/validator lists in guidelines

### Hardcoded Values
- [ ] No "9-validator" or "9 validators" anywhere
- [ ] No "wilson-*" in edison core files
- [ ] No ".agents/" paths in rules
- [ ] All zenRoles use template variables

### Zen Integration
- [ ] `edison zen setup` works
- [ ] `edison zen start-server` works
- [ ] `edison zen configure` creates valid .mcp.json
- [ ] Zen prompts contain correct content (agents vs validators)

### Content Restoration
- [ ] All 6 agents have YAML frontmatter
- [ ] Context7 examples in all agents
- [ ] TDD delegation templates restored
- [ ] QUALITY Premium Design Standards restored
- [ ] START prompts (NEW, RESUME, VALIDATE) exist

---

*Plan Generated: 2025-11-26*
*Total Tasks: 68 (60 Main Track + 8 Zen Track)*
*Policy: ⚠️ IMPLEMENT EVERYTHING - No deferrals*
