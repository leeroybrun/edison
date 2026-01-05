# Pal MCP Server Setup Guide

## Overview

Edison delegates work to specialized sub-agents using the [Pal MCP Server](https://github.com/BeehiveInnovations/pal-mcp-server). This document covers setup, configuration, and troubleshooting.

The Pal MCP Server enables Edison to:
- Delegate tasks to specialized AI agents
- Maintain conversation context across delegations
- Execute tasks in isolated environments
- Coordinate complex multi-agent workflows

## Prerequisites

- Python 3.10+
- uvx (comes with uv): `pip install uv`
- Edison installed: `pip install edison` or `pip install -e .` for development

## Installation Methods

### Method 1: Automatic (Recommended)

The easiest way to set up Pal integration is during project initialization:

```bash
edison init my-project
```

This automatically:
1. Creates `.edison/` directory structure
2. Checks for uvx/pal-mcp-server availability
3. Configures `.mcp.json` with Pal server entry
4. Verifies the setup

### Method 2: Manual Setup

If you need to set up Pal manually or add it to an existing project:

```bash
# 1. Verify uvx is installed
pip install uv

# 2. Run Edison pal setup
edison mcp setup

# 3. Configure your project
edison mcp configure .

# 4. Verify the setup
edison mcp setup --check
```

## Configuration

### .mcp.json Structure

The `edison mcp configure` command creates a `.mcp.json` file in your project root:

```json
{
  "mcpServers": {
    "edison-pal": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/BeehiveInnovations/pal-mcp-server.git",
        "pal-mcp-server"
      ],
      "env": {
        "PAL_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

### MCP for Child CLIs (Codex, Gemini, etc.)

Pal runs as the MCP server, but it often delegates execution to *child CLIs* (e.g. `codex`, `claude`, `gemini`) using generated configs under `.pal/conf/cli_clients/*.json`.

Some child CLIs (notably Codex CLI) do **not** read the project’s `.mcp.json`. Edison supports **per-role MCP injection** so only the specific agent/validator that needs an MCP server gets it.

**How it works**

- MCP servers are defined in `mcp.yaml` (core + packs + project overrides).
- A role declares required servers:
  - **Validators**: `validation.validators.<id>.mcp_servers: ["playwright", ...]`
  - **Agents**: agent prompt frontmatter `mcp_servers: ["playwright", ...]` (also supports `mcp: { servers: [...] }`)
- When Pal invokes a child CLI for a role, Edison injects CLI-specific args into that role’s `role_args`.
  - For Codex, this uses `-c mcp_servers.<name>.*=...` overrides so no global `~/.codex/config.toml` edits are required.

**Configuration**

- Enable/choose injection style per child CLI in `pal.yaml`:
  - `pal.cli_clients.clients.codex.mcp_override_style: codex_config`

### Configuration Options

#### Preview Configuration

See what will be written without making changes:

```bash
edison mcp configure --dry-run
```

#### Configure Specific Project

Configure a project in a different directory:

```bash
edison mcp configure /path/to/project
```

#### Override Config File Location

Write to a custom location:

```bash
edison mcp configure --config-file /custom/path/.mcp.json
```

## Starting the Server

### Foreground Mode

Start the server in the current terminal (useful for debugging):

```bash
edison mcp start-server
```

### Background Mode

Start the server in the background:

```bash
edison mcp start-server --background
```

## Verification

### Check Setup Status

Verify that Pal is properly configured:

```bash
edison mcp setup --check
```

This will check:
- ✅ uvx is installed and available
- ✅ pal-mcp-server can be accessed via uvx
- ✅ Configuration is valid

### Test Delegation

After setup, test that delegation works:

```bash
# Initialize a project
edison init test-project
cd test-project

# Create a test task
edison task new "Test delegation" --description "Verify Pal MCP integration"

# The task system should be able to delegate to Pal
```

## Troubleshooting

### uvx Not Found

**Problem**: Error message `uvx not found`

**Solution**:
```bash
# Install uv (includes uvx)
pip install uv

# Verify installation
uvx --version
```

### pal-mcp-server Installation Fails

**Problem**: `uvx` fails to install pal-mcp-server from GitHub

**Solution**:
1. Check your internet connection
2. Verify Git is installed: `git --version`
3. Try installing manually:
   ```bash
   uvx --from git+https://github.com/BeehiveInnovations/pal-mcp-server.git pal-mcp-server --version
   ```

### .mcp.json Not Found

**Problem**: Edison can't find `.mcp.json` configuration

**Solution**:
```bash
# Run configure again
edison mcp configure .

# Or specify the path explicitly
edison mcp configure --config-file ./.mcp.json
```

### Permission Denied

**Problem**: Permission errors when creating `.mcp.json`

**Solution**:
```bash
# Check directory permissions
ls -la .

# Ensure you have write access to the project directory
# Or use --config-file to write to a different location
edison mcp configure --config-file ~/.mcp.json
```

### Server Won't Start

**Problem**: `edison mcp start-server` fails

**Solutions**:
1. **Check uvx installation**:
   ```bash
   uvx --version
   ```

2. **Verify pal-mcp-server is accessible**:
   ```bash
   uvx --from git+https://github.com/BeehiveInnovations/pal-mcp-server.git pal-mcp-server --version
   ```

3. **Check for port conflicts**: Pal may use specific ports that are already in use

4. **Review error messages**: Look for specific error details in the output

### Configuration Override Issues

**Problem**: `.mcp.json` gets overwritten unexpectedly

**Solution**:
- The `edison mcp configure` command overwrites existing configuration by default
- Use `--dry-run` first to preview changes
- Back up your `.mcp.json` before running configure:
  ```bash
  cp .mcp.json .mcp.json.backup
  edison mcp configure --dry-run  # Preview first
  edison mcp configure            # Then apply
  ```

### Environment Variable Issues

**Problem**: `PAL_WORKING_DIR` not set correctly

**Solution**:
The `PAL_WORKING_DIR` environment variable in `.mcp.json` should point to your project root. If it's incorrect:

1. Edit `.mcp.json` manually:
   ```json
   {
     "mcpServers": {
       "edison-pal": {
         "env": {
           "PAL_WORKING_DIR": "/correct/path/to/project"
         }
       }
     }
   }
   ```

2. Or regenerate the configuration:
   ```bash
   cd /correct/path/to/project
   edison mcp configure .
   ```

## Advanced Usage

### Using Custom Pal MCP Server

If you're developing a custom version of pal-mcp-server:

1. Clone the repository:
   ```bash
   git clone https://github.com/BeehiveInnovations/pal-mcp-server.git
   cd pal-mcp-server
   ```

2. Install in development mode:
   ```bash
   pip install -e .
   ```

3. Update `.mcp.json` to use the local installation:
   ```json
   {
     "mcpServers": {
       "edison-pal": {
         "command": "pal-mcp-server",
         "args": [],
         "env": {
           "PAL_WORKING_DIR": "/path/to/project"
         }
       }
     }
   }
   ```

### Multiple Projects

You can configure Pal for multiple projects:

```bash
# Configure project A
cd /path/to/project-a
edison mcp configure .

# Configure project B
cd /path/to/project-b
edison mcp configure .
```

Each project gets its own `.mcp.json` with project-specific paths.

### Integration with CI/CD

For automated environments:

```yaml
# Example GitHub Actions workflow
steps:
  - name: Install uv
    run: pip install uv

  - name: Setup Edison Pal
    run: |
      edison mcp setup
      edison mcp configure .
      edison mcp setup --check
```

## Getting Help

### Command-Line Help

```bash
# General pal help
edison mcp --help

# Specific command help
edison mcp setup --help
edison mcp configure --help
edison mcp start-server --help
```

### Community Support

- **GitHub Issues**: https://github.com/BeehiveInnovations/pal-mcp-server/issues
- **Edison Issues**: Report Edison-specific issues to the Edison repository

### Debugging

Enable verbose output for debugging:

```bash
# Check setup with detailed output
edison mcp setup --check -v

# View configuration
edison mcp configure --dry-run
```

## Best Practices

1. **Always verify setup**: Run `edison mcp setup --check` after configuration
2. **Use relative paths**: Avoid hardcoded absolute paths in `.mcp.json`
3. **Version control**: Commit `.mcp.json` to your repository (it's project-specific)
4. **Document custom changes**: If you modify `.mcp.json` manually, document why
5. **Test after updates**: Re-run verification after updating Edison or Pal MCP Server

## Next Steps

After successful setup:

1. **Initialize a project**: `edison init my-project`
2. **Create tasks**: `edison task new "Description"`
3. **Test delegation**: Verify tasks can be delegated to sub-agents
4. **Explore Edison**: Check out the main Edison documentation

## Reference

### Related Commands

- `edison init` - Initialize a new Edison project (includes Pal setup)
- `edison mcp setup` - Setup pal-mcp-server
- `edison mcp configure` - Configure .mcp.json
- `edison mcp start-server` - Start the Pal MCP server

### Configuration Files

- `.mcp.json` - MCP server configuration (project-specific)
- `.edison/` - Edison project configuration directory

### External Links

- [Pal MCP Server Repository](https://github.com/BeehiveInnovations/pal-mcp-server)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [uvx Documentation](https://docs.astral.sh/uv/)


Note: Adapters are unified under `src/edison/core/adapters/` (components/ + platforms/pal/). See `docs/TEMPLATING.md` for the composition pipeline feeding adapter outputs.
