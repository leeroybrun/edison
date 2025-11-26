# AUDIT 4: Quick Reference Guide

**Purpose:** Fast lookup for developers during refactoring work

---

## 🎯 THE THREE BIG PROBLEMS

### Problem 1: The 51% Problem
**51% of code lives in 27 god files**
- Top 10 files: 5,622 LOC (23.9% of codebase)
- Violates Single Responsibility Principle
- Fix: Split into focused classes (~180 LOC each)

### Problem 2: The Coupling Crisis
**ConfigManager instantiated 28 times across 65 files**
- No dependency injection
- Cannot test in isolation
- Fix: Extract interface, inject dependencies

### Problem 3: The Global State Problem
**16 global variables managing state**
- Module-level singletons
- Cache variables scattered
- Fix: Context objects + dependency injection

---

## 📋 TOP 10 FILES TO REFACTOR

| Rank | File | LOC | Action |
|------|------|-----|--------|
| 1 | `qa/evidence.py` | 720 | Split into 4 classes |
| 2 | `composition/packs.py` | 604 | Split into 3 modules |
| 3 | `session/store.py` | 585 | Split into 5 classes |
| 4 | `adapters/sync/zen.py` | 581 | Split into 3 classes |
| 5 | `session/worktree.py` | 538 | Split into 2 classes |
| 6 | `composition/composers.py` | 532 | Extract validation/caching |
| 7 | `qa/validator.py` | 525 | Split scoring/roster |
| 8 | `paths/resolver.py` | 518 | Extract caching layer |
| 9 | `setup/questionnaire.py` | 512 | Split rendering/validation |
| 10 | `config.py` | 507 | Extract merge/validation |

---

## 🔧 REFACTORING PATTERNS

### Pattern 1: God Class → Focused Classes

**Before:**
```python
class EvidenceManager:  # 720 LOC, 29 methods
    def __init__(self, task_id): ...
    def create_next_round_dir(self): ...
    def read_bundle_summary(self): ...
    def write_implementation_report(self): ...
    # ... 25 more methods
```

**After:**
```python
class EvidencePathResolver:  # 180 LOC
    """Resolves evidence directory paths"""

class EvidenceRoundManager:  # 180 LOC
    """Manages evidence rounds"""
    def __init__(self, path_resolver: EvidencePathResolver): ...

class EvidenceReportIO:  # 180 LOC
    """Handles report file I/O"""
    def __init__(self, path_resolver: EvidencePathResolver): ...

class EvidenceBundleManager:  # 180 LOC
    """Manages validation bundles"""
    def __init__(self, report_io: EvidenceReportIO, round_mgr: EvidenceRoundManager): ...
```

### Pattern 2: Direct Instantiation → Dependency Injection

**Before:**
```python
class HookComposer:
    def __init__(self, config=None, repo_root=None):
        self.cfg_mgr = ConfigManager(repo_root)  # ❌ Direct instantiation
        self.config = config or self.cfg_mgr.load_config()
```

**After:**
```python
class HookComposer:
    def __init__(self, config_provider: IConfigProvider, repo_root=None):
        self.config_provider = config_provider  # ✅ Dependency injection
        self.config = config_provider.get_config()

# Usage
config_provider = ConfigFactory.create()
composer = HookComposer(config_provider)
```

### Pattern 3: Global State → Context Object

**Before:**
```python
_ROOT_CACHE: Path | None = None  # ❌ Global state

def get_root() -> Path:
    global _ROOT_CACHE
    if _ROOT_CACHE is None:
        _ROOT_CACHE = _discover_root()
    return _ROOT_CACHE
```

**After:**
```python
@dataclass
class PathContext:  # ✅ Context object
    _root_cache: Optional[Path] = None

    def get_root(self) -> Path:
        if self._root_cache is None:
            self._root_cache = _discover_root()
        return self._root_cache

# Or use functools.lru_cache
from functools import lru_cache

@lru_cache(maxsize=1)
def get_root() -> Path:
    return _discover_root()
```

### Pattern 4: Nested Conditionals → Guard Clauses

**Before:**
```python
def process_task(task_id: str) -> None:
    if task_id:
        task = get_task(task_id)
        if task:
            if task.state == "wip":
                if task.has_evidence():
                    # actual logic (deeply nested!)
```

**After:**
```python
def process_task(task_id: str) -> None:
    if not task_id:
        return

    task = get_task(task_id)
    if not task:
        return

    if task.state != "wip":
        return

    if not task.has_evidence():
        return

    # actual logic (not nested!)
```

### Pattern 5: Complex Type → Type Alias

**Before:**
```python
def load_config(path: Path) -> Optional[Dict[str, Union[str, int, List[Dict[str, Any]]]]]:
    ...
```

**After:**
```python
ConfigValue = Union[str, int, List[Dict[str, Any]]]
ConfigDict = Dict[str, ConfigValue]

def load_config(path: Path) -> Optional[ConfigDict]:
    ...
```

---

## 🚀 REFACTORING WORKFLOW

### Step-by-Step Process

```
1. SELECT TARGET
   ↓
2. WRITE TESTS
   • Characterization tests (capture current behavior)
   • Cover all public methods
   • Aim for 100% coverage
   ↓
3. EXTRACT INTERFACES
   • Document public API
   • Define contracts
   • Plan new class structure
   ↓
4. SPLIT CLASSES
   • Create focused classes (~180 LOC each)
   • One responsibility per class
   • Inject dependencies
   ↓
5. UPDATE CALLERS
   • Replace old usage
   • Inject dependencies
   • Update imports
   ↓
6. VERIFY TESTS
   • All tests still pass
   • No regressions
   • Coverage maintained
   ↓
7. REMOVE OLD CODE
   • Delete legacy implementation
   • Clean up imports
   • Update documentation
   ↓
8. CODE REVIEW
   • Peer review
   • Architecture review
   • Merge to main
```

### Testing Pyramid

```
       E2E Tests (Regressions)
          Integration Tests (Compositions)
             Characterization Tests (Current Behavior)
                Unit Tests (New Classes)
```

---

## 📊 QUALITY GATES

### File-Level Gates

```yaml
✅ Max LOC per file: 300
✅ Avg LOC per file: 150
✅ Max methods per class: 10
✅ Max classes per file: 2
```

### Method-Level Gates

```yaml
✅ Max LOC per method: 50
✅ Avg LOC per method: 20
✅ Max cyclomatic complexity: 10
✅ Max nesting depth: 3
```

### Architecture Gates

```yaml
✅ Direct instantiations: 0
✅ Global variables: 0
✅ Module side effects: 0
✅ Circular dependencies: 0
```

### Coverage Gates

```yaml
✅ Line coverage: >80%
✅ Branch coverage: >75%
✅ Test/source ratio: >1.5
```

---

## 🎯 PRIORITIES

### P0 - Do First (Critical)

**Week 1-4: Top 5 God Files**
- [ ] `qa/evidence.py` (720 LOC → 4 classes)
- [ ] `composition/packs.py` (604 LOC → 3 modules)
- [ ] `session/store.py` (585 LOC → 5 classes)
- [ ] `adapters/sync/zen.py` (581 LOC → 3 classes)
- [ ] `session/worktree.py` (538 LOC → 2 classes)

**Week 5-6: ConfigManager Decoupling**
- [ ] Extract `IConfigProvider` interface
- [ ] Create `ConfigFactory`
- [ ] Update 28 instantiation sites
- [ ] Inject dependencies

**Week 7-8: Global State Removal**
- [ ] Replace `task/paths.py` caches (10 variables)
- [ ] Fix `paths/management.py` singleton
- [ ] Fix `state/*` module registries (3 instances)

### P1 - Do Next (High)

**Week 9-16: Remaining God Files**
- [ ] Refactor 17 files (300-500 LOC each)

**Week 17-18: Simplify Complexity**
- [ ] Extract platform strategy pattern
- [ ] Simplify nested conditionals (1,472 blocks)

### P2 - Do Later (Medium)

- [ ] Review try/except blocks (663 total)
- [ ] Centralize config constants (50+)
- [ ] Extract type aliases

### P3 - Future (Low)

- [ ] Add missing abstractions
- [ ] Layer architecture improvements

---

## 🔍 DETECTION COMMANDS

### Find God Files
```bash
find src/edison -name "*.py" -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 300 ] && echo "$lines lines: $1"' _ {} \; | sort -rn
```

### Find Direct Instantiations
```bash
grep -rn "= [A-Z][a-zA-Z]*(" src/edison/core --include="*.py" | grep -v "Path\|Exception\|Error"
```

### Find Global State
```bash
grep -rn "^[A-Z_]* = \|^[A-Z_]*: " src/edison/core --include="*.py"
```

### Find Deep Nesting
```bash
grep -rn "        if\|        for\|        while" src/edison/core --include="*.py" | wc -l
```

### Count Methods in Files
```bash
for f in $(find src/edison/core -name "*.py"); do methods=$(grep -c "def " "$f" 2>/dev/null); echo "$methods methods: $f"; done | sort -rn | head -20
```

---

## 📚 EXAMPLE REFACTORINGS

### Example 1: EvidenceManager Split

**File:** `src/edison/core/qa/evidence.py`

**Before:** 720 LOC, 1 class, 29 methods

**After:**
```
src/edison/core/qa/
  evidence/
    __init__.py          # Public API
    path_resolver.py     # EvidencePathResolver (180 LOC)
    round_manager.py     # EvidenceRoundManager (180 LOC)
    report_io.py         # EvidenceReportIO (180 LOC)
    bundle_manager.py    # EvidenceBundleManager (180 LOC)
```

**Migration:**
```python
# Old usage
from ..qa.evidence import EvidenceManager
mgr = EvidenceManager(task_id)
latest = mgr.get_latest_round_dir()

# New usage
from ..qa.evidence import EvidenceBundleManager, create_evidence_manager
mgr = create_evidence_manager(task_id)  # Factory function
latest = mgr.get_latest_round_dir()
```

### Example 2: ConfigManager Decoupling

**File:** `src/edison/core/config.py`

**Before:**
```python
class HookComposer:
    def __init__(self, config=None, repo_root=None):
        self.cfg_mgr = ConfigManager(repo_root)
```

**After:**
```python
# config.py
class IConfigProvider(Protocol):
    def get_config(self) -> Dict[str, Any]: ...
    def get_repo_root(self) -> Path: ...

class ConfigManager(IConfigProvider):
    # ... existing implementation

class ConfigFactory:
    @staticmethod
    def create(repo_root: Optional[Path] = None) -> IConfigProvider:
        return ConfigManager(repo_root)

# hooks.py
class HookComposer:
    def __init__(self, config_provider: IConfigProvider, repo_root=None):
        self.config_provider = config_provider
        self.config = config_provider.get_config()
```

### Example 3: Global State Removal

**File:** `src/edison/core/task/paths.py`

**Before:**
```python
_ROOT_CACHE: Path | None = None
_TASK_ROOT_CACHE: Path | None = None
_QA_ROOT_CACHE: Path | None = None

def get_task_root() -> Path:
    global _TASK_ROOT_CACHE
    if _TASK_ROOT_CACHE is None:
        _TASK_ROOT_CACHE = _discover_task_root()
    return _TASK_ROOT_CACHE
```

**After:**
```python
from functools import lru_cache

@dataclass
class PathContext:
    repo_root: Path

    @lru_cache(maxsize=1)
    def get_task_root(self) -> Path:
        return _discover_task_root(self.repo_root)

    @lru_cache(maxsize=1)
    def get_qa_root(self) -> Path:
        return _discover_qa_root(self.repo_root)

# Factory
def create_path_context(repo_root: Optional[Path] = None) -> PathContext:
    root = repo_root or PathResolver.resolve_project_root()
    return PathContext(root)
```

---

## ⚠️ COMMON PITFALLS

### ❌ Don't: Create Too Many Small Classes
Bad: 50 classes with 20 LOC each
Good: 5-10 classes with 150-200 LOC each

### ❌ Don't: Over-Engineer Abstractions
Bad: Abstract base classes for everything
Good: Concrete classes with clear responsibilities

### ❌ Don't: Break Working Code Without Tests
Bad: Refactor → Test
Good: Test → Refactor

### ❌ Don't: Batch All Changes
Bad: Refactor all 27 files at once
Good: Refactor incrementally, merge often

### ❌ Don't: Ignore Callers
Bad: Change API without updating usage
Good: Update all callers before removing old code

### ✅ Do: Write Tests First
Always write characterization tests before refactoring

### ✅ Do: Keep Changes Small
One file at a time, merge frequently

### ✅ Do: Maintain Backward Compatibility
Deprecate → Migrate → Remove (not immediate breaking changes)

### ✅ Do: Document As You Go
Update docstrings and architecture docs

### ✅ Do: Get Code Reviews
Fresh eyes catch issues early

---

## 🎓 LEARNING RESOURCES

### SOLID Principles
- **S**ingle Responsibility: One reason to change
- **O**pen/Closed: Open for extension, closed for modification
- **L**iskov Substitution: Subtypes must be substitutable
- **I**nterface Segregation: Many specific interfaces > one general
- **D**ependency Inversion: Depend on abstractions, not concretions

### Recommended Reading
- "Refactoring" by Martin Fowler
- "Clean Code" by Robert C. Martin
- "Working Effectively with Legacy Code" by Michael Feathers

### Tools
- **ruff:** Python linter with complexity checks
- **pytest-cov:** Coverage measurement
- **radon:** Cyclomatic complexity
- **mypy:** Type checking

---

## 📞 GETTING HELP

### Questions to Ask

**Before Refactoring:**
- What is the single responsibility of this class?
- Can I test this in isolation?
- Are dependencies injected or created?
- Is there global state?

**During Refactoring:**
- Are my tests comprehensive?
- Have I maintained backward compatibility?
- Are new classes focused and cohesive?
- Is coupling minimized?

**After Refactoring:**
- Do all tests pass?
- Has coverage improved?
- Is the code easier to understand?
- Would I be comfortable maintaining this?

---

## ✅ CHECKLIST

### Before Starting
- [ ] Read full audit report
- [ ] Understand target architecture
- [ ] Set up dev environment
- [ ] Configure quality gates

### For Each File
- [ ] Write characterization tests
- [ ] Extract interface/API
- [ ] Plan class structure
- [ ] Implement new classes
- [ ] Inject dependencies
- [ ] Update callers
- [ ] Verify tests pass
- [ ] Remove old code
- [ ] Code review
- [ ] Merge

### After Each Milestone
- [ ] Run quality gates
- [ ] Update metrics
- [ ] Document changes
- [ ] Celebrate progress! 🎉

---

**Remember:** The goal is sustainable, maintainable code. Take your time, test thoroughly, and refactor incrementally. You've got this! 💪
