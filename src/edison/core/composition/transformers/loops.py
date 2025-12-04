"""Loop transformer for template composition.

Handles Handlebars-style loops:
- {{#each collection}}...{{/each}} - Iterate over array from context
- {{#each this.property}}...{{/each}} - Nested loops over item properties
- {{this}} - Current item in loop
- {{this.property}} - Access item property
- {{@index}} - Current index (0-based)
- {{@last}} - True if last item
- {{#if this.prop}}...{{else}}...{{/if}} - Conditionals inside loops
- {{#unless @last}}...{{/unless}} - Unless blocks
"""
from __future__ import annotations

import re
from typing import Any, List, Optional

from .base import ContentTransformer, TransformContext


class LoopExpander(ContentTransformer):
    """Expand {{#each collection}}...{{/each}} loops.

    Iterates over arrays from context.context_vars and expands the template
    for each item. Supports nested properties, loop variables, and inline conditionals.

    Example:
        Context: {"validators": [{"name": "v1", "blocking": true}, {"name": "v2"}]}
        Template: {{#each validators}}| {{this.name}} | {{#if this.blocking}}✅{{else}}❌{{/if}} |{{/each}}
        Output:
        | v1 | ✅ |
        | v2 | ❌ |
    """

    # Pattern for each blocks: {{#each collection}}content{{/each}}
    # Use non-greedy to handle nested loops
    EACH_PATTERN = re.compile(
        r"\{\{#each\s+([\w.]+)\s*\}\}(.*?)\{\{/each\}\}",
        re.DOTALL,
    )

    # Pattern for current item: {{this}} or {{this.property}}
    THIS_PATTERN = re.compile(r"\{\{this(?:\.([\w.]+))?\}\}")

    # Pattern for index: {{@index}}
    INDEX_PATTERN = re.compile(r"\{\{@index\}\}")

    # Pattern for inline if inside loops: {{#if this.prop}}...{{else}}...{{/if}}
    IF_ELSE_PATTERN = re.compile(
        r"\{\{#if\s+this\.([\w.]+)\s*\}\}(.*?)\{\{else\}\}(.*?)\{\{/if\}\}",
        re.DOTALL,
    )

    # Pattern for inline if without else: {{#if this.prop}}...{{/if}}
    IF_PATTERN = re.compile(
        r"\{\{#if\s+this\.([\w.]+)\s*\}\}(.*?)\{\{/if\}\}",
        re.DOTALL,
    )

    # Pattern for unless: {{#unless @last}}...{{/unless}}
    UNLESS_LAST_PATTERN = re.compile(
        r"\{\{#unless\s+@last\s*\}\}(.*?)\{\{/unless\}\}",
        re.DOTALL,
    )

    def transform(self, content: str, context: TransformContext) -> str:
        """Expand all each loops in content.

        Args:
            content: Content with {{#each}} blocks
            context: Transform context with data in context_vars

        Returns:
            Content with loops expanded
        """
        # Process loops iteratively to handle nesting correctly
        # We need to find outermost loops first and process them
        return self._process_loops(content, context)

    def _process_loops(self, content: str, context: TransformContext) -> str:
        """Process loops with proper handling of nested blocks.

        Finds the outermost {{#each}} blocks first and expands them,
        then recursively processes any nested loops within the template.
        """
        result = content
        while True:
            # Find the first {{#each collection}} that has a matching {{/each}}
            match = self._find_outermost_loop(result)
            if not match:
                break

            start, end, collection_path, template = match
            expanded = self._expand_loop(collection_path, template, context)
            result = result[:start] + expanded + result[end:]

        return result

    def _find_outermost_loop(self, content: str) -> Optional[tuple]:
        """Find the outermost {{#each}}...{{/each}} block.

        Returns tuple of (start, end, collection_path, template) or None.
        """
        # Find first {{#each ...}}
        each_start = re.search(r"\{\{#each\s+([\w.]+)\s*\}\}", content)
        if not each_start:
            return None

        start_pos = each_start.start()
        collection_path = each_start.group(1)
        search_pos = each_start.end()

        # Count nested {{#each}} and {{/each}} to find matching close
        depth = 1
        pos = search_pos
        while depth > 0 and pos < len(content):
            next_open = content.find("{{#each", pos)
            next_close = content.find("{{/each}}", pos)

            if next_close == -1:
                # No matching close found
                return None

            if next_open != -1 and next_open < next_close:
                # Found another opening before closing
                depth += 1
                pos = next_open + 7  # len("{{#each")
            else:
                # Found closing
                depth -= 1
                if depth == 0:
                    # This is our matching close
                    end_pos = next_close + 9  # len("{{/each}}")
                    template = content[search_pos:next_close]
                    return (start_pos, end_pos, collection_path, template)
                pos = next_close + 9

        return None

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
        total = len(collection)
        for index, item in enumerate(collection):
            is_last = index == total - 1
            expanded = self._expand_item(template, item, index, is_last)
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

    def _expand_item(
        self,
        template: str,
        item: Any,
        index: int,
        is_last: bool = False,
    ) -> str:
        """Expand template for a single item.

        Args:
            template: Template with {{this}}, {{@index}}, etc.
            item: Current item value
            index: Current index
            is_last: Whether this is the last item in the collection

        Returns:
            Expanded template
        """
        result = template

        # Replace {{@index}}
        result = self.INDEX_PATTERN.sub(str(index), result)

        # Process {{#if this.prop}}...{{else}}...{{/if}} blocks
        def replace_if_else(match: re.Match[str]) -> str:
            prop = match.group(1)
            true_content = match.group(2)
            false_content = match.group(3)
            value = self._get_nested_prop(item, prop)
            return true_content.strip() if value else false_content.strip()

        result = self.IF_ELSE_PATTERN.sub(replace_if_else, result)

        # Process {{#if this.prop}}...{{/if}} blocks (without else)
        def replace_if(match: re.Match[str]) -> str:
            prop = match.group(1)
            content = match.group(2)
            value = self._get_nested_prop(item, prop)
            return content.strip() if value else ""

        result = self.IF_PATTERN.sub(replace_if, result)

        # Process nested {{#each this.property}}...{{/each}} loops BEFORE {{#unless @last}}
        # This ensures nested loops handle their own @last values correctly
        result = self._expand_nested_loops(result, item)

        # Process {{#unless @last}}...{{/unless}} blocks for the CURRENT loop level
        def replace_unless_last(match: re.Match[str]) -> str:
            content = match.group(1)
            return "" if is_last else content

        result = self.UNLESS_LAST_PATTERN.sub(replace_unless_last, result)

        # Replace {{this}} and {{this.property}}
        def replace_this(match: re.Match[str]) -> str:
            prop = match.group(1)
            if prop is None:
                # {{this}} - return whole item
                return str(item) if item is not None else ""
            # {{this.property}} - return item property
            return str(self._get_nested_prop(item, prop) or "")

        result = self.THIS_PATTERN.sub(replace_this, result)

        return result

    def _expand_nested_loops(self, content: str, item: Any) -> str:
        """Expand nested {{#each this.property}} loops.

        Args:
            content: Content that may contain nested loops
            item: Current item from parent loop

        Returns:
            Content with nested loops expanded
        """
        result = content
        while True:
            # Find nested loop pattern: {{#each this.property}}
            match = self._find_nested_loop(result)
            if not match:
                break

            start, end, prop_path, inner_template = match

            # Get nested collection from current item
            nested_collection = self._get_nested_prop(item, prop_path)

            if not nested_collection or not isinstance(nested_collection, list):
                # Remove the loop block if collection is empty/invalid
                result = result[:start] + result[end:]
                continue

            # Expand nested loop with its own is_last tracking
            nested_results: List[str] = []
            total = len(nested_collection)
            for nested_idx, nested_item in enumerate(nested_collection):
                nested_is_last = nested_idx == total - 1
                expanded = self._expand_item(
                    inner_template, nested_item, nested_idx, nested_is_last
                )
                nested_results.append(expanded)

            expanded_content = "".join(nested_results)
            result = result[:start] + expanded_content + result[end:]

        return result

    def _find_nested_loop(self, content: str) -> Optional[tuple]:
        """Find nested {{#each this.property}}...{{/each}} block.

        Returns tuple of (start, end, property_path, template) or None.
        """
        # Find first {{#each this.property}}
        each_start = re.search(r"\{\{#each\s+this\.([\w.]+)\s*\}\}", content)
        if not each_start:
            return None

        start_pos = each_start.start()
        prop_path = each_start.group(1)
        search_pos = each_start.end()

        # Count nested blocks to find matching close
        depth = 1
        pos = search_pos
        while depth > 0 and pos < len(content):
            next_open = content.find("{{#each", pos)
            next_close = content.find("{{/each}}", pos)

            if next_close == -1:
                return None

            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 7
            else:
                depth -= 1
                if depth == 0:
                    end_pos = next_close + 9
                    template = content[search_pos:next_close]
                    return (start_pos, end_pos, prop_path, template)
                pos = next_close + 9

        return None

    def _get_nested_prop(self, item: Any, prop_path: str) -> Any:
        """Get nested property from item using dot notation.

        Args:
            item: Object to get property from
            prop_path: Dot-separated property path (e.g., "foo.bar")

        Returns:
            Property value or None
        """
        if not isinstance(item, dict):
            return None

        parts = prop_path.split(".")
        current = item
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current
