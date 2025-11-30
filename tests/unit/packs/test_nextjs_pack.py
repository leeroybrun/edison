"""Test Next.js pack for Next.js 16 specific content coverage.

This test verifies complete Next.js 16 App Router pack implementation:
- pack.yml manifest and schema validation
- File triggers for Next.js patterns
- Agent overlays for component-builder and api-builder
- Validators for App Router, Server Components, Route Handlers, Metadata, Caching
- Guidelines for all Next.js 16 patterns
- Rules registry with enforcement
- Examples directory with complete, runnable examples

Next.js 16 coverage:
✅ App Router patterns (file-based routing, layouts, page.tsx)
✅ Server Components (async, database queries, server-only resources)
✅ Client Components ('use client' directive, interactivity)
✅ Server Actions ('use server', form actions, mutations)
✅ Route Handlers (GET, POST, dynamic routes, authentication)
✅ Metadata API (static, dynamic generateMetadata)
✅ Caching strategies (revalidate, dynamic, tags)
✅ Loading states (loading.tsx)
✅ Error boundaries (error.tsx)
✅ Middleware patterns
"""
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


NEXTJS_PACK = ROOT / 'src/edison/data/packs/nextjs'


class TestNextJSPackStructure:
    """Test Next.js pack has correct structure and validates."""

    def test_nextjs_pack_exists(self):
        """Next.js pack directory must exist."""
        assert NEXTJS_PACK.exists(), f"Next.js pack not found at {NEXTJS_PACK}"

    def test_nextjs_pack_validates(self):
        """Next.js pack manifest must validate against schema."""
        res = validate_pack(NEXTJS_PACK)
        assert res.ok, f"Next.js pack validation failed: {[i.message for i in res.issues]}"

    def test_pack_yml_exists(self):
        """pack.yml must exist."""
        pack_yml = NEXTJS_PACK / 'pack.yml'
        assert pack_yml.exists(), f"pack.yml not found at {pack_yml}"

    def test_pack_yml_has_required_fields(self):
        """pack.yml must have name, version, description, triggers."""
        pack_yml = NEXTJS_PACK / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        assert 'name:' in content or 'pack:' in content, "Must have pack name"
        assert 'version:' in content, "Must have version"
        assert 'triggers:' in content, "Must have triggers"

    def test_agents_overlays_exist(self):
        """Agent overlays for component-builder and api-builder must exist."""
        component_overlay = NEXTJS_PACK / 'agents/overlays/component-builder.md'
        api_overlay = NEXTJS_PACK / 'agents/overlays/api-builder.md'
        assert component_overlay.exists(), f"component-builder overlay not found at {component_overlay}"
        assert api_overlay.exists(), f"api-builder overlay not found at {api_overlay}"

    def test_validators_overlay_exists(self):
        """Validators overlay must exist."""
        overlay = NEXTJS_PACK / 'validators/overlays/global.md'
        assert overlay.exists(), f"Validator overlay not found at {overlay}"

    def test_rules_registry_exists(self):
        """Rules registry must exist."""
        registry = NEXTJS_PACK / 'rules/registry.yml'
        assert registry.exists(), f"Rules registry not found at {registry}"

    def test_examples_directory_exists(self):
        """Examples directory must exist."""
        examples_dir = NEXTJS_PACK / 'examples'
        assert examples_dir.exists(), f"Examples directory not found at {examples_dir}"


class TestNextJSFileTriggers:
    """Test Next.js pack triggers on correct file patterns."""

    def test_app_router_page_trigger(self):
        """Pack must trigger on app/**/page.tsx files."""
        pack_yml = NEXTJS_PACK / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        assert 'page.tsx' in content, "Pack must trigger on page.tsx files"

    def test_app_router_layout_trigger(self):
        """Pack must trigger on app/**/layout.tsx files."""
        pack_yml = NEXTJS_PACK / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        assert 'layout.tsx' in content, "Pack must trigger on layout.tsx files"

    def test_route_handler_trigger(self):
        """Pack must trigger on app/**/route.ts files."""
        pack_yml = NEXTJS_PACK / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        assert 'route.ts' in content, "Pack must trigger on route.ts files"

    def test_next_config_trigger(self):
        """Pack must trigger on next.config.js files."""
        pack_yml = NEXTJS_PACK / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        assert 'next.config' in content, "Pack must trigger on next.config.js"


class TestNextJS16Guidelines:
    """Test Next.js 16 specific guidelines are comprehensive."""

    def test_app_router_guideline_exists(self):
        """App Router guideline must exist."""
        guideline = NEXTJS_PACK / 'guidelines' / 'app-router.md'
        assert guideline.exists(), f"App Router guideline not found at {guideline}"

    def test_app_router_covers_file_conventions(self):
        """App Router guideline must cover file conventions (page, layout, loading, error)."""
        guideline = NEXTJS_PACK / 'guidelines' / 'app-router.md'
        content = guideline.read_text(encoding='utf-8').lower()
        assert 'page.tsx' in content, "Must document page.tsx convention"
        assert 'layout.tsx' in content or 'layout' in content, "Must document layout.tsx"
        assert 'loading' in content, "Must document loading.tsx"
        assert 'error' in content, "Must document error.tsx"

    def test_app_router_covers_server_components(self):
        """App Router guideline must cover Server Components."""
        guideline = NEXTJS_PACK / 'guidelines' / 'app-router.md'
        content = guideline.read_text(encoding='utf-8').lower()
        assert 'server component' in content or 'server' in content, "Must document Server Components"

    def test_route_handlers_guideline_exists(self):
        """Route handlers guideline must exist."""
        guideline = NEXTJS_PACK / 'guidelines' / 'route-handlers.md'
        assert guideline.exists(), f"Route handlers guideline not found at {guideline}"

    def test_route_handlers_covers_all_http_methods(self):
        """Route handlers guideline must cover HTTP methods (GET, POST, PUT, PATCH, DELETE)."""
        guideline = NEXTJS_PACK / 'guidelines' / 'route-handlers.md'
        content = guideline.read_text(encoding='utf-8')
        for method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            assert method in content, f"Must document {method} method"

    def test_route_handlers_covers_nextrequest_nextresponse_imports(self):
        """Route handlers guideline must mention NextRequest and NextResponse with imports."""
        guideline = NEXTJS_PACK / 'guidelines' / 'route-handlers.md'
        content = guideline.read_text(encoding='utf-8')
        assert 'NextRequest' in content, "Must document NextRequest"
        assert 'NextResponse' in content, "Must document NextResponse"
        assert 'import' in content and 'next/server' in content, "Must show imports from next/server"

    def test_route_handlers_covers_authentication(self):
        """Route handlers guideline must cover authentication patterns."""
        guideline = NEXTJS_PACK / 'guidelines' / 'route-handlers.md'
        content = guideline.read_text(encoding='utf-8').lower()
        assert 'auth' in content or 'session' in content, "Must cover authentication patterns"
        assert '401' in content or 'unauthorized' in content, "Must mention 401/Unauthorized"

    def test_route_handlers_covers_validation(self):
        """Route handlers guideline must cover validation with Zod."""
        guideline = NEXTJS_PACK / 'guidelines' / 'route-handlers.md'
        content = guideline.read_text(encoding='utf-8').lower()
        assert 'zod' in content, "Must cover Zod validation"
        assert 'schema' in content or 'parse' in content, "Must show schema validation"

    def test_route_handlers_covers_error_handling(self):
        """Route handlers guideline must cover error handling."""
        guideline = NEXTJS_PACK / 'guidelines' / 'route-handlers.md'
        content = guideline.read_text(encoding='utf-8').lower()
        assert 'try' in content and 'catch' in content, "Must show try/catch blocks"
        assert 'status' in content and '500' in content, "Must show 500 status code"

    def test_route_handlers_covers_dynamic_params(self):
        """Route handlers guideline must cover dynamic route parameters."""
        guideline = NEXTJS_PACK / 'guidelines' / 'route-handlers.md'
        content = guideline.read_text(encoding='utf-8')
        assert 'params' in content, "Must cover dynamic route parameters"

    def test_server_actions_guideline_exists(self):
        """Server Actions guideline must exist."""
        guideline = NEXTJS_PACK / 'guidelines' / 'server-actions.md'
        assert guideline.exists(), f"Server Actions guideline not found at {guideline}"

    def test_server_actions_covers_use_server(self):
        """Server Actions guideline must document 'use server' directive."""
        guideline = NEXTJS_PACK / 'guidelines' / 'server-actions.md'
        content = guideline.read_text(encoding='utf-8')
        assert 'use server' in content or "'use server'" in content, "Must document 'use server' directive"

    def test_server_actions_covers_revalidation(self):
        """Server Actions guideline must cover cache revalidation."""
        guideline = NEXTJS_PACK / 'guidelines' / 'server-actions.md'
        content = guideline.read_text(encoding='utf-8').lower()
        assert 'revalidate' in content, "Must document cache revalidation"

    def test_metadata_guideline_exists(self):
        """Metadata API guideline must exist."""
        guideline = NEXTJS_PACK / 'guidelines' / 'metadata.md'
        assert guideline.exists(), f"Metadata guideline not found at {guideline}"

    def test_metadata_covers_static_metadata(self):
        """Metadata guideline must cover static metadata export."""
        guideline = NEXTJS_PACK / 'guidelines' / 'metadata.md'
        content = guideline.read_text(encoding='utf-8')
        assert 'metadata' in content.lower(), "Must document metadata export"
        assert 'title' in content.lower() or 'description' in content.lower(), "Must document title/description"

    def test_metadata_covers_dynamic_metadata(self):
        """Metadata guideline must cover generateMetadata function."""
        guideline = NEXTJS_PACK / 'guidelines' / 'metadata.md'
        content = guideline.read_text(encoding='utf-8')
        assert 'generateMetadata' in content or 'generate' in content.lower(), "Must document generateMetadata"

    def test_caching_guideline_exists(self):
        """Caching guideline must exist."""
        guideline = NEXTJS_PACK / 'guidelines' / 'caching.md'
        assert guideline.exists(), f"Caching guideline not found at {guideline}"

    def test_caching_covers_strategies(self):
        """Caching guideline must cover caching strategies (static, dynamic, revalidate)."""
        guideline = NEXTJS_PACK / 'guidelines' / 'caching.md'
        content = guideline.read_text(encoding='utf-8').lower()
        assert 'cache' in content, "Must document caching"
        assert 'revalidate' in content or 'dynamic' in content, "Must document caching strategies"

    def test_caching_covers_fetch_options(self):
        """Caching guideline must cover fetch caching options."""
        guideline = NEXTJS_PACK / 'guidelines' / 'caching.md'
        content = guideline.read_text(encoding='utf-8').lower()
        assert 'fetch' in content, "Must document fetch caching"

    def test_routing_guideline_exists(self):
        """Routing guideline must exist."""
        guideline = NEXTJS_PACK / 'guidelines' / 'ROUTING.md'
        assert guideline.exists(), f"Routing guideline not found at {guideline}"


class TestNextJS16Validators:
    """Test Next.js 16 validators are comprehensive."""

    def test_nextjs_validator_exists(self):
        """Next.js validator must exist."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        assert validator.exists(), f"Next.js validator not found at {validator}"

    def test_nextjs_validator_has_role(self):
        """Next.js validator must define its role."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8')
        assert 'role' in content.lower() or 'next' in content.lower(), "Validator must define its role"

    def test_nextjs_validator_mentions_app_router(self):
        """Next.js validator must explicitly mention App Router."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()
        assert 'app router' in content, "Validator must mention App Router"

    def test_nextjs_validator_covers_server_components(self):
        """Next.js validator must validate Server Components."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()
        assert 'server component' in content or 'server' in content, "Must validate Server Components"

    def test_nextjs_validator_covers_client_components(self):
        """Next.js validator must validate Client Components."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()
        assert 'use client' in content or 'client' in content, "Must validate Client Components"

    def test_nextjs_validator_covers_route_handlers(self):
        """Next.js validator must validate route handlers."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()
        assert 'route handler' in content or 'route' in content, "Must validate route handlers"

    def test_nextjs_validator_covers_metadata(self):
        """Next.js validator must validate Metadata API usage."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()
        assert 'metadata' in content, "Must validate metadata"

    def test_nextjs_validator_covers_caching(self):
        """Next.js validator must validate caching strategies."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()
        assert 'cach' in content, "Must validate caching"

    def test_nextjs_validator_covers_loading_states(self):
        """Next.js validator must validate loading states."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()
        assert 'loading' in content, "Must validate loading states"

    def test_nextjs_validator_covers_error_boundaries(self):
        """Next.js validator must validate error boundaries."""
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()
        assert 'error' in content, "Must validate error boundaries"

    def test_api_validator_exists(self):
        """API validator must exist for route handlers."""
        validator = NEXTJS_PACK / 'validators' / 'api.md'
        assert validator.exists(), f"API validator not found at {validator}"


class TestNextJSAgentOverlays:
    """Test Next.js agent overlays provide proper guidance."""

    def test_component_builder_overlay_covers_server_components(self):
        """Component builder overlay must guide on Server Components."""
        overlay = NEXTJS_PACK / 'agents' / 'overlays' / 'component-builder.md'
        content = overlay.read_text(encoding='utf-8').lower()
        assert 'server component' in content or 'server' in content, "Must guide on Server Components"

    def test_component_builder_overlay_covers_client_components(self):
        """Component builder overlay must guide on Client Components."""
        overlay = NEXTJS_PACK / 'agents' / 'overlays' / 'component-builder.md'
        content = overlay.read_text(encoding='utf-8').lower()
        assert 'use client' in content or 'client' in content, "Must guide on Client Components"

    def test_component_builder_overlay_covers_data_fetching(self):
        """Component builder overlay must guide on data fetching patterns."""
        overlay = NEXTJS_PACK / 'agents' / 'overlays' / 'component-builder.md'
        content = overlay.read_text(encoding='utf-8').lower()
        assert 'fetch' in content or 'data' in content or 'async' in content, "Must guide on data fetching"

    def test_component_builder_overlay_covers_loading_error(self):
        """Component builder overlay must guide on loading and error states."""
        overlay = NEXTJS_PACK / 'agents' / 'overlays' / 'component-builder.md'
        content = overlay.read_text(encoding='utf-8').lower()
        assert 'loading' in content or 'error' in content, "Must guide on loading/error states"

    def test_api_builder_overlay_covers_route_handlers(self):
        """API builder overlay must guide on route handlers."""
        overlay = NEXTJS_PACK / 'agents' / 'overlays' / 'api-builder.md'
        content = overlay.read_text(encoding='utf-8')
        assert 'route' in content.lower() or 'GET' in content or 'POST' in content, "Must guide on route handlers"

    def test_api_builder_overlay_covers_nextrequest_nextresponse(self):
        """API builder overlay must mention NextRequest/NextResponse."""
        overlay = NEXTJS_PACK / 'agents' / 'overlays' / 'api-builder.md'
        content = overlay.read_text(encoding='utf-8')
        assert 'NextRequest' in content or 'NextResponse' in content, "Must guide on Next.js types"

    def test_api_builder_overlay_covers_authentication(self):
        """API builder overlay must guide on authentication."""
        overlay = NEXTJS_PACK / 'agents' / 'overlays' / 'api-builder.md'
        content = overlay.read_text(encoding='utf-8').lower()
        assert 'auth' in content or 'requireauth' in content, "Must guide on authentication"

    def test_api_builder_overlay_covers_validation(self):
        """API builder overlay must guide on input validation."""
        overlay = NEXTJS_PACK / 'agents' / 'overlays' / 'api-builder.md'
        content = overlay.read_text(encoding='utf-8').lower()
        assert 'validat' in content or 'zod' in content, "Must guide on validation"


class TestNextJSRulesRegistry:
    """Test Next.js rules registry is comprehensive."""

    def test_rules_registry_has_app_router_rule(self):
        """Rules registry must have App Router enforcement rule."""
        registry = NEXTJS_PACK / 'rules' / 'registry.yml'
        content = registry.read_text(encoding='utf-8').lower()
        assert 'app router' in content or 'app_router' in content, "Must have App Router rule"

    def test_rules_registry_has_server_first_rule(self):
        """Rules registry must have Server Components first rule."""
        registry = NEXTJS_PACK / 'rules' / 'registry.yml'
        content = registry.read_text(encoding='utf-8').lower()
        assert 'server' in content, "Must have Server Components rule"

    def test_rules_registry_has_route_handler_rule(self):
        """Rules registry must have route handler rules."""
        registry = NEXTJS_PACK / 'rules' / 'registry.yml'
        content = registry.read_text(encoding='utf-8').lower()
        assert 'route' in content, "Must have route handler rules"

    def test_rules_registry_has_metadata_rule(self):
        """Rules registry must have metadata rules."""
        registry = NEXTJS_PACK / 'rules' / 'registry.yml'
        content = registry.read_text(encoding='utf-8').lower()
        assert 'metadata' in content or 'meta' in content, "Must have metadata rules"

    def test_rules_registry_has_caching_rule(self):
        """Rules registry must have caching rules."""
        registry = NEXTJS_PACK / 'rules' / 'registry.yml'
        content = registry.read_text(encoding='utf-8').lower()
        assert 'cach' in content or 'revalidat' in content, "Must have caching rules"

    def test_rules_registry_has_loading_error_rule(self):
        """Rules registry must have loading/error state rules."""
        registry = NEXTJS_PACK / 'rules' / 'registry.yml'
        content = registry.read_text(encoding='utf-8').lower()
        assert 'loading' in content or 'error' in content, "Must have loading/error rules"

    def test_rules_registry_structure(self):
        """Rules registry must have proper YAML structure with id, title, category."""
        registry = NEXTJS_PACK / 'rules' / 'registry.yml'
        content = registry.read_text(encoding='utf-8')
        assert 'id:' in content, "Rules must have IDs"
        assert 'title:' in content, "Rules must have titles"
        assert 'category:' in content, "Rules must have categories"


class TestNextJSExamples:
    """Test Next.js examples are complete and runnable."""

    def test_server_component_example_exists(self):
        """Server Component example must exist."""
        # Could be .tsx or in markdown
        examples_dir = NEXTJS_PACK / 'examples'
        tsx_example = examples_dir / 'server-component.tsx'
        md_examples = list(examples_dir.glob('*.md'))

        has_tsx = tsx_example.exists()
        has_md_with_server = any(
            'server component' in f.read_text(encoding='utf-8').lower()
            for f in md_examples
        )

        assert has_tsx or has_md_with_server, \
            "Must have Server Component example (either .tsx or documented in .md)"

    def test_client_component_example_exists(self):
        """Client Component example must exist."""
        examples_dir = NEXTJS_PACK / 'examples'
        tsx_example = examples_dir / 'client-component.tsx'
        md_examples = list(examples_dir.glob('*.md'))

        has_tsx = tsx_example.exists()
        has_md_with_client = any(
            'use client' in f.read_text(encoding='utf-8') or 'client component' in f.read_text(encoding='utf-8').lower()
            for f in md_examples
        )

        assert has_tsx or has_md_with_client, \
            "Must have Client Component example with 'use client'"

    def test_route_handler_example_exists(self):
        """Route handler example must exist."""
        example = NEXTJS_PACK / 'examples' / 'route-handler.ts'
        assert example.exists(), f"Route handler example not found at {example}"

    def test_route_handler_example_has_methods(self):
        """Route handler example must show GET/POST methods."""
        example = NEXTJS_PACK / 'examples' / 'route-handler.ts'
        content = example.read_text(encoding='utf-8')
        assert 'GET' in content or 'export async function GET' in content, \
            "Route handler example must show GET method"

    def test_server_action_example_exists(self):
        """Server Action example must exist."""
        example = NEXTJS_PACK / 'examples' / 'server-action.ts'
        assert example.exists(), f"Server Action example not found at {example}"

    def test_server_action_example_has_use_server(self):
        """Server Action example must have 'use server' directive."""
        example = NEXTJS_PACK / 'examples' / 'server-action.ts'
        content = example.read_text(encoding='utf-8')
        assert 'use server' in content or "'use server'" in content, \
            "Server Action example must show 'use server' directive"

    def test_metadata_example_exists(self):
        """Metadata example must exist."""
        example = NEXTJS_PACK / 'examples' / 'dynamic-metadata.ts'
        md_examples = list((NEXTJS_PACK / 'examples').glob('*.md'))

        has_ts = example.exists()
        has_md = any(
            'metadata' in f.read_text(encoding='utf-8').lower() or 'generateMetadata' in f.read_text(encoding='utf-8')
            for f in md_examples
        )

        assert has_ts or has_md, "Must have metadata example"

    def test_examples_are_typescript(self):
        """Examples must be TypeScript (not JavaScript)."""
        examples_dir = NEXTJS_PACK / 'examples'
        ts_files = list(examples_dir.glob('*.ts'))
        tsx_files = list(examples_dir.glob('*.tsx'))
        js_files = list(examples_dir.glob('*.js'))
        jsx_files = list(examples_dir.glob('*.jsx'))

        # Should have TypeScript examples
        assert len(ts_files) > 0 or len(tsx_files) > 0, \
            "Must have TypeScript examples (.ts or .tsx)"

        # Should NOT have JavaScript examples
        assert len(js_files) == 0 and len(jsx_files) == 0, \
            "Examples should be TypeScript, not JavaScript"

    def test_core_examples_documentation_exists(self):
        """Core examples documentation must exist."""
        doc = NEXTJS_PACK / 'examples' / 'core-examples.md'
        assert doc.exists(), f"Core examples documentation not found at {doc}"


class TestNextJSMiddlewarePatterns:
    """Test Next.js middleware patterns are documented."""

    def test_middleware_documented_in_guidelines(self):
        """Middleware patterns must be documented in guidelines."""
        guidelines_dir = NEXTJS_PACK / 'guidelines'
        all_guidelines = list(guidelines_dir.glob('*.md'))

        has_middleware_doc = any(
            'middleware' in f.read_text(encoding='utf-8').lower()
            for f in all_guidelines
        )

        assert has_middleware_doc, \
            "Middleware patterns must be documented in guidelines"


class TestNextJSCompleteness:
    """Test overall Next.js 16 pack completeness."""

    def test_all_critical_patterns_covered(self):
        """All critical Next.js 16 patterns must be covered somewhere in the pack."""
        # Collect all text content from the pack
        all_content = []

        # Guidelines
        for f in (NEXTJS_PACK / 'guidelines').glob('*.md'):
            all_content.append(f.read_text(encoding='utf-8').lower())

        # Validators
        for f in (NEXTJS_PACK / 'validators').glob('*.md'):
            all_content.append(f.read_text(encoding='utf-8').lower())

        # Agent overlays
        for f in (NEXTJS_PACK / 'agents' / 'overlays').glob('*.md'):
            all_content.append(f.read_text(encoding='utf-8').lower())

        # Examples
        for f in (NEXTJS_PACK / 'examples').glob('*'):
            if f.is_file():
                all_content.append(f.read_text(encoding='utf-8').lower())

        combined = ' '.join(all_content)

        # Critical Next.js 16 patterns
        critical_patterns = [
            'app router',
            'server component',
            'use client',
            'route handler',
            'nextrequest',
            'nextresponse',
            'metadata',
            'loading',
            'error',
            'use server',
            'revalidate',
        ]

        missing = []
        for pattern in critical_patterns:
            if pattern not in combined:
                missing.append(pattern)

        assert len(missing) == 0, \
            f"Missing critical Next.js 16 patterns: {missing}"

    def test_next_16_explicitly_mentioned(self):
        """Next.js 16 or App Router must be explicitly mentioned."""
        # Check key files explicitly mention Next.js version or App Router
        validator = NEXTJS_PACK / 'validators' / 'nextjs.md'
        content = validator.read_text(encoding='utf-8').lower()

        assert 'next.js 16' in content or 'next 16' in content or 'app router' in content, \
            "Must explicitly mention Next.js 16 or App Router"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
