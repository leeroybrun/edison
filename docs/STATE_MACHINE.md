# Edison State Machine System

Complete reference for Edison's declarative state machine, guards, conditions, actions, and recommendations.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Guards](#guards)
- [Conditions](#conditions)
- [Actions](#actions)
- [Recommendations](#recommendations)
- [Extensibility](#extensibility)
- [API Reference](#api-reference)

---

## Overview

Edison uses a declarative state machine to manage the lifecycle of tasks, QA briefs, and sessions. The system is:

- **Configuration-driven**: All states, transitions, guards, conditions, and actions are defined in `workflow.yaml`
- **Extensible**: Custom handlers can be added via layered composition (core → packs → project)
- **Fail-safe**: Guards follow a fail-closed principle, returning `False` when context is missing
- **Unified**: A single `WorkflowConfig` class provides access to all state machine configuration

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| States | Define entity lifecycle stages | `workflow.yaml` |
| Transitions | Define allowed state changes | `workflow.yaml` |
| Guards | Boolean checks that allow/block transitions | `data/guards/` |
| Conditions | Prerequisites for transitions | `data/conditions/` |
| Actions | Side effects executed during transitions | `data/actions/` |
| Recommendations | Suggested next actions for `session next` | `workflow.yaml` |

---

## Architecture

### Execution Flow

When a state transition is requested, the system executes in this order:

```
1. Pre-transition actions (when: before)
       ↓
2. Guard check (single boolean gate)
       ↓
3. Condition checks (multiple prerequisites with OR support)
       ↓
4. Post-transition actions (when: after, default)
```

### Component Hierarchy

```
WorkflowConfig (config/domains/workflow.py)
    └── _statemachine (workflow.yaml → workflow.statemachine)
        ├── task
        │   └── states (todo, wip, blocked, done, validated)
        ├── qa
        │   └── states (waiting, todo, wip, done, validated)
        └── session
            └── states (draft, active, blocked, done, closing, validated, recovery, archived)

RichStateMachine (core/state/engine.py)
    ├── GuardRegistry (core/state/guards.py)
    │   └── Loaded from data/guards/
    ├── ConditionRegistry (core/state/conditions.py)
    │   └── Loaded from data/conditions/
    └── ActionRegistry (core/state/actions.py)
        └── Loaded from data/actions/

StateValidator (core/state/validator.py)
    └── Uses RichStateMachine for validation

validate_transition() (core/state/transitions.py)
    └── Unified entry point for transition validation
```

---

## Configuration

State machine configuration lives in `workflow.yaml` under `workflow.statemachine`:

```yaml
workflow:
  statemachine:
    task:
      states:
        todo:
          description: "Task awaiting claim"
          initial: true
          allowed_transitions:
            - to: wip
              guard: can_start_task
              conditions:
                - name: task_claimed
              rules: [RULE.GUARDS.FAIL_CLOSED]
              recommendations:
                - id: task.claim
                  entity: task
                  rationale: "Task ready to claim"
                  blocking: true
                  cmd_template: ["edison", "task", "claim", "{task_id}"]
              actions:
                - name: record_activation_time
                  when: after
```

### State Definition

| Property | Type | Description |
|----------|------|-------------|
| `description` | string | Human-readable state description |
| `initial` | boolean | Marks this as the initial state for new entities |
| `final` | boolean | Marks this as a terminal state (no outgoing transitions) |
| `allowed_transitions` | array | List of valid transitions from this state |

### Transition Definition

| Property | Type | Description |
|----------|------|-------------|
| `to` | string | Target state name |
| `guard` | string | Guard function name (single gate) |
| `conditions` | array | Condition checks with OR support |
| `actions` | array | Actions to execute |
| `rules` | array | Rule IDs to display/enforce |
| `recommendations` | array | Suggested actions for `session next` |

---

## Guards

Guards are boolean functions that determine if a transition is allowed. They follow the **fail-closed principle**: return `False` when required context is missing.

### Built-in Guards

| Guard | Domain | Description |
|-------|--------|-------------|
| `always_allow` | shared | Always returns `True` |
| `fail_closed` | shared | Always returns `False` |
| `can_start_task` | task | Task must be claimed by session |
| `can_finish_task` | task | Implementation report must exist |
| `has_blockers` | task | Check if task has blockers |
| `has_implementation_report` | task | Alias for `can_finish_task` |
| `requires_rollback_reason` | task | Rollback reason required for done→wip |
| `can_activate_session` | session | Session has claimed tasks |
| `can_complete_session` | session | Session is ready to complete |
| `has_session_blockers` | session | Check if session has blockers |
| `is_session_ready` | session | Session ready for closing |
| `can_start_qa` | qa | Task must be done for QA to start |
| `can_validate_qa` | qa | All blocking validators passed (reads evidence) |
| `has_validator_reports` | qa | Validator reports exist with required evidence |
| `has_all_waves_passed` | qa | All validator waves passed in order |
| `has_bundle_approval` | qa | Bundle approval JSON exists |

### Guard Implementation

Guards are Python functions in `data/guards/`:

```python
# data/guards/task.py
from typing import Any, Mapping

def can_start_task(ctx: Mapping[str, Any]) -> bool:
    """Task can start only if claimed by current session.
    
    FAIL-CLOSED: Returns False if any required data is missing.
    """
    task = ctx.get("task")
    session = ctx.get("session")
    
    if not isinstance(task, Mapping) or not isinstance(session, Mapping):
        return False  # FAIL-CLOSED
    
    task_session = task.get("session_id") or task.get("sessionId")
    session_id = session.get("id")
    
    if not task_session or not session_id:
        return False  # FAIL-CLOSED
    
    return str(task_session) == str(session_id)
```

### Fail-Closed Principle

Guards must follow fail-closed semantics:

```python
# CORRECT: Fail-closed
def my_guard(ctx: Mapping[str, Any]) -> bool:
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        return False  # Missing context = deny
    return bool(task.get("allowed"))

# INCORRECT: Fail-open (security risk)
def bad_guard(ctx: Mapping[str, Any]) -> bool:
    task = ctx.get("task", {})
    return task.get("allowed", True)  # Default True = allow by default
```

---

## Conditions

Conditions are prerequisite checks for transitions. Unlike guards (single gate), multiple conditions can be defined with OR logic support.

### Built-in Conditions

| Condition | Domain | Description |
|-----------|--------|-------------|
| `all_work_complete` | core | All work items are complete |
| `no_pending_commits` | core | No uncommitted changes |
| `ready_to_close` | core | Entity is ready to close |
| `has_task` | task | Session has at least one task |
| `task_claimed` | task | Task is claimed by session |
| `task_ready_for_qa` | task | Task ready for QA validation |
| `validation_failed` | session | Validation has failed |
| `dependencies_missing` | session | Dependencies are missing |
| `has_blocker_reason` | session | Blocker reason is present |
| `blockers_resolved` | session | Blockers have been cleared |
| `session_has_owner` | session | Session has owner assigned |
| `all_tasks_validated` | session | All session tasks validated |
| `has_required_evidence` | qa | Required evidence files exist |
| `has_bundle_approval` | qa | Bundle approval JSON exists |
| `has_all_waves_passed` | qa | All validator waves passed in order |
| `all_blocking_validators_passed` | qa | All blocking validators passed |
| `has_validator_reports` | qa | At least one validator report exists |

### OR Logic

Conditions support alternative checks via `or`:

```yaml
conditions:
  - name: validation_failed
    or:
      - name: dependencies_missing
    error: "Session blocked due to validation or dependencies"
```

### Condition Implementation

```python
# data/conditions/session.py
from typing import Any, Mapping

def validation_failed(ctx: Mapping[str, Any]) -> bool:
    """Check if validation has failed."""
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        if session.get("validation_failed") is not None:
            return bool(session.get("validation_failed"))
    
    validation = ctx.get("validation_results", {})
    if isinstance(validation, Mapping):
        failed = validation.get("failed_validators", [])
        return bool(failed)
    
    return False
```

---

## Actions

Actions are side-effect functions executed during transitions. They can modify context, persist state, or trigger external systems.

### Action Timing

Actions support configurable timing via the `when` property:

| Value | Description |
|-------|-------------|
| `before` | Execute before guard/condition checks |
| `after` | Execute after successful transition (default) |
| `config.path` | Conditional execution based on config value |

```yaml
actions:
  # Pre-transition validation
  - name: validate_prerequisites
    when: before
  
  # Conditional worktree creation
  - name: create_worktree
    when: config.worktrees_enabled
  
  # Post-transition timestamps (default)
  - name: record_activation_time
    when: after
  
  # No 'when' = defaults to 'after'
  - name: notify_session_start
```

### Built-in Actions

| Action | Domain | Description |
|--------|--------|-------------|
| `record_completion_time` | core | Record completion timestamp |
| `record_blocker_reason` | core | Record blocker reason |
| `record_closed` | core | Record session closed timestamp |
| `log_transition` | core | Log the state transition |
| `create_worktree` | worktree | Create git worktree for session |
| `cleanup_worktree` | worktree | Remove session worktree |
| `record_activation_time` | session | Record session activation |
| `notify_session_start` | session | Notify session started |
| `finalize_session` | session | Finalize and persist session |
| `validate_prerequisites` | session | Pre-transition validation |

### Action Implementation

```python
# data/actions/session.py
from typing import Any, MutableMapping

def record_activation_time(ctx: MutableMapping[str, Any]) -> None:
    """Record session activation timestamp."""
    from edison.core.utils.time import utc_timestamp
    
    timestamp = utc_timestamp()
    ctx.setdefault("_timestamps", {})["activated"] = timestamp
    
    session = ctx.get("session", {})
    if isinstance(session, MutableMapping):
        session.setdefault("meta", {})["activatedAt"] = timestamp
```

---

## Recommendations

Recommendations are suggested actions displayed by `session next`. They are defined per transition in `workflow.yaml`.

### Recommendation Definition

```yaml
recommendations:
  - id: task.claim
    entity: task
    rationale: "Task ready to claim"
    blocking: true
    cmd_template: ["edison", "task", "claim", "{task_id}", "--session", "{session_id}"]
```

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique identifier for the recommendation |
| `entity` | string | Entity type (task, qa, session) |
| `rationale` | string | Human-readable explanation |
| `blocking` | boolean | Whether this blocks other actions |
| `cmd_template` | array | Command template with placeholders |

### Template Placeholders

| Placeholder | Description |
|-------------|-------------|
| `{task_id}` | Current task ID |
| `{session_id}` | Current session ID |
| `{round}` | Current QA round number |

---

## Extensibility

### Layered Composition

Handlers are loaded from layered folders with priority (later overrides earlier):

1. **Core**: `edison/data/guards|actions|conditions/`
2. **Bundled packs**: `edison/data/packs/<pack>/guards|actions|conditions/`
3. **Project packs**: `.edison/packs/<pack>/guards|actions|conditions/`
4. **Project**: `.edison/guards|actions|conditions/`

### Adding Custom Handlers

**1. Create handler file:**

```python
# .edison/guards/custom.py
from typing import Any, Mapping

def my_custom_guard(ctx: Mapping[str, Any]) -> bool:
    """Custom guard with fail-closed semantics."""
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        return False  # FAIL-CLOSED
    return bool(task.get("my_custom_check"))
```

**2. Reference in workflow.yaml:**

```yaml
allowed_transitions:
  - to: wip
    guard: my_custom_guard
```

### Registration Decorators

For explicit registration (optional):

```python
from edison.core.state import register_guard, register_action, register_condition

@register_guard("my_guard")
def my_guard(ctx: Mapping[str, Any]) -> bool:
    return True

@register_action("my_action")
def my_action(ctx: MutableMapping[str, Any]) -> None:
    ctx["_my_action"] = True

@register_condition("my_condition")
def my_condition(ctx: Mapping[str, Any]) -> bool:
    return True
```

---

## API Reference

### WorkflowConfig

```python
from edison.core.config.domains.workflow import WorkflowConfig

cfg = WorkflowConfig()

# Get states for a domain
task_states = cfg.get_states("task")  # ["todo", "wip", "blocked", "done", "validated"]

# Get semantic state name
wip_state = cfg.get_semantic_state("task", "wip")  # "wip"

# Get initial state
initial = cfg.get_initial_state("task")  # "todo"

# Get transition recommendations
recs = cfg.get_recommendations("task", "todo", "wip")

# Get transition rules
rules = cfg.get_transition_rules("task", "wip", "done")
```

### validate_transition

```python
from edison.core.state import validate_transition

# Validate without executing
is_valid, error = validate_transition(
    entity_type="task",
    from_state="todo",
    to_state="wip",
    context={"task": task_dict, "session": session_dict}
)
```

### transition_entity

```python
from edison.core.state import transition_entity

# Execute transition with actions
result = transition_entity(
    entity_type="task",
    entity_id="TASK-001",
    to_state="wip",
    context={"task": task_dict, "session": session_dict},
    record_history=True
)
# Returns: {"state": "wip", "previous_state": "todo", "history_entry": {...}}
```

### RichStateMachine

```python
from edison.core.state import RichStateMachine, guard_registry, condition_registry, action_registry

machine = RichStateMachine(
    name="task",
    spec={"states": states_config},
    guards=guard_registry,
    conditions=condition_registry,
    actions=action_registry
)

# Validate transition
machine.validate("todo", "wip", context=ctx, execute_actions=True)

# Get allowed targets
targets = machine.allowed_targets("todo")  # ["wip", "done", "blocked"]
```

### Handler Registries

```python
from edison.core.state import guard_registry, condition_registry, action_registry

# Check a guard
result = guard_registry.check("can_start_task", context=ctx, domain="task")

# Check a condition
result = condition_registry.check("task_claimed", context=ctx)

# Execute an action
action_registry.execute("record_completion_time", context=ctx)

# List handlers
handlers = guard_registry.list_handlers(domain="task")
```

### Handler Loading

```python
from edison.core.state import load_handlers, load_guards, load_actions, load_conditions

# Load all handlers from layered folders
counts = load_handlers(project_root=None, active_packs=None)
# Returns: {"guards": 10, "actions": 8, "conditions": 12}

# Load specific handler types
load_guards(project_root, active_packs)
load_actions(project_root, active_packs)
load_conditions(project_root, active_packs)
```

---

## Task States

```
┌───────┐
│  todo │ ─────────────────────────────────────┐
└───┬───┘                                      │
    │ can_start_task                           │
    ▼                                          │
┌───────┐     has_blockers     ┌─────────┐    │
│  wip  │ ───────────────────► │ blocked │    │
└───┬───┘                      └────┬────┘    │
    │ can_finish_task               │         │
    ▼                               │         │
┌───────┐  requires_rollback_reason │         │
│ done  │ ─────────► wip ◄──────────┘         │
└───┬───┘                                     │
    │ can_finish_task                         │
    ▼                                         │
┌───────────┐                                 │
│ validated │ (final) ◄───────────────────────┘
└───────────┘
```

**Key Task Guards:**
- `todo → wip`: `can_start_task` (task claimed by session)
- `wip → done`: `can_finish_task` (implementation report exists)
- `done → wip`: `requires_rollback_reason` (reason required for rollback)
- `done → validated`: `can_finish_task` (evidence complete)

## QA States

```
┌─────────┐
│ waiting │ ─────────────────┐
└────┬────┘                  │
     │ can_start_qa          │
     ▼                       │
┌───────┐                    │
│ todo  │ ◄──────────────────┤
└───┬───┘                    │
    │ always_allow           │
    ▼                        │
┌───────┐                    │
│  wip  │ ◄──────────────────┤
└───┬───┘ (has_validator_reports) │
    │                        │
    ▼                        │
┌───────┐                    │
│ done  │ ◄──────────────────┘
└───┬───┘
    │ can_validate_qa
    ▼
┌───────────┐
│ validated │ (final)
└───────────┘
```

**Key QA Guards:**
- `waiting → todo`: `can_start_qa` (task must be done)
- `wip → done`: `has_validator_reports` (validators must have run)
- `done → validated`: `can_validate_qa` (all blocking validators passed)

## Session States

```
┌───────┐
│ draft │
└───┬───┘
    │ can_activate_session
    ▼
┌────────┐     has_blockers     ┌─────────┐
│ active │ ───────────────────► │ blocked │
└───┬────┘                      └────┬────┘
    │                                │
    │ can_complete_session           │
    ▼                                │
┌─────────┐                          │
│ closing │ ◄────────────────────────┘
└────┬────┘
     │ can_complete_session
     ▼
┌───────────┐
│ validated │
└─────┬─────┘
      │ always_allow
      ▼
┌──────────┐
│ archived │ (final)
└──────────┘

     ┌──────────┐
     │ recovery │ (accessible from active/closing)
     └──────────┘
```
