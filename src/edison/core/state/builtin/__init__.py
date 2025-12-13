"""Built-in handler implementations for state machine transitions.

This package contains the built-in handlers (guards, actions, conditions)
that are loaded by the state machine loader. Pack and project handlers
can extend or override these.

Named "builtin" to avoid conflict with handlers.py (which contains
the registry base classes).

Handler loading order:
1. Core handlers (this package)
2. Bundled pack handlers (data/packs/<pack>/)
3. Project pack handlers (.edison/packs/<pack>/)
4. Project handlers (.edison/)
"""
