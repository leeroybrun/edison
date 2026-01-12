"""Domain-specific configuration for CI commands.

Provides cached access to project CI commands used for evidence capture and
workflow documentation.
"""

from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path
from typing import Any

from ..base import BaseDomainConfig


class CIConfig(BaseDomainConfig):
    """CI configuration accessor.

    Reads the top-level `ci` section from merged config.
    """

    def _config_section(self) -> str:
        return "ci"

    @cached_property
    def commands(self) -> dict[str, str]:
        """Return configured CI commands (name -> command string)."""
        raw = self.section.get("commands") if isinstance(self.section, dict) else None
        if not isinstance(raw, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in raw.items():
            key = str(k).strip()
            if not key:
                continue
            cmd = str(v).strip() if v is not None else ""
            if not cmd:
                continue
            out[key] = cmd
        return out

    @cached_property
    def fingerprint_git_roots(self) -> list[str]:
        """Repo roots to include in evidence fingerprinting (multi-repo workspaces).

        Config:
          ci:
            fingerprint:
              git_roots: ["./", "/abs/path/to/other/repo"]
        """
        fp = self.section.get("fingerprint") if isinstance(self.section, dict) else None
        raw = fp.get("git_roots") if isinstance(fp, dict) else None
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for v in raw:
            s = str(v).strip()
            if s:
                out.append(s)
        return out

    @cached_property
    def fingerprint_extra_files(self) -> list[str]:
        """Extra file paths to include in evidence fingerprinting.

        This is useful when behavior depends on external config (e.g. a stack env file).
        """
        fp = self.section.get("fingerprint") if isinstance(self.section, dict) else None
        raw = fp.get("extra_files") if isinstance(fp, dict) else None
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for v in raw:
            s = str(v).strip()
            if s:
                out.append(s)
        return out

    def _resolve_env_path_token(self, raw: str) -> str:
        s = str(raw or "").strip()
        if s.startswith("{ENV:") and s.endswith("}"):
            var = s[len("{ENV:") : -1].strip()
            return str(os.environ.get(var) or "").strip()
        return s

    def resolve_fingerprint_git_roots(self) -> list[Path]:
        """Resolve configured git roots into absolute Paths."""
        roots: list[Path] = []
        for raw in self.fingerprint_git_roots:
            token = self._resolve_env_path_token(raw)
            if not token:
                continue
            p = Path(token)
            if not p.is_absolute():
                p = (self.repo_root / p).resolve()
            roots.append(p)
        # De-dupe stable by string value
        seen: set[str] = set()
        out: list[Path] = []
        for p in roots:
            key = str(p)
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        return out

    def resolve_fingerprint_extra_files(self) -> list[Path]:
        """Resolve extra files into absolute Paths.

        Supports {ENV:VAR} tokens, and relative paths are resolved from repo root.
        Missing/empty tokens are skipped.
        """
        files: list[Path] = []
        for raw in self.fingerprint_extra_files:
            token = self._resolve_env_path_token(raw)
            if not token:
                continue
            p = Path(token)
            if not p.is_absolute():
                p = (self.repo_root / p).resolve()
            files.append(p)
        seen: set[str] = set()
        out: list[Path] = []
        for p in files:
            key = str(p)
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        return out

    def get_command(self, name: str) -> str | None:
        """Return a specific CI command by name."""
        return self.commands.get(str(name).strip())


__all__ = ["CIConfig"]

