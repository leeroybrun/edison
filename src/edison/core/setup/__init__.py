"""Setup utilities package for Edison framework.

This module provides core setup functionality including:
- SetupDiscovery: Auto-discovery of packs, validators, agents, orchestrators
- SetupQuestionnaire: Interactive/programmatic setup questionnaire
- configure_project: High-level function for interactive project configuration

These are pure library classes with no CLI dependencies.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from .discovery import SetupDiscovery
from .questionnaire import SetupQuestionnaire


def configure_project(
    repo_root: Path,
    interactive: bool = True,
    mode: str = "basic",
    provided_answers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Configure a project using the setup questionnaire.

    Args:
        repo_root: Path to the project root directory
        interactive: If True, prompt user for input; if False, use defaults
        mode: Setup mode ('basic' or 'advanced')
        provided_answers: Pre-filled answers (bypasses prompting for those keys)

    Returns:
        Dict with 'success' boolean and either 'configs' or 'error' key
    """
    try:
        questionnaire = SetupQuestionnaire(
            repo_root=repo_root,
            assume_yes=not interactive,
        )

        answers = questionnaire.run(
            mode=mode,
            provided_answers=provided_answers,
            assume_yes=not interactive,
        )

        configs = questionnaire.render_modular_configs(answers)

        return {
            "success": True,
            "answers": answers,
            "configs": configs,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


__all__ = ["SetupDiscovery", "SetupQuestionnaire", "configure_project"]
