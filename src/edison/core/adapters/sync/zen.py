#!/usr/bin/env python3
from __future__ import annotations

"""
Zen MCP Sync Adapter (full-featured)

This module provides complete integration between the Edison
composition system (guidelines + rules + Zen prompt helpers) and the
Zen MCP server's role-based system prompts.

Responsibilities:
  - Discover and filter guidelines/rules for a given logical role
  - Compose role/model-specific prompt text suitable for Zen MCP
  - Sync composed prompts into `.zen/conf/systemprompts/clink/project/`
    while preserving existing workflow loop sections.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import json
import fnmatch

from ...paths import PathResolver
from ...composition import CompositionEngine  # type: ignore
from ...composition.formatting import compose_for_role  # type: ignore
from ...config import ConfigManager  # type: ignore
from ...composition.guidelines import GuidelineRegistry
from ...rules import RulesRegistry  # type: ignore


WORKFLOW_HEADING = "## Edison Workflow Loop"


def _detect_repo_root(explicit_root: Optional[Path] = None) -> Path:
    """Resolve repository root for adapter operations.

    Prefer an explicitly provided root; otherwise delegate to the
    canonical PathResolver so ZenSync shares consistent semantics
    with the rest of Edison.
    """
    if explicit_root is not None:
        return explicit_root.resolve()

    return PathResolver.resolve_project_root()


def _canonical_model(model: str) -> str:
    """Normalize model identifier to codex|claude|gemini."""
    low = (model or "").strip().lower()
    if low.startswith("codex"):
        return "codex"
    if low.startswith("claude"):
        return "claude"
    if low.startswith("gemini"):
        return "gemini"
    return low or "codex"


def _canonical_role(role: str) -> str:
    """Normalize logical role names for filtering.

    Examples:
      - "default" → "default"
      - "codereviewer" / "code-reviewer" / "project-code-reviewer" → "codereviewer"
      - "planner" / "project-planner" → "planner"
      - Any other "project-*" → "project"
    """
    raw = (role or "").strip()
    low = raw.lower()

    if low.startswith("project-"):
        base = low[len("project-") :]
        if base in {"codereviewer", "code-reviewer"}:
            return "codereviewer"
        if base == "planner":
            return "planner"
        return "project"

    if low in {"codereviewer", "code-reviewer"}:
        return "codereviewer"
    if low == "planner":
        return "planner"
    if low == "default" or not low:
        return "default"

    return low


@dataclass
class ZenSync:
    """Full-featured adapter between Edison composition and Zen MCP prompts."""

    repo_root: Path
    config: Dict[str, Any]
    engine: CompositionEngine
    guideline_registry: GuidelineRegistry
    rules_registry: RulesRegistry
    _zen_roles_config: Dict[str, Any]
    _role_config_validated: bool

    def __init__(self, repo_root: Optional[Path] = None, config: Optional[Dict[str, Any]] = None) -> None:
        root = _detect_repo_root(repo_root)
        cfg_mgr = ConfigManager(root)
        self.repo_root = root
        self.config = config or cfg_mgr.load_config(validate=False)
        self.engine = CompositionEngine(self.config, repo_root=root)
        self.guideline_registry = GuidelineRegistry(repo_root=root)
        self.rules_registry = RulesRegistry(project_root=root)
        self._zen_roles_config = {}
        self._role_config_validated = False

    # ------------------------------------------------------------------
    # Public API: role-aware discovery
    # ------------------------------------------------------------------
    def _active_packs(self) -> List[str]:
        packs = ((self.config or {}).get("packs", {}) or {}).get("active", [])
        if isinstance(packs, list):
            return packs
        return []

    # ---------- Role configuration helpers ----------
    def _load_zen_roles_config(self) -> Dict[str, Any]:
        """Return raw zen.roles config as a mapping (or empty dict).

        Supports both legacy list form (ignored here) and new mapping form.
        """
        if self._zen_roles_config:
            return self._zen_roles_config

        zen_cfg = self.config.get("zen") or {}
        roles_cfg = zen_cfg.get("roles") or {}
        if isinstance(roles_cfg, dict):
            self._zen_roles_config = roles_cfg
        else:
            # Legacy form: list of model ids; no per-role config available.
            self._zen_roles_config = {}
        return self._zen_roles_config

    def _validate_role_config(self) -> None:
        """Lightweight structural validation for zen.roles config."""
        if self._role_config_validated:
            return

        roles_cfg = self._load_zen_roles_config()
        for role_name, spec in roles_cfg.items():
            if not isinstance(spec, dict):
                raise ValueError(f"zen.roles.{role_name} must be a mapping")
            for key in ("guidelines", "rules", "packs"):
                if key in spec and not isinstance(spec[key], list):
                    raise ValueError(f"zen.roles.{role_name}.{key} must be a list when present")
        self._role_config_validated = True

    def _get_role_spec(self, role: str) -> Optional[Dict[str, Any]]:
        """Fetch config spec for a role (case-insensitive).

        Supports both concrete project roles (e.g. ``project-api-builder``)
        and their generic counterparts (e.g. ``api-builder``) via
        delegation.roleMapping.
        """
        roles_cfg = self._load_zen_roles_config()
        if not roles_cfg:
            return None

        self._validate_role_config()

        # Case-insensitive lookup by exact key match.
        lowered: Dict[str, str] = {k.lower(): k for k in roles_cfg.keys()}
        key = (role or "").strip().lower()

        # Direct hit
        if key in lowered:
            return roles_cfg[lowered[key]]

        # For project-prefixed roles, also try generic name via delegation.roleMapping
        delegation_cfg = self.config.get("delegation") or {}
        role_mapping: Dict[str, str] = (delegation_cfg.get("roleMapping") or {})  # type: ignore[assignment]

        if key.startswith("project-"):
            concrete = key
            inverse_map: Dict[str, str] = {v.lower(): k for k, v in role_mapping.items()}
            generic = inverse_map.get(concrete)
            if generic and generic in lowered:
                return roles_cfg[lowered[generic]]

        return None

    def get_applicable_guidelines(self, role: str) -> List[str]:
        """Return guideline names applicable to a logical role.

        Role mapping reference:
          - default: All guidelines
          - codereviewer: Quality, security, performance, review-focused
          - planner: Architecture / design oriented
          - project-*: Project overlays + pack guidelines
        """
        packs = self._active_packs()
        role_spec = self._get_role_spec(role)

        # Role-specific pack selection: intersect configured packs with active packs.
        effective_packs = packs
        if role_spec is not None and isinstance(role_spec.get("packs"), list):
            requested_packs = [str(p).strip() for p in role_spec.get("packs", []) if str(p).strip()]
            if requested_packs:
                effective_packs = [p for p in packs if p in requested_packs]
                if not effective_packs:
                    # Fallback to all active packs when intersection is empty.
                    effective_packs = packs

        all_names = self.guideline_registry.all_names(effective_packs, include_project=True)

        # Config-driven guideline patterns (wildcards + substrings)
        if role_spec is not None and isinstance(role_spec.get("guidelines"), list):
            patterns = [str(p).strip().lower() for p in role_spec.get("guidelines", []) if str(p).strip()]
            if patterns:
                selected: List[str] = []
                for name in all_names:
                    lower = name.lower()
                    for pat in patterns:
                        if fnmatch.fnmatch(lower, pat) or pat in lower:
                            selected.append(name)
                            break
                return selected

        canonical = _canonical_role(role)

        if canonical == "default":
            return all_names

        if canonical == "codereviewer":
            review_keywords = {"quality", "security", "performance", "review"}
            selected = []
            for name in all_names:
                lower = name.lower()
                if any(keyword in lower for keyword in review_keywords):
                    selected.append(name)
            return selected

        if canonical == "planner":
            planner_keywords = {"architecture", "design", "planning"}
            selected = []
            for name in all_names:
                lower = name.lower()
                if any(keyword in lower for keyword in planner_keywords):
                    selected.append(name)
            return selected

        if canonical == "project":
            # Project overlays + pack guidelines only (skip core-only guidelines)
            selected = []
            for name in all_names:
                has_project = self.guideline_registry.project_override_path(name) is not None
                has_pack = bool(self.guideline_registry.pack_paths(name, effective_packs))
                if has_project or has_pack:
                    selected.append(name)
            return selected

        # Fallback: return everything for unknown roles
        return all_names

    def get_applicable_rules(self, role: str) -> List[Dict[str, Any]]:
        """Return composed rules applicable to a logical role."""
        packs = self._active_packs()

        composed = self.rules_registry.compose(packs=packs)
        rules_map: Dict[str, Dict[str, Any]] = composed.get("rules", {}) or {}
        role_spec = self._get_role_spec(role)
        canonical = _canonical_role(role)

        # Category-based filtering uses raw registries (which retain category).
        core_registry = self.rules_registry.load_core_registry()
        ids_by_category: Dict[str, Set[str]] = {}
        ids_by_origin: Dict[str, Dict[str, Set[str]]] = {}

        def _record_rules(registry: Dict[str, Any], origin: str) -> None:
            for raw_rule in registry.get("rules", []) or []:
                if not isinstance(raw_rule, dict):
                    continue
                rid = str(raw_rule.get("id") or "").strip()
                if not rid:
                    continue
                category = str(raw_rule.get("category") or "").lower()
                if not category:
                    continue
                ids_by_category.setdefault(category, set()).add(rid)
                bucket = ids_by_origin.setdefault(origin, {})
                bucket.setdefault(category, set()).add(rid)

        _record_rules(core_registry, "core")
        for pack_name in packs:
            pack_registry = self.rules_registry.load_pack_registry(pack_name)
            _record_rules(pack_registry, pack_name)

        # Config-driven rule category + pack filtering
        if role_spec is not None and isinstance(role_spec.get("rules"), list):
            categories = {str(c).strip().lower() for c in role_spec.get("rules", []) if str(c).strip()}
            packs_filter: List[str] = []
            if isinstance(role_spec.get("packs"), list):
                packs_filter = [str(p).strip() for p in role_spec.get("packs", []) if str(p).strip()]

            selected_ids: Set[str] = set()
            for category in categories:
                if packs_filter:
                    # Always include core rules for the category, plus rules from configured packs.
                    selected_ids.update(ids_by_origin.get("core", {}).get(category, set()))
                    for pack_name in packs_filter:
                        selected_ids.update(ids_by_origin.get(pack_name, {}).get(category, set()))
                else:
                    selected_ids.update(ids_by_category.get(category, set()))

            return [rules_map[rid] for rid in selected_ids if rid in rules_map]

        # Default/unknown roles see the full composed view.
        if canonical in {"default", "project"}:
            return list(rules_map.values())

        if canonical == "codereviewer":
            include_categories = {"validation", "implementation", "context", "general"}
        elif canonical == "planner":
            include_categories = {"delegation", "session", "transition", "context"}
        else:
            # Fallback: no additional filtering
            return list(rules_map.values())

        selected_ids: Set[str] = set()
        for category in include_categories:
            selected_ids.update(ids_by_category.get(category, set()))

        return [rules_map[rid] for rid in selected_ids if rid in rules_map]

    # ------------------------------------------------------------------
    # Public API: prompt composition
    # ------------------------------------------------------------------
    def compose_zen_prompt(self, role: str, model: str, packs: List[str]) -> str:
        """Generate prompt text for a given role/model combination.

        The prompt includes:
          - Model/role header with model-specific context hints
          - Base Edison context (via CompositionEngine)
          - Role-specific guideline excerpts
          - Role-specific rules summary
        """
        model_key = _canonical_model(model)
        canonical_role = _canonical_role(role)

        # Base content derives from the model-specific role used for validators.
        base_content = compose_for_role(self.engine, model_key)

        guideline_names = self.get_applicable_guidelines(role)
        guideline_sections: List[str] = []
        for name in guideline_names:
            result = self.guideline_registry.compose(name, packs, project_overrides=True)
            guideline_sections.append(f"## Guideline: {name}\n\n{result.text.strip()}")
        guidelines_block = "\n\n".join(guideline_sections)

        rules = self.get_applicable_rules(role)
        rule_lines: List[str] = []
        if rules:
            rule_lines.append("## Role-Specific Rules")
            for rule_obj in rules:
                rid = rule_obj.get("id") or ""
                title = rule_obj.get("title") or rid
                category = rule_obj.get("category") or ""
                blocking = bool(rule_obj.get("blocking"))
                level = "BLOCKING" if blocking else "NON-BLOCKING"
                label = f"[{level}] {title}"
                if category:
                    label = f"{label} (category: {category})"
                rule_lines.append(f"- {label}")
        rules_block = "\n".join(rule_lines)

        header_lines: List[str] = [
            "=== Edison / Zen MCP Prompt ===",
            f"Model: {model_key}",
            f"Role: {canonical_role}",
        ]
        # Model-specific context window hints (token-aware formatting)
        if model_key == "codex":
            header_lines.append("Context window: ~200k tokens (approximate)")
        elif model_key == "claude":
            header_lines.append("Context window: ~200k+ tokens; prefer concise reasoning.")
        elif model_key == "gemini":
            header_lines.append("Context window: ~1M tokens; richer references allowed.")

        header = "\n".join(header_lines)

        sections: List[str] = [header, base_content]
        if guidelines_block:
            sections.append("=== Role-Specific Guidelines ===\n\n" + guidelines_block)
        if rules_block:
            sections.append(rules_block)

        return "\n\n".join([section for section in sections if section]).rstrip() + "\n"

    # ------------------------------------------------------------------
    # Public API: prompt sync
    # ------------------------------------------------------------------
    def _workflow_template(self) -> Optional[str]:
        template_path = self.repo_root / ".zen" / "templates" / "workflow-loop.txt"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def _split_workflow_section(content: str) -> tuple[str, Optional[str]]:
        """Split content into (body, workflow_section)."""
        idx = content.find(WORKFLOW_HEADING)
        if idx == -1:
            return content, None
        body = content[:idx].rstrip()
        workflow = content[idx:]
        return body, workflow

    def _attach_workflow_loop(self, core_text: str, existing_file: Optional[Path]) -> str:
        """Attach or preserve workflow loop section when syncing prompts."""
        existing_loop: Optional[str] = None
        if existing_file is not None and existing_file.exists():
            _, existing_loop = self._split_workflow_section(
                existing_file.read_text(encoding="utf-8")
            )

        loop_text = existing_loop or self._workflow_template()
        if not loop_text:
            # No workflow template available; return core text as-is.
            return core_text

        if WORKFLOW_HEADING in core_text:
            # Already attached; avoid duplication.
            return core_text

        return core_text.rstrip() + "\n\n" + loop_text.rstrip() + "\n"

    def _zen_prompts_dir(self) -> Path:
        out_dir = self.repo_root / ".zen" / "conf" / "systemprompts" / "clink" / "project"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def sync_role_prompts(self, model: str, roles: List[str]) -> Dict[str, Path]:
        """Sync composed prompts for a model across one or more logical roles.

        Generic roles (default / codereviewer / planner) are combined into
        the model-level file `<model>.txt`. project-specific roles
        (`project-*`) are written to individual files matching the Zen role
        name (e.g. `project-api-builder.txt`).
        """
        model_key = _canonical_model(model)
        if not roles:
            roles = ["default"]

        packs = self._active_packs()
        prompts_dir = self._zen_prompts_dir()

        results: Dict[str, Path] = {}

        generic_roles: List[str] = []
        project_roles: List[str] = []
        for role in roles:
            if role.lower().startswith("project-"):
                project_roles.append(role)
            else:
                generic_roles.append(role)

        # Generic roles share a single file per model
        if generic_roles:
            sections: List[str] = []
            for role in generic_roles:
                sections.append(self.compose_zen_prompt(role=role, model=model_key, packs=packs))
            combined = "\n\n".join(sections)
            target = prompts_dir / f"{model_key}.txt"
            final_text = self._attach_workflow_loop(combined, target if target.exists() else None)
            target.write_text(final_text, encoding="utf-8")
            for role in generic_roles:
                results[role] = target

        # project roles each get their own file
        for role in project_roles:
            target = prompts_dir / f"{role}.txt"
            text = self.compose_zen_prompt(role=role, model=model_key, packs=packs)
            final_text = self._attach_workflow_loop(text, target if target.exists() else None)
            target.write_text(final_text, encoding="utf-8")
            results[role] = target

        return results

    # ------------------------------------------------------------------
    # Public API: CLI prompt verification
    # ------------------------------------------------------------------
    def verify_cli_prompts(self, sync: bool = True) -> Dict[str, Any]:
        """
        Verify that all Zen MCP CLI client roles have prompt files.

        When ``sync`` is True (default), this method first syncs prompts
        for all project-specific roles discovered in CLI client configs
        before performing verification.

        Returns a report dictionary with the following keys:
          - ``ok`` (bool): True when no problems were found.
          - ``models`` (list[str]): Models discovered from CLI configs.
          - ``roles`` (list[str]): project roles discovered from CLI configs.
          - ``missing`` (list[str]): Human-readable entries for missing files.
          - ``missingWorkflow`` (list[str]): Entries for files lacking the
            Edison workflow loop section.
        """
        cli_dir = self.repo_root / ".zen" / "conf" / "cli_clients"
        report: Dict[str, Any] = {
            "ok": True,
            "models": [],
            "roles": [],
            "missing": [],
            "missingWorkflow": [],
        }

        if not cli_dir.exists():
            # Nothing to verify; treat as success but keep report minimal.
            return report

        models: Set[str] = set()
        roles: Set[str] = set()
        role_to_paths: Dict[str, Set[Path]] = {}

        for cfg_path in sorted(cli_dir.glob("*.json")):
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
            except Exception:
                # Malformed configs are treated as having no roles for verification.
                continue

            model_name = str(data.get("name") or cfg_path.stem)
            models.add(_canonical_model(model_name))

            raw_roles = data.get("roles") or {}
            if not isinstance(raw_roles, dict):
                continue

            for role_name, spec in raw_roles.items():
                if not isinstance(spec, dict):
                    continue
                # Only verify project-specific roles; generic prompts share model files.
                if not role_name.startswith("project-"):
                    continue
                prompt_rel = spec.get("prompt_path")
                if not isinstance(prompt_rel, str):
                    continue
                prompt_path = (cfg_path.parent / prompt_rel).resolve()
                roles.add(role_name)
                role_to_paths.setdefault(role_name, set()).add(prompt_path)

        report["models"] = sorted(models)
        report["roles"] = sorted(roles)

        # Optionally sync prompts for all discovered roles first.
        if sync and roles:
            for model in sorted(models):
                self.sync_role_prompts(model=model, roles=sorted(roles))

        missing: List[str] = []
        missing_workflow: List[str] = []

        for role_name, paths in role_to_paths.items():
            for path in paths:
                if not path.exists():
                    missing.append(f"{role_name} → {path}")
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:
                    missing.append(f"{role_name} → {path}")
                    continue
                if WORKFLOW_HEADING not in text:
                    missing_workflow.append(f"{role_name} → {path}")

        report["missing"] = missing
        report["missingWorkflow"] = missing_workflow
        report["ok"] = not missing and not missing_workflow
        return report


__all__ = [
    "ZenAdapter",
    "WORKFLOW_HEADING",
]
