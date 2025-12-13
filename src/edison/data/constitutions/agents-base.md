# Agent Constitution Base (Embedded)

<!--
This file is embedded into EVERY agent prompt via:
  {{ include:constitutions/agents-base.md }}

CRITICAL:
- Single source of truth for agent constitution content
- Technology-agnostic core only
- Packs may extend via SECTION markers below
-->

## Core Principles (CRITICAL)

{{include-section:guidelines/includes/_TDD.md#principles}}

{{include-section:guidelines/includes/NO_MOCKS.md#philosophy}}

{{include-section:guidelines/includes/QUALITY.md#principles}}

{{include-section:guidelines/includes/CONFIGURATION.md#principles}}

{{include-section:guidelines/includes/_TDD.md#agent-execution}}

## Pack Extensions

<!-- section: pack-constitution -->
<!-- Pack overlays extend here -->
<!-- /section: pack-constitution -->

