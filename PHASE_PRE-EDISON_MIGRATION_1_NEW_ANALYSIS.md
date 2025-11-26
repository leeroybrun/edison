# Edison Migration - Complete Analysis & Implementation Plan

**Date:** 2025-11-25
**Status:** IN PROGRESS
**Version:** 1.0
**Validated By:** 10 Parallel Validators (5 Codex + 5 Opus)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Validation Methodology](#2-validation-methodology)
3. [Critical Findings - Agents](#3-critical-findings---agents)
4. [Critical Findings - Validators](#4-critical-findings---validators)
5. [Critical Findings - Guidelines](#5-critical-findings---guidelines)
6. [Critical Findings - Orchestrator Entry Points](#6-critical-findings---orchestrator-entry-points)
7. [Critical Findings - Duplicates & Cleanup](#7-critical-findings---duplicates--cleanup)
7B. [Core Architectural Principles (CRITICAL)](#7b-core-architectural-principles-critical)
8. [Constitution System Design](#8-constitution-system-design)
9. [Dynamic Generation Architecture](#9-dynamic-generation-architecture)
10. [Implementation Tasks](#10-implementation-tasks)
11. [Independent Re-Analysis Results](#11-independent-re-analysis-results)
12. [Deep File-by-File Analysis Results](#12-deep-file-by-file-analysis-results)

---

## 1. Executive Summary

### Overview
This document captures the comprehensive findings from a deep validation analysis comparing:
- **PRE-EDISON**: `/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/`
- **POST-EDISON GENERATED**: `/Users/leeroy/Documents/Development/wilson-leadgen/.agents/_generated/`
- **EDISON CORE**: `/Users/leeroy/Documents/Development/wilson-leadgen/.edison/`

### Key Statistics
| Metric | Count |
|--------|-------|
| Agents Analyzed | 6 |
| Validators Analyzed | 9 |
| Guidelines Analyzed | 9 |
| Entry Points Analyzed | 3 |
| Critical Issues Found | 47 |
| High Priority Issues | 38 |
| Medium Priority Issues | 24 |
| Duplicate Files Found | 12+ |
| Files to Remove | 30+ |

### Severity Distribution
- 🔴 **CRITICAL**: 15 issues (blocking functionality)
- 🟠 **HIGH**: 23 issues (missing significant content)
- 🟡 **MEDIUM**: 18 issues (organization/cleanup)
- 🟢 **LOW**: 10 issues (enhancements)

---

## 2. Validation Methodology

### Parallel Validation Approach
We used 10 parallel validators (5 Codex via Zen MCP + 5 Claude Opus subagents) to analyze:

1. **Agent Files Deep Comparison** - All 6 agents
2. **Validator Files Deep Comparison** - All 9 validators
3. **Guidelines Files Deep Comparison** - All 9 guidelines
4. **Orchestrator Entry Points Comparison** - CLAUDE.md, START.SESSION.md, AGENTS.md
5. **Cleanup and Duplicate Detection** - Both .agents and .edison directories

### Comparison Criteria
- Missing sections/headings
- Missing instructions/rules
- Missing code examples
- Content split correctness (core vs pack vs project)
- Hardcoded lists that should be dynamic
- Configuration path changes
- Output format changes

---

## 3. Critical Findings - Agents

### 3.1 Universal Gaps Across ALL 6 Agents

| Gap ID | Gap Description | Severity | Impact |
|--------|-----------------|----------|--------|
| AGT-001 | YAML Frontmatter missing (`name`, `description`, `model`, `zenRole`) | HIGH | Agent registration/metadata lost |
| AGT-002 | MANDATORY WORKFLOW references removed | CRITICAL | Agents don't know workflow to follow |
| AGT-003 | OUTPUT FORMAT references missing | HIGH | Implementation report format undefined |
| AGT-004 | CONFIGURATION AUTHORITY sections missing | HIGH | Config file locations unknown |
| AGT-005 | Context7 MCP explicit examples removed | CRITICAL | Post-training package lookup broken |
| AGT-006 | "Knowledge Outdated" warning removed | MEDIUM | Agents may use stale knowledge |
| AGT-007 | Canonical Guide reference tables removed | HIGH | Missing guide linkage |
| AGT-008 | Validator count hardcoded ("9 validators") | MEDIUM | Should be dynamic |

### 3.2 Agent-Specific Missing Content

#### api-builder.md
```
MISSING SECTIONS:
- Front-matter metadata (lines 1-6)
- MANDATORY WORKFLOW pointing to IMPLEMENTER_WORKFLOW.md (lines 12-17)
- Output Format with Ephemeral Summaries policy (lines 36-41)
- VALIDATION AWARENESS with 9-validator architecture (lines 57-66)
- DELEGATION AWARENESS with config.json reference (lines 69-82)
- CONTEXT7 MCP SERVER workflow section (lines 85-112)
- Configuration Authority section (lines 328-350)
- Canonical Guide table (lines 354-369)

MISSING EXAMPLES:
- Next.js route handler GET/POST example with Zod (lines 123-205) - 80+ lines
- Error handling with Prisma P2002 conflict (lines 254-282)
- Authentication pattern using requireAuth (lines 285-300)
```

#### component-builder.md
```
MISSING SECTIONS:
- Tailwind v4 critical syntax rules (lines 113-160)
- Server vs Client component examples (lines 163-238)
- Animations with Motion 12 (lines 303-321)
- Forms with validation example (lines 323-385)
- Design System rules (lines 389-429)
- Important Rules list (8 items) (lines 481-490)

MISSING EXAMPLES:
- Complete LeadList client component
- MetricCard with trend indicator
- LeadForm with Zod validation
- Server Component page with Prisma query
```

#### database-architect.md
```
MISSING SECTIONS:
- Prisma schema patterns with concrete models (lines 123-189)
- Migration workflow with commands (lines 192-239)
- Performance optimization section (lines 242-300)
- Data integrity constraints (lines 304-335)
- Relationship patterns (lines 339-390)

MISSING EXAMPLES:
- Complete schema.prisma example with @@map
- Migration safety classifications
- Query optimization patterns
- Many-to-many relationship pattern
```

#### code-reviewer.md
```
MISSING SECTIONS:
- Step-by-step review workflow (30+ checkbox items) (lines 182-289)
- Issue severity categorization (lines 291-314)

MISSING INSTRUCTIONS:
- Reference to VALIDATOR_WORKFLOW.md
- Package version warnings (Next.js 16 vs 14, React 19 vs 18, etc.)
```

#### test-engineer.md
```
MISSING SECTIONS:
- Complete API route testing with namespace helpers (lines 246-358)
- Tech stack section (lines 529-542)
- Configuration Authority section

MISSING EXAMPLES:
- Complete namespace helper usage
- Template database unit test with createAuthenticatedRequest
- TDD workflow RED-GREEN report template
```

#### feature-implementer.md
```
MISSING SECTIONS:
- Premium Design Standards (lines 169-181)
- Quality Standards checklist (lines 183-195)

MISSING INSTRUCTIONS:
- "Sub-agents never call other models" statement
- "CRITICAL: This is a Next.js 16 project, NOT Fastify!" emphasis
- "VERIFY DELEGATION" rule
```

---

## 4. Critical Findings - Validators

### 4.1 Global Validators (codex-global, claude-global)

| Gap ID | Gap Description | Severity |
|--------|-----------------|----------|
| VAL-001 | Hardcoded version table removed (Next.js 16.0.0, React 19.2.0, etc.) | HIGH |
| VAL-002 | Context7 code examples (`mcp__context7__get-library-docs()`) removed | CRITICAL |
| VAL-003 | Common Mistakes to Avoid section removed (v3→v4 examples) | HIGH |
| VAL-004 | Pack section duplicated 5-7 TIMES (massive bloat) | CRITICAL |
| VAL-005 | Config path changed to ConfigManager overlays | MEDIUM |
| VAL-006 | Type-safety gates removed (no `any`, no `@ts-ignore`) | HIGH |
| VAL-007 | React/Next patterns removed (App Router, server components) | HIGH |
| VAL-008 | API security basics removed (Zod validation, auth) | HIGH |
| VAL-009 | Performance checks removed (bundle-size, N+1) | HIGH |
| VAL-010 | Testing coverage/quality checks removed | HIGH |

### 4.2 Critical Validators (security, performance)

#### security.md
```
MISSING SECTIONS:
- Context7 Knowledge Refresh (MANDATORY) (lines 22-40)
- Check for plain text passwords (lines 167-174)
- Check for vulnerabilities (lines 366-432)
- Check for custom auth implementation (lines 433-452)
- Check all API routes use Zod (lines 491-504)
- User-controlled fetch/SSRF checks (lines 615-618)
- Open redirect checks (lines 619-625)
- Wilson-Specific Security Requirements (lines 636-704)

MISSING VALIDATION RULES:
- Missing requireAuth call detection
- Raw SQL with string interpolation flagging
- Custom JWT implementation prohibition
- Zod validation enforcement per route
```

#### performance.md
```
MISSING SECTIONS:
- Bundle-size report example table (lines 71-74)
- Server vs Client Components section (lines 133-209)
- Image and Font Optimization (lines 378-404)
- Code Splitting and Dynamic Imports (lines 427-455)
- React Performance Patterns (lines 529-620)

MISSING CHECKS:
- Bundle size thresholds and reporting
- Server-vs-client component balance verification
- Code-splitting expectations
- React perf pattern checklist
```

### 4.3 Specialized Validators

| Validator | Issues |
|-----------|--------|
| api.md | Added non-relevant pack contexts (1006 lines vs 694) |
| nextjs.md | Missing Wilson Dashboard branding, 40% file size increase |
| testing.md | Missing Wilson-specific test helpers, 40% size increase |
| react.md | Missing Wilson Dashboard language, 52% size increase |
| database.md | Missing Wilson schema baseline, 47% size increase |

### 4.4 Pack Section Duplication (CRITICAL)

The pack context sections are duplicated multiple times within validator files:

| File | Duplications | Wasted Lines |
|------|--------------|--------------|
| codex-global.md | 5 times | ~1000 lines |
| claude-global.md | 7 times | ~1400 lines |
| api.md | 3 times | ~600 lines |
| nextjs.md | 3 times | ~600 lines |

**ROOT CAUSE**: Composition system appending pack contexts multiple times instead of deduplicating.

---

## 5. Critical Findings - Guidelines

### 5.1 TDD/TDD_GUIDE.md

| Gap ID | Gap Description | Pre-Edison Lines | Severity |
|--------|-----------------|------------------|----------|
| GDL-001 | "Why TDD is Mandatory" section missing | 54-95 | CRITICAL |
| GDL-002 | RED-GREEN-REFACTOR detailed cycle missing | 99-170 | HIGH |
| GDL-003 | TDD When Delegating to Sub-Agents missing | 374-507 | HIGH |
| GDL-004 | Verification Checklist & Report Template missing | 512-640 | HIGH |
| GDL-005 | Enforcement Rules missing | 746-801 | MEDIUM |
| GDL-006 | Testing Infrastructure & Patterns missing | 821-1017 | HIGH |
| GDL-007 | Real Examples & Troubleshooting missing | 1334-1606 | MEDIUM |
| GDL-008 | Unresolved placeholders (`{{orm}}`, `{{web-framework}}`) | Multiple | HIGH |

### 5.2 DELEGATION.md

| Gap ID | Gap Description | Severity |
|--------|-----------------|----------|
| GDL-009 | Delegation config structure with concrete defaults missing | HIGH |
| GDL-010 | Deterministic priority chain with real rules missing | HIGH |
| GDL-011 | Placeholder tokens unresolved throughout | HIGH |

### 5.3 SESSION_WORKFLOW.md

| Gap ID | Gap Description | Severity |
|--------|-----------------|----------|
| GDL-012 | Task & QA architecture/directory semantics missing | HIGH |
| GDL-013 | Session Start Protocol missing | CRITICAL |
| GDL-014 | Planning & Delegation workflow missing | HIGH |
| GDL-015 | QA brief creation/activation missing | HIGH |
| GDL-016 | Extended guide file missing entirely | CRITICAL |

### 5.4 VALIDATION.md

| Gap ID | Gap Description | Severity |
|--------|-----------------|----------|
| GDL-017 | 9 Validators table with triggers/models missing | HIGH |
| GDL-018 | Architecture Execution Flow diagram missing | HIGH |
| GDL-019 | Batched Parallel Execution Model missing | HIGH |
| GDL-020 | Unresolved placeholders throughout | HIGH |

### 5.5 EPHEMERAL_SUMMARIES_POLICY.md

| Gap ID | Gap Description | Severity |
|--------|-----------------|----------|
| GDL-021 | **ENTIRE FILE MISSING** from post-Edison | CRITICAL |

**Content that needs restoration:**
- Absolute Prohibition on Auto-Summaries
- Canonical Tracking Surfaces table
- Allowed vs Forbidden Locations table
- Workflow Enforcement
- Migration Notes
- FAQ

### 5.6 Other Guidelines

| Guideline | Issues |
|-----------|--------|
| QUALITY.md | Premium Design Standards missing, Code Smell Checklist condensed |
| HONEST_STATUS.md | Communication Templates missing, Context Pressure handling missing |
| GIT_WORKFLOW.md | PR creation section missing, Branch Operations missing |
| CONTEXT7.md | Wilson-specific package list missing from project config |

---

## 6. Critical Findings - Orchestrator Entry Points

### 6.1 CLAUDE.md Missing Instructions

| Gap ID | Pre-Edison Source | Missing Content |
|--------|-------------------|-----------------|
| ORC-001 | CLAUDE.md line 3 | Manifest preload + rule fetching via `scripts/rules require <RULE_ID>` |
| ORC-002 | CLAUDE.md lines 6-9 | Task split parallelization with `scripts/tasks/split` |
| ORC-003 | CLAUDE.md line 16 | Self-edit limit (≤10 lines), delegate everything else |
| ORC-004 | CLAUDE.md lines 27-30 | Bundle/validate/promote CLIs |
| ORC-005 | START.SESSION.md line 10 | Human confirmation requirement before work |
| ORC-006 | START.SESSION.md lines 17-18 | Stale task takeover policy (4hr rule) |
| ORC-007 | START.SESSION.md line 32 | Bundle-first rule before validators |
| ORC-008 | AGENTS.md line 14 | Context7-first requirement |
| ORC-009 | AGENTS.md line 15 | Automation gate sequence |
| ORC-010 | AGENTS.md line 20 | Fail-closed guardrail behavior |

### 6.2 ORCHESTRATOR_GUIDE.md Issues

| Gap ID | Issue | Severity |
|--------|-------|----------|
| ORC-011 | Agent roster hardcoded (23 names with duplicates) | HIGH |
| ORC-012 | Validator roster with models hardcoded | HIGH |
| ORC-013 | Priority chain file patterns hardcoded | HIGH |
| ORC-014 | Blocking validators list hardcoded | MEDIUM |
| ORC-015 | Empty priority chains section | HIGH |
| ORC-016 | File pattern rules incomplete (10 vs 20+) | HIGH |
| ORC-017 | Sub-agent defaults missing | HIGH |
| ORC-018 | Model capabilities/strengths/weaknesses missing | MEDIUM |

### 6.3 Configuration Gaps

| Config Area | Missing |
|-------------|---------|
| Validator Config | priority, blocksOnFail, alwaysRun, specFile, interface, zenRole, fileTriggers |
| Delegation Config | filePatternRules, taskTypeRules, modelDefinitions, orchestratorGuidance, subAgentDefaults |
| Session Config | Timeout values not shown in docs |

---

## 7. Critical Findings - Duplicates & Cleanup

### 7.1 Critical Duplicate Files

| File 1 | File 2 | Issue |
|--------|--------|-------|
| `.edison/core/validators/global/codex-core.md` | `.edison/core/validators/global/codex-global.md` | IDENTICAL content |
| `.edison/packs/fastify/validators/api.md` | `.edison/packs/nextjs/validators/api.md` | 720+ lines identical |
| `.edison/core/guidelines/TDD.md` | `.edison/core/guidelines/shared/TDD.md` | Pattern 1 & 2 duplicated |
| `.edison/core/defaults.yaml` | `.edison/core/config/defaults.yaml` | Significant overlap |
| `.agents/.cache/composed/*.md` | `.agents/_generated/validators/*.md` | All validators duplicated |
| `.agents/guidelines/*.md` | `.agents/_generated/guidelines/*.md` | Source and generated copies |

### 7.2 Leftover Files to Remove

```
CACHE DIRECTORIES (24+):
.edison/core/__pycache__/
.edison/core/scripts/rules/__pycache__/
.edison/core/scripts/session/__pycache__/
.edison/core/lib/paths/__pycache__/
.edison/core/lib/qa/__pycache__/
.edison/core/lib/utils/__pycache__/
.edison/core/lib/__pycache__/
.edison/core/lib/state/__pycache__/
.edison/core/lib/composition/__pycache__/
.edison/core/lib/adapters/__pycache__/
.edison/core/lib/task/__pycache__/
.edison/core/lib/git/__pycache__/
.edison/core/lib/orchestrator/__pycache__/
.edison/core/lib/process/__pycache__/
.edison/core/lib/session/__pycache__/
.edison/vendor/site-packages/yaml/__pycache__/

OTHER:
.agents/.cache/ (entire directory - should be gitignored)
.edison/.agents/ (empty directory)
.edison/tmp-tech-stack-context.md (temporary scratch)
.edison/tmp-tech-stack-full.md (temporary scratch)
```

### 7.3 Misplaced Content

| Location | Content | Should Be In |
|----------|---------|--------------|
| `.edison/core/defaults.yaml` lines 71-72 | context7Packages: [next, react, uistylescss...] | `.agents/config/` (Wilson-specific) |
| `.edison/core/defaults.yaml` lines 249-360 | Wilson-specific file pattern rules | `.agents/config/delegation.yml` |
| `.edison/core/guidelines/shared/QUALITY.md` | Wilson-specific pnpm commands | `.agents/guidelines/` |

### 7.4 Hardcoded Lists in Config Files

| File | Lines | Hardcoded Content |
|------|-------|-------------------|
| `.agents/config/validators.yml` | 3-16 | Validator roster |
| `.agents/config/delegation.yml` | 3-8 | Implementer list |
| `.agents/config/packs.yml` | 6-13 | Active packs list |
| `.edison/core/defaults.yaml` | 59-210 | Complete validator roster |

### 7.5 Broken/Corrupted Files

| File | Issue |
|------|-------|
| `_generated/guidelines/wilson-architecture.md` | Truncated (53 lines vs 70 source) |
| `.edison/core/config/defaults.yaml` | Duplicate YAML keys (`database:`, `subprocess_timeouts:`) |

---

## 7B. Core Architectural Principles (CRITICAL)

### 7B.1 Composition & Extension Model

**RULE: Everything is composable at three levels:**
```
CORE → PACKS → PROJECT
```

| Layer | Location | Purpose |
|-------|----------|---------|
| **CORE** | `.edison/core/` | Base definitions, framework defaults |
| **PACKS** | `.edison/packs/<pack>/` | Technology-specific extensions (React, Prisma, etc.) |
| **PROJECT** | `.agents/` | Project-specific overrides and additions |

**Extension Rules:**
1. Guidelines, rules, agents, validators can be defined at ANY layer
2. Lower layers extend/override higher layers (PROJECT > PACKS > CORE)
3. Pack-specific content (React patterns) stays in packs, NOT in core
4. Project-specific content (Wilson auth) stays in project, NOT in packs

### 7B.2 Generated Files Principle

**RULE: NEVER link to source files, ONLY to generated files**

```
# WRONG - linking to source
See: .edison/core/guidelines/TDD.md

# CORRECT - linking to generated
See: .agents/_generated/guidelines/TDD.md
```

**Rationale:**
- Generated files contain FULL composed content (core + packs + project)
- Source files are incomplete without pack/project extensions
- Only generated files represent the "truth" for this project

**Generated Output Location:** Configurable via `{.agents|.edison}/_generated/`

### 7B.3 No Hardcoded Values

**RULE: NO hardcoded lists, settings, or values anywhere**

| Wrong | Correct |
|-------|---------|
| `validators: [codex-global, claude-global]` | `validators: {{from_registry}}` |
| `model: claude` | `model: {{default_model}}` |
| `agents: [api-builder, test-engineer]` | `agents: {{from_agent_registry}}` |

All values must come from:
- Configuration files (`.agents/config/*.yml`)
- Registry queries (AgentRegistry, ValidatorRegistry)
- Dynamic generation at compose time

### 7B.4 Role-Based Architecture

**Three distinct roles with separate constitutions:**

| Role | Constitution File | Entry Point |
|------|------------------|-------------|
| **Orchestrator** | `constitution/ORCHESTRATOR.md` | `.claude/CLAUDE.md` → constitution |
| **Agent** | `constitution/AGENTS.md` | Agent prompt → constitution |
| **Validator** | `constitution/VALIDATORS.md` | Validator prompt → constitution |

**Key Principles:**
- Claude can act as ANY role (orchestrator/agent/validator)
- `.claude/CLAUDE.md` is Claude-specific, NOT role-specific
- Role constitutions contain role-specific instructions
- Each role reads ONLY its relevant constitution

### 7B.5 Constitution as Mandatory Read

**RULE: Constitutions REPLACE manifest.json and START.SESSION.md**

| Pre-Edison | Post-Edison |
|------------|-------------|
| `manifest.json` + `START.SESSION.md` | `constitution/ORCHESTRATOR.md` |
| Agent instructions in agent prompts | `constitution/AGENTS.md` (mandatory read) |
| Validator instructions in validator prompts | `constitution/VALIDATORS.md` (mandatory read) |

**Auto-injection:**
- Agent prompts automatically include: "Read constitution/AGENTS.md before starting"
- Validator prompts automatically include: "Read constitution/VALIDATORS.md before starting"
- Orchestrator session starts with constitution/ORCHESTRATOR.md as system prompt

### 7B.6 Constitution Composition

**Constitutions are ALSO composable:**

```
constitution/ORCHESTRATOR.md =
  core/constitution/orchestrator-base.md
  + packs/*/constitution/orchestrator-additions.md (if any)
  + project/constitution/orchestrator-overrides.md (if any)
```

**Constitution Content:**
1. Role identification ("You are an AGENT/VALIDATOR/ORCHESTRATOR")
2. Mandatory reads list (auto-generated from config)
3. Applicable rules (filtered by `applies_to` field)
4. Where to find this constitution file
5. RE-READ instruction on compaction/new session

### 7B.7 CLAUDE.md vs AGENTS.md Separation

**`.claude/CLAUDE.md`** - Claude-specific entry point:
- IDE integration settings
- Claude-specific tool configurations
- Link to project's AGENTS.md
- NOT role-specific (orchestrator/agent/validator)

**`AGENTS.md`** (generated) - Universal agent instructions:
- Common to ALL agent types (orchestrator/agent/validator)
- Project context and overview
- NOT role-specific instructions
- Generated from core + packs + project

**Role-specific instructions go in:**
- `constitution/ORCHESTRATOR.md` for orchestrators
- `constitution/AGENTS.md` for agents
- `constitution/VALIDATORS.md` for validators

### 7B.8 Compaction & Session Hooks

**RULE: Auto-remind on compaction/new session**

Add Claude hooks to:
1. Detect compaction events
2. Based on role type, remind to re-read constitution
3. Auto-inject constitution path in reminder

**Hook Implementation:**
```yaml
# .claude/hooks/compaction.yml
on_compaction:
  - action: remind_constitution
    message: "Session compacted. Re-read your constitution at {constitution_path}"
    determine_role: from_session_context
```

### 7B.9 Self-Identification in Generated Files

**RULE: Every generated file must self-identify**

```markdown
<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Source: core + packs(react, prisma) + project -->
<!-- Regenerate: scripts/prompts/compose --all -->
<!-- Role: AGENT -->
<!-- Constitution: .agents/_generated/constitution/AGENTS.md -->
<!-- RE-READ this file on each new session or compaction -->
```

### 7B.10 Summary: File Generation Matrix

| File Type | Core | Packs | Project | Generated To |
|-----------|------|-------|---------|--------------|
| Guidelines | ✅ | ✅ | ✅ | `_generated/guidelines/` |
| Rules | ✅ | ✅ | ✅ | `_generated/rules/` (or registry) |
| Agents | ✅ | ✅ | ✅ | `_generated/agents/` |
| Validators | ✅ | ✅ | ✅ | `_generated/validators/` |
| Constitution | ✅ | ✅ | ✅ | `_generated/constitution/` |
| AGENTS.md | ✅ | ✅ | ✅ | `_generated/AGENTS.md` |
| Rosters | - | - | - | `_generated/AVAILABLE_*.md` |

---

## 8. Constitution System Design

### 8.1 Problem Statement

Currently:
- Agent/validator lists are hardcoded in multiple places
- No single entry point for each role type
- Guidelines scattered without clear mandatory reads
- Rules not associated with specific role types
- **ORCHESTRATOR_GUIDE.md mixes concerns** (manifest data + workflow instructions + roster)
- **manifest.json and START.SESSION.md** need replacement with constitution system
- **No auto-reminder on compaction** to re-read constitution
- **No self-identification** in generated files

### 8.2 Decision: Replace ORCHESTRATOR_GUIDE.md with Constitution Folder

**ORCHESTRATOR_GUIDE.md will be DEPRECATED and REPLACED by the constitution/ folder structure.**

| Current (DEPRECATED) | New (Constitution) |
|---------------------|-------------------|
| `ORCHESTRATOR_GUIDE.md` (single file) | `constitution/ORCHESTRATOR.md` (entry point) |
| Embedded agent list | `AVAILABLE_AGENTS.md` (root of _generated/) |
| Embedded validator list | `AVAILABLE_VALIDATORS.md` (root of _generated/) |
| No agent/validator constitution | `constitution/AGENTS.md` + `constitution/VALIDATORS.md` |
| No role-based rules | Rules with `applies_to` field |

**Migration Path:**
1. Generate new constitution/ folder with 3 role files
2. Generate AVAILABLE_AGENTS.md and AVAILABLE_VALIDATORS.md at _generated/ root
3. Update `.claude/CLAUDE.md` to reference `constitution/ORCHESTRATOR.md`
4. Delete `ORCHESTRATOR_GUIDE.md` (or rename to `.deprecated/`)
5. Update `scripts/prompts/compose --orchestrator` to generate constitution/ instead

### 8.3 Proposed Architecture

```
.agents/_generated/
├── AVAILABLE_AGENTS.md            # NEW: Dynamic agent roster (root level)
├── AVAILABLE_VALIDATORS.md        # NEW: Dynamic validator roster (root level)
├── constitution/                   # NEW: Role-based entry points
│   ├── ORCHESTRATOR.md            # REPLACES: ORCHESTRATOR_GUIDE.md
│   ├── AGENTS.md                  # NEW: Agent constitution
│   └── VALIDATORS.md              # NEW: Validator constitution
├── agents/                        # Composed agent prompts
├── validators/                    # Composed validator prompts
└── guidelines/                    # Composed guidelines

# DELETED:
# ├── ORCHESTRATOR_GUIDE.md        # DEPRECATED - replaced by constitution/
```

### 8.3 Constitution File Specifications

#### constitution/ORCHESTRATOR.md
```markdown
# Orchestrator Constitution

## Mandatory Preloads
<!-- GENERATED: Do not edit directly -->
{{#each mandatoryReads.orchestrator}}
- {{this.path}}: {{this.purpose}}
{{/each}}

## Session Workflow
<!-- Link to SESSION_WORKFLOW.md -->

## Available Agents
<!-- GENERATED: From AgentRegistry -->
See: ../AVAILABLE_AGENTS.md

## Available Validators
<!-- GENERATED: From ValidatorRegistry -->
See: ../AVAILABLE_VALIDATORS.md

## Delegation Rules
<!-- GENERATED: From delegation.yml -->
{{#each delegationRules}}
- {{this.pattern}} → {{this.agent}} ({{this.model}})
{{/each}}

## Applicable Rules
<!-- GENERATED: Rules where applies_to includes 'orchestrator' -->
{{#each rules.orchestrator}}
### {{this.id}}: {{this.name}}
{{this.content}}
{{/each}}
```

#### constitution/AGENTS.md
```markdown
# Agent Constitution

## Mandatory Preloads (All Agents)
<!-- GENERATED: From config -->
{{#each mandatoryReads.agents}}
- {{this.path}}: {{this.purpose}}
{{/each}}

## Workflow Requirements
1. Follow MANDATORY_WORKFLOW.md
2. Query Context7 for post-training packages
3. Generate implementation report
4. Mark ready via edison CLI

## Output Format
See: guidelines/agents/OUTPUT_FORMAT.md

## Applicable Rules
<!-- GENERATED: Rules where applies_to includes 'agent' -->
{{#each rules.agent}}
### {{this.id}}: {{this.name}}
{{this.content}}
{{/each}}
```

#### constitution/VALIDATORS.md
```markdown
# Validator Constitution

## Mandatory Preloads (All Validators)
<!-- GENERATED: From config -->
{{#each mandatoryReads.validators}}
- {{this.path}}: {{this.purpose}}
{{/each}}

## Validation Workflow
1. Refresh Context7 knowledge
2. Review changes against criteria
3. Generate JSON report
4. Return verdict

## Output Format
See: guidelines/validators/OUTPUT_FORMAT.md

## Applicable Rules
<!-- GENERATED: Rules where applies_to includes 'validator' -->
{{#each rules.validator}}
### {{this.id}}: {{this.name}}
{{this.content}}
{{/each}}
```

### 8.4 Configuration Schema for Mandatory Reads

```yaml
# .edison/core/config/constitution.yaml
mandatoryReads:
  orchestrator:
    - path: constitution/ORCHESTRATOR.md
      purpose: Main entry point
    - path: guidelines/orchestrators/SESSION_WORKFLOW.md
      purpose: Session lifecycle
    - path: guidelines/shared/DELEGATION.md
      purpose: Delegation rules
    - path: AVAILABLE_AGENTS.md
      purpose: Agent roster
    - path: AVAILABLE_VALIDATORS.md
      purpose: Validator roster

  agents:
    - path: constitution/AGENTS.md
      purpose: Agent constitution
    - path: guidelines/agents/MANDATORY_WORKFLOW.md
      purpose: Implementation workflow
    - path: guidelines/agents/OUTPUT_FORMAT.md
      purpose: Report format
    - path: guidelines/shared/TDD.md
      purpose: TDD requirements
    - path: guidelines/agents/CONTEXT7_REQUIREMENT.md
      purpose: Context7 usage

  validators:
    - path: constitution/VALIDATORS.md
      purpose: Validator constitution
    - path: guidelines/validators/VALIDATOR_WORKFLOW.md
      purpose: Validation workflow
    - path: guidelines/validators/OUTPUT_FORMAT.md
      purpose: Report format
```

---

## 9. Dynamic Generation Architecture

### 9.1 Rules System Enhancement

Add `applies_to` field to rules registry:

```yaml
# .edison/core/rules/registry.yml
rules:
  RULE.TDD.RED_FIRST:
    name: "Test Must Fail First"
    content: "Write failing test before implementation code"
    applies_to: [agent, validator]
    severity: critical

  RULE.CONTEXT7.QUERY_BEFORE_CODE:
    name: "Query Context7 Before Coding"
    content: "Always query Context7 for post-training packages"
    applies_to: [agent, orchestrator]
    severity: critical

  RULE.DELEGATION.ORCHESTRATOR_ONLY:
    name: "Orchestrator Delegates"
    content: "Only orchestrator delegates; agents implement"
    applies_to: [orchestrator]
    severity: high

  RULE.VALIDATION.BUNDLE_FIRST:
    name: "Bundle Before Validate"
    content: "Create bundle before running validators"
    applies_to: [orchestrator]
    severity: high
```

### 9.2 Dynamic Agent Roster Generation

```python
# .edison/core/lib/composition/constitution.py
def generate_available_agents():
    """Generate AVAILABLE_AGENTS.md from AgentRegistry"""
    agents = AgentRegistry.get_all()

    return f"""# Available Agents
<!-- GENERATED: {datetime.now().isoformat()} -->
<!-- Do not edit directly - regenerate with: edison prompts compose -->

## Agent Roster

| Agent | Type | Pack | Model |
|-------|------|------|-------|
{format_agent_table(agents)}

## Agent Details

{format_agent_details(agents)}
"""
```

### 9.3 Dynamic Validator Roster Generation

```python
def generate_available_validators():
    """Generate AVAILABLE_VALIDATORS.md from ValidatorRegistry"""
    validators = ValidatorRegistry.get_all()

    return f"""# Available Validators
<!-- GENERATED: {datetime.now().isoformat()} -->

## Validator Roster

### Global Validators (Always Run)
{format_validator_section(validators.global)}

### Critical Validators (Blocking)
{format_validator_section(validators.critical)}

### Specialized Validators (Pattern-Triggered)
{format_validator_section(validators.specialized)}

## Validator Triggers

| Validator | File Patterns | Task Types |
|-----------|---------------|------------|
{format_trigger_table(validators)}
"""
```

### 9.4 Rule Extraction for Constitutions

```python
def extract_rules_for_role(role: str) -> List[Rule]:
    """Extract rules that apply to a specific role"""
    rules = RuleRegistry.get_all()
    return [r for r in rules if role in r.applies_to]

def embed_rules_in_constitution(constitution: str, role: str) -> str:
    """Embed applicable rules directly in constitution"""
    rules = extract_rules_for_role(role)
    rules_section = format_rules_section(rules)
    return constitution.replace("{{EMBEDDED_RULES}}", rules_section)
```

---

## 10. Implementation Tasks

### 10.1 Priority 1: CRITICAL (Blocking)

| Task ID | Task | Files Affected | Est. Hours |
|---------|------|----------------|------------|
| P1-001 | Restore EPHEMERAL_SUMMARIES_POLICY.md | `.edison/core/guidelines/shared/` | 1 |
| P1-002 | Remove pack section duplication in validators | `codex-global.md`, `claude-global.md` | 2 |
| P1-003 | Restore MANDATORY WORKFLOW references in all agents | 6 agent files | 1 |
| P1-004 | Restore Context7 MCP explicit examples | All agents + global validators | 2 |
| P1-005 | Fix broken config/defaults.yaml duplicate keys | `.edison/core/config/defaults.yaml` | 0.5 |
| P1-006 | Delete duplicate codex-core.md | `.edison/core/validators/global/` | 0.5 |
| P1-007 | Restore SESSION_WORKFLOW extended guide | `.edison/core/guides/extended/` | 2 |

**Subtotal: ~9 hours**

### 10.2 Priority 2: HIGH (Missing Content)

| Task ID | Task | Files Affected | Est. Hours |
|---------|------|----------------|------------|
| P2-001 | Restore YAML frontmatter to all agents | 6 agent files | 1 |
| P2-002 | Restore Configuration Authority sections | 5 implementer agents | 1.5 |
| P2-003 | Restore version tables in global validators | `codex-global.md`, `claude-global.md` | 1 |
| P2-004 | Restore Common Mistakes to Avoid sections | Global validators | 1.5 |
| P2-005 | Restore TDD detailed sections | `TDD.md` | 2 |
| P2-006 | Restore code examples to all agents | All 6 agents | 3 |
| P2-007 | Restore security validator checks | `security.md` | 1.5 |
| P2-008 | Restore performance validator checks | `performance.md` | 1.5 |
| P2-009 | Resolve placeholder tokens in guidelines | TDD, DELEGATION, VALIDATION | 2 |
| P2-010 | Restore orchestrator missing instructions | CLAUDE.md, ORCHESTRATOR_GUIDE | 2 |

**Subtotal: ~17 hours**

### 10.3 Priority 3: MEDIUM (Organization/Cleanup)

| Task ID | Task | Files Affected | Est. Hours |
|---------|------|----------------|------------|
| P3-001 | Remove all __pycache__ directories | 24+ directories | 0.5 |
| P3-002 | Remove/gitignore .agents/.cache/ | Cache directory | 0.5 |
| P3-003 | Remove Wilson-specific content from core | `defaults.yaml`, QUALITY.md | 1 |
| P3-004 | Fix truncated wilson-architecture.md | `_generated/guidelines/` | 0.5 |
| P3-005 | Remove duplicate defaults.yaml | `.edison/core/defaults.yaml` | 0.5 |
| P3-006 | Remove duplicate api.md in packs | `fastify/`, `nextjs/` | 1 |
| P3-007 | Clean up empty directories | `.edison/.agents/` | 0.5 |
| P3-008 | Remove temporary scratch files | `.edison/tmp-*.md` | 0.5 |

**Subtotal: ~5 hours**

### 10.4 Priority 4: ENHANCEMENTS (Architecture)

| Task ID | Task | Description | Est. Hours |
|---------|------|-------------|------------|
| P4-001 | Create constitution system | `_generated/constitution/*.md` | 4 |
| P4-002 | Add `applies_to` field to rules | Rule registry enhancement | 2 |
| P4-003 | Extract duplicated agent sections | Move to shared guidelines | 3 |
| P4-004 | Restore validator config richness | Priority, blocking, triggers | 2 |
| P4-005 | Restore delegation config richness | Model profiles, defaults | 2 |
| P4-006 | Implement dynamic roster generation | Composition system update | 4 |
| P4-007 | Create AVAILABLE_AGENTS.md generator | New generator | 2 |
| P4-008 | Create AVAILABLE_VALIDATORS.md generator | New generator | 2 |
| P4-009 | Add mandatory reads config | `constitution.yaml` | 1 |
| P4-010 | Embed rules in constitutions | Template enhancement | 2 |

**Subtotal: ~24 hours**

### 10.5 Task Summary

| Priority | Tasks | Hours |
|----------|-------|-------|
| P1 CRITICAL | 7 | 9 |
| P2 HIGH | 10 | 17 |
| P3 MEDIUM | 8 | 5 |
| P4 ENHANCEMENT | 10 | 24 |
| **TOTAL** | **35** | **55** |

---

## 11. Independent Re-Analysis Results

**Re-Analysis Date:** 2025-11-25
**Validators Used:** 10 (5 Codex via Zen MCP + 5 Claude Opus subagents)
**Status:** COMPLETE

### 11.1 Re-Analysis Scope
- ✅ Fresh comparison of all 6 agents (pre-Edison vs post-Edison)
- ✅ Fresh comparison of all 11 validators (pre-Edison vs post-Edison)
- ✅ CLAUDE.md and ORCHESTRATOR_GUIDE.md analysis
- ✅ Guidelines migration completeness check
- ✅ Constitution System gap analysis

---

### 11.2 Agent Re-Analysis Findings

#### Critical: All 6 Agents Missing zenRole Frontmatter
Pre-Edison agents had `zenRole: wilson-<agent-name>` in YAML frontmatter for Zen MCP clink integration. ALL 6 post-Edison agents are missing this field entirely.

| Agent | Pre-Edison zenRole | Post-Edison Status |
|-------|-------------------|-------------------|
| api-builder | `wilson-api-builder` | ❌ MISSING |
| code-reviewer | `wilson-code-reviewer` | ❌ MISSING |
| component-builder | `wilson-component-builder` | ❌ MISSING |
| database-architect | `wilson-database-architect` | ❌ MISSING |
| feature-implementer | `wilson-feature-implementer` | ❌ MISSING |
| test-engineer | `wilson-test-engineer` | ❌ MISSING |

#### Critical: Missing Frontmatter Fields (ALL 6 agents)
```yaml
# MISSING FROM ALL POST-EDISON AGENTS:
zenRole: wilson-<agent-name>      # Zen MCP integration
context7_ids: []                   # Explicit Context7 library IDs
allowed_tools: []                  # Tool access control
requires_validation: true          # Validator requirements
```

#### High: Content Reduction Metrics
| Agent | Pre-Edison Lines | Post-Edison Lines | Reduction |
|-------|-----------------|-------------------|-----------|
| component-builder | ~553 | ~303 | **45%** |
| database-architect | ~464 | ~209 | **55%** |
| api-builder | ~375 | ~365 | 3% |
| code-reviewer | ~418 | ~401 | 4% |
| feature-implementer | ~428 | ~323 | 25% |
| test-engineer | ~578 | ~490 | 15% |

#### High: Missing Agent Sections
1. **CONFIGURATION AUTHORITY** - Removed from api-builder, component-builder, database-architect
2. **Context7 workflow examples** - Explicit mcp__context7 code examples removed
3. **Tailwind CSS v4 detailed rules** - 50+ lines reduced significantly
4. **Motion 12 animation patterns** - Removed from component-builder
5. **Forms with Validation (Zod)** - Removed from component-builder
6. **Prisma Schema Patterns** - Comprehensive examples reduced

---

### 11.3 Validator Re-Analysis Findings

#### CRITICAL: Pack Section Duplication Bug

The composition engine is injecting pack context **multiple times** instead of once:

| Validator | Pack Duplications | Expected | Bloat Factor |
|-----------|------------------|----------|--------------|
| claude-global.md | **7x** | 1x | 3.27x (24KB → 79KB) |
| codex-global.md | **5x** | 1x | 2.71x (22KB → 61KB) |

**Exact Line Numbers for claude-global.md Next.js Duplications:**
- Lines: 73, 424, 859, 1175, 1725, 1993, 2275

#### CRITICAL: Missing Version Tables
Pre-Edison validators had explicit package version tables:
```markdown
| Package | Version | Critical Issues |
|---------|---------|-----------------|
| Next.js | 16.0.0 | Major App Router changes |
| React | 19.2.0 | New use() hook, Server Components |
| Tailwind CSS | 4.0.0 | COMPLETELY different syntax |
| Zod | 4.1.12 | Breaking changes from v3 API |
| Motion | 12.23.24 | API changes (formerly Framer Motion) |
| TypeScript | 5.7.0 | New type inference features |
```
**Post-Edison Status:** MISSING - no version tables found

#### CRITICAL: Missing Context7 Tool Examples
- Pre-Edison: **4 explicit mcp__context7 tool call examples**
- Post-Edison: **1 generic reference**

Pre-Edison examples included:
```typescript
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: '/vercel/next.js',
  topic: 'route handlers, app router patterns...'
})
```

#### Validators Missing Pack Context
| Validator | Pack Sections | Status |
|-----------|--------------|--------|
| security.md | 0 | ❌ No framework-specific security patterns |
| performance.md | 0 | ❌ No framework-specific performance guidance |

---

### 11.4 Orchestrator Re-Analysis Findings

#### Missing Preloads in CLAUDE.md
| Preload | Pre-Edison | Post-Edison |
|---------|------------|-------------|
| manifest.json | ✅ Explicit | ❌ Missing |
| IMPLEMENTER_WORKFLOW.md | ✅ Listed | ❌ Missing |
| VALIDATOR_WORKFLOW.md | ✅ Listed | ❌ Not in framework preloads |
| HONEST_STATUS.md | ✅ Listed | ❌ Missing |
| VALIDATION.md | ✅ Listed | ❌ Missing |
| QUALITY.md | ✅ Listed | ❌ Missing |
| CONTEXT7.md | ✅ Listed | ❌ Missing |
| GIT_WORKFLOW.md | ✅ Listed | ❌ Missing |
| EPHEMERAL_SUMMARIES_POLICY.md | ✅ Listed | ❌ Missing |
| rules/registry.json | ✅ Listed | ❌ Missing |
| validators/config.json | ✅ Listed | ❌ Missing |
| delegation/config.json | ✅ Listed | ❌ Missing |

#### Hardcoded Lists Found
**Location:** .claude/CLAUDE.md lines 47-59, 117-120
```
HARDCODED AGENTS:
- component-builder-nextjs
- api-builder
- database-architect-prisma
- test-engineer
- feature-implementer

HARDCODED VALIDATORS:
- codex-global, claude-global, security, database, testing
```
**Should:** Reference dynamic roster from ORCHESTRATOR_GUIDE.md

#### Missing Critical Sections
1. **Manifest preload instruction** - No equivalent to "Load .agents/manifest.json first"
2. **Task split guidance** - `scripts/tasks/split` not documented
3. **Bundle-first rule** - Not in CLAUDE.md entry point
4. **START.SESSION.md equivalent** - No dedicated intake checklist

#### Delegation Rules Incomplete
- Pre-Edison: **16 file patterns**, **10 task types**
- Post-Edison: **10 file patterns**, **4 task types**

Missing patterns:
- `**/page.tsx → component-builder`
- `**/loading.tsx → component-builder`
- `**/error.tsx → component-builder`
- `**/middleware.ts → api-builder`
- `**/lib/**/*.ts → feature-implementer`
- `**/types/**/*.ts → api-builder`

---

### 11.5 Guidelines Re-Analysis Findings

#### Missing Guidelines
| Guideline | Pre-Edison | Post-Edison |
|-----------|------------|-------------|
| AUTH_TESTING_GUIDE.md | ✅ | ❌ NOT MIGRATED |
| Extended SESSION_WORKFLOW.md | ✅ Referenced | ❌ File doesn't exist |
| IMPLEMENTER_WORKFLOW.md | ✅ Referenced | ❌ File doesn't exist |

#### Unresolved Placeholders Found (8 instances)

| Placeholder | File | Line |
|-------------|------|------|
| `{{framework}}` | .edison/core/guidelines/README.md | 31 |
| `{{orm}}` | .edison/core/guidelines/README.md | 32 |
| `{{test-framework}}` | .edison/core/guidelines/README.md | 33 |
| `{{component-framework}}` | .edison/core/guidelines/shared/VALIDATION.md | 20 |
| `{{web-framework}}` | .edison/core/guidelines/shared/VALIDATION.md | 20 |
| `{{library}}` | .edison/core/guidelines/shared/CONTEXT7.md | 47 |
| `{{web-framework}}` | .edison/core/guides/extended/TDD.md | 64 |

#### Broken Cross-References (6 instances)

| Source File | Reference | Issue |
|-------------|-----------|-------|
| orchestrators/SESSION_WORKFLOW.md:6 | `../../guides/extended/SESSION_WORKFLOW.md` | File doesn't exist |
| agents/CONTEXT7_REQUIREMENT.md:254 | `CONTEXT7_GUIDE.md` | Named `CONTEXT7.md` |
| agents/DELEGATION_AWARENESS.md:177 | `DELEGATION_GUIDE.md` | Named `DELEGATION.md` |
| agents/MANDATORY_WORKFLOW.md:154 | `IMPLEMENTER_WORKFLOW.md` | File doesn't exist |
| agents/IMPORTANT_RULES.md:314 | `QUALITY_STANDARDS.md` | Named `QUALITY.md` |
| agents/VALIDATION_AWARENESS.md:216 | `VALIDATION_GUIDE.md` | Named `VALIDATION.md` |

---

### 11.6 Constitution System Gap Analysis

#### Current State Assessment
| Requirement | Status | Details |
|-------------|--------|---------|
| constitution.yaml exists | ❌ | No central config file |
| Role-based mandatory reads | ⚠️ Partial | Hardcoded in orchestrator.py:288-303 |
| Dynamic roster generation | ✅ | AgentRegistry and validators work |
| AVAILABLE_AGENTS.md | ❌ | Not generated as standalone file |
| AVAILABLE_VALIDATORS.md | ❌ | Not generated as standalone file |
| Rules `applies_to` field | ❌ | No role-based filtering |
| Role-based rule query API | ❌ | get_rules_for_role() doesn't exist |

#### Critical Constitution Gaps (4)

1. **GAP-C1: Missing constitution.yaml**
   - No central configuration for role-based mandatory reads
   - Currently hardcoded in Python code

2. **GAP-C2: Rules lack 'applies_to' field**
   - Rules use 'category' but can't filter by orchestrator/agent/validator role

3. **GAP-C3: No role-based rule query**
   - RulesEngine.get_rules_for_context() can't filter by role type

4. **GAP-C4: Hardcoded mandatory guidelines**
   - collect_mandatory_guidelines() hardcodes SESSION_WORKFLOW.md, DELEGATION.md, TDD.md

---

### 11.7 New Implementation Tasks from Re-Analysis

#### P0 - IMMEDIATE (Blocking Functionality)

| Task ID | Description | Effort |
|---------|-------------|--------|
| **RE-001** | Fix pack duplication bug in composition engine | 2h |
| **RE-002** | Add zenRole to all 6 agent frontmatter | 1h |
| **RE-003** | Create missing SESSION_WORKFLOW.md extended guide | 1h |
| **RE-004** | Create missing IMPLEMENTER_WORKFLOW.md | 1h |

#### P1 - HIGH (Restore Critical Content)

| Task ID | Description | Effort |
|---------|-------------|--------|
| **RE-005** | Add version table generation to composition | 2h |
| **RE-006** | Restore Context7 tool call examples (4 calls) | 1h |
| **RE-007** | Add pack context to security.md | 1h |
| **RE-008** | Add pack context to performance.md | 1h |
| **RE-009** | Fix 6 broken cross-references (naming mismatch) | 1h |
| **RE-010** | Resolve 8 unresolved placeholders | 1h |
| **RE-011** | Restore CONFIGURATION AUTHORITY to 3 agents | 1h |
| **RE-012** | Add missing file patterns to delegation (6 patterns) | 1h |
| **RE-013** | Add missing task types to delegation (6 types) | 1h |

#### P2 - MEDIUM (Complete Migration)

| Task ID | Description | Effort |
|---------|-------------|--------|
| **RE-014** | Migrate AUTH_TESTING_GUIDE.md content | 2h |
| **RE-015** | Add context7_ids frontmatter to all agents | 1h |
| **RE-016** | Add allowed_tools frontmatter to all agents | 1h |
| **RE-017** | Add requires_validation frontmatter to all agents | 1h |
| **RE-018** | Restore Tailwind v4 detailed rules to component-builder | 1h |
| **RE-019** | Restore Motion 12 patterns to component-builder | 1h |
| **RE-020** | Restore Prisma schema examples to database-architect | 1h |
| **RE-021** | Add manifest preload equivalent to CLAUDE.md | 1h |
| **RE-022** | Add task split guidance to orchestrator docs | 1h |

#### P3 - CONSTITUTION SYSTEM (Replaces ORCHESTRATOR_GUIDE.md)

| Task ID | Description | Effort |
|---------|-------------|--------|
| **RE-023** | Create constitution.yaml with role-based reads | 3h |
| **RE-024** | Add 'applies_to' field to rules registry schema | 2h |
| **RE-025** | Add get_rules_for_role() to RulesEngine | 2h |
| **RE-026** | Generate _generated/AVAILABLE_AGENTS.md from registry | 1h |
| **RE-027** | Generate _generated/AVAILABLE_VALIDATORS.md from registry | 1h |
| **RE-028** | Create constitution.schema.json | 1h |
| **RE-029** | Move mandatory guidelines from hardcoded to config | 1h |
| **RE-030** | Generate constitution/ORCHESTRATOR.md (replaces ORCHESTRATOR_GUIDE.md) | 2h |
| **RE-031** | Generate constitution/AGENTS.md | 1h |
| **RE-032** | Generate constitution/VALIDATORS.md | 1h |
| **RE-034** | Update compose --orchestrator to generate constitution/ folder | 2h |
| **RE-035** | Deprecate/delete ORCHESTRATOR_GUIDE.md | 0.5h |

---

### 11.8 Summary Statistics

| Category | Count | Status |
|----------|-------|--------|
| Critical Issues Confirmed | 15 | From initial + 4 new |
| High Issues Confirmed | 28 | From initial + 10 new |
| New Tasks Added | 35 | RE-001 through RE-035 |
| Total Estimated Hours | ~45.5h | For all RE-* tasks |

#### Task Breakdown by Priority
| Priority | Tasks | Hours |
|----------|-------|-------|
| P0 IMMEDIATE | 4 | 5h |
| P1 HIGH | 9 | 11h |
| P2 MEDIUM | 9 | 11h |
| P3 CONSTITUTION | 13 | 18.5h |

### 11.9 Validator Agreement

**Codex vs Opus Agreement Rate: 100%**

Both validator sets independently found:
- ✅ Pack duplication bug (exact same line numbers)
- ✅ Missing zenRole frontmatter (all 6 agents)
- ✅ Missing version tables
- ✅ Missing Context7 examples
- ✅ Constitution system gaps
- ✅ Broken cross-references
- ✅ Unresolved placeholders

---

## Appendix A: File Inventory

### Pre-Edison Files Analyzed
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/
├── agents/
│   ├── api-builder.md (374 lines)
│   ├── component-builder.md (552 lines)
│   ├── database-architect.md (463 lines)
│   ├── code-reviewer.md (417 lines)
│   ├── test-engineer.md (577 lines)
│   └── feature-implementer.md (428 lines)
├── validators/
│   ├── global/codex-global.md
│   ├── global/claude-global.md
│   ├── security/codex-security.md
│   ├── performance/codex-performance.md
│   └── specialized/{api,nextjs,testing,react,prisma}.md
├── guides/
│   └── extended/{TDD_GUIDE,DELEGATION,SESSION_WORKFLOW,VALIDATION_GUIDE,QUALITY_STANDARDS}.md
├── guidelines/
│   └── {CONTEXT7,HONEST_STATUS,GIT_WORKFLOW,EPHEMERAL_SUMMARIES_POLICY}.md
├── START.SESSION.md
├── AGENTS.md
└── manifest.json
```

### Post-Edison Files Generated
```
/Users/leeroy/Documents/Development/wilson-leadgen/.agents/_generated/
├── agents/
│   ├── api-builder.md
│   ├── component-builder.md
│   ├── database-architect.md
│   ├── code-reviewer.md
│   ├── test-engineer.md
│   └── feature-implementer.md
├── validators/
│   ├── codex-global.md
│   ├── claude-global.md
│   ├── security.md
│   ├── performance.md
│   ├── api.md
│   ├── nextjs.md
│   ├── testing.md
│   ├── react.md
│   └── database.md
├── guidelines/
│   ├── agents/
│   ├── validators/
│   ├── orchestrators/
│   └── shared/
└── ORCHESTRATOR_GUIDE.md
```

---

## Appendix B: Validator Cross-Reference

### Codex vs Opus Agreement Matrix

| Finding Area | Codex Found | Opus Found | Agreement |
|--------------|-------------|------------|-----------|
| Agent YAML frontmatter missing | ✅ | ✅ | 100% |
| Context7 examples removed | ✅ | ✅ | 100% |
| Pack section duplication | ✅ | ✅ | 100% |
| EPHEMERAL_SUMMARIES missing | ✅ | ✅ | 100% |
| Validator config path change | ✅ | ✅ | 100% |
| Hardcoded lists in ORCHESTRATOR | ✅ | ✅ | 100% |
| Missing code examples | ✅ | ✅ | 100% |
| Duplicate files found | ✅ | ✅ | 100% |

**Overall Agreement: 100%** - Both validator sets found the same critical issues.

---

## 12. Deep File-by-File Analysis Results

This section contains the comprehensive findings from 24+ parallel validators analyzing every file in the pre-Edison `.agents/` folder against post-Edison equivalents.

### 12.1 Validation Methodology (Round 2)

**Validators Used:**
- 6 Claude Opus validators for agents/ folder
- 3 Task-based validators for delegation/ folder
- 6 Task-based validators for guidelines/ folder
- 3 Task-based validators for rules/ and validators/ folders
- 2 Task-based validators for entry points

**Comparison Criteria:**
- Section counts (pre vs post)
- Missing instructions (exact count)
- Missing code examples (exact count)
- Architectural violations
- YAML frontmatter compliance
- Constitution reference compliance
- Hardcoded values detection

---

### 12.2 Agent Files - Complete Analysis

#### 12.2.1 api-builder.md

| Metric | Pre-Edison | Post-Edison | Delta |
|--------|-----------|-------------|-------|
| **Lines** | 375 | 361 | -14 |
| **Sections** | 16 | 12 | -4 |
| **Code Examples** | 8 | 1 | -7 |
| **Instructions** | 42+ | ~15 | -27 |

**CRITICAL Missing Content:**
1. ❌ YAML Frontmatter (name, description, model, zenRole: wilson-api-builder)
2. ❌ MANDATORY WORKFLOW section with failure warning
3. ❌ Context7 MCP code example (resolve-library-id + get-library-docs)
4. ❌ Complete 80-line route handler example
5. ❌ 9-validator architecture explanation
6. ❌ 4-step delegation workflow with checkmarks
7. ❌ Tech Stack section (Fastify API + Next.js Proxy)
8. ❌ "Why Critical" explanations for guides

**Severity:** 🔴 CRITICAL

---

#### 12.2.2 component-builder.md

| Metric | Pre-Edison | Post-Edison | Delta |
|--------|-----------|-------------|-------|
| **Lines** | 552 | 298 | -254 (46%) |
| **Sections** | 30 | 24 | -6 |
| **Code Examples** | 10+ | 3 | -7 |
| **Instructions** | 60+ | ~20 | -40 |

**CRITICAL Missing Content:**
1. ❌ YAML Frontmatter
2. ❌ Tailwind CSS v4 Deep Dive (critical - "syntax COMPLETELY different from v3")
3. ❌ Server Components code example (with Prisma query)
4. ❌ Client Components code example (with Motion animations)
5. ❌ Animations with Motion 12 patterns
6. ❌ Forms with Validation (Zod + form handling)
7. ❌ Design System Rules (colors, typography, spacing)
8. ❌ Context7 workflow with code example
9. ❌ 8 IMPORTANT RULES (numbered list)
10. ❌ CONFIGURATION AUTHORITY section

**Severity:** 🔴 CRITICAL

---

#### 12.2.3 database-architect.md

| Metric | Pre-Edison | Post-Edison | Delta |
|--------|-----------|-------------|-------|
| **Lines** | 464 | 205 | -259 (56%) |
| **Sections** | 21 | 14 | -7 |
| **Code Examples** | 12 | 0 | -12 |
| **Instructions** | 40+ | ~15 | -25 |

**CRITICAL Missing Content:**
1. ❌ YAML Frontmatter
2. ❌ Complete Prisma schema.prisma template (40+ lines)
3. ❌ Full Lead model example with comments
4. ❌ Migration workflow bash commands (5-step)
5. ❌ Rollback strategy commands (3-step)
6. ❌ Index strategy examples (single + composite)
7. ❌ Query optimization (good vs bad examples)
8. ❌ Zod + Prisma integration code
9. ❌ Complete one-to-many Prisma example
10. ❌ Complete many-to-many join table example
11. ❌ Migration safety (safe vs dangerous operations)
12. ❌ 7 IMPORTANT RULES

**Severity:** 🔴 CRITICAL

---

#### 12.2.4 code-reviewer.md

| Metric | Pre-Edison | Post-Edison | Delta |
|--------|-----------|-------------|-------|
| **Lines** | 418 | 397 | -21 |
| **Sections** | 11 | 12 | +1 |
| **Code Examples** | 3 | 2 | -1 |
| **Instructions** | 30+ | ~20 | -10 |

**CRITICAL Missing Content:**
1. ❌ YAML Frontmatter
2. ❌ Context7 MCP tool call example with exact parameters
3. ❌ Version gap warnings (Next 16, React 19, Tailwind 4, Prisma 6)
4. ❌ "Quality Assurance Specialist" subtitle
5. ❌ Validation architecture (9-validator system explanation)
6. ❌ Why no delegation reasoning (4 bullet points)
7. ❌ MANDATORY WORKFLOW failure warning
8. ❌ Red flags list (5 TDD violations)
9. ❌ EPHEMERAL_SUMMARIES_POLICY reference

**Severity:** 🔴 CRITICAL

---

#### 12.2.5 test-engineer.md

| Metric | Pre-Edison | Post-Edison | Delta |
|--------|-----------|-------------|-------|
| **Lines** | 578 | 486 | -92 |
| **Sections** | 12 | 12 | 0 |
| **Code Examples** | 12 | 9 | -3 |
| **Instructions** | 18+ | ~12 | -6 |

**CRITICAL Missing Content:**
1. ❌ YAML Frontmatter
2. ❌ Context7 MCP call example
3. ❌ mcp__wilson-zen__clink delegation example
4. ❌ Weak vs strong test comparison
5. ❌ Tech Stack standalone section
6. ❌ Specific entity examples (prisma.lead vs db.record)
7. ❌ Specific external APIs (Odoo, Piloterr)
8. ❌ Version footer with line count

**Severity:** 🟠 HIGH

---

#### 12.2.6 feature-implementer.md

| Metric | Pre-Edison | Post-Edison | Delta |
|--------|-----------|-------------|-------|
| **Lines** | 429 | 319 | -110 (26%) |
| **Sections** | 17 | 13 | -4 |
| **Code Examples** | 2 | 0 | -2 |
| **Instructions** | 47+ | ~20 | -27 |

**CRITICAL Missing Content:**
1. ❌ YAML Frontmatter
2. ❌ Context7 MCP TypeScript call example
3. ❌ Tailwind v4 syntax examples (font-sans, cache clearing)
4. ❌ Tech Stack section with "NOT Fastify!" warning
5. ❌ Premium Design Standards (8pt grid, tokens, dark mode)
6. ❌ Quality Standards checklist (8 items)
7. ❌ MANDATORY WORKFLOW section
8. ❌ Validation architecture details (9 validators)

**Severity:** 🔴 CRITICAL

---

### 12.3 Delegation Files - Complete Analysis

#### 12.3.1 config.json → delegation.yml

| Metric | Pre-Edison | Post-Edison | Delta |
|--------|-----------|-------------|-------|
| **Entries** | 61+ | 5 | -56 (92%) |
| **File Patterns** | 16 | 0 | -16 |
| **Task Types** | 11 | 0 | -11 |
| **Sub-agent Defaults** | 6 | 5 | -1 |
| **Zen MCP Roles** | 18 | 5 | -13 |

**CRITICAL Missing Content:**
1. ❌ 16 file pattern rules (*.tsx→claude, schema.prisma→codex, etc.)
2. ❌ 11 task type rules (api-route, ui-component, full-stack-feature)
3. ❌ 9 validator Zen MCP roles (wilson-validator-*)
4. ❌ Model definitions with strengths/weaknesses
5. ❌ Priority chain enforcement logic
6. ❌ Orchestrator guidance frameworks

**Impact:** Automatic delegation BROKEN - every task requires manual selection

**Severity:** 🔴 CRITICAL

---

#### 12.3.2 README.md → DELEGATION.md

| Gap | Status |
|-----|--------|
| Tool name migration (wilson-zen→edison-zen) | ⚠️ Examples not updated |
| Config architecture | ❌ Mismatch (26KB→21 lines) |
| OUTPUT_FORMAT.md | ❌ MISSING |
| Session worktree requirement | ⚠️ Not consistently emphasized |
| Decision authority | ⚠️ Conflicting (config guides vs sub-agent decides) |

**Severity:** 🔴 CRITICAL

---

#### 12.3.3 OUTPUT_FORMAT.md

| Metric | Pre-Edison | Post-Edison | Delta |
|--------|-----------|-------------|-------|
| **Lines** | 90 | 42 | -48 (53%) |
| **Fields Documented** | 8 | 4 | -4 |

**CRITICAL Issues:**
1. ❌ Schema field name violations (to vs filePattern, result vs outcome)
2. ❌ Missing `role` field (REQUIRED in schema)
3. ❌ Missing standalone delegation report format
4. ❌ Missing CLI documentation
5. ❌ Example CONTRADICTS actual schema

**Severity:** 🔴 CRITICAL

---

### 12.4 Guidelines Files - Complete Analysis

#### 12.4.1 TDD.md
**Status:** ✅ 95% Complete - Production Ready
- Minor: Docker quick start missing
- Minor: Performance targets relocated to extended guide
- Minor: Coverage inconsistency (80% vs 90%)

**Severity:** 🟢 LOW

---

#### 12.4.2 VALIDATION.md
**Status:** ⚠️ 70% Complete

**Missing:**
1. ❌ Round N rejection cycle documentation
2. ❌ Session tracking ("Last Active")
3. ❌ Gemini Global validator (undocumented)
4. ❌ Blocking config per validator in YAML

**Severity:** 🟠 HIGH

---

#### 12.4.3 SESSION_WORKFLOW.md
**Status:** ⚠️ INCOMPLETE MIGRATION

**Key Issues:**
1. ❌ Missing extended SESSION_WORKFLOW.md (referenced but doesn't exist!)
2. ❌ QA guards simplified to `always_allow` without explanation
3. ❌ Session conditions undefined (`can_complete_session`, etc.)
4. State machine grew 46% (3→9 states, 2→12 transitions)

**Severity:** 🔴 CRITICAL

---

#### 12.4.4 DELEGATION.md
**Status:** ✅ 99% Complete
- All 5 priority chain levels verified
- All 4 core delegation rules preserved
- Minor: MISMATCH pattern only in awareness doc

**Severity:** 🟢 LOW

---

#### 12.4.5 CONTEXT7.md
**Status:** ✅ 95% Complete
- All MCP tools documented (+ 2 new tools added)
- Minor: Framer-Motion and Better-Auth packages missing

**Severity:** 🟢 LOW

---

#### 12.4.6 QUALITY.md
**Status:** ⚠️ 50% Reduction

**Missing:**
1. ❌ Pattern 1/2 architecture guidance (CRITICAL REMOVAL)
2. ❌ Docker-compose command
3. ❌ WCAG AA downgraded to implicit Level A
4. ❌ Theme-aware UI requirement

**Severity:** 🟠 HIGH

---

### 12.5 Rules & Validators - Complete Analysis

#### 12.5.1 Rules Registry
**Status:** ✅ 100% Complete
- All 37 rules preserved
- Schema evolved v1.0.0 → v2.0.0
- All 7 categories maintained

**Severity:** 🟢 LOW

---

#### 12.5.2 Validators Configuration
**Status:** ✅ 100% Migration (10/10 validators)
- 2 new validators added (gemini-global, styling)
- Blocking status bug fixed (react/nextjs/api now correctly non-blocking)

**Severity:** 🟢 LOW

---

#### 12.5.3 Validators README
**Status:** ⚠️ Significant Documentation Loss

**Missing:**
1. ❌ Orchestrator validator invocation guide (6 code examples)
2. ❌ Validator execution flow diagram (6-step ASCII)
3. ❌ Approval criteria decision matrix
4. ❌ Troubleshooting guide (4 scenarios)

**Severity:** 🟠 HIGH

---

### 12.6 Entry Points - Complete Analysis

#### 12.6.1 AGENTS.md
**Status:** 🔴 CRITICAL GAPS

**Missing:**
1. ❌ START.SESSION.md intake checklist (35 lines)
2. ❌ START.AUDIT.md (27 lines)
3. ❌ 94% of mandatory preload list (19→3 items)
4. ❌ Session workflow loop documentation
5. ❌ CLI commands reference section

**Severity:** 🔴 CRITICAL

---

#### 12.6.2 START.SESSION.md
**Status:** 🔴 CRITICAL GAPS

**Root Causes:**
1. ❌ File is TEMPLATED (not actionable) - contains {session_id}, {process} placeholders
2. ❌ Circular dependency - SESSION_WORKFLOW assumes intake done, but START.SESSION is templated
3. ❌ 4 missing explicit steps:
   - Confirm human request
   - Close assigned work
   - Shared QA boundary rule
   - Intake complete declaration

**Impact:** Sessions may start without proper context, orphaned work, missing safeguards

**Severity:** 🔴 CRITICAL

---

### 12.7 Summary Statistics (Round 2)

#### Overall Migration Completeness

| Domain | Files | Complete | Partial | Critical Gaps |
|--------|-------|----------|---------|---------------|
| **Agents** | 6 | 0 | 1 | 5 |
| **Delegation** | 3 | 0 | 0 | 3 |
| **Guidelines** | 6 | 3 | 2 | 1 |
| **Rules** | 1 | 1 | 0 | 0 |
| **Validators** | 2 | 1 | 1 | 0 |
| **Entry Points** | 2 | 0 | 0 | 2 |
| **TOTAL** | 20 | 5 (25%) | 4 (20%) | 11 (55%) |

#### Content Loss Summary

| Category | Pre-Edison Lines | Post-Edison Lines | Loss |
|----------|-----------------|-------------------|------|
| Agent files | 2,814 | 2,066 | -748 (27%) |
| Delegation config | 772 | 21 | -751 (97%) |
| Code examples | 60+ | ~15 | -45 (75%) |
| Instructions | 250+ | ~100 | -150 (60%) |

#### Blocking Issues Count

| Severity | Count | Examples |
|----------|-------|----------|
| 🔴 CRITICAL | 11 | YAML frontmatter, delegation config, entry points |
| 🟠 HIGH | 8 | Code examples, validator docs, quality standards |
| 🟡 MEDIUM | 5 | Version tables, minor sections |
| 🟢 LOW | 3 | Format improvements |

---

### 12.8 Prioritized Remediation Plan (Updated)

#### PHASE 1: BLOCKING ISSUES (Immediate - 8h)

| Task | Description | Hours |
|------|-------------|-------|
| FIX-001 | Add YAML frontmatter to all 6 agents | 1h |
| FIX-002 | Restore delegation config (16 patterns, 11 types) | 2h |
| FIX-003 | Fix START.SESSION.md (remove templates, add 9 steps) | 1h |
| FIX-004 | Create missing extended SESSION_WORKFLOW.md | 2h |
| FIX-005 | Fix OUTPUT_FORMAT.md schema violations | 1h |
| FIX-006 | Add mandatory preloads to AGENTS.md | 1h |

#### PHASE 2: CRITICAL CONTENT (High Priority - 12h)

| Task | Description | Hours |
|------|-------------|-------|
| FIX-007 | Restore Context7 MCP examples to all agents | 2h |
| FIX-008 | Restore Tailwind v4 section to component-builder | 1h |
| FIX-009 | Restore Prisma examples to database-architect | 2h |
| FIX-010 | Restore 80-line route handler to api-builder | 1h |
| FIX-011 | Add version gap warnings to code-reviewer | 1h |
| FIX-012 | Restore validation architecture sections | 2h |
| FIX-013 | Restore IMPORTANT RULES sections | 1h |
| FIX-014 | Add Pattern 1/2 guidance to QUALITY.md | 1h |
| FIX-015 | Document Round N rejection cycle | 1h |

#### PHASE 3: CONSTITUTION SYSTEM (As Planned - 18h)

No changes from Section 11 - RE-023 through RE-035

---

### 12.9 Conclusion

The deep file-by-file analysis reveals that the Edison migration is approximately **45% complete** with significant content loss in critical areas:

**What Works:**
- ✅ Rules registry (100% preserved)
- ✅ Validators configuration (100% + 2 new)
- ✅ TDD guidelines (95%)
- ✅ DELEGATION guidelines (99%)
- ✅ CONTEXT7 guidelines (95%)

**What's Broken:**
- ❌ All 6 agent files missing YAML frontmatter and critical sections
- ❌ Delegation config lost 92% of entries
- ❌ Entry points (AGENTS.md, START.SESSION.md) have critical gaps
- ❌ SESSION_WORKFLOW has circular dependency
- ❌ 75% of code examples removed

**Estimated Total Remediation: 38 hours**

---

## 13. Constitution System - Refined Architecture (NEW)

**Added:** 2025-11-26
**Source:** User requirements for complete migration architecture

### 13.1 Core Architecture Principles (MUST IMPLEMENT)

#### 13.1.1 Three-Layer Composability

**RULE: Everything is composable at three levels:**

```
CORE (edison/core/) → PACKS (edison/packs/<pack>/) → PROJECT (.edison/)
```

| Layer | Location | Purpose |
|-------|----------|---------|
| **CORE** | `edison/core/` | Base definitions, framework defaults |
| **PACKS** | `edison/packs/<pack>/` | Technology-specific (React, Prisma, etc.) |
| **PROJECT** | `.edison/` | Project-specific overrides and additions |

**What is composable at ALL three levels:**
1. ✅ Guidelines
2. ✅ Rules
3. ✅ Agents
4. ✅ Validators
5. ✅ **Constitutions** (NEW - must be composable)

**Extension Rules:**
- Lower layers extend/override higher layers (PROJECT > PACKS > CORE)
- Pack-specific content stays in packs, NOT in core
- Project-specific content stays in project, NOT in packs or core

#### 13.1.2 Generated Files Principle

**RULE: NEVER link to source files, ONLY to generated files**

```markdown
# WRONG - linking to source
See: edison/core/guidelines/TDD.md

# CORRECT - linking to generated
See: .edison/_generated/guidelines/TDD.md
```

**Rationale:**
- Generated files contain FULL composed content (core + packs + project)
- Source files are incomplete without pack/project extensions
- Only generated files represent the "truth" for this project

**Generated Output Locations:**
- `.edison/_generated/` - Main generated folder
- `.claude/CLAUDE.md` - Claude-specific entry point (composed)
- `.claude/agents/`, `.claude/commands/`, `.claude/hooks/` - Claude specifics
- `.cursor/commands/` - Cursor-specific commands
- `.zen/conf/cli_clients/` - Zen MCP client configs
- `.zen/conf/systemprompts/` - Zen MCP system prompts
- `AGENTS.md` - Project root universal instructions (composed)

#### 13.1.3 No Hardcoded Values - ANYWHERE

**RULE: NO hardcoded lists, settings, or values in code OR prompts/guidelines**

| Wrong | Correct |
|-------|---------|
| `validators: [codex-global, claude-global]` in prompt | Dynamic from registry |
| `model: claude` hardcoded | `model: {{default_model}}` |
| `agents: [api-builder, test-engineer]` in guideline | Dynamic from AgentRegistry |
| List of 9 validators in VALIDATION.md | Reference to AVAILABLE_VALIDATORS.md |

**All values must come from:**
- Configuration files (`.edison/config/*.yml`)
- Registry queries (AgentRegistry, ValidatorRegistry)
- Dynamic generation at compose time

---

### 13.2 Constitution System - Complete Design

#### 13.2.1 Constitution vs ORCHESTRATOR_GUIDE

**DECISION: Replace ORCHESTRATOR_GUIDE.md with Constitution Folder**

| Current (DEPRECATED) | New (Constitution) |
|---------------------|-------------------|
| `ORCHESTRATOR_GUIDE.md` (single file) | `constitution/ORCHESTRATORS.md` |
| `manifest.json` | Merged into constitution |
| `START.SESSION.md` as separate file | Multiple START prompts (configurable) |
| Embedded agent/validator lists | `AVAILABLE_AGENTS.md` + `AVAILABLE_VALIDATORS.md` |

**New Constitution Structure:**
```
.edison/_generated/
├── AVAILABLE_AGENTS.md              # Dynamic agent roster
├── AVAILABLE_VALIDATORS.md          # Dynamic validator roster
├── constitutions/                   # Role-based constitutions
│   ├── ORCHESTRATORS.md            # Orchestrator constitution
│   ├── AGENTS.md                   # Agent constitution
│   └── VALIDATORS.md               # Validator constitution
├── agents/                         # Composed agent prompts
├── validators/                     # Composed validator prompts
└── guidelines/                     # Composed guidelines
```

#### 13.2.2 Constitution Composition Flow

**Constitutions are ALSO composable:**

```
constitution/ORCHESTRATORS.md =
  edison/core/constitutions/orchestrator-base.md
  + edison/packs/*/constitutions/orchestrator-additions.md (if any)
  + .edison/constitutions/orchestrator-overrides.md (if any)
```

**Same pattern for AGENTS.md and VALIDATORS.md constitutions.**

#### 13.2.3 Constitution Content Requirements

**Every constitution file MUST contain:**

1. **Role Identification** - "You are an AGENT/VALIDATOR/ORCHESTRATOR"
2. **Constitution Location** - Where to find this file for re-read
3. **RE-READ Instruction** - "Re-read this file on each new session or compaction"
4. **Mandatory Reads List** - Auto-generated from config
5. **Applicable Rules** - Filtered by `applies_to` field
6. **Role-Specific Instructions** - Workflow, output format, etc.

**Example Constitution Header:**
```markdown
<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Source: core + packs(nextjs, prisma) + project -->
<!-- Regenerate: edison compose --all -->
<!-- Role: AGENT -->
<!-- Constitution: .edison/_generated/constitutions/AGENTS.md -->
<!-- RE-READ this file on each new session or compaction -->

# Agent Constitution

You are an AGENT in the Edison framework. This constitution defines your mandatory behaviors.

## Constitution Location
This file is located at: `.edison/_generated/constitutions/AGENTS.md`

## CRITICAL: Re-read this entire file:
- At the start of every new session
- After any context compaction
- When instructed by the orchestrator
```

#### 13.2.4 Multiple START Prompts (Instead of Single START.SESSION.md)

**DECISION: Support multiple START prompt types**

| START Prompt | Purpose | When Used |
|--------------|---------|-----------|
| `START_NEW_SESSION.md` | Fresh session with new tasks | `edison session start` |
| `START_RESUME_SESSION.md` | Resume previous session | `edison session resume <id>` |
| `START_AUTO_TASKS.md` | Auto-claim unclaimed todo tasks | `edison session auto` |
| `START_WAIT_FOR_INPUT.md` | Wait for user to assign tasks | `edison session wait` |

**Constitution vs START prompts separation:**
- **Constitution** = Common logic, mandatory reads, rules (role-based)
- **START prompts** = Session initialization patterns (scenario-based)

---

### 13.3 CLAUDE.md vs AGENTS.md - Clear Separation

#### 13.3.1 AGENTS.md (Universal - Generated)

**Purpose:** Universal agent instructions for ALL agent types

**Contains:**
- Project context and overview
- Common instructions for ALL roles (orchestrator/agent/validator)
- Links to constitutions for role-specific details
- NOT role-specific orchestration/validation logic

**Generated from:** core + packs + project overlays

**Location:** Project root `AGENTS.md`

#### 13.3.2 .claude/CLAUDE.md (Claude-Specific - Generated)

**Purpose:** Claude-specific entry point and settings

**Contains:**
- Claude IDE integration settings
- Claude-specific tool configurations
- Link to project's AGENTS.md
- Link to appropriate constitution based on current role
- NOT role-specific instructions (those go in constitutions)

**Generated from:** core + packs + project overlays

**NOTE:** Claude can act as orchestrator, agent, or validator - CLAUDE.md should NOT assume a specific role.

#### 13.3.3 Role-Specific Instructions Go In Constitutions

| Role | Constitution | Entry Point Flow |
|------|--------------|------------------|
| Orchestrator | `constitutions/ORCHESTRATORS.md` | CLAUDE.md → AGENTS.md → ORCHESTRATORS.md |
| Agent | `constitutions/AGENTS.md` | Agent prompt → AGENTS.md → AGENTS.md (constitution) |
| Validator | `constitutions/VALIDATORS.md` | Validator prompt → VALIDATORS.md |

---

### 13.4 Auto-Injection and Mandatory Reads

#### 13.4.1 Constitution Auto-Injection in Agent/Validator Prompts

**RULE: Agent and validator prompts automatically include constitution reference**

**Agent prompt template:**
```markdown
## MANDATORY: Read Constitution First
Before starting any work, you MUST read the Agent Constitution at:
`.edison/_generated/constitutions/AGENTS.md`

This constitution contains:
- Your mandatory workflow
- Applicable rules
- Output format requirements
- All mandatory guideline reads
```

**Same for validator prompts referencing VALIDATORS.md constitution.**

#### 13.4.2 Compaction Hooks

**RULE: Auto-remind on compaction/new session**

**Implementation via Claude hooks:**
```yaml
# .claude/hooks/compaction.yml (generated)
on_compaction:
  - action: remind_constitution
    message: |
      Session compacted. Based on your role, re-read your constitution:
      - Orchestrator: .edison/_generated/constitutions/ORCHESTRATORS.md
      - Agent: .edison/_generated/constitutions/AGENTS.md
      - Validator: .edison/_generated/constitutions/VALIDATORS.md
```

#### 13.4.3 Configuration Schema for Mandatory Reads

```yaml
# edison/core/config/constitution.yaml
mandatoryReads:
  orchestrator:
    - path: constitutions/ORCHESTRATORS.md
      purpose: Main constitution
    - path: guidelines/orchestrators/SESSION_WORKFLOW.md
      purpose: Session lifecycle
    - path: guidelines/shared/DELEGATION.md
      purpose: Delegation rules
    - path: AVAILABLE_AGENTS.md
      purpose: Agent roster
    - path: AVAILABLE_VALIDATORS.md
      purpose: Validator roster

  agents:
    - path: constitutions/AGENTS.md
      purpose: Agent constitution
    - path: guidelines/agents/MANDATORY_WORKFLOW.md
      purpose: Implementation workflow
    - path: guidelines/agents/OUTPUT_FORMAT.md
      purpose: Report format
    - path: guidelines/shared/TDD.md
      purpose: TDD requirements

  validators:
    - path: constitutions/VALIDATORS.md
      purpose: Validator constitution
    - path: guidelines/validators/VALIDATOR_WORKFLOW.md
      purpose: Validation workflow
    - path: guidelines/validators/OUTPUT_FORMAT.md
      purpose: Report format
```

---

### 13.5 Rules System Enhancement

#### 13.5.1 Add `applies_to` Field

**RULE: Rules must have `applies_to` field for role-based filtering**

```yaml
# edison/core/rules/registry.yml
rules:
  RULE.TDD.RED_FIRST:
    name: "Test Must Fail First"
    content: "Write failing test before implementation code"
    applies_to: [agent, validator]
    severity: critical

  RULE.CONTEXT7.QUERY_BEFORE_CODE:
    name: "Query Context7 Before Coding"
    applies_to: [agent, orchestrator]
    severity: critical

  RULE.DELEGATION.ORCHESTRATOR_ONLY:
    name: "Orchestrator Delegates"
    applies_to: [orchestrator]
    severity: high
```

#### 13.5.2 Role-Based Rule Query API

**NEW API Required:**
```python
def get_rules_for_role(role: str) -> List[Rule]:
    """Extract rules that apply to a specific role"""
    rules = RuleRegistry.get_all()
    return [r for r in rules if role in r.applies_to]
```

**Used in constitution generation to embed applicable rules.**

---

### 13.6 Self-Identification in Generated Files

**RULE: Every generated file must self-identify**

```markdown
<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Source: core + packs(react, prisma) + project -->
<!-- Regenerate: edison compose --all -->
<!-- Role: AGENT (if applicable) -->
<!-- Constitution: .edison/_generated/constitutions/AGENTS.md (if applicable) -->
<!-- Last Generated: 2025-11-26T10:30:00Z -->
<!-- RE-READ this file on each new session or compaction -->
```

---

### 13.7 Generated Files Output Matrix

| File Type | Core | Packs | Project | Generated To |
|-----------|------|-------|---------|--------------|
| Guidelines | ✅ | ✅ | ✅ | `.edison/_generated/guidelines/` |
| Rules | ✅ | ✅ | ✅ | Registry + embedded in constitutions |
| Agents | ✅ | ✅ | ✅ | `.edison/_generated/agents/` |
| Validators | ✅ | ✅ | ✅ | `.edison/_generated/validators/` |
| Constitutions | ✅ | ✅ | ✅ | `.edison/_generated/constitutions/` |
| AGENTS.md | ✅ | ✅ | ✅ | Project root `AGENTS.md` |
| Rosters | - | - | - | `.edison/_generated/AVAILABLE_*.md` |
| CLAUDE.md | ✅ | ✅ | ✅ | `.claude/CLAUDE.md` |
| Zen configs | - | - | - | `.zen/conf/cli_clients/*.json` |
| Zen prompts | ✅ | ✅ | ✅ | `.zen/conf/systemprompts/` |

---

### 13.8 Implementation Tasks - Constitution System

#### P0 - CRITICAL (Constitution Foundation)

| Task ID | Description | Files Affected |
|---------|-------------|----------------|
| CONST-001 | Create core constitution templates | `edison/core/constitutions/*.md` |
| CONST-002 | Create constitution.yaml config schema | `edison/core/config/constitution.yaml` |
| CONST-003 | Implement constitution composer | `edison/core/composition/constitution.py` |
| CONST-004 | Add `applies_to` field to all rules | `edison/core/rules/*.yml` |
| CONST-005 | Implement `get_rules_for_role()` API | `edison/core/rules/engine.py` |
| CONST-006 | Generate AVAILABLE_AGENTS.md dynamically | Composer update |
| CONST-007 | Generate AVAILABLE_VALIDATORS.md dynamically | Composer update |
| CONST-008 | Remove ORCHESTRATOR_GUIDE.md generation | Deprecate old code |
| CONST-009 | Update agent prompts with constitution auto-injection | Agent templates |
| CONST-010 | Update validator prompts with constitution auto-injection | Validator templates |
| CONST-011 | Add compaction hooks for constitution re-read | `.claude/hooks/` |
| CONST-012 | Create multiple START prompt templates | `edison/core/start/*.md` |
| CONST-013 | Update CLAUDE.md composer for role-agnostic output | Composer update |
| CONST-014 | Update AGENTS.md composer for universal instructions | Composer update |
| CONST-015 | Add self-identification headers to all generated files | All composers |

#### P1 - HIGH (Zen & IDE Integration)

| Task ID | Description | Files Affected |
|---------|-------------|----------------|
| ZEN-001 | Generate `.zen/conf/cli_clients/claude.json` from composition | Zen composer |
| ZEN-002 | Generate `.zen/conf/cli_clients/codex.json` from composition | Zen composer |
| ZEN-003 | Generate `.zen/conf/cli_clients/gemini.json` from composition | Zen composer |
| ZEN-004 | Generate `.zen/conf/systemprompts/` from agents/validators | Zen composer |
| IDE-001 | Generate `.claude/agents/` from composed agents | Claude composer |
| IDE-002 | Generate `.claude/commands/` from config | Claude composer |
| IDE-003 | Generate `.claude/hooks/` including compaction hook | Claude composer |
| IDE-004 | Generate `.cursor/commands/` from config | Cursor composer |

---

## 14. Additional Critical Requirements (NEW)

### 14.1 No Hardcoded Lists in Prompts/Guidelines

**CRITICAL: Current violations to fix:**

1. ❌ `VALIDATION.md` - Hardcoded list of 9 validators
2. ❌ `DELEGATION.md` - Hardcoded list of agents
3. ❌ `CLAUDE.md` - Hardcoded list of preloads
4. ❌ Agent prompts - Hardcoded validator architecture (9 validators)
5. ❌ `ORCHESTRATOR_GUIDE.md` - Hardcoded agent roster

**FIX: Replace with dynamic references:**
```markdown
<!-- OLD (wrong) -->
The 9 validators are: codex-global, claude-global, security, ...

<!-- NEW (correct) -->
See AVAILABLE_VALIDATORS.md for the current validator roster.
```

### 14.2 Composition Output Verification

**Every compose run MUST generate:**

1. `.edison/_generated/` folder with:
   - `agents/*.md` - All composed agent prompts
   - `validators/*.md` - All composed validator prompts
   - `guidelines/**/*.md` - All composed guidelines
   - `constitutions/*.md` - All three constitutions
   - `AVAILABLE_AGENTS.md` - Dynamic roster
   - `AVAILABLE_VALIDATORS.md` - Dynamic roster

2. Project root:
   - `AGENTS.md` - Universal instructions (composed)

3. `.claude/` folder:
   - `CLAUDE.md` - Claude entry point (composed)
   - `settings.json` - Claude settings
   - `agents/` - Claude agent definitions
   - `commands/` - Claude commands
   - `hooks/` - Claude hooks including compaction

4. `.cursor/` folder:
   - `commands/` - Cursor commands

5. `.zen/` folder:
   - `conf/cli_clients/claude.json`
   - `conf/cli_clients/codex.json`
   - `conf/cli_clients/gemini.json`
   - `conf/systemprompts/` - All agent/validator zen prompts

### 14.3 Config File Consolidation

**All config must live in YAML files, not in code:**

| Config Type | Location |
|-------------|----------|
| Delegation rules | `.edison/config/delegation.yml` |
| Validator config | `.edison/config/validators.yml` |
| Agent registry | `.edison/config/agents.yml` |
| Pack activation | `.edison/config/packs.yml` |
| Project settings | `.edison/config/project.yml` |
| Constitution config | `.edison/config/constitution.yml` |
| Commands | `.edison/config/commands.yml` |
| Hooks | `.edison/config/hooks.yml` |
| Settings | `.edison/config/settings.yml` |

**NO config values in Python/JS code.**

---

## 15. Validation Checklist for Deep Analysis

The subagent validators must check:

### 15.1 For Each Pre-Edison File

- [ ] Is the content migrated to the correct layer (core/packs/project)?
- [ ] Are hardcoded lists converted to dynamic references?
- [ ] Are all instructions preserved in the new structure?
- [ ] Are cross-references updated to use generated file paths?
- [ ] Does the composed output include this content?

### 15.2 For Constitution System

- [ ] Are all three constitutions generated?
- [ ] Do constitutions include self-identification headers?
- [ ] Do constitutions include RE-READ instructions?
- [ ] Do agent/validator prompts auto-inject constitution references?
- [ ] Are rules filtered by `applies_to` in constitutions?

### 15.3 For Generated Outputs

- [ ] Is AVAILABLE_AGENTS.md generated dynamically?
- [ ] Is AVAILABLE_VALIDATORS.md generated dynamically?
- [ ] Is ORCHESTRATOR_GUIDE.md removed/deprecated?
- [ ] Are all Zen configs generated correctly?
- [ ] Are all Claude configs generated correctly?

---

---

## 16. Wave 1 Validation Results: Agent Files (2025-11-26)

**Validators Used:** 6 Claude Opus subagents (one per agent file)
**Status:** COMPLETE

### 16.1 Critical Findings Summary - ALL 6 AGENTS

| Agent | Pre-Edison Lines | Post-Edison Lines | Reduction | Critical Gaps |
|-------|-----------------|-------------------|-----------|---------------|
| api-builder | 375 | 361 | 4% | 8 |
| component-builder | 553 | 299 | **46%** | 15 |
| database-architect | 464 | 205 | **56%** | 12 |
| code-reviewer | 418 | 397 | 5% | 9 |
| test-engineer | 578 | 486 | 16% | 8 |
| feature-implementer | 429 | 319 | **26%** | 10 |

### 16.2 Universal Gaps Across ALL 6 Agents

**CRITICAL - Missing in ALL agents:**

1. ❌ **YAML Frontmatter** - ALL 6 agents missing YAML frontmatter
   - Missing: `name`, `description`, `model`, `zenRole`
   - Impact: Cannot map to Zen roles, no metadata for registry

2. ❌ **Context7 MCP Tool Call Examples** - ALL 6 agents missing
   - Pre-Edison had TypeScript code showing `mcp__context7__get-library-docs()`
   - Post-Edison has generic references only
   - Impact: Agents don't know HOW to use Context7

3. ❌ **Training Cutoff Warning** - ALL 6 agents missing
   - Pre-Edison: "Your knowledge is outdated for Next.js 16, React 19, Tailwind 4!"
   - Impact: Agents may use stale knowledge

4. ❌ **Ephemeral Summaries Policy Reference** - ALL 6 agents missing
   - Pre-Edison explicitly referenced this policy
   - Impact: Agents may create forbidden summary files

5. ❌ **Version/Line Count Metadata** - ALL 6 agents missing
   - Pre-Edison had: "Version: 2.0, Lines: ~400 (was 1,067)"
   - Impact: No change tracking

6. ❌ **Self-Identification Header** - ALL 6 agents missing
   - Should include constitution reference and RE-READ instruction

### 16.3 Agent-Specific Critical Gaps

#### api-builder.md (4% reduction but significant gaps)

| Gap | Severity | Description |
|-----|----------|-------------|
| POST handler example | HIGH | 19-line POST handler with Zod validation missing |
| Prisma error handling | HIGH | P2002 conflict error handling missing |
| CONFIGURATION AUTHORITY section | HIGH | No explanation of config files |
| Honest completion warning | CRITICAL | "DO NOT rush and mark incomplete work as done" missing |

#### component-builder.md (46% reduction - SEVERE)

| Gap | Severity | Description |
|-----|----------|-------------|
| Server Component example | CRITICAL | 18-line database query example missing |
| Client Component example | CRITICAL | 35-line state/motion example missing |
| Motion 12 patterns | HIGH | Animation patterns completely missing |
| Forms with Zod validation | HIGH | 59-line form example missing |
| Tailwind v4 rules | CRITICAL | 5 detailed rules + cache clearing missing |
| Design System rules | HIGH | Color/typography/spacing rules missing |
| IMPORTANT RULES (8 items) | HIGH | Numbered checklist missing |

#### database-architect.md (56% reduction - SEVERE)

| Gap | Severity | Description |
|-----|----------|-------------|
| Complete schema.prisma template | CRITICAL | 50-line working template missing |
| Migration workflow commands | HIGH | 5-step npx prisma workflow missing |
| Rollback strategy | HIGH | 3-step rollback procedure missing |
| Migration safety classifications | CRITICAL | Safe vs dangerous operations missing |
| Query optimization patterns | HIGH | GOOD vs BAD examples missing |
| Index strategy examples | HIGH | Composite index patterns missing |
| IMPORTANT RULES (7 items) | CRITICAL | Numbered checklist missing |

#### code-reviewer.md (5% reduction but key gaps)

| Gap | Severity | Description |
|-----|----------|-------------|
| 9-validator architecture breakdown | HIGH | "2 Global + 2 Critical + 5 Specialized" missing |
| "Why no delegation" reasoning | HIGH | 4 bullet points explaining why missing |
| Version gap warnings | CRITICAL | Next 16, React 19, Tailwind 4, Prisma 6 warnings missing |
| Context7 tool call example | CRITICAL | TypeScript MCP call example missing |

#### test-engineer.md (16% reduction)

| Gap | Severity | Description |
|-----|----------|-------------|
| Wilson-specific entity examples | HIGH | `prisma.lead` replaced with generic `db.record` |
| `withTestServer` helper | HIGH | API testing helper missing |
| `createAuthenticatedRequest` helper | HIGH | Auth testing helper missing |
| "NOT Fastify!" warning | HIGH | Architecture clarification missing |
| Odoo/Piloterr integration examples | MEDIUM | External API examples missing |

#### feature-implementer.md (26% reduction + ZEN PROMPT MISMATCH)

| Gap | Severity | Description |
|-----|----------|-------------|
| **Zen Prompt Wrong Role** | 🔴 BLOCKER | Zen prompt contains Gemini validator, NOT feature-implementer |
| Fastify vs Next.js contradiction | CRITICAL | Post-Edison mentions Fastify but pre-Edison says "NOT Fastify!" |
| Premium Design Standards | HIGH | 8pt grid, design tokens, micro-interactions missing |
| Quality Standards checklist | HIGH | 8-item checklist missing |
| Tailwind v4 examples | CRITICAL | font-sans requirement, cache clearing missing |

### 16.4 Zen Prompt Issues (CRITICAL)

**MAJOR FINDING: Most Zen prompts contain WRONG content**

| Agent | Expected Content | Actual Content | Status |
|-------|-----------------|----------------|--------|
| wilson-api-builder.txt | API Builder agent | ??? | Needs verification |
| wilson-component-builder.txt | Component Builder agent | Gemini Global Validator | 🔴 **WRONG** |
| wilson-database-architect.txt | Database Architect agent | Gemini Global Validator | 🔴 **WRONG** |
| wilson-code-reviewer.txt | Code Reviewer agent | Gemini Global Validator | 🔴 **WRONG** |
| wilson-test-engineer.txt | Test Engineer agent | Gemini Global Validator | 🔴 **WRONG** |
| wilson-feature-implementer.txt | Feature Implementer agent | Gemini Global Validator | 🔴 **WRONG** |

**Root Cause**: The Zen prompt composition is generating VALIDATOR prompts instead of AGENT prompts.

### 16.5 New Implementation Tasks from Wave 1

| Task ID | Description | Priority | Effort |
|---------|-------------|----------|--------|
| W1-001 | Add YAML frontmatter to all 6 agents | CRITICAL | 1h |
| W1-002 | Restore Context7 MCP tool call examples to all agents | CRITICAL | 2h |
| W1-003 | Fix Zen prompt composition - wrong role being generated | 🔴 BLOCKER | 4h |
| W1-004 | Restore training cutoff warning to all agents | CRITICAL | 0.5h |
| W1-005 | Restore EPHEMERAL_SUMMARIES_POLICY references | HIGH | 0.5h |
| W1-006 | Restore component-builder Server/Client examples | CRITICAL | 2h |
| W1-007 | Restore database-architect schema.prisma template | CRITICAL | 1h |
| W1-008 | Restore database-architect migration safety classifications | CRITICAL | 1h |
| W1-009 | Restore Tailwind v4 detailed rules (all relevant agents) | CRITICAL | 1h |
| W1-010 | Restore IMPORTANT RULES sections (numbered lists) | HIGH | 1h |
| W1-011 | Resolve Fastify vs Next.js contradiction | CRITICAL | 0.5h |
| W1-012 | Add self-identification headers with constitution reference | HIGH | 1h |
| W1-013 | Restore "Why no delegation" reasoning to code-reviewer | MEDIUM | 0.5h |
| W1-014 | Restore Wilson-specific entity examples (prisma.lead) | MEDIUM | 1h |

---

## 17. Wave 2 Validation Results: Delegation Files (2025-11-26)

**Validators Used:** 2 Claude Opus subagents
**Status:** COMPLETE

### 17.1 Delegation Config Migration - CRITICAL GAPS

| Metric | Pre-Edison | Post-Edison | Loss |
|--------|-----------|-------------|------|
| Total Lines | 772 | 20 | **97%** |
| File Pattern Rules | 16 | 0 in config | Lost (only in manifest) |
| Task Type Rules | 11 | 4 | **64%** |
| Sub-Agent Defaults | 6 | 2 | **67%** |
| Zen Role Mappings | 18 | 6 | **67%** |
| Model Definitions | 3 full | 0 | **100%** |

### 17.2 Missing Task Type Rules (7 of 11)

| Task Type | Preferred Model | Sub-Agent | Status |
|-----------|----------------|-----------|--------|
| database-schema | codex | database-architect | ❌ MISSING |
| test-suite | codex | test-engineer | ❌ MISSING |
| refactoring | codex | api-builder | ❌ MISSING |
| security-audit | codex | code-reviewer | ❌ MISSING |
| performance-optimization | codex | api-builder | ❌ MISSING |
| documentation | gemini | feature-implementer | ❌ MISSING |
| architecture-design | gemini | feature-implementer | ❌ MISSING |

### 17.3 Missing Configuration Sections (100% loss)

1. ❌ **`models{}`** - Model capabilities, strengths, weaknesses, cost tiers
2. ❌ **`orchestratorGuidance{}`** - Delegation workflow, tie-breakers, exceptions
3. ❌ **`workflowContext{}`** - Session workflow integration
4. ❌ **`zenMcpIntegration.description`** - Usage documentation
5. ❌ **`references{}`** - Cross-reference documentation

### 17.4 Missing Output Format Documentation

- Pre-Edison OUTPUT_FORMAT.md: 91 lines with complete schema
- Post-Edison: NO dedicated output format file
- Missing fields: `taskId`, `compliance`, `notes`, `suggestedFollowups`

### 17.5 Delegation Wave 2 Tasks

| Task ID | Description | Priority |
|---------|-------------|----------|
| W2-001 | Restore 7 missing task type rules | CRITICAL |
| W2-002 | Restore model definitions (codex, claude, gemini) | CRITICAL |
| W2-003 | Restore orchestratorGuidance section | CRITICAL |
| W2-004 | Restore 4 missing sub-agent defaults | HIGH |
| W2-005 | Create OUTPUT_FORMAT.md with schema | HIGH |
| W2-006 | Restore 12 missing Zen role mappings | HIGH |
| W2-007 | Restore delegation examples directory | MEDIUM |

---

## 18. Wave 3 Validation Results: Guidelines Files (2025-11-26)

**Validators Used:** 6 Claude Opus subagents
**Status:** COMPLETE

### 18.1 Guidelines Content Reduction Summary

| Guideline | Pre-Edison Lines | Post-Edison Lines | Reduction |
|-----------|-----------------|-------------------|-----------|
| TDD.md + TDD_GUIDE.md | 1,866 | 391 | **79%** |
| VALIDATION.md + VALIDATION_GUIDE.md | 1,495 | 350 | **77%** |
| QUALITY.md + QUALITY_STANDARDS.md | 643 | 78 | **88%** |
| SESSION_WORKFLOW.md (both) | 651 | 517 | 21% |
| CONTEXT7.md (both) | 437 | 310 | 29% |
| EPHEMERAL_SUMMARIES_POLICY.md | 20 | 24 | ✅ +20% |

### 18.2 TDD Guidelines - CRITICAL GAPS

**SEVERITY: 🔴 CRITICAL**

| Missing Section | Pre-Edison Lines | Impact |
|-----------------|------------------|--------|
| TDD When Delegating | 136 lines | Orchestrators can't enforce TDD |
| Verification Checklist | 125 lines | No standardized compliance check |
| Report Template | 46 lines | No TDD documentation format |
| Enforcement Rules | 72 lines | No consequences for violations |
| Troubleshooting | 190 lines | No debugging guidance |
| Red Flags Details | 102 lines | Can't recognize violations |
| Real Examples | 83 lines | No reference implementations |

**Key Missing Content:**
- ❌ Orchestrator TDD delegation templates (component-builder, api-builder, feature-implementer)
- ❌ TDD verification report template
- ❌ Step-by-step verification commands
- ❌ 10 code evolution examples
- ❌ 7 red flag anti-pattern examples

### 18.3 VALIDATION Guidelines - HARDCODED VALUES VIOLATION

**SEVERITY: 🔴 CRITICAL - VIOLATES CONSTITUTION PRINCIPLES**

**Hardcoded Values Found (MUST FIX):**
1. Line 8: `"9-validator architecture"` - Should be dynamic
2. Line 14: `"9 independent validators"` - Should reference AVAILABLE_VALIDATORS.md
3. Lines 18-20: Hardcoded validator names - Should be template variables

**Missing Sections:**
- ❌ Batched Parallel Execution Model (CRITICAL for performance)
- ❌ Round N Rejection Cycle (CRITICAL for workflow)
- ❌ 9-Validator Table with triggers/models/blocking status
- ❌ Execution Flow Diagram
- ❌ Validator-Specific Checklists
- ❌ Troubleshooting Section

### 18.4 SESSION_WORKFLOW Guidelines - BROKEN REFERENCES

**SEVERITY: 🟠 HIGH**

**Broken Reference Found:**
- Lines 3, 5 reference: `../../guides/extended/SESSION_WORKFLOW.md`
- **File does NOT exist** at that path

**Missing Content from Pre-Edison Extended Guide:**
- ❌ Task & QA Architecture (file naming patterns)
- ❌ Session Start Protocol (Validation-First)
- ❌ Planning & Delegation matrix usage
- ❌ Automated Checks command sequence
- ❌ Common Failure Modes table
- ❌ FAQ section

### 18.5 CONTEXT7 Guidelines - Missing Package IDs

**SEVERITY: 🟠 HIGH**

**Missing Wilson-Specific Package IDs:**
- ❌ `/vercel/next.js` - Next.js 16
- ❌ `/facebook/react` - React 19
- ❌ `/tailwindlabs/tailwindcss` - Tailwind CSS 4
- ❌ `/colinhacks/zod` - Zod 4
- ❌ `/prisma/prisma` - Prisma 6
- ❌ Motion 12 library ID
- ❌ Better-Auth library ID

**Missing MCP Tools (2 of 4):**
- ❌ `mcp__context7__search-docs`
- ❌ `mcp__context7__get-latest-version`

### 18.6 QUALITY Guidelines - SEVERE CONTENT LOSS

**SEVERITY: 🔴 CRITICAL**

**Content Reduction: 88% (643 → 78 lines)**

**Missing Sections:**
- ❌ Premium Design Standards (design tokens, 8pt grid)
- ❌ Micro-interactions (transitions, hover states)
- ❌ Code Smell Checklist (40+ items)
- ❌ WCAG AA Details (contrast ratios)
- ❌ Theme Support (dark mode requirements)
- ❌ Loading State Examples
- ❌ Empty State Examples
- ❌ Responsive Design Breakpoints
- ❌ Progressive Quality Gates (Task/Module/Phase)
- ❌ Performance Standards (bundle size targets)
- ❌ Security Standards

**Missing Code Examples: 10+**

### 18.7 EPHEMERAL_SUMMARIES_POLICY - COMPLETE ✅

**Status:** Successfully migrated (24 lines vs 20 pre-Edison)

**Note:** Has broken reference to extended guide that doesn't exist, but core content is complete.

### 18.8 Wave 3 Implementation Tasks

| Task ID | Description | Priority |
|---------|-------------|----------|
| W3-001 | Remove ALL hardcoded validator counts/names from guidelines | 🔴 BLOCKER |
| W3-002 | Restore TDD delegation templates | CRITICAL |
| W3-003 | Restore TDD verification checklist + report template | CRITICAL |
| W3-004 | Restore VALIDATION batched parallel execution | CRITICAL |
| W3-005 | Restore VALIDATION Round N rejection cycle | CRITICAL |
| W3-006 | Fix broken SESSION_WORKFLOW extended guide reference | HIGH |
| W3-007 | Restore SESSION_WORKFLOW extended content OR remove reference | HIGH |
| W3-008 | Add Wilson-specific Context7 package IDs overlay | HIGH |
| W3-009 | Restore QUALITY Premium Design Standards | HIGH |
| W3-010 | Restore QUALITY Code Smell Checklist | HIGH |
| W3-011 | Restore QUALITY code examples (10+) | HIGH |
| W3-012 | Add missing Context7 MCP tools documentation | MEDIUM |
| W3-013 | Restore TDD troubleshooting section | MEDIUM |
| W3-014 | Restore VALIDATION troubleshooting section | MEDIUM |

---

## 19. Hardcoded Values Audit (CRITICAL VIOLATION)

**This section tracks ALL hardcoded values that MUST be replaced with dynamic references per Section 13.1.3**

### 19.1 Hardcoded Validator References

| File | Line | Hardcoded Value | Should Be |
|------|------|-----------------|-----------|
| VALIDATION.md | 8 | "9-validator architecture" | `{{validation.totalValidators}}-validator architecture` |
| VALIDATION.md | 14 | "9 independent validators" | `{{validation.roster | length}} independent validators` |
| VALIDATION.md | 18-20 | Validator name list | `See AVAILABLE_VALIDATORS.md` |
| VALIDATION_AWARENESS.md | 8 | "9-validator architecture" | Dynamic reference |
| VALIDATION_AWARENESS.md | 14 | "9 independent validators" | Dynamic reference |
| All 6 agent files | Various | "9 validators" mentions | Dynamic reference |

### 19.2 Hardcoded Agent References

| File | Line | Hardcoded Value | Should Be |
|------|------|-----------------|-----------|
| DELEGATION.md | Various | Agent name lists | `See AVAILABLE_AGENTS.md` |
| ORCHESTRATOR_GUIDE.md | Multiple | Agent roster | Generated from AgentRegistry |

### 19.3 Hardcoded Configuration Values

| File | Value | Should Be |
|------|-------|-----------|
| TDD guidelines | "80% coverage" | `{{quality.coverageTarget}}` |
| QUALITY.md | Coverage percentages | From config |
| Various | "5000 tokens" | `{{context7.defaultTokens}}` |

---

## 20. Wave 4 Validation Results: Rules & Validators Folders (2025-11-26)

**Validators Used:** 8 Claude Opus subagents
**Status:** COMPLETE

### 20.1 Rules Registry Analysis

**File:** `rules/registry.json`
**Pre-Edison Lines:** 266
**Post-Edison Equivalent:** `/edison/src/edison/data/rules/registry.yml`
**Post-Edison Lines:** 224
**Content Loss:** 15.8% (expected due to JSON→YAML compression)
**Rule Count Match:** ✅ YES (37 rules in both)

#### 20.1.1 Rule Categories Migration

| Pre-Edison Categories (14) | Edison Categories (7) | Notes |
|---------------------------|----------------------|-------|
| CONTEXT, CONTEXT7, DELEGATION, EVIDENCE, FOLLOWUPS, GUARDS, IMPLEMENTATION, LINK, PARALLEL, PARENT, QA, SESSION, STATE, VALIDATION | context, delegation, general, implementation, session, transition, validation | Intentional consolidation |

#### 20.1.2 Critical Hardcoded Values - MUST FIX

**🔴 CRITICAL: Project Path References (32 of 37 rules)**
```
HARDCODED: ".agents/guidelines/" prefix in all sourcePath fields
EXAMPLE: "sourcePath": ".agents/guidelines/DELEGATION.md"
IMPACT: Cannot reuse in other projects without modification
FIX: Implement configuration-driven base paths
```

**🔴 CRITICAL: HTML Comment Markers (37 rules)**
```
HARDCODED: "<!-- RULE: RULE.[ID].[SUFFIX] START/END -->"
IMPACT: Tightly coupled to specific guideline file content
FIX: Switch to structured anchor format (<!-- ANCHOR: name -->)
```

#### 20.1.3 Missing Anchor Fragments
- Pre-Edison lacks anchor IDs in sourcePath
- Edison partially adds them but inconsistently
- Some rules have `#anchor`, others don't

#### 20.1.4 No Blocking Rules Defined
- All 37 rules have `blocking: false`
- No rules are actually enforced at runtime
- Need audit to determine which rules SHOULD be blocking

#### 20.1.5 Constitution Alignment (3-Layer)

| Layer | Status | Location |
|-------|--------|----------|
| CORE | ✅ 37 rules | `edison/src/edison/data/rules/registry.yml` |
| PACKS | ❌ MISSING | No `.edison/packs/*/rules/registry.yml` defined |
| PROJECT | ❌ MISSING | No project-level rule overrides defined |

**Migration Readiness Score: 60% COMPLETE**

---

### 20.2 Validators Config Analysis

**File:** `validators/config.json`
**Pre-Edison Lines:** 436
**Post-Edison Equivalent:** `/edison/src/edison/data/config/validators.yaml`
**Post-Edison Lines:** 180
**Content Loss:** 58.7% (intentional architectural migration)

#### 20.2.1 Validator Roster Comparison

| Tier | Pre-Edison | Post-Edison | Status |
|------|-----------|-------------|--------|
| Global | 2 (codex, claude) | 3 (codex, claude, gemini) | ✅ +1 |
| Critical | 2 (security, performance) | 2 (same) | ✅ Same |
| Specialized | 6 (react, nextjs, api, database, testing, styling) | 5 (prisma renamed) | ✅ Same |

#### 20.2.2 CRITICAL GAPS

**❌ POST-TRAINING PACKAGES COMPLETELY MISSING**
```
Pre-Edison had 9 packages with versions and Context7 topics:
- next: 16.0.0
- react: 19.2.0
- tailwindcss: 4.0.0
- zod: 4.1.12
- framer-motion: 12.23.24
- typescript: 5.7.0
- prisma: 6.0.0
- better-auth: 0.0.0
- Training cutoff: 2025-01

Edison validators.yaml has NO equivalent section
```

**❌ WORKFLOW CONTEXT HARDCODED IN PYTHON**
```
Pre-Edison defined in config.json:
- QA directory states: waiting, todo, wip, done, validated
- Validation lifecycle rules
- Approval/rejection/revalidation flows

Edison: Embedded in Python code (validator.py), NOT configurable
```

**❌ HARDCODED WILSON-SPECIFIC ZENROLES**
```
Pre-Edison: "wilson-validator-codex-global", etc.
Edison: "validator-codex-global" (generic)
Need: Project overlay mapping mechanism documented
```

**❌ HARDCODED FILE PATH PATTERNS**
```
Wilson-specific paths in triggers:
- apps/dashboard/src/**/*.tsx
- packages/api-core/**/*.ts
- packages/db/**/*.ts

Need: Externalize to project overlays
```

---

### 20.3 Validators README Analysis

**File:** `validators/README.md`
**Pre-Edison Lines:** 502
**Post-Edison Equivalent:** Distributed across multiple files
**Post-Edison Total Lines:** 1,032+ (combined)
**Content Loss:** NEGATIVE (-106%, more comprehensive)

#### 20.3.1 Content Distribution

| Pre-Edison Section | Post-Edison Location | Lines |
|-------------------|---------------------|-------|
| Overview | VALIDATOR_WORKFLOW.md | 10 |
| Architecture | VALIDATOR_GUIDELINES.md | 11 |
| Execution Flow | validator.py | ~250 |
| Configuration | validators.yaml | 181 |
| Validator Specs | codex-global.md (expanded) | 799+ |

#### 20.3.2 Missing Documentation

- ❌ **ORCHESTRATOR_VALIDATOR_RUNBOOK.md** - 8-step flow with wave management
- ❌ **ROSTER.md** - Detailed validator descriptions
- ❌ **Pack Validator Guide** - How packs contribute validators
- ❌ **ConfigManager Overlay Resolution** - Configuration precedence docs
- ❌ **QA State Machine Integration** - How validators update QA briefs
- ❌ **Troubleshooting Guide** - Common validator issues

---

### 20.4 Validators OUTPUT_FORMAT Analysis

**File:** `validators/OUTPUT_FORMAT.md`
**Pre-Edison Lines:** 155
**Post-Edison Lines:** 34
**Content Loss:** 78%

#### 20.4.1 Field Simplification

| Pre-Edison Fields | Post-Edison Fields | Status |
|-------------------|-------------------|--------|
| taskId, round, validatorId, model, verdict | taskId, round, validator, model, verdict | ✅ Kept |
| evidenceReviewed[] (full paths) | evidence[] (filenames only) | ⚠️ Simplified |
| suggestedFollowups[] (10 fields) | followUps[] (3 fields) | 🔴 70% LOST |
| tracking (processId, hostname, etc.) | REMOVED | 🔴 LOST |
| zenRole, context7Used, context7Packages | REMOVED | 🔴 LOST |
| strengths[] | REMOVED | 🔴 LOST |

#### 20.4.2 Follow-up Task Metadata Loss

**Pre-Edison suggestedFollowups:**
- title, description, type, severity, blocking
- claimNow, parentId, files[], suggestedSlug, suggestedWave

**Post-Edison followUps:**
- title, description, severity, blocking

**Lost Fields (60% reduction):** claimNow, parentId, files[], suggestedSlug, suggestedWave, type

---

### 20.5 VALIDATOR_WORKFLOW Analysis

**File:** `validators/VALIDATOR_WORKFLOW.md`
**Pre-Edison Lines:** 51
**Post-Edison Lines:** 10
**Content Loss:** 80.4%

#### 20.5.1 Workflow Steps Comparison

**Pre-Edison (8 orchestrator-level steps):**
1. Scope: Open QA brief, ensure bundle manifest
2. Launch: Promote QA todo → wip
3. Waves: Run validators (global → critical → specialized)
4. Model binding: Call exact model per config
5. Deliverables: Produce Markdown + JSON reports
6. Findings: Summarize verdicts, suggest follow-ups
7. Decision: REJECT if blocking fails, APPROVE if all pass
8. Archive: Promote done → validated

**Post-Edison (8 validator-only steps):**
1. Intake - Open QA brief and bundle manifest
2. Load context - Read implementation report, evidence, git diff
3. Prepare checks - Map changed files to validators
4. Execute - Run commands, capture to evidence
5. Findings - Document issues with severity
6. Verdict - approve/reject/blocked
7. Report - Write JSON and update QA brief
8. Handoff - If rejected, return to waiting

#### 20.5.2 Lost Orchestrator Logic

- ❌ Wave-based execution model (global → critical → specialized)
- ❌ QA state transitions (todo → wip → done → validated)
- ❌ Tracking integration (`scripts/track start|complete`)
- ❌ Bundle-level approval logic
- ❌ Concurrency cap enforcement

---

### 20.6 Critical Validators Analysis

**Files:** `validators/critical/performance.md`, `validators/critical/security.md`

| File | Pre-Edison Lines | Post-Edison Lines | Change | Checks |
|------|-----------------|-------------------|--------|--------|
| performance.md | 792 | 775 | -2.1% | 121 |
| security.md | 826 | 853 | +3.3% | 161 |

#### 20.6.1 Intentional Genericization

**Pre-Edison:** Wilson-specific (Next.js 16, React 19, Prisma, Better-Auth, Zod)
**Post-Edison:** Framework-agnostic with pack overlays

#### 20.6.2 ZEN PROMPT GENERATION - CRITICAL ISSUE

```
PROBLEM: Generated Zen files are INCOMPLETE

Files found:
- validator-performance.txt (100 lines) = WORKFLOW TEMPLATE ONLY
- validator-security.txt (59 lines) = WORKFLOW TEMPLATE ONLY

MISSING:
- Validator markdown content NOT EMBEDDED in Zen prompts
- Framework-specific security context NOT INJECTED
- Pack-specific customizations NOT APPLIED
```

---

### 20.7 Global Validators Analysis

**Files:** `validators/global/claude-global.md`, `validators/global/codex-global.md`

| File | Pre-Edison Lines | Post-Edison Lines | Growth |
|------|-----------------|-------------------|--------|
| claude-global.md | 824 | 2,537 | +208% |
| codex-global.md | 790 | 1,990 | +152% |

#### 20.7.1 Zen Prompt Dual Files Issue

```
Two forms exist for each validator:
- validator-claude-global.txt (2,212 bytes) - Orchestrator wrapper
- wilson-validator-claude-global.txt (32,930 bytes) - Full validator

UNCLEAR: Which is active in Zen pipeline?
```

#### 20.7.2 Missing Consensus Logic

- Pre-Edison: Detailed "Consensus with Codex Global Validator" section
- Post-Edison: Consensus mentioned but not detailed
- Need: Verify Edison orchestrator handles dual-validator consensus

---

### 20.8 Specialized Validators Analysis

| File | Pre-Edison | Post-Edison | Growth | Pack Mapping |
|------|-----------|-------------|--------|--------------|
| api.md | 693 | 1,005 | +45% | nextjs-api |
| database.md | 674 | 992 | +47% | prisma |
| nextjs.md | 699 | 1,059 | +51% | nextjs |
| react.md | 587 | 893 | +52% | react |
| testing.md | 759 | 1,066 | +40% | vitest |
| **TOTALS** | **3,412** | **5,015** | **+47%** | 5 packs |

**Status: ✅ COMPLETE MIGRATION WITH ENHANCEMENTS**

All specialized validators successfully migrated with:
- 100% core content preserved
- Tech-stack context added (Packs system)
- Project-specific extensions (Wilson) added
- Pack overlay architecture implemented

---

### 20.9 Wave 4 Implementation Tasks

| Task ID | Description | Priority |
|---------|-------------|----------|
| W4-001 | Create post-training-packages.yaml config | 🔴 BLOCKER |
| W4-002 | Externalize workflow context to YAML (not Python) | 🔴 BLOCKER |
| W4-003 | Fix rule sourcePath hardcoding (.agents/ → configurable) | 🔴 BLOCKER |
| W4-004 | Convert HTML rule markers to structured anchors | CRITICAL |
| W4-005 | Add blocking flags to appropriate rules | CRITICAL |
| W4-006 | Create pack-specific rule registries | HIGH |
| W4-007 | Create ORCHESTRATOR_VALIDATOR_RUNBOOK.md | HIGH |
| W4-008 | Restore follow-up task metadata (claimNow, parentId, etc.) | HIGH |
| W4-009 | Document zenRole project overlay mapping | HIGH |
| W4-010 | Verify Zen prompt generation embeds validator content | HIGH |
| W4-011 | Create ConfigManager overlay documentation | MEDIUM |
| W4-012 | Add tracking integration documentation | MEDIUM |
| W4-013 | Create validator troubleshooting guide | MEDIUM |

---

## 21. Wave 5 Validation Results: Main Entry Points (2025-11-26)

**Validators Used:** 3 Claude Opus subagents
**Status:** COMPLETE

### 21.1 AGENTS.md Constitution Analysis

**File:** `/wilson-pre-edison/.agents/AGENTS.md`
**Pre-Edison Lines:** 110
**Post-Edison Equivalent:** DISTRIBUTED across multiple files
**Post-Edison Total Lines:** 2,500+ (combined)
**Content Loss:** 23% (but significantly expanded in Edison)

#### 21.1.1 Agent Roster Defined

| Agent | Model | ZenRole | Responsibility |
|-------|-------|---------|----------------|
| api-builder | codex | wilson-api-builder | Backend APIs, routes, validation |
| component-builder | claude | wilson-component-builder | React UI, layouts, accessibility |
| database-architect | codex | wilson-database-architect | Schema, migrations, relationships |
| test-engineer | codex | wilson-test-engineer | TDD, unit/integration/E2E tests |
| feature-implementer | claude | wilson-feature-implementer | Full-stack features |
| code-reviewer | claude | wilson-code-reviewer | Validation only (NO implementation) |

#### 21.1.2 Content Distribution (Pre → Post)

| Pre-Edison Section | Post-Edison Location | Status |
|-------------------|---------------------|--------|
| Agent Roster (implicit) | `/edison/data/agents/*.md` | ✅ Migrated |
| Delegation Guidance | `/edison/data/config/delegation.yaml` | ✅ 77% compressed |
| Mandatory Preload | ConfigManager composition | ✅ Restructured |
| Model Definitions | `/edison/data/config/models.yaml` | ✅ Migrated |
| Agent Briefs (2,811 lines) | Edison core briefs (1,626 lines) | ✅ 42% compressed |

#### 21.1.3 Critical Issues

**🔴 NO CANONICAL AGENTS CONSTITUTION FILE**
- Pre-Edison AGENTS.md is only 110 lines - an INDEX to 18+ files
- No single source of truth for "what is an agent"
- Edison needs: `/edison/AGENTS_CONSTITUTION.md` (500-1000 lines)

**🔴 PROJECT-SPECIFIC HARDCODING (30+ occurrences)**
```
"wilson-component-builder" (10+ references)
"wilson-api-builder" (10+ references)
"wilson-validator-*" (15+ references)
"wilson-leadgen-worktrees" (worktree path)
"WILSON_OWNER" (environment variable)
```

**🔴 SCATTERED CONSTITUTION**
- Full constitution spans: manifest.json (142) + delegation/config.json (773) + 6 agent briefs (2,811) = 3,726+ lines
- No single document answers "how are agents orchestrated?"

**🟠 TOOL/CLI REFERENCE DRIFT**
```
Pre-Edison: .agents/scripts/session new
Post-Edison: edison session new

Pre-Edison: .agents/scripts/tasks/claim
Post-Edison: edison tasks claim
```

---

### 21.2 CLAUDE.md Orchestrator Analysis

**File:** `/wilson-pre-edison/.claude/CLAUDE.md`
**Pre-Edison Lines:** 31
**Post-Edison Equivalent:** Template-driven generation (198 lines template)
**Generated Output:** 401 lines (wilson-leadgen with 7 packs)
**Content Loss:** -538% (EXPANSION - Edison is 540% more detailed)

#### 21.2.1 Orchestrator Instructions Comparison

| Aspect | Pre-Edison | Post-Edison | Gap |
|--------|-----------|-------------|-----|
| Orchestration Role | 90% | 100% | +10% |
| Delegation Chain | 40% (implicit) | 100% (4-level explicit) | +60% |
| Task Management | 80% | 100% | +20% |
| Validation Model | 70% | 100% | +30% |
| Error Recovery | 0% | 100% | 🔴 MISSING |
| Constitutional Principles | 0% | 100% | 🔴 MISSING |
| Pack Awareness | 0% | 100% | 🔴 MISSING |

#### 21.2.2 Critical Constitutional Gaps in Pre-Edison

Pre-Edison CLAUDE.md **MISSING** these Edison principles:
- ❌ NO MOCKS
- ❌ NO LEGACY
- ❌ 100% CONFIGURABLE
- ❌ DRY / SOLID / KISS / YAGNI
- ❌ ROOT CAUSE FIXING
- ❌ STRICT COHERENCE

#### 21.2.3 Fundamental Shift: Static → Dynamic

**Pre-Edison:** Manual orchestrator brief (31 static lines)
**Post-Edison:** Template-driven generation with composition engine
- Source: `.edison/data/packs/clients/claude/CLAUDE.md` (template)
- Output: `.agents/_generated/ORCHESTRATOR_GUIDE.md` (dynamic)
- Injection: `.claude/CLAUDE.md` (for Claude Code)

#### 21.2.4 Workflow Loop Evolution

**Pre-Edison:** "Run scripts/tasks/split to create child tasks"
**Post-Edison:** "Before EVERY action, run `scripts/session next <session-id>`"

This is a **critical behavioral change** - from manual decision-making to framework-guided state machine.

---

### 21.3 START.SESSION.md Analysis

**File:** `/wilson-pre-edison/.agents/START.SESSION.md`
**Pre-Edison Lines:** 34
**Post-Edison Equivalent:** SESSION_WORKFLOW.md (544 lines)
**Content Loss:** -37% (comprehensive expansion)

#### 21.3.1 Session Protocol Comparison

**Pre-Edison (9 steps):**
1. Preload manifest.json
2. Launch session via `.agents/scripts/session new`
3. Confirm human request
4. Close stale work (>4h)
5. Leave shared QA alone
6. Reclaim stale tasks
7. Select fresh work (1-5 tasks)
8. Declare intake complete
9. Drive via `.agents/scripts/session next --limit 8`

**Post-Edison (5 phases + state machine):**
1. Auto-start via `edison session start`
2. Keep session alive (2h updates)
3. Implementation loop per task
4. Validation integration (waves)
5. Session closure (`edison session close`)

#### 21.3.2 Missing START Prompt Types

Per constitution requirements, Edison needs **THREE** START prompts:

| Type | Pre-Edison | Post-Edison | Status |
|------|-----------|-------------|--------|
| START_NEW_SESSION.md | START.SESSION.md | MISSING | 🔴 CRITICAL |
| START_RESUME_SESSION.md | (implicit) | MISSING | 🔴 CRITICAL |
| START_VALIDATE_SESSION.md | START.AUDIT.md | MISSING | 🟠 HIGH |

#### 21.3.3 State Machine Integration

**Pre-Edison:** Basic states (wip, done), no explicit state machine
**Post-Edison:** Canonical state machine in `.edison/core/defaults.yaml`
- Task states: `todo → wip ↔ blocked → done → validated`
- QA states: `waiting → todo → wip → done → validated`
- Enforcement via guards: `validate_state_transition`

#### 21.3.4 Hardcoded Values (Must Remove)

```
Line 15: "4-hour threshold" (staleness) → Should be configurable
Line 20: "1-5 tasks" (concurrency cap) → Should reference config
Line 29: "8" (session next limit) → Should be configurable
```

---

### 21.4 Wave 5 Implementation Tasks

| Task ID | Description | Priority |
|---------|-------------|----------|
| W5-001 | Create AGENTS_CONSTITUTION.md (500-1000 lines, single source of truth) | 🔴 BLOCKER |
| W5-002 | Create START_NEW_SESSION.md | 🔴 BLOCKER |
| W5-003 | Create START_RESUME_SESSION.md | 🔴 BLOCKER |
| W5-004 | Create START_VALIDATE_SESSION.md | CRITICAL |
| W5-005 | Inject constitutional principles into CLAUDE.md template | CRITICAL |
| W5-006 | Remove all "wilson-*" hardcoded zenRoles (30+ occurrences) | CRITICAL |
| W5-007 | Update all CLI references (.agents/scripts/ → edison) | HIGH |
| W5-008 | Document ConfigManager overlay mechanism | HIGH |
| W5-009 | Create project overlay template for zenRole mapping | HIGH |
| W5-010 | Add Error Recovery section to CLAUDE.md | HIGH |
| W5-011 | Document state machine explicitly in START prompts | MEDIUM |
| W5-012 | Extract hardcoded paths to config variables | MEDIUM |

---

## 22. Final Summary: All Waves Complete (2025-11-26)

### 22.1 Overall Migration Status

| Wave | Category | Files Analyzed | Status | Critical Issues |
|------|----------|---------------|--------|-----------------|
| 1 | Agents | 6 | ✅ COMPLETE | Missing YAML frontmatter, Context7 tools, Zen prompts wrong |
| 2 | Delegation | 2 | ✅ COMPLETE | 97% content loss, model definitions missing |
| 3 | Guidelines | 9 | ✅ COMPLETE | 77-88% content loss, hardcoded values |
| 4 | Rules + Validators | 15 | ✅ COMPLETE | Hardcoded paths, missing pack registries |
| 5 | Main Entry Points | 3 | ✅ COMPLETE | No AGENTS_CONSTITUTION, missing START prompts |

### 22.2 Content Analysis Summary

| Category | Pre-Edison Lines | Post-Edison Lines | Change |
|----------|-----------------|-------------------|--------|
| Agent Briefs | 2,811 | 1,626 | -42% (compressed) |
| Delegation Config | 773 | 176 | -77% (YAML efficiency) |
| Validators Config | 436 | 180 | -59% (refactored) |
| Rules Registry | 266 | 224 | -16% (JSON→YAML) |
| CLAUDE.md | 31 | 198 (template) | +538% (expanded) |
| SESSION_WORKFLOW | 34 | 544 | +1500% (comprehensive) |
| Specialized Validators | 3,412 | 5,015 | +47% (enhanced) |
| Global Validators | 1,614 | 4,527 | +180% (expanded) |

### 22.3 BLOCKER Issues (Must Fix Before Migration)

| ID | Issue | Files Affected | Impact |
|----|-------|----------------|--------|
| B-001 | No AGENTS_CONSTITUTION.md | All agents | No single source of truth |
| B-002 | Missing START_NEW_SESSION.md | Session bootstrap | Can't start clean sessions |
| B-003 | Missing START_RESUME_SESSION.md | Session recovery | Can't resume after crash |
| B-004 | Post-training packages MISSING | validators.yaml | Models can't reference Context7 |
| B-005 | Workflow context hardcoded in Python | validator.py | Not configurable via YAML |
| B-006 | Rule sourcePath hardcoding (.agents/) | registry.yml | Can't reuse in other projects |
| B-007 | Zen prompts contain WRONG content | composition engine | Validators get wrong prompts |

### 22.4 CRITICAL Issues (High Priority)

| ID | Issue | Severity |
|----|-------|----------|
| C-001 | 30+ hardcoded "wilson-*" zenRoles | Must extract to overlay |
| C-002 | TDD guidelines lost 79% content | Missing delegation templates |
| C-003 | VALIDATION guidelines hardcoded "9 validators" | Must be dynamic |
| C-004 | No pack-specific rule registries | 3-layer architecture incomplete |
| C-005 | Missing ORCHESTRATOR_VALIDATOR_RUNBOOK.md | Lost wave-based execution docs |
| C-006 | Follow-up task metadata 70% lost | Missing claimNow, parentId, files |
| C-007 | Missing constitutional principles in pre-Edison | TDD/SOLID/DRY not enforced |

### 22.5 Task Summary by Priority

| Priority | Count | Categories |
|----------|-------|------------|
| 🔴 BLOCKER | 7 | Constitution, START prompts, config gaps |
| CRITICAL | 14 | Content restoration, hardcoded values |
| HIGH | 19 | Documentation, CLI updates, pack support |
| MEDIUM | 8 | Troubleshooting, tracking, guides |

### 22.6 Migration Readiness Score

| Component | Score | Notes |
|-----------|-------|-------|
| Agent System | 70% | Briefs exist, missing constitution |
| Delegation | 60% | Config migrated, hardcoded zenRoles |
| Guidelines | 45% | Significant content loss |
| Rules | 60% | Registry migrated, paths hardcoded |
| Validators | 75% | Enhanced, missing post-training packages |
| Session System | 55% | STATE_WORKFLOW exists, missing START prompts |
| Constitution | 20% | Framework defined, files missing |
| **OVERALL** | **55%** | **Not ready for production** |

### 22.7 Recommended Migration Phases

**Phase 1: Constitution Foundation (Week 1)**
- [ ] Create AGENTS_CONSTITUTION.md
- [ ] Create START_NEW_SESSION.md
- [ ] Create START_RESUME_SESSION.md
- [ ] Create START_VALIDATE_SESSION.md
- [ ] Inject constitutional principles into CLAUDE.md

**Phase 2: Content Restoration (Week 2)**
- [ ] Restore TDD delegation templates (136 lines)
- [ ] Restore TDD verification checklist (125 lines)
- [ ] Restore VALIDATION batched parallel execution
- [ ] Restore QUALITY Premium Design Standards
- [ ] Create post-training-packages.yaml

**Phase 3: Hardcoded Value Removal (Week 3)**
- [ ] Extract "wilson-*" zenRoles to project overlay
- [ ] Remove hardcoded ".agents/" paths from rules
- [ ] Remove hardcoded validator counts from guidelines
- [ ] Externalize workflow context to YAML

**Phase 4: Pack Architecture (Week 4)**
- [ ] Create pack-specific rule registries
- [ ] Document ConfigManager overlay mechanism
- [ ] Verify Zen prompt generation embeds validator content
- [ ] Test 3-layer composition (CORE → PACKS → PROJECT)

---

## 23. Appendix: All Implementation Tasks

### 23.1 Wave 1 Tasks (Agents)
- W1-001: Add YAML frontmatter to all 6 agent files
- W1-002: Add Context7 MCP tool examples
- W1-003: Fix Zen prompt composition (BLOCKER)
- W1-004: Restore DELEGATION.md examples
- W1-005: Restore IMPLEMENTER_WORKFLOW.md extended guide
- W1-006: Add zenRole to all agent frontmatter

### 23.2 Wave 2 Tasks (Delegation)
- W2-001: Restore 7 missing task type rules
- W2-002: Restore model definitions (codex, claude, gemini)
- W2-003: Restore orchestratorGuidance section
- W2-004: Restore 4 missing sub-agent defaults
- W2-005: Create OUTPUT_FORMAT.md with schema
- W2-006: Restore 12 missing Zen role mappings
- W2-007: Restore delegation examples directory

### 23.3 Wave 3 Tasks (Guidelines)
- W3-001: Remove ALL hardcoded validator counts/names
- W3-002: Restore TDD delegation templates
- W3-003: Restore TDD verification checklist + report template
- W3-004: Restore VALIDATION batched parallel execution
- W3-005: Restore VALIDATION Round N rejection cycle
- W3-006: Fix broken SESSION_WORKFLOW extended guide reference
- W3-007: Restore SESSION_WORKFLOW extended content
- W3-008: Add Wilson-specific Context7 package IDs overlay
- W3-009: Restore QUALITY Premium Design Standards
- W3-010: Restore QUALITY Code Smell Checklist
- W3-011: Restore QUALITY code examples (10+)
- W3-012: Add missing Context7 MCP tools documentation
- W3-013: Restore TDD troubleshooting section
- W3-014: Restore VALIDATION troubleshooting section

### 23.4 Wave 4 Tasks (Rules + Validators)
- W4-001: Create post-training-packages.yaml config
- W4-002: Externalize workflow context to YAML
- W4-003: Fix rule sourcePath hardcoding
- W4-004: Convert HTML rule markers to structured anchors
- W4-005: Add blocking flags to appropriate rules
- W4-006: Create pack-specific rule registries
- W4-007: Create ORCHESTRATOR_VALIDATOR_RUNBOOK.md
- W4-008: Restore follow-up task metadata
- W4-009: Document zenRole project overlay mapping
- W4-010: Verify Zen prompt generation embeds validator content
- W4-011: Create ConfigManager overlay documentation
- W4-012: Add tracking integration documentation
- W4-013: Create validator troubleshooting guide

### 23.5 Wave 5 Tasks (Main Entry Points)
- W5-001: Create AGENTS_CONSTITUTION.md
- W5-002: Create START_NEW_SESSION.md
- W5-003: Create START_RESUME_SESSION.md
- W5-004: Create START_VALIDATE_SESSION.md
- W5-005: Inject constitutional principles into CLAUDE.md
- W5-006: Remove all "wilson-*" hardcoded zenRoles
- W5-007: Update all CLI references
- W5-008: Document ConfigManager overlay mechanism
- W5-009: Create project overlay template
- W5-010: Add Error Recovery section to CLAUDE.md
- W5-011: Document state machine in START prompts
- W5-012: Extract hardcoded paths to config variables

---

*Document Updated: 2025-11-26*
*Validation Round: 5 FINAL (Constitution System + Deep Analysis)*
*Status: ✅ ALL WAVES COMPLETE - 55% Migration Readiness*
*Total Implementation Tasks: 52*
*Blockers: 7 | Critical: 14 | High: 19 | Medium: 8*
