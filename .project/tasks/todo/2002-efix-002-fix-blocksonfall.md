<!-- TaskID: 2002-efix-002-fix-blocksonfall -->
<!-- Priority: 2002 -->
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

# EFIX-002: Fix blocksOnFail Field Name in rosters.py

## Summary
Fix the field name mismatch in `rosters.py` where `blocking` is used but validators use `blocksOnFail`. This causes AVAILABLE_VALIDATORS.md to show all validators as non-blocking (❌) when some should be blocking (✅).

## Problem Statement
The validator roster generator at `rosters.py:138` checks:
```python
blocking = "✅" if v.get('blocking', False) else "❌"
```

But the validator config uses the field `blocksOnFail`:
```yaml
# In validators.yml
- id: codex-global
  blocksOnFail: true  # <-- correct field name
```

Result: AVAILABLE_VALIDATORS.md shows:
- codex-global: ❌ (WRONG - should be ✅)
- claude-global: ❌ (WRONG - should be ✅)
- security: ❌ (WRONG - should be ✅)

## Dependencies
- None - standalone fix

## Objectives
- [x] Locate the exact line in rosters.py
- [x] Change `blocking` to `blocksOnFail`
- [x] Verify validators.yml uses blocksOnFail
- [x] Regenerate AVAILABLE_VALIDATORS.md
- [x] Verify blocking values are correct

## Source Files

### File to Modify
```
/Users/leeroy/Documents/Development/edison/src/edison/core/composition/registries/rosters.py
```

### Line to Change
Line ~138 (exact location may vary, search for `blocking`):
```python
# BEFORE (wrong):
blocking = "✅" if v.get('blocking', False) else "❌"

# AFTER (correct):
blocking = "✅" if v.get('blocksOnFail', False) else "❌"
```

### Reference - Validator Config Format
```
/Users/leeroy/Documents/Development/edison/src/edison/data/config/validators.yml
```
Expected structure:
```yaml
validators:
  global:
    - id: codex-global
      blocksOnFail: true
    - id: claude-global
      blocksOnFail: true
  critical:
    - id: security
      blocksOnFail: true
    - id: performance
      blocksOnFail: true
  specialized:
    - id: api
      blocksOnFail: false
    # etc.
```

## Precise Instructions

### Step 1: Find the Exact Line
```bash
cd /Users/leeroy/Documents/Development/edison
grep -n "blocking" src/edison/core/composition/registries/rosters.py
# Find line with v.get('blocking', False)
```

### Step 2: Verify Validator Config Uses blocksOnFail
```bash
grep -n "blocksOnFail" src/edison/data/config/validators.yml | head -10
# Should show multiple validators with blocksOnFail: true
```

### Step 3: Make the Change
Open `src/edison/core/composition/registries/rosters.py` and change:
```python
# Find this line (around line 138):
blocking = "✅" if v.get('blocking', False) else "❌"

# Replace with:
blocking = "✅" if v.get('blocksOnFail', False) else "❌"
```

### Step 4: Verify the Fix
```bash
# Run Python test
python3 -c "
v = {'id': 'test', 'blocksOnFail': True}
blocking = '✅' if v.get('blocksOnFail', False) else '❌'
assert blocking == '✅', 'blocksOnFail=True should produce ✅'
print('Test passed')
"
```

### Step 5: Regenerate AVAILABLE_VALIDATORS.md
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose validators
# Check the output
cat .edison/_generated/AVAILABLE_VALIDATORS.md | head -30
```

### Step 6: Verify Output
The AVAILABLE_VALIDATORS.md should now show:
```markdown
| codex-global | Global | * | ✅ | ✅ |
| claude-global | Global | * | ✅ | ✅ |
| security | Critical | * | ✅ | ✅ |
| performance | Critical | * | ✅ | ✅ |
| api | Specialized | **/api/**/*.ts | ❌ | ❌ |
```

## Verification Checklist
- [ ] `grep "blocksOnFail" src/edison/core/composition/registries/rosters.py` returns 1+ matches
- [ ] `grep "blocking" src/edison/core/composition/registries/rosters.py` returns 0 matches (for the field access)
- [ ] AVAILABLE_VALIDATORS.md shows ✅ for global validators
- [ ] AVAILABLE_VALIDATORS.md shows ✅ for critical validators
- [ ] Unit tests pass (if any exist for rosters)

## Success Criteria
AVAILABLE_VALIDATORS.md correctly displays blocking status for all validators based on their `blocksOnFail` config value.

## Related Issues
- Audit ID: NEW-005
- Audit ID: CG-014
