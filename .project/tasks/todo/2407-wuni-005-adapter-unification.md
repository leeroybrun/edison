<!-- TaskID: 2407-wuni-005-adapter-unification -->
<!-- Priority: 2407 -->
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
<!-- EstimatedHours: 6 -->
<!-- DependsOn: 2405-wuni-003 -->
<!-- BlocksTask: none -->

# WUNI-005: Unify Adapter Patterns

## Summary
Eliminate duplication across prompt and sync adapters by enhancing base classes (`PromptAdapter`, `SyncAdapter`) with shared functionality: path resolution via `OutputPathResolver`, registry access, config loading, and file writing patterns.

## Problem Statement

### Current Adapter Duplication

**1. AdaptersConfig instantiated 6+ times:**
```python
# claude.py, cursor.py, zen.py (prompt)
adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
self.claude_dir = adapters_cfg.get_client_path("claude")

# claude.py, cursor.py, zen/sync.py (sync)
adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
```

**2. OutputConfigLoader instantiated inconsistently:**
```python
# Cursor: self._output_config = OutputConfigLoader(repo_root=...)
# Zen: self._config = OutputConfigLoader(...)
# Claude: return OutputConfigLoader(...) from _load_config()
```

**3. Registry instantiation duplicated:**
```python
# cursor.py sync
self.guideline_registry = GuidelineRegistry(repo_root=root)
self.rules_registry = RulesRegistry(project_root=root)

# zen/client.py
# Same pattern
```

**4. File writing patterns repeated:**
```python
# All adapters
ensure_directory(path.parent)
path.write_text(content, encoding="utf-8")
```

**5. ConfigMixin reimplemented:**
```python
# codex.py reimplements _load_config() even though ConfigMixin exists
def _load_config(self) -> Dict:
    if self._cached_config is not None:
        return self._cached_config
    # ... identical to ConfigMixin
```

### Zen Adapter Over-Complexity
The Zen adapter is split across 4 files with 3 mixins:
- `discovery.py` - ZenDiscoveryMixin
- `composer.py` - ZenComposerMixin
- `sync.py` - ZenSyncMixin
- `client.py` - ZenSync (combines all 3)

This should be consolidated into a simpler structure.

## Objectives
- [ ] Enhance `SyncAdapter` base with shared functionality
- [ ] Enhance `PromptAdapter` with template method patterns
- [ ] Create `RegistryMixin` for registry access
- [ ] Use `OutputPathResolver` everywhere
- [ ] Consolidate Zen adapter to single file
- [ ] Use `CompositionFileWriter` for all writes

## Proposed Changes

### 1. Enhanced SyncAdapter Base

```python
class SyncAdapter(ABC):
    """Enhanced base class for sync adapters.

    Provides:
    - Path resolution via OutputPathResolver
    - Lazy registry access
    - Config loading
    - Directory validation
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        from edison.core.composition.output import OutputPathResolver
        from edison.core.config.domains import AdaptersConfig

        self._path_resolver = OutputPathResolver(repo_root)
        self.repo_root = self._path_resolver.repo_root
        self.project_config_dir = self._path_resolver.project_dir

        self._adapters_cfg = AdaptersConfig(repo_root=self.repo_root)

        # Lazy registries
        self._guideline_registry: Optional[GuidelineRegistry] = None
        self._rules_registry: Optional[RulesRegistry] = None
        self._agent_registry: Optional[AgentRegistry] = None

    @property
    def path_resolver(self) -> OutputPathResolver:
        """Get unified path resolver."""
        return self._path_resolver

    @property
    def adapters_config(self) -> AdaptersConfig:
        """Get adapters configuration."""
        return self._adapters_cfg

    @property
    def guideline_registry(self) -> GuidelineRegistry:
        """Lazy guideline registry."""
        if self._guideline_registry is None:
            from edison.core.composition.registries import GuidelineRegistry
            self._guideline_registry = GuidelineRegistry(repo_root=self.repo_root)
        return self._guideline_registry

    @property
    def rules_registry(self) -> RulesRegistry:
        """Lazy rules registry."""
        if self._rules_registry is None:
            from edison.core.composition.registries import RulesRegistry
            self._rules_registry = RulesRegistry(project_root=self.repo_root)
        return self._rules_registry

    @property
    def agent_registry(self) -> AgentRegistry:
        """Lazy agent registry."""
        if self._agent_registry is None:
            from edison.core.composition.registries import AgentRegistry
            self._agent_registry = AgentRegistry(project_root=self.repo_root)
        return self._agent_registry

    def ensure_directory(self, path: Path, create_missing: bool = True) -> Path:
        """Ensure directory exists with error handling."""
        if not path.exists():
            if not create_missing:
                raise AdapterError(f"Directory not found: {path}")
            from edison.core.utils.io import ensure_directory
            ensure_directory(path)
        return path

    def get_client_dir(self, client_name: str) -> Path:
        """Get client directory (e.g., .claude/, .cursor/)."""
        return self._adapters_cfg.get_client_path(client_name).parent

    @abstractmethod
    def _load_config(self) -> Dict[str, Any]:
        """Load adapter-specific configuration."""
        pass

    @abstractmethod
    def sync_all(self) -> Dict[str, Any]:
        """Execute complete synchronization."""
        pass
```

### 2. Enhanced PromptAdapter Base

```python
class PromptAdapter(ABC):
    """Enhanced base class for prompt adapters.

    Provides:
    - Template method patterns for writing
    - Consistent file listing
    - Post-processing hooks
    """

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        self.generated_root = generated_root.resolve()
        self.repo_root = repo_root.resolve() if repo_root else self.generated_root.parents[1]

        from edison.core.composition.core import CompositionFileWriter
        self._writer = CompositionFileWriter()

    # Template method for writing agents
    def write_agents(
        self,
        output_dir: Path,
        pattern: str = "{name}.md",
    ) -> List[Path]:
        """Write all agents to output directory."""
        from edison.core.utils.io import ensure_directory
        ensure_directory(output_dir)

        written = []
        for agent_name in self.list_agents():
            content = self.render_agent(agent_name)
            formatted = self._format_agent_file(agent_name, content)
            filename = pattern.format(name=agent_name)
            path = output_dir / filename
            self._writer.write_text(path, formatted)
            written.append(path)
        return written

    # Template method for writing validators
    def write_validators(
        self,
        output_dir: Path,
        pattern: str = "{name}.md",
    ) -> List[Path]:
        """Write all validators to output directory."""
        from edison.core.utils.io import ensure_directory
        ensure_directory(output_dir)

        written = []
        for validator_name in self.list_validators():
            content = self.render_validator(validator_name)
            formatted = self._format_validator_file(validator_name, content)
            filename = pattern.format(name=validator_name)
            path = output_dir / filename
            self._writer.write_text(path, formatted)
            written.append(path)
        return written

    def _format_agent_file(self, name: str, content: str) -> str:
        """Hook for formatting agent file. Override in subclasses."""
        return self._post_process_agent(name, content)

    def _format_validator_file(self, name: str, content: str) -> str:
        """Hook for formatting validator file. Override in subclasses."""
        return self._post_process_validator(name, content)

    # ... existing methods
```

### 3. Consolidated ZenSync

Replace 4 files with single consolidated class:

```python
# adapters/sync/zen.py (consolidated)
class ZenSync(SyncAdapter):
    """Zen MCP sync adapter.

    Syncs Edison composition outputs to Zen MCP format.
    """

    def __init__(self, repo_root: Optional[Path] = None, config: Optional[Dict] = None):
        super().__init__(repo_root)
        self._config_override = config

    def _load_config(self) -> Dict[str, Any]:
        if self._config_override:
            return self._config_override
        from edison.core.config import ConfigManager
        mgr = ConfigManager(self.repo_root)
        try:
            return mgr.load_config(validate=False)
        except FileNotFoundError:
            return {}

    def sync_all(self) -> Dict[str, Any]:
        """Sync all Zen outputs."""
        result = {"roles": {}, "workflows": []}

        # Use base class registries
        guidelines = self.guideline_registry
        rules = self.rules_registry

        # Sync logic...
        return result

    # Discovery methods (from ZenDiscoveryMixin)
    def discover_role_guidelines(self, role: str) -> List[str]:
        """Discover guidelines for a role."""
        # ...

    # Composition methods (from ZenComposerMixin)
    def compose_role_prompt(self, role: str, model: str) -> str:
        """Compose prompt for a role."""
        # ...

    # Sync methods (from ZenSyncMixin)
    def sync_role_prompts(self, roles: List[str]) -> List[Path]:
        """Sync role prompts to filesystem."""
        # ...
```

### 4. Fix CodexAdapter to Use ConfigMixin

```python
# Before - reimplements ConfigMixin
class CodexAdapter(PromptAdapter):
    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None):
        super().__init__(generated_root, repo_root)
        self._cached_config: Optional[Dict] = None

    def _load_config(self) -> Dict:
        # Duplicate implementation!

# After - use ConfigMixin
class CodexAdapter(PromptAdapter, ConfigMixin):
    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None):
        super().__init__(generated_root, repo_root)
        # ConfigMixin provides _load_config and config property
```

## Files to Create/Modify

### Create
```
src/edison/core/adapters/sync/zen.py      # Consolidated ZenSync (replaces zen/)
```

### Delete (after consolidation)
```
src/edison/core/adapters/sync/zen/discovery.py
src/edison/core/adapters/sync/zen/composer.py
src/edison/core/adapters/sync/zen/sync.py
src/edison/core/adapters/sync/zen/client.py
src/edison/core/adapters/sync/zen/__init__.py
```

### Modify
```
src/edison/core/adapters/sync/base.py     # Enhanced SyncAdapter
src/edison/core/adapters/base.py          # Enhanced PromptAdapter
src/edison/core/adapters/sync/claude.py   # Use base class utilities
src/edison/core/adapters/sync/cursor.py   # Use base class utilities
src/edison/core/adapters/prompt/codex.py  # Use ConfigMixin
src/edison/core/adapters/prompt/cursor.py # Use base class utilities
src/edison/core/adapters/prompt/zen.py    # Use base class utilities
```

## Migration Summary

| Adapter | Current Issues | After |
|---------|---------------|-------|
| ClaudeSync | Manual path resolution | Uses SyncAdapter.path_resolver |
| CursorSync | Manual registry init | Uses SyncAdapter.guideline_registry |
| ZenSync | 4 files, 3 mixins | Single consolidated file |
| ClaudeAdapter | OK | Uses enhanced PromptAdapter |
| CursorPromptAdapter | OK | Uses enhanced PromptAdapter |
| ZenPromptAdapter | Manual writes | Uses PromptAdapter.write_agents() |
| CodexAdapter | Duplicates ConfigMixin | Extends ConfigMixin |

## Verification Checklist
- [ ] SyncAdapter enhanced with shared functionality
- [ ] PromptAdapter enhanced with template methods
- [ ] Zen adapter consolidated to single file
- [ ] CodexAdapter uses ConfigMixin
- [ ] All adapters use OutputPathResolver
- [ ] Registry access via lazy properties
- [ ] File writing uses CompositionFileWriter
- [ ] All adapter tests pass
- [ ] ~150 lines of duplication eliminated

## Success Criteria
1. Single `SyncAdapter` provides path resolution, config, registries
2. Single `PromptAdapter` provides template methods for writing
3. Zen adapter is 1 file instead of 4
4. No more duplicate AdaptersConfig instantiation
5. No more duplicate registry instantiation
6. ConfigMixin used consistently

## Related Files
- WUNI-003 (OutputPathResolver) - prerequisite
- WUNI-002 (CompositionFileWriter) - used by adapters
- All adapter files in `adapters/`
