# Edison Framework

AI-automated project management framework for coordinating AI agents, managing tasks, and orchestrating complex software development workflows.

## Installation

```bash
# From PyPI (after publishing)
pip install edison

# Or using uvx
uvx edison --help

# For development
pip install -e .
```

## Usage

```bash
# Get help
edison --help

# Session management
edison session next [session-id]
edison session status [session-id]
edison session close [session-id]

# Task management
edison task ready
edison task claim <task-id>
edison task status <task-id>

# Configuration
edison config validate
edison config configure

# Validation
edison validators validate <task-id>
```

## Project Structure

```
src/edison/
├── cli/           # CLI with auto-discovery
│   ├── session/   # Session commands
│   ├── task/      # Task commands
│   └── ...
├── core/          # Core library
│   ├── session/   # Session management
│   ├── task/      # Task management
│   └── ...
└── data/          # Bundled configuration
    ├── config/    # Default configs
    ├── schemas/   # JSON schemas
    └── packs/     # Technology packs
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/edison

# Linting
ruff check src/ tests/
```

## License

MIT
