<!-- TaskID: 2403-wuni-001-composition-base-class -->
<!-- Priority: 2403 -->
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
<!-- EstimatedHours: 8 -->
<!-- DependsOn: 2402-wtpl-002 -->
<!-- BlocksTask: 2404-wuni-002, 2405-wuni-003 -->

# WUNI-001: Create Unified CompositionBase Class

## Summary
Extract a shared `CompositionBase` class that unifies the common functionality between `BaseRegistry` and `IDEComposerBase`. Both hierarchies independently implement the same patterns: path resolution, config loading, active packs access, and three-layer composition.

## Problem Statement

### Current Duplication
Two separate inheritance hierarchies evolved independently with duplicated logic:

**BaseRegistry hierarchy** (entity-based):
- Location: `edison/core/entity/registry.py`
- Used by: AgentRegistry, ValidatorRegistry, GuidelineRegistry, RulesRegistry

**IDEComposerBase hierarchy** (ide-based):
- Location: `edison/core/composition/ide/base.py`
- Used by: HookComposer, CommandComposer, SettingsComposer, CodeRabbitComposer

### Duplicated Patterns

| Pattern | BaseRegistry | IDEComposerBase | Duplicated Lines |
|---------|--------------|-----------------|------------------|
| Path init | `PathResolver.resolve_project_root()` | `PathResolver.resolve_project_root()` | ~10 |
| Project dir | `get_project_config_dir()` | `get_project_config_dir()` | ~5 |
| Config loading | Manual in subclasses | `ConfigManager` in __init__ | ~15 |
| Active packs | Parameter-based | Lazy property | ~10 |
| YAML loading | None | `_load_yaml_safe()` | ~20 |
| Definition merging | None | `_merge_definitions()` | ~30 |

**Total duplication: ~90+ lines**

## Objectives
- [ ] Create `CompositionBase` class in `composition/base.py`
- [ ] Extract common initialization (paths, config, packs)
- [ ] Provide `_setup_composition_dirs()` extension point
- [ ] Update `BaseRegistry` to extend `CompositionBase`
- [ ] Update `IDEComposerBase` to extend `CompositionBase`
- [ ] Maintain backward compatibility

## Proposed Architecture

### New Class Hierarchy

```
CompositionBase (NEW - composition/base.py)
├── BaseRegistry (entity/registry.py)
│   ├── AgentRegistry
│   ├── ValidatorRegistry
│   ├── GuidelineRegistry
│   ├── RulesRegistry
│   └── FilePatternRegistry
└── IDEComposerBase (composition/ide/base.py)
    ├── HookComposer
    ├── CommandComposer
    ├── SettingsComposer
    └── CodeRabbitComposer
```

### CompositionBase Design

```python
"""Shared base for layered content composition."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from edison.core.config import ConfigManager
from edison.core.config.domains import PacksConfig
from edison.core.utils.paths import PathResolver, get_project_config_dir


class CompositionBase(ABC):
    """Shared base for registries and IDE composers.

    Provides:
    - Unified path resolution (project_root, project_dir)
    - Config manager access (self.cfg_mgr, self.config)
    - Active packs discovery (get_active_packs())
    - YAML loading utilities (load_yaml_safe, merge_yaml)
    - Definition merging (merge_definitions)
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        config: Optional[Dict] = None,
    ) -> None:
        # Path resolution - UNIFIED
        self.project_root = project_root or PathResolver.resolve_project_root()
        self.project_dir = get_project_config_dir(self.project_root, create=False)

        # Config - UNIFIED
        self.cfg_mgr = ConfigManager(self.project_root)
        base_cfg = self.cfg_mgr.load_config(validate=False)
        self.config = self.cfg_mgr.deep_merge(base_cfg, config or {})

        # Active packs - UNIFIED (lazy)
        self._packs_config: Optional[PacksConfig] = None

        # Subclass-specific paths
        self._setup_composition_dirs()

    @abstractmethod
    def _setup_composition_dirs(self) -> None:
        """Setup core/packs directories. Override in subclasses.

        BaseRegistry implementation:
            self.core_dir = self.project_dir / "core"
            self.packs_dir = self.project_dir / "packs"

        IDEComposerBase implementation:
            self.core_dir = Path(get_data_path(""))
            self.bundled_packs_dir = Path(get_data_path("packs"))
            self.project_packs_dir = self.project_dir / "packs"
        """
        pass

    def get_active_packs(self) -> List[str]:
        """Get active packs list (cached)."""
        if self._packs_config is None:
            self._packs_config = PacksConfig(repo_root=self.project_root)
        return self._packs_config.active_packs

    def load_yaml_safe(self, path: Path) -> Dict[str, Any]:
        """Load YAML file, returning empty dict if not found."""
        if not path.exists():
            return {}
        return self.cfg_mgr.load_yaml(path) or {}

    def merge_yaml(
        self,
        base: Dict[str, Any],
        path: Path,
        key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Merge YAML file into base dict."""
        data = self.load_yaml_safe(path)
        if key:
            data = data.get(key, {}) or {}
        if not data:
            return base
        return self.cfg_mgr.deep_merge(base, data)

    def merge_definitions(
        self,
        merged: Dict[str, Dict[str, Any]],
        definitions: Any,
        key_getter: Callable[[Dict], str] = lambda d: d.get("id"),
    ) -> Dict[str, Dict[str, Any]]:
        """Generic merge for definitions by unique key."""
        if isinstance(definitions, dict):
            for def_key, def_dict in definitions.items():
                if not isinstance(def_dict, dict):
                    continue
                existing = merged.get(def_key, {})
                merged[def_key] = self.cfg_mgr.deep_merge(existing, def_dict)
            return merged

        if isinstance(definitions, list):
            for def_dict in definitions:
                if not isinstance(def_dict, dict):
                    continue
                def_key = key_getter(def_dict)
                if not def_key:
                    continue
                existing = merged.get(def_key, {})
                merged[def_key] = self.cfg_mgr.deep_merge(existing, def_dict)
            return merged

        return merged
```

## Files to Create/Modify

### Create
```
src/edison/core/composition/base.py       # CompositionBase class
tests/unit/composition/test_base.py       # Tests
```

### Modify
```
src/edison/core/entity/registry.py        # BaseRegistry extends CompositionBase
src/edison/core/composition/ide/base.py   # IDEComposerBase extends CompositionBase
```

## Implementation Steps

### Step 1: Create CompositionBase
Create `src/edison/core/composition/base.py` with the class above.

### Step 2: Update BaseRegistry
```python
# Before
class BaseRegistry(BaseEntityManager[T], Generic[T]):
    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()
        self.project_dir = get_project_config_dir(self.project_root, create=False)

# After
class BaseRegistry(CompositionBase, Generic[T]):
    def _setup_composition_dirs(self) -> None:
        self.core_dir = self.project_dir / "core"
        self.packs_dir = self.project_dir / "packs"
```

### Step 3: Update IDEComposerBase
```python
# Before
class IDEComposerBase(ABC):
    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        self.cfg_mgr = ConfigManager(self.repo_root)
        # ... 20+ lines of initialization

# After
class IDEComposerBase(CompositionBase):
    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None):
        super().__init__(project_root=repo_root, config=config)
        # Alias for backward compatibility
        self.repo_root = self.project_root

    def _setup_composition_dirs(self) -> None:
        self.core_dir = Path(get_data_path(""))
        self.bundled_packs_dir = Path(get_data_path("packs"))
        self.project_packs_dir = self.project_dir / "packs"
        self.packs_dir = self.bundled_packs_dir  # backward compat
```

### Step 4: Update Subclasses
Remove duplicate initialization from:
- AgentRegistry, ValidatorRegistry, GuidelineRegistry, RulesRegistry
- HookComposer, CommandComposer, SettingsComposer, CodeRabbitComposer

Replace manual packs loading with `self.get_active_packs()`.

## Verification Checklist
- [ ] CompositionBase created with all shared functionality
- [ ] BaseRegistry extends CompositionBase
- [ ] IDEComposerBase extends CompositionBase
- [ ] All registry subclasses still work
- [ ] All IDE composer subclasses still work
- [ ] Backward compatibility maintained (repo_root alias)
- [ ] Tests pass for both hierarchies
- [ ] ~90 lines of duplication eliminated

## Success Criteria
1. Single `CompositionBase` provides path, config, and packs access
2. Both `BaseRegistry` and `IDEComposerBase` extend it
3. No duplicate path resolution or config loading
4. `get_active_packs()` used consistently
5. All existing tests pass

## Related Files
- `src/edison/core/entity/registry.py` - BaseRegistry
- `src/edison/core/composition/ide/base.py` - IDEComposerBase
- `src/edison/core/composition/registries/*.py` - All registries
- `src/edison/core/composition/ide/*.py` - All IDE composers
