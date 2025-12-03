"""Function transformer for Edison composition engine.

Enables embedding custom Python functions in templates that return text.
Functions can access TransformContext for project information.

Syntax:
    {{function:name()}}              - Call with no arguments
    {{function:name("arg")}}         - Call with string argument
    {{function:name("a", "b")}}      - Call with multiple arguments

Functions that take TransformContext as first argument receive it automatically.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Callable, Dict, List, Optional, Union

from .base import ContentTransformer, TransformContext


# Type for registered functions
FunctionType = Callable[..., str]


class FunctionRegistry:
    """Registry for custom template functions.

    Functions can be registered using the @register decorator:

        registry = FunctionRegistry()

        @registry.register("greet")
        def greet(name: str) -> str:
            return f"Hello, {name}!"

    Functions can optionally receive TransformContext:

        @registry.register("project")
        def project_name(ctx: TransformContext) -> str:
            return ctx.project_root.name if ctx.project_root else "unknown"
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._functions: Dict[str, FunctionType] = {}

    def register(self, name: str) -> Callable[[FunctionType], FunctionType]:
        """Decorator to register a function.

        Args:
            name: Name to register the function under

        Returns:
            Decorator that registers the function
        """
        def decorator(func: FunctionType) -> FunctionType:
            self._functions[name] = func
            return func
        return decorator

    def add(self, name: str, func: FunctionType) -> None:
        """Add a function to the registry.

        Args:
            name: Name to register the function under
            func: The function to register
        """
        self._functions[name] = func

    def get(self, name: str) -> Optional[FunctionType]:
        """Get a function by name.

        Args:
            name: Function name

        Returns:
            The function or None if not found
        """
        return self._functions.get(name)

    def __contains__(self, name: str) -> bool:
        """Check if a function is registered."""
        return name in self._functions

    def list_functions(self) -> List[str]:
        """List all registered function names."""
        return list(self._functions.keys())


# Global registry for convenience
global_registry = FunctionRegistry()


def register_function(name: str) -> Callable[[FunctionType], FunctionType]:
    """Register a function in the global registry.

    Usage:
        @register_function("hello")
        def hello() -> str:
            return "Hello!"
    """
    return global_registry.register(name)


class FunctionTransformer(ContentTransformer):
    """Transform function calls in templates.

    Processes {{function:name(args)}} directives by calling registered
    functions and substituting the result.
    """

    # Pattern to match function calls: {{function:name(args)}}
    FUNCTION_PATTERN = re.compile(
        r"\{\{function:(\w+)\((.*?)\)\}\}",
        re.DOTALL
    )

    def __init__(self, registry: Optional[FunctionRegistry] = None) -> None:
        """Initialize with optional custom registry.

        Args:
            registry: FunctionRegistry to use (defaults to global_registry)
        """
        self.registry = registry or global_registry

    def transform(self, content: str, context: TransformContext) -> str:
        """Transform function calls in content.

        Args:
            content: Input content with function directives
            context: TransformContext for the transformation

        Returns:
            Content with function calls resolved
        """
        def replace_function(match: re.Match[str]) -> str:
            func_name = match.group(1)
            args_str = match.group(2).strip()

            func = self.registry.get(func_name)
            if func is None:
                return f"[ERROR: function '{func_name}' not found]"

            try:
                # Parse arguments
                args = self._parse_args(args_str)

                # Check if function wants context
                result = self._call_function(func, args, context)
                return result

            except Exception as e:
                return f"[ERROR: {func_name}() - {e}]"

        return self.FUNCTION_PATTERN.sub(replace_function, content)

    def _parse_args(self, args_str: str) -> List[Any]:
        """Parse function arguments from string.

        Supports:
        - String literals: "hello" or 'hello'
        - Numbers: 42, 3.14
        - Empty args: ()

        Args:
            args_str: The argument string (without parentheses)

        Returns:
            List of parsed arguments
        """
        if not args_str:
            return []

        # Use Python's AST to safely parse literals
        try:
            # Wrap in a list literal to parse multiple args
            parsed = ast.literal_eval(f"[{args_str}]")
            return list(parsed)
        except (ValueError, SyntaxError):
            # Fallback: try to parse as a single string
            return [args_str.strip('"\'')]

    def _call_function(
        self,
        func: FunctionType,
        args: List[Any],
        context: TransformContext
    ) -> str:
        """Call a function with appropriate arguments.

        If the function's first parameter is annotated as TransformContext,
        the context is passed automatically.

        Args:
            func: The function to call
            args: Parsed arguments
            context: TransformContext

        Returns:
            Function result as string
        """
        import inspect

        # Check if function wants context
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if params:
            first_param = params[0]
            # Check annotation
            if first_param.annotation is TransformContext:
                return str(func(context, *args))
            # Check parameter name
            if first_param.name in ("ctx", "context"):
                return str(func(context, *args))

        return str(func(*args))


__all__ = [
    "FunctionRegistry",
    "FunctionTransformer",
    "register_function",
    "global_registry",
]
