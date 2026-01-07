"""OpenCode platform adapter.

This adapter generates OpenCode artifacts (.opencode/ directory) for Edison
projects via the composition system.

Artifacts generated:
- .opencode/plugin/edison.ts - TypeScript plugin
- .opencode/agent/*.md - Agent definitions
- .opencode/command/*.md - Command definitions
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

from edison.core.adapters.base import PlatformAdapter
from edison.core.utils.io import ensure_directory, write_text
from edison.core.utils.text import render_template_text
from edison.data import read_text as data_read_text
from edison.data import read_yaml as data_read_yaml

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig


class OpenCodeAdapterError(RuntimeError):
    """Error in OpenCode adapter operations."""


_TEMPLATE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _validate_template_name(name: str) -> str:
    """Validate that a template name cannot escape its template directory."""
    if not isinstance(name, str) or not name or name.strip() != name:
        raise OpenCodeAdapterError(f"Invalid template name: {name!r}")
    if _TEMPLATE_NAME_RE.fullmatch(name) is None:
        raise OpenCodeAdapterError(f"Invalid template name: {name!r}")
    return name


def _get_opencode_config() -> dict[str, Any]:
    """Load OpenCode configuration from YAML."""
    raw = data_read_yaml("config", "opencode.yaml")
    config: dict[str, Any] = raw.get("opencode", {})
    return config


def _get_agent_templates() -> list[str]:
    """Get agent template names from config."""
    cfg = _get_opencode_config()
    return list(cfg.get("agentTemplates", []))


def _get_command_templates() -> list[str]:
    """Get command template names from config."""
    cfg = _get_opencode_config()
    return list(cfg.get("commandTemplates", []))


def _render_plugin_template(*, repo_root: Path) -> str:
    """Render the TypeScript plugin template."""
    template = data_read_text("templates", "opencode/plugin/edison.ts.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


def _render_agent_template(name: str, *, repo_root: Path) -> str:
    """Render an agent template by name."""
    name = _validate_template_name(name)
    template = data_read_text("templates", f"opencode/agent/{name}.md.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


def _render_command_template(name: str, *, repo_root: Path) -> str:
    """Render a command template by name."""
    name = _validate_template_name(name)
    template = data_read_text("templates", f"opencode/command/{name}.md.template")
    return render_template_text(template, {"repo_root": str(repo_root)})


class OpenCodeAdapter(PlatformAdapter):
    """Platform adapter for OpenCode artifacts.

    Generates .opencode/ directory structure for Edison projects:
    - Plugin (TypeScript)
    - Agent definitions (Markdown)
    - Command definitions (Markdown)
    """

    def __init__(
        self,
        project_root: Path | None = None,
        adapter_config: AdapterConfig | None = None,
    ) -> None:
        super().__init__(project_root=project_root, adapter_config=adapter_config)

    @property
    def platform_name(self) -> str:
        return "opencode"

    def _write_if_changed(self, target: Path, content: str) -> bool:
        """Write content to target file if it differs or doesn't exist.

        Returns True if file was written, False if unchanged.
        """
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if existing == content:
                return False

        ensure_directory(target.parent)
        write_text(target, content, encoding="utf-8")
        return True

    def _sync_plugin(self) -> list[Path]:
        """Sync the TypeScript plugin."""
        target = self.project_root / ".opencode" / "plugin" / "edison.ts"
        content = _render_plugin_template(repo_root=self.project_root)
        self._write_if_changed(target, content)
        return [target]

    def _sync_agents(self) -> list[Path]:
        """Sync agent definition files."""
        files: list[Path] = []
        agent_dir = self.project_root / ".opencode" / "agent"

        for name in _get_agent_templates():
            safe_name = _validate_template_name(name)
            target = agent_dir / f"{safe_name}.md"
            content = _render_agent_template(safe_name, repo_root=self.project_root)
            self._write_if_changed(target, content)
            files.append(target)

        return files

    def _sync_commands(self) -> list[Path]:
        """Sync command definition files."""
        files: list[Path] = []
        cmd_dir = self.project_root / ".opencode" / "command"

        for name in _get_command_templates():
            safe_name = _validate_template_name(name)
            target = cmd_dir / f"{safe_name}.md"
            content = _render_command_template(safe_name, repo_root=self.project_root)
            self._write_if_changed(target, content)
            files.append(target)

        return files

    def sync_all(self) -> dict[str, list[Path]]:
        """Sync all OpenCode artifacts.

        Returns:
            Dict with 'files' key containing list of artifact file paths.
        """
        files: list[Path] = []

        # Ensure base .opencode directory exists
        ensure_directory(self.project_root / ".opencode")

        # Sync all artifact types
        files.extend(self._sync_plugin())
        files.extend(self._sync_agents())
        files.extend(self._sync_commands())

        return {"files": files}


__all__ = ["OpenCodeAdapter", "OpenCodeAdapterError"]
