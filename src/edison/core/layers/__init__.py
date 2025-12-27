"""Generalized layer stack resolution for Edison.

Edison supports multiple overlay layers for all composable/configurable surfaces
(config, packs, markdown registries, rules, python extensions, etc).

The layer stack is defined via bootstrap YAML at:
  - <layer_root>/config/layers.yaml

Default stack (low → high precedence):
  user (~/.edison) → project (<repo>/.edison)

Packs are resolved from:
  bundled (edison.data/packs) → <layer_root>/packs for each overlay layer
"""

from .stack import LayerSpec, LayerStack, resolve_layer_stack

__all__ = ["LayerSpec", "LayerStack", "resolve_layer_stack"]

