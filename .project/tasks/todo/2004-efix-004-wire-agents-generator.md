<!-- TaskID: 2004-efix-004-wire-agents-generator -->
<!-- Priority: 2004 -->
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

# EFIX-004: Wire AGENTS.md Generator into Compose Pipeline

## Summary
The AGENTS.md template and configuration exist, but the generator function was never implemented and wired into the compose pipeline. This task completes the 90%-done feature.

## Problem Statement
Current state:
1. Template exists: `src/edison/data/canonical/AGENTS.md` ✅
2. Config exists: `composition.yaml` → `outputs.canonical_entry` ✅
3. OutputConfigLoader has `get_canonical_entry_config()` method ✅
4. Generator function: ❌ DOES NOT EXIST
5. CLI integration: ❌ Not called in `compose all`

Result: No root AGENTS.md is generated as a unified hub document.

## Dependencies
- None - standalone implementation

## Objectives
- [x] Create `generate_canonical_entry()` function
- [x] Wire into compose/all.py
- [x] Generate AGENTS.md to _generated/
- [x] Verify content is correct

## Source Files

### Template File
```
/Users/leeroy/Documents/Development/edison/src/edison/data/canonical/AGENTS.md
```

### Config Reference
```
/Users/leeroy/Documents/Development/edison/src/edison/data/config/composition.yaml
```
Look for `canonical_entry` section.

### Files to Modify
```
/Users/leeroy/Documents/Development/edison/src/edison/core/composition/__init__.py
/Users/leeroy/Documents/Development/edison/src/edison/cli/compose/all.py
```

### Potentially Create
```
/Users/leeroy/Documents/Development/edison/src/edison/core/composition/canonical.py
```

## Precise Instructions

### Step 1: Understand Template Structure
```bash
cd /Users/leeroy/Documents/Development/edison
cat src/edison/data/canonical/AGENTS.md
```

Look for template variables like:
- `{{MANDATORY_READS}}`
- `{{AVAILABLE_AGENTS}}`
- `{{WORKFLOW_SUMMARY}}`

### Step 2: Check Existing Config
```bash
grep -A 20 "canonical_entry" src/edison/data/config/composition.yaml
```

### Step 3: Create Generator Function

Create new file or add to existing module:

```python
# src/edison/core/composition/canonical.py

from pathlib import Path
from typing import Dict, Any
import importlib.resources

def generate_canonical_entry(
    project_root: Path,
    agents: list,
    guidelines: list,
    validators: list,
) -> str:
    """Generate the root AGENTS.md hub document."""

    # Load template
    data_package = importlib.resources.files('edison.data')
    template_path = data_package / 'canonical' / 'AGENTS.md'
    template = template_path.read_text()

    # Build agent roster
    agent_table = "| Agent | Description | Primary Task Types |\n"
    agent_table += "|-------|-------------|--------------------|\n"
    for agent in agents:
        agent_table += f"| {agent['id']} | {agent.get('description', 'N/A')} | {agent.get('taskTypes', 'N/A')} |\n"

    # Build guideline list
    guideline_list = "\n".join([f"- {g['name']}" for g in guidelines])

    # Build validator list
    validator_list = "\n".join([f"- {v['id']} ({v['type']})" for v in validators])

    # Substitute variables
    output = template
    output = output.replace("{{AGENT_ROSTER}}", agent_table)
    output = output.replace("{{GUIDELINE_LIST}}", guideline_list)
    output = output.replace("{{VALIDATOR_LIST}}", validator_list)
    output = output.replace("{{GENERATED_TIMESTAMP}}", datetime.now().isoformat())

    return output


def write_canonical_entry(
    project_root: Path,
    content: str,
    output_dir: Path = None
) -> Path:
    """Write the generated AGENTS.md to output directory."""
    if output_dir is None:
        output_dir = project_root / ".edison" / "_generated"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "AGENTS.md"
    output_path.write_text(content)

    return output_path
```

### Step 4: Export from __init__.py

Add to `src/edison/core/composition/__init__.py`:
```python
from .canonical import generate_canonical_entry, write_canonical_entry
```

### Step 5: Wire into compose/all.py

Add to the main composition function:
```python
from edison.core.composition import generate_canonical_entry, write_canonical_entry

def compose_all(project_root: Path, ...):
    # ... existing compositions ...

    # Generate canonical AGENTS.md
    console.print("[bold blue]Generating AGENTS.md...[/bold blue]")
    agents_content = generate_canonical_entry(
        project_root=project_root,
        agents=composed_agents,  # from earlier composition
        guidelines=composed_guidelines,
        validators=composed_validators,
    )
    agents_path = write_canonical_entry(project_root, agents_content)
    console.print(f"[green]✓[/green] Generated {agents_path}")
```

### Step 6: Test the Implementation
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose all

# Verify AGENTS.md was generated
ls -la .edison/_generated/AGENTS.md
cat .edison/_generated/AGENTS.md | head -50
```

## Expected Output Structure
```markdown
# Edison Agent Hub

**Generated**: 2025-12-02T...

## Available Agents

| Agent | Description | Primary Task Types |
|-------|-------------|---------------------|
| api-builder | Builds API endpoints | api-route |
| component-builder | Builds UI components | ui-component |
| ... | ... | ... |

## Guidelines Reference

- SESSION_WORKFLOW
- DELEGATION
- TDD
- ...

## Validators Reference

- codex-global (Global)
- claude-global (Global)
- security (Critical)
- ...
```

## Verification Checklist
- [ ] `generate_canonical_entry` function exists
- [ ] Function is exported from composition module
- [ ] `edison compose all` calls the generator
- [ ] `.edison/_generated/AGENTS.md` is created
- [ ] File contains agent roster table
- [ ] File contains guideline references
- [ ] File contains validator references

## Success Criteria
Running `edison compose all` generates a complete AGENTS.md hub document that lists all available agents, guidelines, and validators in a unified format.

## Related Issues
- Audit ID: NEW-003
- Audit ID: CG-022
