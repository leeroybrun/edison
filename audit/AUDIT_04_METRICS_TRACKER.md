# AUDIT 4: Metrics Tracker

**Purpose:** Track refactoring progress and measure improvements

---

## 📊 BASELINE METRICS (2025-11-26)

### Codebase Size
- **Total Files:** 131 Python files
- **Total LOC:** 23,566
- **Avg LOC/file:** 179
- **Test Files:** 252

### God File Metrics
- **Files >500 LOC:** 10 (CRITICAL)
- **Files 300-500 LOC:** 17 (HIGH)
- **Total God Files:** 27 (20.6% of files)
- **God File LOC:** 12,043 (51.1% of total LOC)

### Coupling Metrics
- **ConfigManager imports:** 65 files
- **ConfigManager instantiations:** 28 sites
- **Direct instantiations total:** 50+ sites

### Complexity Metrics
- **Deeply nested (4+ levels):** 1,472 blocks
- **Deeply nested (5+ levels):** 610 blocks
- **Try/except blocks:** 663
- **Complex conditionals:** 30+

### State Management
- **Global variables:** 16
- **Module-level registries:** 3
- **Singleton patterns:** 2+

---

## 🎯 TARGET METRICS

### Codebase Size
- **Total Files:** ~150 (after splitting)
- **Total LOC:** ~24,000 (slight increase due to better separation)
- **Avg LOC/file:** <150
- **Test Files:** 300+ (increased coverage)

### God File Metrics
- **Files >500 LOC:** 0
- **Files 300-500 LOC:** <5
- **Total God Files:** <5 (3.8% of files)
- **God File LOC:** <1,500 (<7% of total LOC)

### Coupling Metrics
- **ConfigManager imports:** 65 (IConfigProvider instead)
- **ConfigManager instantiations:** 0 (factory pattern)
- **Direct instantiations total:** 0

### Complexity Metrics
- **Deeply nested (4+ levels):** <500 blocks
- **Deeply nested (5+ levels):** <200 blocks
- **Try/except blocks:** <400 (reviewed & simplified)
- **Complex conditionals:** <10

### State Management
- **Global variables:** 0
- **Module-level registries:** 0 (lazy initialization)
- **Singleton patterns:** 0 (DI instead)

---

## 📈 PROGRESS TRACKER

### Week-by-Week Progress

| Week | Target | Status | Files Fixed | LOC Reduced | Notes |
|------|--------|--------|-------------|-------------|-------|
| W1 | Setup + Tests | ⏳ Pending | 0 | 0 | Infrastructure setup |
| W2 | Tests Complete | ⏳ Pending | 0 | 0 | Characterization tests |
| W3 | evidence.py | ⏳ Pending | 0 | 0 | 720→180 LOC per class |
| W4 | packs.py | ⏳ Pending | 0 | 0 | 604→200 LOC per module |
| W5 | store.py | ⏳ Pending | 0 | 0 | 585→117 LOC per class |
| W6 | zen.py | ⏳ Pending | 0 | 0 | 581→193 LOC per class |
| W7 | worktree.py | ⏳ Pending | 0 | 0 | 538→269 LOC per class |
| W8 | ConfigManager DI | ⏳ Pending | 0 | 0 | Extract interface |
| W9 | ConfigManager rollout | ⏳ Pending | 28 | 0 | Update all sites |
| W10 | Global state (paths) | ⏳ Pending | 1 | 0 | Remove 10 globals |
| W11 | Global state (other) | ⏳ Pending | 3 | 0 | Remove 6 globals |
| W12 | P0 Complete | ⏳ Pending | 5 | ~2,800 | Milestone review |

### Milestone Tracker

| Milestone | Target Date | Status | Completion |
|-----------|-------------|--------|------------|
| **P0.1: Top 5 God Files** | Week 7 | ⏳ Pending | 0% |
| **P0.2: ConfigManager DI** | Week 9 | ⏳ Pending | 0% |
| **P0.3: Global State** | Week 11 | ⏳ Pending | 0% |
| **P0 Complete** | Week 12 | ⏳ Pending | 0% |
| **P1.1: Remaining God Files** | Week 20 | ⏳ Pending | 0% |
| **P1 Complete** | Week 22 | ⏳ Pending | 0% |
| **P2 Complete** | Week 26 | ⏳ Pending | 0% |

---

## 🏆 TOP 10 GOD FILES - REFACTORING STATUS

| Rank | File | Baseline LOC | Target | Status | New LOC | Reduction |
|------|------|--------------|--------|--------|---------|-----------|
| 1 | `qa/evidence.py` | 720 | 4 classes × 180 | ⏳ | - | - |
| 2 | `composition/packs.py` | 604 | 3 modules × 200 | ⏳ | - | - |
| 3 | `session/store.py` | 585 | 5 classes × 117 | ⏳ | - | - |
| 4 | `adapters/sync/zen.py` | 581 | 3 classes × 193 | ⏳ | - | - |
| 5 | `session/worktree.py` | 538 | 2 classes × 269 | ⏳ | - | - |
| 6 | `composition/composers.py` | 532 | Split | ⏳ | - | - |
| 7 | `qa/validator.py` | 525 | Split | ⏳ | - | - |
| 8 | `paths/resolver.py` | 518 | Split | ⏳ | - | - |
| 9 | `setup/questionnaire.py` | 512 | Split | ⏳ | - | - |
| 10 | `config.py` | 507 | Split | ⏳ | - | - |
| **Total** | **5,622 LOC** | **Target** | **Status** | **-** | **-** |

**Legend:**
- ⏳ Pending
- 🚧 In Progress
- ✅ Complete
- ⚠️ Blocked

---

## 📋 DETAILED FILE METRICS

### qa/evidence.py

**Baseline:**
- LOC: 720
- Methods: 29
- Classes: 2
- Responsibilities: 4+ (path resolution, round mgmt, I/O, bundling)

**Target:**
```
evidence/
  path_resolver.py     180 LOC   EvidencePathResolver
  round_manager.py     180 LOC   EvidenceRoundManager
  report_io.py         180 LOC   EvidenceReportIO
  bundle_manager.py    180 LOC   EvidenceBundleManager
```

**Progress:**
- [ ] Characterization tests written
- [ ] Interface extracted
- [ ] Classes split
- [ ] Callers updated
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged

**Metrics After:**
- LOC: -
- Methods: -
- Classes: 4
- Avg LOC/class: -

---

### composition/packs.py

**Baseline:**
- LOC: 604
- Methods: 19
- Classes: 6
- Responsibilities: Pack loading, dependencies, composition, auto-activation

**Target:**
```
packs/
  loader.py           200 LOC   PackLoader, PackManifest
  dependencies.py     200 LOC   DependencyResolver
  activation.py       200 LOC   PackActivator
```

**Progress:**
- [ ] Characterization tests written
- [ ] Interface extracted
- [ ] Modules split
- [ ] Callers updated
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged

**Metrics After:**
- LOC: -
- Methods: -
- Modules: 3
- Avg LOC/module: -

---

### session/store.py

**Baseline:**
- LOC: 585
- Methods: 27
- Classes: 0 (all functions)
- Responsibilities: CRUD, locking, state mgmt, migration, config

**Target:**
```
session/
  store/
    crud.py           117 LOC   SessionCRUD
    locking.py        117 LOC   SessionLocking
    state.py          117 LOC   SessionStateManager
    migration.py      117 LOC   SessionMigration
    paths.py          117 LOC   SessionPathResolver
```

**Progress:**
- [ ] Characterization tests written
- [ ] Interface extracted
- [ ] Classes created
- [ ] Callers updated
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged

**Metrics After:**
- LOC: -
- Methods: -
- Classes: 5
- Avg LOC/class: -

---

### adapters/sync/zen.py

**Baseline:**
- LOC: 581
- Methods: 17
- Classes: 1 (ZenSync)
- Responsibilities: Adapter, composition, guidelines, rules

**Target:**
```
adapters/sync/
  zen/
    adapter.py        193 LOC   ZenAdapter
    composer.py       193 LOC   ZenComposer
    registry.py       193 LOC   ZenRegistry
```

**Progress:**
- [ ] Characterization tests written
- [ ] Interface extracted
- [ ] Classes split
- [ ] Callers updated
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged

**Metrics After:**
- LOC: -
- Methods: -
- Classes: 3
- Avg LOC/class: -

---

### session/worktree.py

**Baseline:**
- LOC: 538
- Methods: -
- Classes: -
- Responsibilities: Worktree mgmt, git ops, cleanup, state

**Target:**
```
session/
  worktree/
    manager.py        269 LOC   WorktreeManager
    git_ops.py        269 LOC   WorktreeGitOps
```

**Progress:**
- [ ] Characterization tests written
- [ ] Interface extracted
- [ ] Classes split
- [ ] Callers updated
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Merged

**Metrics After:**
- LOC: -
- Methods: -
- Classes: 2
- Avg LOC/class: -

---

## 🎯 COUPLING METRICS TRACKER

### ConfigManager Decoupling

**Baseline:** 28 direct instantiation sites

| Module | Sites | Status | Notes |
|--------|-------|--------|-------|
| `ide/*` | 5 | ⏳ | HookComposer, CommandComposer, SettingsComposer |
| `adapters/*` | 6 | ⏳ | All sync adapters |
| `task/*` | 4 | ⏳ | Task management modules |
| `composition/*` | 3 | ⏳ | Composition engine |
| `session/*` | 3 | ⏳ | Session management |
| `utils/*` | 3 | ⏳ | Utility modules |
| `qa/*` | 2 | ⏳ | QA modules |
| `rules/*` | 1 | ⏳ | Rules engine |
| Other | 1 | ⏳ | Misc |
| **Total** | **28** | **⏳** | - |

**Target:** 0 direct instantiations (all use factory/DI)

**Progress:**
- [ ] IConfigProvider interface created
- [ ] ConfigFactory implemented
- [ ] Update ide/* (5 sites)
- [ ] Update adapters/* (6 sites)
- [ ] Update task/* (4 sites)
- [ ] Update composition/* (3 sites)
- [ ] Update session/* (3 sites)
- [ ] Update utils/* (3 sites)
- [ ] Update qa/* (2 sites)
- [ ] Update rules/* (1 site)
- [ ] Update other (1 site)
- [ ] All tests passing

---

## 🌍 GLOBAL STATE ELIMINATION

**Baseline:** 16 global variables

| Location | Variables | Status | Replacement |
|----------|-----------|--------|-------------|
| `task/paths.py` | 10 caches | ⏳ | PathContext + lru_cache |
| `paths/management.py` | 1 singleton | ⏳ | Factory function |
| `paths/resolver.py` | 1 cache | ⏳ | lru_cache decorator |
| `composition/includes.py` | 1 override | ⏳ | Parameter passing |
| `state/guards.py` | 1 registry | ⏳ | Lazy initialization |
| `state/actions.py` | 1 registry | ⏳ | Lazy initialization |
| `state/conditions.py` | 1 registry | ⏳ | Lazy initialization |
| **Total** | **16** | **⏳** | - |

**Target:** 0 global variables

**Progress:**
- [ ] PathContext class created
- [ ] Refactor task/paths.py (10 globals)
- [ ] Refactor paths/management.py (1 singleton)
- [ ] Refactor paths/resolver.py (1 cache)
- [ ] Refactor composition/includes.py (1 override)
- [ ] Refactor state registries (3 instances)
- [ ] All tests passing
- [ ] No global state remaining

---

## 🧪 TEST COVERAGE METRICS

| Category | Baseline | Target | Current | Status |
|----------|----------|--------|---------|--------|
| Line Coverage | Unknown | >80% | - | ⏳ |
| Branch Coverage | Unknown | >75% | - | ⏳ |
| Test Files | 252 | 300+ | 252 | ⏳ |
| Test/Source Ratio | Unknown | >1.5 | - | ⏳ |

**Coverage by Module:**

| Module | Baseline | Target | Current | Status |
|--------|----------|--------|---------|--------|
| `qa/evidence.py` | Unknown | 100% | - | ⏳ |
| `composition/packs.py` | Unknown | 100% | - | ⏳ |
| `session/store.py` | Unknown | 100% | - | ⏳ |
| `adapters/sync/zen.py` | Unknown | 100% | - | ⏳ |
| `session/worktree.py` | Unknown | 100% | - | ⏳ |

---

## 🎨 COMPLEXITY METRICS

### Nested Blocks Reduction

| Level | Baseline | Target | Current | Reduction |
|-------|----------|--------|---------|-----------|
| 4+ indent | 1,472 | <500 | - | - |
| 5+ indent | 610 | <200 | - | - |

**Files with Most Nesting:**

| File | 4+ Blocks | 5+ Blocks | Status |
|------|-----------|-----------|--------|
| TBD | - | - | ⏳ |

### Try/Except Reduction

| Metric | Baseline | Target | Current | Status |
|--------|----------|--------|---------|--------|
| Total blocks | 663 | <400 | - | ⏳ |
| Avg per file | 5.06 | <3 | - | ⏳ |

**Review Progress:**
- [ ] Identify unnecessary defensive catches
- [ ] Replace bare except with specific exceptions
- [ ] Consolidate error handling
- [ ] Document exception strategy

---

## 📉 TREND ANALYSIS

### Weekly God File Count

| Week | >500 LOC | 300-500 LOC | Total | % of Files |
|------|----------|-------------|-------|------------|
| W0 (baseline) | 10 | 17 | 27 | 20.6% |
| W1 | - | - | - | - |
| W2 | - | - | - | - |
| W12 | 5 (target) | 12 | 17 | 11.3% |
| W26 | 0 (target) | <5 | <5 | <3.8% |

### Weekly Average File Size

| Week | Avg LOC | Max LOC | Trend |
|------|---------|---------|-------|
| W0 (baseline) | 179 | 720 | - |
| W1 | - | - | - |
| W2 | - | - | - |
| W12 | 165 (target) | 450 | ↓ |
| W26 | <150 (target) | <300 | ↓ |

### Weekly Coupling Index

| Week | Direct Inst. | Global Vars | Total |
|------|--------------|-------------|-------|
| W0 (baseline) | 28 | 16 | 44 |
| W1 | - | - | - |
| W2 | - | - | - |
| W12 | 0 (target) | 0 (target) | 0 |

---

## 🏅 SUCCESS CRITERIA

### Phase 1 (P0) Success - Week 12

- [x] Top 5 god files refactored (5,622 LOC → ~900 LOC per module)
- [x] ConfigManager decoupled (28 sites → 0 direct instantiations)
- [x] Global state eliminated (16 vars → 0)
- [x] All tests passing (no regressions)
- [x] Coverage >80% on refactored modules

### Phase 2 (P1) Success - Week 22

- [ ] All 27 god files refactored
- [ ] Platform strategy pattern implemented
- [ ] Nested blocks reduced (1,472 → <500)
- [ ] Coverage >80% overall

### Phase 3 (P2) Success - Week 26

- [ ] Try/except blocks reviewed (663 → <400)
- [ ] Config constants centralized (50+ → YAML)
- [ ] Type aliases extracted
- [ ] Documentation updated

### Final Success Criteria

- [ ] 0 files >500 LOC
- [ ] <5 files >300 LOC
- [ ] 0 direct instantiations
- [ ] 0 global variables
- [ ] <500 deeply nested blocks (4+)
- [ ] >80% test coverage
- [ ] All quality gates passing
- [ ] Team trained on new architecture

---

## 📊 DASHBOARD

```
╔════════════════════════════════════════════════════════════╗
║           REFACTORING PROGRESS DASHBOARD                   ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  P0 MILESTONES                         Status: ⏳ 0%      ║
║  ┌────────────────────────────────────────────────────┐   ║
║  │ P0.1: Top 5 God Files          [░░░░░░░░░░] 0/5   │   ║
║  │ P0.2: ConfigManager DI         [░░░░░░░░░░] 0/28  │   ║
║  │ P0.3: Global State             [░░░░░░░░░░] 0/16  │   ║
║  └────────────────────────────────────────────────────┘   ║
║                                                            ║
║  GOD FILE REDUCTION                                        ║
║  ┌────────────────────────────────────────────────────┐   ║
║  │ Baseline: 27 files, 12,043 LOC (51.1%)            │   ║
║  │ Current:  27 files, 12,043 LOC (51.1%)  ⚫⚫⚫⚫⚫   │   ║
║  │ Target:   <5 files, <1,500 LOC (<7%)    ⚪⚪⚪⚪⚪   │   ║
║  └────────────────────────────────────────────────────┘   ║
║                                                            ║
║  COUPLING REDUCTION                                        ║
║  ┌────────────────────────────────────────────────────┐   ║
║  │ Baseline: 44 coupling sites                        │   ║
║  │ Current:  44 coupling sites            ⚫⚫⚫⚫⚫     │   ║
║  │ Target:   0 coupling sites             ⚪⚪⚪⚪⚪     │   ║
║  └────────────────────────────────────────────────────┘   ║
║                                                            ║
║  COMPLEXITY REDUCTION                                      ║
║  ┌────────────────────────────────────────────────────┐   ║
║  │ Baseline: 1,472 nested blocks                      │   ║
║  │ Current:  1,472 nested blocks          ⚫⚫⚫⚫⚫     │   ║
║  │ Target:   <500 nested blocks           ⚪⚪⚪⚪⚪     │   ║
║  └────────────────────────────────────────────────────┘   ║
║                                                            ║
║  OVERALL PROGRESS                         0% Complete     ║
║  [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0/26w║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

## 🔄 UPDATE INSTRUCTIONS

### How to Update This Tracker

1. **After Each File Refactoring:**
   - Update "Top 10 God Files" table with new LOC
   - Mark status as ✅ Complete
   - Update progress percentage

2. **After Each Week:**
   - Fill in weekly progress row
   - Update trend analysis
   - Update dashboard ASCII art

3. **After Each Milestone:**
   - Mark milestone as complete
   - Calculate metrics
   - Update success criteria checklist

4. **Continuous:**
   - Run detection commands to verify metrics
   - Update test coverage numbers
   - Track any blockers or issues

---

**Last Updated:** 2025-11-26 (Baseline)
**Next Update:** TBD (After first refactoring)
**Update Frequency:** Weekly during active refactoring
