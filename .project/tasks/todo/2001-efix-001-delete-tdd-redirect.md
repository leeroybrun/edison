<!-- TaskID: 2001-efix-001-delete-tdd-redirect -->
<!-- Priority: 2001 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: bugfix -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: codex -->
<!-- ParallelGroup: wave1-groupA -->
<!-- EstimatedHours: 0.5 -->

# EFIX-001: Delete TDD.md Redirect File

## Summary
Delete the legacy 9-line TDD.md redirect file in Edison core that shadows the canonical 296-line TDD.md in the shared/ subdirectory.

## Problem Statement
The Edison core has TWO TDD.md files:
1. `/src/edison/data/guidelines/TDD.md` (9 lines) - A redirect stub that says "See ./shared/TDD.md"
2. `/src/edison/data/guidelines/shared/TDD.md` (296 lines) - The canonical, complete TDD guide

The `GuidelineRegistry.core_path()` method uses `rglob(f"{name}.md")` which finds BOTH files, and after sorting, returns the FIRST match (root wins over nested). This causes the 9-line redirect to be used instead of the canonical 296-line file.

## Root Cause Analysis
```python
# In registries/guidelines.py:
def core_path(self, name: str) -> Path:
    matches = list(self.core_dir.rglob(f"{name}.md"))
    return sorted(matches)[0]  # Root TDD.md sorts before shared/TDD.md
```

## Dependencies
- None - this is a standalone fix

## Objectives
- [x] Verify the redirect file exists and contains redirect text
- [x] Verify the canonical file exists and contains full content
- [x] Delete the redirect file
- [x] Verify GuidelineRegistry now finds the canonical file
- [x] Run edison compose to verify output

## Source Files to Verify
```
/Users/leeroy/Documents/Development/edison/src/edison/data/guidelines/TDD.md
```
Expected content (9 lines, redirect):
```markdown
# TDD Guidelines

See ./shared/TDD.md for the complete TDD guidelines.
```

```
/Users/leeroy/Documents/Development/edison/src/edison/data/guidelines/shared/TDD.md
```
Expected: 296 lines, complete TDD guide with sections for TDD methodology, patterns, verification checklist.

## Precise Instructions

### Step 1: Verify Files Exist
```bash
cd /Users/leeroy/Documents/Development/edison
wc -l src/edison/data/guidelines/TDD.md
# Expected: 9 (or similar small number)

wc -l src/edison/data/guidelines/shared/TDD.md
# Expected: ~296 lines
```

### Step 2: Verify Redirect Content
```bash
cat src/edison/data/guidelines/TDD.md
# Should show redirect message, NOT actual TDD content
```

### Step 3: Delete Redirect File
```bash
rm src/edison/data/guidelines/TDD.md
```

### Step 4: Verify Canonical File Still Works
```bash
# Test that rglob still finds the shared/TDD.md
python3 -c "
from pathlib import Path
core_dir = Path('src/edison/data/guidelines')
matches = list(core_dir.rglob('TDD.md'))
print(f'Found: {matches}')
assert len(matches) == 1, 'Should have exactly 1 TDD.md now'
assert 'shared' in str(matches[0]), 'Should find shared/TDD.md'
"
```

### Step 5: Run Composition Test
```bash
# From Wilson project
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose guidelines --dry-run
# Verify TDD.md output is ~296 lines, not 9
```

## Verification Checklist
- [ ] `/src/edison/data/guidelines/TDD.md` no longer exists
- [ ] `/src/edison/data/guidelines/shared/TDD.md` exists and has ~296 lines
- [ ] `python -c "from pathlib import Path; print(list(Path('src/edison/data/guidelines').rglob('TDD.md')))"` returns exactly 1 match
- [ ] `edison compose guidelines --dry-run` produces TDD.md with full content

## Success Criteria
The canonical 296-line TDD.md at `shared/TDD.md` is now discovered by the GuidelineRegistry instead of the 9-line redirect stub.

## Rollback Plan
If needed, recreate the redirect file:
```bash
cat > src/edison/data/guidelines/TDD.md << 'EOF'
# TDD Guidelines

See ./shared/TDD.md for the complete TDD guidelines.
EOF
```

## Related Issues
- Audit ID: NEW-004
- Audit ID: CG-013
