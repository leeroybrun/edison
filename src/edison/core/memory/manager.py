"""Memory manager (provider selection + aggregation)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from edison.core.config import ConfigManager
from edison.core.memory.models import MemoryHit
from edison.core.memory.providers import (
    ExternalCliMemoryProvider,
    ExternalCliTextMemoryProvider,
    GraphitiPythonMemoryProvider,
    MemoryProvider,
)


@dataclass(frozen=True)
class MemoryConfig:
    enabled: bool
    max_hits: int
    providers: dict[str, dict[str, Any]]


def _load_memory_config(*, project_root: Path) -> MemoryConfig:
    full = ConfigManager(repo_root=project_root).load_config(validate=False, include_packs=True)
    mem = full.get("memory", {}) if isinstance(full.get("memory", {}), dict) else {}
    enabled = bool(mem.get("enabled", False))
    defaults = mem.get("defaults", {}) if isinstance(mem.get("defaults", {}), dict) else {}
    max_hits = int(defaults.get("maxHits", 5))
    providers = mem.get("providers", {}) if isinstance(mem.get("providers", {}), dict) else {}
    return MemoryConfig(enabled=enabled, max_hits=max_hits, providers=providers)


class MemoryManager:
    """Aggregate memory providers configured for a project."""

    def __init__(self, *, project_root: Path) -> None:
        self.project_root = project_root
        self._cfg = _load_memory_config(project_root=project_root)
        self._providers: list[MemoryProvider] = self._build_providers()

    @property
    def enabled(self) -> bool:
        return bool(self._cfg.enabled)

    def _build_providers(self) -> list[MemoryProvider]:
        if not self._cfg.enabled:
            return []

        providers: list[MemoryProvider] = []
        for provider_id, raw in self._cfg.providers.items():
            if not isinstance(raw, dict) or raw.get("enabled") is False:
                continue
            kind = str(raw.get("kind") or "").strip()

            if kind == "external-cli":
                command = str(raw.get("command") or "").strip()
                search_args = raw.get("searchArgs", [])
                save_args = raw.get("saveArgs", [])
                timeout_seconds = int(raw.get("timeoutSeconds", 10))
                if isinstance(search_args, list) and isinstance(save_args, list) and command:
                    providers.append(
                        ExternalCliMemoryProvider(
                            id=str(provider_id),
                            command=command,
                            search_args=tuple(str(a) for a in search_args),
                            save_args=tuple(str(a) for a in save_args),
                            timeout_seconds=timeout_seconds,
                        )
                    )
            if kind == "external-cli-text":
                command = str(raw.get("command") or "").strip()
                search_args = raw.get("searchArgs", [])
                save_args = raw.get("saveArgs", [])
                timeout_seconds = int(raw.get("timeoutSeconds", 10))
                if isinstance(search_args, list) and command:
                    providers.append(
                        ExternalCliTextMemoryProvider(
                            id=str(provider_id),
                            command=command,
                            search_args=tuple(str(a) for a in search_args),
                            save_args=tuple(str(a) for a in save_args)
                            if isinstance(save_args, list)
                            else (),
                            timeout_seconds=timeout_seconds,
                        )
                    )
            if kind == "graphiti-python":
                module = str(raw.get("module") or "graphiti_memory").strip()
                class_name = str(raw.get("class") or "GraphitiMemory").strip()
                spec_dir_raw = raw.get("specDir")
                if not isinstance(spec_dir_raw, str) or not spec_dir_raw.strip():
                    continue
                spec_dir = Path(str(spec_dir_raw)).expanduser()
                if not spec_dir.is_absolute():
                    spec_dir = (self.project_root / spec_dir).resolve()

                group_id_mode = str(raw.get("groupIdMode") or "project").strip()
                include_project_context = bool(raw.get("includeProjectContext", True))
                include_session_history = bool(raw.get("includeSessionHistory", False))
                session_history_limit = int(raw.get("sessionHistoryLimit", 3))
                save_method = str(raw.get("saveMethod") or "save_pattern").strip()
                save_template = str(raw.get("saveTemplate") or "{summary}")

                if module and class_name:
                    providers.append(
                        GraphitiPythonMemoryProvider(
                            id=str(provider_id),
                            project_root=self.project_root,
                            spec_dir=spec_dir,
                            module=module,
                            class_name=class_name,
                            group_id_mode=group_id_mode,
                            include_project_context=include_project_context,
                            include_session_history=include_session_history,
                            session_history_limit=session_history_limit,
                            save_method=save_method,
                            save_template=save_template,
                        )
                    )

        return providers

    def search(self, query: str, *, limit: Optional[int] = None) -> list[MemoryHit]:
        if not self.enabled:
            return []
        effective_limit = self._cfg.max_hits if limit is None else max(0, int(limit))

        hits: list[MemoryHit] = []
        for provider in self._providers:
            try:
                hits.extend(provider.search(query, limit=effective_limit))
            except Exception:
                continue

        hits.sort(key=lambda h: (h.score is not None, h.score or 0.0), reverse=True)
        return hits[:effective_limit]

    def save(self, session_summary: str, *, session_id: Optional[str] = None) -> None:
        if not self.enabled:
            return
        for provider in self._providers:
            try:
                provider.save(session_summary, session_id=session_id)
            except Exception:
                continue


__all__ = [
    "MemoryManager",
    "MemoryConfig",
]
