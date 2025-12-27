<!-- TaskID: 2015-wcfg-005-json-schema-composition -->
<!-- Priority: 2015 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: feature -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: codex -->
<!-- ParallelGroup: wave1-groupB -->
<!-- EstimatedHours: 10 -->

# WCFG-005: Implement JSON Schema Composition

## Summary
Implement a JSON schema composition system that merges schemas from core → packs → project, then generates project-specific schemas in `_generated/schemas/`.

## Problem Statement
Edison has 14 schemas in `src/edison/data/schemas/` but:
- NO composition support
- NO pack schema extensions
- NO project schema overrides
- Schemas not accessible from projects (bundled in package)

Projects need generated schemas that combine core + pack + project extensions.

## Dependencies
- None - foundational feature

## Objectives
- [x] Add `schemas` composition type to composition.yaml
- [x] Create JsonSchemaComposer class
- [x] Support pack schema directories
- [x] Support project schema overrides
- [x] Generate to `_generated/schemas/`
- [x] Create implementation-report.schema.json

## Source Files

### Existing Schemas
```
/Users/leeroy/Documents/Development/edison/src/edison/data/schemas/
├── config/
├── reports/
│   └── delegation-report.schema.json
├── states/
├── tracking/
└── validation/
```

### Files to Create/Modify
```
/Users/leeroy/Documents/Development/edison/src/edison/core/composition/schemas.py
/Users/leeroy/Documents/Development/edison/src/edison/data/config/composition.yaml
/Users/leeroy/Documents/Development/edison/src/edison/cli/compose/all.py
```

## Precise Instructions

### Step 1: Update composition.yaml

Add schemas type:
```yaml
types:
  # ... existing types ...

  schemas:
    mode: json_merge
    sources:
      - core: src/edison/data/schemas/
      - packs: packs/{pack}/schemas/
      - project: .edison/schemas/
    output: _generated/schemas/
    merge_strategy: deep  # Deep merge JSON objects
```

### Step 2: Create JsonSchemaComposer

```python
# src/edison/core/composition/schemas.py

import json
from pathlib import Path
from typing import Any, Dict, List
from copy import deepcopy

class JsonSchemaComposer:
    """Composes JSON schemas from core → packs → project."""

    def __init__(self, project_root: Path, active_packs: List[str]):
        self.project_root = project_root
        self.active_packs = active_packs

    def compose_all(self) -> Dict[str, Dict]:
        """Compose all schemas."""
        schemas = {}

        # 1. Load core schemas
        core_schemas = self._load_core_schemas()
        schemas.update(core_schemas)

        # 2. Merge pack schemas
        for pack in self.active_packs:
            pack_schemas = self._load_pack_schemas(pack)
            for name, schema in pack_schemas.items():
                if name in schemas:
                    schemas[name] = self._deep_merge(schemas[name], schema)
                else:
                    schemas[name] = schema

        # 3. Merge project schemas
        project_schemas = self._load_project_schemas()
        for name, schema in project_schemas.items():
            if name in schemas:
                schemas[name] = self._deep_merge(schemas[name], schema)
            else:
                schemas[name] = schema

        return schemas

    def _load_core_schemas(self) -> Dict[str, Dict]:
        """Load schemas from Edison core."""
        import importlib.resources
        schemas = {}
        data_package = importlib.resources.files('edison.data')
        schemas_dir = data_package / 'schemas'

        for category in ['config', 'reports', 'states', 'tracking', 'validation']:
            category_dir = schemas_dir / category
            if category_dir.is_dir():
                for schema_file in category_dir.iterdir():
                    if schema_file.suffix == '.json':
                        name = f"{category}/{schema_file.stem}"
                        content = schema_file.read_text()
                        schemas[name] = json.loads(content)

        return schemas

    def _load_pack_schemas(self, pack_name: str) -> Dict[str, Dict]:
        """Load schemas from a pack."""
        schemas = {}
        import importlib.resources
        packs_package = importlib.resources.files('edison.packs')
        pack_schemas = packs_package / pack_name / 'schemas'

        if pack_schemas.is_dir():
            for schema_file in pack_schemas.rglob('*.json'):
                rel_path = schema_file.relative_to(pack_schemas)
                name = str(rel_path.with_suffix(''))
                content = schema_file.read_text()
                schemas[name] = json.loads(content)

        return schemas

    def _load_project_schemas(self) -> Dict[str, Dict]:
        """Load schemas from project .edison/schemas/."""
        schemas = {}
        project_schemas = self.project_root / '.edison' / 'schemas'

        if project_schemas.exists():
            for schema_file in project_schemas.rglob('*.json'):
                rel_path = schema_file.relative_to(project_schemas)
                name = str(rel_path.with_suffix(''))
                with open(schema_file) as f:
                    schemas[name] = json.load(f)

        return schemas

    def _deep_merge(self, base: Dict, overlay: Dict) -> Dict:
        """Deep merge overlay into base."""
        result = deepcopy(base)

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)

        return result

    def write_schemas(self, schemas: Dict[str, Dict], output_dir: Path) -> None:
        """Write composed schemas to output directory."""
        for name, schema in schemas.items():
            output_path = output_dir / f"{name}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(schema, f, indent=2)
```

### Step 3: Wire into compose/all.py

```python
from edison.core.composition.schemas import JsonSchemaComposer

def compose_all(project_root: Path, ...):
    # ... existing compositions ...

    # Compose schemas
    console.print("[bold blue]Composing schemas...[/bold blue]")
    schema_composer = JsonSchemaComposer(project_root, active_packs)
    schemas = schema_composer.compose_all()

    output_dir = project_root / ".edison" / "_generated" / "schemas"
    schema_composer.write_schemas(schemas, output_dir)
    console.print(f"[green]✓[/green] Generated {len(schemas)} schemas")
```

### Step 4: Create Missing implementation-report.schema.json

See task `2014-wcfg-004` for the schema content.

### Step 5: Test Composition
```bash
cd /Users/leeroy/Documents/Development/wilson-leadgen
edison compose all

ls .edison/_generated/schemas/
# Should list composed schemas

# Verify a schema merged correctly
cat .edison/_generated/schemas/reports/delegation-report.json
```

## Verification Checklist
- [ ] JsonSchemaComposer class created
- [ ] composition.yaml has schemas type
- [ ] compose all calls schema composition
- [ ] Core schemas copied to _generated
- [ ] Pack schemas merged (if any exist)
- [ ] Project schemas override (if any exist)
- [ ] implementation-report.schema.json exists

## Success Criteria
Running `edison compose all` generates project-specific schemas that combine core + packs + project layers.

## Related Issues
- Audit ID: NEW-001
- Audit ID: CG-015
