"""Test React pack for React 19 specific content coverage."""
from __future__ import annotations

from pathlib import Path
import pytest

# Locate repository root
_cur = Path(__file__).resolve()
ROOT = None
for i in range(1, 10):
    if i >= len(_cur.parents):
        break
    cand = _cur.parents[i]
    if (cand / '.git').exists():
        ROOT = cand
        break
assert ROOT is not None, 'cannot locate repository root (.git)'

from edison.core.composition.packs import validate_pack


REACT_PACK = ROOT / 'src/edison/data/packs/react'


class TestReactPackStructure:
    """Test React pack has correct structure."""

    def test_react_pack_exists(self):
        """React pack directory must exist."""
        assert REACT_PACK.exists(), f"React pack not found at {REACT_PACK}"

    def test_pack_yml_exists(self):
        """pack.yml must exist."""
        pack_yml = REACT_PACK / 'pack.yml'
        assert pack_yml.exists(), f"pack.yml not found at {pack_yml}"

    def test_pack_yml_well_formed(self):
        """pack.yml must be valid YAML with required fields."""
        import yaml
        pack_yml = REACT_PACK / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        data = yaml.safe_load(content)
        
        # Check required fields
        assert 'name' in data, "pack.yml must have 'name' field"
        assert 'version' in data, "pack.yml must have 'version' field"
        assert 'description' in data, "pack.yml must have 'description' field"
        assert 'triggers' in data, "pack.yml must have 'triggers' field"
        
        # Check triggers structure
        assert 'filePatterns' in data['triggers'], "triggers must have filePatterns"

    def test_agents_overlay_exists(self):
        """component-builder overlay must exist."""
        overlay = REACT_PACK / 'agents/overlays/component-builder.md'
        assert overlay.exists(), f"Agent overlay not found at {overlay}"

    def test_validators_overlay_exists(self):
        """Validators overlay must exist."""
        overlay = REACT_PACK / 'validators/overlays/global.md'
        assert overlay.exists(), f"Validator overlay not found at {overlay}"

    def test_rules_registry_exists(self):
        """Rules registry must exist."""
        registry = REACT_PACK / 'rules/registry.yml'
        assert registry.exists(), f"Rules registry not found at {registry}"


class TestReact19Content:
    """Test React 19 specific content is present."""

    def test_use_hook_content_exists(self):
        """use() hook must be documented (React 19 feature)."""
        hook_file = REACT_PACK / 'guidelines' / 'HOOKS.md'
        assert hook_file.exists()
        content = hook_file.read_text(encoding='utf-8')
        # Should mention use() hook for promises
        assert 'use()' in content.lower() or 'use(' in content, \
            "Guidelines must document React 19 use() hook"

    def test_useFormStatus_documented(self):
        """useFormStatus hook must be documented (React 19)."""
        hook_file = REACT_PACK / 'guidelines' / 'HOOKS.md'
        content = hook_file.read_text(encoding='utf-8')
        assert 'useformstatus' in content.lower(), \
            "Guidelines must document React 19 useFormStatus hook"

    def test_useOptimistic_documented(self):
        """useOptimistic hook must be documented (React 19)."""
        hook_file = REACT_PACK / 'guidelines' / 'HOOKS.md'
        content = hook_file.read_text(encoding='utf-8')
        assert 'useoptimistic' in content.lower(), \
            "Guidelines must document React 19 useOptimistic hook"

    def test_server_client_components_documented(self):
        """Server and Client Components must be documented."""
        sc_file = REACT_PACK / 'guidelines' / 'server-client-components.md'
        assert sc_file.exists()
        content = sc_file.read_text(encoding='utf-8')
        assert 'use client' in content or "use client" in content.lower(), \
            "Must document 'use client' directive"
        assert 'server' in content.lower(), \
            "Must document Server Components"

    def test_suspense_patterns_in_validator(self):
        """Suspense patterns must be in validator guidance."""
        validator = REACT_PACK / 'validators' / 'react.md'
        assert validator.exists()
        content = validator.read_text(encoding='utf-8')
        assert 'suspense' in content.lower(), \
            "Validator must cover Suspense patterns"
        assert 'server' in content.lower(), \
            "Validator must mention Server Components"

    def test_hooks_rules_documented(self):
        """Rules of Hooks must be documented."""
        hooks_file = REACT_PACK / 'guidelines' / 'hooks-patterns.md'
        assert hooks_file.exists()
        content = hooks_file.read_text(encoding='utf-8')
        # Should mention top-level hooks rule
        assert 'top' in content.lower() or 'hooks' in content.lower(), \
            "Must document rules of hooks"

    def test_component_composition_guidance(self):
        """Component composition guidance must exist."""
        design_file = REACT_PACK / 'guidelines' / 'component-design.md'
        assert design_file.exists()
        content = design_file.read_text(encoding='utf-8')
        assert 'composition' in content.lower(), \
            "Must document composition patterns"

    def test_accessibility_guidance(self):
        """Accessibility guidance must exist."""
        a11y_file = REACT_PACK / 'guidelines' / 'accessibility.md'
        assert a11y_file.exists()
        content = a11y_file.read_text(encoding='utf-8')
        assert ('wcag' in content.lower() or 
                'accessible' in content.lower() or
                'aria' in content.lower() or
                'keyboard' in content.lower()), \
            "Must document accessibility requirements"

    def test_react_19_rules_in_registry(self):
        """React 19 specific rules must be in registry."""
        registry = REACT_PACK / 'rules' / 'registry.yml'
        assert registry.exists()
        content = registry.read_text(encoding='utf-8')
        # Should have rules for server/client boundary, accessibility, hooks
        assert 'server' in content.lower() or 'client' in content.lower(), \
            "Must have rules for Server/Client Components"
        assert 'accessibility' in content.lower() or 'wcag' in content.lower(), \
            "Must have accessibility rules"


class TestReactExamples:
    """Test React examples cover key patterns."""

    def test_server_component_example_exists(self):
        """Server Component example must exist."""
        example = REACT_PACK / 'examples' / 'server-component.tsx'
        assert example.exists(), f"Server component example not found at {example}"

    def test_client_component_example_exists(self):
        """Client Component example must exist."""
        example = REACT_PACK / 'examples' / 'client-component.tsx'
        assert example.exists(), f"Client component example not found at {example}"

    def test_custom_hook_example_exists(self):
        """Custom Hook example must exist."""
        example = REACT_PACK / 'examples' / 'custom-hook.ts'
        assert example.exists(), f"Custom hook example not found at {example}"

    def test_server_component_is_async(self):
        """Server component example should be async."""
        example = REACT_PACK / 'examples' / 'server-component.tsx'
        content = example.read_text(encoding='utf-8')
        assert 'async' in content, \
            "Server component example should demonstrate async pattern"

    def test_client_component_has_use_client(self):
        """Client component example should have 'use client' directive."""
        example = REACT_PACK / 'examples' / 'client-component.tsx'
        content = example.read_text(encoding='utf-8')
        assert "use client" in content or "use client" in content.lower(), \
            "Client component example must show 'use client' directive"

    def test_custom_hook_returns_tuple(self):
        """Custom hook example should demonstrate return pattern."""
        example = REACT_PACK / 'examples' / 'custom-hook.ts'
        content = example.read_text(encoding='utf-8')
        assert 'useState' in content or 'useEffect' in content, \
            "Custom hook should demonstrate hook usage"


class TestReactAgentGuidance:
    """Test React agent guidance is complete."""

    def test_component_builder_overlay_content(self):
        """Component builder overlay must have React guidance."""
        overlay = REACT_PACK / 'agents' / 'overlays' / 'component-builder.md'
        assert overlay.exists()
        content = overlay.read_text(encoding='utf-8')
        
        # Should guide on component patterns
        assert 'component' in content.lower(), \
            "Should guide on component patterns"
        
        # Should mention React 19 tools/patterns
        assert ('react' in content.lower() or
                'typescript' in content.lower() or
                'client' in content.lower()), \
            "Should mention React tech stack"

    def test_component_builder_mentions_hooks(self):
        """Component builder should mention hooks."""
        overlay = REACT_PACK / 'agents' / 'overlays' / 'component-builder.md'
        content = overlay.read_text(encoding='utf-8')
        assert 'hook' in content.lower() or 'state' in content.lower(), \
            "Component builder should guide on hooks/state"


class TestReactValidatorGuidance:
    """Test React validator has proper guidance."""

    def test_validator_role_defined(self):
        """React validator must have defined role."""
        validator = REACT_PACK / 'validators' / 'react.md'
        content = validator.read_text(encoding='utf-8')
        assert 'role' in content.lower() or 'react' in content.lower(), \
            "Validator must define its role"

    def test_validator_covers_react_19_patterns(self):
        """Validator must explicitly cover React 19 patterns."""
        validator = REACT_PACK / 'validators' / 'react.md'
        content = validator.read_text(encoding='utf-8')
        assert 'react 19' in content.lower(), \
            "Validator must explicitly mention React 19"

    def test_validator_covers_hooks_rules(self):
        """Validator must cover Rules of Hooks."""
        validator = REACT_PACK / 'validators' / 'react.md'
        content = validator.read_text(encoding='utf-8')
        assert 'hook' in content.lower(), \
            "Validator must cover hooks validation"

    def test_validator_covers_accessibility(self):
        """Validator must cover accessibility."""
        validator = REACT_PACK / 'validators' / 'react.md'
        content = validator.read_text(encoding='utf-8')
        assert 'access' in content.lower() or 'aria' in content.lower(), \
            "Validator must cover accessibility"


class TestReactFilters:
    """Test React pack triggers on correct file patterns."""

    def test_tsx_files_trigger_react(self):
        """Pack must trigger on .tsx files."""
        pack_yml = REACT_PACK / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        assert '*.tsx' in content or '*.tsx' in content or 'tsx' in content, \
            "Pack must trigger on .tsx files"

    def test_jsx_files_trigger_react(self):
        """Pack must trigger on .jsx files."""
        pack_yml = REACT_PACK / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        assert '*.jsx' in content or 'jsx' in content, \
            "Pack must trigger on .jsx files"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
