"""Config generation for setup questionnaire."""
from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

from edison.core.file_io.utils import read_yaml_safe, dump_yaml_string

from .context import build_context_with_defaults, build_config_dict
from .templates import render_readme_template as _render_readme, render_template_dict

if TYPE_CHECKING:
    from .base import SetupQuestionnaire


def render_modular_configs(
    questionnaire: "SetupQuestionnaire",
    answers: Dict[str, Any]
) -> Dict[str, str]:
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
    context = build_context_with_defaults(questionnaire, answers)
    config_dict = build_config_dict(context)
    pack_configs = _render_pack_configs(questionnaire, context)

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
    configs["defaults.yml"] = dump_yaml_string(defaults_config, sort_keys=False)

    # packs.yml - enabled packs and pack-specific config
    packs_config = {
        "packs": {
            "enabled": config_dict.get("project", {}).get("packs", [])
        }
    }
    if pack_configs:
        packs_config["pack_config"] = pack_configs
    configs["packs.yml"] = dump_yaml_string(packs_config, sort_keys=False)

    # validators.yml - validator configuration
    if config_dict.get("validators"):
        configs["validators.yml"] = dump_yaml_string(
            {"validators": config_dict["validators"]},
            sort_keys=False
        )

    # delegation.yml - agents configuration
    if config_dict.get("agents"):
        configs["delegation.yml"] = dump_yaml_string(
            {"agents": config_dict["agents"]},
            sort_keys=False
        )

    # orchestrators.yml - IDE orchestrators
    if config_dict.get("orchestrators"):
        configs["orchestrators.yml"] = dump_yaml_string(
            {"orchestrators": config_dict["orchestrators"]},
            sort_keys=False
        )

    # worktrees.yml - worktree configuration
    if config_dict.get("worktrees"):
        configs["worktrees.yml"] = dump_yaml_string(
            {"worktrees": config_dict["worktrees"]},
            sort_keys=False
        )

    # workflow.yml - task and session states
    if config_dict.get("workflow"):
        configs["workflow.yml"] = dump_yaml_string(
            {"workflow": config_dict["workflow"]},
            sort_keys=False
        )

    # tdd.yml - TDD enforcement rules
    if config_dict.get("tdd"):
        configs["tdd.yml"] = dump_yaml_string(
            {"tdd": config_dict["tdd"]},
            sort_keys=False
        )

    # ci.yml - CI commands
    if config_dict.get("ci"):
        configs["ci.yml"] = dump_yaml_string(
            {"ci": config_dict["ci"]},
            sort_keys=False
        )

    return configs


def render_readme_template(
    questionnaire: "SetupQuestionnaire",
    answers: Dict[str, Any]
) -> str:
    """Render the README template using provided answers."""
    context = build_context_with_defaults(questionnaire, answers)
    return _render_readme(questionnaire, context)


# Re-export template utilities for backward compatibility
from .templates import render_template_value


# ========== Internal helpers ==========

def _render_pack_configs(
    questionnaire: "SetupQuestionnaire",
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Render pack-specific configuration sections."""
    selected_packs = context.get("packs") or []
    pack_configs: Dict[str, Any] = {}

    for pack in selected_packs:
        pack_setup_path = questionnaire.edison_core.parent / "packs" / pack / "config" / "setup.yml"
        if not pack_setup_path.exists():
            continue

        pack_setup = read_yaml_safe(pack_setup_path, default={})
        config_template = (pack_setup.get("setup") or {}).get("config_template") or {}
        if not config_template:
            continue

        rendered = render_template_dict(config_template, context)
        if isinstance(rendered, dict) and len(rendered) == 1 and pack in rendered:
            pack_configs[pack] = rendered[pack]
        else:
            pack_configs[pack] = rendered

    return pack_configs
