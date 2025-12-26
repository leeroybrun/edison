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


class StructuredMemoryProvider(Protocol):
    id: str

    def save_structured(self, record: dict[str, Any], *, session_id: Optional[str] = None) -> None:
        ...


class IndexableMemoryProvider(Protocol):
    id: str

    def index(self, *, event: str, session_id: Optional[str] = None) -> None:
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
    index_args: tuple[str, ...] = ()
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

    def index(self, *, event: str, session_id: Optional[str] = None) -> None:
        if not self._is_available() or not self.index_args:
            return
        argv = [self.command] + [
            a.format(event=event, session_id=session_id or "") if "{" in a else a for a in self.index_args
        ]
        try:
            proc = self._run(argv)
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
    index_args: tuple[str, ...] = ()
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

    def index(self, *, event: str, session_id: Optional[str] = None) -> None:
        if not self._is_available() or not self.index_args:
            return
        argv = [self.command] + [
            a.format(event=event, session_id=session_id or "") if "{" in a else a for a in self.index_args
        ]
        try:
            proc = self._run(argv)
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

    Best-effort optional import with fail-open behavior.
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
    save_structured_method: str = "save_structured_insights"
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

    def save_structured(self, record: dict[str, Any], *, session_id: Optional[str] = None) -> None:
        if not self.module or not self.class_name:
            return

        try:
            memory = self._instantiate()
        except Exception:
            return

        try:
            fn = getattr(memory, self.save_structured_method, None)
            if fn is None:
                return
            payload = dict(record)
            if session_id and not payload.get("sessionId"):
                payload["sessionId"] = session_id
            _run_awaitable(fn(payload))
        except Exception:
            return
        finally:
            try:
                _run_awaitable(getattr(memory, "close")())  # type: ignore[misc]
            except Exception:
                pass


@dataclass(frozen=True)
class McpToolsMemoryProvider:
    """Provider backed by MCP tools.

    Intended for episodic memory servers that expose a search tool.
    """

    id: str
    project_root: Path
    server_id: str
    search_tool: str
    read_tool: str | None = None
    response_format: str = "json"
    timeout_seconds: int = 10
    search_arguments: dict[str, Any] | None = None

    def _build_search_args(self, query: str, limit: int) -> dict[str, Any]:
        base: dict[str, Any] = {"query": query, "limit": max(0, int(limit))}
        if not self.search_arguments:
            return base

        args: dict[str, Any] = {}
        for k, v in self.search_arguments.items():
            if isinstance(v, str) and "{" in v:
                try:
                    args[str(k)] = v.format(query=query, limit=max(0, int(limit)))
                except Exception:
                    args[str(k)] = v
            else:
                args[str(k)] = v
        if "query" not in args:
            args["query"] = query
        if "limit" not in args:
            args["limit"] = max(0, int(limit))
        return args

    def search(self, query: str, *, limit: int) -> list[MemoryHit]:
        try:
            from edison.core.memory.mcp_client import call_tool

            result = call_tool(
                project_root=self.project_root,
                server_id=self.server_id,
                tool_name=self.search_tool,
                arguments=self._build_search_args(query, limit),
                timeout_seconds=self.timeout_seconds,
            )
        except Exception:
            return []

        if result is None:
            return []

        texts: list[str] = []
        for item in result.content:
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                texts.append(item["text"])

        hits: list[MemoryHit] = []
        for t in texts:
            if str(self.response_format).lower() != "json":
                if t.strip():
                    hits.append(MemoryHit(provider_id=self.id, text=t.strip(), score=None, meta=None))
                continue

            try:
                obj = json.loads(t)
            except Exception:
                continue

            results = obj.get("results") if isinstance(obj, dict) else None
            if not isinstance(results, list):
                continue

            for r in results:
                if not isinstance(r, dict):
                    continue
                snippet = r.get("snippet") or r.get("text") or r.get("content")
                if not isinstance(snippet, str) or not snippet.strip():
                    continue
                score_raw = r.get("similarity") or r.get("score")
                score: Optional[float]
                try:
                    score = float(score_raw) if score_raw is not None else None
                except Exception:
                    score = None
                meta = {k: v for k, v in r.items() if k not in {"snippet", "text", "content", "similarity", "score"}}
                hits.append(MemoryHit(provider_id=self.id, text=snippet.strip(), score=score, meta=meta or None))

        hits.sort(key=lambda h: (h.score is not None, h.score or 0.0), reverse=True)
        return hits[: max(0, int(limit))]

    def save(self, session_summary: str, *, session_id: Optional[str] = None) -> None:
        # No generic write tool standard; keep fail-open.
        return


@dataclass(frozen=True)
class FileStoreMemoryProvider:
    """File-based structured memory fallback provider.

    Persists memory artifacts under a project-managed directory so memory survives
    even when external providers are unavailable.
    """

    id: str
    memory_root: Path
    codebase_map_path: Path
    patterns_path: Path
    gotchas_path: Path
    session_insights_dir: Path

    def search(self, query: str, *, limit: int) -> list[MemoryHit]:
        return []

    def save(self, session_summary: str, *, session_id: Optional[str] = None) -> None:
        return

    def _ensure_dirs(self) -> None:
        self.memory_root.mkdir(parents=True, exist_ok=True)
        self.session_insights_dir.mkdir(parents=True, exist_ok=True)

    def _read_lines_set(self, path: Path) -> set[str]:
        try:
            if not path.exists():
                return set()
            return {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}
        except Exception:
            return set()

    def _append_deduped_bullets(self, path: Path, items: list[str]) -> None:
        try:
            existing = self._read_lines_set(path)
            to_add: list[str] = []
            for it in items:
                s = str(it).strip()
                if not s:
                    continue
                line = f"- {s}"
                if line in existing:
                    continue
                to_add.append(line)
                existing.add(line)
            if not to_add:
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                if path.stat().st_size == 0:
                    f.write("")  # no-op (keeps file present)
                for ln in to_add:
                    f.write(ln + "\n")
        except Exception:
            return

    def _merge_codebase_map(self, updates: dict[str, str]) -> None:
        try:
            self.codebase_map_path.parent.mkdir(parents=True, exist_ok=True)
            base: dict[str, Any] = {}
            if self.codebase_map_path.exists():
                try:
                    base_raw = json.loads(self.codebase_map_path.read_text(encoding="utf-8") or "{}")
                    if isinstance(base_raw, dict):
                        base = base_raw
                except Exception:
                    base = {}

            for k, v in updates.items():
                ks = str(k).strip()
                vs = str(v).strip()
                if not ks or not vs:
                    continue
                base[ks] = vs

            self.codebase_map_path.write_text(
                json.dumps(base, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except Exception:
            return

    def save_structured(self, record: dict[str, Any], *, session_id: Optional[str] = None) -> None:
        self._ensure_dirs()
        sid = str(session_id or record.get("sessionId") or "").strip()
        if not sid:
            return
        out_path = self.session_insights_dir / f"{sid}.json"
        try:
            out_path.write_text(
                json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except Exception:
            return

        discoveries = record.get("discoveries") if isinstance(record.get("discoveries"), dict) else {}
        patterns = discoveries.get("patterns_found", []) if isinstance(discoveries, dict) else []
        gotchas = discoveries.get("gotchas_encountered", []) if isinstance(discoveries, dict) else []
        files_understood = discoveries.get("files_understood", {}) if isinstance(discoveries, dict) else {}

        if isinstance(patterns, list):
            self._append_deduped_bullets(self.patterns_path, [p for p in patterns if isinstance(p, str)])
        if isinstance(gotchas, list):
            self._append_deduped_bullets(self.gotchas_path, [g for g in gotchas if isinstance(g, str)])
        if isinstance(files_understood, dict):
            updates = {str(k): str(v) for k, v in files_understood.items() if isinstance(k, str)}
            self._merge_codebase_map(updates)


__all__ = [
    "MemoryProvider",
    "StructuredMemoryProvider",
    "IndexableMemoryProvider",
    "ExternalCliMemoryProvider",
    "ExternalCliTextMemoryProvider",
    "GraphitiPythonMemoryProvider",
    "McpToolsMemoryProvider",
    "FileStoreMemoryProvider",
]
