"""Dynamic setup questionnaire powered by setup.yaml."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import copy
import re
import yaml
from textwrap import dedent

from edison.core.paths.management import get_management_paths

try:  # Optional dependency; fallback rendering when missing
    from jinja2 import Template  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    Template = None  # type: ignore[assignment]

from edison.core.paths.resolver import PathResolver
from .discovery import SetupDiscovery


class SetupQuestionnaire:
    """Execute setup questions defined in setup.yaml."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        edison_core: Optional[Path] = None,
        config_path: Optional[Path] = None,
        discovery: Optional[SetupDiscovery] = None,
        assume_yes: bool = False,
    ) -> None:
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        self.edison_core = edison_core or (self.repo_root / ".edison" / "core")
        self.config_path = config_path or (self.edison_core / "config" / "setup.yaml")
        self.assume_yes = assume_yes

        self.config = self._load_config()
        self.discovery = discovery or SetupDiscovery(self.edison_core, self.repo_root)
        self.detected = {
            "project_name": self.discovery.detect_project_name(),
            "project_type": self.discovery.detect_project_type(),
        }

    # ---------- Public API ----------
    def run(
        self,
        mode: str,
        provided_answers: Optional[Dict[str, Any]] = None,
        assume_yes: Optional[bool] = None,
    ) -> Dict[str, Any]:
        provided: Dict[str, Any] = provided_answers or {}
        resolved: Dict[str, Any] = {}
        effective_assume_yes = self.assume_yes if assume_yes is None else assume_yes

        def _process_question(question: Dict[str, Any]) -> None:
            qid = question.get("id")
            if not qid:
                return

            options = self._resolve_options(question, resolved)
            default_value = self._default_value(question)
            value = provided.get(qid, None)

            if value is None:
                if effective_assume_yes:
                    value = copy.deepcopy(default_value)
                else:
                    value = self._prompt(question, options, default_value)

            value = self._coerce_value(question, value)
            self._validate(question, value, options)
            resolved[qid] = value

        for question in self._questions_for_mode(mode):
            _process_question(question)

            if question.get("id") == "packs":
                selected_packs = resolved.get("packs") or []
                pack_questions = self.discovery.discover_pack_setup_questions(selected_packs)

                for pack_q in pack_questions:
                    pack_mode = pack_q.get("mode", "basic")
                    if pack_mode == mode or mode == "advanced":
                        _process_question(pack_q)

        return resolved

    # ---------- Rendering helpers ----------
    def defaults_for_mode(self, mode: str) -> Dict[str, Any]:
        """Return default answers for all questions in a mode without prompting."""

        defaults: Dict[str, Any] = {}
        for question in self._questions_for_mode(mode):
            qid = question.get("id")
            if not qid:
                continue
            defaults[qid] = self._default_value(question)
        return defaults

    def render_modular_configs(self, answers: Dict[str, Any]) -> Dict[str, str]:
        """Render modular config files following core's config/*.yml pattern.

        Returns a dict mapping filename to YAML content:
            {
                "defaults.yml": "paths: ...",
                "packs.yml": "packs: ...",
                "validators.yml": "validators: ...",
                ...
            }

        This follows the same pattern as .edison/core/config/*.yaml where each
        domain has its own file for better separation of concerns.
        """
        context = self._context_with_defaults(answers)
        config_dict = self._config_dict(context)
        pack_configs = self._render_pack_configs(context)

        configs: Dict[str, str] = {}

        # defaults.yml - paths and project metadata
        defaults_config = {
            "paths": config_dict.get("paths", {}),
            "project": config_dict.get("project", {}),
        }
        if config_dict.get("database"):
            defaults_config["database"] = config_dict["database"]
        if config_dict.get("auth"):
            defaults_config["auth"] = config_dict["auth"]
        configs["defaults.yml"] = yaml.safe_dump(defaults_config, sort_keys=False)

        # packs.yml - enabled packs and pack-specific config
        packs_config = {
            "packs": {
                "enabled": config_dict.get("project", {}).get("packs", [])
            }
        }
        if pack_configs:
            packs_config["pack_config"] = pack_configs
        configs["packs.yml"] = yaml.safe_dump(packs_config, sort_keys=False)

        # validators.yml - validator configuration
        if config_dict.get("validators"):
            configs["validators.yml"] = yaml.safe_dump(
                {"validators": config_dict["validators"]},
                sort_keys=False
            )

        # delegation.yml - agents configuration
        if config_dict.get("agents"):
            configs["delegation.yml"] = yaml.safe_dump(
                {"agents": config_dict["agents"]},
                sort_keys=False
            )

        # orchestrators.yml - IDE orchestrators
        if config_dict.get("orchestrators"):
            configs["orchestrators.yml"] = yaml.safe_dump(
                {"orchestrators": config_dict["orchestrators"]},
                sort_keys=False
            )

        # worktrees.yml - worktree configuration
        if config_dict.get("worktrees"):
            configs["worktrees.yml"] = yaml.safe_dump(
                {"worktrees": config_dict["worktrees"]},
                sort_keys=False
            )

        # workflow.yml - task and session states
        if config_dict.get("workflow"):
            configs["workflow.yml"] = yaml.safe_dump(
                {"workflow": config_dict["workflow"]},
                sort_keys=False
            )

        # tdd.yml - TDD enforcement rules
        if config_dict.get("tdd"):
            configs["tdd.yml"] = yaml.safe_dump(
                {"tdd": config_dict["tdd"]},
                sort_keys=False
            )

        # ci.yml - CI commands
        if config_dict.get("ci"):
            configs["ci.yml"] = yaml.safe_dump(
                {"ci": config_dict["ci"]},
                sort_keys=False
            )

        return configs

    def render_readme_template(self, answers: Dict[str, Any]) -> str:
        """Render the README template using provided answers."""

        context = self._context_with_defaults(answers)
        template_path = self.edison_core / "templates" / "setup" / "project-readme.md.template"

        if Template is not None and template_path.exists():
            try:
                text = template_path.read_text(encoding="utf-8")
                return Template(text).render(**context)
            except Exception:
                pass

        tech_stack = context.get("tech_stack") or []
        tech_label = ", ".join(tech_stack) if tech_stack else ""
        config_dir = context.get("project_config_dir", ".agents")
        management_dir = context.get("project_management_dir", ".project")

        return (
            dedent(
                f"""
                # Edison Framework Setup for {context.get('project_name', '')}

                Welcome to your newly initialized Edison workspace. The `edison setup` wizard
                generated baseline configuration under `{config_dir}/config/` using a modular
                structure where each domain has its own file. This follows the same pattern as
                `.edison/core/config/*.yaml` for consistency and maintainability.

                ## Generated Structure

                - `{config_dir}/config/defaults.yml` — paths and project metadata (type: {context.get('project_type', '')}, db: {context.get('database', '')})
                - `{config_dir}/config/packs.yml` — enabled packs: {tech_label}
                - `{config_dir}/config/validators.yml` — validator configuration
                - `{config_dir}/config/delegation.yml` — agents and delegation settings
                - `{config_dir}/config/ci.yml` — CI/CD commands (lint, test, build, type-check)
                - `{config_dir}/config/tdd.yml` — TDD enforcement rules
                - `{config_dir}/config/worktrees.yml` — git worktree settings
                - `{config_dir}/config/workflow.yml` — task and session lifecycle states
                - `{config_dir}/guidelines/` — team guidelines and conventions
                - `{management_dir}/` — project management artifacts (tasks/sessions)

                ## Configuration Pattern

                Configuration follows this precedence (lowest → highest):
                1. Core defaults: `.edison/core/config/*.yaml`
                2. Project overrides: `{config_dir}/config/*.yml` (this directory)
                3. Environment variables: `EDISON_*`

                Each domain has its own file for better separation of concerns. To modify settings:
                - Edit the relevant `config/*.yml` file directly
                - Use `edison configure` for interactive menu-driven changes
                - Override via environment: `EDISON_tdd__enforcement=strict`

                ## Next Steps

                1. Review `{config_dir}/config/*.yml` files and adjust as needed
                2. Add project-specific guidelines to `{config_dir}/guidelines/`
                3. Run `edison compose all` to generate IDE integrations (commands/hooks/settings)
                4. Keep `{config_dir}/` committed so teammates share the same automation surface

                ## Support

                - `edison utils doctor` — verify your environment
                - `edison configure` — interactive configuration menu
                - `edison config edison-config` — inspect merged configuration
                - See `.edison/core/docs/HELP_SYSTEM_TEMPLATE.md` for CLI help
                """
            ).strip()
            + "\n"
        )

    # ---------- Internal helpers ----------
    def _render_pack_configs(self, context: Dict[str, Any]) -> Dict[str, Any]:
        selected_packs = context.get("packs") or []
        pack_configs: Dict[str, Any] = {}

        for pack in selected_packs:
            pack_setup_path = self.edison_core.parent / "packs" / pack / "config" / "setup.yml"
            if not pack_setup_path.exists():
                continue

            pack_setup = yaml.safe_load(pack_setup_path.read_text(encoding="utf-8")) or {}
            config_template = (pack_setup.get("setup") or {}).get("config_template") or {}
            if not config_template:
                continue

            rendered = self._render_template_dict(config_template, context)
            if isinstance(rendered, dict) and len(rendered) == 1 and pack in rendered:
                pack_configs[pack] = rendered[pack]
            else:
                pack_configs[pack] = rendered

        return pack_configs

    def _render_template_dict(self, template_obj: Any, context: Dict[str, Any]) -> Any:
        if isinstance(template_obj, dict):
            return {k: self._render_template_dict(v, context) for k, v in template_obj.items()}
        if isinstance(template_obj, list):
            return [self._render_template_dict(v, context) for v in template_obj]
        if isinstance(template_obj, str):
            return self._render_template_value(template_obj, context)
        return template_obj

    def _render_template_value(self, value: str, context: Dict[str, Any]) -> Any:
        full_match = re.fullmatch(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", value)
        if full_match:
            key = full_match.group(1)
            return context.get(key, "")

        if Template is not None:
            try:
                return Template(value).render(**context)
            except Exception:
                pass

        pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
        return pattern.sub(lambda m: str(context.get(m.group(1), "")), value)

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        with self.config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)  # type: ignore[no-untyped-call]
            return data or {}

    def _questions_for_mode(self, mode: str) -> List[Dict[str, Any]]:
        setup = self.config.get("setup") or {}
        basic = setup.get("basic") or []
        advanced = setup.get("advanced") or []
        if mode == "basic":
            return list(basic)
        if mode == "advanced":
            return list(basic) + list(advanced)
        raise ValueError(f"Unknown setup mode: {mode}")

    def _context_with_defaults(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Merge provided answers with defaults and detected values."""

        context: Dict[str, Any] = {}
        # Defaults from both modes
        context.update(self.defaults_for_mode("basic"))
        context.update(self.defaults_for_mode("advanced"))
        # Provided answers override defaults
        context.update(answers or {})

        # Ensure detected values are applied when answers left blank
        context.setdefault("project_name", self.detected.get("project_name"))
        context.setdefault("project_type", self.detected.get("project_type"))

        # Normalise list fields
        for key in ("tech_stack", "packs", "orchestrators", "validators", "agents", "task_states", "session_states"):
            val = context.get(key)
            if val is None:
                context[key] = []

        # Path defaults
        context.setdefault("project_config_dir", ".agents")
        mgmt_path = get_management_paths(self.repo_root).get_management_root()
        try:
            mgmt_rel = str(mgmt_path.relative_to(self.repo_root))
        except Exception:
            mgmt_rel = str(mgmt_path)
        if "project_management_dir" not in (answers or {}):
            context["project_management_dir"] = mgmt_rel

        return context

    def _config_dict(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build a YAML-friendly config dictionary from context."""

        return {
            "paths": {
                "config_dir": context.get("project_config_dir", ".agents"),
                "management_dir": context.get("project_management_dir", ".project"),
            },
            "project": {
                "name": context.get("project_name", ""),
                "type": context.get("project_type", ""),
                "tech_stack": context.get("tech_stack") or [],
                "packs": context.get("packs") or [],
            },
            "database": context.get("database", ""),
            "auth": {"provider": context.get("auth_provider", "")},
            "orchestrators": context.get("orchestrators") or [],
            "validators": {"enabled": context.get("validators") or []},
            "agents": {"enabled": context.get("agents") or []},
            "worktrees": {"enabled": bool(context.get("enable_worktrees"))},
            "workflow": {
                "tasks": {"states": context.get("task_states") or []},
                "sessions": {"states": context.get("session_states") or []},
            },
            "tdd": {
                "enforcement": context.get("tdd_enforcement", "warn"),
                "coverage_threshold": context.get("coverage_threshold", 0),
            },
            "ci": {
                "commands": {
                    "lint": context.get("ci_lint", ""),
                    "test": context.get("ci_test", ""),
                    "build": context.get("ci_build", ""),
                    "type-check": context.get("ci_type_check", ""),
                }
            },
        }

    def _resolve_options(self, question: Dict[str, Any], resolved: Dict[str, Any]) -> List[Any]:
        source = question.get("source", "static")
        if source == "static":
            return list(question.get("options") or [])
        if source == "discover_packs":
            return self.discovery.discover_packs()
        if source == "discover_orchestrators":
            return self.discovery.discover_orchestrators()
        if source == "discover_validators":
            packs = resolved.get("packs") or []
            return self.discovery.discover_validators(packs)
        if source == "discover_agents":
            packs = resolved.get("packs") or []
            return self.discovery.discover_agents(packs)
        return []

    def _default_value(self, question: Dict[str, Any]) -> Any:
        raw_default = question.get("default")
        if isinstance(raw_default, str):
            return self._render_templates(raw_default)
        if isinstance(raw_default, (list, dict)):
            return copy.deepcopy(raw_default)
        return raw_default

    def _render_templates(self, value: str) -> str:
        pattern = re.compile(r"\{\{\s*detected\.([a-zA-Z0-9_]+)\s*\}\}")

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(self.detected.get(key, ""))

        return pattern.sub(_replace, value)

    def _prompt(self, question: Dict[str, Any], options: List[Any], default: Any) -> Any:
        prompt = question.get("prompt", question.get("id", ""))
        suffix = f" [{default}]" if default not in (None, "") else ""
        raw = input(f"{prompt}{suffix}: ")
        if raw == "" and default is not None:
            return default
        if question.get("type") == "multiselect":
            return [part.strip() for part in raw.split(",") if part.strip()]
        if question.get("type") == "list":
            return [part.strip() for part in raw.split(",") if part.strip()]
        if question.get("type") == "boolean":
            return raw.lower() in ("y", "yes", "true", "1")
        if question.get("type") == "integer":
            return int(raw)
        return raw

    def _coerce_value(self, question: Dict[str, Any], value: Any) -> Any:
        qtype = question.get("type")
        if qtype == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes", "y", "on")
            return bool(value)

        if qtype == "integer":
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip():
                return int(value.strip())
            raise ValueError(f"Expected integer for {question.get('id')}")

        if qtype == "list":
            if isinstance(value, list):
                return [str(v) for v in value]
            if isinstance(value, str):
                return [part.strip() for part in value.split(",") if part.strip()]
            raise ValueError(f"Expected list for {question.get('id')}")

        if qtype == "multiselect":
            if isinstance(value, list):
                return [str(v) for v in value]
            if isinstance(value, str):
                return [part.strip() for part in value.split(",") if part.strip()]
            raise ValueError(f"Expected list for {question.get('id')}")

        # Default: string passthrough
        return value

    def _validate(self, question: Dict[str, Any], value: Any, options: List[Any]) -> None:
        qid = question.get("id", "<unknown>")
        required = question.get("required", False)
        if required and (value is None or value == "" or value == []):
            raise ValueError(f"{qid} is required")

        qtype = question.get("type")
        if qtype == "choice":
            if options and value not in options:
                raise ValueError(f"{qid} must be one of {options}")

        if qtype == "multiselect":
            if not isinstance(value, list):
                raise ValueError(f"{qid} must be a list")
            invalid = [v for v in value if options and v not in options]
            if invalid:
                raise ValueError(f"{qid} contains invalid selections: {invalid}")

        if qtype == "integer":
            if not isinstance(value, int):
                raise ValueError(f"{qid} must be an integer")

        validation = question.get("validation")
        if validation:
            range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", validation)
            if range_match and isinstance(value, int):
                low, high = int(range_match.group(1)), int(range_match.group(2))
                if not (low <= value <= high):
                    raise ValueError(f"{qid} must be between {low} and {high}")
            elif isinstance(value, str):
                if not re.match(validation, value):
                    raise ValueError(f"{qid} failed validation pattern {validation}")
