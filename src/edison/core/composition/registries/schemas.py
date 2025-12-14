"""JSON Schema Registry - composes schemas from core → packs → project.

Uses ConfigManager.deep_merge() for schema merging.
Implements standard ComposableRegistry interface.
"""
from __future__ import annotations

import json
import importlib.resources
from pathlib import Path
from typing import Any, Callable, ClassVar, Dict, List, Optional

from ._base import ComposableRegistry


class JsonSchemaRegistry(ComposableRegistry[str]):
    """Registry for composing JSON schemas.
    
    Composes schemas from core → packs → project using deep merge.
    Implements standard ComposableRegistry interface.
    
    Note: JSON schemas use json_merge composition mode, not markdown sections.
    """

    content_type: ClassVar[str] = "schemas"
    file_pattern: ClassVar[str] = "*.json"
    strategy_config: ClassVar[Dict[str, Any]] = {
        "enable_sections": False,
        "enable_dedupe": False,
        "enable_template_processing": False,
    }

    def _load_json(self, path: Any) -> Optional[Dict[str, Any]]:
        """Load JSON from path or traversable."""
        try:
            if hasattr(path, "read_text"):
                content = path.read_text()
            else:
                content = Path(path).read_text()
            return json.loads(content)
        except Exception:
            return None

    def _discover_core_schemas(self) -> Dict[str, Any]:
        """Discover core schema files from bundled data."""
        schemas: Dict[str, Any] = {}
        try:
            data_package = importlib.resources.files("edison.data")
            schemas_dir = data_package / "schemas"

            for category in ["config", "reports", "domain", "manifests", "adapters"]:
                category_path = schemas_dir / category
                if hasattr(category_path, "iterdir"):
                    for schema_file in category_path.iterdir():
                        if str(schema_file).endswith(".json"):
                            name = f"{category}/{Path(str(schema_file)).stem}"
                            schema = self._load_json(schema_file)
                            if schema:
                                schemas[name] = schema
        except Exception:
            pass
        return schemas

    def _discover_pack_schemas(self, pack_name: str) -> Dict[str, Any]:
        """Discover schemas from a pack."""
        schemas: Dict[str, Any] = {}
        
        # Bundled pack schemas
        try:
            packs_package = importlib.resources.files("edison.data") / "packs"
            pack_schemas = packs_package / pack_name / "schemas"
            if hasattr(pack_schemas, "iterdir"):
                for schema_file in pack_schemas.iterdir():
                    if str(schema_file).endswith(".json"):
                        name = Path(str(schema_file)).stem
                        schema = self._load_json(schema_file)
                        if schema:
                            schemas[name] = schema
        except Exception:
            pass
        
        # Project pack schemas
        project_pack_schemas = self.project_root / ".edison" / "packs" / pack_name / "schemas"
        if project_pack_schemas.exists():
            for schema_file in project_pack_schemas.rglob("*.json"):
                rel = schema_file.relative_to(project_pack_schemas)
                name = str(rel.with_suffix(""))
                schema = self._load_json(schema_file)
                if schema and name in schemas:
                    schemas[name] = self.cfg_mgr.deep_merge(schemas[name], schema)
                elif schema:
                    schemas[name] = schema
        
        return schemas

    def _discover_project_schemas(self) -> Dict[str, Any]:
        """Discover schemas from project .edison/schemas/."""
        schemas: Dict[str, Any] = {}
        project_schemas = self.project_root / ".edison" / "schemas"

        if project_schemas.exists():
            for schema_file in project_schemas.rglob("*.json"):
                rel_path = schema_file.relative_to(project_schemas)
                name = str(rel_path.with_suffix(""))
                schema = self._load_json(schema_file)
                if schema:
                    schemas[name] = schema

        return schemas

    def list_names(self) -> List[str]:
        """List all available schema names."""
        names: set[str] = set()
        
        # Core schemas
        names.update(self._discover_core_schemas().keys())
        
        # Pack schemas
        for pack in self.get_active_packs():
            names.update(self._discover_pack_schemas(pack).keys())
        
        # Project schemas
        names.update(self._discover_project_schemas().keys())
        
        return sorted(names)

    def _compose_schema_dict(self, name: str, packs: List[str]) -> Optional[Dict[str, Any]]:
        """Compose a single schema by name, returning dict.
        
        Args:
            name: Schema name (e.g., "config/session")
            packs: Active pack names
            
        Returns:
            Composed schema dict or None if not found
        """
        # Start with core
        core_schemas = self._discover_core_schemas()
        schema = core_schemas.get(name)
        
        if schema is None:
            # Check if it exists in packs or project
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
        
        # Merge pack schemas
        for pack in packs:
            pack_schemas = self._discover_pack_schemas(pack)
            if name in pack_schemas:
                schema = self.cfg_mgr.deep_merge(schema, pack_schemas[name])
        
        # Merge project schemas
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
        """Compose a schema and return as JSON string.
        
        Implements standard ComposableRegistry interface.
        
        Args:
            name: Schema name
            packs: Optional list of active pack names
            
        Returns:
            JSON string of composed schema, or None if not found
        """
        _ = include_provider  # Schemas do not use template includes
        packs = packs or self.get_active_packs()
        schema = self._compose_schema_dict(name, packs)
        if schema is None:
            return None
        return json.dumps(schema, indent=2)

    def compose_all(
        self,
        packs: Optional[List[str]] = None,
        *,
        include_provider: Optional[Callable[[str], Optional[str]]] = None,
    ) -> Dict[str, str]:
        """Compose all schemas.
        
        Standard interface - returns Dict[str, str] (JSON strings).
        
        Args:
            packs: Optional list of active pack names
            
        Returns:
            Dict mapping schema name to JSON string
        """
        _ = include_provider  # Schemas do not use template includes
        packs = packs or self.get_active_packs()
        results: Dict[str, str] = {}
        
        for name in self.list_names():
            content = self.compose(name, packs)
            if content:
                results[name] = content
        
        return results


__all__ = ["JsonSchemaRegistry"]
