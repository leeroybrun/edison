"""
Edison Framework Configuration Management (YAML-only, no legacy fallbacks).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import os
import json
import re
import logging

from edison.core.utils.merge import deep_merge as _deep_merge, merge_arrays
from edison.data import get_data_path
from edison.core.utils.profiling import span
from edison.core.config.cache import get_cached_config

# Module logger (warnings are user-visible via CLI log config).
logger = logging.getLogger(__name__)

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
    2. Project-local config: <project-config-dir>/config.local/*.yaml (alphabetical order, uncommitted)
    3. Project config: <project-config-dir>/config/*.yaml (alphabetical order)
    4. User config: <user-config-dir>/config/*.yaml (alphabetical order)
    5. Pack configs: bundled_packs/*/config/*.yaml + user_packs/*/config/*.yaml + project_packs/*/config/*.yaml
    4. Bundled defaults: edison.data/config/*.yaml (alphabetical order)

    Pack-aware loading uses two phases:
    - Phase 1 (Bootstrap): core > user > project > project-local to determine packs.active
    - Phase 2 (Full): core > packs > user > project > project-local

    All YAML files are loaded and merged - no special handling for defaults.yaml.
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or self._find_repo_root()

        # Lazy import to avoid circular dependencies
        from edison.core.utils.paths import get_project_config_dir
        project_root_dir = get_project_config_dir(self.repo_root, create=False)
        from edison.core.utils.paths import get_user_config_dir
        user_root_dir = get_user_config_dir(create=False)

        # Bundled defaults from edison.data package (always available)
        self.core_config_dir = get_data_path("config")

        # User-specific config overlays (e.g. ~/.edison/config)
        self.user_config_dir = user_root_dir / "config"

        # Project-specific config overrides
        self.project_config_dir = project_root_dir / "config"
        # Project-local config overrides (uncommitted; per-user per-project)
        self.project_local_config_dir = project_root_dir / "config.local"

        # Pack directories
        self.bundled_packs_dir = get_data_path("packs")
        self.user_packs_dir = user_root_dir / "packs"
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
        from edison.core.utils.layered_yaml import merge_yaml_directory

        return merge_yaml_directory(cfg, directory)

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
        """Load config from active packs across pack roots.

        Pack configs are loaded in low→high precedence order across pack roots.
        Default roots are bundled → user → project, but tests (and future layers)
        can inject additional roots via `self._pack_roots`.

        Args:
            cfg: Base configuration to merge into
            active_packs: List of active pack names

        Returns:
            Configuration with pack overlays merged
        """
        roots = self._iter_pack_roots()

        for pack_name in active_packs:
            for root in roots:
                pack_config_dir = root.path / pack_name / "config"
                cfg = self._load_directory(pack_config_dir, cfg)

        return cfg

    def _find_user_only_packs(self, active_packs: List[str]) -> List[str]:
        """Return packs that resolve only from the user packs directory."""
        user_only: List[str] = []
        roots = self._iter_pack_roots()

        for pack_name in active_packs:
            present = {r.kind for r in roots if (r.path / pack_name).exists()}
            if present == {"user"}:
                user_only.append(pack_name)

        return user_only

    def _find_missing_packs(self, active_packs: List[str]) -> List[str]:
        """Return packs that do not exist in any pack root (bundled/user/project)."""
        missing: List[str] = []

        roots = self._iter_pack_roots()

        for pack_name in active_packs:
            if not any((r.path / pack_name).exists() for r in roots):
                missing.append(pack_name)

        return missing

    def _iter_pack_roots(self):
        """Return pack roots in low→high precedence order.

        Default roots are bundled → user → project. Tests (and future layers)
        can inject additional roots via `self._pack_roots`.
        """
        from edison.core.packs.paths import PackRoot

        roots = getattr(self, "_pack_roots", None)
        if roots is not None:
            return roots

        return (
            PackRoot(kind="bundled", path=Path(self.bundled_packs_dir)),
            PackRoot(kind="user", path=Path(self.user_packs_dir)),
            PackRoot(kind="project", path=Path(self.project_packs_dir)),
        )

    def _packs_portability_user_only_mode(self, cfg: Dict[str, Any]) -> str:
        packs = cfg.get("packs") if isinstance(cfg.get("packs"), dict) else {}
        portability = packs.get("portability") if isinstance(packs.get("portability"), dict) else {}
        raw = portability.get("userOnly", portability.get("user_only", "warn"))
        mode = str(raw).strip().lower() if raw is not None else "warn"

        if mode in {"warn", "warning"}:
            return "warn"
        if mode in {"error", "fail", "fatal"}:
            return "error"
        if mode in {"off", "none", "false", "0"}:
            return "off"
        return "warn"

    def _packs_portability_missing_mode(self, cfg: Dict[str, Any]) -> str:
        packs = cfg.get("packs") if isinstance(cfg.get("packs"), dict) else {}
        portability = packs.get("portability") if isinstance(packs.get("portability"), dict) else {}
        raw = portability.get("missing", "warn")
        mode = str(raw).strip().lower() if raw is not None else "warn"

        if mode in {"warn", "warning"}:
            return "warn"
        if mode in {"error", "fail", "fatal"}:
            return "error"
        if mode in {"off", "none", "false", "0"}:
            return "off"
        return "warn"

    def _enforce_pack_portability(self, cfg: Dict[str, Any], *, active_packs: List[str]) -> None:
        """Warn/error when active packs are resolved only from the user layer."""
        missing = self._find_missing_packs(active_packs)
        missing_mode = self._packs_portability_missing_mode(cfg)
        if missing and missing_mode != "off":
            if missing_mode == "error":
                packs_list = ", ".join(sorted(missing))
                raise RuntimeError(
                    "Pack portability check failed: active pack(s) were not found in bundled, user, or project packs: "
                    f"{packs_list}."
                )
            for pack_name in missing:
                logger.warning(
                    "Active pack '%s' was not found in bundled, user, or project packs. "
                    "This pack will be ignored.",
                    pack_name,
                )

        user_only = self._find_user_only_packs(active_packs)
        if not user_only:
            return

        mode = self._packs_portability_user_only_mode(cfg)
        if mode == "off":
            return

        if mode == "error":
            packs_list = ", ".join(sorted(user_only))
            raise RuntimeError(
                "Pack portability check failed: active pack(s) resolve only from the user packs directory: "
                f"{packs_list}. "
                "To make the project reproducible, vendor the pack into project packs, "
                "or install the pack for all users/CI, or relax packs.portability.userOnly."
            )

        for pack_name in user_only:
            logger.warning(
                "Active pack '%s' is resolved only from the user packs directory (%s). "
                "This project may not be reproducible for other users/CI unless they install the pack.",
                pack_name,
                str(Path(self.user_packs_dir) / pack_name),
            )

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
            3. Project config: <project-config-dir>/config/*.yaml (alphabetical order)
            4. Environment variable overrides (EDISON_*)

        Args:
            validate: If True, validate against JSON schema
            include_packs: If True, include pack config overlays (default: True)

        Returns:
            Merged configuration dictionary
        """
        with span("config.load_config.total", include_packs=include_packs, validate=validate):
            cfg: Dict[str, Any] = {}
            active_packs: List[str] = []

            # Layer 1: Core config (bundled defaults)
            with span("config.load_config.core"):
                cfg = self._load_directory(self.core_config_dir, cfg)

            # Phase 1 bootstrap: Get active packs from core + project (without pack configs)
            if include_packs:
                with span("config.load_config.bootstrap"):
                    bootstrap_cfg = dict(cfg)
                    bootstrap_cfg = self._load_directory(self.user_config_dir, bootstrap_cfg)
                    bootstrap_cfg = self._load_directory(self.project_config_dir, bootstrap_cfg)
                    bootstrap_cfg = self._load_directory(self.project_local_config_dir, bootstrap_cfg)
                    active_packs = self._get_bootstrap_packs(bootstrap_cfg)

                # Layer 2: Pack configs (bundled + project packs)
                if active_packs:
                    with span("config.load_config.packs", count=len(active_packs)):
                        cfg = self._load_pack_configs(cfg, active_packs)

            # Layer 3: User config (wins over packs)
            with span("config.load_config.user"):
                cfg = self._load_directory(self.user_config_dir, cfg)

            # Layer 4: Project config (wins over user)
            with span("config.load_config.project"):
                cfg = self._load_directory(self.project_config_dir, cfg)

            # Layer 5: Project-local config (wins over committed project config)
            with span("config.load_config.project_local"):
                cfg = self._load_directory(self.project_local_config_dir, cfg)

            # Layer 6: Environment overrides
            with span("config.load_config.env"):
                self._apply_project_env_aliases(cfg)
                self._apply_database_env_aliases(cfg)
                self.apply_env_overrides(cfg, strict=validate)

            # Cross-key compatibility and canonicalization (kept minimal).
            self._apply_compat_shims(cfg)

            # Expand runtime config tokens (single-brace `{PROJECT_*}` only).
            # This must run after all layering and compatibility shims so tokens
            # can reference canonicalized config values.
            self._apply_token_interpolation(cfg)

            # Post-merge checks that depend on the final config.
            if include_packs and active_packs:
                self._enforce_pack_portability(cfg, active_packs=active_packs)

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

        # Validation execution defaults: keep `validation.execution.*` consistent with
        # `orchestration.*` settings used by runtime QA workflows.
        #
        # Canonical runtime keys:
        # - orchestration.maxConcurrentAgents
        # - orchestration.validatorTimeout
        # - orchestration.executionMode
        #
        # Canonical documentation/config keys (historical):
        # - validation.execution.concurrency
        # - validation.execution.timeout
        # - validation.execution.mode
        orchestration = cfg.get("orchestration") if isinstance(cfg.get("orchestration"), dict) else {}
        validation = cfg.get("validation") if isinstance(cfg.get("validation"), dict) else {}
        execution = validation.get("execution") if isinstance(validation.get("execution"), dict) else {}

        orch_concurrency = orchestration.get("maxConcurrentAgents")
        exec_concurrency = execution.get("concurrency")
        if orch_concurrency is not None:
            execution["concurrency"] = int(orch_concurrency)
        elif exec_concurrency is not None:
            orchestration["maxConcurrentAgents"] = int(exec_concurrency)

        orch_timeout = orchestration.get("validatorTimeout")
        exec_timeout = execution.get("timeout")
        if orch_timeout is not None:
            execution["timeout"] = int(orch_timeout)
        elif exec_timeout is not None:
            orchestration["validatorTimeout"] = int(exec_timeout)

        orch_mode = orchestration.get("executionMode")
        exec_mode = execution.get("mode")
        if orch_mode is not None:
            execution["mode"] = str(orch_mode)
        elif exec_mode is not None:
            orchestration["executionMode"] = str(exec_mode)

        validation["execution"] = execution
        cfg["validation"] = validation
        cfg["orchestration"] = orchestration

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

    def _apply_token_interpolation(self, cfg: Dict[str, Any]) -> None:
        """Expand runtime config `{TOKEN}` placeholders throughout merged config.

        Edison composition templates use `{{...}}` and MUST NOT be mutated by
        config interpolation. The interpolation implementation only expands
        single-brace tokens via `edison.core.config.tokens`.
        """
        from edison.core.config.tokens import build_tokens, interpolate

        tokens = build_tokens(self.repo_root, cfg)
        interpolate(cfg, tokens)

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
        # When callers monkeypatch ConfigManager's directory attributes (common in
        # tests), the global cache cannot safely be reused because it would ignore
        # those overrides (cache loads via a fresh ConfigManager instance).
        #
        # Default behaviour remains centrally cached for production.
        try:
            from edison.data import get_data_path
            from edison.core.utils.paths import get_project_config_dir

            project_root_dir = get_project_config_dir(self.repo_root, create=False)
            defaults = {
                "core_config_dir": get_data_path("config"),
                "bundled_packs_dir": get_data_path("packs"),
                "schemas_dir": get_data_path("schemas"),
                "project_config_dir": project_root_dir / "config",
                "project_packs_dir": project_root_dir / "packs",
            }
            overridden = any(
                getattr(self, key) != val for key, val in defaults.items()  # type: ignore[arg-type]
            )
        except Exception:
            overridden = False

        if overridden:
            cfg = self._load_config_uncached(validate=False, include_packs=include_packs)
        else:
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
