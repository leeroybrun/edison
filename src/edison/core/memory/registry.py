"""Memory provider registry (kind -> builder).

The memory domain is provider-driven: Edison only defines a small set of
capabilities (search, save text, optional structured save/index), and providers
implement those capabilities behind configuration boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from edison.core.config import ConfigManager
from edison.core.memory.providers import (
    ExternalCliMemoryProvider,
    ExternalCliTextMemoryProvider,
    FileStoreMemoryProvider,
    GraphitiPythonMemoryProvider,
    McpToolsMemoryProvider,
    MemoryProvider,
)


ProviderBuilder = Callable[[str, dict[str, Any], Path], MemoryProvider]


@dataclass(frozen=True)
class ProviderBuildError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _build_external_cli(provider_id: str, raw: dict[str, Any], project_root: Path) -> MemoryProvider:
    command = str(raw.get("command") or "").strip()
    search_args = raw.get("searchArgs", [])
    save_args = raw.get("saveArgs", [])
    index_args = raw.get("indexArgs", [])
    timeout_seconds = int(raw.get("timeoutSeconds", 10))
    if not command or not isinstance(search_args, list):
        raise ProviderBuildError(f"memory.providers.{provider_id}: external-cli requires command and searchArgs")

    return ExternalCliMemoryProvider(
        id=str(provider_id),
        command=command,
        search_args=tuple(str(a) for a in search_args),
        save_args=tuple(str(a) for a in save_args) if isinstance(save_args, list) else (),
        index_args=tuple(str(a) for a in index_args) if isinstance(index_args, list) else (),
        timeout_seconds=timeout_seconds,
    )


def _build_external_cli_text(provider_id: str, raw: dict[str, Any], project_root: Path) -> MemoryProvider:
    command = str(raw.get("command") or "").strip()
    search_args = raw.get("searchArgs", [])
    save_args = raw.get("saveArgs", [])
    index_args = raw.get("indexArgs", [])
    timeout_seconds = int(raw.get("timeoutSeconds", 10))
    if not command or not isinstance(search_args, list):
        raise ProviderBuildError(
            f"memory.providers.{provider_id}: external-cli-text requires command and searchArgs"
        )

    return ExternalCliTextMemoryProvider(
        id=str(provider_id),
        command=command,
        search_args=tuple(str(a) for a in search_args),
        save_args=tuple(str(a) for a in save_args) if isinstance(save_args, list) else (),
        index_args=tuple(str(a) for a in index_args) if isinstance(index_args, list) else (),
        timeout_seconds=timeout_seconds,
    )


def _build_graphiti_python(provider_id: str, raw: dict[str, Any], project_root: Path) -> MemoryProvider:
    module = str(raw.get("module") or "graphiti_memory").strip()
    class_name = str(raw.get("class") or "GraphitiMemory").strip()
    spec_dir_raw = raw.get("specDir")
    if not isinstance(spec_dir_raw, str) or not spec_dir_raw.strip():
        raise ProviderBuildError(f"memory.providers.{provider_id}: graphiti-python requires specDir")
    spec_dir = Path(str(spec_dir_raw)).expanduser()
    if not spec_dir.is_absolute():
        spec_dir = (project_root / spec_dir).resolve()

    group_id_mode = str(raw.get("groupIdMode") or "project").strip()
    include_project_context = bool(raw.get("includeProjectContext", True))
    include_session_history = bool(raw.get("includeSessionHistory", False))
    session_history_limit = int(raw.get("sessionHistoryLimit", 3))
    save_method = str(raw.get("saveMethod") or "save_pattern").strip()
    save_structured_method = str(raw.get("saveStructuredMethod") or "save_structured_insights").strip()
    save_template = str(raw.get("saveTemplate") or "{summary}")

    return GraphitiPythonMemoryProvider(
        id=str(provider_id),
        project_root=project_root,
        spec_dir=spec_dir,
        module=module,
        class_name=class_name,
        group_id_mode=group_id_mode,
        include_project_context=include_project_context,
        include_session_history=include_session_history,
        session_history_limit=session_history_limit,
        save_method=save_method,
        save_structured_method=save_structured_method,
        save_template=save_template,
    )


def _build_mcp_tools(provider_id: str, raw: dict[str, Any], project_root: Path) -> MemoryProvider:
    server_id = str(raw.get("serverId") or "").strip()
    search_tool = str(raw.get("searchTool") or "").strip()
    read_tool = str(raw.get("readTool") or "").strip() or None
    response_format = str(raw.get("responseFormat") or "json").strip()
    timeout_seconds = int(raw.get("timeoutSeconds", 10))
    search_arguments = raw.get("searchArguments")
    if search_arguments is not None and not isinstance(search_arguments, dict):
        raise ProviderBuildError(f"memory.providers.{provider_id}: searchArguments must be an object")
    if not server_id or not search_tool:
        raise ProviderBuildError(f"memory.providers.{provider_id}: mcp-tools requires serverId and searchTool")

    return McpToolsMemoryProvider(
        id=str(provider_id),
        project_root=project_root,
        server_id=server_id,
        search_tool=search_tool,
        read_tool=read_tool,
        response_format=response_format,
        timeout_seconds=timeout_seconds,
        search_arguments=search_arguments if isinstance(search_arguments, dict) else None,
    )


def _build_file_store(provider_id: str, raw: dict[str, Any], project_root: Path) -> MemoryProvider:
    full = ConfigManager(repo_root=project_root).load_config(validate=False, include_packs=True)
    mem = full.get("memory", {}) if isinstance(full.get("memory", {}), dict) else {}
    paths = mem.get("paths", {}) if isinstance(mem.get("paths", {}), dict) else {}

    pm_root = full.get("project_management_dir")
    if not isinstance(pm_root, str) or not pm_root.strip():
        legacy = full.get("paths", {}) if isinstance(full.get("paths", {}), dict) else {}
        pm_root = legacy.get("management_dir") if isinstance(legacy.get("management_dir"), str) else ".project"

    root_raw = str(paths.get("root") or f"{pm_root}/memory")
    root = Path(root_raw).expanduser()
    if not root.is_absolute():
        root = (project_root / root).resolve()

    codebase_map_file = str(paths.get("codebaseMapFile") or "codebase_map.json")
    patterns_file = str(paths.get("patternsFile") or "patterns.md")
    gotchas_file = str(paths.get("gotchasFile") or "gotchas.md")
    insights_dir = str(paths.get("sessionInsightsDir") or "session_insights")

    return FileStoreMemoryProvider(
        id=str(provider_id),
        memory_root=root,
        codebase_map_path=(root / codebase_map_file),
        patterns_path=(root / patterns_file),
        gotchas_path=(root / gotchas_file),
        session_insights_dir=(root / insights_dir),
    )


_PROVIDERS: dict[str, ProviderBuilder] = {
    "external-cli": _build_external_cli,
    "external-cli-text": _build_external_cli_text,
    "graphiti-python": _build_graphiti_python,
    "mcp-tools": _build_mcp_tools,
    "file-store": _build_file_store,
}


def build_provider(provider_id: str, raw: dict[str, Any], *, project_root: Path) -> MemoryProvider:
    kind = str(raw.get("kind") or "").strip()
    if not kind:
        raise ProviderBuildError(f"memory.providers.{provider_id}: missing kind")
    builder = _PROVIDERS.get(kind)
    if builder is None:
        raise ProviderBuildError(f"memory.providers.{provider_id}: unknown kind '{kind}'")
    return builder(provider_id, raw, project_root)


__all__ = ["build_provider", "ProviderBuildError"]
