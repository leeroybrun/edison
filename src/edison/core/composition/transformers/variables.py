"""Variable transformers for template composition.

Handles three types of variable substitution:
- {{config.path.to.value}} - Config variables from YAML
- {{source_layers}}, {{timestamp}} - Context variables
- {{PROJECT_EDISON_DIR}} - Path variables
"""
from __future__ import annotations

import re
from typing import Any

from .base import ContentTransformer, TransformContext


class ConfigVariableTransformer(ContentTransformer):
    """Substitute {{config.path.to.value}} and {{project.path}} variables from configuration.

    Accesses nested config values using dot notation.
    {{project.xxx}} is treated as an alias for {{config.project.xxx}}

    Examples:
        Config: {"project": {"name": "edison", "palRoles": {"api-builder": "agent-api"}}}
        Template: Project: {{config.project.name}}
        Output: Project: edison
        Template: palRole: "{{project.palRoles.api-builder}}"
        Output: palRole: "agent-api"
    """

    # Pattern for config variables: {{config.path.to.value}} or {{project.path}}
    # Allow alphanumeric, hyphens, underscores, and dots in paths
    CONFIG_PATTERN = re.compile(r"\{\{config\.([a-zA-Z_][\w.-]*)\}\}")
    PROJECT_PATTERN = re.compile(r"\{\{project\.([a-zA-Z_][\w.-]*)\}\}")

    def transform(self, content: str, context: TransformContext) -> str:
        """Substitute all config and project variables.

        Args:
            content: Content with {{config.}} or {{project.}} variables
            context: Transform context with config dict

        Returns:
            Content with config variables substituted
        """

        def config_replacer(match: re.Match[str]) -> str:
            path = match.group(1)
            value = context.get_config(path)

            if value is not None:
                context.record_variable(f"config.{path}", resolved=True)
                return str(value)
            else:
                context.record_variable(f"config.{path}", resolved=False)
                return match.group(0)  # Keep original if not found

        def project_replacer(match: re.Match[str]) -> str:
            # {{project.xxx}} is an alias for {{config.project.xxx}}
            path = match.group(1)
            full_path = f"project.{path}"
            value = context.get_config(full_path)

            if value is not None:
                context.record_variable(f"project.{path}", resolved=True)
                return str(value)
            else:
                context.record_variable(f"project.{path}", resolved=False)
                return match.group(0)  # Keep original if not found

        # Process both patterns
        content = self.CONFIG_PATTERN.sub(config_replacer, content)
        content = self.PROJECT_PATTERN.sub(project_replacer, content)
        return content


class ContextVariableTransformer(ContentTransformer):
    """Substitute context variables like {{source_layers}}, {{timestamp}}, and custom vars.

    Context variables are set at runtime and provide composition metadata.
    Any variable in context.context_vars can be substituted using {{var_name}} syntax.

    Built-in variables (always available):
    - {{source_layers}} - "core + pack1 + pack2 + project"
    - {{timestamp}} - ISO timestamp of composition
    - {{PROJECT_EDISON_DIR}} - Path to Edison config directory (".edison")

    Custom variables (set via CompositionContext.context_vars):
    - {{version}} - Edison version
    - {{template}} - Template path
    - {{generated_date}} - Generation timestamp
    - Any other string value in context_vars
    """

    # Pattern for context variables: any {{word}} that's not a special directive
    # Excludes: config., project., include, #each, /each, @, etc.
    CONTEXT_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")

    def transform(self, content: str, context: TransformContext) -> str:
        """Substitute all context variables from context_vars.

        Only substitutes variables that exist in context.context_vars and have
        string values (not lists/dicts which are for {{#each}} loops).

        Args:
            content: Content with context variables
            context: Transform context with context_vars

        Returns:
            Content with context variables substituted
        """

        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            value = context.context_vars.get(var_name)

            # Only substitute if value is a string (not list/dict for loops)
            if value is not None and isinstance(value, (str, int, float, bool)):
                context.record_variable(var_name, resolved=True)
                return str(value)
            elif value is not None:
                # Value exists but is a collection - leave for {{#each}} processing
                return match.group(0)
            else:
                # Variable not found in context_vars - leave unchanged
                # Don't record as missing since it might be an intentional placeholder
                return match.group(0)

        return self.CONTEXT_PATTERN.sub(replacer, content)


class PathVariableTransformer(ContentTransformer):
    """Substitute path variables like {{PROJECT_EDISON_DIR}}.

    NOTE: {{PROJECT_EDISON_DIR}} is intentionally NOT resolved here.
    It must be resolved later via resolve_project_dir_placeholders()
    after the target output path is known, so it can use relative paths.

    Path variables are resolved relative to project structure.

    Variables:
    - {{PROJECT_EDISON_DIR}} - Path to .edison directory (NOT resolved here)
    """

    # Pattern for path variables (currently empty - no patterns to resolve)
    PATH_PATTERN = re.compile(r"(?!)")  # Never matches

    def transform(self, content: str, context: TransformContext) -> str:
        """Substitute all path variables.

        NOTE: Currently this transformer does nothing, as {{PROJECT_EDISON_DIR}}
        must be resolved later by resolve_project_dir_placeholders().

        Args:
            content: Content with path variables
            context: Transform context with project_root

        Returns:
            Content unchanged (path variables resolved elsewhere)
        """
        # {{PROJECT_EDISON_DIR}} must be resolved AFTER we know the target path,
        # so we can compute relative paths. This happens in resolve_project_dir_placeholders().
        return content


class VariableTransformer(ContentTransformer):
    """Combined transformer for all variable types.

    Processes in order:
    1. Config variables ({{config.}})
    2. Context variables ({{source_layers}}, etc.)
    3. Path variables ({{PROJECT_EDISON_DIR}})
    """

    def __init__(self) -> None:
        """Initialize with sub-transformers."""
        self.config_transformer = ConfigVariableTransformer()
        self.context_transformer = ContextVariableTransformer()
        self.path_transformer = PathVariableTransformer()

    def transform(self, content: str, context: TransformContext) -> str:
        """Substitute all variable types.

        Args:
            content: Content with variables
            context: Transform context

        Returns:
            Content with variables substituted
        """
        content = self.config_transformer.transform(content, context)
        content = self.context_transformer.transform(content, context)
        content = self.path_transformer.transform(content, context)
        return content
