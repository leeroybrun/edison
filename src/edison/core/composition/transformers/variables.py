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
    """Substitute {{config.path.to.value}} variables from configuration.

    Accesses nested config values using dot notation.

    Example:
        Config: {"project": {"name": "edison"}}
        Template: Project: {{config.project.name}}
        Output: Project: edison
    """

    # Pattern for config variables: {{config.path.to.value}}
    CONFIG_PATTERN = re.compile(r"\{\{config\.([a-zA-Z_][\w.]*)\}\}")

    def transform(self, content: str, context: TransformContext) -> str:
        """Substitute all config variables.

        Args:
            content: Content with {{config.}} variables
            context: Transform context with config dict

        Returns:
            Content with config variables substituted
        """

        def replacer(match: re.Match[str]) -> str:
            path = match.group(1)
            value = context.get_config(path)

            if value is not None:
                context.record_variable(f"config.{path}", resolved=True)
                return str(value)
            else:
                context.record_variable(f"config.{path}", resolved=False)
                return match.group(0)  # Keep original if not found

        return self.CONFIG_PATTERN.sub(replacer, content)


class ContextVariableTransformer(ContentTransformer):
    """Substitute context variables like {{source_layers}}, {{timestamp}}.

    Context variables are set at runtime and provide composition metadata.

    Common variables:
    - {{source_layers}} - "core + pack1 + pack2 + project"
    - {{timestamp}} - ISO timestamp of composition
    - {{version}} - Edison version
    """

    # Pattern for context variables (simple names)
    CONTEXT_PATTERN = re.compile(r"\{\{(source_layers|timestamp|version|template)\}\}")

    def transform(self, content: str, context: TransformContext) -> str:
        """Substitute all context variables.

        Args:
            content: Content with context variables
            context: Transform context with context_vars

        Returns:
            Content with context variables substituted
        """

        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            value = context.context_vars.get(var_name)

            if value is not None:
                context.record_variable(var_name, resolved=True)
                return str(value)
            else:
                context.record_variable(var_name, resolved=False)
                return match.group(0)  # Keep original if not found

        return self.CONTEXT_PATTERN.sub(replacer, content)


class PathVariableTransformer(ContentTransformer):
    """Substitute path variables like {{PROJECT_EDISON_DIR}}.

    Path variables are resolved relative to project structure.

    Variables:
    - {{PROJECT_EDISON_DIR}} - Path to .edison directory
    """

    # Pattern for path variables
    PATH_PATTERN = re.compile(r"\{\{PROJECT_EDISON_DIR\}\}")

    def transform(self, content: str, context: TransformContext) -> str:
        """Substitute all path variables.

        Args:
            content: Content with path variables
            context: Transform context with project_root

        Returns:
            Content with path variables substituted
        """
        if context.project_root is None:
            return content

        edison_dir = context.project_root / ".edison"

        def replacer(match: re.Match[str]) -> str:
            context.record_variable("PROJECT_EDISON_DIR", resolved=True)
            return str(edison_dir)

        return self.PATH_PATTERN.sub(replacer, content)


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
