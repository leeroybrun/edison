"""Schema registry - composes schemas from core → packs → project.

Edison stores JSON Schema documents serialized as YAML for readability and for
consistency with the rest of the configuration surface.

This registry discovers schema files across:
- bundled core: ``edison.data/schemas/**``
- bundled packs: ``edison.data/packs/<pack>/schemas/**`` (optional)
- project pack overlays: ``.edison/packs/<pack>/schemas/**`` (optional)
- project overrides: ``.edison/schemas/**`` (optional)

and composes them with ConfigManager.deep_merge() in the standard order:
core → packs → project.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import Any, Callable, ClassVar, Dict, List, Optional

from edison.core.utils.io import dump_yaml_string, parse_yaml_string, read_yaml
from edison.core.utils.paths import get_project_config_dir

from ._base import ComposableRegistry


class SchemaRegistry(ComposableRegistry[str]):
    """Registry for composing YAML-serialized JSON Schemas."""

    content_type: ClassVar[str] = "schemas"
    file_pattern: ClassVar[str] = "*.yaml"
    strategy_config: ClassVar[Dict[str, Any]] = {
        "enable_sections": False,
        "enable_dedupe": False,
        "enable_template_processing": False,
    }

    def _load_yaml(self, path: Any) -> Optional[Dict[str, Any]]:
        try:
            if isinstance(path, Path):
                data = read_yaml(path, default=None, raise_on_error=True)
            elif hasattr(path, "read_text"):
                data = parse_yaml_string(path.read_text(), default=None)
            else:
                data = read_yaml(Path(path), default=None, raise_on_error=True)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _is_schema_file(self, name: str) -> bool:
        lower = name.lower()
        return lower.endswith(".yaml") or lower.endswith(".yml")

    def _discover_core_schemas(self) -> Dict[str, Any]:
        schemas: Dict[str, Any] = {}
        try:
            data_package = importlib.resources.files("edison.data")
            schemas_dir = data_package / "schemas"

            for category in ["config", "reports", "domain", "manifests", "adapters"]:
                category_path = schemas_dir / category
                if hasattr(category_path, "iterdir"):
                    for schema_file in category_path.iterdir():
                        if not self._is_schema_file(str(schema_file)):
                            continue
                        name = f"{category}/{Path(str(schema_file)).stem}"
                        schema = self._load_yaml(schema_file)
                        if schema:
                            schemas[name] = schema
        except Exception:
            pass
        return schemas

    def _discover_pack_schemas(self, pack_name: str) -> Dict[str, Any]:
        schemas: Dict[str, Any] = {}

        # Bundled pack schemas
        try:
            packs_package = importlib.resources.files("edison.data") / "packs"
            pack_schemas = packs_package / pack_name / "schemas"
            if hasattr(pack_schemas, "iterdir"):
                for schema_file in pack_schemas.iterdir():
                    if not self._is_schema_file(str(schema_file)):
                        continue
                    name = Path(str(schema_file)).stem
                    schema = self._load_yaml(schema_file)
                    if schema:
                        schemas[name] = schema
        except Exception:
            pass

        # Project pack schemas
        project_dir = get_project_config_dir(self.project_root, create=False)
        project_pack_schemas = project_dir / "packs" / pack_name / "schemas"
        if project_pack_schemas.exists():
            for schema_file in project_pack_schemas.rglob("*.y*ml"):
                rel = schema_file.relative_to(project_pack_schemas)
                name = str(rel.with_suffix(""))
                schema = self._load_yaml(schema_file)
                if schema and name in schemas:
                    schemas[name] = self.cfg_mgr.deep_merge(schemas[name], schema)
                elif schema:
                    schemas[name] = schema

        return schemas

    def _discover_project_schemas(self) -> Dict[str, Any]:
        schemas: Dict[str, Any] = {}
        project_dir = get_project_config_dir(self.project_root, create=False)
        project_schemas = project_dir / "schemas"

        if project_schemas.exists():
            for schema_file in project_schemas.rglob("*.y*ml"):
                rel_path = schema_file.relative_to(project_schemas)
                name = str(rel_path.with_suffix(""))
                schema = self._load_yaml(schema_file)
                if schema:
                    schemas[name] = schema

        return schemas

    def list_names(self) -> List[str]:
        names: set[str] = set()
        names.update(self._discover_core_schemas().keys())
        for pack in self.get_active_packs():
            names.update(self._discover_pack_schemas(pack).keys())
        names.update(self._discover_project_schemas().keys())
        return sorted(names)

    def _compose_schema_dict(self, name: str, packs: List[str]) -> Optional[Dict[str, Any]]:
        core_schemas = self._discover_core_schemas()
        schema = core_schemas.get(name)

        if schema is None:
            for pack in packs:
                pack_schemas = self._discover_pack_schemas(pack)
                if name in pack_schemas:
                    schema = pack_schemas[name]
                    break

            if schema is None:
                project_schemas = self._discover_project_schemas()
                schema = project_schemas.get(name)

        if schema is None:
            return None

        for pack in packs:
            pack_schemas = self._discover_pack_schemas(pack)
            if name in pack_schemas:
                schema = self.cfg_mgr.deep_merge(schema, pack_schemas[name])

        project_schemas = self._discover_project_schemas()
        if name in project_schemas:
            schema = self.cfg_mgr.deep_merge(schema, project_schemas[name])

        return schema

    def compose(
        self,
        name: str,
        packs: Optional[List[str]] = None,
        *,
        include_provider: Optional[Callable[[str], Optional[str]]] = None,
    ) -> Optional[str]:
        _ = include_provider
        packs = packs or self.get_active_packs()
        schema = self._compose_schema_dict(name, packs)
        if schema is None:
            return None
        return dump_yaml_string(schema, sort_keys=False)

    def compose_all(
        self,
        packs: Optional[List[str]] = None,
        *,
        include_provider: Optional[Callable[[str], Optional[str]]] = None,
    ) -> Dict[str, str]:
        _ = include_provider
        packs = packs or self.get_active_packs()
        results: Dict[str, str] = {}

        for name in self.list_names():
            content = self.compose(name, packs)
            if content:
                results[name] = content

        return results


__all__ = ["SchemaRegistry"]
