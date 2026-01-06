from __future__ import annotations

from pathlib import Path

from edison.core.config import ConfigManager


def test_load_config_interpolates_single_brace_tokens(tmp_path: Path) -> None:
    """ConfigManager should expand `{PROJECT_*}` tokens after merge.

    This keeps the config values directly usable by runtime code while avoiding
    hardcoded `.edison` / `.project` paths in core YAML.
    """
    cfg = ConfigManager(tmp_path).load_config(validate=False)

    assert cfg["tasks"]["paths"]["root"] == ".project/tasks"

    assert cfg["logging"]["audit"]["path"] == ".project/logs/edison/audit.jsonl"


def test_load_config_does_not_touch_double_brace_template_vars(tmp_path: Path) -> None:
    """ConfigManager must not mutate Edison template vars like `{{PROJECT_EDISON_DIR}}`."""
    cfg = ConfigManager(tmp_path).load_config(validate=False)
    assert cfg["composition"]["content_types"]["agents"]["output_path"] == "{{PROJECT_EDISON_DIR}}/_generated/agents"


def test_load_config_interpolates_config_derived_tokens(tmp_path: Path) -> None:
    """Workflow guard messages may reference config-derived tokens like bundle filename."""
    cfg = ConfigManager(tmp_path).load_config(validate=False)

    qa_done = cfg["workflow"]["statemachine"]["qa"]["states"]["done"]
    validated_transition = next(t for t in qa_done["allowed_transitions"] if t["to"] == "validated")
    has_bundle = next(c for c in validated_transition["conditions"] if c["name"] == "has_bundle_approval")

    assert "validation-summary.md" in has_bundle["error"]
