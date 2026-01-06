# Edison Framework Architecture

## System Overview

Edison is an AI-automated software development framework that coordinates multiple LLM agents through a centralized orchestrator. The system enforces strict workflows via declarative state machines and maintains all configuration through YAML files. This architecture enables predictable, auditable, and reproducible AI-driven development workflows.

### Core Design Principles

1. **YAML-Driven Configuration**: All behavior, workflows, and constraints are defined in YAML configuration files. No hardcoded values in code.
2. **Declarative State Machines**: Task, QA, and Session lifecycles are governed by state machine definitions with guards, conditions, and actions.
3. **Layered Composition**: Content (agents, validators, guidelines) is composed from three layers: Core (bundled) → Packs (technology-specific) → Project (customization).
4. **Entity-Based Persistence**: Tasks, Sessions, and QA Records are first-class entities with metadata, state history, and JSON persistence.
5. **File-Based Storage**: All data persists as JSON files in the `.edison/` directory structure, enabling git-friendly version control.
6. **CLI-First Design**: All operations are CLI-driven with auto-discovery of commands from domain subfolders.

---

## Core Components

### 1. CLI Layer (`edison.cli`)

The CLI layer provides the user-facing interface with automatic command discovery.

```
edison.cli/
├── _dispatcher.py          # Auto-discovers commands from domain folders
├── commands/               # Root-level commands (init)
│   └── init.py            # Project initialization
├── session/                # Session management commands
│   ├── create.py          # Create new session
│   ├── next.py            # Compute next actions
│   ├── status.py          # Show session status
│   ├── close.py           # Close session
│   ├── validate.py        # Validate session state
│   └── recovery/          # Session recovery utilities
├── task/                   # Task management commands
│   ├── new.py             # Create task
│   ├── claim.py           # Claim task for session
│   ├── waves.py           # Plan parallelizable task waves (depends_on)
│   ├── blocked.py         # Explain todo tasks blocked by depends_on
│   ├── relate.py          # Link related tasks (non-blocking)
│   ├── ready.py           # List ready-to-claim tasks (legacy completion alias)
│   ├── done.py            # Complete task (wip→done)
│   ├── status.py          # Show task status
│   └── split.py           # Split task into subtasks
├── qa/                     # QA and validation commands
│   ├── new.py             # Create QA record
│   ├── run.py             # Run validators
│   ├── promote.py         # Promote QA state
│   ├── validate.py        # Validate task
│   └── bundle.py          # Bundle validation evidence
├── compose/                # Composition commands
│   ├── all.py             # Compose all artifacts
│   ├── settings.py        # Compose IDE settings
│   ├── commands.py        # Compose slash commands
│   └── hooks.py           # Compose git hooks
├── config/                 # Configuration commands
│   ├── validate.py        # Validate configuration
│   ├── show.py            # Display configuration
│   └── configure.py       # Configure project
├── git/                    # Git/worktree management
│   ├── worktree_create.py  # CLI: worktree-create (create worktree for session)
│   ├── worktree_restore.py # CLI: worktree-restore (restore archived worktree)
│   ├── worktree_archive.py # CLI: worktree-archive (archive worktree)
│   ├── worktree_cleanup.py # CLI: worktree-cleanup (cleanup worktrees)
│   ├── worktree_list.py    # CLI: worktree-list (list worktrees)
│   ├── worktree_health.py  # CLI: worktree-health (health checks)
│   └── status.py          # Show git status
├── rules/                  # Rule management
│   ├── list.py            # List all rules
│   ├── check.py           # Check rule compliance
│   └── show.py            # Show rule details
└── orchestrator/           # Orchestrator management
    ├── start.py           # Start orchestrator
    └── profiles.py        # Manage orchestrator profiles
```

**Key Features**:
- **Auto-Discovery**: Commands are automatically registered by scanning domain folders for `.py` files
- **Hierarchical Structure**: Commands organized as `edison <domain> <command>` (e.g., `edison task claim`)
- **Consistent Interface**: All commands follow common patterns for arguments and output

---

### 2. Core Library (`edison.core`)

The core library implements all business logic, state management, and workflows.

```
edison.core/
├── entity/                 # Entity framework
│   ├── base.py            # BaseEntity, EntityMetadata, StateHistoryEntry
│   ├── repository.py      # Repository protocol
│   ├── file_repository.py # JSON file-based repository
│   ├── manager.py         # Entity lifecycle management
│   └── session_scoped.py  # Session-scoped entity helpers
├── state/                  # State machine engine
│   ├── engine.py          # RichStateMachine implementation
│   ├── guards.py          # Guard registry and functions
│   ├── conditions.py      # Condition registry and checks
│   ├── actions.py         # Action registry and execution
│   └── validator.py       # State machine validation
├── task/                   # Task domain
│   ├── models.py          # Task entity definition
│   ├── repository.py      # Task persistence
│   ├── manager.py         # Task lifecycle operations
│   └── workflow.py        # Task state transitions
├── session/                # Session domain
│   ├── core/              # Core session types
│   │   ├── models.py      # Session, TaskEntry, QAEntry, GitInfo
│   │   ├── context.py     # SessionContext helpers
│   │   ├── id.py          # Session ID generation/validation
│   │   └── naming.py      # Session naming conventions
│   ├── lifecycle/         # Session lifecycle
│   │   ├── manager.py     # Session creation/closing
│   │   ├── recovery.py    # Session recovery after failures
│   │   └── transaction.py # Transactional session updates
│   ├── persistence/       # Session persistence
│   │   ├── repository.py  # Session storage
│   │   ├── database.py    # Session database operations
│   │   └── graph.py       # Session dependency graphs
│   ├── worktree/          # Git worktree management
│   │   ├── manager.py     # Worktree creation/cleanup
│   │   └── cleanup.py     # Automatic cleanup
│   └── next/              # Next action computation
│       ├── compute.py     # Main computation logic
│       ├── actions.py     # Action inference
│       ├── rules.py       # Rule application
│       └── output.py      # Output formatting
├── qa/                     # QA and validation domain
│   ├── models.py          # QARecord entity
│   ├── manager.py         # QA lifecycle operations
│   ├── validator/         # Validator utilities
│   │   └── base.py        # Template processing, dimension validation
│   ├── engines/           # Unified validator engine system
│   │   ├── base.py        # ValidationResult, ValidatorConfig, EngineProtocol
│   │   ├── executor.py    # ValidationExecutor - centralized execution
│   │   ├── cli.py         # CLIEngine - executes CLI validators
│   │   ├── delegated.py   # PalMCPEngine - orchestrator delegation
│   │   ├── registry.py    # EngineRegistry - engine/validator management
│   │   └── parsers/       # CLI output parsers
│   │       ├── codex.py   # Codex JSONL parser
│   │       ├── claude.py  # Claude JSON parser
│   │       ├── gemini.py  # Gemini JSON parser
│   │       ├── auggie.py  # Auggie JSON parser
│   │       └── coderabbit.py # CodeRabbit text parser
│   ├── evidence/          # Validation evidence
│   │   ├── io.py          # Evidence file I/O
│   │   ├── analysis.py    # Evidence analysis
│   │   ├── reports.py     # Report generation
│   │   └── rounds.py      # Multi-round validation
│   ├── bundler/           # Validation bundling
│   │   └── bundler.py     # Bundle evidence for promotion
│   └── workflow/          # QA workflow
│       ├── repository.py  # QA record storage
│       └── transaction.py # QA state transitions
├── composition/            # Unified composition system
│   ├── context.py         # CompositionContext (unified context with context_vars)
│   ├── engine.py          # TemplateEngine (10-step transformation pipeline)
│   ├── core/              # Core composition infrastructure
│   │   ├── base.py        # CompositionBase, CompositionPathResolver
│   │   ├── discovery.py   # LayerDiscovery for file discovery
│   │   └── sections.py    # SectionParser, SectionRegistry
│   ├── strategies/        # Composition strategies
│   │   ├── base.py        # CompositionStrategy, LayerContent
│   │   └── markdown.py    # MarkdownCompositionStrategy (sections + template processing)
│   ├── transformers/      # Template transformation pipeline
│   │   ├── base.py        # ContentTransformer, TransformContext, TransformerPipeline
│   │   ├── includes.py    # {{include:path}}, {{include-section:path#name}}
│   │   ├── conditionals.py # {{if:COND}}...{{/if}}, {{include-if:COND:path}}
│   │   ├── loops.py       # {{#each collection}}...{{/each}} with context_vars
│   │   ├── variables.py   # {{config.key}}, {{timestamp}}, custom context vars
│   │   ├── references.py  # {{reference-section:path#name|purpose}}
│   │   └── functions.py   # {{fn:name(args)}} - custom Python functions
│   ├── generators/        # Content generators (ComposableGenerator base)
│   │   ├── base.py        # ComposableGenerator abstract base class
│   │   ├── available_agents.py # AgentRosterGenerator
│   │   ├── available_validators.py # ValidatorRosterGenerator
│   │   └── state_machine.py # StateMachineGenerator
│   ├── registries/        # Content registries (ComposableRegistry pattern)
│   │   ├── _base.py       # ComposableRegistry with built-in context_vars
│   │   ├── generic.py     # GenericRegistry (config-driven for most content types)
│   │   ├── constitutions.py # ConstitutionRegistry (constitution-specific context)
│   │   ├── schemas.py     # JsonSchemaRegistry (JSON composition)
│   │   └── _types_manager.py # ComposableTypesManager (CLI orchestration)
│   ├── packs/             # Pack system
│   │   ├── registry.py    # Pack discovery and activation
│   │   └── activation.py  # Pack activation logic
│   └── output/            # Output utilities
│       ├── config.py      # OutputConfigLoader
│       ├── writer.py      # CompositionFileWriter
│       └── headers.py     # Generated file headers
├── rules/                  # Rule system
│   ├── engine.py          # RulesEngine (enforcement + guidance)
│   ├── models.py          # Rule, RuleViolation
│   ├── checkers.py        # Rule checker registry
│   └── errors.py          # Rule-specific exceptions
├── adapters/               # Unified platform adapters
│   ├── base.py            # PlatformAdapter base class
│   ├── platforms/         # Platform-specific adapters
│   │   ├── claude.py      # ClaudeAdapter (.claude/, CLAUDE.md)
│   │   ├── cursor.py      # CursorAdapter (.cursor/)
│   │   ├── pal.py/        # PalAdapter package (.pal/)
│   │   ├── codex.py       # CodexAdapter (.codex/)
│   │   └── coderabbit.py  # CoderabbitAdapter (.coderabbit.yaml)
│   └── components/        # Shared adapter components
│       ├── base.py        # AdapterComponent base
│       ├── commands.py    # CommandComposer (slash commands)
│       ├── hooks.py       # HookComposer (git hooks)
│       └── settings.py    # SettingsComposer (IDE settings)
├── config/                 # Configuration management
│   ├── manager.py         # ConfigManager (loads/merges YAML)
│   ├── base.py            # Base configuration types
│   ├── cache.py           # Configuration caching
│   └── domains/           # Domain-specific typed configs
│       ├── task.py        # Task configuration
│       ├── session.py     # Session configuration
│       ├── qa.py          # QA configuration
│       ├── workflow.py    # Workflow configuration
│       ├── composition.py # CompositionConfig - typed accessor for composition.yaml
│       ├── orchestrator.py # Orchestrator configuration
│       └── ...
├── orchestrator/           # Orchestrator management
│   ├── launcher.py        # Launch orchestrator sessions
│   └── utils.py           # Orchestrator utilities
├── utils/                  # Shared utilities
│   ├── io/                # I/O utilities
│   │   ├── core.py        # File operations
│   │   ├── json.py        # JSON I/O with validation
│   │   ├── yaml.py        # YAML I/O
│   │   └── locking.py     # File locking
│   ├── paths/             # Path utilities
│   │   ├── resolver.py    # Path resolution
│   │   ├── management.py  # Management path helpers
│   │   └── project.py     # Project path detection
│   ├── git/               # Git utilities
│   │   ├── repository.py  # Git repository operations
│   │   ├── worktree.py    # Worktree helpers
│   │   ├── diff.py        # Diff parsing
│   │   └── status.py      # Status parsing
│   ├── cli/               # CLI utilities
│   │   ├── arguments.py   # Argument parsing
│   │   ├── output.py      # Output formatting
│   │   └── errors.py      # Error handling
│   └── text/              # Text utilities
│       ├── markdown.py    # Markdown processing
│       └── anchors.py     # Anchor extraction
└── mcp/                    # MCP integration
    └── config.py          # MCP configuration generation
```

---

### 3. Data Layer (`edison.data`)

The data layer provides bundled configuration, templates, and content.

```
edison.data/
├── config/                 # Default YAML configurations
│   ├── state-machine.yaml # State machine definitions
│   ├── workflow.yaml      # Workflow rules
│   ├── composition.yaml   # Composition settings
│   ├── commands.yaml      # Slash command templates
│   ├── hooks.yaml         # Git hook templates
│   ├── orchestrator.yaml  # Orchestrator configuration
│   ├── validation.yaml    # Validation configuration (presets, engines, validators, evidence)
│   ├── session.yaml       # Session configuration
│   ├── tasks.yaml         # Task configuration
│   └── ...                # 40+ configuration files
├── constitutions/          # Role constitutions (foundational rules)
│   ├── agents.md          # Agent constitution (discovered from filename)
│   ├── orchestrator.md    # Orchestrator constitution
│   └── validators.md      # Validator constitution
├── guidelines/             # Guideline documents
│   ├── shared/            # Shared guidelines
│   │   └── TDD.md         # TDD workflow
│   ├── agents/            # Agent-specific guidelines
│   ├── orchestrators/     # Orchestrator guidelines
│   └── validators/        # Validator guidelines
├── agents/                 # Agent prompt templates
│   ├── api-builder.md     # API development agent
│   ├── component-builder.md # UI component agent
│   ├── database-architect.md # Database design agent
│   ├── feature-implementer.md # Feature implementation agent
│   └── test-engineer.md   # Testing agent
├── validators/             # Validator prompt templates
│   ├── critical/          # Critical validators (must pass)
│   │   └── ...
│   └── global/            # Global validators (all tasks)
│       └── ...
├── packs/                  # Technology packs
│   ├── typescript/        # TypeScript pack
│   │   ├── config/
│   │   ├── guidelines/
│   │   ├── validators/
│   │   └── examples/
│   ├── nextjs/            # Next.js pack
│   ├── react/             # React pack
│   ├── prisma/            # Prisma pack
│   ├── tailwind/          # Tailwind pack
│   ├── vitest/            # Vitest pack
│   └── _template/         # Pack template
├── rules/                  # Rule definitions
│   ├── registry.yml       # Rule registry
│   ├── file_patterns/     # File pattern rules
│   └── task_types/        # Task type rules
├── start/                  # Session start prompts
│   ├── START_NEW_SESSION.md # New session workflow
│   ├── START_RESUME_SESSION.md # Resume session workflow
│   └── START_VALIDATE_SESSION.md # Validate session workflow
├── templates/              # File templates
│   ├── commands/          # Slash command templates
│   ├── hooks/             # Git hook templates
│   ├── setup/             # Project setup templates
│   └── mcp.json.template  # MCP configuration template
└── schemas/                # JSON schemas
    ├── config/            # Configuration schemas
    ├── domain/            # Domain entity schemas
    ├── manifests/         # Manifest schemas
    └── reports/           # Report schemas
```

---

## State Machines

Edison uses declarative state machines (defined in `state-machine.yaml`) to enforce entity lifecycles.

### Task State Machine

**States**: `todo` → `wip` → `done` → `validated` (with `blocked` escape hatch)

```
┌──────┐
│ todo │ ← Initial state (awaiting claim)
└──┬───┘
   │ claim (guard: can_start_task, condition: task_claimed)
   ↓
┌─────┐
│ wip │ ← Work in progress
└──┬──┘
   │ ready (guard: can_finish_task, conditions: all_work_complete, no_pending_commits)
   ↓
┌──────┐
│ done │ ← Implementation complete, awaiting validation
└──┬───┘
   │ promote (guard: can_finish_task, after QA approval)
   ↓
┌───────────┐
│ validated │ ← Final state (QA approved)
└───────────┘

   ┌─────────┐
   │ blocked │ ← Escape hatch for external blockers
   └─────────┘
```

**Guards**:
- `can_start_task`: Validates task is claimable
- `can_finish_task`: Ensures work is complete before transition
- `has_blockers`: Checks for blocking conditions
- `always_allow`: Permissive guard for recovery paths

**Conditions**:
- `task_claimed`: Task must be claimed by a session
- `all_work_complete`: All implementation criteria met
- `no_pending_commits`: No uncommitted changes

**Actions**:
- `record_completion_time`: Timestamp when task completed
- `record_blocker_reason`: Log why task is blocked

---

### QA State Machine

**States**: `waiting` → `todo` → `wip` → `done` → `validated`

```
┌─────────┐
│ waiting │ ← Initial state (pending hand-off from implementation)
└────┬────┘
     │ handoff
     ↓
┌──────┐
│ todo │ ← QA backlog
└──┬───┘
   │ start
   ↓
┌─────┐
│ wip │ ← Validation in progress (validators running)
└──┬──┘
   │ complete (all validators finished)
   ↓
┌──────┐
│ done │ ← Validation complete (awaiting approval)
└──┬───┘
   │ promote (if approved) / reject (if failed)
   ↓
┌───────────┐
│ validated │ ← Final state (approved)
└───────────┘
```

**Key Transitions**:
- `waiting → todo`: Implementation complete, QA ready to start
- `todo → wip`: Validators launched
- `wip → done`: All validators finished
- `done → validated`: All blocking validators passed
- `done → wip`: Validators rejected, re-run needed

---

### Session State Machine

**States**: `active` → `closing` → `validated` → `archived` (with `recovery` escape hatch)

```
┌────────┐
│ active │ ← Work in progress
└───┬────┘
    │ close (guard: can_complete_session, condition: ready_to_close)
    ↓
┌─────────┐
│ closing │ ← Awaiting final validation
└────┬────┘
     │ validate (guard: can_complete_session)
     ↓
┌───────────┐
│ validated │ ← Session validated
└─────┬─────┘
      │ archive
      ↓
┌──────────┐
│ archived │ ← Final state (git worktree cleaned up)
└──────────┘

  ┌──────────┐
  │ recovery │ ← Escape hatch for timeout/failure recovery
  └──────────┘
```

**Special States**:
- `draft`: Optional pre-active state (not shown, deprecated)
- `blocked`: Session blocked on validation or dependencies
- `recovery`: Session in recovery after timeout or failure

**Actions**:
- `create_worktree`: Create git worktree when session activates
- `finalize_session`: Clean up and prepare for closure
- `record_activation_time`: Timestamp when session started
- `record_completion_time`: Timestamp when session completed
- `notify_session_start`: Trigger any session start hooks

---

## Composition System

Edison's composition system assembles content from multiple layers with intelligent merging.

### Layer Hierarchy

**Core → Packs → Overlay Layers** (later layers override earlier)

1. **Core Layer**: Bundled defaults from `edison.data/`
   - Location: `edison.data/{type}/{name}.md`
   - Example: `edison.data/agents/api-builder.md`
   - Immutable (shipped with Edison)

2. **Pack Layer**: Technology-specific additions/overrides (from ALL pack roots)
   - Location: `edison.data/packs/{pack}/{type}/{name}.md` (new entities)
   - Location: `edison.data/packs/{pack}/{type}/overlays/{name}.md` (overrides)
   - Additional pack roots: `<overlay-layer-root>/packs/{pack}/...`
   - Example: `edison.data/packs/nextjs/agents/overlays/api-builder.md`
   - Activated via project config

3. **Overlay Layers**: Customization roots that participate in composition
   - Default overlay stack: `user → project`
   - User layer (not committed by default):
     - Location: `~/.edison/{type}/{name}.md` (new entities)
     - Location: `~/.edison/{type}/overlays/{name}.md` (overrides)
   - Project layer:
     - Location: `.edison/{type}/{name}.md` (new entities)
     - Location: `.edison/{type}/overlays/{name}.md` (overrides)
   - Extra layers (e.g. `company`) can be inserted via `config/layers.yaml` (loaded from core → user → project → project-local).

**Config-only local overrides** (highest precedence for YAML config):
- `.edison/config.local/*.yml|*.yaml` (uncommitted; intended for per-user per-project settings like enabling personal packs)

### Section-Based Composition

Content is composed using HTML comment markers:

```markdown
<!-- section:role -->
You are an API builder specializing in REST APIs.
<!-- end:section -->

<!-- section:workflow -->
Follow these steps:
1. Analyze requirements
2. Design endpoints
<!-- end:section -->
```

**Section Modes**:

1. **Replace Mode** (default): Replace entire section
   ```markdown
   <!-- section:role mode:replace -->
   Updated role definition replaces core entirely
   <!-- end:section -->
   ```

2. **Append Mode**: Add to existing section
   ```markdown
   <!-- section:workflow mode:append -->
   Additional workflow steps appended to core
   <!-- end:section -->
   ```

3. **New Section**: Add entirely new section
   ```markdown
   <!-- section:project-specific new:true -->
   This section is only in this project
   <!-- end:section -->
   ```

### Deduplication

The composition engine deduplicates content using **shingle matching**:
- Text is split into n-grams (shingles)
- Similar sections are detected via Jaccard similarity
- Duplicate content is removed from lower-priority layers

Configured in `composition.yaml`:
```yaml
deduplication:
  enabled: true
  threshold: 0.8  # 80% similarity = duplicate
  shingleSize: 4  # 4-word shingles
```

### Output Structure

Composed artifacts are written to `_generated/`:

```
_generated/
├── agents/              # Composed agent prompts
│   ├── api-builder.md
│   ├── component-builder.md
│   └── ...
├── validators/          # Composed validator prompts
│   ├── critical/
│   └── global/
├── constitutions/       # Composed constitutions
│   ├── AGENTS.md
│   ├── ORCHESTRATOR.md
│   └── VALIDATORS.md
├── guidelines/          # Composed guidelines
│   ├── TDD.md
│   └── ...
└── clients/             # IDE-specific files
    ├── claude.md        # Claude-specific content
    └── pal.md           # Pal-specific content
```

**Generated File Headers**: All `_generated/` files include a header:
```markdown
<!-- GENERATED FILE - DO NOT EDIT -->
<!-- This file was auto-generated by Edison's composition system -->
<!-- To make changes, edit the source files in core/packs/project layers -->
<!-- Generated: 2025-12-01T18:30:00Z -->
```

---

## Entity Framework

Edison uses a consistent entity model across all domains.

### BaseEntity Structure

All entities (Task, Session, QARecord) inherit from `BaseEntity`:

```python
@dataclass
class BaseEntity:
    id: EntityId              # Unique identifier (e.g., "T-001", "S-20251201-183000")
    state: str                # Current state (e.g., "wip", "active")
    metadata: EntityMetadata  # Timestamps, ownership
    state_history: List[StateHistoryEntry]  # Audit trail
```

### EntityMetadata

Every entity tracks metadata:

```python
@dataclass
class EntityMetadata:
    created_at: str       # ISO timestamp (UTC)
    updated_at: str       # ISO timestamp (UTC)
    created_by: Optional[str]  # Owner/creator
    session_id: Optional[str]  # Associated session
```

### StateHistoryEntry

Every state transition is recorded:

```python
@dataclass
class StateHistoryEntry:
    from_state: str       # Previous state
    to_state: str         # New state
    timestamp: str        # When transition occurred
    reason: Optional[str] # Why transition occurred
    violations: List[str] # Any rule violations (warnings)
```

### Repository Pattern

Entities are persisted using the Repository pattern:

```python
class Repository(Protocol):
    def get(self, id: EntityId) -> Optional[BaseEntity]: ...
    def save(self, entity: BaseEntity) -> None: ...
    def delete(self, id: EntityId) -> None: ...
    def list(self) -> List[BaseEntity]: ...
```

**FileRepository** implementation:
- Stores entities as JSON files in `.edison/`
- Uses file locking to prevent concurrent modifications
- Validates entities against JSON schemas before writing

### Session-Scoped Entities

Tasks and QA records are scoped to sessions and persisted as **Markdown files**
in a directory-based state machine. The directory layout is the **single source
of truth** for state (not a JSON index).

```
.project/sessions/<state>/<session-id>/
├── session.json                 # Session entity (metadata + activity log; not a task index)
├── tasks/
│   ├── <state>/
│   │   ├── <task-id>.md        # Task entity
│   │   └── ...
│   └── ...
└── qa/
    ├── <state>/
    │   ├── <task-id>-qa.md     # QA entity
    │   └── ...
    └── ...
```

Notes:
- `edison session status --json` reports `tasks` / `qa` by **scanning the directories** above.
- `edison session show` prints the raw `session.json` on disk for recovery/debugging.

---

## Workflow Engine

The workflow engine orchestrates the development loop using state machines and rules.

### Workflow Loop

The main workflow loop is driven by `edison session next`:

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   1. Load Session State                        │
│      ↓                                          │
│   2. Compute Next Actions (Rules Engine)       │
│      ↓                                          │
│   3. Present Actions to Orchestrator           │
│      ↓                                          │
│   4. Orchestrator Executes Action              │
│      ↓                                          │
│   5. Update Entity State                       │
│      ↓                                          │
│   6. Record State Transition                   │
│      └──────────────────────────────────────┐  │
│                                              ↓  │
└──────────────────────────────────────────────┘  │
                                                  │
                           Loop Back ─────────────┘
```

### State Machine Guards

Guards enforce preconditions before state transitions:

```python
# In state-machine.yaml
states:
  wip:
    allowed_transitions:
      - to: done
        guard: can_finish_task        # Guard function
        conditions:                   # Additional checks
          - name: all_work_complete
          - name: no_pending_commits
        actions:                      # Side effects
          - name: record_completion_time
```

Guards are enforced by CLI commands:
- `edison task claim` checks `can_start_task` guard
- `edison task done` checks `can_finish_task` guard
- `edison qa promote` checks QA-specific guards

### Rule System

Edison has two types of rules:

1. **Enforcement Rules**: Linked to state transitions
   - Defined in `state-machine.yaml` as guards/conditions
   - Enforced by CLI commands (hard blocks)
   - Example: "Task must be claimed before starting"

2. **Guidance Rules**: Suggest next actions
   - Defined in `rules/registry.yml`
   - Surfaced by `edison session next`
   - Example: "Delegate to validator when task done"

**Rules Engine** (`edison.core.rules.engine`):
- Loads rules from YAML configuration
- Evaluates rules based on context (task state, file patterns, etc.)
- Returns violations or recommendations
- Supports custom rule checkers via registry

---

## Workflow Diagram

```
                    ┌─────────────────────┐
                    │   Orchestrator      │
                    │   (Human/AI)        │
                    └──────────┬──────────┘
                               │
                               │ edison session next
                               ↓
                    ┌─────────────────────┐
                    │  Compute Next       │
                    │  Actions (Rules)    │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ↓                  ↓                  ↓
     ┌──────────┐       ┌──────────┐      ┌──────────┐
     │ Task:    │       │ Task:    │      │ Session: │
     │ todo→wip │       │ wip→done │      │ No action│
     └─────┬────┘       └─────┬────┘      └──────────┘
           │                  │
           │ edison task      │ edison task done
           │ claim T-001      │ T-001
           ↓                  ↓
     ┌──────────┐       ┌──────────┐
     │ Delegate │       │ Create   │
     │ to Agent │       │ QA Record│
     └─────┬────┘       └─────┬────┘
           │                  │
           │ (Agent           │ edison qa new T-001
           │  implements)     ↓
           ↓            ┌──────────┐
     ┌──────────┐      │ Launch   │
     │ Mark     │      │ Validators│
     │ Ready    │      └─────┬────┘
     └─────┬────┘            │
           │                 │ edison qa run T-001
           │                 ↓
           │           ┌──────────┐
           │           │ Delegate │
           │           │ to       │
           │           │ Validators│
           │           └─────┬────┘
           │                 │
           │                 │ (Validators execute)
           │                 ↓
           │           ┌──────────┐
           │           │ Collect  │
           │           │ Evidence │
           │           └─────┬────┘
           │                 │
           │                 │ edison qa bundle T-001
           │                 ↓
           │           ┌──────────┐
           │           │ Promote  │
           │           │ done→    │
           │           │ validated│
           │           └─────┬────┘
           │                 │
           └─────────────────┼─────────────┐
                             ↓             │
                       ┌──────────┐        │
                       │ Task:    │        │
                       │ done→    │        │
                       │ validated│        │
                       └──────────┘        │
                                           │
                       Loop Back ──────────┘
```

---

## Delegation Model

Edison delegates work to specialized agents via the **Pal MCP Server**.

### Agent Roster

Agents are defined in `edison.data/agents/`:
- `api-builder.md`: REST API development
- `component-builder.md`: UI component development
- `database-architect.md`: Database schema design
- `feature-implementer.md`: Feature implementation
- `test-engineer.md`: Test development

### Validator Configuration

Validators are configured in `validation.yaml` with:
- **Engines**: CLI execution backends (codex-cli, claude-cli, gemini-cli, auggie-cli, coderabbit-cli, pal-mcp)
- **Validators**: Flat list with engine references, prompts, and execution parameters
- **Waves**: Execution groups (critical, comprehensive) with ordering and failure behavior

### Validator Execution Flow

1. **Orchestrator** prepares a round via `edison qa round prepare <task-id>` and triggers validation via `edison qa validate <task-id> --execute`
2. **EngineRegistry** loads validator configurations and builds execution roster
3. **CLIEngine** executes validators directly via CLI tools when available
4. **Fallback**: If CLI unavailable, `PalMCPEngine` generates delegation instructions
5. **Parsers** normalize CLI output to structured `ValidationResult`
6. **Round reports** saved to `.project/qa/validation-reports/{task-id}/round-N/` (validator reports, implementation report, validation summary)
7. **Command evidence** saved to `.project/qa/evidence-snapshots/<gitHead>/<diffHash>/<clean|dirty>/` (tests/lint/build/type-check outputs)
8. **Results** feed into QA state machine for promotion decisions

### Unified Validator Execution

The validation system uses a centralized `ValidationExecutor` for all execution:

```
┌─────────────────────┐
│  Edison CLI         │
│  (qa validate)      │
└──────────┬──────────┘
           │
           │ 1. ValidationExecutor.execute()
           ↓
┌─────────────────────┐
│  ValidationExecutor │
│  (executor.py)      │
└──────────┬──────────┘
           │
           │ 2. For each wave (in order):
           │    ├── Separate: executable vs delegated
           │    ├── Run executable in parallel (CLIEngine)
           │    └── Generate delegation for others (PalMCPEngine)
           ↓
    ┌──────┴──────┐
    ↓             ↓
┌─────────┐  ┌─────────────┐
│CLIEngine│  │PalMCPEngine │
└────┬────┘  └──────┬──────┘
     │              │
     │ Execute      │ Generate
     │ subprocess   │ instructions
     ↓              ↓
┌─────────┐  ┌─────────────┐
│ Parser  │  │ Delegation  │
│(*.py)   │  │ Instructions│
└────┬────┘  └──────┬──────┘
     │              │
     └──────┬───────┘
            ↓
┌─────────────────────┐
│  Evidence Files     │
│  (round-N/)         │
├─────────────────────┤
│ command-*.txt       │ ← CLI output
│ delegation-*.md     │ ← Orchestrator instructions
│ validator-*-report  │ ← Structured results
└─────────────────────┘
```

**Key Features:**
- **Wave-based execution**: Validators grouped into ordered waves
- **Parallel execution**: Within each wave, validators run concurrently
- **Automatic fallback**: CLI → delegation when tools not installed
- **Mixed execution**: CLI and delegated validators in same wave
- **Evidence collection**: Round reports in `qa/validation-reports/`, command evidence snapshots in `qa/evidence-snapshots/`

---

## Directory Structure

### Project Structure (After `edison init`)

```
my-project/
├── .edison/                    # Edison configuration + overlays (tracked)
│   ├── config/                 # Project configuration (tracked)
│   ├── config.local/           # Project-local overrides (uncommitted)
│   ├── agents/                 # Project agent overlays (optional)
│   ├── validators/             # Project validator overlays (optional)
│   ├── guidelines/             # Project guidelines (optional)
│   ├── rules/                  # Project rules (optional)
│   └── _generated/             # Composed artifacts (DO NOT EDIT)
├── .project/                   # Project management artifacts (uncommitted)
│   ├── tasks/                  # Task state files
│   ├── qa/                     # QA briefs + evidence
│   │   ├── evidence-snapshots/  # Repo-fingerprint command evidence (tests/lint/build)
│   │   │   └── <gitHead>/<diffHash>/<clean|dirty>/
│   │   │       └── command-test.txt
│   │   └── validation-reports/  # Per-task rounds (reports + validator outputs)
│   │       └── T-001/
│   │           └── round-1/
│   │               ├── implementation-report.md
│   │               └── validator-security-report.md
│   ├── sessions/               # Session entities + worktree links
│   └── logs/                   # Runtime logs (append-only)
│       └── edison/
│           └── process-events.jsonl
├── .claude/                    # Claude IDE integration
│   ├── settings.json           # IDE settings (generated)
│   └── commands/               # Slash commands (generated)
├── .cursor/                    # Cursor IDE integration
│   ├── settings.json
│   └── ...
├── .pal/                       # Pal IDE integration
│   ├── settings.json
│   └── ...
├── .mcp.json                   # MCP server configuration
└── .gitignore                  # Git ignore (includes .project/ and .edison/_generated/)
```

Notes:
- The project management directory defaults to `.project` and is configurable via `project_management_dir`.
- The process events log is append-only and is used to derive the “current process list” in the CLI/UI.

### File Naming Conventions

- **Sessions**: `S-{YYYYMMDD}-{HHMMSS}` (e.g., `S-20251201-183000`)
- **Tasks**: `T-{NNN}` (e.g., `T-001`, `T-002`)
- **QA Records**: `{task-id}-qa` (e.g., `T-001-qa`)
- **Evidence**: `round-{N}` (e.g., `round-1`, `round-2`)

---

## Configuration System

### Configuration Loading

Edison uses a **layered configuration system**:

1. **Core defaults**: `edison.data/config/*.yaml` (40+ files)
2. **Pack configs**: `edison.data/packs/{pack}/config/*.yaml`
3. **Project overrides**: `.edison/config/*.yaml`

**ConfigManager** (`edison.core.config.manager`):
- Loads all layers and merges them
- Caches merged config for performance
- Validates against JSON schemas
- Provides typed domain-specific accessors

### Key Configuration Files

- `state-machine.yaml`: State machine definitions
- `workflow.yaml`: Workflow rules and timeouts
- `composition.yaml`: Composition settings
- `orchestrator.yaml`: Orchestrator configuration
- `validation.yaml`: Validation configuration (presets, engines, validators, evidence)
- `session.yaml`: Session configuration
- `tasks.yaml`: Task configuration
- `commands.yaml`: Slash command templates
- `hooks.yaml`: Git hook templates
- `mcp.yaml`: MCP server configuration

### Domain Configuration Objects

Each domain has a typed configuration object:

```python
# edison.core.config.domains.task
@dataclass
class TaskConfig:
    default_state: str = "todo"
    allowed_transitions: Dict[str, List[str]] = field(default_factory=dict)
    id_format: str = "T-{counter:03d}"
    # ...

# Load via ConfigManager
config = ConfigManager().load_config()
task_config = TaskConfig.from_dict(config["task"])
```

---

## IDE Integration

Edison generates IDE-specific configuration files for Claude, Cursor, and Pal.

### Composition Flow

1. **Core templates**: `edison.data/config/commands.yaml`, `hooks.yaml`
2. **Pack overlays**: `edison.data/packs/{pack}/commands.yaml`, etc.
3. **Project overlays**: `.edison/config/commands.yaml`, etc.
4. **Composition**: Layered composer merges all layers
5. **Output**: Write to `.claude/`, `.cursor/`, `.pal/`

### Claude Integration

**Files Generated**:
- `.claude/settings.json`: Claude-specific settings
- `.claude/commands/`: Slash commands for Claude
  - `edison.task-claim.md`: Claim a task
  - `edison.task-ready.md`: List ready-to-claim tasks
  - `edison.task-done.md`: Complete a task (wip→done)
  - `edison.qa-validate.md`: Validate a task
  - `edison.session-next.md`: Compute next actions

### Cursor Integration

**Files Generated**:
- `.cursor/settings.json`: Cursor-specific settings
- `.cursor/commands/`: Slash commands for Cursor

### Pal Integration

**Files Generated**:
- `.pal/settings.json`: Pal-specific settings
- `.pal/commands/`: Slash commands for Pal

### Settings Sync

Edison can sync settings bi-directionally:

```bash
# Sync settings from IDE to Edison config
edison compose settings --sync-from-ide

# Sync settings from Edison config to IDE
edison compose settings --sync-to-ide
```

---

## Testing Architecture

Edison follows strict TDD principles (enforced by rules):

1. **Write failing test first** (RED)
2. **Implement minimal code** (GREEN)
3. **Refactor** (CLEAN)

### Test Organization

```
tests/
├── unit/                   # Unit tests (fast, isolated)
│   ├── core/              # Core library tests
│   ├── cli/               # CLI tests
│   └── config/            # Config tests
├── integration/            # Integration tests (cross-module)
│   ├── task_workflow/     # Task workflow tests
│   ├── qa_workflow/       # QA workflow tests
│   └── session_lifecycle/ # Session lifecycle tests
└── e2e/                    # End-to-end tests (full workflows)
    ├── test_task_lifecycle.py
    ├── test_qa_lifecycle.py
    └── test_session_lifecycle.py
```

### Test Principles

- **No mocks**: Test real behavior, real code, real libraries
- **Real file I/O**: Use temp directories, real JSON files
- **Real git operations**: Use actual git repos in temp dirs
- **Isolation**: Each test creates its own environment
- **Cleanup**: Tests clean up after themselves

---

## Technology Stack

### Core Technologies

- **Python 3.12+**: Core implementation language
- **YAML**: Configuration format
- **JSON**: Entity persistence format
- **Git**: Version control integration
- **Markdown**: Documentation and prompt format

### Key Libraries

- **dataclasses**: Entity definitions
- **pathlib**: Path operations (no string paths)
- **argparse**: CLI argument parsing
- **json**: JSON serialization
- **yaml**: YAML parsing (PyYAML)
- **pytest**: Testing framework

### External Integration

- **Pal MCP Server**: Sub-agent delegation
- **Claude/Cursor/Pal IDEs**: AI code editors
- **Git**: Worktree management, diff parsing
- **Context7 API**: Documentation context (optional)

---

## Error Handling

### Exception Hierarchy

```python
EdisonError (base)
├── StateTransitionError      # Invalid state transition
├── RuleViolationError        # Rule enforcement failure
├── EntityNotFoundError       # Entity lookup failure
├── ConfigurationError        # Invalid configuration
├── CompositionValidationError # Composition validation failure
└── EdisonPathError           # Path resolution failure
```

### Error Recovery

- **Session recovery**: `edison session recovery recover` repairs broken sessions
- **Lock cleanup**: `edison session recovery clear-locks` removes stale locks
- **Worktree cleanup**: `edison git worktree-cleanup` removes orphaned worktrees

---

## Performance Considerations

### Caching

- **Configuration caching**: ConfigManager caches merged config
- **Composition caching**: LayeredComposer caches layer discovery
- **Entity caching**: Repository implementations may cache entities

### File Locking

- **Concurrent access**: FileRepository uses file locks to prevent conflicts
- **Lock timeout**: Configurable lock timeout (default: 10 seconds)
- **Lock cleanup**: Automatic cleanup on process exit

### Scalability

- **File-based storage**: Scales to thousands of tasks/sessions
- **Lazy loading**: Entities loaded on-demand
- **Incremental composition**: Only recompose changed files

---

## Extension Points

### Adding New Agents

1. Create agent prompt: `.edison/agents/my-agent.md`
2. Add to roster: `.edison/config/delegation.yaml`
3. Recompose: `edison compose all`

### Adding New Validators

1. Create validator prompt: `.edison/validators/my-validator.md`
2. Add to roster: `.edison/config/validation.yaml`
3. Recompose: `edison compose all`

### Adding New Rules

1. Define rule: `.edison/rules/registry.yml`
2. Implement checker: Custom Python module (optional)
3. Link to state machine: `.edison/config/state-machine.yaml` (for enforcement)

### Adding New Packs

1. Create pack structure: `edison.data/packs/my-pack/`
2. Add pack metadata: `manifest.yaml`
3. Activate in project: `.edison/config/packs.yaml`

### Adding New CLI Commands

1. Create command file: `edison/cli/{domain}/{command}.py`
2. Define `register_args()` and `main()` functions
3. Auto-discovered by `_dispatcher.py`

---

## Security Considerations

- **No arbitrary code execution**: All logic is declarative (YAML, state machines)
- **File permissions**: Entities stored with restricted permissions
- **Lock files**: Prevent concurrent modification
- **Schema validation**: All entities validated before persistence
- **Git integration**: Uses read-only git operations (no force push, no hard reset)

---

## Future Architecture

### Planned Enhancements

- **Database backend**: Optional SQLite/PostgreSQL for larger projects
- **Web UI**: Browser-based session management
- **Distributed validation**: Parallel validator execution
- **Cloud sync**: Remote session storage
- **Metrics**: Performance tracking and analytics

### Deprecations

- **Draft session state**: Deprecated, use `active` directly
- **Legacy paths**: Old file structure migrated to new layout
- **Hardcoded values**: All being migrated to YAML config

---

## Glossary

- **Agent**: Specialized AI assistant for specific tasks (e.g., API builder, test engineer)
- **CodeRabbit**: External AI-powered code review tool integrated as a hybrid validator
- **Composition**: Process of merging content from Core/Packs/Project layers
- **Constitution**: Foundational rules for a role (agent, orchestrator, validator)
- **Entity**: First-class object with state, metadata, and persistence (Task, Session, QARecord)
- **Guard**: Precondition enforced before state transition
- **Guideline**: Best practice document for agents/validators
- **Orchestrator**: Human or AI managing the overall workflow
- **Pack**: Technology-specific bundle of agents, validators, guidelines, and rules
- **Repository**: Persistence layer for entities (file-based or database-backed)
- **Rule**: Constraint enforced during workflow (enforcement) or suggested as guidance
- **Session**: Work context with associated tasks, QA records, and git worktree
- **State Machine**: Declarative definition of entity lifecycle with states and transitions
- **Validator**: AI assistant that validates task implementation quality
- **External Validator**: CLI tool (e.g., CodeRabbit) executed separately with output transformed by LLM
- **Worktree**: Git worktree isolated for a session's work

---

## References

- **Repository**: https://github.com/BeehiveInnovations/edison
- **Documentation**: `/docs/`
- **Configuration Reference**: `edison.data/config/`
- **Example Projects**: `/examples/`

---

**Last Updated**: 2025-12-04
**Version**: 2.0.0
**Authors**: Edison Framework Team

👉 For full templating/composition details (layers, syntax, functions, outputs), see `docs/TEMPLATING.md`.

## Unified Composition (current)

### Architecture Overview

The composition system is fully configuration-driven with typed access via `CompositionConfig`:

```
composition.yaml (under composition: key)
       ↓
CompositionConfig (typed domain config)
       ↓
ComposableRegistry.comp_config (lazy property)
       ↓
get_strategy_config(), _resolve_output_paths(), get_context_vars()
```

### Key Components

- **`CompositionConfig`**: Typed accessor for all composition settings (`composition.defaults`, `composition.content_types`, `composition.adapters`)
- **`ComposableRegistry`**: Base class for all registries with built-in context variables and config-driven strategy loading
- **`GenericRegistry`**: Config-driven registry used for most content types (agents, validators, guidelines, documents, roots, cursor_rules)
- **`ConstitutionRegistry`**: Extends base with constitution-specific context (mandatoryReads, optionalReads, rules)
- **`JsonSchemaRegistry`**: JSON schema composition with deep merge
- **`ComposableTypesManager`**: CLI orchestration - iterates content_types from config

### Built-in Context Variables

All registries automatically provide via `get_context_vars()`:
- `name`, `content_type` - Entity identification
- `source_layers`, `timestamp`, `generated_date`, `version` - Composition metadata
- `template`, `output_dir`, `output_path`, `PROJECT_EDISON_DIR` - Paths (all relative to project root)

### Configuration Namespacing

All composition config is under the `composition:` key to prevent conflicts when merged with other config files:

```yaml
composition:
  defaults:
    dedupe: { shingle_size: 12, ... }
  content_types:
    agents: { enabled: true, output_path: "...", ... }
  adapters:
    claude: { enabled: true, adapter_class: "...", ... }
```

### Composition Principles

- **Single strategy**: `MarkdownCompositionStrategy` for all markdown. YAML uses layered config loader.
- **Layer order**: core → packs → user → project. Overlays go in `overlays/` subdirectory.
- **Templating pipeline**: sections/extend → includes → conditionals → loops → functions → variables → references → validation
- **Zero hardcoding**: All content types, output paths, and adapters are defined in `composition.yaml`
- **Functions extension**: Python files in `functions/` directories; call with `{{fn:name arg1}}`
