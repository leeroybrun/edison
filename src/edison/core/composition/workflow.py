from __future__ import annotations

"""Workflow loop instructions for orchestrators.

Loads workflow instructions from configuration instead of hardcoding them.
"""

from typing import Dict

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def get_workflow_loop_instructions() -> Dict:
    """Return workflow loop instructions for orchestrators.

    Loads from composition.yaml config if available, falls back to
    hardcoded defaults for backward compatibility.

    Returns:
        Dict with command, frequency, and readOrder instructions
    """
    # Try to load from config first
    from edison.data import get_data_path

    composition_config_path = get_data_path("config", "composition.yaml")

    if composition_config_path.exists() and yaml is not None:
        try:
            config_data = yaml.safe_load(composition_config_path.read_text(encoding="utf-8"))
            if config_data and isinstance(config_data, dict):
                composition_cfg = config_data.get("composition", {})
                if isinstance(composition_cfg, dict):
                    workflow_cfg = composition_cfg.get("workflowLoop")
                    if isinstance(workflow_cfg, dict):
                        return workflow_cfg
        except Exception:
            pass  # Fall back to defaults

    # Hardcoded fallback (backward compatibility)
    return {
        "command": "scripts/session next <session-id>",
        "frequency": "Before EVERY action",
        "readOrder": [
            "1. 📋 APPLICABLE RULES (read FIRST)",
            "2. 🎯 RECOMMENDED ACTIONS (read AFTER rules)",
            "3. 🤖 DELEGATION HINT (follow priority chain)",
            "4. 🔍 VALIDATORS (auto-detected from git diff)",
        ],
    }


__all__ = [
    "get_workflow_loop_instructions",
]
