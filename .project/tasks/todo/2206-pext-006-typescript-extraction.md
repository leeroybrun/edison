<!-- TaskID: 2206-pext-006-typescript-extraction -->
<!-- Priority: 2206 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: refactor -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave3 -->
<!-- EstimatedHours: 0.5 -->
<!-- DependsOn: Wave 1 -->

# PEXT-006: Extract Wilson Content from TypeScript Pack

## Summary
Extract Wilson-specific content from the Edison typescript pack.

## Problem Statement
The typescript pack may contain Wilson-specific type examples or path aliases.

## Objectives
- [x] Audit for Wilson content
- [x] Move project-specific to overlays
- [x] Keep generic TypeScript patterns

## Source Files

### Pack Location
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/typescript/
```

## Precise Instructions

### Step 1: Audit Pack
```bash
cd /Users/leeroy/Documents/Development/edison/src/edison/packs/typescript
grep -rn "wilson\|Lead\|Source\|@wilson\|@/lib" . --include="*.md"
```

### Step 2: Content Categories

**Keep in Pack:**
- Strict mode configuration
- Type safety patterns
- Advanced types
- Generic patterns
- Utility types

**Move to Wilson Overlay:**
- Wilson type examples (Lead, Source)
- Wilson path aliases (@wilson/*)

### Step 3: Create Wilson Overlay (if needed)
```markdown
# Wilson TypeScript Overlay

## Path Aliases
- `@wilson/api-core` - API business logic
- `@wilson/db` - Database client

## Core Types
- Lead, Source, LeadStatus
- DashboardUser
```

## Verification Checklist
- [ ] Audit complete
- [ ] Wilson types moved if present
- [ ] Pack contains generic TypeScript patterns

## Success Criteria
TypeScript pack is project-agnostic.
