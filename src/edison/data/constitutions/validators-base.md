# Validator Constitution Base (Embedded)

<!--
This file is embedded into EVERY validator prompt via:
  {{ include:constitutions/validators-base.md }}

CRITICAL:
- Single source of truth for validator constitution content
- Technology-agnostic core only
- Packs may extend via SECTION markers below
-->

## Core Principles (CRITICAL)

{{include-section:guidelines/includes/_TDD.md#principles}}

{{include-section:guidelines/includes/NO_MOCKS.md#philosophy}}

{{include-section:guidelines/includes/QUALITY.md#principles}}

{{include-section:guidelines/includes/CONFIGURATION.md#principles}}

{{include-section:guidelines/includes/_TDD.md#validator-check}}

{{include-section:guidelines/includes/NO_MOCKS.md#validator-flags}}

{{include-section:guidelines/includes/QUALITY.md#validator-checklist}}

## Pack Extensions

<!-- section: pack-constitution -->
<!-- Pack overlays extend here -->
<!-- /section: pack-constitution -->

