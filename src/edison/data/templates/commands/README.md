# Command Templates

Jinja2 templates for generating IDE slash-command help across Claude Code, Cursor, and Codex. Each template expects the same context keys and renders platform-specific markdown.

## Context variables
- `name`: display id (e.g., `edison-session-next`)
- `short_desc`: brief summary (<80 chars)
- `full_desc`: detailed description
- `cli`: CLI invocation (e.g., `edison session next`)
- `args`: list of `{name, description, required}` dicts
- `when_to_use`: guidance text
- `related_commands`: list of related command ids

## Templates
- `claude-command.md.template`: adds `allowed-tools: [bash]` frontmatter and prefixes the command with `!` for execution.
- `cursor-command.md.template`: lightweight markdown without frontmatter.
- `codex-prompt.md.template`: YAML frontmatter with `description` and optional `argument-hint`; includes a global-use notice.

## Quick render example
```python
from pathlib import Path
from jinja2 import Template

context = {
    "name": "edison-session-next",
    "short_desc": "Show next session steps",
    "full_desc": "Shows recommended next actions...",
    "cli": "edison session next",
    "args": [],
    "when_to_use": "After completing a task",
    "related_commands": ["edison-session-status"],
}

text = Template(Path(".edison/core/templates/commands/claude-command.md.template").read_text()).render(**context)
```
