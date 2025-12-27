<!-- TaskID: 2023-wdoc-003-constitution-awareness -->
<!-- Priority: 2023 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: documentation -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave1-groupC -->
<!-- EstimatedHours: 1 -->

# WDOC-003: Add Constitution Awareness Section to Agent Templates

## Summary
Add a "Constitution Awareness" section to all agent templates that explicitly declares the agent type, constitution location, and re-read requirements.

## Problem Statement
Current agents lack:
1. Explicit declaration of agent type (AGENT vs VALIDATOR vs ORCHESTRATOR)
2. Constitution file location
3. Re-read requirement after context compaction
4. Role boundary explanation

This causes agents to not know their boundaries or where to find authoritative configuration.

## Dependencies
- None - template addition

## Objectives
- [x] Design standard constitution awareness section
- [x] Add to all Edison core agent templates
- [x] Ensure section is included in composition output
- [x] Verify generated agents have the section

## Source Files

### Templates to Modify
```
/Users/leeroy/Documents/Development/edison/src/edison/data/agents/*.md
```

Specifically:
- api-builder.md
- code-reviewer.md
- component-builder.md
- database-architect.md
- feature-implementer.md
- test-engineer.md

### Constitution Files to Reference
```
.edison/_generated/constitutions/AGENTS.md
.edison/_generated/constitutions/VALIDATORS.md
.edison/_generated/constitutions/ORCHESTRATORS.md
```

## Precise Instructions

### Step 1: Design Standard Section

Create this section template:

```markdown
## Constitution Awareness

**Role Type**: AGENT
**Constitution**: `.edison/_generated/constitutions/AGENTS.md`

### Binding Rules
1. **Re-read Constitution**: At the start of every task assignment and after any context compaction, re-read the constitution file.
2. **Authority Hierarchy**: Constitution > Guidelines > Task Instructions
3. **Role Boundaries**: You are an AGENT. You implement tasks assigned by the orchestrator. You do NOT:
   - Make delegation decisions (that's the orchestrator's job)
   - Validate other agents' work (that's validators' job)
   - Manage sessions or task states (that's the orchestrator's job)
4. **Scope Mismatch**: If assigned a task outside your specialization, return `MISMATCH` with explanation.

### When to Re-read
- Start of new task assignment
- After `/compact` command
- After session resume
- When confused about role boundaries
```

### Step 2: Add to Each Agent Template

For each agent file in `src/edison/data/agents/`, add the section after the frontmatter and before the main content.

```bash
cd /Users/leeroy/Documents/Development/edison/src/edison/data/agents

# For each file, insert after the first '---' block (frontmatter)
for file in *.md; do
  echo "Processing $file"
  # Manual edit required - see template below
done
```

### Step 3: Template for Each Agent Type

**api-builder.md** (AGENT):
```markdown
## Constitution Awareness

**Role Type**: AGENT
**Constitution**: `.edison/_generated/constitutions/AGENTS.md`
**Specialization**: API endpoint implementation with Fastify

### Binding Rules
1. **Re-read Constitution**: At task start and after context compaction
2. **Authority Hierarchy**: Constitution > Guidelines > Task Instructions
3. **Role Boundaries**: You implement API routes. You do NOT make delegation decisions.
4. **Scope Mismatch**: Return `MISMATCH` if assigned UI or database-only tasks
```

**database-architect.md** (AGENT):
```markdown
## Constitution Awareness

**Role Type**: AGENT
**Constitution**: `.edison/_generated/constitutions/AGENTS.md`
**Specialization**: Database schema design with Prisma

### Binding Rules
1. **Re-read Constitution**: At task start and after context compaction
2. **Authority Hierarchy**: Constitution > Guidelines > Task Instructions
3. **Role Boundaries**: You design schemas and migrations. You do NOT make delegation decisions.
4. **Scope Mismatch**: Return `MISMATCH` if assigned UI or API-only tasks
```

**component-builder.md** (AGENT):
```markdown
## Constitution Awareness

**Role Type**: AGENT
**Constitution**: `.edison/_generated/constitutions/AGENTS.md`
**Specialization**: UI component creation with React/Next.js

### Binding Rules
1. **Re-read Constitution**: At task start and after context compaction
2. **Authority Hierarchy**: Constitution > Guidelines > Task Instructions
3. **Role Boundaries**: You build UI components. You do NOT make delegation decisions.
4. **Scope Mismatch**: Return `MISMATCH` if assigned API or database tasks
```

**test-engineer.md** (AGENT):
```markdown
## Constitution Awareness

**Role Type**: AGENT
**Constitution**: `.edison/_generated/constitutions/AGENTS.md`
**Specialization**: Test creation with Vitest

### Binding Rules
1. **Re-read Constitution**: At task start and after context compaction
2. **Authority Hierarchy**: Constitution > Guidelines > Task Instructions
3. **Role Boundaries**: You write tests. You do NOT make delegation decisions.
4. **Scope Mismatch**: Return `MISMATCH` if assigned implementation tasks without TDD context
```

**code-reviewer.md** (AGENT):
```markdown
## Constitution Awareness

**Role Type**: AGENT
**Constitution**: `.edison/_generated/constitutions/AGENTS.md`
**Specialization**: Code quality review

### Binding Rules
1. **Re-read Constitution**: At task start and after context compaction
2. **Authority Hierarchy**: Constitution > Guidelines > Task Instructions
3. **Role Boundaries**: You review code quality. You do NOT implement features.
4. **Scope Mismatch**: Return `MISMATCH` if assigned implementation tasks
```

**feature-implementer.md** (AGENT):
```markdown
## Constitution Awareness

**Role Type**: AGENT
**Constitution**: `.edison/_generated/constitutions/AGENTS.md`
**Specialization**: Full-stack feature implementation

### Binding Rules
1. **Re-read Constitution**: At task start and after context compaction
2. **Authority Hierarchy**: Constitution > Guidelines > Task Instructions
3. **Role Boundaries**: You implement features across the stack.
4. **Scope Mismatch**: Return `MISMATCH` if task requires specialized deep expertise
```

### Step 4: Verify Section Is Included in Composition

After editing, run composition:
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose agents

# Check output includes constitution section
grep -A 10 "Constitution Awareness" .edison/_generated/agents/api-builder.md
```

### Step 5: Verify All Agents Have Section
```bash
for agent in api-builder code-reviewer component-builder database-architect feature-implementer test-engineer; do
  echo "=== $agent ==="
  grep -c "Constitution Awareness" .edison/_generated/agents/$agent.md
done
# Each should return 1
```

## Verification Checklist
- [ ] All 6 agent templates have Constitution Awareness section
- [ ] Section includes: Role Type, Constitution path, Binding Rules
- [ ] Each agent has appropriate Specialization
- [ ] Re-read requirement is clearly stated
- [ ] MISMATCH return is documented
- [ ] Composition includes the section in output

## Success Criteria
All generated agent files include a Constitution Awareness section that explicitly declares the agent's type, constitution location, and re-read requirements.

## Related Issues
- Audit ID: R1-006 (Constitution awareness missing)
- Audit ID: AI-005 (No agent type indication)
- Audit ID: AI-006 (No re-read instruction)
