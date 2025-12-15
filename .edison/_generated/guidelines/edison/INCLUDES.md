# Edison Development Guidelines - Includes

This file aggregates critical Edison-specific guidelines for composition into prompts.

## Prompt Engineering (When Modifying Edison Prompts/Agents/Validators)

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

## References

- **Full Documentation**: `docs/PROMPT_DEVELOPMENT.md`
- **Architecture**: `.edison/guidelines/edison/ARCHITECTURE.md`
- **Critical Principles**: `.edison/guidelines/edison/CRITICAL_PRINCIPLES.md`
- **Contributing**: `.edison/guidelines/edison/CONTRIBUTING.md`