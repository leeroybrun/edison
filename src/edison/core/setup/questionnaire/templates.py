"""Template rendering utilities for setup questionnaire."""
from __future__ import annotations

from textwrap import dedent
from typing import Any, Dict, TYPE_CHECKING

from edison.core.utils.paths import DEFAULT_PROJECT_CONFIG_PRIMARY
from edison.core.utils.text.templates import (
    render_template_dict,
    render_template_text,
)

if TYPE_CHECKING:
    from .base import SetupQuestionnaire


def render_readme_template(
    questionnaire: "SetupQuestionnaire",
    context: Dict[str, Any]
) -> str:
    """Render the README template using provided context."""
    template_path = questionnaire.edison_core / "templates" / "setup" / "project-readme.md.template"

    if template_path.exists():
        try:
            text = template_path.read_text(encoding="utf-8")
            return render_template_text(text, context)
        except Exception:
            pass

    tech_stack = context.get("tech_stack") or []
    tech_label = ", ".join(tech_stack) if tech_stack else ""
    config_dir = DEFAULT_PROJECT_CONFIG_PRIMARY
    management_dir = context.get("project_management_dir", ".project")

    return (
        dedent(
            f"""
            # Edison Framework Setup for {context.get('project_name', '')}

            Welcome to your newly initialized Edison workspace. The `edison setup` wizard
            generated baseline configuration under `{config_dir}/config/` using a modular
            structure where each domain has its own file.

            ## Generated Structure

            - `{config_dir}/config/defaults.yml` — paths and project metadata (type: {context.get('project_type', '')}, db: {context.get('database', '')})
            - `{config_dir}/config/packs.yml` — enabled packs: {tech_label}
            - `{config_dir}/config/validation.yaml` — validation configuration
            - `{config_dir}/config/delegation.yml` — agents and delegation settings
            - `{config_dir}/config/ci.yml` — CI/CD commands (lint, test, build, type-check)
            - `{config_dir}/config/tdd.yml` — TDD enforcement rules
            - `{config_dir}/config/worktrees.yml` — git worktree settings
            - `{config_dir}/config/workflow.yml` — task and session lifecycle states
            - `{config_dir}/guidelines/` — team guidelines and conventions
            - `{management_dir}/` — project management artifacts (tasks/sessions)

            ## Configuration Pattern

            Configuration follows this precedence (lowest → highest):
            1. Core defaults: bundled edison.data package
            2. Project overrides: `{config_dir}/config/*.yml` (this directory)
            3. Environment variables: `EDISON_*`

            Each domain has its own file for better separation of concerns. To modify settings:
            - Edit the relevant `config/*.yml` file directly
            - Use `edison configure` for interactive menu-driven changes
            - Override via environment: `EDISON_tdd__enforcement=strict`

            ## Next Steps

            1. Review `{config_dir}/config/*.yml` files and adjust as needed
            2. Add project-specific guidelines to `{config_dir}/guidelines/`
            3. Run `edison compose all` to generate IDE integrations (commands/hooks/settings)
            4. Keep `{config_dir}/` committed so teammates share the same automation surface

            ## Support

            - `edison utils doctor` — verify your environment
            - `edison configure` — interactive configuration menu
            - `edison config edison-config` — inspect merged configuration
            - Run `edison --help` for CLI help
            """
        ).strip()
        + "\n"
    )
