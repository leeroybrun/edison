"""Actor identity resolution module.

This module provides centralized actor identity resolution for Edison,
enabling reliable "who am I?" resolution for compaction recovery and
context restoration.
"""

from edison.core.actor.identity import ActorIdentity, resolve_actor_identity

__all__ = [
    "ActorIdentity",
    "resolve_actor_identity",
]
