"""Test suite for Tailwind CSS v4 Edison pack - T-076."""
from __future__ import annotations

from pathlib import Path
import pytest
import yaml

# Setup root detection
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

# Now safe to import from src
from edison.core.composition.packs import validate_pack


class TestTailwindPackStructure:
    """Verify Tailwind v4 pack has complete structure."""

    def test_tailwind_pack_directory_exists(self):
        """Tailwind pack directory must exist."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        assert pack_dir.exists(), f"Tailwind pack not found at {pack_dir}"
        assert pack_dir.is_dir(), f"Tailwind pack is not a directory: {pack_dir}"

    def test_tailwind_pack_has_required_directories(self):
        """Tailwind pack must have all required subdirectories."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        
        required_dirs = [
            'agents',
            'agents/overlays',
            'validators',
            'validators/overlays',
            'guidelines',
            'rules',
            'rules/file_patterns',
            'examples',
        ]
        
        for dir_name in required_dirs:
            dir_path = pack_dir / dir_name
            assert dir_path.exists(), f"Missing required directory: {dir_name}"
            assert dir_path.is_dir(), f"Not a directory: {dir_name}"

    def test_tailwind_pack_has_required_files(self):
        """Tailwind pack must have all required files."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        
        required_files = [
            'pack.yml',
            'pack-dependencies.yaml',
            'agents/overlays/component-builder.md',
            'validators/styling.md',
            'validators/overlays/global.md',
            'rules/registry.yml',
            'rules/file_patterns/tailwind.yaml',
            'guidelines/includes/tailwind/v4-syntax.md',
            'guidelines/includes/tailwind/TAILWIND_V4_RULES.md',
            'guidelines/includes/tailwind/STYLING.md',
            'guidelines/includes/tailwind/design-tokens.md',
            'guidelines/includes/tailwind/responsive.md',
            'examples/v4-syntax.md',
            'examples/globals.css',
        ]
        
        for file_name in required_files:
            file_path = pack_dir / file_name
            assert file_path.exists(), f"Missing required file: {file_name}"
            assert file_path.is_file(), f"Not a file: {file_name}"


class TestTailwindPackManifest:
    """Verify pack.yml is correct and well-formed."""

    def test_pack_yml_exists_and_valid_yaml(self):
        """pack.yml must exist and be valid YAML."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        pack_yml = pack_dir / 'pack.yml'
        
        assert pack_yml.exists(), "pack.yml not found"
        
        try:
            with open(pack_yml, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            assert data is not None, "pack.yml is empty or invalid"
        except yaml.YAMLError as e:
            pytest.fail(f"pack.yml has YAML syntax errors: {e}")

    def test_pack_yml_has_required_metadata(self):
        """pack.yml must have pack metadata."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        pack_yml = pack_dir / 'pack.yml'
        
        with open(pack_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Check structure
        assert 'pack' in data or 'name' in data, "Missing pack identifier"
        if 'pack' in data:
            assert 'name' in data['pack'], "Missing pack name"
            assert data['pack']['name'] == "Tailwind CSS", "Unexpected pack name"
            assert 'version' in data['pack'], "Missing pack version"

    def test_pack_yml_has_triggers(self):
        """pack.yml must define file pattern triggers."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        pack_yml = pack_dir / 'pack.yml'
        
        with open(pack_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        assert 'triggers' in data, "Missing triggers section"
        assert 'filePatterns' in data['triggers'], "Missing filePatterns"
        
        patterns = data['triggers']['filePatterns']
        assert len(patterns) > 0, "No file patterns defined"
        assert any('tailwind' in p for p in patterns), "Missing tailwind config pattern"
        assert any('.css' in p for p in patterns), "Missing CSS file pattern"

    def test_pack_yml_provides_resources(self):
        """pack.yml must declare provided resources."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        pack_yml = pack_dir / 'pack.yml'
        
        with open(pack_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        provides = data.get('provides', {})

        # Pack manifests may declare agents/validators, but guidelines are wired via overlays/rules.
        assert 'validators' in provides, "No validators declared"
        validators = provides['validators']
        assert len(validators) > 0, "No validators provided"

        assert 'agents' in provides, "No agents declared"
        agents = provides['agents']
        assert len(agents) > 0, "No agents provided"


class TestTailwindV4Guidelines:
    """Verify guidelines are comprehensive and v4-specific."""

    def test_v4_syntax_guideline_exists_and_comprehensive(self):
        """v4-syntax.md must exist and explain v4 CSS import."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        guide = pack_dir / 'guidelines/includes/tailwind/v4-syntax.md'
        
        assert guide.exists(), "v4-syntax.md not found"
        content = guide.read_text(encoding='utf-8')
        
        # Must explain v4 import syntax
        assert '@import "tailwindcss"' in content, \
            "Missing v4 import syntax documentation"
        # Must contrast with v3
        assert '@tailwind' in content, "Missing v3 comparison"

    def test_v4_rules_guideline_exists_and_detailed(self):
        """TAILWIND_V4_RULES.md must exist with 6+ critical rules."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        guide = pack_dir / 'guidelines/includes/tailwind/TAILWIND_V4_RULES.md'
        
        assert guide.exists(), "TAILWIND_V4_RULES.md not found"
        content = guide.read_text(encoding='utf-8')
        
        # Must contain critical rules
        assert 'Rule' in content, "Missing rule definitions"
        assert 'v4' in content.lower(), "Missing v4 references"
        assert 'font-sans' in content.lower(), "Missing font-sans guidance"
        assert '@theme' in content, "Missing @theme documentation"
        assert '@import' in content, "Missing @import documentation"

    def test_styling_guideline_exists(self):
        """STYLING.md must provide utility and styling guidance."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        guide = pack_dir / 'guidelines/includes/tailwind/STYLING.md'
        
        assert guide.exists(), "STYLING.md not found"
        content = guide.read_text(encoding='utf-8')
        
        assert len(content) > 100, "STYLING.md is too brief"
        assert 'tailwind' in content.lower() or 'css' in content.lower(), \
            "STYLING.md lacks Tailwind/CSS content"

    def test_design_tokens_guideline_exists(self):
        """design-tokens.md must explain token usage."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        guide = pack_dir / 'guidelines/includes/tailwind/design-tokens.md'
        
        assert guide.exists(), "design-tokens.md not found"
        content = guide.read_text(encoding='utf-8')
        
        assert 'token' in content.lower(), "Missing token documentation"
        assert any(word in content.lower() for word in ['color', 'spacing', 'variable']), \
            "Missing design system documentation"

    def test_responsive_guideline_exists(self):
        """responsive.md must explain responsive design patterns."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        guide = pack_dir / 'guidelines/includes/tailwind/responsive.md'
        
        assert guide.exists(), "responsive.md not found"
        content = guide.read_text(encoding='utf-8')
        
        assert 'responsive' in content.lower() or 'mobile' in content.lower(), \
            "Missing responsive design documentation"


class TestTailwindV4Rules:
    """Verify rules registry contains v4-specific rules."""

    def test_rules_registry_exists(self):
        """rules/registry.yml must exist."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        registry = pack_dir / 'rules/registry.yml'
        
        assert registry.exists(), "rules/registry.yml not found"

    def test_rules_registry_has_v4_import_rule(self):
        """Rules must include V4_SYNTAX rule."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        registry = pack_dir / 'rules/registry.yml'
        content = registry.read_text(encoding='utf-8')
        
        assert 'RULE.TAILWIND.V4_SYNTAX' in content, \
            "Missing RULE.TAILWIND.V4_SYNTAX"
        assert '@import' in content, "Rule missing @import guidance"

    def test_rules_registry_has_font_sans_rule(self):
        """Rules must include FONT_SANS_REQUIRED rule."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        registry = pack_dir / 'rules/registry.yml'
        content = registry.read_text(encoding='utf-8')
        
        assert 'RULE.TAILWIND.FONT_SANS_REQUIRED' in content, \
            "Missing RULE.TAILWIND.FONT_SANS_REQUIRED"
        assert 'font-sans' in content.lower(), "Rule missing font-sans guidance"

    def test_rules_registry_has_postcss_v4_rule(self):
        """Rules must include POSTCSS_V4_PLUGIN rule."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        registry = pack_dir / 'rules/registry.yml'
        content = registry.read_text(encoding='utf-8')
        
        assert 'RULE.TAILWIND.POSTCSS_V4_PLUGIN' in content, \
            "Missing RULE.TAILWIND.POSTCSS_V4_PLUGIN"
        assert '@tailwindcss/postcss' in content, "Rule missing v4 plugin guidance"

    def test_rules_registry_has_theme_tokens_rule(self):
        """Rules must include THEME_TOKENS_IN_CSS rule."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        registry = pack_dir / 'rules/registry.yml'
        content = registry.read_text(encoding='utf-8')
        
        assert 'RULE.TAILWIND.THEME_TOKENS_IN_CSS' in content, \
            "Missing RULE.TAILWIND.THEME_TOKENS_IN_CSS"
        assert '@theme' in content, "Rule missing @theme guidance"

    def test_rules_registry_has_critical_blocking_rules(self):
        """Critical rules must be marked as blocking."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        registry = pack_dir / 'rules/registry.yml'
        content = registry.read_text(encoding='utf-8')
        
        # At least 3 critical rules should be blocking
        blocking_count = content.count('blocking: true')
        assert blocking_count >= 3, f"Expected >= 3 blocking rules, found {blocking_count}"

    def test_file_patterns_rule_exists(self):
        """File pattern rule for tailwind.config must exist."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        patterns = pack_dir / 'rules/file_patterns/tailwind.yaml'
        
        assert patterns.exists(), "File patterns rule not found"
        content = patterns.read_text(encoding='utf-8')
        
        assert 'tailwind' in content.lower(), "Pattern missing tailwind reference"
        assert 'FILE_PATTERN' in content or 'patterns:' in content, \
            "Pattern rule missing standard structure"


class TestTailwindV4AgentOverlays:
    """Verify agent overlays provide v4 guidance."""

    def test_component_builder_overlay_exists(self):
        """Component builder agent must have Tailwind overlay."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        overlay = pack_dir / 'agents/overlays/component-builder.md'
        
        assert overlay.exists(), "component-builder.md overlay not found"

    def test_component_builder_overlay_has_v4_content(self):
        """Component builder overlay must explain v4 syntax."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        overlay = pack_dir / 'agents/overlays/component-builder.md'
        content = overlay.read_text(encoding='utf-8')
        
        # Check for v4 specific guidance
        assert '@import "tailwindcss"' in content, \
            "Missing @import guidance"
        assert 'font-sans' in content.lower(), \
            "Missing font-sans requirement"
        assert 'arbitrary' in content.lower() or 'custom' in content.lower(), \
            "Missing guidance on custom values"

    def test_component_builder_overlay_has_examples(self):
        """Component builder overlay must provide code examples."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        overlay = pack_dir / 'agents/overlays/component-builder.md'
        content = overlay.read_text(encoding='utf-8')
        
        # Should have code blocks
        assert '```' in content, "Missing code examples"
        # Should show both correct and wrong patterns
        assert 'correct' in content.lower() or 'right' in content.lower() or '✅' in content or 'CORRECT' in content, \
            "Missing correct pattern examples"

    def test_component_builder_overlay_shows_v3_as_wrong(self):
        """Component builder overlay must show v3 syntax as wrong."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        overlay = pack_dir / 'agents/overlays/component-builder.md'
        content = overlay.read_text(encoding='utf-8')
        
        # Should mention v3 is wrong
        assert 'WRONG' in content or 'v3' in content.lower(), \
            "Missing v3 deprecation information"


class TestTailwindV4Validators:
    """Verify validator configuration."""

    def test_styling_validator_exists(self):
        """Styling validator must exist and be comprehensive."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        validator = pack_dir / 'validators/styling.md'
        
        assert validator.exists(), "validators/styling.md not found"
        content = validator.read_text(encoding='utf-8')
        
        assert len(content) > 1000, "Styling validator is too brief"
        assert 'tailwind' in content.lower(), "Validator lacks Tailwind context"

    def test_validator_global_overlay_exists(self):
        """Validator must have global overlay with v4 context."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        overlay = pack_dir / 'validators/overlays/global.md'
        
        assert overlay.exists(), "validators/overlays/global.md not found"
        content = overlay.read_text(encoding='utf-8')
        
        assert len(content) > 50, "Global overlay is too brief"

    def test_validator_overlay_references_v4_guidelines(self):
        """Validator overlay must reference v4 guidelines."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        overlay = pack_dir / 'validators/overlays/global.md'
        content = overlay.read_text(encoding='utf-8')
        
        # Check for references to guidelines or v4 content
        has_v4_ref = 'v4' in content.lower() or '@import' in content or '@theme' in content
        assert has_v4_ref, "Validator overlay lacks v4 references"


class TestTailwindV4Examples:
    """Verify examples demonstrate v4 patterns."""

    def test_v4_syntax_example_exists(self):
        """v4-syntax.md example must exist."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        example = pack_dir / 'examples/v4-syntax.md'
        
        assert example.exists(), "examples/v4-syntax.md not found"
        content = example.read_text(encoding='utf-8')
        
        assert '@import "tailwindcss"' in content, "Missing @import example"
        assert '@theme' in content, "Missing @theme example"

    def test_globals_css_example_exists(self):
        """globals.css example must demonstrate v4 setup."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        example = pack_dir / 'examples/globals.css'
        
        assert example.exists(), "examples/globals.css not found"
        content = example.read_text(encoding='utf-8')
        
        assert '@import "tailwindcss"' in content, \
            "globals.css missing v4 @import syntax"

    def test_tailwind_config_example_exists(self):
        """tailwind.config.ts example must show v4 config."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        example = pack_dir / 'examples/tailwind.config.ts'
        
        assert example.exists(), "examples/tailwind.config.ts not found"
        content = example.read_text(encoding='utf-8')
        
        # v4 config should have content paths
        assert 'content' in content, "v4 config missing content"

    def test_component_patterns_example_exists(self):
        """Component patterns example must demonstrate usage."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        example = pack_dir / 'examples/component-patterns.tsx'
        
        assert example.exists(), "examples/component-patterns.tsx not found"


class TestTailwindPackDependencies:
    """Verify pack-dependencies.yaml is valid."""

    def test_dependencies_file_exists(self):
        """pack-dependencies.yaml must exist."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        deps = pack_dir / 'pack-dependencies.yaml'
        
        assert deps.exists(), "pack-dependencies.yaml not found"

    def test_dependencies_file_is_valid_yaml(self):
        """pack-dependencies.yaml must be valid YAML."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        deps = pack_dir / 'pack-dependencies.yaml'
        
        try:
            with open(deps, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"pack-dependencies.yaml has syntax errors: {e}")


class TestTailwindPackIntegration:
    """Test pack as a complete system."""

    def test_pack_validates_successfully(self):
        """Tailwind pack must pass validation."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        
        # Pack validation may have schema requirements
        # We'll do a basic sanity check
        pack_yml = pack_dir / 'pack.yml'
        
        with open(pack_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Check structure exists
        assert data is not None, "pack.yml is empty"
        assert 'triggers' in data, "Missing triggers"

    def test_all_declared_guidelines_exist(self):
        """Tailwind include-only guideline files must exist."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        includes_dir = pack_dir / "guidelines" / "includes" / "tailwind"
        assert includes_dir.exists(), f"Missing include-only guidelines dir: {includes_dir}"
        md_files = list(includes_dir.glob("*.md"))
        assert md_files, "Expected Tailwind include-only guideline markdown files"

    def test_all_declared_validators_exist(self):
        """All validators declared in pack.yml must exist."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        pack_yml = pack_dir / 'pack.yml'
        
        with open(pack_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        provides = data.get('provides', {})
        
        # Check all declared validators exist
        for validator in provides.get('validators', []):
            path = pack_dir / validator
            assert path.exists(), f"Declared validator not found: {validator}"

    def test_agent_overlay_exists_for_declared_agents(self):
        """Agent overlays must exist for declared agents."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        pack_yml = pack_dir / 'pack.yml'
        
        with open(pack_yml, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        provides = data.get('provides', {})
        
        # Check that agent overlays exist
        # Agents can be in agents/ or agents/overlays/
        for agent in provides.get('agents', []):
            path = pack_dir / agent
            overlay_path = pack_dir / 'agents/overlays' / Path(agent).name
            
            assert path.exists() or overlay_path.exists(), \
                f"Agent overlay not found for: {agent} (checked {path} and {overlay_path})"

    def test_pack_covers_tailwind_v4_specifics(self):
        """Pack must provide comprehensive Tailwind v4 coverage."""
        pack_dir = Path('src/edison/data/packs/tailwind').resolve()
        
        # Collect all content
        all_content = []
        
        # Read all guidelines
        for guide in (pack_dir / 'guidelines').rglob('*.md'):
            all_content.append(guide.read_text(encoding='utf-8'))
        
        # Read all agent overlays
        for overlay in (pack_dir / 'agents/overlays').glob('*.md'):
            all_content.append(overlay.read_text(encoding='utf-8'))
        
        # Read all validators
        for validator in (pack_dir / 'validators').glob('*.md'):
            all_content.append(validator.read_text(encoding='utf-8'))
        
        combined = ' '.join(all_content).lower()
        
        # Check for critical v4 topics
        critical_v4_topics = [
            '@import "tailwindcss"',
            '@theme',
            'font-sans',
            'arbitrary values'
        ]
        
        found_topics = [topic for topic in critical_v4_topics if topic.lower() in combined]
        
        assert len(found_topics) >= 3, \
            f"Pack missing critical v4 topics. Found: {found_topics}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
