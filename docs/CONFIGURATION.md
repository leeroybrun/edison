# Edison Configuration Guide

Complete reference for configuring the Edison Framework.

## Table of Contents

- [Configuration Hierarchy](#configuration-hierarchy)
- [Environment Variables](#environment-variables)
- [Core Configuration Files](#core-configuration-files)
- [Pack Configuration](#pack-configuration)
- [Project Configuration](#project-configuration)
- [Configuration Examples](#configuration-examples)

---

## Configuration Hierarchy

Edison uses a layered configuration system with the following priority (highest to lowest):

1. **Environment variables** (`EDISON_*`)
2. **Project-local overrides** (`.edison/config.local/`, uncommitted; per-user per-project)
3. **Project overrides** (`.edison/config/`)
4. **Overlay layer overrides** (`<layer>/config/` for each overlay layer; user layer defaults to `~/.edison/config/`)
5. **Pack configurations** (`<pack-root>/{pack}/config/` from bundled + overlay-layer pack roots for active packs)
6. **Bundled defaults** (`src/edison/data/config/`)

Notes:
- **Pack-aware bootstrap**: Edison first loads `core → user → project → project-local` to determine `packs.active`, then performs the full merge including pack configs.
- **User config directory** defaults to `~/.edison` and is configurable via `EDISON_paths__user_config_dir`.
- **Configurable overlay layers**: Add extra layer roots (e.g. a shared company layer) via `config/layers.yaml` (loaded from core → user → project → project-local).

### How Merging Works

- **Deep merge**: Nested objects merge recursively
- **List operations**:
  - `EDISON_KEY__0=value` - Set specific index
  - `EDISON_KEY__APPEND=value` - Append to list
- **Type coercion**: Environment variables are automatically converted to booleans, integers, floats, or JSON

---

## Environment Variables

### Standard Edison Variables

All Edison configuration can be overridden via environment variables using the `EDISON_` prefix:

```bash
# Simple values
export EDISON_TDD__ENFORCE_RED_GREEN_REFACTOR=true
export EDISON_SESSION__RECOVERY__TIMEOUT_HOURS=12

# Deep paths (use double underscores)
export EDISON_DELEGATION__RESILIENCE__RETRY__MAX_ATTEMPTS=5
export EDISON_DELEGATION__RESILIENCE__CIRCUIT_BREAKER__THRESHOLD=10

# Lists - set specific index
export EDISON_AGENTS__0=codex
export EDISON_AGENTS__1=claude

# Lists - append
export EDISON_PACKS__APPEND=testing
export EDISON_AGENTS__APPEND=gemini

# JSON values
export EDISON_JSON_OBJECT='{"key": "value"}'
export EDISON_JSON_ARRAY='["a", "b", "c"]'

# New keys (preserve case for new keys)
export EDISON_QUALITY__LEVEL=gold  # Creates {"quality": {"LEVEL": "gold"}}
export EDISON_RUNTIME__LOG_LEVEL=debug  # Creates {"RUNTIME": {"LOG_LEVEL": "debug"}}
```

### Path Configuration

```bash
# Override project config directory (default: .edison)
export EDISON_paths__project_config_dir=.custom_config

# Override user config directory (default: ~/.edison)
export EDISON_paths__user_config_dir=~/.my-edison
```

### Project Variables

```bash
# Project identification (optional)
export PROJECT_NAME=my-app
```

### Reserved Variables (Set by Edison)

These are set by Edison and should not be manually configured:

- `EDISON_SESSION_ID` - Current session identifier (set by session manager)
- `CLAUDE_CODE_MAX_OUTPUT_TOKENS` - Claude Code output token limit

---

## Core Configuration Files

All core configuration files are located in `src/edison/data/config/` and can be overridden in your project's `.edison/config/` directory.

### workflow.yaml

Defines workflow configuration including state machines for tasks, QA, and sessions. The state machine is now merged into workflow.yaml under the `workflow.statemachine` key.

```yaml
workflow:
  # Workflow settings
  version: "1.0.0"
  validationLifecycle:
    onApprove:
      qaState: done → validated
      taskState: done → validated
    onReject:
      qaState: wip → waiting
      taskState: done → wip
    onRevalidate:
      qaState: waiting → todo
  
  timeouts:
    staleTaskThreshold: 4h
    sessionTimeout: 2h
    validatorTimeout: 5m

  # State machine configuration
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
          - to: done
            guard: can_finish_task
            conditions:
              - name: all_work_complete
              - name: no_pending_commits
            actions:
              - name: record_completion_time
          - to: blocked
            guard: has_blockers
            actions:
              - name: record_blocker_reason

      wip:
        description: "Task in progress"
        allowed_transitions:
          - to: blocked
            guard: has_blockers
          - to: done
            guard: can_finish_task
          - to: todo
            guard: always_allow
          - to: validated
            guard: always_allow

      blocked:
        description: "Waiting on external blockers"
        allowed_transitions:
          - to: wip
            guard: can_start_task
          - to: todo
            guard: always_allow

      done:
        description: "Implementation complete, awaiting validation"
        allowed_transitions:
          - to: validated
            guard: can_finish_task
          - to: wip
            guard: always_allow

      validated:
        description: "Validated and complete"
        final: true
        allowed_transitions: []

  qa:
    states:
      waiting:
        initial: true
        description: "Pending hand-off from implementation"
      todo:
        description: "QA backlog"
      wip:
        description: "QA in progress"
      done:
        description: "QA review complete"
      validated:
        description: "QA validated"
        final: true

  session:
    states:
      draft:
        description: "Session in draft state, not yet active"
        allowed_transitions:
          - to: active
            guard: can_activate_session
            conditions:
              - name: has_task
              - name: task_claimed
            actions:
              - name: create_worktree
                when: config.worktrees_enabled
              - name: record_activation_time

      active:
        description: "Session is active, work in progress"
        initial: true
        allowed_transitions:
          - to: done
            guard: can_complete_session
          - to: blocked
            guard: has_blockers
          - to: closing
            guard: can_complete_session
          - to: recovery
            guard: always_allow

      blocked:
        description: "Session blocked due to validation or dependencies"

      done:
        description: "Session work complete"

      closing:
        description: "Session closing and awaiting validation"

      validated:
        description: "Session validated"
        allowed_transitions:
          - to: archived
            guard: always_allow

      recovery:
        description: "Session in recovery after timeout or failure"

      archived:
        description: "Session archived"
        final: true
```

**Override Example** (`.edison/config/workflow.yaml`):

```yaml
# Add custom task state
workflow:
  statemachine:
    task:
      states:
        review:
          description: "Code review in progress"
          allowed_transitions:
            - to: wip
              guard: always_allow
            - to: done
              guard: can_finish_task
```

#### Action Timing (`when:` property)

Actions can be configured to run at different points during a transition:

```yaml
allowed_transitions:
  - to: active
    guard: can_activate_session
    actions:
      # Pre-transition: runs BEFORE guards/conditions
      - name: validate_prerequisites
        when: before
      
      # Conditional: runs only if config value is truthy
      - name: create_worktree
        when: config.worktrees_enabled
      
      # Post-transition: runs AFTER guards/conditions (default)
      - name: record_activation_time
        when: after
      
      # No 'when' = defaults to 'after'
      - name: notify_session_start
```

Valid `when` values:
- `before` - Execute before guard/condition checks
- `after` - Execute after successful transition (default)
- `config.path` - Conditional execution based on configuration value

#### Extensible Handlers (Guards, Actions, Conditions)

Handlers are loaded dynamically from layered folders with the following priority:

1. **Core**: `edison/data/guards|actions|conditions/`
2. **Bundled packs**: `edison/data/packs/<pack>/guards|actions|conditions/`
3. **Project packs**: `.edison/packs/<pack>/guards|actions|conditions/`
4. **Project**: `.edison/guards|actions|conditions/`

Later layers override earlier ones, allowing project-specific customization.

**Adding a custom guard:**

```python
# .edison/guards/custom.py
from typing import Any, Mapping

def my_custom_guard(ctx: Mapping[str, Any]) -> bool:
    """Custom guard following fail-closed principle."""
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        return False  # FAIL-CLOSED
    return bool(task.get("my_custom_check"))
```

Then reference in `workflow.yaml`:

```yaml
allowed_transitions:
  - to: wip
    guard: my_custom_guard
```

**Guard Fail-Closed Principle**: Guards should return `False` when required context is missing, ensuring secure-by-default behavior.

---

### session.yaml

Session management, recovery, and worktree configuration.

```yaml
session:
  paths:
    root: ".project/sessions"
    archive: ".project/archive"
    tx: ".project/sessions/_tx"
    templates:
      primary: "{PROJECT_CONFIG_DIR}/sessions/TEMPLATE.json"
      repo: "{PROJECT_CONFIG_DIR}/sessions/TEMPLATE.json"

  recovery:
    timeoutHours: 8
    staleCheckIntervalHours: 1
    clockSkewAllowanceSeconds: 300
    defaultTimeoutMinutes: 60

  validation:
    idRegex: "^[a-zA-Z0-9_\\-\\.]+$"
    maxLength: 64

  states:
    draft: "draft"
    active: "wip"
    wip: "wip"
    done: "done"
    closing: "done"
    validated: "validated"
    recovery: "recovery"
    archived: "archived"

  defaults:
    initialState: "active"

  lookupOrder:
    - "wip"
    - "active"
    - "done"
    - "validated"
    - "closing"
    - "recovery"
    - "archived"

  worktree:
    uuidSuffixLength: 6
    timeouts:
      health_check: 10
      fetch: 60
      checkout: 30
      worktree_add: 30
      clone: 60
      install: 300
      branch_check: 10
      prune: 10

  transaction:
    minDiskHeadroom: 5242880  # ~5MB
```

**Common Overrides**:

```bash
# Increase session timeout
export EDISON_SESSION__RECOVERY__TIMEOUT_HOURS=12

# Adjust worktree install timeout
export EDISON_SESSION__WORKTREE__TIMEOUTS__INSTALL=600
```

---

### validators.yaml

Validation framework configuration with engines, validators, and execution waves.

```yaml
validation:
  # Validation dimensions and weights
  dimensions:
    functionality: 30
    reliability: 25
    security: 20
    maintainability: 15
    performance: 10

  # Cache directory for generated validators
  cache:
    directory: "{PROJECT_CONFIG_DIR}/_generated/validators"

  # Required evidence files
  requiredEvidenceFiles:
    - command-type-check.txt
    - command-lint.txt
    - command-test.txt
    - command-build.txt

  # Execution settings
  execution:
    mode: parallel        # parallel | sequential
    concurrency: 4        # max parallel validators
    timeout: 300          # per-validator timeout in seconds

  # Engine definitions (execution backends)
  engines:
    codex-cli:
      type: cli
      command: "codex"
      subcommand: "exec"
      response_parser: codex

    claude-cli:
      type: cli
      command: "claude"
      subcommand: "-p"
      output_flags: ["--output-format", "json"]
      read_only_flags: ["--permission-mode", "plan"]
      response_parser: claude

    gemini-cli:
      type: cli
      command: "gemini"
      output_flags: ["--output-format", "json"]
      response_parser: gemini
      prompt_mode: arg

    auggie-cli:
      type: cli
      command: "auggie"
      output_flags: ["--output-format", "json"]
      read_only_flags: ["--print", "--quiet"]
      response_parser: auggie

    coderabbit-cli:
      type: cli
      command: "coderabbit"
      subcommand: "review"
      read_only_flags: ["--prompt-only"]
      response_parser: coderabbit

    pal-mcp:
      type: delegated
      description: "Generate delegation instructions for orchestrator"

  # Flat validator definitions
  validators:
    global-codex:
      name: "Global Validator (Codex)"
      engine: codex-cli
      fallback_engine: pal-mcp
      prompt: "_generated/validators/global.md"
      wave: critical
      always_run: true
      blocking: true
      timeout: 300
      context7_required: true
      context7_packages: [next, react, typescript]

    global-claude:
      name: "Global Validator (Claude)"
      engine: claude-cli
      fallback_engine: pal-mcp
      prompt: "_generated/validators/global.md"
      wave: critical
      always_run: true
      blocking: true
      context7_required: true
      context7_packages: [next, react, typescript]

    security:
      name: "Security Validator"
      engine: codex-cli
      fallback_engine: pal-mcp
      prompt: "critical/security.md"
      wave: critical
      always_run: false
      blocking: true
      context7_required: true
      context7_packages: [next, zod]
      focus: [authentication, authorization, input-validation]

    react:
      name: "React Validator"
      engine: codex-cli
      fallback_engine: pal-mcp
      prompt: "specialized/react.md"
      wave: comprehensive
      always_run: false
      blocking: false
      triggers: ["**/*.tsx", "**/*.jsx", "**/components/**/*"]
      context7_packages: [react]

  # Wave definitions (execution groups)
  waves:
    - name: critical
      validators: [global-codex, global-claude, global-gemini, security, performance]
      execution: parallel
      continue_on_fail: false
      requires_previous_pass: false

    - name: comprehensive
      validators: [react, nextjs, api, prisma, testing]
      execution: parallel
      continue_on_fail: true
      requires_previous_pass: true
```

**Key Concepts**:

- **Engines**: Define execution backends (CLI tools or delegation)
- **Validators**: Reference engines with fallback support
- **Waves**: Group validators for ordered execution
- **palRole**: Automatically inferred as `validator-{id}` (no explicit config needed)

**Common Overrides**:

```bash
# Run validators sequentially for debugging
export EDISON_VALIDATION__EXECUTION__MODE=sequential

# Increase validator timeout
export EDISON_VALIDATION__EXECUTION__TIMEOUT=600
```

---

### delegation.yaml

Agent delegation rules based on file patterns and task types.

```yaml
delegation:
  implementers:
    primary: codex
    fallbackChain: [gemini, claude]
    maxFallbackAttempts: 3

  resilience:
    circuitBreaker:
      enabled: false
      failureThreshold: 3
      resetTimeoutSeconds: 60
    retryLogic:
      enabled: false
      maxRetries: 4
      backoffMultiplier: 2
      maxBackoffSeconds: 30

  # File pattern rules
  filePatternRules:
    "*.tsx":
      preferredModel: claude
      reason: "UI/UX thinking, component design, accessibility"
      subAgentType: component-builder-nextjs
      excludePatterns: ["**/*.test.tsx", "**/*.spec.tsx"]
      preferredPalRole: component-builder-nextjs
      confidence: high

    "**/route.ts":
      preferredModel: codex
      reason: "API security, precise validation, error handling, type safety"
      subAgentType: api-builder
      delegateVia: pal-mcp
      preferredPalRole: api-builder
      confidence: very-high

    "**/*.test.ts":
      preferredModel: codex
      reason: "Systematic test coverage, edge case generation, TDD compliance"
      subAgentType: test-engineer
      delegateVia: pal-mcp
      preferredPalRole: test-engineer
      confidence: high

    "schema.prisma":
      preferredModel: codex
      reason: "Schema precision, relationship correctness, migration safety"
      subAgentType: database-architect-prisma
      delegateVia: pal-mcp
      preferredPalRole: database-architect-prisma
      confidence: very-high

  # Task type rules
  taskTypeRules:
    ui-component:
      preferredModel: claude
      subAgentType: component-builder-nextjs
      reason: "Component design needs UX thinking, accessibility"
      delegation: required
      preferredPalRole: component-builder-nextjs

    api-route:
      preferredModel: codex
      subAgentType: api-builder
      reason: "API security, validation, error handling precision"
      delegation: required
      preferredPalRole: api-builder

    full-stack-feature:
      preferredModel: multi
      preferredModels: [gemini, codex]
      subAgentType: feature-implementer
      reason: "UI parts use Gemini; backend uses Codex (multi-model)"
      delegation: partial
      preferredPalRole: feature-implementer
```

---

### composition.yaml

Prompt composition and content generation configuration. All composition settings are namespaced under the `composition:` key.

```yaml
version: "2.0"

composition:
  # ===========================================================================
  # DEFAULTS
  # ===========================================================================
  defaults:
    dedupe:
      shingle_size: 12
      min_shingles: 5
      threshold: 0.37
    composition_mode: section_merge
    generated_header: |
      <!--
        AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
        Generated by: Edison Framework {{version}}
        Template: {{template}}
        Generated at: {{timestamp}}
        Project config root: {{PROJECT_EDISON_DIR}}
      -->

  # ===========================================================================
  # CONTENT TYPES
  # ===========================================================================
  # Every composable content type is defined here.
  # Each type can be composed via: edison compose <type>
  #
  # Properties:
  #   enabled         - Whether to compose this type (default: true)
  #   description     - Human-readable description
  #   composition_mode - section_merge | concatenate | yaml_merge | json_merge
  #   dedupe          - Enable deduplication (default: false)
  #   registry        - Registry class name (null = GenericRegistry)
  #   content_path    - Source directory path, relative to data/
  #   file_pattern    - Glob pattern for source files
  #   output_path     - Where composed files are written
  #   filename_pattern - Pattern for output filenames

  content_types:
    agents:
      enabled: true
      description: "Agent prompt templates"
      composition_mode: section_merge
      dedupe: false
      registry: null  # Use GenericRegistry
      content_path: "agents"
      file_pattern: "*.md"
      output_path: "{{PROJECT_EDISON_DIR}}/_generated/agents"
      filename_pattern: "{name}.md"

    validators:
      enabled: true
      description: "Validator prompt templates"
      composition_mode: section_merge
      dedupe: false
      registry: null
      content_path: "validators"
      file_pattern: "*.md"
      output_path: "{{PROJECT_EDISON_DIR}}/_generated/validators"
      filename_pattern: "{name}.md"

    constitutions:
      enabled: true
      description: "Role constitutions (orchestrators, agents, validators)"
      composition_mode: section_merge
      dedupe: false
      registry: edison.core.composition.registries.constitutions.ConstitutionRegistry
      content_path: "constitutions"
      file_pattern: "*.md"
      output_path: "{{PROJECT_EDISON_DIR}}/_generated/constitutions"
      filename_pattern: "{NAME}.md"

    guidelines:
      enabled: true
      description: "Guideline documents"
      composition_mode: concatenate
      dedupe: true
      registry: null
      content_path: "guidelines"
      file_pattern: "*.md"
      output_path: "{{PROJECT_EDISON_DIR}}/_generated/guidelines"
      filename_pattern: "{name}.md"

    roots:
      enabled: true
      description: "Root entry point files (AGENTS.md, CLAUDE.md)"
      composition_mode: section_merge
      dedupe: false
      registry: null
      content_path: "roots"
      file_pattern: "*.md"
      output_path: "."
      filename_pattern: "{NAME}.md"
      output_mapping:
        CLAUDE: ".claude/CLAUDE.md"

    schemas:
      enabled: true
      description: "JSON schemas"
      composition_mode: json_merge
      dedupe: false
      registry: edison.core.composition.registries.schemas.JsonSchemaRegistry
      content_path: "schemas"
      file_pattern: "*.json"
      output_path: "{{PROJECT_EDISON_DIR}}/_generated/schemas"
      filename_pattern: "{name}.json"

  # ===========================================================================
  # PLATFORM ADAPTERS
  # ===========================================================================
  adapters:
    claude:
      enabled: true
      adapter_class: edison.core.adapters.platforms.claude.ClaudeAdapter
      description: "Claude Code / Claude Desktop integration"
      output_path: ".claude"
      sync:
        agents:
          enabled: true
          source: "{{PROJECT_EDISON_DIR}}/_generated/agents"
          destination: ".claude/agents"
          filename_pattern: "{name}.md"

    cursor:
      enabled: true
      adapter_class: edison.core.adapters.platforms.cursor.CursorAdapter
      description: "Cursor IDE integration"
      output_path: ".cursor"
```

**Override Example** (`.edison/config/composition.yaml`):

```yaml
# Override composition settings (note the composition: prefix)
composition:
  content_types:
    validators:
      enabled: false  # Disable validator output

    agents:
      output_path: "{{PROJECT_EDISON_DIR}}/custom/agents"  # Custom path
```

#### Write Policies (Managed Blocks)

By default, Edison overwrites generated files entirely (`replace`). For shared instruction files like `AGENTS.md` / `CLAUDE.md`, you may want to preserve manual edits and let Edison manage only a marker-delimited block (`markers`).

You can configure:

- Global glob rules (`composition.write_policies`) for specific files/paths
- Default write policy per content type (`composition.content_types.<type>.write_policy`)
- Default write policy per adapter (`composition.adapters.<name>.write_policy`)

Precedence is: first matching `write_policies` glob rule → content-type/adapter default → `replace`.

```yaml
composition:
  write_policies:
    - id: agents-managed-block
      globs:
        - "AGENTS.md"
        - ".claude/CLAUDE.md"
      policy:
        mode: markers
        begin_marker: "<!-- EDISON:START -->"
        end_marker: "<!-- EDISON:END -->"
        on_missing: prepend  # or: append | error

  content_types:
    roots:
      # Can be a policy id (references write_policies[].id) or an inline mapping.
      write_policy: agents-managed-block

  adapters:
    claude:
      write_policy: agents-managed-block
```

### Configuration Access Architecture

All composition configuration is accessed through `CompositionConfig`:

```python
from edison.core.config.domains.composition import CompositionConfig

comp = CompositionConfig(repo_root=Path("/path/to/project"))

# Access defaults
shingle_size = comp.shingle_size

# Access content types
for ct in comp.get_enabled_content_types():
    print(ct.name, ct.output_path)

# Access adapters
for adapter in comp.get_enabled_adapters():
    print(adapter.name, adapter.adapter_class)
```

Registries use the typed `comp_config` property instead of raw config access.

---

### constitution.yaml

Defines mandatory reads for each role type.

```yaml
version: "1.0.0"

mandatoryReads:
  orchestrator:
    - path: constitutions/ORCHESTRATOR.md
      purpose: Main orchestrator constitution
    - path: guidelines/orchestrators/SESSION_WORKFLOW.md
      purpose: Session lifecycle management
    - path: guidelines/shared/DELEGATION.md
      purpose: Delegation rules and patterns
    - path: AVAILABLE_AGENTS.md
      purpose: Dynamic agent roster
    - path: AVAILABLE_VALIDATORS.md
      purpose: Dynamic validator roster
    - path: guidelines/shared/TDD.md
      purpose: TDD enforcement requirements

  agents:
    - path: guidelines/shared/COMMON.md
      purpose: Shared Context7, TDD, and configuration guardrails
    - path: constitutions/AGENTS.md
      purpose: Agent constitution
    - path: guidelines/agents/MANDATORY_WORKFLOW.md
      purpose: Implementation workflow
    - path: guidelines/shared/TDD.md
      purpose: TDD requirements
    - path: guidelines/shared/CONTEXT7.md
      purpose: Context7 usage requirements

  validators:
    - path: guidelines/shared/COMMON.md
      purpose: Shared Context7, TDD, and configuration guardrails
    - path: constitutions/VALIDATORS.md
      purpose: Validator constitution
    - path: guidelines/validators/VALIDATOR_WORKFLOW.md
      purpose: Validation workflow
    - path: guidelines/shared/CONTEXT7.md
      purpose: Context7 knowledge refresh
```

---

### commands.yaml

IDE slash command generation configuration.

```yaml
commands:
  enabled: true
  # Default to repo-local platforms. Codex prompts are user-global by default
  # (`~/.codex/prompts`) and should be opt-in at the project layer.
  platforms: [claude, cursor]

  # Selection strategy
  selection:
    mode: "domains"  # all | domains | explicit
    domains:
      - session
      - task
      - qa
      - rules
    # Optional domains like `memory` can be enabled at the project layer.
    exclude:
      - setup
      - internal
      - migrate

  # Platform configurations
  platform_config:
    claude:
      enabled: true
      output_dir: ".claude/commands"
      prefix: "edison."
      max_short_desc: 80
      template: "claude-command.md.template"
      # Default to workflow guidance prompts (no implicit execution).
      allow_bash: false

    cursor:
      enabled: true
      output_dir: ".cursor/commands"
      prefix: "edison."
      max_short_desc: 120
      template: "cursor-command.md.template"
      allow_bash: true
```

Notes:

- `commands.selection` exists to keep the slash-command catalog small and relevant.
  - `mode: domains` includes only the listed domains.
  - Packs should put their commands under a distinct domain (e.g. `typescript`) and **projects opt in** by adding that domain.

- **Command definitions are markdown files**, not YAML lists.
  - Core: `src/edison/data/commands/**`
  - User: `~/.edison/commands/**`
  - Project: `.edison/commands/**`
  - Packs: `<pack>/commands/**`
  - Overrides/shadowing are by `id`: higher-precedence layers win when two files define the same `id`.

**Add/Override Example** (`.edison/commands/reporting/custom-report.md`):

```md
---
id: custom-report
domain: reporting
command: report
short_desc: "Generate custom report"
cli: "edison custom report"
args: []
when_to_use: |
  - When you need a project-specific report
related_commands: []
---

Write your full prompt/methodology here.
```

**Override Example: enable extra domains (project opt-in)**:

```yaml
commands:
  selection:
    domains: ["+", "typescript"]
```

**Override Example: disable a core command**:

```yaml
commands:
  definitions:
    - id: task-claim
      enabled: false
```

---

### models.yaml

Model delegation configuration with capabilities and strengths.

```yaml
delegation:
  models:
    codex:
      displayName: "Codex (ChatGPT PRO)"
      provider: pal-mcp
      interface: clink
      roles: [default, planner, codereviewer]
      capabilities:
        editFiles: true
        readFiles: true
        runCommands: true
        reviewCode: true
        generateTests: true
      costTier: medium
      rateLimit:
        requests: 300
        window: "5 hours"
      strengths:
        - precise-refactoring
        - security-auditing
        - performance-analysis
        - type-inference
        - test-generation
        - api-implementation
        - database-schemas
      optimalFor:
        - "API routes and backend logic"
        - "Database schemas and migrations"
        - "Security-critical code"
        - "Type-safe refactoring"

    claude:
      displayName: "Claude Sonnet 4.5"
      provider: anthropic
      interface: direct
      roles: [default, code-reviewer]
      capabilities:
        editFiles: true
        readFiles: true
        runCommands: true
        reviewCode: true
        designComponents: true
      costTier: high
      strengths:
        - architecture-design
        - ui-ux-thinking
        - component-composition
        - integration-work
        - documentation
      optimalFor:
        - "React components and UI"
        - "System architecture"
        - "Feature planning"

    gemini:
      displayName: "Gemini 2.5 Pro/Flash"
      provider: pal-mcp
      interface: clink
      roles: [default, planner, codereviewer]
      capabilities:
        editFiles: true
        readFiles: true
        runCommands: true
        reviewCode: true
        multimodal: true
      strengths:
        - fast-iteration
        - multimodal-analysis
        - creative-tasks
        - large-context-window
      optimalFor:
        - "Rapid prototyping"
        - "Image/diagram analysis"
        - "Large codebase analysis"
```

---

### tdd.yaml

Test-Driven Development enforcement settings.

```yaml
tdd:
  enforceRedGreenRefactor: true
  requireEvidence: true
  hmacValidation: false
```

**Override Example**:

```bash
export EDISON_TDD__ENFORCE_RED_GREEN_REFACTOR=false
```

---

### qa.yaml

Quality assurance and validation workflow configuration.

```yaml
version: "1.0.0"

validation:
  defaultSessionId: "validation-session"

  requiredEvidenceFiles:
    - command-type-check.txt
    - command-lint.txt
    - command-test.txt
    - command-build.txt

  evidence:
    minRequiredFiles: 4
    patterns:
      - "command-*.txt"
      - "context7-*.md"
      - "context7-*.txt"
      - "validator-*-report.md"
      - "validator-*-report.json" # legacy

  transaction:
    maxAgeHours: 24
    autoCleanup: true
```

---

### orchestration.yaml

Multi-agent orchestration and process tracking configuration.

```yaml
orchestration:
  # Whether Edison may execute external CLI validator engines (codex/claude/gemini/etc).
  # Default is false for safety and determinism; projects may override.
  allowCliEngines: false

  tracking:
    # Staleness threshold for "active" runs (seconds since lastActive heartbeat).
    activeStaleSeconds: 120

    # Append-only process events log (JSONL). This is the source of truth for the
    # process list shown in the CLI and edison-ui.
    processEventsJsonl: "{PROJECT_MANAGEMENT_DIR}/logs/edison/process-events.jsonl"
```

Notes:
- This file is **append-only** at runtime: Edison appends one JSON object per line.
- The “process index” is derived from events (no mutable `process-index.json` file).
- Edison may append `process.detected_stopped` when it detects a tracked local PID is no longer running.

---

### worktrees.yaml

Git worktree management for session isolation.

```yaml
worktrees:
  enabled: true
  baseBranch: "main"
  baseDirectory: "../{PROJECT_NAME}-worktrees"
  archiveDirectory: "../{PROJECT_NAME}-worktrees/_archived"
  branchPrefix: "session/"
  pathTemplate: "../{PROJECT_NAME}-worktrees/{sessionId}"
  sharedState:
    # Canonical list of meta-managed shared paths (single source of truth).
    # Includes `.project/*` management state and `.edison/_generated` by default.
    sharedPaths: ["+", {path: ".pal", scopes: ["primary", "session"]}]
    # Meta commit guard: allows sharedPaths with commitAllowed=true + explicit extras.
    commitGuard:
      allowPrefixes: []
    # Excludes are per-worktree via `core.excludesFile`.
    gitExcludes:
      primary: []
      session: []
      meta: []
  cleanup:
    autoArchive: true
    archiveAfterDays: 30
    deleteAfterDays: 90
```

**Override Example**:

```yaml
# .edison/config/worktrees.yaml
worktrees:
  enabled: false  # Disable worktrees
```

Or via environment:

```bash
export EDISON_WORKTREES__ENABLED=false
```

---

### hooks.yaml

Claude Code hooks for workflow enforcement and context injection.

```yaml
hooks:
  enabled: true
  platforms: [claude]

  settings:
    timeout_seconds: 60
    parallel_execution: true
    log_output: true

  definitions:
    # Context injection hooks
    inject-session-context:
      type: UserPromptSubmit
      hook_type: prompt
      enabled: true
      description: "Inject current session context before prompt"
      template: "inject-session-context.sh.template"
      config:
        include_worktree: true
        include_task_state: true
        max_length: 500

    # Guard hooks (can block)
    commit-guard:
      type: PreToolUse
      hook_type: command
      matcher: "Bash(git commit:*)"
      enabled: true
      blocking: true
      description: "Block commits with failing tests"
      template: "commit-guard.sh.template"
      config:
        require_tests_pass: true
        require_coverage: true
        coverage_threshold: 90

    # Validation hooks
    auto-format:
      type: PostToolUse
      hook_type: command
      matcher: "Write|Edit"
      enabled: true
      blocking: false
      description: "Auto-format code after modifications"
      template: "auto-format.sh.template"
      config:
        tools: [prettier, eslint]
```

---

### mcp.yaml

MCP (Model Context Protocol) server configuration.

```yaml
mcp:
  config_file: ".mcp.json"
  tool_names:
    edison_pal_clink: "mcp__edison-pal__clink"

  servers:
    edison-pal:
      # Portable: use uvx to run pal-mcp-server from git
      command: "uvx"
      args:
        - "--from"
        - "git+https://github.com/BeehiveInnovations/pal-mcp-server.git"
        - "pal-mcp-server"
      env:
        PAL_WORKING_DIR: "{PROJECT_ROOT}"
      setup:
        require:
          commands:
            - "uvx"
        instructions: |
          Install uvx: pip install uv
          Configure API keys in {PROJECT_ROOT}/.pal/.env

    context7:
      command: "npx"
      args:
        - "-y"
        - "@upstash/context7-mcp@latest"
      env: {}
      setup:
        require:
          commands:
            - "npx"

    sequential-thinking:
      command: "npx"
      args:
        - "-y"
        - "@modelcontextprotocol/server-sequential-thinking"
      env: {}
```

**Project Override Example** (`.edison/config/mcp.yml`):

```yaml
mcp:
  servers:
    edison-pal:
      # Use local script for development
      command: "./scripts/pal/run-server.sh"
      args: []
      env: {}
```

---

### settings.yaml

Claude Code settings generation.

```yaml
settings:
  enabled: true
  platforms: [claude]

  claude:
    enabled: true
    generate: true
    preserve_custom: true
    backup_before: true

    # Permissions
    permissions:
      allow:
        - "Read(./**)"
        - "Edit(./**)"
        - "Write(./**)"
        - "Bash(git:*)"
        - "WebSearch"
        - "WebFetch"

      deny:
        - "Read(./.env*)"
        - "Edit(./.env*)"
        - "Bash(sudo:*)"
        - "Bash(rm -rf /:*)"

      ask:
        - "Bash(git push:*)"
        - "Bash(npm publish:*)"

    # Environment
    env:
      CLAUDE_CODE_MAX_OUTPUT_TOKENS: "64000"

    enableAllProjectMcpServers: true
    cleanupPeriodDays: 120
```

---

### paths.yaml

Path configuration for Edison project structure.

```yaml
paths:
  project_config_dir: ".edison"
```

---

## Pack Configuration

Packs extend Edison with technology-specific configurations, guidelines, and validators.

### Available Packs

Edison includes the following bundled packs:

- `typescript` - TypeScript support
- `react` - React component development
- `nextjs` - Next.js application framework
- `prisma` - Prisma ORM and database
- `tailwind` - Tailwind CSS styling
- `vitest` - Vitest testing framework
- `e2e-web` - Playwright-first web E2E testing + browser UI validation
- `fastify` - Fastify API framework

### Pack Portability

Projects may enable packs that are not available on every developer machine (e.g. user-only packs under `~/.edison/packs/`). Edison can warn or fail fast:

- `packs.portability.userOnly: warn|error|off` — a pack exists only in the user pack root
- `packs.portability.missing: warn|error|off` — a pack listed in `packs.active` is missing from all pack roots

### Pack Structure

Packs can live in any pack root, and the structure is identical in each root:
- Bundled: `src/edison/data/packs/{pack}/` (ships with Edison)
- User: `~/.edison/packs/{pack}/` (personal, not committed)
- Project: `.edison/packs/{pack}/` (committed to the repo)

Each pack is located in `{packs_root}/{pack}/` with:

```
packs/{pack}/
├── config/
│   ├── setup.yml          # Setup questions and config templates
│   ├── commands.yml       # Pack-specific commands (optional)
│   └── hooks.yml          # Pack-specific hooks (optional)
├── agents/
│   └── overlays/          # Agent prompt extensions
├── validators/
│   └── specialized/       # Pack-specific validators
├── guidelines/
│   └── overlays/          # Guideline extensions
└── pack-dependencies.yaml # Pack dependencies
```

### pack-dependencies.yaml

Defines pack dependencies and npm packages.

**Example** (`nextjs/pack-dependencies.yaml`):

```yaml
dependencies:
  - react
  - typescript
```

**Example** (`typescript/pack-dependencies.yaml`):

```yaml
requiredPacks: []
dependencies: {}
devDependencies:
  typescript: "^5.7.2"
  tsx: "^4.0.0"
```

### Pack Setup Configuration

Packs can define setup questions.

**Example** (`typescript/config/setup.yml`):

```yaml
setup:
  questions:
    - id: typescript_strict
      prompt: "Enable TypeScript strict mode?"
      type: boolean
      default: true
      mode: basic
      category: packs
      help: "Strict mode enables all strict type-checking options"
      depends_on:
        - pack: typescript
          enabled: true

    - id: typescript_target
      prompt: "TypeScript compilation target"
      type: choice
      source: static
      options: [ES2020, ES2021, ES2022, ESNext]
      default: ES2022
      mode: advanced
      category: packs

  config_template:
    typescript:
      strict: "{{ typescript_strict }}"
      target: "{{ typescript_target }}"
      module: "{{ typescript_module }}"
```

### Enabling Packs

Packs are configured in `.edison/config/packs.yaml`:

```yaml
packs:
  enabled: true
  directory: ".edison/packs"
  composition:
    strategy: deep-merge
    sections:
      - dependencies
      - devDependencies
      - scripts

  loadOrder:
    algorithm: toposort
    dependencyFile: "pack-dependencies.yaml"
```

### Default Pack Scripts

Edison provides default scripts for common packs:

```yaml
defaults:
  nextjs:
    scripts:
      "next:dev": "next dev"
      "next:build": "next build"
      "next:start": "next start"

  prisma:
    scripts:
      "db:generate": "prisma generate"
      "db:migrate": "prisma migrate dev"
      "db:studio": "prisma studio"

  typescript:
    scripts:
      "type-check": "tsc --noEmit"

  vitest:
    scripts:
      "test": "vitest run"
```

---

## Project Configuration

Project-specific overrides are placed in `.edison/config/`.

### Directory Structure

```
.edison/
├── config/
│   ├── delegation.yaml      # Override delegation rules
│   ├── validators.yaml      # Override validator config
│   ├── composition.yaml     # Override composition settings
│   ├── session.yaml         # Override session settings
│   ├── mcp.yml             # Override MCP servers
│   └── ...                  # Any core config file
├── agents/
│   └── overlays/            # Extend or override agent prompts
├── validators/
│   └── specialized/         # Add project-specific validators
├── guidelines/
│   └── overlays/            # Extend guidelines
└── packs.yaml              # Enable/configure packs
```

### Merge Behavior

- **Objects**: Deep merge with project config taking precedence
- **Lists**: Project config can:
  - Replace entire list
  - Append items (`EDISON_KEY__APPEND`)
  - Set specific indices (`EDISON_KEY__0`)
- **Scalars**: Project config replaces default

### Example Overrides

**`.edison/config/delegation.yaml`**:

```yaml
# Add custom file pattern rule
delegation:
  filePatternRules:
    "**/custom/**/*.ts":
      preferredModel: claude
      reason: "Custom logic requires architectural thinking"
      subAgentType: feature-implementer
      confidence: high
```

**`.edison/config/validators.yaml`**:

```yaml
# Disable a validator
validation:
  roster:
    specialized:
      - id: react
        name: React Validator
        enabled: false  # Disable React validator
```

**`.edison/config/session.yaml`**:

```yaml
# Increase session timeout
session:
  recovery:
    timeoutHours: 16

  worktree:
    timeouts:
      install: 600
```

---

## Configuration Examples

### Example 1: Increase Session Timeout

**Via Environment**:

```bash
export EDISON_SESSION__RECOVERY__TIMEOUT_HOURS=16
```

**Via Project Config** (`.edison/config/session.yaml`):

```yaml
session:
  recovery:
    timeoutHours: 16
```

---

### Example 2: Disable Worktrees

**Via Environment**:

```bash
export EDISON_WORKTREES__ENABLED=false
```

**Via Project Config** (`.edison/config/worktrees.yaml`):

```yaml
worktrees:
  enabled: false
```

---

### Example 3: Add Custom Validator

**`.edison/config/validators.yaml`**:

```yaml
validation:
  roster:
    specialized:
      - id: custom-accessibility
        name: Accessibility Validator
        model: claude
        interface: Task
        role: code-reviewer
        palRole: validator-accessibility
        specFile: specialized/accessibility.md
        triggers: ["**/*.tsx", "**/*.jsx"]
        alwaysRun: false
        priority: 3
        context7Required: false
        blocksOnFail: false
```

Then create `.edison/validators/specialized/accessibility.md`:

```markdown
# Accessibility Validator

## Purpose
Validate WCAG 2.1 AA compliance and accessibility best practices.

## Checks
- Semantic HTML usage
- ARIA attributes
- Keyboard navigation
- Color contrast ratios
- Screen reader compatibility

## Examples
...
```

---

### Example 4: Custom Delegation Rule

**`.edison/config/delegation.yaml`**:

```yaml
delegation:
  filePatternRules:
    "**/utils/analytics/*.ts":
      preferredModel: codex
      reason: "Analytics tracking requires precision"
      subAgentType: api-builder
      preferredPalRole: api-builder
      confidence: high
```

---

### Example 5: Configure MCP Server

**`.edison/config/mcp.yml`**:

```yaml
mcp:
  servers:
    custom-mcp:
      command: "npx"
      args:
        - "-y"
        - "my-custom-mcp-server"
      env:
        CUSTOM_API_KEY: "{API_KEY}"
      setup:
        require:
          commands:
            - "npx"
        instructions: |
          Set CUSTOM_API_KEY in .env file
```

---

### Example 6: Sequential Validator Execution

**Via Environment**:

```bash
export EDISON_VALIDATION__EXECUTION__MODE=sequential
export EDISON_VALIDATION__EXECUTION__CONCURRENCY=1
```

**Via Project Config** (`.edison/config/validators.yaml`):

```yaml
validation:
  execution:
    mode: sequential
    concurrency: 1
```

---

### Example 7: Disable TDD Enforcement

**Via Environment**:

```bash
export EDISON_TDD__ENFORCE_RED_GREEN_REFACTOR=false
export EDISON_TDD__REQUIRE_EVIDENCE=false
```

**Via Project Config** (`.edison/config/tdd.yaml`):

```yaml
tdd:
  enforceRedGreenRefactor: false
  requireEvidence: false
```

---

### Example 8: Custom Project Config Directory

```bash
export EDISON_paths__project_config_dir=.custom_edison

# Edison will now look for config in .custom_edison/ instead of .edison/
```

---

## Best Practices

1. **Use Environment Variables for Temporary Overrides**
   - CI/CD settings
   - Developer-specific preferences
   - Testing configurations

2. **Use Project Config for Permanent Overrides**
   - Team-wide standards
   - Project-specific rules
   - Custom validators and delegation rules

3. **Document Your Overrides**
   - Add comments explaining why overrides exist
   - Keep override files minimal - only override what's necessary

4. **Test Configuration Changes**
   - Use `edison config validate` to check config validity
   - Test in isolation before committing

5. **Version Control**
   - Commit `.edison/config/` to version control
   - Do NOT commit `.env` files
   - Use `.gitignore` for sensitive config

6. **Configuration Debugging**
   - Use `edison config show` to see merged configuration
   - Check precedence with `edison config explain <key>`

---

## Placeholder Variables

Edison supports the following placeholder variables in configuration:

- `{PROJECT_ROOT}` - Project root directory
- `{PROJECT_NAME}` - Project name
- `{PROJECT_CONFIG_DIR}` or `{{PROJECT_EDISON_DIR}}` - Edison config directory (default: `.edison`)
- `{API_KEY}` - Placeholder for API keys (replace with actual values)

These are automatically resolved when configuration is loaded.

---

## Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [Getting Started](./GETTING_STARTED.md)
- [CLI Reference](./CLI_REFERENCE.md)
- [Validation Guide](./VALIDATION.md)

---

## Configuration Reference Summary

| File | Purpose | Key Settings |
|------|---------|-------------|
| `workflow.yaml` | Workflow & State machines | Task/QA/Session states, transitions, lifecycle |
| `session.yaml` | Session management | Paths, recovery, worktrees, timeouts |
| `validators.yaml` | Validation framework | Validator roster, execution, dimensions |
| `delegation.yaml` | Agent delegation | File patterns, task types, model preferences |
| `composition.yaml` | Prompt composition | Content types, outputs, deduplication |
| `constitution.yaml` | Role requirements | Mandatory reads per role |
| `commands.yaml` | IDE commands | Slash command generation |
| `models.yaml` | Model capabilities | Model strengths, costs, rate limits |
| `tdd.yaml` | TDD enforcement | Red-Green-Refactor, evidence |
| `qa.yaml` | QA workflow | Evidence files, orchestration |
| `worktrees.yaml` | Worktree management | Branch prefix, cleanup, paths |
| `hooks.yaml` | Claude Code hooks | Context injection, guards, validation |
| `mcp.yaml` | MCP servers | Server definitions, setup |
| `settings.yaml` | Claude settings | Permissions, environment |
| `paths.yaml` | Path configuration | Config directory location |
| `packs.yaml` | Pack system | Load order, composition strategy |

## Unified Templating & Functions (Composition)

- **Pipeline order**: sections/extend → includes → variables (config/context) → conditionals → loops → references → functions.
- **Syntax**:
  - Sections: `<!-- SECTION: name -->...<!-- /SECTION: name -->`, `<!-- EXTEND: name -->...`
  - Includes: `{{include:path/to/file.md}}`, `{{include-section:path#section}}`
  - Conditionals: `{{if:cond}}...{{/if}}`, `{{include-if:cond:path}}`
  - Loops: `{{#each items}}...{{/each}}`
  - Variables: `{{config.key}}`, `{{PROJECT_ROOT}}`, `{{timestamp}}`, plus context vars
  - References: `{{reference-section:path#name|purpose}}`
  - Functions: `{{fn:name arg1 arg2}}`
- **Functions extension**:
  - Place `.py` files under `functions/` in core, packs, or project. Later layers override earlier.
  - Functions must return strings; args are passed as strings.
  - Loader: core → active packs → project.
  - Example: `{{fn:task_states current_state}}` or `{{fn:task_states}}`.

---

**Last Updated**: 2025-12-04

👉 Comprehensive templating/composition guide: `docs/TEMPLATING.md`.
