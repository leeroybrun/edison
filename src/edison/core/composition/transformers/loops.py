"""Loop transformer for template composition.

Handles Handlebars-style loops:
- {{#each collection}}...{{/each}} - Iterate over array from context
- {{this}} - Current item in loop
- {{@index}} - Current index (0-based)
"""
from __future__ import annotations

import re
from typing import Any, List

from .base import ContentTransformer, TransformContext


class LoopExpander(ContentTransformer):
    """Expand {{#each collection}}...{{/each}} loops.

    Iterates over arrays from context.context_vars and expands the template
    for each item. Supports nested properties and loop variables.

    Example:
        Context: {"mandatoryReads": ["file1.md", "file2.md"]}
        Template: {{#each mandatoryReads}}- {{this}}{{/each}}
        Output:
        - file1.md
        - file2.md
    """

    # Pattern for each blocks: {{#each collection}}content{{/each}}
    EACH_PATTERN = re.compile(
        r"\{\{#each\s+([\w.]+)\s*\}\}(.*?)\{\{/each\}\}",
        re.DOTALL,
    )

    # Pattern for current item: {{this}} or {{this.property}}
    THIS_PATTERN = re.compile(r"\{\{this(?:\.(\w+))?\}\}")

    # Pattern for index: {{@index}}
    INDEX_PATTERN = re.compile(r"\{\{@index\}\}")

    def transform(self, content: str, context: TransformContext) -> str:
        """Expand all each loops in content.

        Args:
            content: Content with {{#each}} blocks
            context: Transform context with data in context_vars

        Returns:
            Content with loops expanded
        """

        def replacer(match: re.Match[str]) -> str:
            collection_path = match.group(1)
            template = match.group(2)
            return self._expand_loop(collection_path, template, context)

        return self.EACH_PATTERN.sub(replacer, content)

    def _expand_loop(
        self,
        collection_path: str,
        template: str,
        context: TransformContext,
    ) -> str:
        """Expand a single loop.

        Args:
            collection_path: Dot-separated path to collection in context
            template: Template to repeat for each item
            context: Transform context

        Returns:
            Expanded content
        """
        # Get collection from context
        collection = self._get_collection(collection_path, context)

        if not collection:
            return ""

        if not isinstance(collection, list):
            return f"<!-- ERROR: {collection_path} is not a list -->"

        # Expand template for each item
        results: List[str] = []
        for index, item in enumerate(collection):
            expanded = self._expand_item(template, item, index)
            results.append(expanded)

        return "".join(results)

    def _get_collection(
        self,
        path: str,
        context: TransformContext,
    ) -> Any:
        """Get collection from context by path.

        Args:
            path: Dot-separated path
            context: Transform context

        Returns:
            Collection value or None
        """
        # First try context_vars
        if path in context.context_vars:
            return context.context_vars[path]

        # Then try nested access in context_vars
        parts = path.split(".")
        current: Any = context.context_vars
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    def _expand_item(self, template: str, item: Any, index: int) -> str:
        """Expand template for a single item.

        Args:
            template: Template with {{this}}, {{@index}}, etc.
            item: Current item value
            index: Current index

        Returns:
            Expanded template
        """
        result = template

        # Replace {{@index}}
        result = self.INDEX_PATTERN.sub(str(index), result)

        # Replace {{this}} and {{this.property}}
        def replace_this(match: re.Match[str]) -> str:
            prop = match.group(1)
            if prop is None:
                # {{this}} - return whole item
                return str(item) if item is not None else ""
            # {{this.property}} - return item property
            if isinstance(item, dict):
                return str(item.get(prop, ""))
            return ""

        result = self.THIS_PATTERN.sub(replace_this, result)

        return result
