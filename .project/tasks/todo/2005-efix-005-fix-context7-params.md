<!-- TaskID: 2005-efix-005-fix-context7-params -->
<!-- Priority: 2005 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: bugfix -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave1-groupA -->
<!-- EstimatedHours: 2 -->

# EFIX-005: Fix Context7 MCP Parameter Documentation

## Summary
All Edison documentation incorrectly references Context7 MCP parameters that don't exist (`tokens`, `topics:` array) while missing the actual parameters (`topic:` string, `mode`, `page`).

## Problem Statement
Current documentation says:
```markdown
mcp__context7__get-library-docs(
  context7CompatibleLibraryID: "/vercel/next.js",
  topics: ["routing", "caching"],  // WRONG - parameter is 'topic' (singular, string)
  tokens: 5000                      // WRONG - parameter doesn't exist
)
```

Actual MCP interface:
```typescript
mcp__context7__get-library-docs(
  context7CompatibleLibraryID: string,  // Required
  topic?: string,                        // Optional - singular, not array
  mode?: "code" | "info",               // Optional - default "code"
  page?: number                          // Optional - for pagination
)
```

Also referenced but DON'T EXIST:
- `mcp__context7__search-docs()` - NOT a real tool
- `mcp__context7__get-latest-version()` - NOT a real tool

## Dependencies
- None - documentation fix only

## Objectives
- [x] Find all files with incorrect Context7 references
- [x] Fix `topics:` array → `topic:` string
- [x] Remove `tokens` parameter references
- [x] Remove references to non-existent tools
- [x] Add correct parameters: `mode`, `page`
- [x] Update all examples

## Files to Search and Fix

### Search Command
```bash
cd /Users/leeroy/Documents/Development/edison
grep -rn "topics:" src/edison/data/ --include="*.md" | grep -i context7
grep -rn "tokens:" src/edison/data/ --include="*.md" | grep -i context7
grep -rn "search-docs" src/edison/data/ --include="*.md"
grep -rn "get-latest-version" src/edison/data/ --include="*.md"
```

### Known Files to Check
```
src/edison/data/guidelines/shared/CONTEXT7.md
src/edison/data/guidelines/agents/CONTEXT7_REQUIREMENT.md
src/edison/data/agents/*.md (all agent files)
```

## Precise Instructions

### Step 1: Search for All Incorrect References
```bash
cd /Users/leeroy/Documents/Development/edison

echo "=== Files with 'topics:' (wrong) ==="
grep -rln "topics:" src/edison/data/ --include="*.md"

echo "=== Files with 'tokens:' (wrong) ==="
grep -rln "tokens:" src/edison/data/ --include="*.md" | xargs grep -l context7 2>/dev/null

echo "=== Files referencing non-existent tools ==="
grep -rln "search-docs\|get-latest-version" src/edison/data/ --include="*.md"
```

### Step 2: Understand Correct Interface

The ONLY valid Context7 MCP tools are:
1. `mcp__context7__resolve-library-id(libraryName: string)` - Resolves package name to ID
2. `mcp__context7__get-library-docs(...)` - Gets documentation

Correct parameters for `get-library-docs`:
```typescript
{
  context7CompatibleLibraryID: string,  // Required, e.g., "/vercel/next.js"
  topic?: string,                        // Optional, e.g., "routing"
  mode?: "code" | "info",               // Optional, default "code"
  page?: number                          // Optional, 1-10, for pagination
}
```

### Step 3: Fix Each File

For each file found:

**Replace incorrect examples:**
```markdown
// BEFORE (wrong):
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/vercel/next.js",
  topics: ["routing", "caching"],
  tokens: 5000
})

// AFTER (correct):
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/vercel/next.js",
  topic: "routing",
  mode: "code"
})
```

**Remove non-existent tool references:**
```markdown
// REMOVE any mentions of:
- mcp__context7__search-docs()
- mcp__context7__get-latest-version()

// REPLACE WITH explanation:
Use `mcp__context7__resolve-library-id()` to find library IDs, then
use `mcp__context7__get-library-docs()` to fetch documentation.
```

### Step 4: Update CONTEXT7.md Specifically

File: `src/edison/data/guidelines/shared/CONTEXT7.md`

Add or update the "Correct Usage" section:
```markdown
## Context7 MCP Interface

### Available Tools

1. **resolve-library-id** - Find library ID from package name
   ```
   mcp__context7__resolve-library-id({
     libraryName: "next.js"
   })
   // Returns: { libraryId: "/vercel/next.js", ... }
   ```

2. **get-library-docs** - Fetch documentation
   ```
   mcp__context7__get-library-docs({
     context7CompatibleLibraryID: "/vercel/next.js",
     topic: "routing",      // Optional - focus area
     mode: "code",          // Optional - "code" or "info"
     page: 1                // Optional - pagination (1-10)
   })
   ```

### Common Mistakes
- ❌ `topics: ["a", "b"]` - Wrong! Use `topic: "a"` (singular string)
- ❌ `tokens: 5000` - Wrong! This parameter doesn't exist
- ❌ `search-docs()` - Wrong! This tool doesn't exist
```

### Step 5: Verify All Fixes
```bash
# Should return NO matches after fixes:
grep -rn "topics:" src/edison/data/ --include="*.md" | grep -i context7
grep -rn "search-docs\|get-latest-version" src/edison/data/ --include="*.md"

# Tokens might be used elsewhere legitimately, check context:
grep -rn "tokens:" src/edison/data/ --include="*.md"
```

## Verification Checklist
- [ ] No files contain `topics:` array for Context7 (should be `topic:`)
- [ ] No files reference `tokens:` for Context7
- [ ] No files reference `search-docs` tool
- [ ] No files reference `get-latest-version` tool
- [ ] CONTEXT7.md has correct interface documentation
- [ ] Agent files use correct Context7 syntax

## Success Criteria
All Edison documentation correctly describes the Context7 MCP interface with:
- `topic:` (singular string, not array)
- `mode:` ("code" or "info")
- `page:` (pagination)
- No references to non-existent parameters or tools

## Reference: Complete Correct Interface

```typescript
// Tool 1: Resolve library name to ID
mcp__context7__resolve-library-id({
  libraryName: string  // e.g., "react", "prisma", "next.js"
}): {
  libraryId: string,   // e.g., "/facebook/react"
  matches: array       // Potential matches with scores
}

// Tool 2: Get library documentation
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: string,  // Required
  topic?: string,                        // Optional focus
  mode?: "code" | "info",               // Default "code"
  page?: number                          // 1-10, for more content
}): {
  content: string,     // Markdown documentation
  hasMore: boolean     // Whether more pages available
}
```

## Related Issues
- Audit ID: CG-006 (Context7 syntax error)
- Audit ID: Guidelines Wave 2R findings
