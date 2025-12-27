<!-- TaskID: 2405-wuni-003-output-path-resolver -->
<!-- Priority: 2405 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: refactor -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: codex -->
<!-- ParallelGroup: wave5-sequential -->
<!-- EstimatedHours: 4 -->
<!-- DependsOn: 2403-wuni-001 -->
<!-- BlocksTask: none -->

# WUNI-003: Unify OutputConfigLoader and CompositionPathResolver

## Summary
Merge the overlapping functionality of `OutputConfigLoader` and `CompositionPathResolver` into a unified `OutputPathResolver` that provides a single source of truth for ALL path resolution in the composition system.

## Problem Statement

### Current Overlap
Two separate classes resolve paths independently:

**CompositionPathResolver** (core/paths.py):
- Resolves: repo_root, project_dir, core_dir, packs_dir
- Source: PathResolver + get_project_config_dir()
- Returns: ResolvedPaths dataclass

**OutputConfigLoader** (output/config.py):
- Resolves: repo_root, project_config_dir
- Also: Loads composition.yaml and resolves output paths
- Also: Handles `{{PROJECT_EDISON_DIR}}` placeholders

### Duplicated Code

```python
# CompositionPathResolver (core/paths.py:85-90)
self.repo_root = repo_root or PathResolver.resolve_project_root()
project_dir = get_project_config_dir(self.repo_root, create=False)

# OutputConfigLoader (output/config.py:57-58)
self.repo_root = repo_root or PathResolver.resolve_project_root()
self.project_config_dir = project_config_dir or get_project_config_dir(self.repo_root)
```

### Additional Placeholder Duplication

```python
# path_utils.py - Complex relative path resolution
def _project_dir_replacement(project_dir, target_path, repo_root):
    # 40+ lines of complex logic

# OutputConfigLoader._resolve_path() - Simple replacement
def _resolve_path(self, path_template: str) -> Path:
    resolved = path_template.replace("{{PROJECT_EDISON_DIR}}", str(self.project_config_dir))
```

## Objectives
- [ ] Create unified `OutputPathResolver` class
- [ ] Use `CompositionPathResolver` internally for base paths
- [ ] Consolidate placeholder resolution
- [ ] Update all adapters to use unified resolver
- [ ] Remove duplicate path resolution code

## Proposed Design

### OutputPathResolver Class

```python
"""Unified output path resolution for Edison composition."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .core.paths import CompositionPathResolver
from ..utils.io import read_yaml
from ..utils.merge import deep_merge
from edison.data import get_data_path


class OutputPathResolver:
    """Unified path resolution combining base paths + output configuration.

    Combines:
    - CompositionPathResolver for base paths (core_dir, packs_dir, project_dir)
    - composition.yaml output configuration
    - Placeholder resolution ({{PROJECT_EDISON_DIR}})

    Usage:
        resolver = OutputPathResolver(repo_root)

        # Base paths (from CompositionPathResolver)
        resolver.project_dir
        resolver.core_dir
        resolver.packs_dir

        # Output paths (from composition.yaml)
        resolver.get_agents_dir()
        resolver.get_validators_dir()
        resolver.get_constitution_path("orchestrators")

        # Client paths
        resolver.get_client_path("claude")  # Returns .claude/CLAUDE.md path

        # Placeholder resolution
        resolver.resolve_template("{{PROJECT_EDISON_DIR}}/_generated/agents")
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        content_type: Optional[str] = None,
    ) -> None:
        # Use CompositionPathResolver for base paths (SINGLE SOURCE OF TRUTH)
        self._path_resolver = CompositionPathResolver(repo_root, content_type)

        # Expose base paths
        self.repo_root = self._path_resolver.repo_root
        self.project_dir = self._path_resolver.project_dir
        self.core_dir = self._path_resolver.core_dir
        self.packs_dir = self._path_resolver.packs_dir

        # Load output configuration
        self._config: Optional[Dict[str, Any]] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load composition.yaml with core defaults + project overrides."""
        if self._config is not None:
            return self._config

        # Load core defaults
        core_config_path = get_data_path("config", "composition.yaml")
        core_config = read_yaml(core_config_path, default={})

        # Load project overrides
        project_config_path = self.project_dir / "composition.yaml"
        if project_config_path.exists():
            project_config = read_yaml(project_config_path, default={})
            self._config = deep_merge(core_config, project_config)
        else:
            self._config = core_config

        return self._config

    def resolve_template(
        self,
        template: str,
        *,
        target_path: Optional[Path] = None,
    ) -> Path:
        """Resolve path template with placeholders.

        Handles:
        - {{PROJECT_EDISON_DIR}} - Replaced with project_dir
        - Relative paths - Resolved from repo_root

        Args:
            template: Path template string
            target_path: Optional target for relative path calculation

        Returns:
            Resolved absolute Path
        """
        if "{{PROJECT_EDISON_DIR}}" in template:
            if target_path is not None:
                # Use complex relative resolution
                from .path_utils import resolve_project_dir_placeholders
                resolved = resolve_project_dir_placeholders(
                    template,
                    project_dir=self.project_dir,
                    target_path=target_path,
                    repo_root=self.repo_root,
                )
                return Path(resolved)
            else:
                # Simple replacement
                resolved = template.replace(
                    "{{PROJECT_EDISON_DIR}}",
                    str(self.project_dir)
                )
                path = Path(resolved)
                if not path.is_absolute():
                    path = self.repo_root / path
                return path

        path = Path(template)
        if not path.is_absolute():
            path = self.repo_root / path
        return path

    # --- Output Directory Methods ---

    def get_outputs_config(self) -> Dict[str, Any]:
        """Get the full outputs configuration."""
        return self._load_config().get("outputs", {})

    def get_agents_dir(self) -> Optional[Path]:
        """Get resolved directory for agent files."""
        cfg = self.get_outputs_config().get("agents", {})
        if not cfg.get("enabled", True):
            return None
        output_path = cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/agents")
        return self.resolve_template(output_path)

    def get_validators_dir(self) -> Optional[Path]:
        """Get resolved directory for validator files."""
        cfg = self.get_outputs_config().get("validators", {})
        if not cfg.get("enabled", True):
            return None
        output_path = cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/validators")
        return self.resolve_template(output_path)

    def get_guidelines_dir(self) -> Optional[Path]:
        """Get resolved directory for guideline files."""
        cfg = self.get_outputs_config().get("guidelines", {})
        if not cfg.get("enabled", True):
            return None
        output_path = cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/guidelines")
        return self.resolve_template(output_path)

    def get_constitution_path(self, role: str) -> Optional[Path]:
        """Get resolved path for a constitution file."""
        cfg = self.get_outputs_config().get("constitutions", {})
        if not cfg.get("enabled", True):
            return None

        files = cfg.get("files", {})
        role_cfg = files.get(role, {})
        if not role_cfg.get("enabled", True):
            return None

        output_dir = self.resolve_template(
            cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/constitutions")
        )
        filename = role_cfg.get("filename", f"{role.upper()}.md")
        return output_dir / filename

    # --- Client Path Methods ---

    def get_client_path(self, client_name: str) -> Optional[Path]:
        """Get resolved path for a client output file (e.g., CLAUDE.md)."""
        cfg = self.get_outputs_config().get("clients", {}).get(client_name, {})
        if not cfg.get("enabled", False):
            return None
        output_dir = self.resolve_template(cfg.get("output_path", f".{client_name}"))
        filename = cfg.get("filename", f"{client_name.upper()}.md")
        return output_dir / filename

    # --- Sync Path Methods ---

    def get_sync_agents_dir(self, client_name: str) -> Optional[Path]:
        """Get resolved directory for synced agent files."""
        sync_cfg = self.get_outputs_config().get("sync", {}).get(client_name, {})
        if not sync_cfg.get("enabled", False):
            return None
        agents_path = sync_cfg.get("agents_path")
        if not agents_path:
            return None
        return self.resolve_template(agents_path)


# Convenience function
def get_output_path_resolver(repo_root: Optional[Path] = None) -> OutputPathResolver:
    """Get an OutputPathResolver instance."""
    return OutputPathResolver(repo_root=repo_root)
```

## Files to Create/Modify

### Create
```
src/edison/core/composition/output/resolver.py   # OutputPathResolver
tests/unit/composition/output/test_resolver.py   # Tests
```

### Modify
```
# Remove duplicate path resolution from:
src/edison/core/composition/output/config.py     # Simplify, use OutputPathResolver

# Update adapters to use unified resolver:
src/edison/core/adapters/sync/claude.py
src/edison/core/adapters/sync/cursor.py
src/edison/core/adapters/prompt/zen.py
src/edison/core/adapters/prompt/cursor.py
```

## Migration Pattern

### Before (scattered)
```python
# Claude adapter
from edison.core.utils.paths import get_project_config_dir
self.project_config_dir = get_project_config_dir(self.repo_root)
output_loader = OutputConfigLoader(repo_root=self.repo_root)
agents_dir = output_loader.get_agents_dir()

# Cursor adapter
path_resolver = CompositionPathResolver(repo_root, "validators")
self.core_dir = path_resolver.core_dir
```

### After (unified)
```python
# All adapters
from edison.core.composition.output import OutputPathResolver

resolver = OutputPathResolver(repo_root)
agents_dir = resolver.get_agents_dir()
validators_dir = resolver.get_validators_dir()
claude_md_path = resolver.get_client_path("claude")
```

## Backward Compatibility

Keep `OutputConfigLoader` as a thin wrapper for backward compatibility:

```python
class OutputConfigLoader:
    """Backward-compatible wrapper around OutputPathResolver.

    Deprecated: Use OutputPathResolver directly.
    """

    def __init__(self, repo_root: Optional[Path] = None, project_config_dir: Optional[Path] = None):
        self._resolver = OutputPathResolver(repo_root)
        # Ignore project_config_dir - resolved internally

    def get_agents_dir(self) -> Optional[Path]:
        return self._resolver.get_agents_dir()

    def get_validators_dir(self) -> Optional[Path]:
        return self._resolver.get_validators_dir()

    # ... delegate all methods to _resolver
```

## Verification Checklist
- [ ] OutputPathResolver created
- [ ] Uses CompositionPathResolver internally
- [ ] Placeholder resolution works correctly
- [ ] All output path methods work
- [ ] Adapters updated to use unified resolver
- [ ] OutputConfigLoader is thin wrapper
- [ ] Tests pass

## Success Criteria
1. Single `OutputPathResolver` for ALL path resolution
2. Uses `CompositionPathResolver` internally (no duplication)
3. Placeholder resolution unified
4. Adapters use consistent path resolution
5. Backward compatibility via wrapper

## Related Files
- `src/edison/core/composition/core/paths.py` - CompositionPathResolver
- `src/edison/core/composition/output/config.py` - OutputConfigLoader (to wrap)
- `src/edison/core/composition/path_utils.py` - Placeholder resolution
- All adapter files
