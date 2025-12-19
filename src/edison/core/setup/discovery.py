"""
Auto-discovery utilities for Edison setup wizard.

Discovers available packs, validators, agents, and orchestrators from
the bundled edison.data package and project-level directories.

Uses ConfigManager for pack-aware config loading (core > packs > project).

Architecture:
- Core content: ALWAYS from bundled edison.data
- Project overrides: <project-config-dir>/config/*.yaml merged on top of bundled
- Packs: bundled (edison.data/packs/) + project (<project-config-dir>/packs/)
- NO <project-config-dir>/core/ - that is legacy
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Set

from edison.data import get_data_path
from edison.core.utils.paths import get_project_config_dir
from edison.core.packs.paths import iter_pack_dirs


class SetupDiscovery:
    """Auto-discover available options for setup wizard.

    Uses ConfigManager for pack-aware configuration loading.
    """

    def __init__(self, edison_core: Path, repo_root: Path):
        """Initialize discovery.

        Args:
            edison_core: Bundled data directory (edison.data package root)
            repo_root: Project repository root
        """
        from edison.core.config import ConfigManager

        self.edison_core = edison_core
        self.repo_root = repo_root

        # Use ConfigManager for consistent path resolution
        cfg_mgr = ConfigManager(repo_root=repo_root)
        self.bundled_packs_dir = cfg_mgr.bundled_packs_dir
        self.project_packs_dir = cfg_mgr.project_packs_dir
        self.project_config_dir = cfg_mgr.project_config_dir
        self._cfg_mgr = cfg_mgr

        self.setup_config = self._load_setup_config()

    # ---------- Public API ----------
    def discover_packs(self) -> List[str]:
        """Discover available packs from bundled + project packs (v2).

        Packs are first-class only when they have a `pack.yml` manifest.
        """
        names: Set[str] = set()

        for pack_name, pack_dir, _kind in iter_pack_dirs(self.repo_root):
            if (pack_dir / "pack.yml").exists():
                names.add(pack_name)

        return sorted(names)

    def discover_orchestrators(self) -> List[str]:
        """Discover available orchestrators using ConfigManager's pack-aware loading."""
        config = self._cfg_mgr.load_config(validate=False, include_packs=True)
        profiles = ((config.get("orchestrators") or {}).get("profiles") or {})
        if profiles:
            return list(profiles.keys())

        # Fallback from setup config
        cfg = (self.setup_config.get("discovery") or {}).get("orchestrators", {})
        return list(cfg.get("fallback") or ["claude", "cursor", "codex"])

    def discover_validators(self, packs: List[str]) -> List[str]:
        """Discover validators using ConfigManager's pack-aware loading.

        ConfigManager handles the full layering:
        1. Core config (bundled validators.yaml)
        2. Pack configs (bundled + project packs)
        3. Project config (<project-config-dir>/config/validators.yaml)
        """
        config = self._cfg_mgr.load_config(validate=False, include_packs=True)

        # Extract IDs from merged validation config
        ids: List[str] = []
        ids.extend(self._extract_ids_from_data(config.get("validation", {})))

        # Discovery should list ALL available IDs across sources, not only the
        # final merged value (project overrides may replace lists from packs).
        ids.extend(self._extract_validator_ids_from_pack_configs(packs))

        return self._dedupe(ids)

    def discover_agents(self, packs: List[str]) -> List[str]:
        """Discover agents using ConfigManager + directory scanning.

        ConfigManager handles config merging (core > packs > project).
        Directory scanning finds .md agent files.
        """
        ids: List[str] = []

        # Extract IDs from merged config
        config = self._cfg_mgr.load_config(validate=False, include_packs=True)
        ids.extend(self._extract_ids_from_data(config.get("agents", {})))

        # Include pack-defined agent IDs even when project config overrides the
        # same key with replace semantics.
        ids.extend(self._extract_agent_ids_from_pack_configs(packs))

        # Discover from bundled agents directory
        bundled_agents_dir = Path(get_data_path("agents"))
        if bundled_agents_dir.exists():
            for agent_file in bundled_agents_dir.glob("*.md"):
                agent_id = agent_file.stem
                if agent_id not in ids:
                    ids.append(agent_id)

        # Discover from project agents directory
        project_agents_dir = get_project_config_dir(self.repo_root, create=False) / "agents"
        if project_agents_dir.exists():
            for agent_file in project_agents_dir.glob("*.md"):
                agent_id = agent_file.stem
                if agent_id not in ids:
                    ids.append(agent_id)

        # Discover from pack agent directories (bundled + project) for the selected packs.
        for _pack_name, pack_dir, _kind in iter_pack_dirs(self.repo_root, packs=packs):
            pack_agents_dir = pack_dir / "agents"
            if not pack_agents_dir.exists():
                continue
            for agent_file in pack_agents_dir.glob("*.md"):
                agent_id = agent_file.stem
                if agent_id not in ids:
                    ids.append(agent_id)

        return self._dedupe(ids)

    def discover_pack_setup_questions(self, selected_packs: List[str]) -> List[Dict[str, Any]]:
        """Discover setup questions contributed by selected packs."""
        questions: List[Dict[str, Any]] = []

        for pack in selected_packs or []:
            # Check bundled pack setup
            bundled_pack_setup = self.bundled_packs_dir / pack / "config" / "setup.yml"
            if bundled_pack_setup.exists():
                pack_setup = self._load_yaml(bundled_pack_setup)
                pack_questions = (pack_setup.get("setup") or {}).get("questions") or []
                for question in pack_questions:
                    if self._check_dependencies(question, selected_packs):
                        questions.append(question)
            
            # Check project pack setup (overrides/additions)
            project_pack_setup = self.project_packs_dir / pack / "config" / "setup.yml"
            if project_pack_setup.exists():
                pack_setup = self._load_yaml(project_pack_setup)
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
        """Load setup config from bundled data."""
        path = get_data_path("config", "setup.yaml")
        return self._load_yaml(path)

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        from edison.core.utils.io import read_yaml
        return read_yaml(path, default={})

    def _load_json(self, path: Path) -> Dict[str, Any]:
        from edison.core.utils.io import read_json
        return read_json(path, default={})

    def _extract_ids(self, path: Path) -> List[str]:
        """Extract IDs from a YAML file."""
        data = self._load_yaml(path)
        return self._extract_ids_from_data(data)

    def _extract_ids_from_data(self, data: Any) -> List[str]:
        """Extract IDs from a data structure."""
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

    def _iter_pack_overlay_configs(self, packs: List[str], filenames: List[str]) -> List[Path]:
        """Return candidate config overlay paths for selected packs (bundled + project)."""
        paths: List[Path] = []
        for pack in packs or []:
            for base in (self.bundled_packs_dir, self.project_packs_dir):
                for name in filenames:
                    p = base / pack / "config" / name
                    if p.exists():
                        paths.append(p)
        return paths

    def _extract_validator_ids_from_pack_configs(self, packs: List[str]) -> List[str]:
        """Extract validator roster IDs from selected pack config overlays."""
        ids: List[str] = []
        for path in self._iter_pack_overlay_configs(packs, ["validators.yml", "validators.yaml"]):
            data = self._load_yaml(path)
            ids.extend(self._extract_ids_from_data(data.get("validation", {})))
        return ids

    def _extract_agent_ids_from_pack_configs(self, packs: List[str]) -> List[str]:
        """Extract agent IDs from selected pack config overlays."""
        ids: List[str] = []
        for path in self._iter_pack_overlay_configs(packs, ["agents.yml", "agents.yaml"]):
            data = self._load_yaml(path)
            ids.extend(self._extract_ids_from_data(data.get("agents", {})))
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
