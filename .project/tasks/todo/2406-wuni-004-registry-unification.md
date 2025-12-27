<!-- TaskID: 2406-wuni-004-registry-unification -->
<!-- Priority: 2406 -->
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
<!-- DependsOn: 2403-wuni-001 -->
<!-- BlocksTask: none -->

# WUNI-004: Unify Registry Patterns

## Summary
Eliminate duplication across the 6 registries by ensuring consistent use of `LayeredComposer`, `CompositionPathResolver`, config loading patterns, and the base class utilities from WUNI-001.

## Problem Statement

### Registry Inconsistencies

| Registry | Uses LayeredComposer | Uses PathResolver | Config Pattern | BaseRegistry |
|----------|---------------------|-------------------|----------------|--------------|
| AgentRegistry | ✓ Yes | ✓ Via composer | Manual | ✓ Yes |
| ValidatorRegistry | ✗ No | ✓ Direct | Manual + cache | ✓ Yes |
| GuidelineRegistry | ✗ No | ✓ Direct | Manual | ✓ Yes |
| RulesRegistry | ✗ No | ✗ Custom | Manual | ✗ No |
| FilePatternRegistry | ✗ No | ✓ Direct | Manual | ✗ No |
| SchemasRegistry | ✗ No | ✗ Hardcoded | Manual | ✗ No |

### Specific Issues

**1. GuidelineRegistry implements own discovery** (80 lines):
```python
def discover_core(self) -> Dict[str, Path]:
    result: Dict[str, Path] = {}
    if self.core_dir.exists():
        for f in self.core_dir.rglob("*.md"):
            # Manual discovery
    return result
```
Should use `LayeredComposer` like AgentRegistry.

**2. ValidatorRegistry has hollow BaseRegistry contract**:
```python
def discover_core(self) -> Dict[str, Dict[str, Any]]:
    """Validators are config-based, not file-discovered."""
    return {}  # Always empty!
```
Should use `ConfigBasedRegistry` subclass.

**3. RulesRegistry doesn't extend BaseRegistry**:
```python
class RulesRegistry:  # No parent!
    def __init__(self, project_root: Optional[Path] = None):
        # Custom initialization
```
Should extend BaseRegistry or ConfigBasedRegistry.

**4. Config loading duplicated 5+ times**:
```python
# In multiple registries
from edison.core.config import ConfigManager
cfg = ConfigManager().load_config(validate=False)
dry_config = cfg.get("composition", {}).get("dryDetection", {})
```

**5. Active packs loading duplicated**:
```python
# validators.py
packs = ((config.get("packs", {}) or {}).get("active", []) or [])
if not isinstance(packs, list):
    packs = []
# Repeated in guidelines.py, agents.py, etc.
```

## Objectives
- [ ] Create `ConfigBasedRegistry` for config-driven registries
- [ ] Update GuidelineRegistry to use LayeredComposer
- [ ] Update RulesRegistry to extend appropriate base
- [ ] Use `get_active_packs()` from CompositionBase everywhere
- [ ] Extract DRY analysis to shared utility
- [ ] Standardize error hierarchy

## Proposed Changes

### 1. Create ConfigBasedRegistry

For registries that load from config, not files:

```python
class ConfigBasedRegistry(CompositionBase, Generic[T], ABC):
    """Base for registries that load entities from configuration.

    Unlike file-based registries, these don't discover from filesystem.
    Examples: ValidatorRegistry (loads from config.validators)
    """

    def discover_core(self) -> Dict[str, T]:
        """Config-based entities have no file-based core discovery."""
        return {}

    def discover_packs(self, packs: List[str]) -> Dict[str, T]:
        """Config-based entities are handled via config loading."""
        return {}

    def discover_project(self) -> Dict[str, T]:
        """Config-based entities are handled via config loading."""
        return {}

    @abstractmethod
    def _load_entities(self) -> Dict[str, T]:
        """Load entities from configuration. Implement in subclass."""
        ...

    def get_all(self) -> List[T]:
        """Get all entities from config."""
        return list(self._load_entities().values())
```

### 2. Update GuidelineRegistry to use LayeredComposer

```python
# Before
class GuidelineRegistry(BaseRegistry[Path]):
    def __init__(self, project_root: Optional[Path] = None):
        super().__init__(project_root)
        path_resolver = CompositionPathResolver(self.project_root, "guidelines")
        self.core_dir = path_resolver.core_dir / "guidelines"
        # ...manual discovery methods

# After
class GuidelineRegistry(BaseRegistry[LayerSource]):
    def __init__(self, project_root: Optional[Path] = None):
        super().__init__(project_root)
        self._composer = LayeredComposer(
            repo_root=self.project_root,
            content_type="guidelines"
        )

    def discover_core(self) -> Dict[str, LayerSource]:
        return self._composer.discover_core()

    def discover_packs(self, packs: List[str]) -> Dict[str, LayerSource]:
        result = {}
        existing = set(self.discover_core().keys())
        for pack in packs:
            pack_new = self._composer.discover_pack_new(pack, existing)
            result.update(pack_new)
            existing.update(pack_new.keys())
        return result
```

### 3. Update ValidatorRegistry

```python
# Before
class ValidatorRegistry(BaseRegistry[Dict[str, Any]]):
    def discover_core(self) -> Dict[str, Dict[str, Any]]:
        return {}  # Hollow!

# After
class ValidatorRegistry(ConfigBasedRegistry[Dict[str, Any]]):
    def _load_entities(self) -> Dict[str, Dict[str, Any]]:
        # Existing _load_validators logic
        return self._load_validators()
```

### 4. Update RulesRegistry

```python
# Before
class RulesRegistry:
    def __init__(self, project_root: Optional[Path] = None):
        # No base class!

# After
class RulesRegistry(ConfigBasedRegistry[Dict[str, Any]]):
    def _setup_composition_dirs(self) -> None:
        # Custom rules directory setup

    def _load_entities(self) -> Dict[str, Dict[str, Any]]:
        # Existing rules loading logic
```

### 5. Extract DRY Analysis Utility

Create shared utility for agents.py and guidelines.py:

```python
# core/composition/analysis/dry.py
class DRYAnalyzer:
    """Shared DRY analysis utility."""

    def __init__(self, project_root: Path):
        from edison.core.config import ConfigManager
        cfg = ConfigManager(project_root).load_config(validate=False)
        dry_config = cfg.get("composition", {}).get("dryDetection", {})
        self.min_shingles = dry_config.get("minShingles", 2)
        self.shingle_size = dry_config.get("shingleSize", 12)

    def analyze(
        self,
        layers: Dict[str, str],
        min_shingles: Optional[int] = None,
    ) -> Dict:
        """Perform DRY analysis across layers."""
        from edison.core.utils.text import dry_duplicate_report
        min_s = min_shingles if min_shingles is not None else self.min_shingles
        return dry_duplicate_report(layers, min_shingles=min_s, k=self.shingle_size)
```

### 6. Standardize Error Hierarchy

Create unified errors in `core/composition/errors.py`:

```python
class CompositionError(RuntimeError):
    """Base error for composition operations."""

class EntityNotFoundError(CompositionError):
    """Entity not found in registry."""
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(f"{entity_type} '{entity_id}' not found")
        self.entity_type = entity_type
        self.entity_id = entity_id

class CompositionValidationError(CompositionError):
    """Error in composition validation."""

class AnchorNotFoundError(CompositionError):
    """Anchor not found in source file."""
```

## Files to Create/Modify

### Create
```
src/edison/core/composition/registries/config_based.py  # ConfigBasedRegistry
src/edison/core/composition/analysis/dry.py             # DRYAnalyzer
```

### Modify
```
src/edison/core/composition/registries/guidelines.py    # Use LayeredComposer
src/edison/core/composition/registries/validators.py   # Extend ConfigBasedRegistry
src/edison/core/composition/registries/rules.py        # Extend ConfigBasedRegistry
src/edison/core/composition/registries/agents.py       # Use DRYAnalyzer
src/edison/core/composition/core/errors.py             # Add unified errors
```

## Migration Summary

| Registry | Current | After |
|----------|---------|-------|
| AgentRegistry | BaseRegistry + LayeredComposer | No change (already good) |
| ValidatorRegistry | BaseRegistry (hollow) | ConfigBasedRegistry |
| GuidelineRegistry | BaseRegistry + manual | BaseRegistry + LayeredComposer |
| RulesRegistry | No base | ConfigBasedRegistry |
| FilePatternRegistry | No base | BaseRegistry |
| SchemasRegistry | No base | ConfigBasedRegistry |

## Verification Checklist
- [ ] ConfigBasedRegistry created
- [ ] GuidelineRegistry uses LayeredComposer
- [ ] ValidatorRegistry extends ConfigBasedRegistry
- [ ] RulesRegistry extends ConfigBasedRegistry
- [ ] DRYAnalyzer extracted and used
- [ ] Error hierarchy standardized
- [ ] All registry tests pass
- [ ] ~200 lines of duplication eliminated

## Success Criteria
1. All registries extend appropriate base class
2. File-based registries use `LayeredComposer`
3. Config-based registries extend `ConfigBasedRegistry`
4. `get_active_packs()` used everywhere (not manual loading)
5. DRY analysis shared between agents and guidelines
6. Consistent error types across all registries

## Related Files
- WUNI-001 (CompositionBase) - prerequisite
- All registry files in `composition/registries/`
- `core/composition/core/composer.py` - LayeredComposer
