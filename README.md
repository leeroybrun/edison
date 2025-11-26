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

## Zen MCP Integration

Edison uses the [Zen MCP Server](https://github.com/BeehiveInnovations/MCP servers) for sub-agent delegation.

### Quick Setup

```bash
# During project initialization (automatic)
edison init my-project

# Or manually
edison mcp setup
edison mcp configure
```

### Manual Setup

If automatic setup fails:

1. **Install uvx** (provides MCP servers):
   ```bash
   pip install uv
   ```

2. **Configure your project**:
   ```bash
   edison mcp configure /path/to/project
   ```

3. **Verify setup**:
   ```bash
   edison mcp setup --check
   ```

### MCP Server Configuration

All MCP server commands are defined in `config/mcp.yml` (core) plus any pack/project overrides. The `.mcp.json` written by `edison mcp configure` uses those YAML values directly—no hardcoded fallbacks.

### Configuration Options

The `edison mcp configure` command creates a `.mcp.json` file in your project with the following options:

```bash
# Preview configuration without writing
edison mcp configure --dry-run

# Configure specific project
edison mcp configure /path/to/project
```

### Troubleshooting

For detailed setup instructions, troubleshooting, and advanced configuration, see [docs/ZEN_SETUP.md](docs/ZEN_SETUP.md).

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
