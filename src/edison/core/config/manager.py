"""
Edison Framework Configuration Management (YAML-only, no legacy fallbacks).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import os
import json
import re

from edison.core.utils.merge import deep_merge as _deep_merge, merge_arrays
from edison.data import get_data_path
from edison.core.utils.profiling import span
from edison.core.config.cache import get_cached_config

# Lazy imports to avoid circular dependencies
# These are imported at runtime inside methods that need them
if TYPE_CHECKING:
    from edison.core.utils.paths import PathResolver, EdisonPathError

try:  # Optional: Present in Edison core Python env
    import yaml  # type: ignore
except Exception as err:  # pragma: no cover - surfaced at import time
    raise RuntimeError("PyYAML is required: pip install pyyaml") from err

try:  # Optional: Present in Edison core Python env
    import jsonschema  # type: ignore
except Exception as err:  # pragma: no cover - surfaced at import time
    raise RuntimeError("jsonschema is required: pip install jsonschema") from err


class ConfigManager:
    """Load, merge, and validate Edison configuration.

    Configuration sources (highest to lowest priority):
    1. Environment variables: EDISON_*
    2. Project config: .edison/config/*.yaml (alphabetical order)
    3. Pack configs: bundled_packs/*/config/*.yaml + project_packs/*/config/*.yaml
    4. Bundled defaults: edison.data/config/*.yaml (alphabetical order)

    Pack-aware loading uses two phases:
    - Phase 1 (Bootstrap): core > project to determine packs.active
    - Phase 2 (Full): core > bundled_packs > project_packs > project

    All YAML files are loaded and merged - no special handling for defaults.yaml.
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or self._find_repo_root()

        # Lazy import to avoid circular dependencies
        from edison.core.utils.paths import get_project_config_dir
        project_root_dir = get_project_config_dir(self.repo_root, create=False)

        # Bundled defaults from edison.data package (always available)
        self.core_config_dir = get_data_path("config")

        # Project-specific config overrides
        self.project_config_dir = project_root_dir / "config"

        # Pack directories
        self.bundled_packs_dir = get_data_path("packs")
        self.project_packs_dir = project_root_dir / "packs"

        # Schemas from bundled data
        self.schemas_dir = get_data_path("schemas")

    @property
    def project_root(self) -> Path:
        """Alias for repo_root for backward compatibility."""
        return self.repo_root

    def _find_repo_root(self) -> Path:
        # Lazy import to avoid circular dependencies
        from edison.core.utils.paths import PathResolver, EdisonPathError
        try:
            return PathResolver.resolve_project_root()
        except EdisonPathError as exc:
            raise RuntimeError(str(exc)) from exc

    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge dictionaries. Delegates to shared implementation."""
        return _deep_merge(base, override)

    def load_yaml(self, path: Path) -> Dict[str, Any]:
        from edison.core.utils.io import read_yaml
        # Fail closed: configuration must never silently ignore invalid YAML.
        return read_yaml(path, default={}, raise_on_error=True)

    def load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        from edison.core.utils.io import read_json as io_read_json
        data = io_read_json(path)
        return data or {}

    def validate_schema(self, config: Dict[str, Any], schema_name: str) -> None:
        from edison.core.schemas.validation import validate_payload

        validate_payload(config, schema_name, repo_root=self.repo_root)

    ARRAY_APPEND_MARKER = object()

    def _as_bool(self, v: str) -> Optional[bool]:
        low = v.strip().lower()
        if low in {"true", "false"}:
            return low == "true"
        return None

    def _as_int(self, v: str) -> Optional[int]:
        if re.fullmatch(r"[-+]?\d+", v.strip() or " "):
            try:
                return int(v)
            except Exception:
                return None
        return None

    def _as_float(self, v: str) -> Optional[float]:
        s = v.strip()
        if re.fullmatch(r"[-+]?\d*\.\d+", s) or re.fullmatch(r"[-+]?\d+\.\d*", s):
            try:
                return float(s)
            except Exception:
                return None
        return None

    def _as_json(self, v: str) -> Optional[Any]:
        s = v.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except Exception:
                return None
        return None

    def _coerce_type(self, value: str) -> Any:
        for caster in (self._as_bool, self._as_int, self._as_float, self._as_json):
            result = caster(value)
            if result is not None:
                return result
        return value.strip()

    def _parse_env_key(self, raw: str, *, strict: bool) -> List[Union[str, int, object]]:
        if not raw:
            return []
        segs = raw.split("__") if "__" in raw else raw.split("_")
        processed: List[Union[str, int, object]] = []
        for seg in segs:
            if seg == "":
                if strict:
                    raise ValueError(
                        f"Malformed EDISON_* key: empty segment in '{raw}'."
                    )
                return []
            if seg.isdigit():
                processed.append(int(seg))
            elif seg.upper() == "APPEND":
                processed.append(self.ARRAY_APPEND_MARKER)
            else:
                # Normalize to lowercase so env overrides create canonical keys,
                # while still supporting case-insensitive matching for existing keys.
                processed.append(seg.lower())
        return processed

    def _iter_env_overrides(self, *, strict: bool):
        prefix = "EDISON_"
        for key in sorted(os.environ.keys()):
            if not key.startswith(prefix):
                continue
            raw = key[len(prefix) :]
            if not raw:
                if strict:
                    raise ValueError("Malformed EDISON_* key")
                continue
            path = self._parse_env_key(raw, strict=strict)
            if not path:
                continue
            yield path, self._coerce_type(os.environ[key]), raw

    def _set_nested(self, root: Dict[str, Any], path: List[Union[str, int, object]], value: Any) -> None:
        if not path:
            return

        def _assign_leaf(container: Any, leaf: Union[str, int, object], val: Any) -> None:
            if leaf is self.ARRAY_APPEND_MARKER:
                if not isinstance(container, list):
                    raise ValueError("APPEND requires list")
                container.append(val)
                return
            if isinstance(leaf, int):
                if not isinstance(container, list):
                    raise ValueError("Index assignment requires list")
                while len(container) <= leaf:
                    container.append(None)
                container[leaf] = val
                return
            if not isinstance(container, dict):
                raise ValueError("Key assignment requires dict")
            if isinstance(leaf, str):
                lower_map = {k.lower(): k for k in container.keys() if isinstance(k, str)}
                use_key = lower_map.get(leaf.lower(), leaf)
            else:
                use_key = leaf
            container[use_key] = val

        def _navigate_to_parent(container: Any, p: List[Union[str, int, object]]) -> tuple[Any, Union[str, int, object]]:
            cur = container
            for i, part in enumerate(p):
                is_last = i == len(p) - 1
                if is_last:
                    return cur, part
                nxt = p[i + 1]
                if isinstance(part, int) or part is self.ARRAY_APPEND_MARKER:
                    raise ValueError("Invalid path: list index/APPEND may only appear at leaf")
                if not isinstance(cur, dict):
                    raise ValueError("Path traverses non-dict container")
                key_candidates = {k.lower(): k for k in cur.keys() if isinstance(k, str)}
                key_to_use = key_candidates.get(str(part).lower(), part)
                if key_to_use not in cur:
                    cur[key_to_use] = [] if (isinstance(nxt, int) or nxt is self.ARRAY_APPEND_MARKER) else {}
                cur = cur[key_to_use]
            return cur, p[-1]

        parent, leaf = _navigate_to_parent(root, path)
        _assign_leaf(parent, leaf, value)

    def apply_env_overrides(self, cfg: Dict[str, Any], *, strict: bool) -> None:
        for path, typed_value, raw in self._iter_env_overrides(strict=strict):
            self._set_nested(cfg, path, typed_value)

    # ========== Pack-Aware Config Loading ==========

    def _load_directory(self, directory: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Load all YAML files from a directory and merge into config.

        Args:
            directory: Directory containing YAML files
            cfg: Base configuration to merge into

        Returns:
            Merged configuration dictionary
        """
        if not directory.exists():
            return cfg

        yml_files = list(directory.glob("*.yml"))
        yaml_files = list(directory.glob("*.yaml"))
        for path in sorted(yml_files + yaml_files):
            module_cfg = self.load_yaml(path)
            cfg = self.deep_merge(cfg, module_cfg)

        return cfg

    def _get_bootstrap_packs(self, cfg: Dict[str, Any]) -> List[str]:
        """Extract active packs from bootstrap config (Phase 1).

        This is used during two-phase loading to determine which packs
        to load config from before the full merge is complete.

        Args:
            cfg: Partially loaded config (core + project, no packs yet)

        Returns:
            List of active pack names
        """
        packs_section = cfg.get("packs", {}) or {}
        active = packs_section.get("active", []) or []

        if not isinstance(active, list):
            return []

        return [str(p) for p in active if p]

    def _load_pack_configs(
        self, cfg: Dict[str, Any], active_packs: List[str]
    ) -> Dict[str, Any]:
        """Load config from active packs (bundled + project).

        Pack configs are loaded in order:
        1. Bundled packs (edison.data/packs/{pack}/config/*.yaml)
        2. Project packs (.edison/packs/{pack}/config/*.yaml)

        Args:
            cfg: Base configuration to merge into
            active_packs: List of active pack names

        Returns:
            Configuration with pack overlays merged
        """
        for pack_name in active_packs:
            # Load bundled pack config
            bundled_pack_config = self.bundled_packs_dir / pack_name / "config"
            cfg = self._load_directory(bundled_pack_config, cfg)

            # Load project pack config (overrides bundled)
            project_pack_config = self.project_packs_dir / pack_name / "config"
            cfg = self._load_directory(project_pack_config, cfg)

        return cfg

    def _apply_project_env_aliases(self, cfg: Dict[str, Any]) -> None:
        """Route legacy project env vars through the config system."""
        has_edison_project_env = any(k.startswith("EDISON_project__") for k in os.environ.keys())
        if has_edison_project_env:
            return

        alias_map = {
            "PROJECT_NAME": ["project", "name"],
            "PROJECT_TERMS": ["project", "audit_terms"],
            "AGENTS_OWNER": ["project", "owner"],
        }

        for env_key, path in alias_map.items():
            if env_key not in os.environ:
                continue
            raw = os.environ[env_key]
            if env_key == "PROJECT_TERMS":
                value = [t.strip() for t in str(raw).split(",") if t.strip()]
            else:
                value = str(raw).strip()
            self._set_nested(cfg, path, value)

    def _apply_database_env_aliases(self, cfg: Dict[str, Any]) -> None:
        """Allow DATABASE_URL to populate database.url when no EDISON override is present."""
        has_explicit_database_env = any(k.startswith("EDISON_database__") for k in os.environ.keys())
        if has_explicit_database_env:
            return

        legacy_url = os.environ.get("DATABASE_URL")
        if legacy_url is None:
            return

        url = str(legacy_url).strip()
        if not url:
            return

        self._set_nested(cfg, ["database", "url"], url)

    def _load_config_uncached(
        self, validate: bool = True, include_packs: bool = True
    ) -> Dict[str, Any]:
        """Load and merge configuration from multiple sources (UNCACHED).

        Configuration uses two-phase loading:

        Phase 1 (Bootstrap): Determine active packs
            - core/*.yaml + project/*.yaml → packs.active

        Phase 2 (Full merge):
            1. Core config: edison.data/config/*.yaml (alphabetical order)
            2. Pack configs: bundled_packs/*/config/*.yaml + project_packs/*/config/*.yaml
            3. Project config: .edison/config/*.yaml (alphabetical order)
            4. Environment variable overrides (EDISON_*)

        Args:
            validate: If True, validate against JSON schema
            include_packs: If True, include pack config overlays (default: True)

        Returns:
            Merged configuration dictionary
        """
        with span("config.load_config.total", include_packs=include_packs, validate=validate):
            cfg: Dict[str, Any] = {}

            # Layer 1: Core config (bundled defaults)
            with span("config.load_config.core"):
                cfg = self._load_directory(self.core_config_dir, cfg)

            # Phase 1 bootstrap: Get active packs from core + project (without pack configs)
            if include_packs:
                with span("config.load_config.bootstrap"):
                    bootstrap_cfg = self._load_directory(self.project_config_dir, dict(cfg))
                    active_packs = self._get_bootstrap_packs(bootstrap_cfg)

                # Layer 2: Pack configs (bundled + project packs)
                if active_packs:
                    with span("config.load_config.packs", count=len(active_packs)):
                        cfg = self._load_pack_configs(cfg, active_packs)

            # Layer 3: Project config (always wins over packs)
            with span("config.load_config.project"):
                cfg = self._load_directory(self.project_config_dir, cfg)

            # Layer 4: Environment overrides
            with span("config.load_config.env"):
                self._apply_project_env_aliases(cfg)
                self._apply_database_env_aliases(cfg)
                self.apply_env_overrides(cfg, strict=validate)

            # Cross-key compatibility and canonicalization (kept minimal).
            self._apply_compat_shims(cfg)

            if validate:
                with span("config.load_config.validate"):
                    self.validate_schema(cfg, "config/config.schema.yaml")

            return cfg

    def _apply_compat_shims(self, cfg: Dict[str, Any]) -> None:
        """Apply small compatibility shims after merging config layers.

        Goal: keep a single canonical source of truth while maintaining backward
        compatibility with older key paths used by templates and scripts.
        """
        # Paths: canonical is paths.project_config_dir (bootstrap key for config root).
        # Backward-compatible aliases: paths.config_dir, paths.management_dir, management_dir.
        paths = cfg.get("paths") if isinstance(cfg.get("paths"), dict) else {}
        if paths.get("project_config_dir") in (None, "") and isinstance(paths.get("config_dir"), str):
            val = str(paths.get("config_dir")).strip()
            if val:
                paths["project_config_dir"] = val

        if cfg.get("project_management_dir") in (None, ""):
            mgmt = cfg.get("management_dir") or paths.get("management_dir")
            if isinstance(mgmt, str) and mgmt.strip():
                cfg["project_management_dir"] = mgmt.strip()

        cfg["paths"] = paths

        # Packs: canonical is packs.active (v2 object form). Compatibility shim for
        # older modular configs that wrote packs.enabled as a list of pack names.
        packs = cfg.get("packs") if isinstance(cfg.get("packs"), dict) else {}
        packs_active = packs.get("active")
        packs_enabled = packs.get("enabled")
        if isinstance(packs_enabled, list) and not isinstance(packs_active, list):
            packs["active"] = [str(p) for p in packs_enabled if p]
        cfg["packs"] = packs

        # Coverage thresholds: canonical is quality.coverage.overall/changed.
        # Backward-compatible alias: tdd.coverage_threshold.
        tdd = cfg.get("tdd") if isinstance(cfg.get("tdd"), dict) else {}
        quality = cfg.get("quality") if isinstance(cfg.get("quality"), dict) else {}
        coverage = quality.get("coverage") if isinstance(quality.get("coverage"), dict) else {}

        tdd_threshold = tdd.get("coverage_threshold")
        q_overall = coverage.get("overall")

        if q_overall is None and tdd_threshold is not None:
            coverage["overall"] = tdd_threshold
        if tdd_threshold is None and q_overall is not None:
            tdd["coverage_threshold"] = q_overall

        # Ensure changed/new coverage target exists (core default is 100).
        if coverage.get("changed") is None:
            coverage["changed"] = 100

        quality["coverage"] = coverage
        cfg["quality"] = quality
        cfg["tdd"] = tdd

    def load_config(
        self, validate: bool = True, include_packs: bool = True
    ) -> Dict[str, Any]:
        """Load configuration using centralized cache.

        This is the canonical entrypoint for configuration loads.
        Caching is centralized in `edison.core.config.cache`.

        Notes:
        - `validate=True` will validate the (cached) config before returning.
        - Returned dict should be treated as immutable.
        """
        cfg = get_cached_config(repo_root=self.repo_root, validate=False, include_packs=include_packs)
        if validate:
            # Fail-closed: strict parsing of env override paths when validate=True,
            # even if the base config dict came from cache.
            # This ensures malformed EDISON_* keys are detected deterministically.
            _ = list(self._iter_env_overrides(strict=True))
            with span("config.load_config.validate_cached"):
                self.validate_schema(cfg, "config/config.schema.yaml")
        return cfg

    # ========== Accessor Methods ==========

    def get_all(self, include_packs: bool = True) -> Dict[str, Any]:
        """Get full merged configuration.

        Args:
            include_packs: If True, include pack config overlays (default: True)

        Returns:
            Complete merged config dict
        """
        return self.load_config(validate=False, include_packs=include_packs)

    def get(
        self, key: str, default: Any = None, include_packs: bool = True
    ) -> Any:
        """Get a config value by dot-notation key.

        Args:
            key: Dot-notation key (e.g., 'project.name', 'paths.config_dir')
            default: Value to return if key not found
            include_packs: If True, include pack config overlays (default: True)

        Returns:
            Config value or default

        Example:
            >>> manager.get('project.name')
            'my-project'
            >>> manager.get('nonexistent.key', 'fallback')
            'fallback'
        """
        config = self.load_config(validate=False, include_packs=include_packs)
        parts = key.split(".")

        current = config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    # ========== Mutation Methods ==========

    def set(self, key: str, value: Any) -> None:
        """Stage a config change for later saving.
        
        Args:
            key: Dot-notation key (e.g., 'project.name')
            value: Value to set
            
        Note:
            Changes are not persisted until save() is called.
        """
        if not hasattr(self, "_staged_changes"):
            self._staged_changes: Dict[str, Any] = {}
        self._staged_changes[key] = value

    def save(self, target_file: Optional[str] = None) -> Path:
        """Write staged changes to the appropriate config file.
        
        Args:
            target_file: Specific file to write to (e.g., 'project.yml').
                        If None, determines file from key prefixes.
                        
        Returns:
            Path to the written file
            
        Raises:
            ValueError: If no changes staged or cannot determine target file
        """
        from edison.core.utils.io import write_yaml, ensure_directory
        
        if not hasattr(self, "_staged_changes") or not self._staged_changes:
            raise ValueError("No changes staged. Use set() first.")
        
        # Determine target file from staged keys
        if target_file is None:
            # Use first key's prefix to determine file
            first_key = next(iter(self._staged_changes.keys()))
            prefix = first_key.split(".")[0]
            target_file = self._get_file_for_section(prefix)
        
        # Ensure config directory exists
        ensure_directory(self.project_config_dir)
        
        target_path = self.project_config_dir / target_file
        
        # Load existing file content if it exists
        existing = self.load_yaml(target_path) if target_path.exists() else {}
        
        # Apply staged changes
        for key, value in self._staged_changes.items():
            parts = key.split(".")
            self._set_nested(existing, parts, value)
        
        # Write file
        write_yaml(target_path, existing)
        
        # Clear staged changes
        self._staged_changes = {}
        
        return target_path

    def _get_file_for_section(self, section: str) -> str:
        """Determine which config file a section belongs to.
        
        Args:
            section: Top-level config section name
            
        Returns:
            Filename for the section
        """
        section_file_map = {
            "paths": "defaults.yml",
            "project": "project.yml",
            "database": "defaults.yml",
            "auth": "defaults.yml",
            "packs": "packs.yml",
            "validators": "validators.yml",
            "validation": "validators.yml",
            "agents": "delegation.yml",
            "delegation": "delegation.yml",
            "orchestrators": "orchestrators.yml",
            "worktrees": "worktrees.yml",
            "workflow": "workflow.yml",
            "statemachine": "workflow.yml",
            "tdd": "tdd.yml",
            "ci": "ci.yml",
            "commands": "commands.yml",
            "hooks": "hooks.yml",
            "context7": "context7.yml",
            "session": "session.yml",
            "resilience": "defaults.yml",
            "timeouts": "defaults.yml",
        }
        return section_file_map.get(section, f"{section}.yml")


__all__ = ["ConfigManager"]
