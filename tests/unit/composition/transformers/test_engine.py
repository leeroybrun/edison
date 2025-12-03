"""Tests for TemplateEngine.

TDD: These tests define the expected behavior for the 9-step transformation pipeline.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.engine import TemplateEngine
from edison.core.composition.transformers.base import TransformContext


class TestTemplateEngine:
    """Tests for the TemplateEngine 9-step pipeline."""

    def test_engine_initialization(self) -> None:
        """Engine should initialize with config and packs."""
        engine = TemplateEngine(
            config={"project": {"name": "test"}},
            packs=["react", "nextjs"],
        )

        assert engine.config["project"]["name"] == "test"
        assert "react" in engine.packs
        assert "nextjs" in engine.packs

    def test_process_returns_content_and_report(self) -> None:
        """Process should return tuple of content and report."""
        engine = TemplateEngine()
        content, report = engine.process("# Test", entity_name="test-agent")

        assert isinstance(content, str)
        assert report.entity_name == "test-agent"

    def test_process_sets_entity_type(self) -> None:
        """Report should include entity type."""
        engine = TemplateEngine()
        _, report = engine.process(
            "# Test",
            entity_name="test-agent",
            entity_type="agent",
        )

        assert report.entity_type == "agent"

    def test_process_records_source_layers(self) -> None:
        """Report should include source layers."""
        engine = TemplateEngine()
        _, report = engine.process(
            "# Test",
            entity_name="test",
            source_layers=["core", "pack:react", "project"],
        )

        assert report.source_layers == ["core", "pack:react", "project"]
        assert "core" in report.source_layer_string

    def test_process_strips_section_markers(self) -> None:
        """Section markers should be stripped from final output."""
        engine = TemplateEngine()
        content = """
<!-- SECTION: tools -->
- Tool content
<!-- /SECTION: tools -->
"""
        result, _ = engine.process(content, entity_name="test")

        assert "<!-- SECTION:" not in result
        assert "<!-- /SECTION:" not in result
        assert "Tool content" in result


class TestConditionalProcessing:
    """Tests for conditional block processing (Step 3)."""

    def test_if_block_true(self) -> None:
        """If block should render when condition is true."""
        engine = TemplateEngine(packs=["react"])
        content = """
{{if:has-pack(react)}}
React is active
{{/if}}
"""
        result, report = engine.process(content, entity_name="test")

        assert "React is active" in result
        assert report.conditionals_evaluated > 0

    def test_if_block_false(self) -> None:
        """If block should not render when condition is false."""
        engine = TemplateEngine(packs=[])
        content = """
{{if:has-pack(react)}}
React is active
{{/if}}
"""
        result, _ = engine.process(content, entity_name="test")

        assert "React is active" not in result

    def test_if_else_block(self) -> None:
        """If-else block should render correct branch."""
        engine = TemplateEngine(packs=["vue"])
        content = """
{{if:has-pack(react)}}
Using React
{{else}}
Not using React
{{/if}}
"""
        result, _ = engine.process(content, entity_name="test")

        assert "Not using React" in result
        assert "Using React" not in result


class TestLoopProcessing:
    """Tests for loop expansion (Step 4)."""

    def test_each_loop_expands(self) -> None:
        """Each loop should expand for each item."""
        engine = TemplateEngine()
        engine.pipeline.transformers[2].context = TransformContext(
            context_vars={"tools": ["grep", "find", "sed"]},
        )

        # Note: LoopExpander accesses context.context_vars for data
        # For this test we need to inject data into context
        # This would need proper integration with TransformContext

    def test_each_index_substitution(self) -> None:
        """Each loop should substitute index."""
        # Similar to above - needs proper context setup
        pass


class TestVariableProcessing:
    """Tests for variable substitution (Steps 5-7)."""

    def test_config_variable_substitution(self) -> None:
        """Config variables should be substituted."""
        engine = TemplateEngine(
            config={"project": {"name": "MyProject"}},
        )
        content = "Project: {{config.project.name}}"
        result, report = engine.process(content, entity_name="test")

        assert "Project: MyProject" in result
        assert "config.project.name" in report.variables_substituted

    def test_missing_config_variable(self) -> None:
        """Missing config variables should be flagged."""
        engine = TemplateEngine(config={})
        content = "Project: {{config.project.name}}"
        result, report = engine.process(content, entity_name="test")

        # Original marker remains
        assert "{{config.project.name}}" in result
        # Flagged as missing
        assert len(report.variables_missing) > 0

    def test_context_variable_substitution(self) -> None:
        """Context variables should be substituted."""
        engine = TemplateEngine()
        content = "Layers: {{source_layers}}"
        result, report = engine.process(
            content,
            entity_name="test",
            source_layers=["core", "pack:react"],
        )

        assert "Layers: core + pack:react" in result


class TestReferenceProcessing:
    """Tests for reference rendering (Step 8)."""

    def test_reference_section_renders(self) -> None:
        """Reference section should render as pointer."""
        engine = TemplateEngine()
        content = "{{reference-section:guidelines/TDD.md#rules|TDD requirements}}"
        result, _ = engine.process(content, entity_name="test")

        assert "guidelines/TDD.md#rules" in result
        assert "TDD requirements" in result


class TestBatchProcessing:
    """Tests for batch entity processing."""

    def test_process_batch(self) -> None:
        """Batch processing should process multiple entities."""
        engine = TemplateEngine()
        entities = {
            "agent-a": "# Agent A content",
            "agent-b": "# Agent B content",
        }

        results = engine.process_batch(entities, entity_type="agent")

        assert "agent-a" in results
        assert "agent-b" in results
        assert "Agent A content" in results["agent-a"][0]
        assert results["agent-a"][1].entity_type == "agent"


class TestReportGeneration:
    """Tests for composition report generation."""

    def test_report_tracks_includes(self, tmp_path: Path) -> None:
        """Report should track resolved includes."""
        # Create a file to include
        include_file = tmp_path / "include.md"
        include_file.write_text("Included content")

        engine = TemplateEngine(source_dir=tmp_path)
        content = "{{include:include.md}}"
        result, report = engine.process(content, entity_name="test")

        assert "Included content" in result
        assert "include.md" in report.includes_resolved

    def test_report_summary(self) -> None:
        """Report summary should be human-readable."""
        engine = TemplateEngine()
        _, report = engine.process(
            "# Test",
            entity_name="test-agent",
            entity_type="agent",
            source_layers=["core"],
        )

        summary = report.summary()

        assert "test-agent" in summary
        assert "agent" in summary
        assert "Layers:" in summary
