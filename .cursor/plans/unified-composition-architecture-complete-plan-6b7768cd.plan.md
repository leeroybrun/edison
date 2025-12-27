---
name: Unified Composition Architecture - Complete Plan
overview: ""
todos:
  - id: f1e8cf50-cfa7-4972-8c05-20343f4330bd
    content: Add compose_validator() to ValidatorRegistry for file composition
    status: pending
  - id: f5f3797e-4c86-41b8-adee-bfd396c33f04
    content: Convert ConstitutionRegistry from functions to class extending ComposableRegistry
    status: pending
  - id: 824647ab-3eff-4e2b-8588-6182db914b30
    content: Create data/rosters/*.md templates and refactor rosters.py
    status: pending
  - id: 749d83dc-87ec-4f0e-914d-c9f52b87c70c
    content: Create ComposableGenerator base class and refactor roster generators
    status: pending
  - id: c07238a7-27b0-42dc-8748-bdcfa6886f3a
    content: Move composition/ide/ to adapters/components/, create AdapterComponent base
    status: pending
  - id: f027080e-a869-4479-9011-e6968620e1f7
    content: Restructure adapters with component-based architecture
    status: pending
  - id: 8ad7a356-13c5-442d-b159-60575628f5b7
    content: Ensure all composers use _load_layered_config() consistently
    status: pending
  - id: 1c9b6df1-cb52-4300-a302-9164089f6488
    content: Run full test suite and fix all refactoring-related failures
    status: pending
---

# Unified Composition Architecture - Complete Plan

## Critical Principles (Non-Negotiable)

These principles MUST be followed for EVERY task in this plan:

1. **STRICT TDD**: Write failing test FIRST (RED), then implement (GREEN), then refactor
2. **NO MOCKS**: Test real behavior, real code, real libs - NO MOCKS EVER
3. **NO LEGACY**: Delete old code completely - NO backward compatibility, NO fallbacks
4. **NO HARDCODED VALUES**: All config from YAML - NO magic numbers/strings in code
5. **100% CONFIGURABLE**: Every behavior must be configurable via YAML
6. **DRY**: Zero code duplication - extract to shared utilities
7. **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
8. **KISS**: Keep It Simple, Stupid - no over-engineering
9. **YAGNI**: You Aren't Gonna Need It - remove speculative features
10. **LONG-TERM MAINTAINABLE**
11. **UN-DUPLICATED & REUSABLE**: Analyze existing code before implementing - reuse/extend existing features
12. **STRICT COHERENCE AND UNITY**: Understand existing patterns BEFORE implementing - maintain unified codebase style
13. **ROOT CAUSE FIXES**: NEVER apply dirty fixes or skip tests - ALWAYS find and fix ROOT CAUSES
14. **REFACTORING ESSENTIALS**: Update ALL callers/tests/CLIs when refactoring - NO legacy fallbacks
15. **SELF VALIDATION**: Re-analyze everything before marking done - fresh eyes review
16. **GIT SAFETY**: NEVER use `git reset`/`git checkout` except if user explicitly asks

---

## Testing Requirements

- Update ALL related tests when changing code (unit, integration, e2e)
- When tests fail, analyze and fix ROOT CAUSE - never simplify/skip/remove tests to make them pass
- For large test runs: use 30min timeout + redirect output to temp file, then delegate subagent to analyze
- Fix multiple test failures in parallel via dedicated subagents for each root cause

---

## Executive Summary

Unify ALL composition into a single coherent architecture:

- **ONE** `MarkdownCompositionStrategy` for ALL markdown content
- **ONE** `ComposableRegistry` base class for ALL file-based registries  
- **ONE** `CompositionBase` with shared YAML/config utilities
- **ONE** `SyncAdapter` base with shared adapter patterns
- **ZERO** duplicate code across registries, composers, and adapters

---

## Part 1: The Unified Architecture

### Class Hierarchy (New - Fully Unified)

```
CompositionBase (composition/core/base.py)
│   ├── Path resolution via CompositionPathResolver (SINGLE SOURCE)
│   ├── Config loading via ConfigManager
│   ├── YAML utilities: load_yaml_safe(), _load_layered_config()
│   ├── Definition helpers: _extract_definitions(), _merge_by_id()
│   └── Writer property (lazy CompositionFileWriter)
│
├── ComposableRegistry (entity/composable_registry.py) [NEW]
│   │   ├── Uses LayerDiscovery for ALL file discovery
│   │   ├── Uses MarkdownCompositionStrategy for ALL composition
│   │   └── Abstract: content_type, file_pattern, strategy_config
│   │
│   ├── AgentRegistry (registries/agents.py)
│   ├── ValidatorRegistry (registries/validators.py) [ADD file composition]
│   ├── GuidelineRegistry (registries/guidelines.py) [MIGRATE to sections]
│   ├── ConstitutionRegistry (registries/constitutions.py) [MIGRATE]
│   └── DocumentTemplateRegistry (registries/documents.py)
│
├── ComposableGenerator (generators/base.py) [NEW]
│   │   ├── Two-phase: Compose template → Inject data
│   │   └── Abstract: content_type, template_name, get_data()
│   │
│   ├── AgentRosterGenerator (generators/rosters.py)
│   ├── ValidatorRosterGenerator (generators/rosters.py)
│   ├── StateMachineGenerator (generators/state_machine.py)
│   └── CanonicalEntryGenerator (generators/canonical.py)
│
└── PlatformAdapter (adapters/base.py) [UNIFIED]
    │   ├── Inherits from CompositionBase
    │   ├── adapters_config, output_config properties
    │   ├── Common: validate_structure(), sync_agents(), add_frontmatter()
    │   └── Abstract: sync() → Dict[str, Any]
    │
    ├── AdapterComponent (adapters/components/base.py) [NEW]
    │   │   ├── Base for platform components (hooks, settings, commands)
    │   │   ├── References parent PlatformAdapter for shared resources
    │   │   └── Abstract: compose(), write()
    │   │
    │   ├── CommandComponent (adapters/components/commands.py) [MOVE from ide/]
    │   │   ├── Multi-platform command generation
    │   │   └── write_for_platform(platform, output_dir)
    │   │
    │   ├── HookComponent (adapters/components/hooks.py) [MOVE from ide/]
    │   │   └── Base for platform-specific hooks
    │   │
    │   └── SettingsComponent (adapters/components/settings.py) [MOVE from ide/]
    │       └── Base for platform-specific settings
    │
    ├── ClaudeAdapter (adapters/claude/adapter.py) [RESTRUCTURE]
    │   ├── ClaudeHooks (adapters/claude/hooks.py) extends HookComponent
    │   └── ClaudeSettings (adapters/claude/settings.py) extends SettingsComponent
    │
    ├── CursorAdapter (adapters/cursor/adapter.py) [RESTRUCTURE]
    │   └── CursorRules (adapters/cursor/rules.py) - .cursorrules generation
    │
    ├── ZenAdapter (adapters/zen/adapter.py) [RESTRUCTURE]
    │
    ├── CodexAdapter (adapters/codex/adapter.py) [SIMPLIFY]
    │
    └── CoderabbitAdapter (adapters/coderabbit/adapter.py) [MOVE from ide/]
```

### DELETE: composition/ide/ Folder

The "IDE" naming is misleading:

- Claude Code is a CLI, not an IDE
- Codex is a CLI
- CodeRabbit is a review bot
- Only Cursor is an actual IDE

All this logic moves to `adapters/` with proper platform organization.

### Component Pattern

```python
# adapters/components/base.py
class AdapterComponent(ABC):
    """Base for platform adapter components."""
    
    def __init__(self, adapter: "PlatformAdapter"):
        self.adapter = adapter  # Share config/paths with parent
    
    @property
    def config(self) -> Dict: return self.adapter.config
    @property
    def writer(self) -> CompositionFileWriter: return self.adapter.writer
    
    @abstractmethod
    def compose(self) -> Any: pass
    @abstractmethod
    def write(self, output_dir: Path) -> List[Path]: pass

# adapters/claude/adapter.py
class ClaudeAdapter(PlatformAdapter):
    def __init__(self, project_root):
        super().__init__(project_root)
        self.hooks = ClaudeHooks(self)      # Platform-specific
        self.settings = ClaudeSettings(self) # Platform-specific
        self.commands = CommandComponent(self)  # Shared
    
    def sync(self) -> Dict[str, Any]:
        return {
            "hooks": self.hooks.write(...),
            "settings": self.settings.write(...),
            "commands": self.commands.write_for_platform("claude", ...),
            "agents": self.sync_agents_from_generated(...),
        }
```

### Composition Strategy (Single Strategy)

```python
# composition/core/strategies.py [NEW FILE]

class MarkdownCompositionStrategy:
    """THE unified strategy for ALL markdown content.
    
    Features (all configurable):
    - Section-based composition (SECTION/EXTEND markers)
    - DRY deduplication (shingle-based)
    - Include resolution
    - Template processing via TemplateEngine
    """
    
    def __init__(
        self,
        enable_sections: bool = True,
        enable_dedupe: bool = False,
        dedupe_shingle_size: int = 12,
        enable_template_processing: bool = True,
    ):
        self.parser = SectionParser()
        self.enable_sections = enable_sections
        self.enable_dedupe = enable_dedupe
        self.dedupe_shingle_size = dedupe_shingle_size
        self.enable_template_processing = enable_template_processing
    
    def compose(self, layers: List[LayerContent], context: CompositionContext) -> str:
        """Unified composition pipeline:
        1. Parse sections from each layer
        2. Build section registry (SECTION + EXTEND)
        3. Merge sections into template
        4. Apply DRY deduplication (if enabled)
        5. Process through TemplateEngine (if enabled)
        """
        pass
```

---

## Part 2: Content Type Configurations

### All Content Types Using MarkdownCompositionStrategy

| Content Type | `content_type` | `file_pattern` | `enable_sections` | `enable_dedupe` |

|--------------|----------------|----------------|-------------------|-----------------|

| Agents | `"agents"` | `"*.md"` | ✅ Yes | ❌ No |

| Validators | `"validators"` | `"*.md"` | ✅ Yes | ❌ No |

| Guidelines | `"guidelines"` | `"*.md"` | ✅ Yes | ✅ Yes |

| Constitutions | `"constitutions"` | `"*-base.md"` | ✅ Yes | ❌ No |

| Documents | `"documents"` | `"*.md"` | ✅ Yes | ❌ No |

| Rosters | `"rosters"` | `"*.md"` | ✅ Yes | ❌ No |

### Registry Implementations (Minimal Code)

```python
# registries/agents.py
class AgentRegistry(ComposableRegistry[CoreAgent]):
    content_type = "agents"
    file_pattern = "*.md"
    strategy_config = {"enable_sections": True, "enable_dedupe": False}
    
    # Only agent-specific logic remains:
    # - _build_constitution_header()
    # - _read_front_matter()

# registries/validators.py  
class ValidatorRegistry(ComposableRegistry[ValidatorPrompt]):
    content_type = "validators"
    file_pattern = "*.md"
    strategy_config = {"enable_sections": True, "enable_dedupe": False}
    
    # Validator-specific: roster loading from config (separate from file composition)

# registries/guidelines.py
class GuidelineRegistry(ComposableRegistry[GuidelineResult]):
    content_type = "guidelines"
    file_pattern = "*.md"
    strategy_config = {"enable_sections": True, "enable_dedupe": True, "dedupe_shingle_size": 12}
    
    # No custom composition - ALL handled by strategy

# registries/constitutions.py
class ConstitutionRegistry(ComposableRegistry[str]):
    content_type = "constitutions"
    file_pattern = "*-base.md"
    strategy_config = {"enable_sections": True, "enable_dedupe": False}
    
    # Constitution-specific: role normalization, template rendering

# registries/rosters.py [REFACTORED]
class RosterRegistry(ComposableRegistry[str]):
    content_type = "rosters"
    file_pattern = "*.md"
    strategy_config = {"enable_sections": True}
    
    # Templates at data/rosters/AVAILABLE_AGENTS.md, AVAILABLE_VALIDATORS.md
    # No more hardcoded markdown strings!
```

---

## Part 3: CompositionBase Enhancements

### Unified Base Class

```python
# composition/core/base.py

class CompositionBase(ABC):
    """Unified base for ALL composition infrastructure.
    
    Provides:
    - Path resolution via CompositionPathResolver
    - Config management via ConfigManager
    - Active packs via PacksConfig
    - YAML loading utilities
    - Definition extraction and merging
    - Lazy CompositionFileWriter
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        # Path resolution - SINGLE SOURCE OF TRUTH
        self._path_resolver = CompositionPathResolver(project_root)
        self.project_root = self._path_resolver.repo_root
        self.project_dir = self._path_resolver.project_dir
        self.core_dir = self._path_resolver.core_dir
        self.packs_dir = self._path_resolver.packs_dir
        self.bundled_packs_dir = self._path_resolver.bundled_packs_dir
        self.project_packs_dir = self._path_resolver.project_packs_dir
        
        # Config - UNIFIED
        self.cfg_mgr = ConfigManager(self.project_root)
        self.config = self.cfg_mgr.load_config(validate=False)
        
        # Lazy writer
        self._writer: Optional[CompositionFileWriter] = None
    
    @property
    def writer(self) -> CompositionFileWriter:
        """Lazy-initialized file writer."""
        if self._writer is None:
            self._writer = CompositionFileWriter(base_dir=self.project_root)
        return self._writer
    
    def get_active_packs(self) -> List[str]:
        """Get active packs (cached)."""
        return PacksConfig(repo_root=self.project_root).active_packs
    
    # YAML Utilities
    def load_yaml_safe(self, path: Path) -> Dict[str, Any]: ...
    def _load_layered_config(self, config_name: str, subdirs: List[str] = None) -> Dict: ...
    
    # Definition Helpers [NEW]
    def _extract_definitions(self, data: Dict, key: str) -> List[Dict]:
        """Extract definitions list from config data by key path."""
        pass
    
    def _merge_definitions_by_id(
        self, 
        base: Dict[str, Dict], 
        new_defs: List[Dict],
        id_key: str = "id",
    ) -> Dict[str, Dict]:
        """Merge definitions list into base dict by ID."""
        pass
```

---

## Part 4: SyncAdapter Enhancements

### Unified Sync Base

```python
# adapters/sync/base.py

class SyncAdapter(CompositionBase):
    """Base for ALL sync adapters (Claude, Cursor, Zen).
    
    Inherits from CompositionBase to get:
    - Path resolution, config, YAML utilities, writer
    
    Adds:
    - AdaptersConfig access
    - OutputConfigLoader access
    - Common sync patterns
    """
    
    def __init__(self, repo_root: Optional[Path] = None):
        super().__init__(project_root=repo_root)
        self._adapters_config: Optional[AdaptersConfig] = None
        self._output_config: Optional[OutputConfigLoader] = None
    
    @property
    def adapters_config(self) -> AdaptersConfig:
        """Lazy AdaptersConfig accessor."""
        if self._adapters_config is None:
            self._adapters_config = AdaptersConfig(repo_root=self.project_root)
        return self._adapters_config
    
    @property
    def output_config(self) -> OutputConfigLoader:
        """Lazy OutputConfigLoader accessor."""
        if self._output_config is None:
            self._output_config = OutputConfigLoader(repo_root=self.project_root)
        return self._output_config
    
    def validate_structure(self, target_dir: Path, *, create_missing: bool = True) -> Path:
        """Ensure target directory structure exists."""
        if not target_dir.exists():
            if not create_missing:
                raise RuntimeError(f"Missing directory: {target_dir}")
            ensure_directory(target_dir)
        return target_dir
    
    def sync_agents_from_generated(
        self,
        target_dir: Path,
        *,
        add_frontmatter: bool = False,
        frontmatter_fn: Optional[Callable] = None,
    ) -> List[Path]:
        """Common pattern: sync _generated/agents/ to target dir."""
        pass
    
    @abstractmethod
    def sync_all(self) -> Dict[str, Any]:
        """Execute complete sync workflow."""
        pass
```

---

## Part 5: Files to Change

### New Files

| File | Purpose |

|------|---------|

| `composition/core/strategies.py` | `MarkdownCompositionStrategy` |

| `entity/composable_registry.py` | `ComposableRegistry` base class |

| `data/rosters/AVAILABLE_AGENTS.md` | Template for agent roster |

| `data/rosters/AVAILABLE_VALIDATORS.md` | Template for validator roster |

### Files to Refactor

| File | Changes |

|------|---------|

| `composition/core/base.py` | Add `_extract_definitions()`, `_merge_definitions_by_id()`, ensure `writer` property |

| `entity/registry.py` | Simplify - remove duplicate path/config init, inherit from CompositionBase |

| `adapters/sync/base.py` | Inherit from `CompositionBase`, add `adapters_config`, `output_config`, common sync methods |

| `adapters/sync/claude.py` | Remove duplicate writer, use base sync methods |

| `adapters/sync/cursor.py` | Remove duplicate writer, use base sync methods |

| `ide/base.py` | Remove `_setup_composition_dirs()` - use CompositionPathResolver |

| `ide/commands.py` | Use `_load_layered_config()`, remove `_merge_command_list()` |

| `ide/settings.py` | Use `_load_layered_config()` where possible |

| `registries/agents.py` | Extend `ComposableRegistry`, remove custom discovery |

| `registries/validators.py` | Add `compose_validator()` using strategy, extend `ComposableRegistry` |

| `registries/guidelines.py` | Remove 200+ lines of custom composition, extend `ComposableRegistry` |

| `registries/constitutions.py` | Extend `ComposableRegistry`, migrate to sections |

| `registries/documents.py` | Already thin - just extend `ComposableRegistry` |

| `registries/rosters.py` | Refactor to template-based, extend `ComposableRegistry` |

| `registries/schemas.py` | Remove duplicate `_deep_merge()`, use `ConfigManager.deep_merge()` |

### Files to Delete/Merge

| File | Action |

|------|--------|

| Backward compat aliases in `base.py` | Remove `_active_packs()`, `_load_yaml_safe()`, `_merge_from_file()` |

| Backward compat in `registry.py` | Remove duplicate YAML utilities |

| `ide/base.py._merge_definitions()` | Remove alias, use `merge_definitions()` |

---

## Part 6: Migration Path

### Phase 1: Foundation (No Breaking Changes)

1. Create `composition/core/strategies.py` with `MarkdownCompositionStrategy`
2. Create `entity/composable_registry.py` base class
3. Enhance `CompositionBase` with definition helpers
4. Enhance `SyncAdapter` to inherit from `CompositionBase`

### Phase 2: Registry Migration

1. Migrate `AgentRegistry` to extend `ComposableRegistry`
2. Migrate `ValidatorRegistry` - add file composition (currently missing!)
3. Migrate `GuidelineRegistry` - remove 200+ lines, use strategy with dedupe
4. Migrate `ConstitutionRegistry` - use sections
5. Migrate `DocumentTemplateRegistry` - already thin
6. Create `RosterRegistry` with templates

### Phase 3: IDE/Adapter Unification

1. Refactor IDE composers to use `_load_layered_config()` consistently
2. Refactor sync adapters to use `SyncAdapter` base methods
3. Remove duplicate `_deep_merge()` from `JsonSchemaComposer`

### Phase 4: Cleanup

1. Remove all backward compatibility aliases
2. Update all callers to use canonical method names
3. Update all tests

---

## Part 7: Code Reduction Summary

| Category | Before | After | Lines Removed |

|----------|--------|-------|---------------|

| Path resolution | 5 implementations | 1 | ~100 lines |

| Active packs | 4 implementations | 1 | ~40 lines |

| Layer discovery | 6 implementations | 1 | ~150 lines |

| Markdown composition | 4 implementations | 1 | ~300 lines |

| YAML loading | 5 implementations | 1 | ~80 lines |

| Writer pattern | 6 implementations | 1 | ~60 lines |

| Deep merge | 3 implementations | 1 | ~40 lines |

| Backward compat | 8 aliases | 0 | ~30 lines |

| **Total** | | | **~800 lines** |

**Plus**: Validators now have file composition (new feature, not just cleanup)