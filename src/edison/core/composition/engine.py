"""Template Engine for Phase 2 of two-phase composition.

The TemplateEngine processes composed content through a 10-step transformation
pipeline. It works on output from the unified composition strategy (Phase 1).

Two-Phase Architecture:
- Phase 1 (MarkdownCompositionStrategy via registries): Layer merging, EXTEND into SECTION
- Phase 2 (TemplateEngine): Template processing, variable substitution

Transformation Pipeline (10 steps):
1. INCLUDES        - {{include:path}}, {{include-optional:path}}
2. SECTION EXTRACT - {{include-section:path#name}}
3. CONDITIONALS    - {{include-if:COND:path}}, {{if:COND}}...{{/if}}
4. LOOPS           - {{#each collection}}...{{/each}} (uses context_vars)
5. FUNCTIONS       - {{fn:name arg1 arg2}} or {{function:name("arg")}}
6. CONFIG VARS     - {{config.path.to.value}}, {{project.path}}
7. CONTEXT VARS    - {{source_layers}}, {{timestamp}}, and custom context_vars
8. PATH VARS       - {{PROJECT_EDISON_DIR}}
9. REFERENCES      - {{reference-section:path#name|purpose}}
10. VALIDATION     - Check for unresolved {{...}}, strip markers

Context Variables:
- Built-in: source_layers, timestamp (always set)
- Custom: Passed via context_vars parameter, merged with defaults
- Type: strings for {{var}} substitution, lists/dicts for {{#each}} loops
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .core.report import CompositionReport
from .core.sections import SectionParser
from .transformers.base import ContentTransformer, TransformContext, TransformerPipeline
# Import unified CompositionContext from central location
from .context import CompositionContext
from .transformers.conditionals import ConditionEvaluator, ConditionalProcessor
from .transformers.includes import IncludeTransformer
from .transformers.loops import LoopExpander
from .transformers.references import ReferenceRenderer
from .transformers.variables import VariableTransformer
from .transformers.functions import FunctionTransformer


class CodeLiteralProtector(ContentTransformer):
    """Protect template directive tokens inside Markdown code spans/fences.

    Edison templates are processed via regex transformers that do not understand
    Markdown. Without protection, documentation that *shows* Edison directives
    (e.g. `{{include:...}}`) or section markers (e.g. `<!-- SECTION: ... -->`)
    can accidentally execute during composition and/or trigger strict validation.

    This transformer masks directive tokens inside:
    - Inline code spans: `...`
    - Fenced code blocks: ``` ... ```
    and a paired restorer unmasks them at the very end of the pipeline.
    """

    _LBRACE = "⟪EDISON_LBRACE⟫"
    _RBRACE = "⟪EDISON_RBRACE⟫"
    _COMMENT_OPEN = "⟪EDISON_COMMENT_OPEN⟫"
    _COMMENT_CLOSE = "⟪EDISON_COMMENT_CLOSE⟫"

    _INLINE_CODE = re.compile(r"(`+)([^`\n]*?)\1")

    @classmethod
    def _protect_tokens(cls, text: str) -> str:
        return (
            text.replace("{{", cls._LBRACE)
            .replace("}}", cls._RBRACE)
            .replace("<!--", cls._COMMENT_OPEN)
            .replace("-->", cls._COMMENT_CLOSE)
        )

    def transform(self, content: str, context: TransformContext) -> str:
        lines = content.splitlines(keepends=True)
        out: List[str] = []

        in_fence = False
        for line in lines:
            stripped = line.lstrip()
            is_fence = stripped.startswith("```")

            if is_fence:
                # Fence lines themselves should remain unchanged.
                out.append(line)
                in_fence = not in_fence
                continue

            if in_fence:
                out.append(self._protect_tokens(line))
                continue

            # Inline code spans (single-line only).
            def repl(match: re.Match[str]) -> str:
                ticks = match.group(1)
                body = match.group(2)
                return f"{ticks}{self._protect_tokens(body)}{ticks}"

            out.append(self._INLINE_CODE.sub(repl, line))

        return "".join(out)


class CodeLiteralRestorer(ContentTransformer):
    """Restore masked directive tokens produced by CodeLiteralProtector."""

    def transform(self, content: str, context: TransformContext) -> str:
        return (
            content.replace(CodeLiteralProtector._LBRACE, "{{")
            .replace(CodeLiteralProtector._RBRACE, "}}")
            .replace(CodeLiteralProtector._COMMENT_OPEN, "<!--")
            .replace(CodeLiteralProtector._COMMENT_CLOSE, "-->")
        )


class ConditionalTransformer(ContentTransformer):
    """Transformer wrapper for ConditionalProcessor.

    Bridges the ConditionalProcessor (using CompositionContext) with the
    ContentTransformer interface (using TransformContext).
    """

    def transform(self, content: str, context: TransformContext) -> str:
        """Process conditionals using context.

        Args:
            content: Content with conditional blocks
            context: Transform context

        Returns:
            Content with conditionals processed
        """
        # Create CompositionContext from TransformContext
        comp_context = CompositionContext(
            active_packs=context.active_packs,
            config=context.config,
            project_root=context.project_root,
        )

        evaluator = ConditionEvaluator(comp_context)
        processor = ConditionalProcessor(evaluator)

        # Process if blocks
        result = processor.process_if_blocks(content)

        # Process conditional includes
        def include_resolver(path: str) -> str:
            """Resolve include path to content."""
            if context.include_provider is not None:
                provided = context.include_provider(path)
                if provided is not None:
                    context.record_include(path)
                    return provided
            full_path = self._resolve_path(path, context)
            if full_path and full_path.exists():
                context.record_include(path)
                return full_path.read_text(encoding="utf-8")
            return ""

        result = processor.process_conditional_includes(result, include_resolver)

        # Update context stats
        context.conditionals_evaluated += 1

        return result

    def _resolve_path(self, path: str, context: TransformContext) -> Optional[Path]:
        """Resolve path to file."""
        if context.source_dir:
            source_path = context.source_dir / path
            if source_path.exists():
                return source_path
        if context.project_root:
            project_path = context.project_root / path
            if project_path.exists():
                return project_path
        return None


class ValidationTransformer(ContentTransformer):
    """Final validation step - check for unresolved markers.

    Finds any remaining {{...}} patterns that weren't processed.
    """

    # Pattern for any unresolved {{...}}
    UNRESOLVED_PATTERN = re.compile(r"\{\{[^}]+\}\}")

    def __init__(self, parser: Optional[SectionParser] = None) -> None:
        """Initialize with optional section parser.

        Args:
            parser: SectionParser for stripping markers (default: new instance)
        """
        self.parser = parser or SectionParser()

    def transform(self, content: str, context: TransformContext) -> str:
        """Validate and clean content.

        Args:
            content: Content to validate
            context: Transform context

        Returns:
            Cleaned content with markers stripped
        """
        # Find unresolved markers
        unresolved = self.UNRESOLVED_PATTERN.findall(content)
        for marker in unresolved:
            context.record_variable(marker, resolved=False)

        # Fail-closed on any template/include error markers. These should never
        # be emitted into composed artifacts; composition must stop so the root
        # cause can be fixed (missing include, missing section, circular include, etc.).
        if "<!-- ERROR:" in content:
            from edison.core.composition.core.errors import CompositionValidationError

            snippet = content.split("<!-- ERROR:", 1)[1]
            first_line = snippet.split("-->", 1)[0].strip()
            raise CompositionValidationError(f"Composition contains error marker: {first_line}")

        # Strip section markers, then ensure none remain (unbalanced markers indicate
        # a broken template or partial composition output that must be fixed).
        if getattr(context, "strip_section_markers", True):
            stripped = self.parser.strip_markers(content)
            # If any markers remain, they were not part of a well-formed SECTION/EXTEND block.
            if "<!--" in stripped:
                upper = stripped.upper()
                if "<!-- SECTION:" in upper or "<!-- /SECTION:" in upper or "<!-- EXTEND:" in upper or "<!-- /EXTEND" in upper:
                    from edison.core.composition.core.errors import CompositionValidationError

                    raise CompositionValidationError("Unbalanced SECTION/EXTEND markers detected (missing closing marker?)")
            return stripped
        return content


class TemplateEngine:
    """9-step template transformation engine.

    Usage:
        engine = TemplateEngine(config=config, packs=["react", "nextjs"])
        result = engine.process(composed_content, entity_name="api-builder")
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        packs: Optional[List[str]] = None,
        project_root: Optional[Path] = None,
        source_dir: Optional[Path] = None,
        include_provider: Optional[Callable[[str], Optional[str]]] = None,
        *,
        strip_section_markers: bool = True,
        protect_code_literals: bool = True,
    ) -> None:
        """Initialize the template engine.

        Args:
            config: Configuration dictionary
            packs: List of active pack names
            project_root: Project root path
            source_dir: Directory for resolving includes
        """
        self.config = config or {}
        self.packs = packs or []
        self.project_root = project_root
        self.source_dir = source_dir
        self.include_provider = include_provider
        self.strip_section_markers = strip_section_markers
        self.protect_code_literals = protect_code_literals

        # Load custom functions from layered functions/ folders
        try:
            from .transformers.functions_loader import load_functions

            load_functions(project_root=self.project_root, active_packs=self.packs)
        except Exception:
            # Function loading should never break template processing; ignore errors
            pass

        # Build the transformation pipeline
        self.pipeline = self._build_pipeline()

    def _build_pipeline(self) -> TransformerPipeline:
        """Build the 9-step transformation pipeline.

        Returns:
            TransformerPipeline with all transformers
        """
        transformers: list[Any] = []
        if self.protect_code_literals:
            # Step 0: Protect literal examples in markdown code (prevents executing
            # directive examples inside backticks/code fences).
            transformers.append(CodeLiteralProtector())

        transformers.extend(
            [
                # Step 1-2: Includes (regular + section extracts)
                IncludeTransformer(),
                # Step 3: Conditionals
                ConditionalTransformer(),
                # Step 4: Loops
                LoopExpander(),
                # Step 5: Functions (custom Python)
                FunctionTransformer(),
                # Step 6-8: Variables (config, context, path)
                VariableTransformer(),
                # Step 9: References
                ReferenceRenderer(),
                # Step 10: Validation
                ValidationTransformer(),
            ]
        )

        if self.protect_code_literals:
            # Step 11: Restore literal examples in markdown code.
            transformers.append(CodeLiteralRestorer())

        return TransformerPipeline(transformers)

    def process(
        self,
        content: str,
        entity_name: str = "unknown",
        entity_type: str = "template",
        source_layers: Optional[List[str]] = None,
        context_vars: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, CompositionReport]:
        """Process content through the transformation pipeline.

        Args:
            content: Composed content from Phase 1
            entity_name: Name of entity being processed
            entity_type: Type of entity (agent, guideline, etc.)
            source_layers: List of source layers that contributed
            context_vars: Custom template variables to merge with defaults.
                Values can be strings (for {{var}} substitution) or
                lists/dicts (for {{#each}} loops).

        Returns:
            Tuple of (processed content, report)
        """
        # Build default context vars
        # Get the configured project directory name (relative to repo root)
        from edison.core.utils.paths import get_project_config_dir
        if self.project_root is None:
            # Allow TemplateEngine usage in unit tests or library contexts where
            # a repo root is not provided. Fall back to the bootstrapped default.
            from edison.core.utils.paths.project import DEFAULT_PROJECT_CONFIG_PRIMARY

            project_dir_name = DEFAULT_PROJECT_CONFIG_PRIMARY
        else:
            project_dir = get_project_config_dir(self.project_root, create=False)
            project_dir_name = project_dir.name  # e.g., ".edison"
        
        default_vars: Dict[str, Any] = {
            "source_layers": " + ".join(source_layers) if source_layers else "core",
            "timestamp": datetime.now().isoformat(),
            "PROJECT_EDISON_DIR": project_dir_name,
        }

        # Merge custom context_vars (custom vars override defaults)
        merged_vars = {**default_vars, **(context_vars or {})}

        # Build context
        context = TransformContext(
            config=self.config,
            active_packs=self.packs,
            project_root=self.project_root,
            source_dir=self.source_dir,
            include_provider=self.include_provider,
            strip_section_markers=self.strip_section_markers,
            context_vars=merged_vars,
        )

        # Execute pipeline
        result = self.pipeline.execute(content, context)

        # Build report
        report = CompositionReport(
            entity_name=entity_name,
            entity_type=entity_type,
            source_layers=source_layers or ["core"],
            includes_resolved=context.includes_resolved,
            sections_extracted=context.sections_extracted,
            variables_substituted=context.variables_substituted,
            variables_missing=context.variables_missing,
            conditionals_evaluated=context.conditionals_evaluated,
        )

        # Add warnings for missing variables
        for missing in context.variables_missing:
            report.add_warning(f"Unresolved variable: {missing}")

        return result, report

    def process_batch(
        self,
        entities: Dict[str, str],
        entity_type: str = "template",
    ) -> Dict[str, tuple[str, CompositionReport]]:
        """Process multiple entities.

        Args:
            entities: Dict mapping entity name to composed content
            entity_type: Type of entities

        Returns:
            Dict mapping entity name to (processed content, report)
        """
        results: Dict[str, tuple[str, CompositionReport]] = {}

        for name, content in entities.items():
            results[name] = self.process(
                content,
                entity_name=name,
                entity_type=entity_type,
            )

        return results
