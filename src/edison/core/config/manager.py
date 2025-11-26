"""
Edison Framework Configuration Management (YAML-only, no legacy fallbacks).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os
import json
import re

from edison.core.paths import PathResolver, EdisonPathError
from edison.core.paths.project import get_project_config_dir

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
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or self._find_repo_root()
        project_root_dir = get_project_config_dir(self.repo_root, create=False)

        core_config_dir = project_root_dir / "core" / "config"
        if core_config_dir.exists():
            self.core_config_dir = core_config_dir
        else:
            from edison.data import get_data_path
            self.core_config_dir = get_data_path("config")

        self.core_defaults_path = self.core_config_dir / "defaults.yaml"
        self.project_config_dir = project_root_dir / "config"

        edison_schemas_dir = project_root_dir / "core" / "schemas"
        if edison_schemas_dir.exists():
            self.schemas_dir = edison_schemas_dir
        else:
            from edison.data import get_data_path
            self.schemas_dir = get_data_path("config") / "schemas"

    def _find_repo_root(self) -> Path:
        try:
            return PathResolver.resolve_project_root()
        except EdisonPathError as exc:
            raise RuntimeError(str(exc)) from exc

    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = dict(base)
        for key, value in (override or {}).items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self.deep_merge(result[key], value)
                elif isinstance(result[key], list) and isinstance(value, list):
                    result[key] = self._merge_arrays(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    def _merge_arrays(self, base: List[Any], override: List[Any]) -> List[Any]:
        if not override:
            return base
        first = override[0]
        if isinstance(first, str):
            if first.startswith("+"):
                return [*base, *override[1:]]
            if first == "=":
                return list(override[1:])
        return list(override)

    def load_yaml(self, path: Path) -> Dict[str, Any]:
        from edison.core.file_io.utils import read_yaml_safe
        return read_yaml_safe(path, default={})

    def load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        from edison.core.file_io.utils import read_json_safe as io_read_json_safe
        data = io_read_json_safe(path)
        return data or {}

    def validate_schema(self, config: Dict[str, Any], schema_name: str) -> None:
        schema_path = self.schemas_dir / schema_name
        if not schema_path.exists():
            return
        schema = self.load_json(schema_path)
        jsonschema.validate(instance=config, schema=schema)

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
                processed.append(seg)
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

    def load_config(self, validate: bool = True) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}
        defaults_path = self.core_config_dir / "defaults.yaml"
        if defaults_path.exists():
            cfg = self.load_yaml(defaults_path)

        if self.core_config_dir.exists():
            for path in sorted(self.core_config_dir.glob("*.yaml")):
                if path.name == "defaults.yaml":
                    continue
                module_cfg = self.load_yaml(path)
                cfg = self.deep_merge(cfg, module_cfg)

        if self.project_config_dir.exists():
            for path in sorted(self.project_config_dir.glob("*.yml")):
                mod_cfg = self.load_yaml(path)
                cfg = self.deep_merge(cfg, mod_cfg)

        self._apply_project_env_aliases(cfg)
        self._apply_database_env_aliases(cfg)
        self.apply_env_overrides(cfg, strict=validate)
        if validate:
            self.validate_schema(cfg, "config.schema.json")

        return cfg


__all__ = ["ConfigManager"]
