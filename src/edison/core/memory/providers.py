"""Memory provider interfaces and implementations.

Providers are optional integrations that store/search long-lived information
across sessions. Edison treats providers as boundaries: failures must be
fail-open and never break core workflows.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

from edison.core.memory.models import MemoryHit


class MemoryProvider(Protocol):
    id: str

    def search(self, query: str, *, limit: int) -> list[MemoryHit]:
        ...

    def save(self, session_summary: str, *, session_id: Optional[str] = None) -> None:
        ...


@dataclass(frozen=True)
class ExternalCliMemoryProvider:
    """Provider backed by an external CLI that returns JSON on stdout.

    This is the recommended integration path for tools like episodic-memory
    without duplicating their storage/indexing inside Edison.
    """

    id: str
    command: str
    search_args: tuple[str, ...]
    save_args: tuple[str, ...]
    timeout_seconds: int = 10

    def _run(self, argv: list[str], *, stdin_text: Optional[str] = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            input=stdin_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=self.timeout_seconds,
        )

    def _is_available(self) -> bool:
        return bool(self.command) and shutil.which(self.command) is not None

    def search(self, query: str, *, limit: int) -> list[MemoryHit]:
        if not self._is_available():
            return []

        argv = [self.command] + [
            a.format(query=query, limit=limit) if "{" in a else a for a in self.search_args
        ]
        try:
            proc = self._run(argv)
        except Exception:
            return []

        if proc.returncode != 0:
            return []

        try:
            data = json.loads(proc.stdout or "null")
        except Exception:
            return []

        items: list[Any]
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and isinstance(data.get("hits"), list):
            items = data["hits"]
        else:
            return []

        hits: list[MemoryHit] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("content") or item.get("summary") or ""
            if not isinstance(text, str) or not text.strip():
                continue
            score_raw = item.get("score")
            score: Optional[float]
            try:
                score = float(score_raw) if score_raw is not None else None
            except Exception:
                score = None
            meta_raw = item.get("meta")
            meta = meta_raw if isinstance(meta_raw, dict) else None
            hits.append(MemoryHit(provider_id=self.id, text=text, score=score, meta=meta))

        hits.sort(key=lambda h: (h.score is not None, h.score or 0.0), reverse=True)
        return hits[: max(0, int(limit))]

    def save(self, session_summary: str, *, session_id: Optional[str] = None) -> None:
        if not self._is_available():
            return

        argv = [self.command] + [
            a.format(session_id=session_id or "", summary=session_summary) if "{" in a else a
            for a in self.save_args
        ]
        try:
            proc = self._run(argv, stdin_text=session_summary)
        except Exception:
            return
        if proc.returncode != 0:
            return


@dataclass(frozen=True)
class ExternalCliTextMemoryProvider:
    """Provider backed by an external CLI that returns human-readable text.

    This fits tools like `episodic-memory` which primarily emit formatted text.
    """

    id: str
    command: str
    search_args: tuple[str, ...]
    save_args: tuple[str, ...] = ()
    timeout_seconds: int = 10

    def _run(self, argv: list[str], *, stdin_text: Optional[str] = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            input=stdin_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=self.timeout_seconds,
        )

    def _is_available(self) -> bool:
        return bool(self.command) and shutil.which(self.command) is not None

    def search(self, query: str, *, limit: int) -> list[MemoryHit]:
        if not self._is_available():
            return []

        argv = [self.command] + [
            a.format(query=query, limit=limit) if "{" in a else a for a in self.search_args
        ]
        try:
            proc = self._run(argv)
        except Exception:
            return []
        if proc.returncode != 0:
            return []

        text = (proc.stdout or "").strip()
        if not text:
            return []

        return [
            MemoryHit(
                provider_id=self.id,
                text=text,
                score=None,
                meta=None,
            )
        ]

    def save(self, session_summary: str, *, session_id: Optional[str] = None) -> None:
        if not self._is_available() or not self.save_args:
            return
        argv = [self.command] + [
            a.format(session_id=session_id or "", summary=session_summary) if "{" in a else a
            for a in self.save_args
        ]
        try:
            proc = self._run(argv, stdin_text=session_summary)
        except Exception:
            return
        if proc.returncode != 0:
            return


def _run_awaitable(value: Any) -> Any:
    if not inspect.isawaitable(value):
        return value
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(value)
    # Fail-open: Edison memory provider interface is sync; avoid blocking in an active loop.
    return None


@dataclass(frozen=True)
class GraphitiPythonMemoryProvider:
    """Provider backed by a Python GraphitiMemory class (async API).

    This mirrors the integration style used by Auto-Claude: a best-effort
    optional import with fail-open behavior.
    """

    id: str
    project_root: Path
    spec_dir: Path
    module: str = "graphiti_memory"
    class_name: str = "GraphitiMemory"
    group_id_mode: str = "project"
    include_project_context: bool = True
    include_session_history: bool = False
    session_history_limit: int = 3
    save_method: str = "save_pattern"
    save_template: str = "{summary}"

    def _load_class(self) -> Any:
        mod = importlib.import_module(self.module)
        return getattr(mod, self.class_name)

    def _instantiate(self) -> Any:
        cls = self._load_class()
        return cls(self.spec_dir, self.project_root, group_id_mode=self.group_id_mode)

    def search(self, query: str, *, limit: int) -> list[MemoryHit]:
        if not self.module or not self.class_name:
            return []

        try:
            memory = self._instantiate()
        except Exception:
            return []

        hits: list[MemoryHit] = []
        try:
            items = _run_awaitable(
                getattr(memory, "get_relevant_context")(  # type: ignore[misc]
                    query,
                    num_results=max(0, int(limit)),
                    include_project_context=bool(self.include_project_context),
                )
            )
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    text = item.get("content") or item.get("text") or item.get("summary") or ""
                    if not isinstance(text, str) or not text.strip():
                        continue
                    score_raw = item.get("score")
                    score: Optional[float]
                    try:
                        score = float(score_raw) if score_raw is not None else None
                    except Exception:
                        score = None
                    meta = {k: v for k, v in item.items() if k not in {"content", "text", "summary", "score"}}
                    hits.append(MemoryHit(provider_id=self.id, text=text, score=score, meta=meta or None))

            if bool(self.include_session_history):
                hist = _run_awaitable(
                    getattr(memory, "get_session_history")(  # type: ignore[misc]
                        limit=max(0, int(self.session_history_limit))
                    )
                )
                if isinstance(hist, list):
                    for item in hist:
                        if not isinstance(item, dict):
                            continue
                        text = item.get("summary") or item.get("content") or ""
                        if not isinstance(text, str) or not text.strip():
                            # Best-effort: fall back to the raw dict.
                            text = json.dumps(item, sort_keys=True)
                        hits.append(MemoryHit(provider_id=self.id, text=text, score=None, meta={"type": "session"}))
        except Exception:
            return []
        finally:
            try:
                _run_awaitable(getattr(memory, "close")())  # type: ignore[misc]
            except Exception:
                pass

        hits.sort(key=lambda h: (h.score is not None, h.score or 0.0), reverse=True)
        return hits[: max(0, int(limit))]

    def save(self, session_summary: str, *, session_id: Optional[str] = None) -> None:
        if not self.module or not self.class_name:
            return

        try:
            memory = self._instantiate()
        except Exception:
            return

        try:
            try:
                text = str(self.save_template or "{summary}").format(
                    summary=session_summary,
                    session_id=session_id or "",
                    project_root=str(self.project_root),
                )
            except Exception:
                text = session_summary

            fn = getattr(memory, self.save_method, None)
            if fn is None:
                return
            _run_awaitable(fn(text))
        except Exception:
            return
        finally:
            try:
                _run_awaitable(getattr(memory, "close")())  # type: ignore[misc]
            except Exception:
                pass


__all__ = [
    "MemoryProvider",
    "ExternalCliMemoryProvider",
    "ExternalCliTextMemoryProvider",
    "GraphitiPythonMemoryProvider",
]
