<!-- TaskID: 2301-worg-001-tdd-to-vitest -->
<!-- Priority: 2301 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: refactor -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave4 -->
<!-- EstimatedHours: 3 -->
<!-- DependsOn: Wave 3 -->

# WORG-001: Move TDD Testing Patterns to Vitest Pack

## Summary
Move technology-generic TDD testing patterns from Wilson overlays to the Edison vitest pack. These patterns apply to any Vitest project, not just Wilson.

## Problem Statement
Wilson overlays contain TDD patterns that are NOT Wilson-specific:
- Pattern 1/2/3 test strategies
- TDD markers and evidence requirements
- Mock guidelines
- Integration test patterns

These should be in the vitest pack for all projects to use.

## Objectives
- [x] Identify tech-generic TDD content in Wilson overlays
- [x] Move to Edison vitest pack
- [x] Keep Wilson-specific test setup in overlays
- [x] Verify composition works

## Source Files

### Wilson Overlays to Audit
```
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays/
```

### Vitest Pack Destination
```
/Users/leeroy/Documents/Development/edison/src/edison/packs/vitest/guidelines/
```

## Precise Instructions

### Step 1: Audit Wilson Overlays
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen/.edison/overlays
find . -name "*.md" -exec grep -l -i "tdd\|pattern-1\|pattern-2\|test.*first" {} \;
```

### Step 2: Categorize Content

**Move to Vitest Pack (tech-generic):**
- TDD red-green-refactor workflow
- Pattern 1: Simple function testing
- Pattern 2: API route integration testing
- Pattern 3: Complex service testing
- Mock usage guidelines
- Coverage requirements (generic percentages)
- Test organization patterns

**Keep in Wilson Overlays (project-specific):**
- Wilson test database connection
- Wilson-specific fixture generators
- Wilson test commands (`pnpm --filter dashboard`)
- Wilson auth testing helpers

### Step 3: Update Vitest Pack

Add to `edison/src/edison/packs/vitest/guidelines/tdd-workflow.md`:

```markdown
# TDD Workflow

## Red-Green-Refactor Cycle

1. **RED**: Write failing test first
   - Test describes expected behavior
   - Test MUST fail initially
   - Commit test in failing state (TDD evidence)

2. **GREEN**: Minimal implementation
   - Write just enough code to pass
   - No optimization yet
   - Commit passing test + implementation

3. **REFACTOR**: Clean up
   - Improve code quality
   - Maintain passing tests
   - Commit refactored code

## Testing Patterns

### Pattern 1: Unit Tests (Simple Functions)
Use for: Pure functions, utilities, validators

```typescript
describe('calculateTotal', () => {
  it('should return sum of items', () => {
    // Arrange
    const items = [{ price: 10 }, { price: 20 }];

    // Act
    const result = calculateTotal(items);

    // Assert
    expect(result).toBe(30);
  });
});
```

### Pattern 2: Integration Tests (API/Services)
Use for: API routes, services with dependencies

```typescript
describe('POST /api/resource', () => {
  beforeEach(async () => {
    await setupTestDatabase();
  });

  it('should create resource and return 201', async () => {
    const response = await request(app)
      .post('/api/resource')
      .send({ name: 'Test' });

    expect(response.status).toBe(201);
    expect(response.body.data.name).toBe('Test');
  });
});
```

### Pattern 3: Complex Services
Use for: Multi-step operations, orchestration

- Test each step independently
- Mock external services
- Verify state transitions

## Mock Guidelines

### When to Mock
- External APIs (HTTP calls)
- Time-dependent operations
- File system operations
- Random/UUID generation

### When NOT to Mock
- The code under test
- Database in integration tests
- Pure functions
- Internal module functions

## Coverage Requirements
- New code: 90% minimum
- Modified files: No decrease
- Critical paths: 100%
```

### Step 4: Remove from Wilson Overlays

After moving content to pack, update Wilson overlays to ONLY contain:

```markdown
# Wilson Testing Overlay

## Test Database
- Connection: postgresql://wilson_test:...@localhost:5434/wilson_test
- Setup: `scripts/test-db-setup.sh`

## Commands
- Unit tests: `pnpm --filter dashboard test`
- API tests: `pnpm --filter api test`
- Coverage: `pnpm test:coverage`

## Fixtures
See `__fixtures__/` directories in each package.
```

### Step 5: Verify Composition
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose all
grep -r "Pattern 1" .edison/_generated/
```

## Verification Checklist
- [ ] TDD patterns moved to vitest pack
- [ ] Pattern 1/2/3 in pack, not Wilson overlays
- [ ] Wilson overlays only have project-specific test config
- [ ] Composition includes TDD patterns from pack
- [ ] Other projects can use these TDD patterns

## Success Criteria
Any project using the vitest pack gets TDD patterns automatically, without needing Wilson-specific overlays.

## Related Issues
- Content Placement Audit: Wilson overlays 60% misplaced
