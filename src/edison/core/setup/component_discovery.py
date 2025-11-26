"""
Auto-discovery utilities for Edison setup wizard.

Discovers available packs, validators, agents, and orchestrators from
the filesystem and configuration files with NO hardcoded values.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Set
import yaml


class SetupDiscovery:
    """Auto-discover available options for setup wizard."""

    def __init__(self, edison_core: Path, repo_root: Path):
        self.edison_core = edison_core
        self.repo_root = repo_root
        self.setup_config = self._load_setup_config()

    # ---------- Public API ----------
    def discover_packs(self) -> List[str]:
        """Discover available packs from .edison/packs/."""
        cfg = (self.setup_config.get("discovery") or {}).get("packs", {})
        directory = cfg.get("directory")
        pattern = cfg.get("pattern", "")
        if not directory or not pattern:
            return []

        base = self._resolve_repo_path(directory)
        if not base.exists():
            return []

        names: Set[str] = set()
        for path in base.glob(pattern):
            if path.is_file():
                names.add(path.parent.name)
        return sorted(names)

    def discover_orchestrators(self) -> List[str]:
        """Discover available orchestrators."""
        cfg = (self.setup_config.get("discovery") or {}).get("orchestrators", {})
        config_file = cfg.get("config_file")
        fallback = list(cfg.get("fallback") or [])

        if config_file:
            path = self._resolve_repo_path(config_file)
            data = self._load_yaml(path)
            profiles = ((data.get("orchestrators") or {}).get("profiles") or {})
            if profiles:
                return list(profiles.keys())
        return fallback

    def discover_validators(self, packs: List[str]) -> List[str]:
        """Discover validators from core + selected packs."""
        cfg = (self.setup_config.get("discovery") or {}).get("validators", {})
        core_path = cfg.get("core_config")
        pack_pattern = cfg.get("pack_pattern")

        ids: List[str] = []
        if core_path:
            ids.extend(self._extract_ids(self._resolve_repo_path(core_path)))

        for pack in packs or []:
            if not pack_pattern:
                continue
            pack_path = self._resolve_repo_path(pack_pattern.replace("*", pack, 1))
            ids.extend(self._extract_ids(pack_path))

        return self._dedupe(ids)

    def discover_agents(self, packs: List[str]) -> List[str]:
        """Discover agents from core + selected packs."""
        cfg = (self.setup_config.get("discovery") or {}).get("agents", {})
        core_path = cfg.get("core_config")
        pack_pattern = cfg.get("pack_pattern")

        ids: List[str] = []
        if core_path:
            ids.extend(self._extract_ids(self._resolve_repo_path(core_path)))

        for pack in packs or []:
            if not pack_pattern:
                continue
            pack_path = self._resolve_repo_path(pack_pattern.replace("*", pack, 1))
            ids.extend(self._extract_ids(pack_path))

        return self._dedupe(ids)

    def discover_pack_setup_questions(self, selected_packs: List[str]) -> List[Dict[str, Any]]:
        """Discover setup questions contributed by selected packs."""

        questions: List[Dict[str, Any]] = []

        for pack in selected_packs or []:
            pack_setup_path = self.edison_core.parent / "packs" / pack / "config" / "setup.yml"
            if not pack_setup_path.exists():
                continue

            pack_setup = self._load_yaml(pack_setup_path)
            pack_questions = (pack_setup.get("setup") or {}).get("questions") or []

            for question in pack_questions:
                if self._check_dependencies(question, selected_packs):
                    questions.append(question)

        return questions

    def detect_project_name(self) -> str:
        """Detect project name from directory or package.json."""
        pkg_path = self.repo_root / "package.json"
        if pkg_path.exists():
            data = self._load_json(pkg_path)
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return self.repo_root.name

    def detect_project_type(self) -> str:
        """Heuristically detect project type."""
        allowed = self._project_type_options()
        candidate = self._detect_from_files()
        if candidate in allowed:
            return candidate
        if "Other" in allowed:
            return "Other"
        return allowed[0] if allowed else candidate

    # ---------- Helpers ----------
    def _load_setup_config(self) -> Dict[str, Any]:
        path = self.edison_core / "config" / "setup.yaml"
        return self._load_yaml(path)

    def _resolve_repo_path(self, rel: str) -> Path:
        path = Path(rel)
        return path if path.is_absolute() else self.repo_root / path

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        from edison.core.file_io.utils import read_yaml_safe
        return read_yaml_safe(path, default={})

    def _load_json(self, path: Path) -> Dict[str, Any]:
        from edison.core.file_io.utils import read_json_with_default
        return read_json_with_default(path, default={})

    def _extract_ids(self, path: Path) -> List[str]:
        data = self._load_yaml(path)
        ids: List[str] = []

        def walk(obj: Any) -> None:
            if isinstance(obj, dict):
                if "id" in obj and isinstance(obj["id"], str):
                    ids.append(obj["id"])
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(data)
        return ids

    def _dedupe(self, items: List[str]) -> List[str]:
        seen: Set[str] = set()
        result: List[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _check_dependencies(self, question: Dict[str, Any], selected_packs: List[str]) -> bool:
        """Return True when all declared dependencies are satisfied."""

        depends_on = question.get("depends_on") or []
        for dep in depends_on:
            pack = dep.get("pack")
            if pack and pack not in selected_packs:
                return False
        return True

    def _project_type_options(self) -> List[str]:
        setup_cfg = self.setup_config.get("setup") or {}
        basic = setup_cfg.get("basic") or []
        for q in basic:
            if isinstance(q, dict) and q.get("id") == "project_type":
                return list(q.get("options") or [])
        # Fallback empty list; detection will return candidate unchanged
        return []

    def _detect_from_files(self) -> str:
        pkg_path = self.repo_root / "package.json"
        if pkg_path.exists():
            pkg = self._load_json(pkg_path)
            deps = pkg.get("dependencies") or {}
            dev_deps = pkg.get("devDependencies") or {}
            combined = {**deps, **dev_deps}
            names = set(combined.keys())
            if "next" in names:
                return "Next.js Full-Stack"
            if "fastify" in names:
                return "Fastify API"
            if "react" in names:
                return "React App"
            return "Node.js Library"

        if (self.repo_root / "Cargo.toml").exists():
            return "Rust Project"
        if (self.repo_root / "go.mod").exists():
            return "Go Application"
        if (self.repo_root / "pyproject.toml").exists() or (self.repo_root / "setup.py").exists():
            return "Python Library"

        return "Other"
