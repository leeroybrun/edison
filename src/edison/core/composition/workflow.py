from __future__ import annotations

"""Workflow loop instructions for orchestrators.

T-016: NO LEGACY - Only loads from composition.yaml (NO hardcoded fallbacks).

Fail-fast design: Raises clear errors when configuration is missing or invalid.
Users must provide explicit workflowLoop configuration in composition.yaml.
"""

from typing import Dict

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def get_workflow_loop_instructions() -> Dict:
    """Return workflow loop instructions for orchestrators.

    T-016: NO LEGACY - Only loads from composition.yaml (NO hardcoded fallbacks).

    Raises:
        FileNotFoundError: If composition.yaml is missing
        ValueError: If composition.yaml is invalid or missing workflowLoop key
        ImportError: If yaml module is not available

    Returns:
        Dict with command, frequency, and readOrder instructions
    """
    # T-016: NO LEGACY - Require explicit configuration
    from edison.data import get_data_path
    from edison.core.file_io.utils import read_yaml_safe

    if yaml is None:
        raise ImportError(
            "yaml module required for workflow configuration. "
            "Install with: pip install pyyaml"
        )

    composition_config_path = get_data_path("config", "composition.yaml")

    if not composition_config_path.exists():
        raise FileNotFoundError(
            f"composition.yaml not found at {composition_config_path}\n"
            "T-016: NO LEGACY - Hardcoded fallbacks removed.\n"
            "Create composition.yaml with workflowLoop configuration."
        )

    try:
        config_data = read_yaml_safe(composition_config_path, raise_on_error=True)
    except Exception as e:
        raise ValueError(f"Failed to parse composition.yaml: {e}")

    if not config_data or not isinstance(config_data, dict):
        raise ValueError("composition.yaml is empty or invalid")

    composition_cfg = config_data.get("composition", {})
    if not isinstance(composition_cfg, dict):
        raise ValueError("composition.yaml missing 'composition' key")

    workflow_cfg = composition_cfg.get("workflowLoop")
    if not isinstance(workflow_cfg, dict):
        raise ValueError(
            "composition.yaml missing 'composition.workflowLoop' key\n"
            "T-016: NO LEGACY - Hardcoded fallbacks removed.\n"
            "Add workflowLoop configuration to composition.yaml"
        )

    # Validate required keys
    required_keys = ["command", "frequency", "readOrder"]
    missing = [k for k in required_keys if k not in workflow_cfg]
    if missing:
        raise ValueError(f"workflowLoop missing required keys: {missing}")

    return workflow_cfg


__all__ = [
    "get_workflow_loop_instructions",
]
