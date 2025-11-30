"""Section parsing and registry for layered composition.

HTML comment syntax for overlays:
- <!-- EXTEND: SectionName --> content <!-- /EXTEND -->
- <!-- NEW_SECTION: SectionName --> content <!-- /NEW_SECTION -->
- <!-- APPEND --> content <!-- /APPEND -->
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from .errors import CompositionValidationError


class SectionMode(Enum):
    """Mode for section handling in overlays."""
    EXTEND = "extend"       # Extend existing known/extensible section
    NEW_SECTION = "new"     # Define new extensible section
    APPEND = "append"       # Append to catch-all section


@dataclass
class ParsedSection:
    """A parsed section from an overlay file."""
    name: str
    mode: SectionMode
    content: str
    source_layer: str  # "core" | "pack:{name}" | "project"


@dataclass
class SectionRegistry:
    """Registry managing sections across composition layers.
    
    Tracks:
    - known_sections: Core-defined sections (can be extended)
    - extensible_sections: Pack/project-defined sections (can be extended by later layers)
    - append_sections: Catch-all content
    """
    known_sections: Dict[str, List[str]] = field(default_factory=dict)
    extensible_sections: Dict[str, List[str]] = field(default_factory=dict)
    append_sections: List[str] = field(default_factory=list)
    
    def add_extension(self, name: str, content: str) -> None:
        """Extend a known or extensible section."""
        if name in self.known_sections:
            self.known_sections[name].append(content)
        elif name in self.extensible_sections:
            self.extensible_sections[name].append(content)
        else:
            available_known = sorted(self.known_sections.keys())
            available_extensible = sorted(self.extensible_sections.keys())
            raise CompositionValidationError(
                f"Cannot extend section '{name}' - not a known or extensible section.\n"
                f"Known sections: {available_known}\n"
                f"Extensible sections: {available_extensible}\n"
                f"Use NEW_SECTION to define a new extensible section, "
                f"or APPEND for catch-all content."
            )
    
    def add_new_section(self, name: str, content: str) -> None:
        """Define a new extensible section (can be extended by later layers)."""
        if name in self.known_sections:
            raise CompositionValidationError(
                f"Cannot create new section '{name}' - already a known section in core.\n"
                f"Use EXTEND to add to it instead."
            )
        if name not in self.extensible_sections:
            self.extensible_sections[name] = []
        self.extensible_sections[name].append(content)
    
    def add_append(self, content: str) -> None:
        """Add catch-all content."""
        self.append_sections.append(content)


class SectionParser:
    """Parse HTML comment markers in overlay files.
    
    Supported markers:
    - <!-- EXTEND: SectionName --> content <!-- /EXTEND -->
    - <!-- NEW_SECTION: SectionName --> content <!-- /NEW_SECTION -->
    - <!-- APPEND --> content <!-- /APPEND -->
    """
    
    EXTEND_PATTERN = re.compile(
        r'<!--\s*EXTEND:\s*(\w+)\s*-->\s*(.*?)\s*<!--\s*/EXTEND\s*-->',
        re.DOTALL | re.IGNORECASE
    )
    NEW_SECTION_PATTERN = re.compile(
        r'<!--\s*NEW_SECTION:\s*(\w+)\s*-->\s*(.*?)\s*<!--\s*/NEW_SECTION\s*-->',
        re.DOTALL | re.IGNORECASE
    )
    APPEND_PATTERN = re.compile(
        r'<!--\s*APPEND\s*-->\s*(.*?)\s*<!--\s*/APPEND\s*-->',
        re.DOTALL | re.IGNORECASE
    )
    
    def parse(self, content: str, layer: str = "unknown") -> List[ParsedSection]:
        """Parse overlay content into structured sections."""
        sections: List[ParsedSection] = []
        
        # Parse EXTEND sections
        for match in self.EXTEND_PATTERN.finditer(content):
            sections.append(ParsedSection(
                name=match.group(1),
                mode=SectionMode.EXTEND,
                content=match.group(2).strip(),
                source_layer=layer,
            ))
        
        # Parse NEW_SECTION
        for match in self.NEW_SECTION_PATTERN.finditer(content):
            sections.append(ParsedSection(
                name=match.group(1),
                mode=SectionMode.NEW_SECTION,
                content=match.group(2).strip(),
                source_layer=layer,
            ))
        
        # Parse APPEND
        for match in self.APPEND_PATTERN.finditer(content):
            sections.append(ParsedSection(
                name="_append",
                mode=SectionMode.APPEND,
                content=match.group(1).strip(),
                source_layer=layer,
            ))
        
        return sections


class SectionComposer:
    """Compose final output from template and section registry."""
    
    # Pattern for section placeholders: {{SECTION:Name}}
    SECTION_PLACEHOLDER = re.compile(r'\{\{SECTION:(\w+)\}\}')
    
    def compose(self, template: str, registry: SectionRegistry) -> str:
        """Render final output by substituting sections into template."""
        result = template
        
        # 1. Replace known section placeholders
        for name, chunks in registry.known_sections.items():
            placeholder = f"{{{{SECTION:{name}}}}}"
            content = "\n\n".join(c for c in chunks if c)
            result = result.replace(placeholder, content)
        
        # 2. Build extensible sections block
        extensible_parts: List[str] = []
        for name, chunks in registry.extensible_sections.items():
            section_content = "\n\n".join(c for c in chunks if c)
            if section_content:
                extensible_parts.append(section_content)
        extensible_block = "\n\n".join(extensible_parts)
        result = result.replace("{{EXTENSIBLE_SECTIONS}}", extensible_block)
        
        # 3. Build append sections block
        append_block = "\n\n".join(c for c in registry.append_sections if c)
        result = result.replace("{{APPEND_SECTIONS}}", append_block)
        
        # 4. Clean up empty/unused placeholders
        result = self.SECTION_PLACEHOLDER.sub('', result)
        result = result.replace("{{EXTENSIBLE_SECTIONS}}", "")
        result = result.replace("{{APPEND_SECTIONS}}", "")
        
        # 5. Clean up excessive blank lines (max 2 consecutive)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()




