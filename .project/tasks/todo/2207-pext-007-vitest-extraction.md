<!-- TaskID: 2207-pext-007-vitest-extraction -->
<!-- Priority: 2207 -->
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
<!-- EstimatedHours: 1 -->
<!-- DependsOn: Wave 1 -->

# PEXT-007: Extract Wilson Content from Vitest Pack

## Summary
Extract Wilson-specific content from the Edison vitest pack and move it to Wilson project overlays.

## Problem Statement
The vitest pack may contain Wilson-specific testing patterns:
- Wilson test database setup
- Wilson-specific test helpers
- Pattern 1/2 with Wilson context

## Objectives
- [x] Audit for Wilson content
- [x] Move project-specific to overlays
- [x] Keep generic testing patterns

## Source Files

### Pack Location
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/vitest/
```

## Precise Instructions

### Step 1: Audit Pack
```bash
cd /Users/leeroy/Documents/Development/edison/src/edison/packs/vitest
grep -rn "wilson\|Lead\|dashboard\|apps/\|pnpm --filter" . --include="*.md"
```

### Step 2: Content Categories

**Keep in Pack (generic Vitest):**
- Vitest configuration
- Mock patterns
- Test organization
- Coverage configuration
- TDD workflow (generic)
- Pattern 1/2/3 concepts

**Move to Wilson Overlay:**
- Wilson test database setup
- `pnpm --filter dashboard test`
- Wilson-specific test helpers
- Lead/Source test fixtures

### Step 3: Create Wilson Overlay
```markdown
# Wilson Vitest Overlay

## Test Commands
- Unit: `pnpm --filter dashboard test`
- API: `pnpm --filter api test`

## Test Database
- Test DB: wilson_test on port 5434
- Setup: `scripts/test-db-setup.sh`

## Fixtures
- Lead fixtures in `__fixtures__/leads.ts`
- Source fixtures in `__fixtures__/sources.ts`
```

## Verification Checklist
- [ ] Audit complete
- [ ] Wilson test patterns moved
- [ ] Pack contains generic Vitest patterns
- [ ] TDD workflow is project-agnostic

## Success Criteria
Vitest pack works for any Vitest project, not just Wilson.
