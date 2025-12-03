"""Tests for FunctionTransformer.

Tests the custom Python function transformer for Edison composition engine.
Enables embedding custom Python functions that return text in composed files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from edison.core.composition.transformers.base import TransformContext
from edison.core.composition.transformers.functions import (
    FunctionTransformer,
    FunctionRegistry,
    register_function,
)


class TestFunctionRegistry:
    """Test function registration and lookup."""

    def test_register_function_simple(self) -> None:
        """Can register a simple function."""
        registry = FunctionRegistry()

        @registry.register("hello")
        def hello_func() -> str:
            return "Hello, World!"

        assert "hello" in registry
        assert registry.get("hello")() == "Hello, World!"

    def test_register_function_with_args(self) -> None:
        """Can register a function that takes arguments."""
        registry = FunctionRegistry()

        @registry.register("greet")
        def greet_func(name: str) -> str:
            return f"Hello, {name}!"

        assert registry.get("greet")("Edison") == "Hello, Edison!"

    def test_register_function_with_context(self) -> None:
        """Functions can receive TransformContext."""
        registry = FunctionRegistry()

        @registry.register("project_name")
        def project_name_func(ctx: TransformContext) -> str:
            return str(ctx.project_root.name if ctx.project_root else "unknown")

        ctx = TransformContext(project_root=Path("/test/myproject"))
        assert registry.get("project_name")(ctx) == "myproject"

    def test_missing_function_returns_none(self) -> None:
        """Getting a missing function returns None."""
        registry = FunctionRegistry()
        assert registry.get("nonexistent") is None


class TestFunctionTransformer:
    """Test function transformation in templates."""

    def test_transform_simple_function(self, tmp_path: Path) -> None:
        """Transforms simple function call without arguments."""
        registry = FunctionRegistry()

        @registry.register("version")
        def version_func() -> str:
            return "1.0.0"

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = "Version: {{function:version()}}"
        result = transformer.transform(content, ctx)

        assert result == "Version: 1.0.0"

    def test_transform_function_with_string_arg(self, tmp_path: Path) -> None:
        """Transforms function call with string argument."""
        registry = FunctionRegistry()

        @registry.register("upper")
        def upper_func(text: str) -> str:
            return text.upper()

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = 'Result: {{function:upper("hello")}}'
        result = transformer.transform(content, ctx)

        assert result == "Result: HELLO"

    def test_transform_function_with_multiple_args(self, tmp_path: Path) -> None:
        """Transforms function call with multiple arguments."""
        registry = FunctionRegistry()

        @registry.register("join")
        def join_func(sep: str, *parts: str) -> str:
            return sep.join(parts)

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = '{{function:join("-", "a", "b", "c")}}'
        result = transformer.transform(content, ctx)

        assert result == "a-b-c"

    def test_transform_function_with_context(self, tmp_path: Path) -> None:
        """Functions can access TransformContext."""
        registry = FunctionRegistry()

        @registry.register("active_packs_list")
        def active_packs_func(ctx: TransformContext) -> str:
            return ", ".join(ctx.active_packs)

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(
            project_root=tmp_path,
            active_packs=["python", "typescript"]
        )

        content = "Packs: {{function:active_packs_list()}}"
        result = transformer.transform(content, ctx)

        assert result == "Packs: python, typescript"

    def test_transform_function_error_handling(self, tmp_path: Path) -> None:
        """Function errors are handled gracefully."""
        registry = FunctionRegistry()

        @registry.register("bad")
        def bad_func() -> str:
            raise ValueError("Something went wrong")

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = "Result: {{function:bad()}}"
        result = transformer.transform(content, ctx)

        # Should contain error message
        assert "ERROR" in result or "Something went wrong" in result

    def test_transform_unknown_function(self, tmp_path: Path) -> None:
        """Unknown functions are left as-is or show error."""
        registry = FunctionRegistry()
        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = "Result: {{function:unknown()}}"
        result = transformer.transform(content, ctx)

        # Should indicate function not found
        assert "unknown" in result.lower() or "not found" in result.lower() or "{{function:" in result

    def test_transform_multiple_functions(self, tmp_path: Path) -> None:
        """Transforms multiple function calls in same content."""
        registry = FunctionRegistry()

        @registry.register("a")
        def func_a() -> str:
            return "AAA"

        @registry.register("b")
        def func_b() -> str:
            return "BBB"

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = "{{function:a()}} - {{function:b()}}"
        result = transformer.transform(content, ctx)

        assert result == "AAA - BBB"

    def test_transform_nested_quotes(self, tmp_path: Path) -> None:
        """Handles arguments with nested/escaped quotes."""
        registry = FunctionRegistry()

        @registry.register("echo")
        def echo_func(text: str) -> str:
            return text

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = "{{function:echo('hello \"world\"')}}"
        result = transformer.transform(content, ctx)

        assert 'hello "world"' in result


class TestGlobalRegistry:
    """Test global function registration."""

    def test_global_register_decorator(self) -> None:
        """Can use global register decorator."""
        @register_function("global_test")
        def global_test_func() -> str:
            return "global"

        # Should be in the global registry
        from edison.core.composition.transformers.functions import global_registry
        assert "global_test" in global_registry


class TestFunctionTransformerIntegration:
    """Integration tests with realistic functions."""

    def test_generate_timestamp(self, tmp_path: Path) -> None:
        """Function that generates timestamps."""
        registry = FunctionRegistry()

        @registry.register("now")
        def now_func(fmt: str = "%Y-%m-%d") -> str:
            from datetime import datetime
            return datetime.now().strftime(fmt)

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = "Generated: {{function:now()}}"
        result = transformer.transform(content, ctx)

        # Should contain a date
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2}", result)

    def test_read_file_content(self, tmp_path: Path) -> None:
        """Function that reads file content."""
        # Create a test file
        test_file = tmp_path / "version.txt"
        test_file.write_text("2.0.0")

        registry = FunctionRegistry()

        @registry.register("read_version")
        def read_version_func(ctx: TransformContext) -> str:
            vfile = ctx.project_root / "version.txt" if ctx.project_root else None
            if vfile and vfile.exists():
                return vfile.read_text().strip()
            return "0.0.0"

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = "Version: {{function:read_version()}}"
        result = transformer.transform(content, ctx)

        assert result == "Version: 2.0.0"

    def test_list_files_in_directory(self, tmp_path: Path) -> None:
        """Function that lists files in a directory."""
        # Create test files
        (tmp_path / "file1.md").write_text("# File 1")
        (tmp_path / "file2.md").write_text("# File 2")
        (tmp_path / "other.txt").write_text("other")

        registry = FunctionRegistry()

        @registry.register("list_md_files")
        def list_md_func(ctx: TransformContext) -> str:
            if not ctx.project_root:
                return ""
            files = sorted(ctx.project_root.glob("*.md"))
            return "\n".join(f"- {f.name}" for f in files)

        transformer = FunctionTransformer(registry=registry)
        ctx = TransformContext(project_root=tmp_path)

        content = "## Files\n{{function:list_md_files()}}"
        result = transformer.transform(content, ctx)

        assert "- file1.md" in result
        assert "- file2.md" in result
        assert "other.txt" not in result
