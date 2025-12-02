# Edison Framework

AI-automated project management and software development framework that orchestrates multiple LLM agents to implement, validate, and manage tasks with strict workflows and state machine-driven execution.

## What is Edison?

Edison is a comprehensive framework for managing AI-driven software development. It provides a structured environment where multiple specialized AI agents collaborate through well-defined roles, state machines, and validation workflows. Each agent operates within isolated work contexts (sessions) with their own git worktrees, ensuring clean separation of concerns and enabling parallel development.

The framework enforces strict workflows through state machines, requires test-driven development (TDD), and validates all work through multi-model consensus before accepting it as complete. Configuration is entirely YAML-based with zero hardcoded values, making every aspect of the framework customizable.

## Key Features

### Multi-Agent Orchestration
- **Orchestrator agents** coordinate work and delegate to specialized agents
- **Implementer agents** execute tasks following strict TDD workflows
- **Validator agents** review and validate completed work
- Each role has mandatory constitutions (behavioral rules) and guidelines

### Session-Based Isolation
- Each session gets its own git worktree for complete isolation
- Sessions have independent working directories, preventing conflicts
- State machine manages session lifecycle: draft → active → done → validated → archived
- Automatic recovery mechanisms for timed-out or failed sessions

### State Machine-Driven Workflows
- **Task states**: todo → wip → done → validated (with optional blocked state)
- **QA states**: waiting → todo → wip → done → validated
- **Session states**: draft → active → done → closing → validated → archived
- Guards and conditions enforce valid state transitions
- All transitions configurable via YAML

### TDD Enforcement
- Test-first development required by default
- Validation checks for test coverage, type checking, linting, and builds
- Evidence files automatically collected for each validation round
- Required evidence: command-type-check.txt, command-lint.txt, command-test.txt, command-build.txt, command-coderabbit.txt

### Multi-Model Validation
- Same task validated by multiple LLMs for consensus
- Parallel or sequential validator execution
- Configurable timeout per validator (default: 300s)
- Maximum concurrent validators (default: 4)
- External validators (CodeRabbit CLI) with LLM-driven report transformation
- Comprehensive validation reports in JSON format

### Configurable via YAML
- Zero hardcoded values - all behavior driven by configuration
- Hierarchical config system: core → packs → project
- JSON schema validation for all config files
- Runtime composition of prompts, guidelines, and constitutions

### Composition System
- Prompts, guidelines, and constitutions composed from multiple layers
- Section-based composition with placeholders and overlays
- HTML comment syntax for extending core content
- Automatic deduplication using 12-word shingles
- Supports: agents, validators, guidelines, constitutions, start prompts, CodeRabbit config

### Technology Packs
- Framework-specific rules and validations
- Available packs: React, Next.js, TypeScript, Tailwind, Prisma, Vitest, FastAPI, Better Auth, Motion
- Each pack provides validators, guidelines, examples, and CodeRabbit review instructions
- Auto-activation based on file patterns (e.g., `**/*.ts` activates TypeScript pack)
- Custom packs supported via template

## Quick Start

### Installation

```bash
# From PyPI
pip install edison

# Or using uv (recommended)
uv pip install edison

# For development
git clone https://github.com/yourorg/edison.git
cd edison
pip install -e ".[dev]"
```

### Initialize a Project

```bash
# Interactive initialization
cd your-project
edison init

# Non-interactive (uses defaults)
edison init --non-interactive

# This creates:
# - .edison/ directory with config and generated artifacts
# - .project/ directory for sessions, tasks, and QA
# - .mcp.json for Zen MCP Server integration
```

### Compose Artifacts

After initialization, compose all prompts, guidelines, and constitutions:

```bash
# Compose everything
edison compose all

# Or compose specific types
edison compose agents
edison compose validators
edison compose guidelines
edison compose constitutions
edison compose start
edison compose coderabbit
```

### Create and Work on Tasks

```bash
# Create a new task
edison task new --id 100 --slug implement-auth --description "Implement user authentication"

# Create a session
edison session create --session-id sess-001

# Claim a task for the session
edison task claim 100-implement-auth --session sess-001

# Start working on the session (loads composed start prompt)
edison session next sess-001

# Check session status
edison session status sess-001

# Mark task as done when implementation complete
# (status updates tracked in task files)

# Close session when finished
edison session close sess-001
```

### Validation Workflow

```bash
# Create QA brief for a completed task
edison qa new 100-implement-auth

# Run validation round (delegates to validator agents)
edison qa validate 100-implement-auth --round 1

# Check validation status
edison qa audit 100-implement-auth

# Promote task to validated if all validators pass
edison qa promote 100-implement-auth
```

## Core Concepts

### Sessions
Isolated work contexts with their own git worktree and state. Each session is linked to one or more tasks and progresses through states:
- **draft**: Initial state, not yet active
- **active/wip**: Work in progress
- **done**: Implementation complete, awaiting validation
- **closing**: Finalizing session
- **validated**: All validation complete
- **archived**: Final state, session can be cleaned up

Sessions support recovery mechanisms for timeouts and failures.

### Tasks
Units of work tracked through a state machine:
- **todo**: Awaiting claim by a session
- **wip**: Work in progress
- **blocked**: Waiting on external dependencies or blockers
- **done**: Implementation complete, awaiting validation
- **validated**: Final state, all validation passed

Tasks can be split into subtasks, linked to other tasks, and delegated to sub-agents.

### QA Briefs
Validation records paired with tasks. Each QA brief tracks:
- Multiple validation rounds
- Evidence files (test output, type checks, lint results, build logs)
- Validator reports from multiple models
- Final validation status

QA briefs follow their own state machine: waiting → todo → wip → done → validated

### Roles
Three primary roles with distinct responsibilities:

**Orchestrator**
- Coordinates overall workflow
- Delegates tasks to implementer agents
- Makes high-level decisions
- Does not write code directly

**Agent** (Implementer)
- Executes assigned tasks
- Follows TDD workflow strictly
- Writes code, tests, and documentation
- Collects evidence for validation

**Validator**
- Reviews completed work
- Checks adherence to guidelines and best practices
- Verifies test coverage, type safety, and code quality
- Provides structured feedback and validation reports

### Constitutions
Mandatory behavioral rules for each role. Constitutions define:
- Core principles that must be followed
- Prohibited actions
- Required workflows
- Decision-making frameworks

Constitutions are composed from core + packs + project overrides.

### Guidelines
Best practices and workflow documentation. Guidelines provide:
- Recommended patterns
- Framework-specific advice
- Code examples
- Troubleshooting tips

Unlike constitutions (mandatory), guidelines are advisory.

### Packs
Technology-specific configurations that activate based on file patterns:

**Available Packs:**
- **React**: Component patterns, hooks, state management
- **Next.js**: App Router, Server Components, routing
- **TypeScript**: Strict mode, type safety, advanced types
- **Tailwind**: Utility classes, responsive design, dark mode
- **Prisma**: Schema design, migrations, query patterns
- **Vitest**: Test structure, mocking, coverage
- **FastAPI**: API patterns, dependency injection, async
- **Better Auth**: Authentication flows, session management
- **Motion**: Animation patterns, gestures, transitions

Each pack provides validators, guidelines, and examples that compose into the final artifacts.

## Project Structure

After running `edison init`, your project will have:

```
your-project/
├── .edison/                          # Edison configuration
│   ├── config/                       # Project-specific overrides
│   │   ├── settings.yaml             # Core settings
│   │   ├── packs.yaml                # Pack configuration
│   │   └── ...                       # Other config files
│   ├── packs/                        # Custom packs (optional)
│   │   └── my-pack/
│   │       ├── pack.yml              # Pack manifest
│   │       ├── validators/           # Validator overlays
│   │       ├── guidelines/           # Guidelines
│   │       └── examples/             # Code examples
│   └── _generated/                   # Composed artifacts (don't edit)
│       ├── constitutions/            # Role constitutions
│       │   ├── orchestrator.md
│       │   ├── agent.md
│       │   └── validator.md
│       ├── agents/                   # Agent prompts
│       │   └── implementer.md
│       ├── validators/               # Validator prompts
│       │   └── codex.md
│       ├── guidelines/               # Guideline documents
│       │   ├── tdd-workflow.md
│       │   └── ...
│       └── start/                    # Session start prompts
│           └── default.md
├── .project/                         # Runtime data
│   ├── sessions/                     # Session files
│   │   ├── wip/                      # Active sessions
│   │   ├── done/                     # Completed sessions
│   │   ├── validated/                # Validated sessions
│   │   └── _tx/                      # Transaction logs
│   ├── tasks/                        # Task files
│   │   ├── todo/                     # Unclaimed tasks
│   │   ├── wip/                      # Tasks in progress
│   │   ├── done/                     # Completed tasks
│   │   └── validated/                # Validated tasks
│   └── qa/                           # QA briefs and evidence
│       ├── briefs/                   # Validation briefs
│       ├── evidence/                 # Collected evidence
│       └── reports/                  # Validator reports
└── .mcp.json                         # Zen MCP Server config
```

### Important Directories

**`.edison/config/`** - Project-specific configuration overrides. Edit these files to customize Edison behavior for your project.

**`.edison/_generated/`** - Auto-generated composed artifacts. Never edit these directly - they're regenerated by `edison compose`.

**`.project/`** - Runtime data including sessions, tasks, and QA briefs. This directory is created automatically and managed by Edison commands.

## Common Workflows

### Starting a New Feature

```bash
# 1. Create task
edison task new --id 200 --slug user-profile --description "Add user profile page"

# 2. Create session
edison session create --session-id feature-profile

# 3. Claim task
edison task claim 200-user-profile --session feature-profile

# 4. Start working (loads context and guidelines)
edison session next feature-profile

# 5. Implement following TDD:
#    - Write failing tests first
#    - Implement code to pass tests
#    - Refactor and clean up
#    - Commit changes

# 6. Mark done and close session
edison session close feature-profile

# 7. Create QA brief
edison qa new 200-user-profile

# 8. Run validation
edison qa validate 200-user-profile --round 1

# 9. Review validation results
edison qa audit 200-user-profile

# 10. If validation passes, promote to validated
edison qa promote 200-user-profile
```

### Working with Packs

```bash
# List available packs
ls .edison/packs/

# View pack configuration
cat .edison/config/packs.yaml

# Enable/disable packs (edit packs.yaml)
# Packs auto-activate based on file patterns

# Recompose after pack changes
edison compose all
```

### Custom Pack Creation

```bash
# 1. Copy template
cp -r src/edison/data/packs/_template .edison/packs/my-pack

# 2. Edit pack manifest
vim .edison/packs/my-pack/pack.yml

# 3. Add validators (required: codex.md overlay)
vim .edison/packs/my-pack/validators/overlays/codex.md

# 4. Add guidelines and examples
vim .edison/packs/my-pack/guidelines/my-guide.md
vim .edison/packs/my-pack/examples/example.ts

# 5. Validate pack
edison config validate

# 6. Recompose
edison compose all
```

### Recovery and Troubleshooting

```bash
# Check session health
edison session status --all

# Recover timed-out sessions
edison session recovery recover

# Clear stale locks
edison session recovery clear-locks

# Clean up orphaned worktrees
edison session recovery clean-worktrees

# Repair session data
edison session recovery repair --session-id sess-001

# Check git worktree status
edison git worktree-health

# List all worktrees
edison git worktree-list

# Archive completed worktrees
edison git worktree-archive --session-id sess-001
```

## Configuration

### Hierarchical Config System

Edison uses a three-layer configuration system:

1. **Core** - Built-in defaults from `src/edison/data/config/`
2. **Packs** - Framework-specific overrides from packs
3. **Project** - Project-specific overrides from `.edison/config/`

Later layers override earlier layers. The final composed configuration is used at runtime.

### Key Configuration Files

**settings.yaml** - Core Edison settings
```yaml
edison:
  version: "1.0.0"
  projectRoot: "."

session:
  worktree:
    enabled: true
    basePath: ".worktrees"
```

**packs.yaml** - Pack configuration
```yaml
packs:
  enabled:
    - typescript
    - react
    - nextjs
    - vitest
    - tailwind
```

**composition.yaml** - Composition rules
```yaml
content_types:
  agents:
    known_sections:
      - name: Role
        mode: replace
      - name: Guidelines
        mode: append
```

**state-machine.yaml** - State transition rules
```yaml
statemachine:
  task:
    states:
      todo:
        allowed_transitions:
          - to: wip
            guard: can_start_task
```

### Validation

```bash
# Validate all configuration
edison config validate

# Show current configuration
edison config show

# Interactive configuration
edison config configure
```

## CLI Reference

### Session Commands

```bash
edison session create --session-id <id>           # Create new session
edison session next <session-id>                  # Start working on session
edison session status <session-id>                # Check session status
edison session close <session-id>                 # Close session
edison session validate <session-id>              # Validate session
edison session me                                 # Show current session
```

### Task Commands

```bash
edison task new --id <id> --slug <slug>          # Create new task
edison task claim <task-id> --session <sess-id>  # Claim task for session
edison task ready                                # List ready tasks
edison task list                                 # List all tasks
edison task status <task-id>                     # Check task status
edison task split <task-id>                      # Split into subtasks
edison task link <task-id> <target-id>           # Link related tasks
```

### QA Commands

```bash
edison qa new <task-id>                          # Create QA brief
edison qa validate <task-id> --round <n>         # Run validation round
edison qa audit <task-id>                        # Review validation results
edison qa promote <task-id>                      # Promote to validated
edison qa bundle <task-ids...>                   # Bundle multiple validations
```

### Composition Commands

```bash
edison compose all                               # Compose everything
edison compose agents                            # Compose agent prompts
edison compose validators                        # Compose validator prompts
edison compose guidelines                        # Compose guidelines
edison compose constitutions                     # Compose constitutions
edison compose start                             # Compose start prompts
edison compose coderabbit                        # Compose .coderabbit.yaml
edison compose validate                          # Validate composed output
edison compose hooks                             # Setup git hooks
```

### Config Commands

```bash
edison config validate                           # Validate configuration
edison config show                               # Show current config
edison config configure                          # Interactive configuration
```

### Git Commands

```bash
edison git worktree-create <session-id>          # Create worktree
edison git worktree-list                         # List worktrees
edison git worktree-health                       # Check worktree health
edison git worktree-cleanup                      # Clean up worktrees
edison git worktree-archive --session <id>       # Archive worktree
edison git status                                # Git status for session
```

### MCP Commands

```bash
edison mcp setup                                 # Setup Zen MCP Server
edison mcp configure                             # Configure .mcp.json
edison mcp setup --check                         # Verify setup
```

## Zen MCP Integration

Edison uses the [Zen MCP Server](https://github.com/BeehiveInnovations/zen-mcp-server) for sub-agent delegation via the Model Context Protocol.

### Setup

```bash
# Automatic during init
edison init my-project

# Or manual setup
pip install uv                    # Provides uvx
edison mcp setup                  # Setup Zen
edison mcp configure .            # Configure project
edison mcp setup --check          # Verify
```

### Configuration

The `.mcp.json` file configures the Zen MCP Server:

```json
{
  "mcpServers": {
    "edison-zen": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/BeehiveInnovations/zen-mcp-server.git",
        "zen-mcp-server"
      ],
      "env": {
        "ZEN_WORKING_DIR": "/path/to/project"
      }
    }
  }
}
```

For detailed setup instructions and troubleshooting, see [docs/ZEN_SETUP.md](docs/ZEN_SETUP.md).

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourorg/edison.git
cd edison

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
edison --help
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/edison --cov-report=html

# Run specific test categories
pytest -m integration          # Integration tests
pytest -m e2e                  # End-to-end tests
pytest -m fast                 # Fast unit tests
pytest -m "not slow"           # Skip slow tests

# Run specific test file
pytest tests/unit/test_session.py

# Verbose output
pytest -v --tb=short
```

### Code Quality

```bash
# Type checking
mypy src/edison

# Linting
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Project Structure

```
edison/
├── src/edison/                  # Source code
│   ├── cli/                     # CLI commands (auto-discovered)
│   │   ├── session/             # Session commands
│   │   ├── task/                # Task commands
│   │   ├── qa/                  # QA commands
│   │   ├── compose/             # Composition commands
│   │   └── ...
│   ├── core/                    # Core library
│   │   ├── session/             # Session management
│   │   ├── task/                # Task management
│   │   ├── qa/                  # QA and validation
│   │   ├── composition/         # Composition engine
│   │   ├── config/              # Configuration system
│   │   └── ...
│   └── data/                    # Bundled data
│       ├── config/              # Default configs
│       ├── schemas/             # JSON schemas
│       ├── packs/               # Technology packs
│       ├── constitutions/       # Role constitutions
│       ├── agents/              # Agent templates
│       ├── validators/          # Validator templates
│       ├── guidelines/          # Guideline documents
│       └── start/               # Start prompts
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   └── fixtures/                # Test fixtures
├── docs/                        # Documentation
├── pyproject.toml               # Project metadata
└── README.md                    # This file
```

## Documentation

- [Zen MCP Setup Guide](docs/ZEN_SETUP.md) - Detailed Zen MCP Server integration guide

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Write tests first** (TDD) for new functionality
3. **Follow the code style** - use ruff for linting and formatting
4. **Update documentation** for user-facing changes
5. **Run the full test suite** before submitting
6. **Submit a pull request** with a clear description

### Code Standards

- Python 3.10+ required
- Type hints mandatory for all functions
- 100 character line length limit
- Follow existing patterns and conventions
- Zero hardcoded values - everything in YAML
- Comprehensive test coverage

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Documentation**: Check docs/ directory for guides

## Version

Current version: 1.0.0

See [pyproject.toml](pyproject.toml) for detailed version information and dependencies.
