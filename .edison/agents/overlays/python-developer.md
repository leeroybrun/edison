---
name: python-developer
project: edison
overlay_type: extend
---

<!-- EXTEND: Tools -->

### Edison CLI Commands

```bash
# Edison CLI development
edison --help
edison config validate
edison compose all

# Run Edison tests
pytest tests/ -v --tb=short

# Run specific test module
pytest tests/unit/test_module.py -v

# Run with coverage
pytest tests/ --cov=src/edison --cov-report=term-missing

# Type check Edison
mypy --strict src/edison/

# Lint Edison
ruff check src/edison/ tests/
```

<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->

### Edison Framework Development Guidelines

1. **CLI Command Structure**
   - Commands live in `src/edison/cli/{domain}/{command}.py`
   - Each command has `register_args()` and `main()` functions
   - Commands are auto-discovered (no manual registry)
   - Follow existing command patterns exactly

2. **Configuration System**
   - All config in `src/edison/data/config/*.yaml`
   - Use domain-specific config accessors
   - No hardcoded values in code
   - Config validated against JSON schemas

3. **Entity Pattern**
   - Entities inherit from `BaseEntity`
   - Use state machines for lifecycle
   - Store as JSON in `.project/` directory
   - Record state history for audit

4. **Composition System**
   - Use section markers: `{{SECTION:Name}}`
   - Overlays extend base files
   - Layered: Core → Packs → Project
   - Deduplication applied automatically

5. **Pack Development**
   - Follow `src/edison/data/packs/_template/` structure
   - Define triggers in `pack.yml`
   - Create agent/validator overlays
   - Add guidelines and examples

### Edison-Specific Patterns

```python
# Config accessor pattern
from edison.core.config import ConfigManager

config = ConfigManager()
timeout = config.get("session.recovery.timeoutHours", default=24)

# Entity pattern
from edison.core.entity import BaseEntity

@dataclass
class Task(BaseEntity):
    title: str
    status: str = "pending"

# State machine pattern
from edison.core.state import StateValidator

StateValidator.ensure_transition("task", "pending", "in_progress")
```

<!-- /EXTEND -->

<!-- NEW_SECTION: EdisonArchitecture -->

## Edison Architecture

### Module Organization

```
src/edison/
├── cli/                    # CLI commands (auto-discovered)
│   ├── session/           # Session commands
│   ├── task/              # Task commands
│   ├── qa/                # QA commands
│   └── compose/           # Composition commands
├── core/                   # Core business logic
│   ├── config/            # Configuration system
│   ├── entity/            # Entity framework
│   ├── state/             # State machines
│   ├── session/           # Session domain
│   ├── task/              # Task domain
│   ├── qa/                # QA domain
│   └── composition/       # Composition engine
└── data/                   # Bundled data
    ├── config/            # YAML configs
    ├── packs/             # Technology packs
    ├── agents/            # Agent definitions
    ├── validators/        # Validator definitions
    └── guidelines/        # Guideline documents
```

### Key Design Principles

1. **Auto-Discovery**: CLI commands, packs discovered from filesystem
2. **Layered Composition**: Core < Packs < Project overlays
3. **Configuration-Driven**: All behavior from YAML
4. **State Machines**: All entities have state lifecycle
5. **Section-Based Composition**: Markdown sections composable

<!-- /NEW_SECTION -->
