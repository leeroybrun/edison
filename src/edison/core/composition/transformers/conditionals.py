"""Condition evaluation for Edison template composition.

Provides function-based condition expressions for template conditionals.

Supported condition functions:
- has-pack(name): Check if pack is active
- config(path): Check config value truthy
- config-eq(path, value): Config equals value
- env(name): Environment variable set
- file-exists(path): File exists in project
- not(expr): Negate condition
- and(expr1, expr2): Both conditions true
- or(expr1, expr2): Either condition true

Example usage:
    {{if:has-pack(python)}}
    Python-specific content
    {{/if}}

    {{include-if:and(has-pack(vitest), config(strict)):guidelines/STRICT_TESTING.md}}
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from edison.core.config import ConfigManager


@dataclass
class CompositionContext:
    """Context for condition evaluation during composition.

    Provides access to:
    - Active packs list
    - Configuration values
    - Project root for file existence checks
    """

    active_packs: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    project_root: Optional[Path] = None

    def get_config(self, path: str) -> Any:
        """Get config value by dot-separated path.

        Args:
            path: Dot-separated path like 'features.auth.enabled'

        Returns:
            The config value or None if not found
        """
        parts = path.split(".")
        current: Any = self.config
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current


class ConditionEvaluator:
    """Evaluate condition expressions for template conditionals.

    Supports function-based conditions with nested expressions.

    Example expressions:
        has-pack(python)
        config(features.auth)
        and(has-pack(python), not(has-pack(legacy)))
    """

    # Pattern to match function calls: func-name(args)
    # Supports hyphenated function names like has-pack, config-eq
    FUNCTION_PATTERN = re.compile(r"^(\w+(?:-\w+)*)\((.*)?\)$")

    def __init__(self, context: CompositionContext) -> None:
        """Initialize evaluator with composition context.

        Args:
            context: CompositionContext with packs, config, and project_root
        """
        self.context = context
        self.functions: Dict[str, Callable[..., bool]] = {
            "has-pack": self._has_pack,
            "config": self._config_truthy,
            "config-eq": self._config_eq,
            "env": self._env,
            "file-exists": self._file_exists,
            "not": self._not,
            "and": self._and,
            "or": self._or,
        }

    def evaluate(self, expr: str) -> bool:
        """Evaluate a condition expression.

        Args:
            expr: Condition expression like 'has-pack(python)'

        Returns:
            Boolean result of the condition

        Raises:
            ValueError: If expression is malformed or uses unknown function
        """
        expr = expr.strip()
        if not expr:
            raise ValueError("Empty condition expression")

        match = self.FUNCTION_PATTERN.match(expr)
        if not match:
            raise ValueError(f"Invalid condition expression: {expr}")

        func_name = match.group(1)
        args_str = match.group(2) or ""

        if func_name not in self.functions:
            available = sorted(self.functions.keys())
            raise ValueError(
                f"Unknown condition function: {func_name}. "
                f"Available functions: {available}"
            )

        args = self._parse_args(args_str)
        return self.functions[func_name](*args)

    def _parse_args(self, args_str: str) -> List[str]:
        """Parse comma-separated arguments, handling nested function calls.

        Args:
            args_str: Comma-separated arguments string

        Returns:
            List of argument strings
        """
        if not args_str.strip():
            return []

        args: List[str] = []
        current = ""
        depth = 0

        for char in args_str:
            if char == "(":
                depth += 1
                current += char
            elif char == ")":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                args.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            args.append(current.strip())

        return args

    def _has_pack(self, pack_name: str) -> bool:
        """Check if pack is active.

        Args:
            pack_name: Name of the pack to check

        Returns:
            True if pack is in active packs list
        """
        return pack_name in self.context.active_packs

    def _config_truthy(self, path: str) -> bool:
        """Check if config value exists and is truthy.

        Args:
            path: Dot-separated config path

        Returns:
            True if config value exists and is truthy
        """
        value = self.context.get_config(path)
        return bool(value)

    def _config_eq(self, path: str, expected: str) -> bool:
        """Check if config value equals expected value.

        Args:
            path: Dot-separated config path
            expected: Expected value (compared as string)

        Returns:
            True if config value equals expected
        """
        value = self.context.get_config(path)
        return str(value) == expected

    def _env(self, name: str) -> bool:
        """Check if environment variable is set and non-empty.

        Args:
            name: Environment variable name

        Returns:
            True if env var exists and is non-empty
        """
        return bool(os.environ.get(name))

    def _file_exists(self, path: str) -> bool:
        """Check if file exists in project.

        Args:
            path: Relative path from project root

        Returns:
            True if file exists
        """
        if self.context.project_root is None:
            return False
        return (self.context.project_root / path).exists()

    def _not(self, expr: str) -> bool:
        """Negate a condition expression.

        Args:
            expr: Condition expression to negate

        Returns:
            Negated result
        """
        return not self.evaluate(expr)

    def _and(self, expr1: str, expr2: str) -> bool:
        """Logical AND of two condition expressions.

        Args:
            expr1: First condition expression
            expr2: Second condition expression

        Returns:
            True if both conditions are true
        """
        return self.evaluate(expr1) and self.evaluate(expr2)

    def _or(self, expr1: str, expr2: str) -> bool:
        """Logical OR of two condition expressions.

        Args:
            expr1: First condition expression
            expr2: Second condition expression

        Returns:
            True if either condition is true
        """
        return self.evaluate(expr1) or self.evaluate(expr2)


class ConditionalProcessor:
    """Process conditional blocks and includes in templates.

    Handles:
    - {{include-if:CONDITION:path}}: Conditional file inclusion
    - {{if:CONDITION}}...{{/if}}: Conditional blocks
    - {{if:CONDITION}}...{{else}}...{{/if}}: If-else blocks
    """

    # Pattern for conditional includes: {{include-if:CONDITION:path}}
    INCLUDE_IF_PATTERN = re.compile(
        r"\{\{include-if:([^:]+):([^}]+)\}\}",
        re.DOTALL,
    )

    # Pattern for if blocks: {{if:CONDITION}}content{{/if}}
    IF_BLOCK_PATTERN = re.compile(
        r"\{\{if:([^}]+)\}\}(.*?)\{\{/if\}\}",
        re.DOTALL,
    )

    # Pattern for if-else blocks: {{if:CONDITION}}content{{else}}other{{/if}}
    IF_ELSE_BLOCK_PATTERN = re.compile(
        r"\{\{if:([^}]+)\}\}(.*?)\{\{else\}\}(.*?)\{\{/if\}\}",
        re.DOTALL,
    )

    def __init__(self, evaluator: ConditionEvaluator) -> None:
        """Initialize processor with condition evaluator.

        Args:
            evaluator: ConditionEvaluator for evaluating conditions
        """
        self.evaluator = evaluator

    def process_if_blocks(self, content: str) -> str:
        """Process all conditional blocks in content.

        First processes if-else blocks, then simple if blocks.

        Args:
            content: Template content with conditional blocks

        Returns:
            Content with conditionals resolved
        """
        # Process if-else blocks first (they're more specific)
        def replace_if_else(match: re.Match[str]) -> str:
            condition = match.group(1)
            true_content = match.group(2)
            false_content = match.group(3)
            try:
                if self.evaluator.evaluate(condition):
                    return true_content.strip()
                return false_content.strip()
            except ValueError:
                # Keep original if condition is invalid
                return match.group(0)

        content = self.IF_ELSE_BLOCK_PATTERN.sub(replace_if_else, content)

        # Process simple if blocks
        def replace_if(match: re.Match[str]) -> str:
            condition = match.group(1)
            block_content = match.group(2)
            try:
                if self.evaluator.evaluate(condition):
                    return block_content.strip()
                return ""
            except ValueError:
                # Keep original if condition is invalid
                return match.group(0)

        content = self.IF_BLOCK_PATTERN.sub(replace_if, content)

        return content

    def get_conditional_includes(self, content: str) -> List[tuple[str, str, bool]]:
        """Extract conditional includes and their evaluation results.

        Args:
            content: Template content

        Returns:
            List of (condition, path, should_include) tuples
        """
        results: List[tuple[str, str, bool]] = []
        for match in self.INCLUDE_IF_PATTERN.finditer(content):
            condition = match.group(1)
            path = match.group(2)
            try:
                should_include = self.evaluator.evaluate(condition)
            except ValueError:
                should_include = False
            results.append((condition, path, should_include))
        return results

    def process_conditional_includes(
        self,
        content: str,
        include_resolver: Callable[[str], str],
    ) -> str:
        """Process conditional includes, resolving those that pass.

        Args:
            content: Template content
            include_resolver: Function to resolve include path to content

        Returns:
            Content with conditional includes resolved
        """

        def replacer(match: re.Match[str]) -> str:
            condition = match.group(1)
            path = match.group(2)
            try:
                if self.evaluator.evaluate(condition):
                    return include_resolver(path)
                return ""
            except ValueError:
                # Keep original if condition is invalid
                return match.group(0)

        return self.INCLUDE_IF_PATTERN.sub(replacer, content)
