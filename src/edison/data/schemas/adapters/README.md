# Adapter Schemas

Schemas for IDE-specific adapters and agent configurations.

## Schemas

| Schema | Purpose | Validated In |
|--------|---------|--------------|
| `claude-agent.schema.json` | Claude agent definition structure | Tests |
| `claude-agent-config.schema.json` | Claude agent configuration | Tests |

## Usage

Adapter schemas define the interface between Edison and specific platform adapters:

- **claude-agent**: Full agent definition with name, description, model, and sections (role, tools, guidelines, workflows)
- **claude-agent-config**: Configuration options for Claude agent behavior

## Related Code

- `edison.core.adapters` - unified adapter stack (components + platforms, PlatformAdapter base)
- `.edison/_generated/agents/` - Generated agent definitions
- Client-specific implementations (Cursor, Claude Code, etc.)
