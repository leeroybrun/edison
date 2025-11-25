# project application - Multi-Validator Architecture

This directory contains the configuration and specifications for the project application multi-validator architecture.

## Overview

The multi-validator system provides comprehensive code quality assurance through 10 independent validators organized in 3 tiers:

- **3 Global Validators** (run on every task): Codex + Claude Code + Gemini Global
- **2 Critical Validators** (run on every task): Security + Performance
- **5 Specialized Validators** (triggered by file patterns): React, nextjs, API, Database, Testing

## Architecture

```
.edison/core/validators/
├── README.md                # This file (core template; composed with overlays)
├── validators.yaml          # Source roster (loaded via ConfigManager; overlays with packs + .agents/config/validators.yml)
├── config.schema.json       # JSON schema for IDE validation
├── global/                  # Core/global validator specs (includes gemini-global)
├── critical/                # Security + Performance specs
└── specialized/             # React, nextjs, API, Database, Testing specs
```

## Execution Flow

```
┌─────────────────────────────────────────────────┐
│ Step 1: Orchestrator detects task completion   │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│ Step 2: Context7 refresh for post-training pkgs│
│ (nextjs 16, React 19, tailwindcss 4, etc.)     │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│ Step 3: Run Global Validators (parallel up to  │
│           cap; batch overflow)                 │
│ • Codex Global (comprehensive 10-point)        │
│ • Claude Global (identical scope)              │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│ Step 4: Run Critical Validators (parallel up to│
│           cap; batch overflow)                 │
│ • Security (OWASP + Context7) – blocks on fail │
│ • Performance (bundle/query analysis) – blocks │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│ Step 5: Run Specialized Validators (parallel   │
│           up to cap; batch overflow)           │
│ • Triggered by file patterns in git diff       │
│ • React, nextjs, API, Database, Testing       │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│ Step 6: Aggregate Results & Make Decision      │
│ • MUST approve: global, critical (security,    │
│   performance), specialized (React, nextjs,   │
│   API, Database, Testing). All block on fail.  │
└─────────────────────────────────────────────────┘
```

## Configuration (validators.yaml via ConfigManager)

The master configuration file defines:

1. **Validators**: All 9 validators with models, triggers, priorities
2. **Post-Training Packages**: Cutting-edge packages needing Context7
3. **Execution Order**: Step-by-step validation workflow
4. **Approval Criteria**: Which validators block vs warn

### Example: Changing a Validator Model

Configurations are layered: `.edison/core/config/validators.yaml` → pack overlays → project `.agents/config/validators.yml`. Use `edison config print validators` (or ConfigManager API) instead of editing generated JSON. Changing models/roster is done in YAML, then recompose if needed.

## Context7 Integration

All validators MUST use Context7 MCP before validation to refresh knowledge on post-training packages:

### Critical Packages Requiring Context7

| Package | Version | Why Context7 Needed |
|---------|---------|---------------------|
| **nextjs** | 16.0.0 | Major App Router changes, new API patterns |
| **React** | 19.2.0 | New use() hook, Server Components updates |
| **tailwindcss** | 4.0.0 | COMPLETELY different syntax (caused production failure!) |
| **Zod** | 4.1.12 | Breaking changes from v3 API |
| **Motion** | 12.23.24 | API changes (formerly Framer Motion) |
| **TypeScript** | 5.7.0 | New type inference features |

### Example: Context7 Query Before Validation

```typescript
// BEFORE validating nextjs 16 code:
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: '/vercel/next.js',
  topic: 'route handlers',
  tokens: 5000
})

// THEN validate with fresh, accurate knowledge
```

## Validator Specifications

Each validator has a dedicated markdown file with:

1. **Role & Scope**: What this validator checks
2. **Context7 Integration**: Which packages/topics to query
3. **Validation Checklist**: Specific items to verify
4. **Git Diff Review**: How to check uncommitted changes
5. **Output Format**: Expected report structure
6. **Severity Levels**: Critical vs Warning vs Info

### Global Validators (codex-global.md, claude-global.md)

**Scope**: IDENTICAL comprehensive validation (10-point checklist)

1. Task completion verification (git diff vs requirements)
2. Code quality (types, naming, DRY, SOLID)
3. Security (OWASP Top 10, secrets, injection)
4. Performance (bundle size, queries, caching)
5. Error handling (validation, errors, loading states)
6. TDD compliance (tests written first, coverage, quality)
7. Architecture (patterns, separation of concerns)
8. Best practices (framework-specific, accessibility)
9. Regression testing (no unintended changes)
10. Documentation (comments, API docs, READMEs)

**Critical**: Both must approve for task to be marked complete.

### Critical Validators

**Security (security.md)**:
- OWASP Top 10 checks
- Authentication/authorization
- Input validation (Zod schemas)
- SQL injection, XSS, CSRF
- Secrets management
- **Blocks on fail**: ❌ Critical issues prevent task completion

**Performance (performance.md)**:
- Bundle size analysis
- Database query efficiency (N+1 detection)
- Caching strategies
- Memory leak detection
- **Blocks on fail**: ❌ Performance regressions must be addressed

### Specialized Validators

**React (react.md)**:
- React 19 patterns (use() hook, Server Components)
- Hooks rules (useEffect, useState, custom hooks)
- Component patterns (composition, props)
- Accessibility (ARIA, keyboard nav)
- Triggers: `*.tsx`, `*.jsx`, `components/**/*`

**nextjs (nextjs.md)**:
- nextjs 16 App Router patterns
- Route handlers (validation, error handling)
- Metadata API
- Server Actions
- Triggers: `app/**/*.tsx`, `**/route.ts`, `**/layout.tsx`, `**/page.tsx`

**API (api.md)**:
- Zod 4 validation schemas
- Error handling (try/catch, status codes)
- Authentication checks
- Response formatting
- Triggers: `**/route.ts`, `api/**/*.ts`

**Database (database.md)**:
- prisma schema design
- Migration quality
- Query optimization
- Index usage
- **Blocks on fail**: ❌ Critical for data integrity
- Triggers: `schema.prisma`, `prisma/**/*`, `migrations/**/*`

**Testing (testing.md)**:
- TDD compliance (test written first?)
- Test quality (realistic vs mocked)
- Coverage deltas
- Test patterns (describe/it structure)
- **Blocks on fail**: ❌ No code without tests
- Triggers: `**/*.test.ts`, `**/*.test.tsx`, `**/*.spec.ts`

## Approval Criteria

| Validator | Outcome | Impact |
|-----------|---------|--------|
| **Codex Global** | ❌ Fail | **BLOCKS** task completion |
| **Claude Global** | ❌ Fail | **BLOCKS** task completion |
| **Security** | ❌ Fail | **BLOCKS** task completion |
| **Performance** | ⚠️ Fail | **WARNING** (doesn't block) |
| **Database** | ❌ Fail | **BLOCKS** task completion |
| **Testing** | ❌ Fail | **BLOCKS** task completion |
| **React** | ⚠️ Fail | **ISSUES NOTED** (doesn't block) |
| **nextjs** | ⚠️ Fail | **ISSUES NOTED** (doesn't block) |
| **API** | ⚠️ Fail | **ISSUES NOTED** (doesn't block) |

**Consensus Required**: Both global validators + security must approve.

**Human Override**: If any validator blocks, orchestrator escalates to human for review.

## Performance

### Batched Parallel Execution

Validators run **in parallel up to the global cap** defined in `.agents/manifest.json.orchestration.maxConcurrentAgents`, with overflow **batched in waves** via Claude Code's multi-tool calling:

```typescript
// Single message with multiple tool calls up to the cap
const worktreePath = SessionContext.build_zen_environment(sessionId).ZEN_WORKING_DIR
mcp__edison-zen__clink({ prompt: "Codex global validation...", cli_name: 'codex', working_directory: worktreePath })
Task({ subagent_type: 'code-reviewer', prompt: "Claude global validation..." })
mcp__edison-zen__clink({ prompt: "Security validation...", cli_name: 'codex', working_directory: worktreePath })
mcp__edison-zen__clink({ prompt: "Performance validation...", cli_name: 'codex', working_directory: worktreePath })
```

**Result**: All required validators complete in ~5–10 minutes in batched waves (vs much longer strictly sequential).

### Context Preservation

Validators report back to orchestrator (not implement), keeping orchestrator context lean:

- **Before delegation**: ~60k tokens/task (orchestrator implements)
- **With delegation**: ~16k tokens/task (orchestrator coordinates)
- **Result**: **4x more tasks per session**

## Git Diff Review

**CRITICAL**: Every validator MUST review git diff to catch:

1. **Unintended deletions**: Code accidentally removed
2. **Scope creep**: Changes beyond requirements
3. **Regressions**: Breaking existing functionality
4. **Security holes**: New vulnerabilities introduced

### Example Git Diff Check

```bash
# Validator checks uncommitted changes
git diff --cached  # Staged changes
git diff           # Unstaged changes

# Questions to answer:
# 1. Do changes match task requirements?
# 2. Any unintended deletions?
# 3. Any new security vulnerabilities?
# 4. Any performance regressions?
# 5. Are tests updated for changes?
```

## Usage (Orchestrator)

### Step 1: Detect Changed Files

```typescript
const changedFiles = await bash('git diff --name-only HEAD')
const triggers = detectTriggeredValidators(changedFiles)
// Example: ['codex-global', 'claude-global', 'security', 'performance', 'nextjs', 'api']
```

### Step 2: Context7 Refresh

```typescript
// Refresh knowledge for post-training packages
for (const pkg of ['next', 'react', 'uistylescss']) {
  await mcp__context7__get-library-docs({
    context7CompatibleLibraryID: `/org/${pkg}`,
    topic: 'latest features',
    tokens: 5000
  })
}
```

### Step 3: Run Global Validators (Parallel up to cap)

```typescript
// BOTH global validators run in parallel up to the cap
const worktreePath = SessionContext.build_zen_environment(sessionId).ZEN_WORKING_DIR
const [codexGlobal, claudeGlobal] = await Promise.all([
  mcp__edison-zen__clink({
    prompt: readFile('validators/global/codex-global.md') + gitDiff,
    cli_name: 'codex',
    role: 'codereviewer',
    working_directory: worktreePath,
    absolute_file_paths: changedFiles
  }),
  Task({
    subagent_type: 'code-reviewer',
    prompt: readFile('validators/global/claude-global.md') + gitDiff
  })
])

// Check: Both must approve
if (codexGlobal.status !== 'APPROVED' || claudeGlobal.status !== 'APPROVED') {
  escalateToHuman()
}
```

### Step 4: Run Critical Validators (Parallel up to cap)

```typescript
const [security, performance] = await Promise.all([
  mcp__edison-zen__clink({
    prompt: readFile('validators/critical/security.md') + gitDiff,
    cli_name: 'codex',
    role: 'codereviewer',
    working_directory: worktreePath,
    absolute_file_paths: changedFiles
  }),
  mcp__edison-zen__clink({
    prompt: readFile('validators/critical/performance.md') + gitDiff,
    cli_name: 'codex',
    role: 'codereviewer',
    working_directory: worktreePath,
    absolute_file_paths: changedFiles
  })
])

// Check: Security must approve, performance must approve (both block on fail)
if (security.status !== 'APPROVED') {
  escalateToHuman()
}
if (performance.status !== 'APPROVED') {
  logWarning('Performance issues detected')
}
```

### Step 5: Run Specialized Validators (Parallel up to cap)

```typescript
// Only run validators triggered by changed files
const specializedResults = await Promise.all(
  triggers.specialized.map(validator =>
    mcp__edison-zen__clink({
      prompt: readFile(`validators/specialized/${validator}.md`) + gitDiff,
      cli_name: validator.model,
      role: 'codereviewer',
      working_directory: worktreePath,
      absolute_file_paths: changedFiles.filter(f => matchesTrigger(f, validator.triggers))
    })
  )
)

// Check: Database and Testing block, others warn
for (const result of specializedResults) {
  if (result.validator === 'database' || result.validator === 'testing') {
    if (result.status !== 'APPROVED') {
      escalateToHuman()
    }
  } else {
    if (result.status !== 'APPROVED') {
      logWarning(`${result.validator} issues detected`)
    }
  }
}
```

### Step 6: Aggregate & Decide

```typescript
const decision = {
  approved: allBlockingValidatorsApproved(),
  warnings: collectWarnings(),
  evidence: collectEvidence(),
  recommendation: generateRecommendation()
}

if (decision.approved) {
  markTaskComplete()
  updateCheckpoint()
} else {
  escalateToHuman(decision)
}
```

## Adding a New Validator

1. **Update validators.yaml (via ConfigManager overlays)**: Add validator definition
2. **Create spec file**: `validators/{tier}/{name}.md`
3. **Define checklist**: What to validate
4. **Add Context7**: Which packages to query
5. **Set approval**: MUST approve or SHOULD approve?
6. **Test**: Run on sample changes

Example:

```json
{
  "id": "graphql",
  "name": "GraphQL Validator",
  "model": "codex",
  "interface": "clink",
  "role": "codereviewer",
  "specFile": "specialized/graphql.md",
  "triggers": ["**/*.graphql", "graphql/**/*.ts"],
  "alwaysRun": false,
  "priority": 3,
  "context7Required": true,
  "context7Packages": ["graphql", "apollo"],
  "focus": ["schema-design", "resolvers", "queries"],
  "blocksOnFail": false,
  "outputFormat": "GraphQLReport"
}
```

## Troubleshooting

### Issue: Validator Returns Incorrect Results

**Cause**: Outdated knowledge (post-training package)

**Solution**: Ensure Context7 refresh before validation

```typescript
// BEFORE validation:
await mcp__context7__get-library-docs({
  context7CompatibleLibraryID: '/vercel/next.js',
  topic: 'route handlers',
  tokens: 5000
})
```

### Issue: Validation Too Slow

**Cause**: Underutilized concurrency cap or unnecessary serialization

**Solution**: Use batched parallel waves up to the cap

```typescript
// ❌ WRONG - Strictly sequential (slow)
const codex = await mcp__edison-zen__clink({ ..., working_directory: SessionContext.build_zen_environment(sessionId).ZEN_WORKING_DIR })
const claude = await Task({...})

// ✅ CORRECT - Batched parallel (fast)
// Single message with both calls (and more up to the cap)
mcp__edison-zen__clink({ ..., working_directory: SessionContext.build_zen_environment(sessionId).ZEN_WORKING_DIR })
Task({...})
```

### Issue: Conflicting Validator Results

**Cause**: Different validators have different knowledge

**Solution**: Ensure all validators use Context7 for same packages

### Issue: Validator Misses Issues

**Cause**: Git diff not included in validation prompt

**Solution**: Always append git diff to validator prompt

```typescript
const gitDiff = await bash('git diff HEAD')
const prompt = readFile('validator.md') + '\n\n## Git Diff\n' + gitDiff
```

## References

- **Orchestration Guide**: `/docs/project/ORCHESTRATION_GUIDE.md`
- **Main Orchestrator**: `/.agents/AGENTS.md`
- **Sub-Agents**: `/.agents/agents/*.md`
- **Context7 MCP**: https://context7.io

## Version History

- **v1.0.0** (2025-10-29): Initial multi-validator architecture
  - 9 validators (2 global + 2 critical + 5 specialized)
  - Context7 integration for post-training packages
  - Batched parallel execution support
  - Git diff review mandatory

## Edison validation guards (current)
- Validate only against bundles emitted by `edison validators bundle <root-task>`; block/return `BLOCKED` if the manifest or parent `bundle-approved.json` is missing.
- Load roster, triggers, and blocking flags via ConfigManager overlays (`.edison/core/config/validators.yaml` → pack overlays → `.agents/config/validators.yml`) instead of JSON.
- `edison qa promote` now enforces state machine rules plus bundle presence; ensure your Markdown + JSON report lives in the round evidence directory referenced by the bundle.
- Honor Context7 requirements: auto-detected post-training packages must have markers (HMAC when enabled) before issuing approval.
