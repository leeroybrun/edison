---
name: feature-implementer
project: edison
overlay_type: extend
---

<!-- EXTEND: Tools -->

### Edison Development Tools

```bash
# Edison CLI
edison --help
edison config validate
edison compose all
edison session create --session-id test

# Development commands
pytest tests/ -v --tb=short
mypy --strict src/edison/
ruff check src/edison/ tests/

# Run specific tests
pytest tests/unit/test_cli.py -v
pytest tests/integration/test_session.py -v
pytest tests/e2e/test_workflow.py -v

# Install in dev mode
pip install -e ".[dev]"
```

<!-- /EXTEND -->

<!-- EXTEND: Guidelines -->

### Edison Feature Implementation Guidelines

1. **Follow Edison's Own Principles (CLAUDE.md)**
   - STRICT TDD: Write failing test first
   - NO MOCKS: Test real behavior
   - NO HARDCODING: Config from YAML
   - DRY: No code duplication
   - SOLID: Clean architecture

2. **CLI Command Development**
   ```python
   # src/edison/cli/{domain}/{command}.py
   def register_args(parser: argparse.ArgumentParser) -> None:
       parser.add_argument("--option", help="Description")

   def main(args: argparse.Namespace) -> int:
       # Implementation
       return 0  # Exit code
   ```

3. **Configuration Accessors**
   ```python
   from edison.core.config import QAConfig

   qa_config = QAConfig()
   timeout = qa_config.validator_timeout
   ```

4. **Entity Development**
   ```python
   from dataclasses import dataclass
   from edison.core.entity import BaseEntity

   @dataclass
   class NewEntity(BaseEntity):
       field: str

       def to_dict(self) -> dict:
           return {"id": self.id, "field": self.field}
   ```

5. **State Machine Integration**
   ```python
   from edison.core.state import StateValidator

   # Validate transition
   StateValidator.ensure_transition("entity_type", "from_state", "to_state")
   ```

### Edison-Specific Patterns to Follow

- Study existing CLI commands before creating new ones
- Follow the exact same patterns and structure
- Use existing utilities from `edison.core.utils`
- Add config to YAML files, not code
- Create tests in the appropriate test directory

<!-- /EXTEND -->

<!-- NEW_SECTION: EdisonDevWorkflow -->

## Edison Development Workflow

### Adding a New CLI Command

1. Create command file: `src/edison/cli/{domain}/{command}.py`
2. Implement `register_args()` and `main()` functions
3. Command auto-discovered on next run
4. Add tests in `tests/unit/cli/test_{command}.py`

### Adding a New Pack

1. Copy template: `cp -r src/edison/data/packs/_template src/edison/data/packs/new_pack`
2. Edit `pack.yml` with triggers and metadata
3. Create agent overlays in `agents/overlays/`
4. Create validator overlays in `validators/overlays/`
5. Add guidelines in `guidelines/`
6. Run `edison compose all` to verify

### Adding Configuration

1. Add YAML file or section to `src/edison/data/config/`
2. Create domain accessor in `src/edison/core/config/`
3. Add JSON schema if needed
4. Update tests

### Testing Changes

```bash
# Run all tests
pytest tests/ -v

# Run specific domain
pytest tests/unit/core/session/ -v

# Run with coverage
pytest tests/ --cov=src/edison --cov-report=term-missing

# Type check
mypy --strict src/edison/
```

<!-- /NEW_SECTION -->
