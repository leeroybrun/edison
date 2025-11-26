# Zen MCP Server Setup Guide

## Overview

Edison delegates work to specialized sub-agents using the [Zen MCP Server](https://github.com/BeehiveInnovations/zen-mcp-server). This document covers setup, configuration, and troubleshooting.

The Zen MCP Server enables Edison to:
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

The easiest way to set up Zen integration is during project initialization:

```bash
edison init my-project
```

This automatically:
1. Creates `.edison/` directory structure
2. Checks for uvx/zen-mcp-server availability
3. Configures `.mcp.json` with Zen server entry
4. Verifies the setup

### Method 2: Manual Setup

If you need to set up Zen manually or add it to an existing project:

```bash
# 1. Verify uvx is installed
pip install uv

# 2. Run Edison zen setup
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
    "edison-zen": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/BeehiveInnovations/zen-mcp-server.git",
        "zen-mcp-server"
      ],
      "env": {
        "ZEN_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

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

Verify that Zen is properly configured:

```bash
edison mcp setup --check
```

This will check:
- ✅ uvx is installed and available
- ✅ zen-mcp-server can be accessed via uvx
- ✅ Configuration is valid

### Test Delegation

After setup, test that delegation works:

```bash
# Initialize a project
edison init test-project
cd test-project

# Create a test task
edison task new "Test delegation" --description "Verify Zen MCP integration"

# The task system should be able to delegate to Zen
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

### zen-mcp-server Installation Fails

**Problem**: `uvx` fails to install zen-mcp-server from GitHub

**Solution**:
1. Check your internet connection
2. Verify Git is installed: `git --version`
3. Try installing manually:
   ```bash
   uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server --version
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

2. **Verify zen-mcp-server is accessible**:
   ```bash
   uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server --version
   ```

3. **Check for port conflicts**: Zen may use specific ports that are already in use

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

**Problem**: `ZEN_WORKING_DIR` not set correctly

**Solution**:
The `ZEN_WORKING_DIR` environment variable in `.mcp.json` should point to your project root. If it's incorrect:

1. Edit `.mcp.json` manually:
   ```json
   {
     "mcpServers": {
       "edison-zen": {
         "env": {
           "ZEN_WORKING_DIR": "/correct/path/to/project"
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

### Using Custom Zen MCP Server

If you're developing a custom version of zen-mcp-server:

1. Clone the repository:
   ```bash
   git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
   cd zen-mcp-server
   ```

2. Install in development mode:
   ```bash
   pip install -e .
   ```

3. Update `.mcp.json` to use the local installation:
   ```json
   {
     "mcpServers": {
       "edison-zen": {
         "command": "zen-mcp-server",
         "args": [],
         "env": {
           "ZEN_WORKING_DIR": "/path/to/project"
         }
       }
     }
   }
   ```

### Multiple Projects

You can configure Zen for multiple projects:

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

  - name: Setup Edison Zen
    run: |
      edison mcp setup
      edison mcp configure .
      edison mcp setup --check
```

## Getting Help

### Command-Line Help

```bash
# General zen help
edison mcp --help

# Specific command help
edison mcp setup --help
edison mcp configure --help
edison mcp start-server --help
```

### Community Support

- **GitHub Issues**: https://github.com/BeehiveInnovations/zen-mcp-server/issues
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
5. **Test after updates**: Re-run verification after updating Edison or Zen MCP Server

## Next Steps

After successful setup:

1. **Initialize a project**: `edison init my-project`
2. **Create tasks**: `edison task new "Description"`
3. **Test delegation**: Verify tasks can be delegated to sub-agents
4. **Explore Edison**: Check out the main Edison documentation

## Reference

### Related Commands

- `edison init` - Initialize a new Edison project (includes Zen setup)
- `edison mcp setup` - Setup zen-mcp-server
- `edison mcp configure` - Configure .mcp.json
- `edison mcp start-server` - Start the Zen MCP server

### Configuration Files

- `.mcp.json` - MCP server configuration (project-specific)
- `.edison/` - Edison project configuration directory

### External Links

- [Zen MCP Server Repository](https://github.com/BeehiveInnovations/zen-mcp-server)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [uvx Documentation](https://docs.astral.sh/uv/)
