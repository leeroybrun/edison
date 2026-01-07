"""Actor identity resolver for compaction recovery.

This module provides a first-class ActorIdentity resolver that can reliably answer:
- which Edison role is currently active (orchestrator|agent|validator)
- optional role id (e.g. specific agent/validator profile id)
- which constitution file should be re-read
- the exact `edison read …` command to do so

Design goals:
- Centralized and reusable by hooks and CLI commands
- Environment variable-driven with fallback behavior
- Resilient to missing/invalid env vars (never crashes)
- Config-driven constitution path resolution
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from edison.core.utils.paths.project import get_project_config_dir

# Valid actor kinds in Edison
ActorKind = Literal["orchestrator", "agent", "validator", "unknown"]

# Environment variables for actor identity
ENV_ACTOR_KIND = "EDISON_ACTOR_KIND"
ENV_ACTOR_ID = "EDISON_ACTOR_ID"

# Mapping from kind to constitution filename
_KIND_TO_CONSTITUTION: dict[str, str] = {
    "agent": "AGENTS.md",
    "orchestrator": "ORCHESTRATOR.md",
    "validator": "VALIDATORS.md",
}

# Mapping from kind to read command artifact name
_KIND_TO_ARTIFACT: dict[str, str] = {
    "agent": "AGENTS",
    "orchestrator": "ORCHESTRATOR",
    "validator": "VALIDATORS",
}

# Aliases for legacy/plural forms
_KIND_ALIASES: dict[str, str] = {
    "agents": "agent",
    "orchestrators": "orchestrator",
    "validators": "validator",
}


def _normalize_kind(raw: str | None) -> ActorKind:
    """Normalize actor kind from env var, handling case and aliases.

    Args:
        raw: Raw kind value from environment variable.

    Returns:
        Normalized actor kind, or 'unknown' if invalid/missing.
    """
    if not raw:
        return "unknown"

    normalized = raw.strip().lower()

    # Apply legacy aliases
    if normalized in _KIND_ALIASES:
        normalized = _KIND_ALIASES[normalized]

    # Validate against known kinds
    if normalized in ("orchestrator", "agent", "validator"):
        return normalized  # type: ignore[return-value]

    return "unknown"


@dataclass(frozen=True)
class ActorIdentity:
    """Resolved actor identity with constitution and read command.

    Attributes:
        kind: The actor kind (orchestrator, agent, validator, unknown).
        actor_id: Optional actor-specific identifier (e.g., agent profile id).
        constitution_path: Resolved path to the constitution file, or None.
        read_command: The `edison read` command to read the constitution, or None.
        source: How the identity was resolved ('env' or 'fallback').
    """

    kind: ActorKind
    actor_id: str | None
    constitution_path: Path | None
    read_command: str | None
    source: Literal["env", "fallback"]


def resolve_actor_identity(
    project_root: Path,
    session_id: str | None = None,
) -> ActorIdentity:
    """Resolve actor identity from environment variables.

    Resolution precedence:
    1. Environment variables (EDISON_ACTOR_KIND, EDISON_ACTOR_ID)
    2. Fallback to unknown

    Args:
        project_root: Path to the project root.
        session_id: Optional session ID (reserved for future use).

    Returns:
        Resolved ActorIdentity with constitution path and read command.
    """
    # Read and normalize kind from env var
    raw_kind = os.environ.get(ENV_ACTOR_KIND)
    kind = _normalize_kind(raw_kind)

    # Read actor ID from env var
    actor_id_raw = os.environ.get(ENV_ACTOR_ID)
    actor_id = actor_id_raw.strip() if actor_id_raw and actor_id_raw.strip() else None

    # Determine source based on whether env var was present
    source: Literal["env", "fallback"] = "env" if raw_kind else "fallback"

    # Resolve constitution path and read command based on kind
    constitution_path: Path | None = None
    read_command: str | None = None

    if kind != "unknown":
        constitution_filename = _KIND_TO_CONSTITUTION.get(kind)
        artifact_name = _KIND_TO_ARTIFACT.get(kind)

        if constitution_filename and artifact_name:
            try:
                cfg_dir = get_project_config_dir(project_root, create=False)
                constitution_path = cfg_dir / "_generated" / "constitutions" / constitution_filename
                read_command = f"edison read {artifact_name} --type constitutions"
            except Exception:
                # Fail-open: constitution path resolution should never crash
                pass

    return ActorIdentity(
        kind=kind,
        actor_id=actor_id,
        constitution_path=constitution_path,
        read_command=read_command,
        source=source,
    )


__all__ = [
    "ActorIdentity",
    "ActorKind",
    "resolve_actor_identity",
]
