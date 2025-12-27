"""Dynamic setup questionnaire powered by setup.yaml."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.io import read_yaml
from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.paths import PathResolver
from edison.data import get_data_path
from ..discovery import SetupDiscovery

from . import prompts
from . import validation
from . import rendering


class SetupQuestionnaire:
    """Execute setup questions defined in setup.yaml.
    
    Architecture:
    - edison_core: ALWAYS bundled edison.data directory
    - config_path: ALWAYS bundled edison.data/config/setup.yaml
    - project_dir: <project-config-dir>/ for project overrides
    - NO <project-config-dir>/core/ - that is legacy
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        edison_core: Optional[Path] = None,
        config_path: Optional[Path] = None,
        discovery: Optional[SetupDiscovery] = None,
        assume_yes: bool = False,
    ) -> None:
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        
        # Edison core is ALWAYS from bundled data
        self.edison_core = edison_core or Path(get_data_path(""))
        
        # Config path is ALWAYS bundled setup.yaml
        self.config_path = config_path or get_data_path("config", "setup.yaml")
        
        # Project directory for overrides
        self.project_dir = get_project_config_dir(self.repo_root, create=False)
        
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
        """Run the questionnaire and collect answers.

        Args:
            mode: Setup mode ('basic' or 'advanced')
            provided_answers: Pre-filled answers (bypasses prompting)
            assume_yes: If True, use defaults without prompting

        Returns:
            Dictionary of resolved answers
        """
        provided: Dict[str, Any] = provided_answers or {}
        resolved: Dict[str, Any] = {}
        effective_assume_yes = self.assume_yes if assume_yes is None else assume_yes

        def _should_ask(question: Dict[str, Any]) -> bool:
            """Return True if a question should be asked given current answers.

            Supports an optional `when:` clause in setup.yaml to avoid asking irrelevant
            questions (e.g. sharedState details when worktrees are disabled).

            Condition grammar (YAML):
            - when:
                id: <question_id>
                equals: <value>         # default when missing: True
              OR
              when:
                all:
                  - {id: ..., equals: ...}
                  - {id: ..., equals: ...}
              OR
              when:
                any:
                  - {id: ..., equals: ...}
                  - {id: ..., equals: ...}
            """
            cond = question.get("when")
            if not cond:
                return True

            # For gating, allow provided answers to influence visibility even if the
            # question that sets them appears later in the file.
            ctx: Dict[str, Any] = dict(resolved)
            for k, v in provided.items():
                if k not in ctx:
                    ctx[k] = v

            def _eval_one(c: Any) -> bool:
                if not isinstance(c, dict):
                    return bool(c)
                if "all" in c:
                    items = c.get("all") or []
                    return all(_eval_one(x) for x in items)
                if "any" in c:
                    items = c.get("any") or []
                    return any(_eval_one(x) for x in items)
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
                # Default: treat presence as truthy check
                return bool(actual)

            return _eval_one(cond)

        def _process_question(question: Dict[str, Any]) -> None:
            qid = question.get("id")
            if not qid:
                return

            options = prompts.resolve_options(self, question, resolved)
            default_value = prompts.resolve_default_value(self, question)
            value = provided.get(qid, None)

            if value is None:
                if effective_assume_yes:
                    value = copy.deepcopy(default_value)
                else:
                    value = prompts.prompt_user(question, options, default_value)

            value = validation.coerce_value(question, value)
            validation.validate_answer(question, value, options)
            resolved[qid] = value

        for question in self._questions_for_mode(mode):
            if not _should_ask(question):
                continue
            _process_question(question)

            if question.get("id") == "packs":
                selected_packs = resolved.get("packs") or []
                pack_questions = self.discovery.discover_pack_setup_questions(selected_packs)

                for pack_q in pack_questions:
                    pack_mode = pack_q.get("mode", "basic")
                    if pack_mode == mode or mode == "advanced":
                        if not _should_ask(pack_q):
                            continue
                        _process_question(pack_q)

        return resolved

    def defaults_for_mode(self, mode: str) -> Dict[str, Any]:
        """Return default answers for all questions in a mode without prompting."""
        defaults: Dict[str, Any] = {}
        for question in self._questions_for_mode(mode):
            qid = question.get("id")
            if not qid:
                continue
            defaults[qid] = prompts.resolve_default_value(self, question)
        return defaults

    def render_modular_configs(self, answers: Dict[str, Any]) -> Dict[str, str]:
        """Render modular config files following <project-config-dir>/config/*.yml pattern.

        Returns a dict mapping filename to YAML content:
            {
                "defaults.yml": "paths: ...",
                "packs.yml": "packs: ...",
                "validators.yml": "validators: ...",
                ...
            }

        This follows the project config pattern where each domain has its own
        file for better separation of concerns.
        """
        return rendering.render_modular_configs(self, answers)

    def render_readme_template(self, answers: Dict[str, Any]) -> str:
        """Render the README template using provided answers."""
        return rendering.render_readme_template(self, answers)

    # ---------- Internal helpers ----------
    def _load_config(self) -> Dict[str, Any]:
        """Load setup.yaml configuration."""
        return read_yaml(self.config_path, default={})

    def _questions_for_mode(self, mode: str) -> List[Dict[str, Any]]:
        """Get list of questions for a given mode."""
        setup = self.config.get("setup") or {}
        basic = setup.get("basic") or []
        advanced = setup.get("advanced") or []
        if mode == "basic":
            return list(basic)
        if mode == "advanced":
            return list(basic) + list(advanced)
        raise ValueError(f"Unknown setup mode: {mode}")
