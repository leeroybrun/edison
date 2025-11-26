# Edison Migration: Consolidated Implementation Plan

**Generated:** 2025-11-26 (UPDATED)
**Sources:** Claude Opus (Comprehensive) + Codex CLI (via edison-zen MCP) + Gemini CLI (via edison-zen MCP)
**Migration Readiness:** 55% → Target: 100%
**Multi-Model Validation:** ✅ 3 independent AI models analyzed the same 3,356-line document
**Policy:** ⚠️ **IMPLEMENT EVERYTHING** - No "can ship without" - ALL issues must be resolved

---

## Executive Summary

Three independent analyses of the 3,356-line migration document have been merged to create this comprehensive implementation plan.

### Key Metrics

| Metric | Value |
|--------|-------|
| Total Unique Issues | 52 |
| BLOCKER Issues | 7 |
| CRITICAL Issues | 14 |
| HIGH Priority | 19 |
| MEDIUM/LOW Priority | 12 |
| **ALL MUST BE IMPLEMENTED** | ✅ |

### Critical Policy: NO DEFERRALS

**❌ REMOVED: "Can Ship Without" Section**

Per user directive, we will **implement EVERYTHING**. There are no "known limitations" or "defer to v1.1" items. All 52 issues must be resolved before the migration is considered complete.

---

## Multi-Model Analysis Consensus

### Three Models, One Diagnosis

All three AI models (Claude Opus, Codex, Gemini) independently identified the **same core issues**, providing high confidence in the findings:

| Issue | Claude | Codex | Gemini | Consensus |
|-------|--------|-------|--------|-----------|
| Zen prompts contain wrong content | ✅ B-001 | ✅ ISS-03 | ✅ "Identity Crisis" | **UNANIMOUS** |
| Pack duplication bug (5-7x bloat) | ✅ B-003 | ✅ ISS-07 | ✅ Phase 1 | **UNANIMOUS** |
| Missing post-training packages | ✅ B-002 | ✅ ISS-04 | ✅ Phase 0 | **UNANIMOUS** |
| Hardcoded paths in rules | ✅ B-004 | ✅ ISS-06 | ✅ "Fragile Hardcoding" | **UNANIMOUS** |
| Constitution system missing | ✅ B-006/B-007 | ✅ ISS-01/ISS-02 | ✅ Phase 0 (BLOCKING) | **UNANIMOUS** |
| Content loss (TDD/QUALITY) | ✅ C-004/C-006 | ✅ ISS-12 | ✅ "Lost Context Pattern" | **UNANIMOUS** |

### Root Cause Analysis (Multi-Model Synthesis)

#### Gemini's "Three Sins" Framework
1. **Lost Context Pattern**: Critical domain knowledge lost during migration
2. **Identity Crisis (Zen Disconnect)**: Zen prompts disconnected from their sources
3. **Fragile Hardcoding**: Magic values scattered throughout

#### Codex's Issue Registry (22 Issues)
- **ISS-01 through ISS-22** with categories: ARCHITECTURE, CODE, CONFIG, CONTENT, DOCS
- **7 Blockers identified**: ISS-01 (No constitution), ISS-02 (Missing START prompts), ISS-03 (Zen prompt wrong content), ISS-04 (Missing post-training packages), ISS-05 (Workflow hardcoded in Python), ISS-06 (Rules hardcoded paths), ISS-07 (Hardcoded validator counts)

#### Claude's Architectural Insight
- **Premature genericization** without proper abstraction layers
- Migration attempted CORE → PACKS → PROJECT in one leap without defining composition semantics

### Gemini's Recommended Approach: "Literate Configuration"

Gemini recommended treating the **Constitution as a first-class object**:
- Markdown Constitution files become the **source of truth**
- Configuration is derived from, not duplicated in, Constitution
- Pack-based rule inheritance with clear override semantics
- Configuration-driven overlays for project-specific values

---

## Constitution System Architecture (CORRECTED)

### Correct Naming Convention

The constitution files use **PLURAL** naming to match their role-based scope:

```
.edison/_generated/
├── AVAILABLE_AGENTS.md              # Dynamic agent roster
├── AVAILABLE_VALIDATORS.md          # Dynamic validator roster
├── constitutions/                   # Role-based constitutions (PLURAL)
│   ├── ORCHESTRATORS.md            # Orchestrator constitution
│   ├── AGENTS.md                   # Agent constitution
│   └── VALIDATORS.md               # Validator constitution
├── agents/                         # Composed agent prompts
├── validators/                     # Composed validator prompts
└── guidelines/                     # Composed guidelines
```

**Note:** The folder is `constitutions/` (plural) and files are:
- `ORCHESTRATORS.md` (not ORCHESTRATOR_CONSTITUTION.md)
- `AGENTS.md` (not AGENTS_CONSTITUTION.md)
- `VALIDATORS.md` (not VALIDATORS_CONSTITUTION.md)

### Three-Layer Composability

```
CORE (edison/core/) → PACKS (edison/packs/<pack>/) → PROJECT (.edison/)
```

| Layer | Location | Purpose |
|-------|----------|---------|
| **CORE** | `edison/core/constitutions/` | Base definitions |
| **PACKS** | `edison/packs/<pack>/constitutions/` | Technology-specific additions |
| **PROJECT** | `.edison/constitutions/` | Project-specific overrides |

### Generated Outputs

| File Type | Source Layers | Generated To |
|-----------|--------------|--------------|
| ORCHESTRATORS.md | core + packs + project | `.edison/_generated/constitutions/ORCHESTRATORS.md` |
| AGENTS.md | core + packs + project | `.edison/_generated/constitutions/AGENTS.md` |
| VALIDATORS.md | core + packs + project | `.edison/_generated/constitutions/VALIDATORS.md` |

---

## Edison-Zen MCP Server Setup (NEW REQUIREMENT)

### Overview

Edison uses the Zen MCP server for sub-agent delegation. This must be set up automatically when installing Edison in a project.

### Current State

The `scripts/zen/run-server.sh` already handles three installation scenarios:
1. **ZEN_MCP_SERVER_DIR** - Custom location (for development)
2. **~/zen-mcp-server** - Standard clone location
3. **uvx** - Instant setup via `uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server`

### Required Implementation: `edison zen` CLI Commands

#### New CLI Commands

```bash
# Setup zen-mcp-server (downloads/installs if needed)
edison zen setup

# Start zen-mcp-server
edison zen start-server

# Configure .mcp.json in target project
edison zen configure
```

#### `edison zen setup` Implementation

```python
# src/edison/cli/commands/zen.py
@click.group()
def zen():
    """Zen MCP server management commands."""
    pass

@zen.command()
def setup():
    """Setup zen-mcp-server for Edison integration."""
    # Check if zen-mcp-server is already available
    # 1. Check ~/zen-mcp-server exists
    # 2. If not, check uvx is available
    # 3. If uvx not available, prompt to install: pip install uv
    # 4. Verify setup works by running version check
    pass

@zen.command()
def start_server():
    """Start the zen-mcp-server."""
    # Delegates to scripts/zen/run-server.sh
    pass

@zen.command()
@click.argument('project_path', default='.')
def configure(project_path):
    """Configure .mcp.json in target project for edison-zen."""
    # Adds edison-zen entry to .mcp.json
    pass
```

#### MCP Configuration Template

When `edison zen configure` is run, it should add/update `.mcp.json`:

```json
{
  "mcpServers": {
    "edison-zen": {
      "command": "edison",
      "args": ["zen", "start-server"],
      "env": {
        "ZEN_WORKING_DIR": "{{project_root}}"
      }
    }
  }
}
```

**Alternative (shell script approach - current):**

```json
{
  "mcpServers": {
    "edison-zen": {
      "command": "bash",
      "args": ["./scripts/zen/run-server.sh"],
      "env": {
        "ZEN_WORKING_DIR": "{{project_root}}"
      }
    }
  }
}
```

### uvx Dependency Handling

Since Edison is installed via `uvx`, and zen-mcp-server is also available via `uvx`, we have options:

**Option A: Document as prerequisite**
```
# Prerequisites:
# 1. uvx (pip install uv)
# 2. zen-mcp-server will be auto-installed on first run
```

**Option B: Bundle zen-mcp-server as Edison dependency**
- Add `zen-mcp-server` to Edison's `pyproject.toml` dependencies
- Requires zen-mcp-server to be published on PyPI

**Option C: Auto-install via subprocess (RECOMMENDED)**
```python
def ensure_zen_mcp_server():
    """Ensure zen-mcp-server is available."""
    # Try to import or run zen-mcp-server
    # If not found, run: uvx install zen-mcp-server
    pass
```

### Implementation Tasks for Zen MCP

| Task ID | Description | Priority |
|---------|-------------|----------|
| ZEN-001 | Create `edison zen setup` command | BLOCKER |
| ZEN-002 | Create `edison zen start-server` command | BLOCKER |
| ZEN-003 | Create `edison zen configure` command | BLOCKER |
| ZEN-004 | Auto-detect uvx availability | HIGH |
| ZEN-005 | Template .mcp.json configuration | HIGH |
| ZEN-006 | Document zen setup in Edison README | HIGH |
| ZEN-007 | Add zen setup to `edison init` flow | CRITICAL |

---

## Cross-Model Issue Mapping

### Codex → Claude Issue ID Translation

| Codex ID | Description | Claude ID | Category |
|----------|-------------|-----------|----------|
| ISS-01 | No constitutions/AGENTS.md | B-006 | ARCHITECTURE |
| ISS-02 | Missing START prompts | B-007, C-001, C-002 | ARCHITECTURE |
| ISS-03 | Zen prompts contain wrong content | B-001 | CODE |
| ISS-04 | Missing post-training packages config | B-002 | CONFIG |
| ISS-05 | Workflow context hardcoded in Python | C-013 | CODE |
| ISS-06 | Rules hardcoded paths (.agents/) | B-004 | CONFIG |
| ISS-07 | Hardcoded validator counts | C-005 | CONFIG |
| ISS-08 | Pack sections duplicated | B-003 | CODE |
| ISS-09 | Missing YAML frontmatter | B-005 | CONTENT |
| ISS-10 | Broken cross-references | C-009 | CONTENT |
| ISS-11 | Unresolved placeholders | C-010 | CONTENT |
| ISS-12 | TDD guidelines 79% content loss | C-004 | CONTENT |
| ISS-13 | QUALITY guidelines 88% content loss | C-006 | CONTENT |
| ISS-14 | Delegation config 97% content loss | C-007 | CONFIG |
| ISS-15 | Missing Context7 examples | C-008 | CONTENT |
| ISS-16 | Constitutional principles missing | C-014 | CONTENT |
| ISS-17 | Hardcoded "wilson-*" zenRoles | C-003 | CONFIG |
| ISS-18 | Follow-up task metadata lost | C-011 | CONFIG |
| ISS-19 | Missing validator runbook | C-012 | DOCS |
| ISS-20 | Pack-specific rules missing | H-001 | ARCHITECTURE |
| ISS-21 | ConfigManager docs missing | H-002 | DOCS |
| ISS-22 | CLI references outdated | H-003 | CONTENT |

### Gemini's Abstraction Opportunities

| Opportunity | Description | Related Issues |
|-------------|-------------|----------------|
| **Constitution as First-Class Object** | Treat constitutions/*.md as source of truth | B-006, B-007, C-001, C-002 |
| **Pack-Based Rule Inheritance** | Rules inherit CORE → PACKS → PROJECT | B-004, H-001, C-013 |
| **Configuration-Driven Overlays** | All project-specific values externalized | C-003, C-005, C-010, C-014 |
| **Content Recovery Templates** | Structured templates for restoring lost content | C-004, C-006, C-007, C-008 |

---

## 1. Deduplicated Issue Registry

### 1.1 BLOCKER Issues (Must Fix to Release)

| ID | Issue | Category | Root Cause | Files Affected | Effort |
|----|-------|----------|------------|----------------|--------|
| B-001 | Zen prompts contain wrong content | CODE | Composition router maps wrong source | composers.py | 4h |
| B-002 | Missing post-training packages config | CONFIG | Never migrated | validators.yaml | 2h |
| B-003 | Pack sections duplicated 5-7x | CODE | No deduplication in composition | composers.py | 4h |
| B-004 | Hardcoded `.agents/` paths in rules | CONFIG | Legacy paths not updated | registry.yml | 1h |
| B-005 | Missing YAML frontmatter | CONTENT | Template not applied | 6 agent files | 1h |
| B-006 | No constitutions/AGENTS.md | ARCHITECTURE | Never created | New file | 4h |
| B-007 | Missing START_NEW_SESSION.md | ARCHITECTURE | Never created | New file | 3h |
| B-008 | Missing `edison zen` CLI commands | CLI | Never implemented | New commands | 4h |

### 1.2 CRITICAL Issues (ALL MUST BE IMPLEMENTED)

| ID | Issue | Category | Root Cause | Effort |
|----|-------|----------|------------|--------|
| C-001 | Missing START_RESUME_SESSION.md | ARCHITECTURE | Never created | 2h |
| C-002 | Missing START_VALIDATE_SESSION.md | ARCHITECTURE | Never created | 2h |
| C-003 | 30+ hardcoded "wilson-*" zenRoles | CONFIG | Project-specific values | 2h |
| C-004 | TDD guidelines 79% content loss | CONTENT | Migration truncation | 6h |
| C-005 | VALIDATION guidelines hardcoded "9 validators" | CONTENT | Template not used | 1h |
| C-006 | QUALITY guidelines 88% content loss | CONTENT | Migration truncation | 4h |
| C-007 | Delegation config 97% content loss | CONFIG | Migration truncation | 4h |
| C-008 | Missing Context7 tool examples | CONTENT | Never added to agents | 2h |
| C-009 | Broken cross-references (6+ instances) | CONTENT | Path changes not updated | 1h |
| C-010 | Unresolved placeholders ({{framework}}) | CONTENT | Template not processed | 1h |
| C-011 | Follow-up task metadata 70% lost | CONFIG | Schema simplified | 2h |
| C-012 | Missing ORCHESTRATOR_VALIDATOR_RUNBOOK | DOCS | Never created | 3h |
| C-013 | Workflow context hardcoded in Python | CODE | Not externalized to YAML | 3h |
| C-014 | Constitutional principles missing in CLAUDE.md | CONTENT | Never added | 2h |

### 1.3 HIGH Priority Issues (ALL MUST BE IMPLEMENTED)

| ID | Issue | Category | Effort |
|----|-------|----------|--------|
| H-001 | Missing pack-specific rule registries | ARCHITECTURE | 4h |
| H-002 | No ConfigManager overlay documentation | DOCS | 2h |
| H-003 | All CLI references need updating | CONTENT | 2h |
| H-004 | Missing TDD delegation templates | CONTENT | 3h |
| H-005 | Missing TDD verification checklist | CONTENT | 2h |
| H-006 | Missing VALIDATION batched parallel execution | CONTENT | 2h |
| H-007 | Session workflow extended guide broken | CONTENT | 2h |
| H-008 | Missing Context7 package IDs overlay | CONFIG | 2h |
| H-009 | Missing QUALITY Premium Design Standards | CONTENT | 3h |
| H-010 | Missing QUALITY Code Smell Checklist | CONTENT | 2h |
| H-011 | Agent Server/Client examples missing | CONTENT | 2h |
| H-012 | Database schema template missing | CONTENT | 2h |
| H-013 | Test patterns truncated | CONTENT | 2h |
| H-014 | Zen prompt dual files unclear | DOCS | 1h |
| H-015 | Missing validator consensus logic | DOCS | 2h |
| H-016 | Project overlay template needed | CONFIG | 2h |
| H-017 | Error recovery section missing | CONTENT | 2h |
| H-018 | State machine not documented in START | DOCS | 1h |
| H-019 | Hardcoded paths need config variables | CONFIG | 2h |

---

## 2. Dependency Graph

### 2.1 Critical Dependencies

```
B-008 (Zen CLI) ──> ZEN-001 through ZEN-007 (Zen MCP Setup)

B-001 (Zen Prompts) ──┐
                      ├──> B-003 (Pack Duplication) ──> All Content Tasks
B-002 (Post-Training) ┘

B-006 (constitutions/AGENTS.md) ──> B-007 (START_NEW) ──> C-001 (START_RESUME)
                                 └──> C-002 (START_VALIDATE)

B-004 (Rule Paths) ──> H-001 (Pack Registries)

B-005 (Frontmatter) ──> C-008 (Context7 Examples)
```

### 2.2 No Circular Dependencies Found

The task graph forms a clean DAG (Directed Acyclic Graph).

---

## 3. Parallel Execution Waves

### Wave A: Foundation (Week 1) - BLOCKERS

**Duration:** 5 days
**Parallelizable Groups:**

**Group A1: Composition Engine Fixes (1 dev)**
- B-001: Fix Zen prompt composition (4h)
- B-003: Fix pack duplication bug (4h)

**Group A2: Config Creation (1 dev)**
- B-002: Create post-training-packages.yaml (2h)
- B-004: Fix hardcoded paths in rules (1h)
- B-005: Add YAML frontmatter to agents (1h)

**Group A3: Constitution Files (1 dev)**
- B-006: Create constitutions/AGENTS.md (4h)
- B-007: Create START_NEW_SESSION.md (3h)
- C-001: Create START_RESUME_SESSION.md (2h)
- C-002: Create START_VALIDATE_SESSION.md (2h)

**Group A4: Zen MCP CLI (1 dev)**
- B-008: Create `edison zen setup` command (2h)
- B-008: Create `edison zen start-server` command (1h)
- B-008: Create `edison zen configure` command (1h)
- ZEN-007: Add zen setup to `edison init` flow (2h)

**Wave A Validation Checkpoint:**
```bash
# Verify Zen prompts correct
grep "API Builder" .zen/conf/systemprompts/wilson-api-builder.txt
grep "Gemini Global Validator" .zen/conf/systemprompts/wilson-api-builder.txt # Should fail

# Verify frontmatter
grep "zenRole:" .edison/_generated/agents/*.md | wc -l # Should be 6

# Verify constitution files exist (CORRECTED PATHS)
ls .edison/_generated/constitutions/ORCHESTRATORS.md
ls .edison/_generated/constitutions/AGENTS.md
ls .edison/_generated/constitutions/VALIDATORS.md

# Verify Zen CLI works
edison zen setup --check
edison zen configure --dry-run
```

---

### Wave B: Critical Content (Week 2)

**Duration:** 5 days
**Parallelizable Groups:**

**Group B1: Agent Content (1 dev)**
- C-008: Add Context7 tool examples to all 6 agents (2h)
- H-011: Restore Server/Client examples (2h)
- H-012: Restore database schema template (2h)
- H-013: Restore test patterns (2h)

**Group B2: Guideline Content (1 dev)**
- C-004: Restore TDD guidelines (6h)
- H-004: Restore TDD delegation templates (3h)
- H-005: Restore TDD verification checklist (2h)

**Group B3: Configuration (1 dev)**
- C-007: Restore delegation config (4h)
- C-011: Restore follow-up task metadata (2h)
- C-013: Externalize workflow context to YAML (3h)

**Group B4: Hardcoded Values (1 dev)**
- C-003: Remove "wilson-*" hardcoded zenRoles (2h)
- C-005: Remove hardcoded "9 validators" (1h)
- C-009: Fix broken cross-references (1h)
- C-010: Resolve {{placeholders}} (1h)
- C-014: Inject constitutional principles (2h)

**Wave B Validation Checkpoint:**
```bash
# Verify no hardcoded values
grep -r "9-validator" src/edison/data/guidelines/ # Should fail
grep -r "wilson-" src/edison/data/config/ # Should fail (except project overlay)

# Verify content restored
wc -l src/edison/data/guidelines/shared/TDD.md # Should be > 500

# Verify templates resolved
grep "{{" .edison/_generated/**/*.md # Should fail
```

---

### Wave C: High Priority (Week 3) - ALL MUST BE IMPLEMENTED

**Duration:** 5 days
**Parallelizable Groups:**

**Group C1: Content Completion (1 dev)**
- C-006: Restore QUALITY guidelines (4h)
- H-006: Restore VALIDATION parallel execution (2h)
- H-009: Restore QUALITY Premium Design Standards (3h)
- H-010: Restore QUALITY Code Smell Checklist (2h)

**Group C2: Architecture (1 dev)**
- H-001: Create pack-specific rule registries (4h)
- H-008: Create Context7 package IDs overlay (2h)
- H-016: Create project overlay template (2h)
- H-019: Extract hardcoded paths to config (2h)

**Group C3: Documentation (1 dev)**
- C-012: Create ORCHESTRATOR_VALIDATOR_RUNBOOK.md (3h)
- H-002: Document ConfigManager overlays (2h)
- H-014: Clarify Zen prompt dual files (1h)
- H-015: Document validator consensus (2h)

**Group C4: Cleanup (1 dev)**
- H-003: Update all CLI references (2h)
- H-007: Fix session workflow extended guide (2h)
- H-017: Add error recovery section (2h)
- H-018: Document state machine in START (1h)

**Wave C Validation Checkpoint:**
```bash
# Verify all documentation exists
ls edison/docs/ORCHESTRATOR_VALIDATOR_RUNBOOK.md
ls edison/docs/CONFIGMANAGER_OVERLAYS.md

# Verify pack registries
ls edison/packs/nextjs/rules/registry.yml
ls edison/packs/prisma/rules/registry.yml

# Verify CLI references updated
grep -r "\.agents/scripts/" src/edison/data/ # Should fail
```

---

### Wave D: Polish + Verification (Week 4)

**Duration:** 5 days

**ALL Tasks (No Deferrals):**
- End-to-end testing of full composition pipeline
- Migration validation (pre vs post comparison)
- Performance testing (composition time)
- Documentation review and completion
- Final cleanup of duplicate files
- Verify ALL 52 issues are resolved

**Wave D Validation Checkpoint:**
```bash
# Full composition test
edison compose --all
diff -r .edison/_generated.baseline .edison/_generated # No unexpected changes

# Run all tests
pytest tests/composition/ -v
pytest tests/zen/ -v

# Verify migration readiness
python scripts/validators/migration_validator.py # Should pass

# Verify Zen MCP integration
edison zen setup --verify
```

---

## 4. Critical Path Analysis

### 4.1 Multi-Model Critical Path Consensus

**Codex's Critical Path:**
```
ISS-04 (Post-training) → ISS-05 (Workflow) → ISS-06 (Paths) → ISS-03 (Zen) → ISS-01 (Constitution) → ISS-02 (START)
```

**Gemini's Phased Approach:**
```
Phase 0 (BLOCKING): Constitution Foundation + Config Externalization + Zen MCP Setup
    ↓
Phase 1: Critical Content Restoration
    ↓
Phase 2: Architecture & Coherence
    ↓
Phase 3: Quality & Documentation
    ↓
Phase 4: Verification (NO DEFERRALS)
```

**Claude's Wave Structure:**
```
Wave A (Blockers + Zen) → Wave B (Critical) → Wave C (High) → Wave D (Complete All)
```

### 4.2 Unified Minimum Sequence to Production

```
Day 1-2: B-001 (Zen Prompts) + B-003 (Duplication) + B-008 (Zen CLI) [Codex: ISS-03, ISS-07]
    ↓
Day 3: B-002 (Post-Training) + B-004 (Paths) + B-005 (Frontmatter) [Codex: ISS-04, ISS-06]
    ↓
Day 4-5: B-006 (constitutions/AGENTS.md) + B-007 (START_NEW) [Gemini: Phase 0, Codex: ISS-01, ISS-02]
    ↓
Day 6-7: C-003 (zenRoles) + C-005 (hardcoded) + C-009 (refs) [Gemini: "Fragile Hardcoding"]
    ↓
Day 8-10: Content restoration (TDD, VALIDATION, QUALITY) [Gemini: "Lost Context Pattern", Codex: ISS-12]
    ↓
Day 11-13: HIGH priority items (H-001 through H-019) [ALL MUST BE DONE]
    ↓
Day 14-15: End-to-end testing + Final verification
    ↓
Day 16: Release (ALL 52 issues resolved)

Total Critical Path: 16 days (1 developer)
With 4 developers: 10-12 days
```

---

## 5. Quick Wins (Under 30 mins each)

| ID | Task | Time | Command |
|----|------|------|---------|
| QW-1 | Remove "9 validators" hardcoding | 15m | `sed -i 's/9-validator/See AVAILABLE_VALIDATORS.md/g' src/edison/data/**/*.md` |
| QW-2 | Update CLI references | 20m | `find src/edison/data -name "*.md" -exec sed -i 's/\.agents\/scripts\//edison /g' {} \;` |
| QW-3 | Add self-identification headers | 30m | Prepend generation header to all composers |
| QW-4 | Fix broken cross-references | 25m | `sed -i 's/CONTEXT7_GUIDE\.md/CONTEXT7.md/g' src/edison/data/**/*.md` |
| QW-5 | Remove duplicate files | 20m | Delete identified duplicates, keep canonical |

---

## 6. Code Changes Manifest

### 6.1 Critical Files to Modify

**File:** `src/edison/core/composition/composers.py`
```python
# CURRENT (WRONG):
def compose_zen_prompt(agent_name: str):
    return compose_validator(agent_name)  # BUG!

# FIX:
def compose_zen_prompt(agent_name: str):
    role_type = get_role_type(agent_name)
    if role_type == "validator":
        return compose_validator(agent_name)
    elif role_type == "agent":
        return compose_agent(agent_name)
    else:
        raise ValueError(f"Unknown role type for {agent_name}")
```

**File:** `src/edison/data/rules/registry.yml`
```yaml
# FIND/REPLACE:
# OLD: sourcePath: ".agents/guidelines/DELEGATION.md"
# NEW: sourcePath: "guidelines/shared/DELEGATION.md"
```

### 6.2 New Files to Create

| File | Lines | Purpose |
|------|-------|---------|
| `src/edison/data/config/post_training_packages.yaml` | ~80 | Context7 package versions |
| `src/edison/core/constitutions/orchestrators-base.md` | ~300 | Core orchestrator constitution |
| `src/edison/core/constitutions/agents-base.md` | ~300 | Core agent constitution |
| `src/edison/core/constitutions/validators-base.md` | ~200 | Core validator constitution |
| `src/edison/core/start/START_NEW_SESSION.md` | ~100 | Session bootstrap |
| `src/edison/core/start/START_RESUME_SESSION.md` | ~80 | Session recovery |
| `src/edison/core/start/START_VALIDATE_SESSION.md` | ~80 | Validation intake |
| `src/edison/cli/commands/zen.py` | ~150 | Zen MCP CLI commands |

### 6.3 Generated Output Files

| Generated File | Source Layers | Purpose |
|----------------|---------------|---------|
| `.edison/_generated/constitutions/ORCHESTRATORS.md` | core + packs + project | Orchestrator constitution |
| `.edison/_generated/constitutions/AGENTS.md` | core + packs + project | Agent constitution |
| `.edison/_generated/constitutions/VALIDATORS.md` | core + packs + project | Validator constitution |
| `.mcp.json` | `edison zen configure` | MCP server configuration |

---

## 7. Risk Assessment

### 7.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Composition rewrite required | 30% | HIGH | Start with targeted fix, escalate if needed |
| Content restoration incomplete | 40% | MEDIUM | Use pre-Edison as fallback reference |
| Template system complexity | 25% | MEDIUM | Start with simple Handlebars |
| Pack architecture unclear | 35% | MEDIUM | Document as you implement |
| Zen MCP uvx compatibility | 20% | MEDIUM | Test on multiple environments |

### 7.2 Process Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep | 50% | HIGH | **NO DEFERRALS** - implement all 52 issues |
| Merge conflicts | 30% | LOW | Clear file ownership per developer |
| Testing gaps | 40% | MEDIUM | Add validation checkpoints per wave |

### 7.3 Rollback Strategy

```bash
# If Edison compose breaks:
git tag pre-migration-fix
git revert HEAD~4..HEAD

# If Zen prompts wrong:
cp .zen/conf/systemprompts.backup/*.txt .zen/conf/systemprompts/

# If Zen MCP fails:
edison zen setup --force
```

---

## 8. Success Metrics

### 8.1 Completion Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Migration Readiness | 55% | **100%** |
| Blocker Issues | 7 | **0** |
| Critical Issues | 14 | **0** |
| High Issues | 19 | **0** |
| Content Loss (avg) | 45% | **<10%** |

### 8.2 Quality Metrics

| Metric | Target |
|--------|--------|
| Hardcoded values | **0** |
| Broken references | **0** |
| Unresolved placeholders | **0** |
| Duplicate files | **0** |

### 8.3 Architecture Metrics

| Metric | Target |
|--------|--------|
| Core files referencing project | **0** |
| Template variable resolution | **100%** |
| Composition determinism | **Same input = same output** |
| Zen MCP integration | **Working on all platforms** |

---

## 9. Recommended Team Structure

### Option 1: Solo Developer (4 weeks)

Week 1: Wave A (Blockers + Zen CLI)
Week 2: Wave B (Critical)
Week 3: Wave C (High)
Week 4: Wave D (Complete All + Verification)

### Option 2: 4 Developers (2.5 weeks)

| Developer | Week 1 | Week 2 |
|-----------|--------|--------|
| Dev 1 | Composition Engine (A1) | Content - Agents (B1) |
| Dev 2 | Config Creation (A2) | Content - Guidelines (B2) |
| Dev 3 | Constitution Files (A3) | Configuration (B3) |
| Dev 4 | Zen CLI (A4) | Hardcoded Values (B4) |

Week 3: All devs on Wave C + D (parallel documentation + testing + verification)

---

## 10. Appendix: Complete Task Checklist

### BLOCKERS (8)
- [ ] B-001: Fix Zen prompt composition
- [ ] B-002: Create post-training-packages.yaml
- [ ] B-003: Fix pack duplication bug
- [ ] B-004: Fix hardcoded paths in rules
- [ ] B-005: Add YAML frontmatter to agents
- [ ] B-006: Create constitutions/AGENTS.md
- [ ] B-007: Create START_NEW_SESSION.md
- [ ] B-008: Create `edison zen` CLI commands

### CRITICAL (14)
- [ ] C-001: Create START_RESUME_SESSION.md
- [ ] C-002: Create START_VALIDATE_SESSION.md
- [ ] C-003: Remove "wilson-*" zenRoles
- [ ] C-004: Restore TDD guidelines
- [ ] C-005: Remove hardcoded "9 validators"
- [ ] C-006: Restore QUALITY guidelines
- [ ] C-007: Restore delegation config
- [ ] C-008: Add Context7 tool examples
- [ ] C-009: Fix broken cross-references
- [ ] C-010: Resolve {{placeholders}}
- [ ] C-011: Restore follow-up task metadata
- [ ] C-012: Create ORCHESTRATOR_VALIDATOR_RUNBOOK
- [ ] C-013: Externalize workflow context
- [ ] C-014: Inject constitutional principles

### HIGH (19)
- [ ] H-001: Create pack-specific rule registries
- [ ] H-002: Document ConfigManager overlays
- [ ] H-003: Update all CLI references
- [ ] H-004: Restore TDD delegation templates
- [ ] H-005: Restore TDD verification checklist
- [ ] H-006: Restore VALIDATION parallel execution
- [ ] H-007: Fix session workflow extended guide
- [ ] H-008: Create Context7 package IDs overlay
- [ ] H-009: Restore QUALITY Premium Design Standards
- [ ] H-010: Restore QUALITY Code Smell Checklist
- [ ] H-011: Restore Agent Server/Client examples
- [ ] H-012: Restore database schema template
- [ ] H-013: Restore test patterns
- [ ] H-014: Clarify Zen prompt dual files
- [ ] H-015: Document validator consensus logic
- [ ] H-016: Create project overlay template
- [ ] H-017: Add error recovery section
- [ ] H-018: Document state machine in START
- [ ] H-019: Extract hardcoded paths to config

### ZEN MCP SETUP (7)
- [ ] ZEN-001: Create `edison zen setup` command
- [ ] ZEN-002: Create `edison zen start-server` command
- [ ] ZEN-003: Create `edison zen configure` command
- [ ] ZEN-004: Auto-detect uvx availability
- [ ] ZEN-005: Template .mcp.json configuration
- [ ] ZEN-006: Document zen setup in Edison README
- [ ] ZEN-007: Add zen setup to `edison init` flow

---

## 11. Multi-Model Validation Summary

### Model Contributions

| Model | Contribution | Unique Insight |
|-------|-------------|----------------|
| **Claude Opus** | Comprehensive issue registry (52 issues), Wave-based execution plan | Architectural root cause: premature genericization |
| **Codex CLI** | 22-issue ISS registry, specific code fixes, dependency chain | Pragmatic blocker assessment |
| **Gemini CLI** | "Three Sins" framework, 4-phase approach, Literate Configuration | Constitution as first-class object |

### Consensus Strength

- **100% Agreement** on 6 core issues (see consensus table)
- **3 different frameworks** for categorizing issues (Waves, ISS-IDs, Phases)
- **1 unified critical path** derived from all three perspectives

### Implementation Policy

**⚠️ ALL ISSUES MUST BE IMPLEMENTED**

1. **Start with Constitution Foundation**: constitutions/ORCHESTRATORS.md, AGENTS.md, VALIDATORS.md
2. **Setup Zen MCP**: `edison zen` CLI commands for seamless integration
3. **Apply ALL blockers**: B-001 through B-008
4. **Complete ALL critical**: C-001 through C-014
5. **Implement ALL high priority**: H-001 through H-019
6. **Add Zen MCP setup**: ZEN-001 through ZEN-007
7. **Verify 100% completion**: No deferrals, no "known limitations"

---

## 12. Detailed Wave Tasks (From Analysis Document)

**Reference:** `PHASE_PRE-EDISON_MIGRATION_1_NEW_ANALYSIS.md` Sections 16-23

### 12.1 Wave 1 Tasks: Agent Files (14 tasks)

| Task ID | Description | Priority | Effort |
|---------|-------------|----------|--------|
| W1-001 | Add YAML frontmatter to all 6 agents (name, description, model, zenRole) | CRITICAL | 1h |
| W1-002 | Restore Context7 MCP tool call examples to all agents | CRITICAL | 2h |
| W1-003 | Fix Zen prompt composition - wrong role being generated | 🔴 BLOCKER | 4h |
| W1-004 | Restore training cutoff warning to all agents | CRITICAL | 0.5h |
| W1-005 | Restore EPHEMERAL_SUMMARIES_POLICY references | HIGH | 0.5h |
| W1-006 | Restore component-builder Server/Client examples (53 lines) | CRITICAL | 2h |
| W1-007 | Restore database-architect schema.prisma template (50 lines) | CRITICAL | 1h |
| W1-008 | Restore database-architect migration safety classifications | CRITICAL | 1h |
| W1-009 | Restore Tailwind v4 detailed rules (all relevant agents) | CRITICAL | 1h |
| W1-010 | Restore IMPORTANT RULES sections (numbered lists) | HIGH | 1h |
| W1-011 | Resolve Fastify vs Next.js contradiction | CRITICAL | 0.5h |
| W1-012 | Add self-identification headers with constitution reference | HIGH | 1h |
| W1-013 | Restore "Why no delegation" reasoning to code-reviewer | MEDIUM | 0.5h |
| W1-014 | Restore Wilson-specific entity examples (prisma.lead) | MEDIUM | 1h |

### 12.2 Wave 2 Tasks: Delegation Files (7 tasks)

| Task ID | Description | Priority | Effort |
|---------|-------------|----------|--------|
| W2-001 | Restore 7 missing task type rules | CRITICAL | 2h |
| W2-002 | Restore model definitions (codex, claude, gemini capabilities) | CRITICAL | 2h |
| W2-003 | Restore orchestratorGuidance section | CRITICAL | 1h |
| W2-004 | Restore 4 missing sub-agent defaults | HIGH | 1h |
| W2-005 | Create OUTPUT_FORMAT.md with schema | HIGH | 1h |
| W2-006 | Restore 12 missing Zen role mappings | HIGH | 1h |
| W2-007 | Restore delegation examples directory | MEDIUM | 1h |

### 12.3 Wave 3 Tasks: Guidelines Files (14 tasks)

| Task ID | Description | Priority | Effort |
|---------|-------------|----------|--------|
| W3-001 | Remove ALL hardcoded validator counts/names from guidelines | 🔴 BLOCKER | 1h |
| W3-002 | Restore TDD delegation templates (136 lines) | CRITICAL | 2h |
| W3-003 | Restore TDD verification checklist + report template (171 lines) | CRITICAL | 2h |
| W3-004 | Restore VALIDATION batched parallel execution | CRITICAL | 1h |
| W3-005 | Restore VALIDATION Round N rejection cycle | CRITICAL | 1h |
| W3-006 | Fix broken SESSION_WORKFLOW extended guide reference | HIGH | 0.5h |
| W3-007 | Restore SESSION_WORKFLOW extended content OR remove reference | HIGH | 2h |
| W3-008 | Add Wilson-specific Context7 package IDs overlay | HIGH | 1h |
| W3-009 | Restore QUALITY Premium Design Standards | HIGH | 2h |
| W3-010 | Restore QUALITY Code Smell Checklist (40+ items) | HIGH | 1h |
| W3-011 | Restore QUALITY code examples (10+) | HIGH | 2h |
| W3-012 | Add missing Context7 MCP tools documentation | MEDIUM | 1h |
| W3-013 | Restore TDD troubleshooting section (190 lines) | MEDIUM | 1h |
| W3-014 | Restore VALIDATION troubleshooting section | MEDIUM | 1h |

### 12.4 Wave 4 Tasks: Rules & Validators (13 tasks)

| Task ID | Description | Priority | Effort |
|---------|-------------|----------|--------|
| W4-001 | Create post-training-packages.yaml config | 🔴 BLOCKER | 2h |
| W4-002 | Externalize workflow context to YAML (not Python) | 🔴 BLOCKER | 3h |
| W4-003 | Fix rule sourcePath hardcoding (.agents/ → configurable) | 🔴 BLOCKER | 1h |
| W4-004 | Convert HTML rule markers to structured anchors | CRITICAL | 2h |
| W4-005 | Add blocking flags to appropriate rules | CRITICAL | 1h |
| W4-006 | Create pack-specific rule registries | HIGH | 4h |
| W4-007 | Create ORCHESTRATOR_VALIDATOR_RUNBOOK.md | HIGH | 3h |
| W4-008 | Restore follow-up task metadata (claimNow, parentId, etc.) | HIGH | 2h |
| W4-009 | Document zenRole project overlay mapping | HIGH | 1h |
| W4-010 | Verify Zen prompt generation embeds validator content | HIGH | 2h |
| W4-011 | Create ConfigManager overlay documentation | MEDIUM | 2h |
| W4-012 | Add tracking integration documentation | MEDIUM | 1h |
| W4-013 | Create validator troubleshooting guide | MEDIUM | 2h |

### 12.5 Wave 5 Tasks: Main Entry Points (12 tasks)

| Task ID | Description | Priority | Effort |
|---------|-------------|----------|--------|
| W5-001 | Create constitutions/AGENTS.md (500-1000 lines, single source of truth) | 🔴 BLOCKER | 4h |
| W5-002 | Create START_NEW_SESSION.md | 🔴 BLOCKER | 2h |
| W5-003 | Create START_RESUME_SESSION.md | 🔴 BLOCKER | 1h |
| W5-004 | Create START_VALIDATE_SESSION.md | CRITICAL | 1h |
| W5-005 | Inject constitutional principles into CLAUDE.md template | CRITICAL | 2h |
| W5-006 | Remove all "wilson-*" hardcoded zenRoles (30+ occurrences) | CRITICAL | 2h |
| W5-007 | Update all CLI references (.agents/scripts/ → edison) | HIGH | 2h |
| W5-008 | Document ConfigManager overlay mechanism | HIGH | 2h |
| W5-009 | Create project overlay template for zenRole mapping | HIGH | 2h |
| W5-010 | Add Error Recovery section to CLAUDE.md | HIGH | 1h |
| W5-011 | Document state machine explicitly in START prompts | MEDIUM | 1h |
| W5-012 | Extract hardcoded paths to config variables | MEDIUM | 1h |

---

## 13. Priority-Based Task Lists (From Section 10)

### 13.1 P1 - CRITICAL Tasks (7 tasks, ~9 hours)

| Task ID | Task | Files Affected | Est. Hours |
|---------|------|----------------|------------|
| P1-001 | Restore EPHEMERAL_SUMMARIES_POLICY.md | `.edison/core/guidelines/shared/` | 1 |
| P1-002 | Remove pack section duplication in validators | `codex-global.md`, `claude-global.md` | 2 |
| P1-003 | Restore MANDATORY WORKFLOW references in all agents | 6 agent files | 1 |
| P1-004 | Restore Context7 MCP explicit examples | All agents + global validators | 2 |
| P1-005 | Fix broken config/defaults.yaml duplicate keys | `.edison/core/config/defaults.yaml` | 0.5 |
| P1-006 | Delete duplicate codex-core.md | `.edison/core/validators/global/` | 0.5 |
| P1-007 | Restore SESSION_WORKFLOW extended guide | `.edison/core/guides/extended/` | 2 |

### 13.2 P2 - HIGH Tasks (10 tasks, ~17 hours)

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

### 13.3 P3 - MEDIUM Tasks (8 tasks, ~5 hours)

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

### 13.4 P4 - ENHANCEMENT Tasks (10 tasks, ~24 hours)

| Task ID | Task | Description | Est. Hours |
|---------|------|-------------|------------|
| P4-001 | Create constitution system | `_generated/constitutions/*.md` | 4 |
| P4-002 | Add `applies_to` field to rules | Rule registry enhancement | 2 |
| P4-003 | Extract duplicated agent sections | Move to shared guidelines | 3 |
| P4-004 | Restore validator config richness | Priority, blocking, triggers | 2 |
| P4-005 | Restore delegation config richness | Model profiles, defaults | 2 |
| P4-006 | Implement dynamic roster generation | Composition system update | 4 |
| P4-007 | Create AVAILABLE_AGENTS.md generator | New generator | 2 |
| P4-008 | Create AVAILABLE_VALIDATORS.md generator | New generator | 2 |
| P4-009 | Add mandatory reads config | `constitution.yaml` | 1 |
| P4-010 | Embed rules in constitutions | Template enhancement | 2 |

---

## 14. Re-Analysis Tasks (From Section 11.7)

### 14.1 P0 - IMMEDIATE (4 tasks, 5 hours)

| Task ID | Description | Effort |
|---------|-------------|--------|
| RE-001 | Fix pack duplication bug in composition engine | 2h |
| RE-002 | Add zenRole to all 6 agent frontmatter | 1h |
| RE-003 | Create missing SESSION_WORKFLOW.md extended guide | 1h |
| RE-004 | Create missing IMPLEMENTER_WORKFLOW.md | 1h |

### 14.2 P1 - HIGH (9 tasks, 11 hours)

| Task ID | Description | Effort |
|---------|-------------|--------|
| RE-005 | Add version table generation to composition | 2h |
| RE-006 | Restore Context7 tool call examples (4 calls) | 1h |
| RE-007 | Add pack context to security.md | 1h |
| RE-008 | Add pack context to performance.md | 1h |
| RE-009 | Fix 6 broken cross-references (naming mismatch) | 1h |
| RE-010 | Resolve 8 unresolved placeholders | 1h |
| RE-011 | Restore CONFIGURATION AUTHORITY to 3 agents | 1h |
| RE-012 | Add missing file patterns to delegation (6 patterns) | 1h |
| RE-013 | Add missing task types to delegation (6 types) | 1h |

### 14.3 P2 - MEDIUM (9 tasks, 11 hours)

| Task ID | Description | Effort |
|---------|-------------|--------|
| RE-014 | Migrate AUTH_TESTING_GUIDE.md content | 2h |
| RE-015 | Add context7_ids frontmatter to all agents | 1h |
| RE-016 | Add allowed_tools frontmatter to all agents | 1h |
| RE-017 | Add requires_validation frontmatter to all agents | 1h |
| RE-018 | Restore Tailwind v4 detailed rules to component-builder | 1h |
| RE-019 | Restore Motion 12 patterns to component-builder | 1h |
| RE-020 | Restore Prisma schema examples to database-architect | 1h |
| RE-021 | Add manifest preload equivalent to CLAUDE.md | 1h |
| RE-022 | Add task split guidance to orchestrator docs | 1h |

### 14.4 P3 - CONSTITUTION SYSTEM (13 tasks, 18.5 hours)

| Task ID | Description | Effort |
|---------|-------------|--------|
| RE-023 | Create constitution.yaml with role-based reads | 3h |
| RE-024 | Add 'applies_to' field to rules registry schema | 2h |
| RE-025 | Add get_rules_for_role() to RulesEngine | 2h |
| RE-026 | Generate _generated/AVAILABLE_AGENTS.md from registry | 1h |
| RE-027 | Generate _generated/AVAILABLE_VALIDATORS.md from registry | 1h |
| RE-028 | Create constitution.schema.json | 1h |
| RE-029 | Move mandatory guidelines from hardcoded to config | 1h |
| RE-030 | Generate constitutions/ORCHESTRATORS.md (replaces ORCHESTRATOR_GUIDE.md) | 2h |
| RE-031 | Generate constitutions/AGENTS.md | 1h |
| RE-032 | Generate constitutions/VALIDATORS.md | 1h |
| RE-034 | Update compose --orchestrator to generate constitutions/ folder | 2h |
| RE-035 | Deprecate/delete ORCHESTRATOR_GUIDE.md | 0.5h |

---

## 15. Task Cross-Reference Matrix

### Issue ID → Wave Task Mapping

| Issue ID | Related Wave Tasks | Priority |
|----------|-------------------|----------|
| B-001 (Zen prompts wrong) | W1-003, RE-001 | BLOCKER |
| B-002 (Post-training missing) | W4-001 | BLOCKER |
| B-003 (Pack duplication) | P1-002, RE-001 | BLOCKER |
| B-004 (Hardcoded paths) | W4-003 | BLOCKER |
| B-005 (YAML frontmatter) | W1-001, RE-002, P2-001 | BLOCKER |
| B-006 (constitutions/AGENTS.md) | W5-001, RE-031, P4-001 | BLOCKER |
| B-007 (START_NEW_SESSION.md) | W5-002 | BLOCKER |
| C-003 (wilson-* zenRoles) | W5-006 | CRITICAL |
| C-004 (TDD content loss) | W3-002, W3-003, P2-005 | CRITICAL |
| C-005 (Hardcoded "9 validators") | W3-001 | CRITICAL |
| C-006 (QUALITY content loss) | W3-009, W3-010, W3-011 | CRITICAL |
| C-008 (Context7 examples) | W1-002, RE-006, P1-004 | CRITICAL |
| C-009 (Broken references) | RE-009 | CRITICAL |
| C-010 (Unresolved placeholders) | RE-010, P2-009 | CRITICAL |

---

## 16. Total Task Count Summary

| Category | Task Count | Est. Hours |
|----------|------------|------------|
| Wave 1 (Agents) | 14 | 17.5h |
| Wave 2 (Delegation) | 7 | 9h |
| Wave 3 (Guidelines) | 14 | 18h |
| Wave 4 (Rules/Validators) | 13 | 26h |
| Wave 5 (Entry Points) | 12 | 21h |
| P1-P4 Tasks | 35 | 55h |
| RE-* Tasks | 35 | 45.5h |
| ZEN-* Tasks | 7 | 8h |
| **TOTAL (Deduplicated)** | **~95 unique tasks** | **~120h** |

**Note:** Many tasks overlap across categories. After deduplication, approximately 95 unique implementation tasks remain.

---

*Plan Generated: 2025-11-26 (UPDATED)*
*Sources: 3 independent AI analyses*
*- Claude Opus (Comprehensive Analysis)*
*- Codex CLI via edison-zen MCP (Pragmatic 22-Issue Registry)*
*- Gemini CLI via edison-zen MCP (Three Sins Framework + Literate Configuration)*
*Total Tasks: ~95 unique (from 52 issues + 7 Zen + detailed wave tasks)*
*Multi-Model Validation: UNANIMOUS on core issues*
*Policy: ⚠️ IMPLEMENT EVERYTHING - No deferrals*
