"""State machine handler infrastructure (registries + utilities).

Canonical built-in handler implementations live in `edison.core.state.builtin`
(guards/actions/conditions). The dynamic loader (`edison.core.state.loader`)
loads from that builtin layer first, then from pack + project layers.

This package intentionally contains only the *infrastructure*:
- `registries.py`: domain-aware handler registries (guards/actions/conditions)
- `utils.py`: shared context helpers
"""




