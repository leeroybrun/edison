"""Memory manager (provider selection + aggregation)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from edison.core.config import ConfigManager
from edison.core.memory.models import MemoryHit
from edison.core.memory.providers import MemoryProvider


@dataclass(frozen=True)
class MemoryConfig:
    enabled: bool
    max_hits: int
    providers: dict[str, dict[str, Any]]


def _load_memory_config(*, project_root: Path, validate_config: bool) -> MemoryConfig:
    full = ConfigManager(repo_root=project_root).load_config(
        validate=bool(validate_config), include_packs=True
    )
    mem = full.get("memory", {}) if isinstance(full.get("memory", {}), dict) else {}
    enabled = bool(mem.get("enabled", False))
    defaults = mem.get("defaults", {}) if isinstance(mem.get("defaults", {}), dict) else {}
    max_hits = int(defaults.get("maxHits", 5))
    providers = mem.get("providers", {}) if isinstance(mem.get("providers", {}), dict) else {}
    return MemoryConfig(enabled=enabled, max_hits=max_hits, providers=providers)


class MemoryManager:
    """Aggregate memory providers configured for a project."""

    def __init__(self, *, project_root: Path, validate_config: bool = False) -> None:
        self.project_root = project_root
        self._validate_config = bool(validate_config)
        self._cfg = _load_memory_config(project_root=project_root, validate_config=self._validate_config)
        self._providers: list[MemoryProvider] = self._build_providers()

    @property
    def enabled(self) -> bool:
        return bool(self._cfg.enabled)

    @property
    def providers(self) -> list[MemoryProvider]:
        return list(self._providers)

    def _build_providers(self) -> list[MemoryProvider]:
        if not self._cfg.enabled:
            return []

        providers: list[MemoryProvider] = []
        from edison.core.memory.registry import ProviderBuildError, build_provider

        for provider_id, raw in self._cfg.providers.items():
            if not isinstance(raw, dict) or raw.get("enabled") is False:
                continue
            try:
                providers.append(build_provider(str(provider_id), raw, project_root=self.project_root))
            except ProviderBuildError:
                if self._validate_config:
                    raise
                continue
            except Exception:
                if self._validate_config:
                    raise
                continue

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

    def save_structured(self, record: dict[str, Any], *, session_id: Optional[str] = None) -> None:
        if not self.enabled:
            return
        for provider in self._providers:
            fn = getattr(provider, "save_structured", None)
            if not callable(fn):
                continue
            try:
                fn(record, session_id=session_id)
            except Exception:
                continue

    def index(self, *, event: str, session_id: Optional[str] = None) -> None:
        if not self.enabled:
            return
        for provider in self._providers:
            fn = getattr(provider, "index", None)
            if not callable(fn):
                continue
            try:
                fn(event=event, session_id=session_id)
            except Exception:
                continue


__all__ = [
    "MemoryManager",
    "MemoryConfig",
]
