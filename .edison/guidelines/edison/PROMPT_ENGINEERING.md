# Edison Prompt Engineering Rules

This file defines the mandatory rules for developing/modifying agents, validators, orchestrators, constitutions, and guidelines in Edison.

<!-- SECTION: core-principles -->
## Core Principles (All Roles)

### Single Source of Truth
- Every rule/guideline exists in ONE canonical file
- All other files include from that source via `{{include-section:}}`
- Change in one place propagates everywhere

### No Double-Loading (CRITICAL)
Content appears ONCE. NEVER:
- Include content AND list it as mandatory read
- Copy content instead of including

### Role-Specific Loading
- **Agents**: HOW to implement (TDD execution, code patterns)
- **Validators**: HOW to verify (compliance checks, flags)
- **Orchestrators**: HOW to coordinate (delegation, waves)

Content for other roles MUST NOT be loaded.

### Technology-Agnostic Core
Core agents/validators have ZERO technology content. Packs inject via EXTEND.

### Constitution Embedding
Constitutions are embedded in prompts via `{{include:constitutions/*-base.md}}`.
Single instruction: "Re-read your file on compact" = everything.

### Dynamic Content via Functions
NEVER hardcode states/rosters/versions. Use `{{fn:function_name}}`.
<!-- /SECTION: core-principles -->

<!-- SECTION: file-structure -->
## File Organization

```
guidelines/
├── includes/          # NEVER read directly (section-only)
│   └── {TOPIC}.md    # Has role-specific sections
├── agents/           # Agent-readable
├── validators/       # Validator-readable
├── orchestrators/    # Orchestrator-readable
└── shared/           # Optional deep-dives

agents/               # Constitution embedded
validators/           # Constitution embedded
constitutions/        # Include-only (embedded in prompts)
packs/{pack}/         # Technology-specific extensions
```
<!-- /SECTION: file-structure -->

<!-- SECTION: templating-rules -->
## Templating Rules

### Includes
```markdown
{{include-section:guidelines/includes/TDD.md#agent-execution}}
```
- Use section includes, not full file includes
- Resolution: project → packs → core

### Sections
```markdown
<!-- SECTION: name -->
Content
<!-- /SECTION: name -->
```
- Required for all content that varies by role
- Required for pack extension points

### Pack Extensions
```markdown
<!-- EXTEND: tools -->
Pack-specific content
<!-- /EXTEND -->
```
- Packs ONLY use EXTEND (never redefine sections)
- No generic content in pack extensions
<!-- /SECTION: templating-rules -->

<!-- SECTION: agent-development -->
## Agent Development Rules

### Agent Template
```markdown
---
name: {agent-name}
---

{{include:constitutions/agents-base.md}}

## Role
[Agent-specific role description]

## Tools
<!-- SECTION: tools -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tools -->

## Guidelines
<!-- SECTION: guidelines -->
<!-- /SECTION: guidelines -->

## Workflow
[Agent-specific workflow]
```

### Agent Rules
1. Constitution embedded first
2. No generic TDD/NO_MOCKS (in constitution)
3. No technology content (in pack overlays)
4. SECTION placeholders for tools/guidelines
5. Only role-specific content remains
<!-- /SECTION: agent-development -->

<!-- SECTION: validator-development -->
## Validator Development Rules

### Validator Template
```markdown
{{include:constitutions/validators-base.md}}

## Mission
[What this validates]

## Triggers
`**/*.test.*`

## Checklist
<!-- SECTION: checklist -->
[Generic checks]
<!-- /SECTION: checklist -->

## Tech Checks
<!-- SECTION: tech-checks -->
<!-- Pack overlays extend here -->
<!-- /SECTION: tech-checks -->
```

### Validator Rules
1. Constitution embedded first
2. Clear triggers and blocking status
3. Generic checklist in core
4. SECTION: tech-checks for packs
<!-- /SECTION: validator-development -->

<!-- SECTION: pack-development -->
## Pack Development Rules

### Pack Overlay Pattern
```markdown
---
name: {target-agent}
pack: {pack}
overlay_type: extend
---

<!-- EXTEND: tools -->
### {Pack} Tools
{Technology-specific commands}
<!-- /EXTEND -->

<!-- EXTEND: guidelines -->
{{include-section:packs/{pack}/guidelines/TESTING.md#patterns}}
<!-- /EXTEND -->
```

### Pack Rules
1. EXTEND only (never redefine)
2. No generic content (TDD philosophy, etc.)
3. Only technology-specific content
4. Include from pack guidelines for complex patterns
<!-- /SECTION: pack-development -->

<!-- SECTION: guidelines-development -->
## Guidelines Development Rules

### Includes File Structure
```markdown
<!-- SECTION: principles -->
## {Topic} Principles (All Roles)
[Universal principles]
<!-- /SECTION: principles -->

<!-- SECTION: agent-{action} -->
## {Topic} for Agents
[Agent-specific]
<!-- /SECTION: agent-{action} -->

<!-- SECTION: validator-{action} -->
## {Topic} for Validators
[Validator-specific]
<!-- /SECTION: validator-{action} -->

<!-- SECTION: orchestrator-{action} -->
## {Topic} for Orchestrators
[Orchestrator-specific]
<!-- /SECTION: orchestrator-{action} -->
```

### Guidelines Rules
1. Includes files have ALL role sections
2. Shared files are truly shared (all roles benefit)
3. No duplicated content across files
4. Sections properly marked with comments
<!-- /SECTION: guidelines-development -->

<!-- SECTION: anti-patterns -->
## Anti-Patterns (FORBIDDEN)

### Double-Loading
```markdown
# FORBIDDEN
mandatoryReads: [shared/TDD.md]
{{include:shared/TDD.md}}  # <-- Same content twice!
```

### Technology in Core
```markdown
# FORBIDDEN in core agent
- pytest tests/   # <-- Python-specific!
- pnpm test       # <-- Node-specific!
```

### Hardcoded Dynamic Content
```markdown
# FORBIDDEN
Valid states: todo, wip, done

# CORRECT
Valid states: {{fn:task_states}}
```

### Generic Content in Packs
```markdown
# FORBIDDEN in pack
## TDD Principles      # <-- Generic, belongs in core!
```

### Copying Instead of Including
```markdown
# FORBIDDEN
[50 lines copied from another file]

# CORRECT
{{include-section:path#section}}
```

### Wrong-Role Content
```markdown
# FORBIDDEN in agent
## Validator Wave Orchestration  # <-- Orchestrator-only!
```
<!-- /SECTION: anti-patterns -->

<!-- SECTION: quality-checklist -->
## Quality Checklist

Before any prompt change:
- [ ] Content is technology-agnostic (core) or technology-specific (pack)?
- [ ] Content already exists in canonical source?
- [ ] Including correct role-specific section?
- [ ] No double-loading?
- [ ] SECTION markers present for extension?

After changes:
- [ ] `edison compose --all` succeeds
- [ ] No broken includes/sections
- [ ] No duplicate content in composed output
- [ ] Each role loads only their content
<!-- /SECTION: quality-checklist -->
