<!-- TaskID: 2408-wuni-006-ide-composer-unification -->
<!-- Priority: 2408 -->
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

# WUNI-006: Unify IDE Composer Patterns

## Summary
Eliminate duplication across IDE composers (HookComposer, CommandComposer, SettingsComposer, CodeRabbitComposer) by enhancing `IDEComposerBase` with shared utilities for three-layer loading, YAML extension fallback, and custom merge handlers.

## Problem Statement

### Current Duplication in IDE Composers

**1. Three-layer loading pattern repeated 4 times:**
```python
# HookComposer
core_file = self._bundled_config_dir / "hooks.yaml"
merged = self._merge_from_file(merged, core_file)
for pack in self._active_packs():
    pack_file = self.packs_dir / pack / "config" / "hooks.yml"
    merged = self._merge_from_file(merged, pack_file)
project_file = self.project_dir / "config" / "hooks.yml"
merged = self._merge_from_file(merged, project_file)

# CommandComposer - identical pattern
# SettingsComposer - similar but with extension fallback
# CodeRabbitComposer - similar but with different paths
```

**2. YAML extension fallback duplicated:**
```python
# SettingsComposer (repeated 3 times)
path = self.core_dir / "config" / "settings.yaml"
if not path.exists():
    path = self.core_dir / "config" / "settings.yml"

# CodeRabbitComposer (repeated 3 times)
path = self.core_dir / "templates" / "configs" / "coderabbit.yaml"
if not path.exists():
    path = self.core_dir / "templates" / "configs" / "coderabbit.yml"
```

**3. Custom merge handlers duplicated:**
```python
# SettingsComposer
def deep_merge_settings(self, base, overlay):
    if key == "permissions":
        # special handling
    elif key == "env":
        # special handling

# CodeRabbitComposer
def _merge_with_list_append(self, base, overlay):
    if key == "path_instructions":
        # special handling
```

**4. Inconsistent path structures:**
```python
# HookComposer: packs_dir / pack / "config" / "hooks.yml"
# CodeRabbitComposer: packs_dir / pack / "configs" / "coderabbit.yaml"  # Note: "configs" vs "config"!
```

## Objectives
- [ ] Add `_load_yaml_with_fallback()` to IDEComposerBase
- [ ] Add `_load_layered_config()` to IDEComposerBase
- [ ] Add `_merge_with_handlers()` to IDEComposerBase
- [ ] Fix CodeRabbitComposer path inconsistency
- [ ] Remove redundant `_bundled_config_dir` from HookComposer
- [ ] Standardize config section accessors

## Proposed Additions to IDEComposerBase

### 1. YAML Extension Fallback

```python
def _load_yaml_with_fallback(self, base_path: Path) -> Dict[str, Any]:
    """Load YAML, trying .yaml then .yml extension.

    Args:
        base_path: Path without extension (e.g., /path/to/config)

    Returns:
        Loaded YAML content or empty dict
    """
    # Try .yaml first
    yaml_path = base_path.with_suffix('.yaml')
    if yaml_path.exists():
        return self._load_yaml_safe(yaml_path)

    # Fallback to .yml
    yml_path = base_path.with_suffix('.yml')
    if yml_path.exists():
        return self._load_yaml_safe(yml_path)

    return {}
```

### 2. Three-Layer Config Loading

```python
def _load_layered_config(
    self,
    config_name: str,
    *,
    core_subpath: str = "config",
    pack_subpath: str = "config",
    project_subpath: str = "config",
    key_path: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Load config from core → packs → project with merging.

    Args:
        config_name: Base file name without extension (e.g., "hooks", "settings")
        core_subpath: Subdirectory in core (default: "config")
        pack_subpath: Subdirectory in packs (default: "config")
        project_subpath: Subdirectory in project (default: "config")
        key_path: Optional list of keys to extract before merging

    Returns:
        Merged configuration dictionary

    Example:
        # Load hooks from all layers
        hooks = self._load_layered_config("hooks")

        # Load settings.claude from all layers
        settings = self._load_layered_config(
            "settings",
            key_path=["settings", "claude"]
        )
    """
    merged: Dict[str, Any] = {}

    # Core layer
    core_file = self.core_dir / core_subpath / config_name
    core_data = self._load_yaml_with_fallback(core_file)
    merged = self._extract_and_merge(merged, core_data, key_path)

    # Pack layers
    for pack in self._active_packs():
        pack_file = self.bundled_packs_dir / pack / pack_subpath / config_name
        pack_data = self._load_yaml_with_fallback(pack_file)
        merged = self._extract_and_merge(merged, pack_data, key_path)

    # Project layer
    project_file = self.project_dir / project_subpath / config_name
    project_data = self._load_yaml_with_fallback(project_file)
    merged = self._extract_and_merge(merged, project_data, key_path)

    return merged

def _extract_and_merge(
    self,
    merged: Dict,
    data: Dict,
    key_path: Optional[List[str]],
) -> Dict:
    """Extract optional nested keys and merge."""
    if key_path:
        for key in key_path:
            data = data.get(key, {}) if isinstance(data, dict) else {}
    if not data:
        return merged
    return self.cfg_mgr.deep_merge(merged, data)
```

### 3. Custom Merge Handlers

```python
def _merge_with_handlers(
    self,
    base: Dict,
    overlay: Dict,
    handlers: Dict[str, Callable[[Any, Any], Any]],
) -> Dict:
    """Deep merge with custom handlers for specific keys.

    Args:
        base: Base dictionary
        overlay: Overlay dictionary
        handlers: Dict mapping key names to merge functions

    Example:
        handlers = {
            "permissions": merge_permissions,
            "env": lambda b, o: {**b, **o},  # Simple update
            "path_instructions": lambda b, o: b + o,  # Append lists
        }
        merged = self._merge_with_handlers(base, overlay, handlers)
    """
    result = dict(base)
    for key, value in (overlay or {}).items():
        if key in handlers:
            base_val = result.get(key)
            result[key] = handlers[key](base_val, value)
        elif isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = self._merge_with_handlers(result[key], value, handlers)
        else:
            result[key] = value
    return result
```

### 4. Config Section Accessor

```python
def _get_config_section(self, *keys: str) -> Dict:
    """Get nested config section safely.

    Args:
        *keys: Path of keys to traverse

    Returns:
        Config section or empty dict

    Example:
        hooks_cfg = self._get_config_section("hooks")
        claude_cfg = self._get_config_section("settings", "claude")
    """
    result = self.config or {}
    for key in keys:
        result = result.get(key, {}) if isinstance(result, dict) else {}
    return result
```

## Files to Modify

```
src/edison/core/composition/ide/base.py       # Add new methods
src/edison/core/composition/ide/hooks.py      # Use _load_layered_config
src/edison/core/composition/ide/commands.py   # Use _load_layered_config
src/edison/core/composition/ide/settings.py   # Use _load_layered_config + handlers
src/edison/core/composition/ide/coderabbit.py # Use _load_layered_config + handlers
```

## Migration Examples

### HookComposer Migration

```python
# Before
def load_definitions(self) -> Dict[str, HookDefinition]:
    merged: Dict[str, Dict[str, Any]] = {}
    core_file = self._bundled_config_dir / "hooks.yaml"
    merged = self._merge_from_file(merged, core_file)
    for pack in self._active_packs():
        pack_file = self.packs_dir / pack / "config" / "hooks.yml"
        merged = self._merge_from_file(merged, pack_file)
    project_file = self.project_dir / "config" / "hooks.yml"
    merged = self._merge_from_file(merged, project_file)
    return self._dicts_to_defs(merged)

# After
def load_definitions(self) -> Dict[str, HookDefinition]:
    merged = self._load_layered_config("hooks")
    return self._dicts_to_defs(merged)
```

### SettingsComposer Migration

```python
# Before
def compose_settings(self) -> Dict:
    settings = self.load_core_settings()  # 10 lines
    for pack in self._active_packs():
        pack_settings = self._load_pack_settings(pack)  # 10 lines
        settings = self.deep_merge_settings(settings, pack_settings)
    project_settings = self._load_project_settings()  # 10 lines
    settings = self.deep_merge_settings(settings, project_settings)
    return settings

# After
def compose_settings(self) -> Dict:
    return self._load_layered_config(
        "settings",
        key_path=["settings", "claude"],
        merge_func=lambda b, o: self._merge_with_handlers(b, o, {
            "permissions": merge_permissions,
            "env": lambda b, o: {**(b or {}), **(o or {})},
        })
    )
```

### CodeRabbitComposer Migration

```python
# Before
def compose_coderabbit_config(self) -> Dict[str, Any]:
    config = self.load_core_coderabbit_config()  # 10 lines, uses "configs"
    for pack in self._active_packs():
        pack_config = self._load_pack_coderabbit_config(pack)  # 10 lines, uses "configs"
        config = self._merge_with_list_append(config, pack_config)
    project_config = self._load_project_coderabbit_config()  # 10 lines, uses "configs"
    config = self._merge_with_list_append(config, project_config)
    return config

# After
def compose_coderabbit_config(self) -> Dict[str, Any]:
    return self._load_layered_config(
        "coderabbit",
        core_subpath="templates/configs",  # Note: core uses different path
        pack_subpath="config",             # Fixed: was "configs", now "config"
        project_subpath="config",          # Fixed: was "configs", now "config"
        merge_func=lambda b, o: self._merge_with_handlers(b, o, {
            "path_instructions": lambda b, o: (b or []) + (o or []),
        })
    )
```

## Path Consistency Fix

Fix CodeRabbitComposer to use "config" instead of "configs":
- Change `packs_dir / pack / "configs"` → `packs_dir / pack / "config"`
- Change `project_dir / "configs"` → `project_dir / "config"`

This aligns with all other IDE composers.

## Verification Checklist
- [ ] `_load_yaml_with_fallback()` added to base
- [ ] `_load_layered_config()` added to base
- [ ] `_merge_with_handlers()` added to base
- [ ] `_get_config_section()` added to base
- [ ] HookComposer uses new methods
- [ ] CommandComposer uses new methods
- [ ] SettingsComposer uses new methods
- [ ] CodeRabbitComposer uses new methods + path fix
- [ ] `_bundled_config_dir` removed from HookComposer
- [ ] All IDE composer tests pass
- [ ] ~80 lines of duplication eliminated

## Success Criteria
1. All IDE composers use `_load_layered_config()`
2. No more extension fallback duplication
3. Custom merge logic via handlers
4. Consistent "config" directory naming
5. Clean, short `load_definitions()` / `compose_*()` methods

## Related Files
- WUNI-001 (CompositionBase) - prerequisite for config access
- All IDE composer files in `composition/ide/`
