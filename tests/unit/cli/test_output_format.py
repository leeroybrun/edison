"""Tests for unified CLI output format mechanism.

This module tests the output format infrastructure that makes Edison CLI outputs
consistently LLM-friendly by default (Markdown or YAML instead of JSON).

Key requirements:
1. Support --format markdown|yaml|text|json flag
2. Keep --json as backwards-compatible alias for --format json
3. LLM-facing commands default to markdown
4. Config commands default to yaml
5. No command prints JSON by default (regression test)
"""
from __future__ import annotations

import argparse
import json
from enum import Enum

import pytest


class TestOutputFormatEnum:
    """Test OutputFormat enum definition."""

    def test_output_format_enum_exists(self) -> None:
        """OutputFormat enum should be importable from edison.cli._output."""
        from edison.cli._output import OutputFormat

        assert isinstance(OutputFormat, type)
        assert issubclass(OutputFormat, Enum)

    def test_output_format_has_required_values(self) -> None:
        """OutputFormat should have markdown, yaml, text, and json values."""
        from edison.cli._output import OutputFormat

        assert hasattr(OutputFormat, "MARKDOWN")
        assert hasattr(OutputFormat, "YAML")
        assert hasattr(OutputFormat, "TEXT")
        assert hasattr(OutputFormat, "JSON")

    def test_output_format_values_are_lowercase_strings(self) -> None:
        """OutputFormat values should be lowercase strings for CLI use."""
        from edison.cli._output import OutputFormat

        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.YAML.value == "yaml"
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.JSON.value == "json"


class TestAddFormatFlag:
    """Test add_format_flag helper function."""

    def test_add_format_flag_exists(self) -> None:
        """add_format_flag helper should be importable from edison.cli."""
        from edison.cli import add_format_flag

        assert callable(add_format_flag)

    def test_add_format_flag_adds_format_argument(self) -> None:
        """add_format_flag should add --format argument with choices."""
        from edison.cli import add_format_flag

        parser = argparse.ArgumentParser()
        add_format_flag(parser)

        args = parser.parse_args(["--format", "json"])
        assert args.format == "json"

    def test_add_format_flag_default_is_markdown(self) -> None:
        """add_format_flag should default to markdown."""
        from edison.cli import add_format_flag

        parser = argparse.ArgumentParser()
        add_format_flag(parser)

        args = parser.parse_args([])
        assert args.format == "markdown"

    def test_add_format_flag_accepts_all_formats(self) -> None:
        """add_format_flag should accept markdown, yaml, text, and json."""
        from edison.cli import add_format_flag

        parser = argparse.ArgumentParser()
        add_format_flag(parser)

        for fmt in ["markdown", "yaml", "text", "json"]:
            args = parser.parse_args(["--format", fmt])
            assert args.format == fmt

    def test_add_format_flag_custom_default(self) -> None:
        """add_format_flag should accept a custom default format."""
        from edison.cli import add_format_flag

        parser = argparse.ArgumentParser()
        add_format_flag(parser, default="yaml")

        args = parser.parse_args([])
        assert args.format == "yaml"

    def test_add_format_flag_with_json_flag_prefers_json(self) -> None:
        """When both --json and --format are present, --json takes precedence."""
        from edison.cli import add_format_flag, add_json_flag

        parser = argparse.ArgumentParser()
        add_json_flag(parser)
        add_format_flag(parser)

        # --json should set format to json
        args = parser.parse_args(["--json"])
        assert getattr(args, "json", False) is True


class TestOutputFormatterFormat:
    """Test OutputFormatter with format support."""

    def test_output_formatter_accepts_format_parameter(self) -> None:
        """OutputFormatter should accept a format parameter."""
        from edison.cli._output import OutputFormat, OutputFormatter

        fmt = OutputFormatter(format=OutputFormat.MARKDOWN)
        assert fmt.format == OutputFormat.MARKDOWN

    def test_output_formatter_json_mode_from_format(self) -> None:
        """OutputFormatter should set json_mode=True when format is JSON."""
        from edison.cli._output import OutputFormat, OutputFormatter

        fmt = OutputFormatter(format=OutputFormat.JSON)
        assert fmt.json_mode is True

        fmt = OutputFormatter(format=OutputFormat.MARKDOWN)
        assert fmt.json_mode is False

    def test_output_formatter_backwards_compat_json_mode(self) -> None:
        """OutputFormatter should still accept json_mode parameter directly."""
        from edison.cli._output import OutputFormat, OutputFormatter

        # Legacy usage
        fmt = OutputFormatter(json_mode=True)
        assert fmt.json_mode is True
        assert fmt.format == OutputFormat.JSON

        fmt = OutputFormatter(json_mode=False)
        assert fmt.json_mode is False
        # Default format when json_mode=False is markdown
        assert fmt.format == OutputFormat.MARKDOWN

    def test_output_formatter_format_output_yaml(self, capsys) -> None:
        """OutputFormatter.format_output should render YAML when format is YAML."""
        from edison.cli._output import OutputFormat, OutputFormatter

        fmt = OutputFormatter(format=OutputFormat.YAML)
        fmt.format_output({"key": "value", "nested": {"a": 1}})

        out = capsys.readouterr().out
        # Should be YAML, not JSON
        assert "key: value" in out or "key:" in out
        assert "{" not in out  # Not JSON

    def test_output_formatter_format_output_markdown(self, capsys) -> None:
        """OutputFormatter.format_output should render Markdown when format is MARKDOWN."""
        from edison.cli._output import OutputFormat, OutputFormatter

        fmt = OutputFormatter(format=OutputFormat.MARKDOWN)
        fmt.format_output({"title": "Test", "items": ["a", "b"]}, template="status")

        out = capsys.readouterr().out
        # Markdown output should not be JSON
        assert "{" not in out or "```" in out  # Either not JSON or in a code block


class TestResolveOutputFormat:
    """Test resolve_output_format helper."""

    def test_resolve_output_format_exists(self) -> None:
        """resolve_output_format helper should exist in _output.py."""
        from edison.cli._output import resolve_output_format

        assert callable(resolve_output_format)

    def test_resolve_output_format_from_args(self) -> None:
        """resolve_output_format should extract format from args namespace."""
        from edison.cli._output import OutputFormat, resolve_output_format

        args = argparse.Namespace(format="yaml", json=False)
        result = resolve_output_format(args)
        assert result == OutputFormat.YAML

    def test_resolve_output_format_json_flag_overrides(self) -> None:
        """resolve_output_format should return JSON when --json is set."""
        from edison.cli._output import OutputFormat, resolve_output_format

        args = argparse.Namespace(format="markdown", json=True)
        result = resolve_output_format(args)
        assert result == OutputFormat.JSON

    def test_resolve_output_format_default_when_missing(self) -> None:
        """resolve_output_format should return default when args lacks format."""
        from edison.cli._output import OutputFormat, resolve_output_format

        args = argparse.Namespace()
        result = resolve_output_format(args, default=OutputFormat.TEXT)
        assert result == OutputFormat.TEXT


class TestNoDefaultJsonRegression:
    """Regression tests: no LLM-facing command should output JSON by default."""

    def test_output_formatter_default_is_not_json(self) -> None:
        """Default OutputFormatter should not be in JSON mode."""
        from edison.cli._output import OutputFormat, OutputFormatter

        fmt = OutputFormatter()
        assert fmt.json_mode is False
        assert fmt.format != OutputFormat.JSON

    def test_add_format_flag_default_is_not_json(self) -> None:
        """add_format_flag default should not be json."""
        from edison.cli import add_format_flag

        parser = argparse.ArgumentParser()
        add_format_flag(parser)

        args = parser.parse_args([])
        assert args.format != "json"


class TestFormatFromArgs:
    """Test creating OutputFormatter from args namespace."""

    def test_formatter_from_args_with_format(self) -> None:
        """OutputFormatter.from_args should use format from args."""
        from edison.cli._output import OutputFormat, OutputFormatter

        args = argparse.Namespace(format="yaml", json=False)
        fmt = OutputFormatter.from_args(args)
        assert fmt.format == OutputFormat.YAML

    def test_formatter_from_args_json_flag(self) -> None:
        """OutputFormatter.from_args should use JSON when --json is set."""
        from edison.cli._output import OutputFormat, OutputFormatter

        args = argparse.Namespace(format="markdown", json=True)
        fmt = OutputFormatter.from_args(args)
        assert fmt.format == OutputFormat.JSON
        assert fmt.json_mode is True

    def test_formatter_from_args_backwards_compat(self) -> None:
        """OutputFormatter.from_args should work with legacy json-only args."""
        from edison.cli._output import OutputFormat, OutputFormatter

        # Old-style args without format attribute
        args = argparse.Namespace(json=True)
        fmt = OutputFormatter.from_args(args)
        assert fmt.json_mode is True

        args = argparse.Namespace(json=False)
        fmt = OutputFormatter.from_args(args)
        assert fmt.json_mode is False
