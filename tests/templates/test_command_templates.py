from jinja2 import Template
from edison.data import get_data_path


def render_template(template_name: str, **context) -> str:
    template_path = get_data_path("templates", f"commands/{template_name}")
    template = Template(template_path.read_text())
    return template.render(**context)


def sample_context(overrides=None):
    base = {
        "name": "edison-session-next",
        "short_desc": "Show next session steps",
        "full_desc": "Shows recommended next actions...",
        "cli": "edison session next",
        "args": [
            {"name": "task", "description": "Task identifier", "required": True},
            {"name": "limit", "description": "Max items to show", "required": False},
        ],
        "when_to_use": "After completing a task",
        "related_commands": ["edison-session-status"],
    }
    return {**base, **(overrides or {})}


def test_claude_template_renders():
    result = render_template("claude-command.md.template", **sample_context())

    assert "# edison-session-next" in result
    assert "!edison session next" in result
    assert "allowed-tools: [bash]" in result
    assert "**task** (required): Task identifier" in result
    assert "## Related Commands" in result


def test_cursor_template_renders():
    result = render_template("cursor-command.md.template", **sample_context())

    assert "# edison-session-next" in result
    assert "```bash\nedison session next\n```" in result
    assert "- task (required): Task identifier" in result
    assert "## Related" in result


def test_codex_template_renders():
    result = render_template("codex-prompt.md.template", **sample_context())

    assert "description: Show next session steps" in result
    assert "argument-hint: task limit" in result
    assert "# edison-session-next" in result
    assert "`task` (required): Task identifier" in result
    assert "global Edison command" in result


def test_template_with_no_args():
    result = render_template(
        "codex-prompt.md.template",
        **sample_context({"args": []}),
    )

    assert "argument-hint" not in result
    assert "## Arguments" not in result


def test_template_with_no_related():
    claude = render_template(
        "claude-command.md.template",
        **sample_context({"related_commands": []}),
    )
    cursor = render_template(
        "cursor-command.md.template",
        **sample_context({"related_commands": []}),
    )

    assert "## Related Commands" not in claude
    assert "## Related" not in cursor


def test_template_escaping():
    weird_desc = "Handles & < > and braces like {{ and }} without escaping."
    result = render_template(
        "cursor-command.md.template",
        **sample_context({
            "full_desc": weird_desc,
            "cli": 'edison session next --flag "quoted"',
            "args": [],
            "related_commands": [],
        }),
    )

    assert weird_desc in result
    assert 'edison session next --flag "quoted"' in result
