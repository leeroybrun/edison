"""
Edison Framework Configuration Management (YAML-only, no legacy fallbacks).

Precedence (in increasing order):
  1) Core defaults and modules (``.edison/core/config/*.yaml``)
  2) Project overlays (``<project_config_dir>/config/*.yml``)
  3) Environment overrides (``EDISON_*``)

Environment overrides:
- Path separator: single underscore ``_`` (e.g., ``EDISON_tdd_enforcement=false``).
- Case handling: case-insensitive lookup against existing keys; preserves
  original key case when creating new keys to avoid breaking camelCase like
  ``worktrees.baseDirectory``.
- Type coercion: bool/int/float/JSON-like strings are coerced.

Strict policy:
- YAML only; no JSON config loading from legacy locations.
- Core config MUST live under ``.edison/core/config/*.yaml``.
- Project overlays MUST live under ``<project_config_dir>/config/*.yml``; legacy
  ``<project_config_dir>/config.yml`` is ignored for NO-LEGACY enforcement.
- No manifest/JSON fallbacks. See EDISON_NO_LEGACY_POLICY.md and the
  config-yaml-only migration notes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os
import json
import re

from .paths import PathResolver, EdisonPathError
from .paths.project import get_project_config_dir

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

    Typical usage:

    ```python
    from .lib.config import ConfigManager
    mgr = ConfigManager()
    cfg = mgr.load_config(validate=True)
    ```

    Attributes:
        repo_root: Repository root used to resolve config files.
        core_config_dir: Path to core config directory (``.edison/core/config``).
        core_defaults_path: Path to core defaults YAML under
            ``.edison/core/config/defaults.yaml``.
        project_config_dir: Path to project config directory
            (``<project_config_dir>/config``), where modular ``*.yml`` files are loaded.
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        """Create a manager rooted at ``repo_root``.

        Args:
            repo_root: Optional repository root. If ``None``, the repo is
                auto-discovered by walking up until a ``.git`` directory is
                found; otherwise current working directory is used.
        """
        self.repo_root = repo_root or self._find_repo_root()
        # Canonical core configuration directory
        # Fall back to packaged data if .edison/core/config doesn't exist
        edison_config_dir = self.repo_root / ".edison" / "core" / "config"
        if edison_config_dir.exists():
            self.core_config_dir = edison_config_dir
        else:
            # Use packaged data directory when running from installed package
            from edison.data import get_data_path
            self.core_config_dir = get_data_path("config")

        # Canonical defaults path lives inside the config directory
        self.core_defaults_path = self.core_config_dir / "defaults.yaml"
        # Resolves project configuration directory (.agents preferred, .edison fallback)
        project_root_dir = get_project_config_dir(self.repo_root)
        # Canonical project overlays (<dir>/config/*.yml)
        self.project_config_dir = project_root_dir / "config"

        # Schemas directory - also fall back to packaged data
        edison_schemas_dir = self.repo_root / ".edison" / "core" / "schemas"
        if edison_schemas_dir.exists():
            self.schemas_dir = edison_schemas_dir
        else:
            from edison.data import get_data_path
            self.schemas_dir = get_data_path("config") / "schemas"

    # ---------- Root detection ----------
    def _find_repo_root(self) -> Path:
        """Resolve repository root using the canonical PathResolver."""
        try:
            return PathResolver.resolve_project_root()
        except EdisonPathError as exc:  # pragma: no cover - defensive
            raise RuntimeError(str(exc)) from exc

    # ---------- Merge helpers ----------
    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge ``override`` into ``base`` returning a copy.

        Dicts are merged recursively. Lists support simple strategies:
        - If override list begins with a string starting with ``+``, append the
          remaining items to the base list.
        - If override list begins with ``=``, replace base with the remaining items.
        - Otherwise, replace the entire list with the override list.

        Args:
            base: Lower-precedence configuration.
            override: Higher-precedence configuration.

        Returns:
            Merged configuration dictionary (new object).
        """
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
        """Intelligently merge two arrays.

        Array merge strategies:
        - If first element of override is string starting with ``+``, append rest to base
        - If first element is ``=``, replace with rest
        - Otherwise, replace entire array

        Args:
            base: Base array
            override: Override array

        Returns:
            Merged array
        """
        if not override:
            return base
        first = override[0]
        if isinstance(first, str):
            if first.startswith("+"):
                return [*base, *override[1:]]
            if first == "=":
                return list(override[1:])
        return list(override)

    # ---------- IO helpers ----------
    def load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file into a dict.

        Args:
            path: YAML file path.

        Returns:
            Dict[str, Any]: Parsed YAML or an empty dict when the file does
            not exist.

        Raises:
            yaml.YAMLError: If the file exists but contains invalid YAML.
        """
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)  # type: ignore[no-untyped-call]
            return data or {}

    def load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON file safely (returns {} when missing/empty)."""
        if not path.exists():
            return {}
        from .io_utils import read_json_safe as io_read_json_safe
        data = io_read_json_safe(path)
        return data or {}

    # ---------- Validation ----------
    def validate_schema(self, config: Dict[str, Any], schema_name: str) -> None:
        """Validate configuration against a JSON schema file.

        Args:
            config: Configuration to validate.
            schema_name: Schema file name (e.g., ``edison.schema.json``).

        Raises:
            jsonschema.ValidationError: If validation fails.
        """
        schema_path = self.schemas_dir / schema_name
        if not schema_path.exists():  # soft warning (framework must run even when schema absent)
            print(f"Warning: Schema {schema_name} not found at {schema_path}")
            return
        schema = self.load_json(schema_path)
        jsonschema.validate(instance=config, schema=schema)  # type: ignore[no-untyped-call]

    # ---------- (removed) pack overrides ----------
    # Packs are no longer layered into configuration per NO-LEGACY policy.

    # ---- C1: Environment override parsing with arrays/deep objects ----
    ARRAY_APPEND_MARKER = object()

    # ---------- Type coercion helpers (extracted to reduce complexity) ----------
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
        """Coerce string to bool/int/float/JSON when appropriate (C3).

        Args:
            value: Raw environment string value.

        Returns:
            Best-effort typed value. Falls back to the original string when
            no coercion applies.
        """
        for caster in (self._as_bool, self._as_int, self._as_float, self._as_json):
            result = caster(value)
            if result is not None:
                return result
        return value.strip()

    def _parse_env_key(self, raw: str, *, strict: bool) -> List[Union[str, int, object]]:
        """Parse the tail of an ``EDISON_*`` key into path components.

        Segments are separated by double underscores ``__``. For backwards
        compatibility, keys without ``__`` fall back to single-underscore
        separation (e.g., ``tdd_enforceRedGreenRefactor``).
        Numeric segments become integer list indices; ``APPEND`` becomes
        :pyattr:`ARRAY_APPEND_MARKER`. Other segments keep their original case
        to allow camelCase keys (e.g., ``worktrees``, ``baseDirectory``).

        Args:
            raw: The substring after ``EDISON_`` (e.g. ``tdd_enforcement``).
            strict: When ``True``, raise on malformed sequences; when
                ``False``, return an empty list to signal skip.

        Returns:
            List of components (str/int/marker). May be empty when
            ``strict`` is ``False`` and the key is malformed.
        """
        if not raw:
            return []
        # Prefer new-style double-underscore separators; fall back to single
        # underscores when no ``__`` is present to support existing keys.
        segs = raw.split("__") if "__" in raw else raw.split("_")
        processed: List[Union[str, int, object]] = []
        for seg in segs:
            if seg == "":
                if strict:
                    raise ValueError(
                        f"Malformed EDISON_* key: empty segment in '{raw}'. Use double underscores between parts."
                    )
                return []
            if seg.isdigit():
                processed.append(int(seg))
            elif seg.upper() == "APPEND":
                processed.append(self.ARRAY_APPEND_MARKER)
            else:
                processed.append(seg)
        return processed

    # ---------- Env iteration (shared between loaders) ----------
    def _iter_env_overrides(self, *, strict: bool):
        """Yield parsed environment overrides as (path, value, raw_key).

        Args:
            strict: When True, malformed keys raise; when False, they are
                skipped.

        Yields:
            Tuple[path_components, typed_value, raw_key]
        """
        prefix = "EDISON_"
        for key in sorted(os.environ.keys()):
            if not key.startswith(prefix):
                continue
            raw = key[len(prefix) :]
            if not raw:
                if strict:
                    raise ValueError("Malformed EDISON_* key: empty tail after prefix")
                continue
            path = self._parse_env_key(raw, strict=strict)
            if not path:
                continue
            yield path, self._coerce_type(os.environ[key]), raw

    def _set_nested(self, root: Dict[str, Any], path: List[Union[str, int, object]], value: Any) -> None:
        """Set a nested value into ``root`` creating containers as needed.

        Note: When creating NEW keys from environment variables, the original
        casing is PRESERVED. For example, ``EDISON_QUALITY__LEVEL`` produces
        ``{\"quality\": {\"LEVEL\": ...}}`` (not ``{\"quality\": {\"level\": ...}}``).
        This keeps env var semantics intact while still allowing case-insensitive
        lookups when the key already exists in YAML.

        Args:
            root: Configuration dict to mutate.
            path: Parsed path (strings for dict keys, ints for list indices,
                or ``ARRAY_APPEND_MARKER`` at the leaf to append).
            value: Value to assign (already type-coerced).

        Raises:
            ValueError: When the path attempts invalid operations (e.g.,
                assigning an index into a non-list container). Error messages
                include the path to aid troubleshooting.
        """
        if not path:
            return

        def _path_str(p: List[Union[str, int, object]]) -> str:
            out: List[str] = []
            for seg in p:
                out.append("APPEND" if seg is self.ARRAY_APPEND_MARKER else str(seg))
            return "__".join(out)

        def _assign_leaf(container: Any, leaf: Union[str, int, object], val: Any) -> None:
            if leaf is self.ARRAY_APPEND_MARKER:
                if not isinstance(container, list):
                    raise ValueError(
                        f"APPEND requires list at leaf (path='{_path_str(path)}', "
                        f"got {type(container).__name__})"
                    )
                container.append(val)
                return
            if isinstance(leaf, int):
                if not isinstance(container, list):
                    raise ValueError(
                        f"Index assignment requires list (path='{_path_str(path)}', "
                        f"got {type(container).__name__})"
                    )
                while len(container) <= leaf:
                    container.append(None)
                container[leaf] = val
                return
            # dict key (case-insensitive replacement when key exists)
            if not isinstance(container, dict):
                raise ValueError(
                    f"Key assignment requires dict (path='{_path_str(path)}', "
                    f"got {type(container).__name__})"
                )
            if isinstance(leaf, str):
                lower_map = {k.lower(): k for k in container.keys() if isinstance(k, str)}
                use_key = lower_map.get(leaf.lower(), leaf)
            else:
                use_key = leaf
            container[use_key] = val

        def _navigate_to_parent(container: Any, p: List[Union[str, int, object]]) -> tuple[Any, Union[str, int, object]]:
            """Return (parent_container, leaf) ready for assignment.

            Creates intermediate dict/list containers as necessary.
            """
            cur = container
            for i, part in enumerate(p):
                is_last = i == len(p) - 1
                if is_last:
                    return cur, part
                nxt = p[i + 1]
                if isinstance(part, int) or part is self.ARRAY_APPEND_MARKER:
                    raise ValueError(
                        f"Invalid path: list index/APPEND may only appear at leaf (path='{_path_str(p)}')"
                    )
                if not isinstance(cur, dict):
                    raise ValueError(
                        f"Path traverses non-dict container (path='{_path_str(p)}', got {type(cur).__name__})"
                    )
                # Case-insensitive lookup to match existing keys while preserving case
                key_candidates = {k.lower(): k for k in cur.keys() if isinstance(k, str)}
                key_to_use = key_candidates.get(str(part).lower(), part)
                if key_to_use not in cur:
                    cur[key_to_use] = [] if (isinstance(nxt, int) or nxt is self.ARRAY_APPEND_MARKER) else {}
                cur = cur[key_to_use]
            # Unreachable due to return on last
            return cur, p[-1]

        parent, leaf = _navigate_to_parent(root, path)
        _assign_leaf(parent, leaf, value)

    def _load_env_overrides(self, *, strict: bool) -> Dict[str, Any]:
        """Build a dictionary from ``EDISON_*`` environment variables.

        Unlike :meth:`apply_env_overrides`, this does not modify an existing
        config. It is primarily used for diagnostics (e.g., ``--show-sources``).

        Args:
            strict: When ``True``, malformed keys raise ``ValueError``.

        Returns:
            Dict[str, Any]: Overrides constructed solely from environment.
        """
        overrides: Dict[str, Any] = {}
        for path, typed_value, raw in self._iter_env_overrides(strict=strict):
            try:
                self._set_nested(overrides, path, typed_value)
            except ValueError:
                if strict:
                    raise
                # Non-strict: skip invalid shapes silently to remain fail-safe.
        return overrides

    def apply_env_overrides(self, cfg: Dict[str, Any], *, strict: bool) -> None:
        """Apply ``EDISON_*`` overrides in-place to ``cfg``.

        This respects list ``APPEND`` semantics that cannot be achieved with a
        post-hoc deep merge.

        Args:
            cfg: Configuration dict to mutate.
            strict: When ``True``, malformed keys raise ``ValueError``.
        """
        for path, typed_value, raw in self._iter_env_overrides(strict=strict):
            self._set_nested(cfg, path, typed_value)

    def load_config(self, validate: bool = True) -> Dict[str, Any]:
        """Load configuration with correct precedence and optional validation.

        Precedence (lowest → highest): defaults → project → env.

        Args:
            validate: When ``True`` (default), validate the merged configuration
                against the canonical Draft-2020-12 config schema and treat
                malformed env keys as errors. Set to ``False`` only for
                diagnostics or migration tooling where strict validation would
                be counter-productive.

        Returns:
            Dict[str, Any]: Fully merged configuration.
        """
        cfg: Dict[str, Any] = {}

        # Layer 1: Core Defaults (Modular)
        # 1a. Load defaults.yaml from .edison/core/config/ first (if it exists)
        defaults_path = self.core_config_dir / "defaults.yaml"
        if defaults_path.exists():
            cfg = self.load_yaml(defaults_path)

        # 1b. Load all other core modules in alphabetical order
        if self.core_config_dir.exists():
            for path in sorted(self.core_config_dir.glob("*.yaml")):
                if path.name == "defaults.yaml":
                    continue
                module_cfg = self.load_yaml(path)
                cfg = self.deep_merge(cfg, module_cfg)

        # Layer 2: Project Overrides
        # 2a. Modular <project_config_dir>/config/*.yml (canonical project overlays)
        if self.project_config_dir.exists():
            # Load .yml overlays in sorted order; .yaml is intentionally
            # ignored for NO-LEGACY enforcement.
            for path in sorted(self.project_config_dir.glob("*.yml")):
                mod_cfg = self.load_yaml(path)
                cfg = self.deep_merge(cfg, mod_cfg)

        # Layer 3: Environment overrides (apply in-place)
        self.apply_env_overrides(cfg, strict=validate)

        # Optional: validate against unified config schema when available
        if validate:
            # Canonical project-agnostic configuration schema
            self.validate_schema(cfg, "config.schema.json")

        return cfg


__all__ = ["ConfigManager"]
