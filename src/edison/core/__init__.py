"""Edison core Python library package.

Exposes helpers consumed by repository-level tests. Minimal surface for W1-G1.
"""

# Re-export exceptions module
from . import exceptions  # noqa: F401

__all__ = ["exceptions"]

