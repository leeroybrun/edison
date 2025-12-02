# Context7 MCP Server Requirement (MANDATORY)

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Generated from pre-Edison agent content extraction -->

## Purpose

This guideline explains how to use Context7 as a pattern for querying up-to-date framework documentation. Context7 is critical when working with frameworks that may have been updated after your training data cutoff.

## Requirements

### Why Context7 is Critical

**Training data limitations**:
- AI training data has a cutoff date (e.g., January 2025)
- Frameworks and libraries evolve continuously after this cutoff
- Major version changes introduce breaking changes and new patterns
- Relying on outdated training data leads to deprecated implementations

**Which frameworks need Context7?**
Active packs define which frameworks require Context7 refresh. Check `.edison/_generated/constitutions/ORCHESTRATORS.md` for:
- Active packs and their framework dependencies
- Pack versions and framework versions
- Breaking changes indicators

**NEVER rely on training data** for frameworks specified in active packs. Always query Context7 first.

### The Context7 Workflow Pattern

**BEFORE implementing ANYTHING**, follow this workflow:

#### Step 1: Identify Framework from Active Packs
```pseudocode
// Check .edison/_generated/constitutions/ORCHESTRATORS.md for active packs
// Example: if 'web-framework' pack is active, identify its main framework
framework_name = get_framework_from_active_pack()
```

#### Step 2: Resolve Library ID
```pseudocode
// Use Context7 MCP to resolve the framework name to a Context7-compatible ID
library_id = mcp__context7__resolve_library_id({
  libraryName: framework_name  // e.g., framework from pack
})
// Returns: Context7-compatible ID (e.g., '/org/project' or '/org/project/version')
```

#### Step 3: Query Documentation
```pseudocode
// Query for specific implementation patterns
documentation = mcp__context7__get_library_docs({
  context7CompatibleLibraryID: library_id,
  topic: 'your_specific_topic',  // Be specific to your implementation need
  mode: 'code',  // 'code' for API refs/examples, 'info' for conceptual guides
  page: 1  // Optional pagination (1-10)
})
// Returns: Current documentation and examples
```

#### Step 4: Implement Using Current Patterns
```pseudocode
// Use patterns from Context7 docs, not training data memory
// Implement based on queried documentation
// Document which queries informed your implementation
```

### Query Topics by Agent Type

#### Pattern: API Implementation Agent
```pseudocode
// Before implementing API routes/endpoints
library_id = resolve_framework_from_pack('api')
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: library_id,
  topic: 'API route handler request validation patterns',
  mode: 'code'
})

// For validation frameworks specified in active packs
validation_lib = resolve_framework_from_pack('validation')
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: validation_lib,
  topic: 'schema validation and transformation',
  mode: 'code'
})
```

#### Pattern: Component Implementation Agent
```pseudocode
// Before implementing UI components
ui_framework = resolve_framework_from_pack('ui')
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: ui_framework,
  topic: 'component architecture best practices',
  mode: 'code'
})

// For styling frameworks in active packs
styling_lib = resolve_framework_from_pack('styling')
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: styling_lib,
  topic: 'current syntax and configuration',
  mode: 'code'
})

// For animation frameworks if present
animation_lib = resolve_framework_from_pack('animation')
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: animation_lib,
  topic: 'animation patterns',
  mode: 'code'
})
```

#### Pattern: Database Implementation Agent
```pseudocode
// Before implementing database schemas
orm_framework = resolve_framework_from_pack('orm')
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: orm_framework,
  topic: 'schema design and relationships',
  mode: 'code'
})

// For migrations
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: orm_framework,
  topic: 'migration workflows',
  mode: 'code'
})
```

#### Pattern: Test Implementation Agent
```pseudocode
// Before implementing tests
test_framework = resolve_framework_from_pack('testing')
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: test_framework,
  topic: 'testing patterns for [component/route/schema]',
  mode: 'code'
})

// For testing libraries specific to UI frameworks
testing_lib = resolve_framework_from_pack('ui-testing')
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: testing_lib,
  topic: 'async user interaction testing',
  mode: 'code'
})
```

#### Pattern: Code Review Agent
```pseudocode
// BEFORE flagging ANY code as wrong, query Context7
framework = identify_framework_from_file_path()
await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: framework,
  topic: '[pattern being reviewed]',
  mode: 'code'
})

// Read current documentation
// THEN provide feedback based on CURRENT standards
// NEVER flag code as wrong based solely on training data!
```

### How to Find Library IDs

**NEVER hardcode library IDs in this guideline.**

Instead, follow this pattern:
1. Check `.edison/_generated/constitutions/ORCHESTRATORS.md` for active packs
2. Identify framework name from pack metadata
3. Use `mcp__context7__resolve_library_id({ libraryName: 'framework-name' })`
4. Context7 returns the correct library ID (format: `/org/project` or `/org/project/version`)

### Breaking Changes Warning

Frameworks often introduce breaking changes between major versions. Common patterns:
- **Syntax changes**: Import statements, configuration files, decorator patterns
- **API changes**: Method signatures, function names, module exports
- **Architecture changes**: Component models, rendering strategies, data flow patterns
- **Configuration changes**: File formats, build tools, plugin systems

**ALWAYS query Context7 for frameworks with major version bumps in active packs**.

### Error Prevention Pattern

**Without Context7**:
```pseudocode
// ❌ Using training data patterns (potentially outdated)
implement_feature_using_memory()
// Risk: Using deprecated patterns, wrong imports, outdated APIs
```

**With Context7**:
```pseudocode
// ✅ Using queried current documentation
framework = resolve_framework_from_pack()
docs = query_context7(framework, topic)
implement_feature_using_current_docs(docs)
// Benefit: Using current patterns, correct imports, latest APIs
```

## Evidence Required

When providing implementation, document Context7 queries:

```markdown
### Context7 Queries

1. **[Framework Name] [Topic]**: Queried `[library-id]` for "[specific topic]"
   - Key finding: [Pattern learned from documentation]
   - Applied to: [Files where pattern was used]

2. **[Framework Name] [Topic]**: Queried `[library-id]` for "[specific topic]"
   - Key finding: [Pattern learned from documentation]
   - Applied to: [Files where pattern was used]
```

**Template**:
- Framework name from active pack
- Library ID resolved via Context7
- Specific topic queried
- Key findings that informed implementation
- Where findings were applied

## MCP Tool Interface

Context7 is accessed via MCP tools (not CLI commands):

```pseudocode
// Step 1: Resolve library ID from framework name
library_id = mcp__context7__resolve_library_id({
  libraryName: framework_name_from_pack
})

// Step 2: Query documentation for specific topic
documentation = mcp__context7__get_library_docs({
  context7CompatibleLibraryID: library_id,
  topic: specific_implementation_topic,
  mode: 'code',  // or 'info' for conceptual guides
  page: 1  // optional pagination (1-10)
})
```

**Key Points**:
- These are MCP function calls, not bash/shell commands
- Framework names come from `.edison/_generated/constitutions/ORCHESTRATORS.md`
- Topics should be specific to implementation needs
- Use `mode: 'code'` for API references and examples, `mode: 'info'` for conceptual guides
- Optional `page` parameter for pagination (default: 1, max: 10)

## References

- Context7 usage guide: `.edison/_generated/guidelines/CONTEXT7.md`
- Extended patterns: `.edison/_generated/guidelines/shared/CONTEXT7.md`
- Tech stack reference: `.edison/_generated/guidelines/TECH_STACK.md`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL agents (implementing and reviewing)
**Critical Warning**: Training data is outdated - ALWAYS query Context7 first!
