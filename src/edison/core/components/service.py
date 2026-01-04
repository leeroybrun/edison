from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from edison.core.config import ConfigManager
from edison.core.config.domains.composition import CompositionConfig
from edison.core.config.domains.packs import PacksConfig
from edison.core.registries.validators import ValidatorRegistry
from edison.core.utils.io import read_yaml, write_yaml
from edison.core.utils.merge import deep_merge
from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.text.templates import render_template_dict

ComponentKind = Literal["pack", "validator", "adapter", "agent"]


@dataclass(frozen=True)
class ComponentToggleResult:
    kind: ComponentKind
    component_id: str
    enabled: bool
    config_path: Path


@dataclass(frozen=True)
class ComponentSetupSpec:
    questions: list[dict[str, Any]]
    config_template: dict[str, Any]
    required_config: list[str]
    optional_config: list[str]
    instructions: str | None = None


@dataclass(frozen=True)
class ComponentStatus:
    kind: ComponentKind
    component_id: str
    available: bool
    enabled: bool
    missing_required_config: list[str]
    config_sources: list[str]


def _normalize_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        s = str(item).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


class ComponentService:
    """Enable/disable Edison components via project config.

    Components:
    - pack: `packs.active` list
    - validator: `validation.validators.<id>.enabled`
    - adapter: `composition.adapters.<id>.enabled`
    - agent: `agents.disabled` denylist (and optional `agents.enabled` allowlist)
    """

    def __init__(self, *, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.cfg = ConfigManager(repo_root=self.repo_root)

        project_cfg_root = get_project_config_dir(self.repo_root, create=True)
        self.project_config_dir = project_cfg_root / "config"
        self.project_config_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def enable(self, kind: ComponentKind, component_id: str) -> ComponentToggleResult:
        return self._toggle(kind, component_id, enabled=True)

    def disable(self, kind: ComponentKind, component_id: str) -> ComponentToggleResult:
        return self._toggle(kind, component_id, enabled=False)

    def list_available(self, kind: ComponentKind) -> list[str]:
        if kind == "pack":
            return list(PacksConfig(repo_root=self.repo_root).available_packs)
        if kind == "validator":
            return ValidatorRegistry(project_root=self.repo_root).list_names()
        if kind == "adapter":
            return sorted(CompositionConfig(repo_root=self.repo_root).adapters.keys())
        if kind == "agent":
            from edison.core.composition.registries.agent_prompts import AgentPromptRegistry

            return AgentPromptRegistry(project_root=self.repo_root).list_names()
        raise ValueError(f"Unknown component kind: {kind}")

    def get_status(self, kind: ComponentKind, component_id: str) -> ComponentStatus:
        cid = str(component_id).strip()
        if not cid:
            raise ValueError("component_id is required")

        available_ids = set(self.list_available(kind))
        available = cid in available_ids
        enabled = False
        sources: list[str] = []

        cfg = self.cfg.load_config(validate=False, include_packs=True)
        if kind == "pack":
            enabled = cid in ((cfg.get("packs") or {}).get("active") or [])
            sources = ["packs.active"]
        elif kind == "validator":
            entry = ((cfg.get("validation") or {}).get("validators") or {}).get(cid) or {}
            enabled = bool(entry.get("enabled", True)) if isinstance(entry, dict) else True
            sources = [f"validation.validators.{cid}.enabled"]
        elif kind == "adapter":
            entry = ((cfg.get("composition") or {}).get("adapters") or {}).get(cid) or {}
            enabled = bool(entry.get("enabled", True)) if isinstance(entry, dict) else True
            sources = [f"composition.adapters.{cid}.enabled"]
        elif kind == "agent":
            agents = cfg.get("agents") or {}
            allow = []
            deny = []
            if isinstance(agents, dict):
                allow = _normalize_list(agents.get("enabled"))
                deny = _normalize_list(agents.get("disabled"))
            if allow:
                enabled = cid in set(allow)
                sources = ["agents.enabled"]
            else:
                enabled = cid not in set(deny)
                sources = ["agents.disabled"]
        else:
            raise ValueError(f"Unknown component kind: {kind}")

        missing_required = []
        try:
            spec = self._load_setup_spec(kind, cid)
            if spec is not None:
                missing_required = self._missing_required_config(spec.required_config)
        except Exception:
            missing_required = []

        return ComponentStatus(
            kind=kind,
            component_id=cid,
            available=available,
            enabled=enabled,
            missing_required_config=missing_required,
            config_sources=sources,
        )

    def configure(
        self,
        kind: ComponentKind,
        component_id: str,
        *,
        interactive: bool,
        provided_answers: dict[str, Any] | None = None,
        mode: str = "basic",
    ) -> list[Path]:
        """Configure a component using its setup spec (if available).

        For packs, this uses `packs/<id>/config/setup.yml` and writes to `packs.yaml`
        under `pack_config.<pack>`.

        For validators/adapters/agents, this uses an optional `setup` block
        co-located under their config entries and deep-merges the rendered
        `config_template` into the appropriate project config file.
        """
        cid = str(component_id).strip()
        if not cid:
            raise ValueError("component_id is required")

        spec = self._load_setup_spec(kind, cid)
        if spec is None:
            return []

        answers = self._run_questions(
            spec.questions,
            interactive=interactive,
            provided_answers=provided_answers or {},
            mode=mode,
        )

        rendered = render_template_dict(spec.config_template, answers)
        written: list[Path] = []

        if kind == "pack":
            written.append(self._apply_pack_config_template(cid, rendered))
        elif kind == "validator":
            written.append(self._apply_template_patch(self._validation_config_path(), rendered))
        elif kind == "adapter":
            written.append(self._apply_template_patch(self._composition_config_path(), rendered))
        elif kind == "agent":
            written.append(self._apply_template_patch(self._agents_config_path(), rendered))
        else:
            raise ValueError(f"Unknown component kind: {kind}")

        missing = self._missing_required_config(spec.required_config)
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return written

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _toggle(
        self, kind: ComponentKind, component_id: str, *, enabled: bool
    ) -> ComponentToggleResult:
        cid = str(component_id).strip()
        if not cid:
            raise ValueError("component_id is required")

        if kind == "pack":
            return self._toggle_pack(cid, enabled=enabled)
        if kind == "validator":
            return self._toggle_validator(cid, enabled=enabled)
        if kind == "adapter":
            return self._toggle_adapter(cid, enabled=enabled)
        if kind == "agent":
            return self._toggle_agent(cid, enabled=enabled)

        raise ValueError(f"Unknown component kind: {kind}")

    def _packs_config_path(self) -> Path:
        # Canonical filename is packs.yaml (bundled config uses this).
        return self.project_config_dir / "packs.yaml"

    def _validation_config_path(self) -> Path:
        return self.project_config_dir / "validation.yaml"

    def _composition_config_path(self) -> Path:
        return self.project_config_dir / "composition.yaml"

    def _agents_config_path(self) -> Path:
        return self.project_config_dir / "agents.yaml"

    def _toggle_pack(self, pack: str, *, enabled: bool) -> ComponentToggleResult:
        available = set(PacksConfig(repo_root=self.repo_root).available_packs)
        if pack not in available:
            raise ValueError(f"Unknown pack: {pack}")

        path = self._packs_config_path()
        data = read_yaml(path, default={}) if path.exists() else {}
        packs_cfg = data.get("packs") if isinstance(data, dict) else None
        if not isinstance(packs_cfg, dict):
            packs_cfg = {}
            data = {} if not isinstance(data, dict) else data
            data["packs"] = packs_cfg

        active = _normalize_list(packs_cfg.get("active"))
        if enabled:
            active.append(pack)
        else:
            active = [p for p in active if p != pack]
        packs_cfg["active"] = _dedupe(active)

        write_yaml(path, data)
        return ComponentToggleResult(
            kind="pack", component_id=pack, enabled=enabled, config_path=path
        )

    def _toggle_validator(self, validator_id: str, *, enabled: bool) -> ComponentToggleResult:
        vreg = ValidatorRegistry(project_root=self.repo_root)
        if not vreg.exists(validator_id):
            raise ValueError(f"Unknown validator: {validator_id}")

        path = self._validation_config_path()
        data = read_yaml(path, default={}) if path.exists() else {}
        if not isinstance(data, dict):
            data = {}
        validation = data.get("validation")
        if not isinstance(validation, dict):
            validation = {}
            data["validation"] = validation
        validators = validation.get("validators")
        if not isinstance(validators, dict):
            validators = {}
            validation["validators"] = validators

        entry = validators.get(validator_id)
        if not isinstance(entry, dict):
            entry = {}
            validators[validator_id] = entry
        entry["enabled"] = bool(enabled)

        write_yaml(path, data)
        return ComponentToggleResult(
            kind="validator", component_id=validator_id, enabled=enabled, config_path=path
        )

    def _toggle_adapter(self, adapter_id: str, *, enabled: bool) -> ComponentToggleResult:
        comp = CompositionConfig(repo_root=self.repo_root)
        if adapter_id not in comp.adapters:
            raise ValueError(f"Unknown adapter: {adapter_id}")

        path = self._composition_config_path()
        data = read_yaml(path, default={}) if path.exists() else {}
        if not isinstance(data, dict):
            data = {}
        composition = data.get("composition")
        if not isinstance(composition, dict):
            composition = {}
            data["composition"] = composition
        adapters = composition.get("adapters")
        if not isinstance(adapters, dict):
            adapters = {}
            composition["adapters"] = adapters

        entry = adapters.get(adapter_id)
        if not isinstance(entry, dict):
            entry = {}
            adapters[adapter_id] = entry
        entry["enabled"] = bool(enabled)

        write_yaml(path, data)
        return ComponentToggleResult(
            kind="adapter", component_id=adapter_id, enabled=enabled, config_path=path
        )

    def _toggle_agent(self, agent_id: str, *, enabled: bool) -> ComponentToggleResult:
        # Validate existence against composed agent prompt templates (core + active packs + overlays).
        from edison.core.composition.registries.agent_prompts import AgentPromptRegistry

        reg = AgentPromptRegistry(project_root=self.repo_root)
        if agent_id not in reg.discover_all_unfiltered().keys():
            raise ValueError(f"Unknown agent: {agent_id}")

        path = self._agents_config_path()
        data = read_yaml(path, default={}) if path.exists() else {}
        if not isinstance(data, dict):
            data = {}
        agents = data.get("agents")
        if not isinstance(agents, dict):
            agents = {}
            data["agents"] = agents

        enabled_allow = _normalize_list(agents.get("enabled"))
        disabled = _normalize_list(agents.get("disabled"))

        if enabled_allow:
            if enabled and agent_id not in enabled_allow:
                enabled_allow.append(agent_id)
            if not enabled:
                enabled_allow = [a for a in enabled_allow if a != agent_id]
            agents["enabled"] = _dedupe(enabled_allow)

        if enabled:
            disabled = [a for a in disabled if a != agent_id]
        else:
            disabled.append(agent_id)
        agents["disabled"] = _dedupe(disabled)

        write_yaml(path, data)
        return ComponentToggleResult(
            kind="agent", component_id=agent_id, enabled=enabled, config_path=path
        )

    def _load_setup_spec(self, kind: ComponentKind, component_id: str) -> ComponentSetupSpec | None:
        if kind == "pack":
            from edison.core.packs.paths import iter_pack_dirs

            pack_dir = None
            for pack_name, path, _kind in iter_pack_dirs(self.repo_root):
                if pack_name == component_id:
                    pack_dir = path
                    break
            if pack_dir is None:
                raise ValueError(f"Unknown pack: {component_id}")
            setup_path = pack_dir / "config" / "setup.yml"
            if not setup_path.exists():
                return None
            raw = read_yaml(setup_path, default={})
            setup = (raw.get("setup") or {}) if isinstance(raw, dict) else {}
            return self._parse_setup_block(setup)

        cfg = self.cfg.load_config(validate=False, include_packs=True)
        if kind == "validator":
            entry = ((cfg.get("validation") or {}).get("validators") or {}).get(component_id) or {}
            setup = entry.get("setup") if isinstance(entry, dict) else None
            return self._parse_setup_block(setup) if setup else None
        if kind == "adapter":
            entry = ((cfg.get("composition") or {}).get("adapters") or {}).get(component_id) or {}
            setup = entry.get("setup") if isinstance(entry, dict) else None
            return self._parse_setup_block(setup) if setup else None
        if kind == "agent":
            agents = cfg.get("agents") or {}
            setup = None
            if isinstance(agents, dict):
                catalog = agents.get("catalog") or {}
                if isinstance(catalog, dict):
                    entry = catalog.get(component_id) or {}
                    if isinstance(entry, dict):
                        setup = entry.get("setup")
            return self._parse_setup_block(setup) if setup else None

        return None

    def _parse_setup_block(self, raw: Any) -> ComponentSetupSpec:
        if not isinstance(raw, dict):
            return ComponentSetupSpec(
                questions=[], config_template={}, required_config=[], optional_config=[]
            )

        questions_raw = raw.get("questions") or []
        questions: list[dict[str, Any]] = []
        if isinstance(questions_raw, list):
            questions = [q for q in questions_raw if isinstance(q, dict)]

        tmpl = raw.get("config_template") or {}
        config_template: dict[str, Any] = tmpl if isinstance(tmpl, dict) else {}

        require = raw.get("require") or {}
        required_config: list[str] = []
        if isinstance(require, dict):
            cfg_req = require.get("config") or []
            if isinstance(cfg_req, list):
                for item in cfg_req:
                    if isinstance(item, str) and item.strip():
                        required_config.append(item.strip())
                    elif isinstance(item, dict):
                        p = str(item.get("path") or item.get("key") or "").strip()
                        if p:
                            required_config.append(p)

        optional_config: list[str] = []
        opt_raw = raw.get("optional_config") or raw.get("optionalConfig") or []
        if isinstance(opt_raw, list):
            for item in opt_raw:
                if isinstance(item, str) and item.strip():
                    optional_config.append(item.strip())
                elif isinstance(item, dict):
                    p = str(item.get("path") or item.get("key") or "").strip()
                    if p:
                        optional_config.append(p)

        instructions = raw.get("instructions")
        inst = str(instructions) if instructions is not None else None

        return ComponentSetupSpec(
            questions=questions,
            config_template=config_template,
            required_config=required_config,
            optional_config=optional_config,
            instructions=inst,
        )

    def _missing_required_config(self, required: list[str]) -> list[str]:
        missing: list[str] = []
        if not required:
            return missing
        cfg = self.cfg.load_config(validate=False, include_packs=True)

        def _get(path: str) -> Any:
            cur: Any = cfg
            for part in path.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return None
            return cur

        for path in required:
            v = _get(path)
            if v is None:
                missing.append(path)
            elif isinstance(v, str) and v.strip() == "":
                missing.append(path)
            elif isinstance(v, list) and len(v) == 0:
                missing.append(path)
            elif isinstance(v, dict) and len(v) == 0:
                missing.append(path)
        return missing

    def _should_ask(self, question: dict[str, Any], ctx: dict[str, Any]) -> bool:
        cond = question.get("when")
        if not cond:
            return True

        def _eval_one(c: Any) -> bool:
            if not isinstance(c, dict):
                return True
            if "all" in c:
                items = c.get("all") or []
                if not isinstance(items, list):
                    return True
                return all(_eval_one(x) for x in items)
            qid = str(c.get("id") or "").strip()
            if not qid:
                return True
            actual = ctx.get(qid)
            if "equals" in c:
                return actual == c.get("equals")
            if "not_equals" in c:
                return actual != c.get("not_equals")
            if "in" in c:
                items = c.get("in") or []
                return actual in items
            return bool(actual)

        return _eval_one(cond)

    def _run_questions(
        self,
        questions: list[dict[str, Any]],
        *,
        interactive: bool,
        provided_answers: dict[str, Any],
        mode: str,
    ) -> dict[str, Any]:
        from edison.core.setup.questionnaire import prompts as q_prompts
        from edison.core.setup.questionnaire import validation as q_validation
        from edison.core.setup.questionnaire.base import SetupQuestionnaire

        questionnaire = SetupQuestionnaire(repo_root=self.repo_root)
        resolved: dict[str, Any] = {}

        def _include(q: dict[str, Any]) -> bool:
            qmode = str(q.get("mode") or "").strip().lower()
            if not qmode:
                return True
            if mode == "basic":
                return qmode == "basic"
            if mode == "advanced":
                return qmode in {"basic", "advanced"}
            return True

        for q in questions:
            if not _include(q):
                continue
            if not self._should_ask(q, resolved):
                continue
            qid = str(q.get("id") or "").strip()
            if not qid:
                continue

            options = q_prompts.resolve_options(questionnaire, q, resolved)
            default = q_prompts.resolve_default_value(questionnaire, q)
            value = provided_answers.get(qid, None)
            if value is None:
                if interactive:
                    value = q_prompts.prompt_user(q, options, default)
                else:
                    value = default

            if q.get("required") and (value is None or value == "" or value == []):
                raise ValueError(f"{qid} is required")

            coerced = q_validation.coerce_value(q, value)
            q_validation.validate_answer(q, coerced, options)
            resolved[qid] = coerced

        return resolved

    def _apply_template_patch(self, path: Path, patch: Any) -> Path:
        if not isinstance(patch, dict) or not patch:
            return path
        existing = read_yaml(path, default={}) if path.exists() else {}
        if not isinstance(existing, dict):
            existing = {}
        merged = deep_merge(existing, patch)
        write_yaml(path, merged)
        return path

    def _apply_pack_config_template(self, pack: str, rendered: Any) -> Path:
        # Write under `pack_config.<pack>` in packs.yaml.
        pack_cfg: Any = rendered
        if isinstance(rendered, dict) and len(rendered) == 1 and pack in rendered:
            pack_cfg = rendered.get(pack)

        path = self._packs_config_path()
        data = read_yaml(path, default={}) if path.exists() else {}
        if not isinstance(data, dict):
            data = {}
        if "pack_config" not in data or not isinstance(data.get("pack_config"), dict):
            data["pack_config"] = {}
        pack_config = data["pack_config"]
        assert isinstance(pack_config, dict)
        pack_config[pack] = pack_cfg
        write_yaml(path, data)
        return path
