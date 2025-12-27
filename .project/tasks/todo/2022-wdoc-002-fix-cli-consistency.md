<!-- TaskID: 2022-wdoc-002-fix-cli-consistency -->
<!-- Priority: 2022 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: documentation -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave1-groupC -->
<!-- EstimatedHours: 1 -->

# WDOC-002: Fix CLI Command Inconsistency Across Documentation

## Summary
Fix inconsistent CLI command naming across all Edison documentation: standardize `task` (singular) vs `tasks` (plural), `qa bundle` vs `validators bundle`, etc.

## Problem Statement
CLI commands are referenced inconsistently:
- `edison task` vs `edison tasks` (which is correct?)
- `edison qa bundle` vs `edison validators bundle`
- `edison session complete` vs `edison session close`
- `edison session track` vs `edison track`

This creates confusion and potential errors when agents try to execute commands.

## Dependencies
- None - documentation standardization

## Objectives
- [x] Determine canonical command names from Edison CLI
- [x] Find all inconsistent references
- [x] Standardize to canonical names
- [x] Update both Edison core and Wilson docs

## Source Files

### Check Edison CLI for Canonical Names
```
/Users/leeroy/Documents/Development/edison/src/edison/cli/
```

### Documentation Files to Update
```
# Edison Core
/Users/leeroy/Documents/Development/edison/src/edison/data/guidelines/**/*.md

# Wilson Project
/Users/leeroy/Documents/Development/wilson-leadgen/.claude/CLAUDE.md
/Users/leeroy/Documents/Development/wilson-leadgen/.edison/_generated/**/*.md
```

## Precise Instructions

### Step 1: Determine Canonical CLI Names
```bash
cd /Users/leeroy/Documents/Development/edison

# List actual CLI commands
ls src/edison/cli/

# Check command group names
ls src/edison/cli/session/
ls src/edison/cli/task/  # or tasks/
ls src/edison/cli/qa/
ls src/edison/cli/compose/
```

### Step 2: Document Canonical Commands

Based on actual CLI structure, fill in this table:

| Subcommand Group | Canonical Form | Notes |
|------------------|----------------|-------|
| Task management | `edison task` | Singular |
| Session management | `edison session` | - |
| QA/Validation | `edison qa` | or `edison validate` |
| Composition | `edison compose` | - |
| Tracking | `edison session track` | Nested under session |

### Step 3: Search for Inconsistencies
```bash
cd /Users/leeroy/Documents/Development/edison

# Find task vs tasks inconsistency
grep -rn "edison task " src/edison/data/ --include="*.md" | head -20
grep -rn "edison tasks " src/edison/data/ --include="*.md" | head -20

# Find qa vs validators inconsistency
grep -rn "edison qa " src/edison/data/ --include="*.md" | head -20
grep -rn "edison validators " src/edison/data/ --include="*.md" | head -20
```

### Step 4: Create Standardization Script

```bash
#!/bin/bash
# standardize-cli.sh

# Define canonical forms (adjust based on Step 2 findings)
# Example assumes: task (singular), session track (not standalone track)

find src/edison/data -name "*.md" -exec sed -i '' \
  -e 's/edison tasks /edison task /g' \
  -e 's/edison validators bundle/edison qa bundle/g' \
  -e 's/edison track /edison session track /g' \
  -e 's/edison session close/edison session complete/g' \
  {} \;
```

### Step 5: Apply to Wilson Project
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen

# Same replacements for Wilson docs
find .edison -name "*.md" -exec sed -i '' \
  -e 's/edison tasks /edison task /g' \
  -e 's/edison validators bundle/edison qa bundle/g' \
  {} \;

# Update CLAUDE.md specifically
sed -i '' \
  -e 's/edison tasks /edison task /g' \
  -e 's/edison validators bundle/edison qa bundle/g' \
  .claude/CLAUDE.md
```

### Step 6: Verify Consistency
```bash
# Should return consistent results
grep -rn "edison task" /Users/leeroy/Documents/Development/edison/src/edison/data/ --include="*.md" | grep -v "edison task " | head -5
# If this returns lines, there are still inconsistencies
```

## Standard CLI Reference

After standardization, these should be the ONLY forms used:

```
edison session next <session-id>     # Get next recommended action
edison session track start           # Start activity tracking
edison session track complete        # Complete activity tracking
edison session track heartbeat       # Send heartbeat
edison session complete              # Mark session complete

edison task ready                    # List ready tasks
edison task claim <task-id>          # Claim a task
edison task status                   # Check task status

edison qa promote <task-id>          # Promote task after validation
edison qa bundle <task-id>           # Create validation bundle

edison validate <task-id>            # Run validators

edison compose all                   # Compose all artifacts
edison compose agents                # Compose agents only
edison compose validators            # Compose validators only
edison compose guidelines            # Compose guidelines only

edison rules show                    # Show applicable rules
```

## Verification Checklist
- [ ] Edison CLI structure documented
- [ ] All `edison tasks` changed to `edison task` (or vice versa based on canonical)
- [ ] All `edison validators bundle` changed to `edison qa bundle` (or vice versa)
- [ ] All `edison track` changed to `edison session track`
- [ ] No mixed forms in any documentation file
- [ ] Commands match actual CLI implementation

## Success Criteria
All documentation uses consistent CLI command names that match the actual Edison CLI implementation.

## Related Issues
- Audit ID: Wave 2R CLI inconsistency findings
