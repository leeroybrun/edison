"""Base class for data-driven document generators.

ComposableGenerator provides two-phase generation:
1. Phase 1: Compose template from layers using MarkdownCompositionStrategy
2. Phase 2: Inject data into template using TemplateEngine

All generators (rosters, state machine, canonical) extend this base class.
"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional

from edison.core.composition.core.base import CompositionBase


class ComposableGenerator(CompositionBase):
    """Base class for data-driven document generation.

    Two-phase generation:
    1. Compose template from layers (MarkdownCompositionStrategy)
    2. Inject data (TemplateEngine with {{#each}} loops)

    Templates support SECTION/EXTEND markers for pack customization,
    then data injection for dynamic content.

    Subclasses MUST implement:
        - template_name: Template filename without extension
        - output_filename: Output filename
        - _gather_data(): Gather data for template injection

    Example:
        class AgentRosterGenerator(ComposableGenerator):
            template_name = "AVAILABLE_AGENTS"
            output_filename = "AVAILABLE_AGENTS.md"

            def _gather_data(self) -> Dict[str, Any]:
                registry = AgentRegistry(project_root=self.project_root)
                return {
                    "agents": registry.get_all_metadata(),
                    "timestamp": utc_timestamp(),
                }
    """

    content_type: ClassVar[str] = "generators"

    @property
    @abstractmethod
    def template_name(self) -> Optional[str]:
        """Template filename without extension (e.g., 'AVAILABLE_AGENTS').

        Return None if no template is needed (generator renders directly from data).

        Returns:
            Template name or None
        """
        ...

    @property
    @abstractmethod
    def output_filename(self) -> str:
        """Output filename (e.g., 'AVAILABLE_AGENTS.md').

        Returns:
            Output filename with extension
        """
        ...

    @abstractmethod
    def _gather_data(self) -> Dict[str, Any]:
        """Gather data for template injection.

        Returns:
            Dictionary of data to inject into template
        """
        ...

    def generate(self) -> str:
        """Two-phase generation: compose template, then inject data.

        Phase 1: Compose template from layers (if template_name is not None)
        Phase 2: Inject data via TemplateEngine

        Returns:
            Generated content as string
        """
        # Phase 1: Compose template from layers (if template exists)
        if self.template_name:
            template = self._compose_template()
        else:
            template = ""

        # Phase 2: Inject data
        data = self._gather_data()
        if template:
            return self._inject_data(template, data)
        else:
            # No template - subclass should override generate() entirely
            return ""

    def _compose_template(self) -> str:
        """Compose template from layers using MarkdownCompositionStrategy.

        Uses LayerDiscovery to find template across layers, then applies
        MarkdownCompositionStrategy for section composition.

        Returns:
            Composed template content
        """
        from edison.core.composition.core.discovery import LayerDiscovery
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        # Discover template files across layers
        discovery = LayerDiscovery(
            content_type=self.content_type,
            core_dir=self.core_dir,
            packs_dir=self.bundled_packs_dir,
            project_dir=self.project_dir,
        )

        # Gather layers for template (same pattern as ComposableRegistry)
        layers = self._gather_template_layers(discovery, self.template_name)

        if not layers:
            raise FileNotFoundError(
                f"Template '{self.template_name}.md' not found in {self.content_type}/ "
                f"across any layers (core, packs, project)"
            )

        # Compose using MarkdownCompositionStrategy
        strategy = MarkdownCompositionStrategy(
            enable_sections=True,
            enable_dedupe=False,
            enable_template_processing=False,  # Don't process {{}} yet
        )

        context = CompositionContext(
            active_packs=self.get_active_packs(),
            config=self.config,
            project_root=self.project_root,
        )

        return strategy.compose(layers, context)

    def _gather_template_layers(
        self,
        discovery: "LayerDiscovery",  # type: ignore[name-defined]
        template_name: str,
    ) -> list[LayerContent]:  # type: ignore[name-defined]
        """Gather template content from all layers.

        Args:
            discovery: LayerDiscovery instance
            template_name: Template name without extension

        Returns:
            List of LayerContent in order (core → packs → project)
        """
        from edison.core.composition.strategies import LayerContent

        layers: list[LayerContent] = []
        packs = self.get_active_packs()

        # Discover core entities
        core_entities = discovery.discover_core()
        existing = set(core_entities.keys())

        # Check if template is in core
        if template_name in core_entities:
            path = core_entities[template_name].path
            content = path.read_text(encoding="utf-8")
            layers.append(LayerContent(content=content, source="core", path=path))

        # Check pack layers
        for pack in packs:
            # Check pack for overlay
            try:
                pack_overlays = discovery.discover_pack_overlays(pack, existing)
                if template_name in pack_overlays:
                    path = pack_overlays[template_name].path
                    content = path.read_text(encoding="utf-8")
                    layers.append(
                        LayerContent(content=content, source=f"pack:{pack}", path=path)
                    )
            except Exception:
                pass

        # Check project layer for overlay
        try:
            project_overlays = discovery.discover_project_overlays(existing)
            if template_name in project_overlays:
                path = project_overlays[template_name].path
                content = path.read_text(encoding="utf-8")
                layers.append(LayerContent(content=content, source="project", path=path))
        except Exception:
            pass

        return layers

    def _inject_data(self, template: str, data: Dict[str, Any]) -> str:
        """Inject data into template using TemplateEngine.

        Args:
            template: Template content with {{...}} markers
            data: Data dictionary for injection

        Returns:
            Content with data injected
        """
        from edison.core.composition.transformers.base import TransformContext
        from edison.core.composition.transformers import TransformerPipeline
        from edison.core.composition.transformers.loops import LoopExpander
        from edison.core.composition.transformers.variables import VariableTransformer

        # Build a simple pipeline for data injection (loops + variables)
        # We don't need includes, conditionals, etc. since template is already composed
        pipeline = TransformerPipeline([
            LoopExpander(),  # Process {{#each}} loops
            VariableTransformer(),  # Process {{variables}}
        ])

        # Create context with our data as context_vars
        context = TransformContext(
            config=self.config,
            active_packs=self.get_active_packs(),
            project_root=self.project_root,
            context_vars=data,  # This is where our data goes
        )

        # Execute pipeline
        result = pipeline.execute(template, context)
        return result

    def write(self, output_dir: Path) -> Path:
        """Generate and write to file.

        Args:
            output_dir: Directory where output file should be written

        Returns:
            Path to written file
        """
        content = self.generate()
        output_path = output_dir / self.output_filename
        self.writer.write_text(output_path, content)
        return output_path


__all__ = [
    "ComposableGenerator",
]
