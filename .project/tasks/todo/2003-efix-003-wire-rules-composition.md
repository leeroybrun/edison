<!-- TaskID: 2003-efix-003-wire-rules-composition -->
<!-- Priority: 2003 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: feature -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: codex -->
<!-- ParallelGroup: wave1-groupA -->
<!-- EstimatedHours: 2 -->

# EFIX-003: Wire Rules Composition into Compose Pipeline

## Summary
The `RulesRegistry` class exists and is fully functional, but it is NOT called by the `edison compose all` command. This means rules are never composed, and `session/next/rules.py` expects a `registry.json` that doesn't exist.

## Problem Statement
Current state:
1. `RulesRegistry` class exists at `src/edison/core/composition/registries/rules.py` ✅
2. Core rules YAML exists at `src/edison/data/rules/registry.yml` ✅
3. `compose/all.py` generates agents, validators, guidelines, constitutions ❌ (missing rules)
4. `session/next/rules.py:43` expects JSON that's never generated ❌

## Dependencies
- None - standalone implementation

## Objectives
- [x] Add rules composition call to compose/all.py
- [x] Ensure RulesRegistry.compose() is called
- [x] Output goes to .edison/_generated/rules/registry.json
- [x] session/next can load the generated rules
- [x] Run compose all and verify rules are generated

## Source Files

### File to Modify
```
/Users/leeroy/Documents/Development/edison/src/edison/cli/compose/all.py
```

### Supporting Files
```
/Users/leeroy/Documents/Development/edison/src/edison/core/composition/registries/rules.py
/Users/leeroy/Documents/Development/edison/src/edison/data/rules/registry.yml
/Users/leeroy/Documents/Development/edison/src/edison/cli/session/next/rules.py
```

## Precise Instructions

### Step 1: Understand Current Compose Flow
```bash
cd /Users/leeroy/Documents/Development/edison
cat src/edison/cli/compose/all.py
```

Look for the main composition function that calls:
- agents composition
- validators composition
- guidelines composition
- constitutions composition

### Step 2: Understand RulesRegistry Interface
```bash
cat src/edison/core/composition/registries/rules.py | head -100
```

Key methods to understand:
- `RulesRegistry.__init__(project_root: Path)`
- `RulesRegistry.compose() -> dict`
- `RulesRegistry.write_output(output_path: Path)`

### Step 3: Add Rules Composition

In `compose/all.py`, add after other compositions:

```python
# Add import at top
from edison.core.composition.registries.rules import RulesRegistry

# Add in main composition function (likely called compose_all or main):
def compose_all(project_root: Path, ...):
    # ... existing compositions ...

    # Add rules composition
    console.print("[bold blue]Composing rules...[/bold blue]")
    rules_registry = RulesRegistry(project_root)
    rules = rules_registry.compose()

    output_dir = project_root / ".edison" / "_generated" / "rules"
    output_dir.mkdir(parents=True, exist_ok=True)

    rules_output = output_dir / "registry.json"
    rules_registry.write_output(rules_output)
    console.print(f"[green]✓[/green] Generated {rules_output}")
```

### Step 4: Verify RulesRegistry Has write_output Method

If `write_output` doesn't exist, implement it:

```python
# In rules.py, add method to RulesRegistry class:
def write_output(self, output_path: Path) -> None:
    """Write composed rules to JSON file."""
    import json
    rules_data = self.compose()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(rules_data, f, indent=2)
```

### Step 5: Test the Change
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose all

# Verify rules were generated
cat .edison/_generated/rules/registry.json | head -50
```

### Step 6: Verify session/next Can Load Rules
```bash
# Check that session/next/rules.py path matches
grep -n "registry.json" src/edison/cli/session/next/rules.py
# Ensure path matches: .edison/_generated/rules/registry.json
```

## Expected Output Structure
```json
{
  "version": "1.0",
  "generated_at": "2025-12-02T...",
  "rules": [
    {
      "id": "RULE.DELEGATION.PRIORITY_CHAIN",
      "category": "delegation",
      "blocking": false,
      "severity": "warning",
      "applies_to": ["orchestrator"],
      "guidance": "..."
    },
    // ... 35 more rules
  ]
}
```

## Verification Checklist
- [ ] `grep -n "RulesRegistry" src/edison/cli/compose/all.py` shows import and usage
- [ ] `edison compose all` completes without errors
- [ ] `.edison/_generated/rules/registry.json` exists
- [ ] JSON file contains 36 rules (matching audit count)
- [ ] `edison session next` can load rules without errors

## Success Criteria
Running `edison compose all` generates a valid `registry.json` containing all composed rules from core, packs, and project layers.

## Rollback Plan
Remove the rules composition call from compose/all.py. The system will continue to work without rules composition (just won't have the feature).

## Related Issues
- Audit ID: NEW-002
- Audit ID: CG-017
