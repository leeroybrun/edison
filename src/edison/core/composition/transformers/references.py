"""Reference transformer for template composition.

Handles {{reference-section:path#name|purpose}} directives.
References output a pointer to a section without embedding its content.
"""
from __future__ import annotations

import re

from .base import ContentTransformer, TransformContext


class ReferenceRenderer(ContentTransformer):
    """Render {{reference-section:path#name|purpose}} as pointers.

    Unlike include-section which embeds content, reference-section outputs
    a formatted pointer for documentation purposes.

    Example:
        {{reference-section:guidelines/VALIDATION.md#tdd|TDD requirements}}
        Output:
        - guidelines/VALIDATION.md#tdd: TDD requirements
    """

    # Pattern: {{reference-section:path#name|purpose}}
    REFERENCE_PATTERN = re.compile(
        r"\{\{reference-section:([^#]+)#([^|]+)\|([^}]+)\}\}"
    )

    def __init__(self, format_template: str = "- {path}#{section}: {purpose}") -> None:
        """Initialize with output format template.

        Args:
            format_template: Template for reference output.
                             Available placeholders: {path}, {section}, {purpose}
        """
        self.format_template = format_template

    def transform(self, content: str, context: TransformContext) -> str:
        """Render all reference directives.

        Args:
            content: Content with {{reference-section:}} directives
            context: Transform context (unused but required by interface)

        Returns:
            Content with references rendered
        """

        def replacer(match: re.Match[str]) -> str:
            path = match.group(1).strip()
            section = match.group(2).strip()
            purpose = match.group(3).strip()

            return self.format_template.format(
                path=path,
                section=section,
                purpose=purpose,
            )

        return self.REFERENCE_PATTERN.sub(replacer, content)
