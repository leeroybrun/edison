"""JSON Schema Composer - composes schemas from core → packs → project."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from copy import deepcopy
import importlib.resources


class JsonSchemaComposer:
    """Composes JSON schemas from core → packs → project."""

    def __init__(self, project_root: Path, active_packs: Optional[List[str]] = None):
        self.project_root = project_root
        self.active_packs = active_packs or []

    def compose_all(self) -> Dict[str, Dict]:
        """Compose all schemas from core, packs, and project."""
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
        schemas = {}
        try:
            data_package = importlib.resources.files('edison.data')
            schemas_dir = data_package / 'schemas'

            for category in ['config', 'reports', 'domain', 'manifests', 'adapters']:
                category_path = schemas_dir / category
                if hasattr(category_path, 'iterdir'):
                    for schema_file in category_path.iterdir():
                        if str(schema_file).endswith('.json'):
                            name = f"{category}/{Path(str(schema_file)).stem}"
                            content = schema_file.read_text()
                            schemas[name] = json.loads(content)
        except Exception as e:
            print(f"Warning: Could not load core schemas: {e}")

        return schemas

    def _load_pack_schemas(self, pack_name: str) -> Dict[str, Dict]:
        """Load schemas from a pack."""
        schemas = {}
        try:
            packs_package = importlib.resources.files('edison.packs')
            pack_schemas = packs_package / pack_name / 'schemas'

            if hasattr(pack_schemas, 'iterdir'):
                for schema_file in pack_schemas.iterdir():
                    if str(schema_file).endswith('.json'):
                        name = Path(str(schema_file)).stem
                        content = schema_file.read_text()
                        schemas[name] = json.loads(content)
        except Exception:
            pass  # Pack may not have schemas

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

    def write_schemas(self, output_dir: Path) -> int:
        """Write composed schemas to output directory."""
        schemas = self.compose_all()

        for name, schema in schemas.items():
            output_path = output_dir / f"{name}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(schema, f, indent=2)

        return len(schemas)
