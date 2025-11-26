from __future__ import annotations

"""
Claude Code sync adapter (full-featured).

Provides complete Claude Code integration with:
  - Agent synchronization with frontmatter generation
  - Configuration file generation
  - Orchestrator guide injection
  - Schema validation

This is the full-featured adapter - use ClaudeAdapter (thin) for simple rendering.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .._schemas import load_schema, validate_payload, SchemaValidationError
from ...paths import PathResolver  # type: ignore
from ...paths.project import get_project_config_dir
from edison.core.file_io.utils import write_json_safe


class ClaudeAdapterError(RuntimeError):
    """Base error for Claude Code adapter failures."""


@dataclass
class EdisonAgentSections:
    """Structured view of an Edison-composed agent document."""

    name: str
    role: str
    tools: str
    guidelines: str
    workflows: str


class ClaudeSync:
    """Adapter for syncing Edison-composed outputs into Claude Code layout."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        # Resolve project root via centralized resolver so tests can isolate
        self.repo_root: Path = repo_root or PathResolver.resolve_project_root()
        self.project_config_dir = get_project_config_dir(self.repo_root)
        self.agents_generated_dir = self.project_config_dir / "_generated" / "agents"
        # T-016: NO LEGACY - Only constitution path supported
        self.orchestrator_constitution_path = (
            self.project_config_dir / "_generated" / "constitutions" / "ORCHESTRATORS.md"
        )
        self.orchestrator_manifest_path = (
            self.project_config_dir / "_generated" / "orchestrator-manifest.json"
        )
        self.claude_dir = self.repo_root / ".claude"
        self.claude_agents_dir = self.claude_dir / "agents"

    # ---------- Public API ----------
    def validate_claude_structure(self, *, create_missing: bool = True) -> Path:
        """Validate (and optionally create) Claude Code directory structure.

        Ensures that ``.claude`` and ``.claude/agents`` exist under the
        resolved project root.

        Args:
            create_missing: When True, create missing directories. When
                False, raise ClaudeAdapterError if structure is incomplete.

        Returns:
            Path to the ``.claude`` directory.
        """
        if not self.claude_dir.exists():
            if not create_missing:
                raise ClaudeAdapterError(f"Missing Claude directory: {self.claude_dir}")
            self.claude_dir.mkdir(parents=True, exist_ok=True)

        if not self.claude_agents_dir.exists():
            if not create_missing:
                raise ClaudeAdapterError(
                    f"Missing Claude agents directory: {self.claude_agents_dir}"
                )
            self.claude_agents_dir.mkdir(parents=True, exist_ok=True)

        return self.claude_dir

    def sync_agents_to_claude(self) -> List[Path]:
        """Sync composed Edison agents into ``.claude/agents``.

        Conversion rules:
          - Source: ``<project_config_dir>/_generated/agents/<name>.md``
          - Target: ``.claude/agents/<name>.md``
          - Frontmatter added:
              name: <agent-name>
              description: <first line of Role section>
              model: sonnet  (overridable via agent config JSON)
          - Body: Original Edison agent Markdown preserved verbatim.

        Incremental behavior:
          - If the target file exists and has a modification time greater
            than or equal to the source file, it is left untouched.

        Returns:
            List of Path objects for agents that were written/updated.
        """
        self.validate_claude_structure()

        if not self.agents_generated_dir.exists():
            return []

        changed: List[Path] = []

        for src in sorted(self.agents_generated_dir.glob("*.md")):
            agent_name = src.stem
            dest = self.claude_agents_dir / f"{agent_name}.md"

            src_mtime = src.stat().st_mtime
            dest_mtime = dest.stat().st_mtime if dest.exists() else 0.0
            if dest.exists() and dest_mtime >= src_mtime:
                # Target is up‑to‑date; skip to preserve incremental behavior
                continue

            text = src.read_text(encoding="utf-8")
            sections = self._parse_edison_agent(text, fallback_name=agent_name)
            agent_cfg = self._load_agent_config(agent_name)

            # Respect per-agent enablement flag (default: enabled)
            if agent_cfg.get("enabled") is False:
                continue

            payload = self._build_agent_payload(sections, agent_cfg)
            self._validate_agent_payload(agent_name, payload)
            rendered = self._render_claude_agent(text, sections, agent_cfg)

            dest.write_text(rendered, encoding="utf-8")
            changed.append(dest)

        return changed

    def sync_orchestrator_to_claude(self) -> Path:
        """Inject orchestrator constitution into ``.claude/CLAUDE.md``.

        T-016: NO LEGACY - Only constitution path is supported.
        ORCHESTRATOR_GUIDE.md fallback removed completely.

        Behavior:
          - Ensures ``.claude`` exists (via validate_claude_structure).
          - If ``CLAUDE.md`` does not exist, creates a minimal stub.
          - If constitution is missing, leaves ``CLAUDE.md`` unchanged.
          - Otherwise, appends or replaces a marked block with constitution content.

        Returns:
            Path to the updated ``CLAUDE.md`` file.
        """
        self.validate_claude_structure()

        claude_md = self.claude_dir / "CLAUDE.md"
        if not claude_md.exists():
            claude_md.write_text("# Claude Code Orchestrator\n", encoding="utf-8")

        # ONLY use constitution path (NO LEGACY fallback)
        constitution_path = self.orchestrator_constitution_path

        if not constitution_path.exists():
            # No constitution available; return unchanged
            return claude_md

        base = claude_md.read_text(encoding="utf-8")
        guide_text = constitution_path.read_text(encoding="utf-8").strip()

        marker_start = "<!-- EDISON_ORCHESTRATOR_GUIDE_START -->"
        marker_end = "<!-- EDISON_ORCHESTRATOR_GUIDE_END -->"

        block_lines = [
            marker_start,
            "",
            "# Edison Orchestrator Constitution (Generated)",
            "",
            guide_text,
            "",
            marker_end,
            "",
        ]
        block = "\n".join(block_lines)

        if marker_start in base and marker_end in base:
            # Replace existing guide block
            prefix, rest = base.split(marker_start, 1)
            _, suffix = rest.split(marker_end, 1)
            new_content = prefix.rstrip() + "\n\n" + block + suffix
        else:
            # Append new block
            new_content = base.rstrip() + "\n\n" + block

        claude_md.write_text(new_content, encoding="utf-8")
        return claude_md

    def generate_claude_config(self) -> Path:
        """Generate ``.claude/config.json`` using orchestrator manifest.

        Structure:
          {
            "version": "2.0.0",
            "orchestratorManifest": "<project_config_dir>/_generated/orchestrator-manifest.json",
            "claudeDir": ".claude",
            "agents": {
              "generic": [...],
              "specialized": [...],
              "project": [...]
            },
            "defaultAgent": "feature-implementer"
          }

        The agent lists are sourced directly from ``orchestrator-manifest.json``
        when available; otherwise they default to empty lists.

        Returns:
            Path to the generated config.json file.
        """
        self.validate_claude_structure()

        agents: Dict[str, List[str]] = {
            "generic": [],
            "specialized": [],
            "project": [],
        }
        version = "1.0.0"

        manifest_rel = f"{self.project_config_dir.name}/_generated/orchestrator-manifest.json"
        if self.orchestrator_manifest_path.exists():
            try:
                data = json.loads(
                    self.orchestrator_manifest_path.read_text(encoding="utf-8")
                )
                version = str(data.get("version", version))
                m_agents = data.get("agents", {}) or {}
                for key in agents.keys():
                    items = m_agents.get(key, []) or []
                    if isinstance(items, list):
                        agents[key] = [str(x) for x in items]
            except Exception:
                # Soft-fail: keep defaults if manifest is malformed
                pass

        default_agent = self._select_default_agent(agents)

        config: Dict[str, Any] = {
            "version": version,
            "orchestratorManifest": manifest_rel
            if self.orchestrator_manifest_path.exists()
            else None,
            "claudeDir": ".claude",
            "agents": agents,
            "defaultAgent": default_agent or "",
        }

        out_path = self.claude_dir / "config.json"
        write_json_safe(out_path, config, indent=2)
        return out_path

    # ---------- Internals ----------

    def _parse_edison_agent(self, text: str, *, fallback_name: str) -> EdisonAgentSections:
        """Extract core sections from an Edison agent Markdown document."""
        name = fallback_name
        role_lines: List[str] = []
        tools_lines: List[str] = []
        guideline_lines: List[str] = []
        workflow_lines: List[str] = []

        current: Optional[str] = None

        for raw in text.splitlines():
            line = raw.rstrip("\n")
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                lower = heading.lower()
                if lower.startswith("agent:"):
                    maybe = heading.split(":", 1)[1].strip()
                    if maybe:
                        name = maybe
                    current = None
                    continue
                if lower == "role":
                    current = "role"
                    continue
                if lower == "tools":
                    current = "tools"
                    continue
                if lower == "guidelines":
                    current = "guidelines"
                    continue
                if lower == "workflows":
                    current = "workflows"
                    continue
                current = None
                continue

            if current == "role":
                role_lines.append(line)
            elif current == "tools":
                tools_lines.append(line)
            elif current == "guidelines":
                guideline_lines.append(line)
            elif current == "workflows":
                workflow_lines.append(line)

        return EdisonAgentSections(
            name=name,
            role="\n".join(role_lines).strip(),
            tools="\n".join(tools_lines).strip(),
            guidelines="\n".join(guideline_lines).strip(),
            workflows="\n".join(workflow_lines).strip(),
        )

    def _load_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Load optional per-agent configuration for Claude agent generation.

        Lookup order (first hit wins):
          - <project_config_dir>/claude/agents/<agent>.json
          - .claude/agents/<agent>.json
        """
        candidates = [
            self.project_config_dir / "claude" / "agents" / f"{agent_name}.json",
            self.claude_agents_dir / f"{agent_name}.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8")) or {}
                except Exception:
                    return {}
                return self._validate_agent_config(agent_name, raw)
        return {}

    def _validate_agent_config(self, agent_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate per-agent JSON config against claude-agent-config.schema.json."""
        if not config:
            return {}

        # Defensive check: ensure basic type constraints even when schema
        # validation is unavailable or overly permissive.
        model = config.get("model")
        if model is not None and not isinstance(model, str):
            raise ClaudeAdapterError(
                f"Claude agent config for '{agent_name}' failed schema validation: "
                f"invalid 'model' type ({type(model).__name__}); expected string."
            )

        try:
            validate_payload(
                config,
                "claude-agent-config.schema.json",
                repo_root=self.repo_root,
            )
        except SchemaValidationError as exc:
            raise ClaudeAdapterError(
                f"Claude agent config for '{agent_name}' failed schema validation: {exc}"
            ) from exc
        except (FileNotFoundError, json.JSONDecodeError):
            # Schema not available or invalid - allow config to pass
            # (graceful degradation)
            pass

        return config

    def _build_agent_payload(
        self,
        sections: EdisonAgentSections,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build structured agent payload combining sections + config overrides."""
        name = config.get("name") or sections.name

        # Description preference: explicit config → first line of Role → fallback
        description = config.get("description")
        if not description:
            first_role_line = (sections.role.splitlines() or [""])[0].strip()
            description = first_role_line or f"{name} agent"

        model = config.get("model", "sonnet")

        payload: Dict[str, Any] = {
            "name": name,
            "description": description,
            "model": model,
            "sections": {
                "role": sections.role,
                "tools": sections.tools,
                "guidelines": sections.guidelines,
                "workflows": sections.workflows,
            },
        }
        if "role" in config:
            payload["role"] = config["role"]
        if "tags" in config:
            payload["tags"] = config["tags"]
        return payload

    def _validate_agent_payload(self, agent_name: str, payload: Dict[str, Any]) -> None:
        """Validate structured agent payload against claude-agent.schema.json."""
        # Defensive check: Role section must not be empty even if JSON Schema
        # validation is unavailable or misconfigured.
        sections = payload.get("sections") or {}
        role = sections.get("role", "")
        if not isinstance(role, str) or not role.strip():
            raise ClaudeAdapterError(
                f"Claude agent '{agent_name}' failed schema validation: "
                "Role section must not be empty."
            )

        try:
            validate_payload(
                payload,
                "claude-agent.schema.json",
                repo_root=self.repo_root,
            )
        except SchemaValidationError as exc:
            raise ClaudeAdapterError(
                f"Claude agent '{agent_name}' failed schema validation: {exc}"
            ) from exc
        except (FileNotFoundError, json.JSONDecodeError):
            # Schema not available or invalid - allow payload to pass
            # (graceful degradation)
            pass

    def _render_claude_agent(
        self,
        body: str,
        sections: EdisonAgentSections,
        config: Dict[str, Any],
    ) -> str:
        """Render a Claude Code agent document with frontmatter + body."""
        payload = self._build_agent_payload(sections, config)

        name = payload["name"]
        description = payload["description"]
        model = payload["model"]

        header_lines = [
            f"name: {name}",
            f"description: {description}",
            f"model: {model}",
        ]

        # Optional passthrough fields to frontmatter
        for key in ("role", "tags"):
            if key in payload:
                header_lines.append(f"{key}: {payload[key]}")

        header_lines.append("---")
        header_lines.append("")  # Blank line before body

        header = "\n".join(header_lines)
        # Preserve original Edison agent body verbatim
        return header + body.lstrip("\n")

    def _select_default_agent(self, agents: Dict[str, List[str]]) -> Optional[str]:
        """Select a default agent name for config.json."""
        preferred = "feature-implementer"
        if preferred in agents.get("generic", []) or preferred in agents.get(
            "project", []
        ):
            return preferred
        if preferred in agents.get("specialized", []):
            return preferred

        for key in ("generic", "specialized", "project"):
            bucket = agents.get(key, [])
            if bucket:
                return bucket[0]
        return None


__all__ = ["ClaudeSync", "ClaudeAdapterError", "EdisonAgentSections"]
