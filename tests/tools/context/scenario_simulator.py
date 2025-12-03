#!/usr/bin/env python3
"""Scenario simulator that tests REAL file patterns and CLI outputs.

This creates actual temporary task/QA structures and invokes REAL CLIs
to measure context consumption in realistic workflows.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from edison.core.utils.subprocess import run_with_timeout
from tests.config import get_task_states, get_qa_states, get_session_states, load_paths

try:
    from .baseline_profiler import BaselineProfiler
    from .token_counter import TokenCounter
except ImportError:
    from baseline_profiler import BaselineProfiler
    from token_counter import TokenCounter


class ScenarioSimulator:
    """Simulate realistic task scenarios with REAL file operations and CLI calls."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize simulator.

        Args:
            repo_root: Repository root path
        """
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[4]

        self.project_root = Path(repo_root)
        self.agents_dir = self.project_root / ".agents"
        self.counter = TokenCounter()
        self.baseline_profiler = BaselineProfiler(repo_root)

        # Load configs for scenario definitions
        self.manifest = self._load_json(self.agents_dir / "manifest.json")
        self.delegation_config = self._load_json(
            self.agents_dir / "delegation" / "config.json"
        )
        self.validators_config = self._load_json(
            self.agents_dir / "validators" / "config.json"
        )

    def _load_json(self, path: Path) -> Dict:
        """Load JSON file safely."""
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def get_triggered_validators(self, file_patterns: List[str]) -> List[Dict]:
        """Determine which validators would be triggered for given files.

        Args:
            file_patterns: List of file paths/patterns (e.g., ["route.ts", "Button.tsx"])

        Returns:
            List of validator configs that would be triggered
        """
        validators = self.validators_config.get("validators", {})
        triggered = []

        # Always include global and critical validators
        for validator in validators.get("global", []):
            if validator.get("alwaysRun", False):
                triggered.append(validator)

        for validator in validators.get("critical", []):
            if validator.get("alwaysRun", False):
                triggered.append(validator)

        # Check specialized validators based on file patterns
        for validator in validators.get("specialized", []):
            file_triggers = validator.get("fileTriggers", [])

            for pattern in file_patterns:
                for trigger in file_triggers:
                    # Simple pattern matching (could be enhanced)
                    if self._pattern_matches(pattern, trigger):
                        triggered.append(validator)
                        break

        return triggered

    def _pattern_matches(self, file_path: str, trigger_pattern: str) -> bool:
        """Check if file path matches trigger pattern.

        Args:
            file_path: File path to check
            trigger_pattern: Trigger pattern (glob-like)

        Returns:
            True if matches
        """
        # Simple matching - could use fnmatch for more accuracy
        if "**" in trigger_pattern:
            # Wildcard matching
            suffix = trigger_pattern.split("**")[-1]
            return file_path.endswith(suffix.strip("/"))
        elif "*" in trigger_pattern:
            # Extension matching
            ext = trigger_pattern.split("*")[-1]
            return file_path.endswith(ext)
        else:
            return trigger_pattern in file_path

    def get_triggered_guides(self, task_type: str, file_paths: List[str]) -> List[Path]:
        """Get guide files that would be triggered.

        Args:
            task_type: Task type (e.g., "api-route", "ui-component")
            file_paths: List of files being worked on

        Returns:
            List of guide file paths
        """
        guides = []
        guide_map = self.manifest.get("guides", {})

        # Check task type triggers
        task_triggers = self.manifest.get("triggers", {}).get("taskTypes", {})
        if task_type in task_triggers:
            for guide_ref in task_triggers[task_type]:
                # guide_ref is like "guides.tdd"
                guide_key = guide_ref.split(".")[-1]
                if guide_key in guide_map:
                    guide_path = self.project_root / guide_map[guide_key]
                    if guide_path.exists():
                        guides.append(guide_path)

        # Check file pattern triggers
        file_triggers = self.manifest.get("triggers", {}).get("filePatterns", {})
        for file_path in file_paths:
            for pattern, guide_refs in file_triggers.items():
                if self._pattern_matches(file_path, pattern):
                    for guide_ref in guide_refs:
                        guide_key = guide_ref.split(".")[-1]
                        if guide_key in guide_map:
                            guide_path = self.project_root / guide_map[guide_key]
                            if guide_path.exists() and guide_path not in guides:
                                guides.append(guide_path)

        return guides

    def get_sub_agent_prompt(self, task_type: str) -> Optional[Path]:
        """Get sub-agent prompt file for task type.

        Args:
            task_type: Task type

        Returns:
            Path to agent prompt file, or None
        """
        task_rules = self.delegation_config.get("taskTypeRules", {})

        if task_type not in task_rules:
            return None

        sub_agent_type = task_rules[task_type].get("subAgentType")
        if not sub_agent_type:
            return None

        # Agent prompts are in .agents/agents/
        agent_file = self.agents_dir / "agents" / f"{sub_agent_type}.md"
        return agent_file if agent_file.exists() else None

    def simulate_scenario(
        self, scenario_name: str, task_type: str, file_paths: List[str]
    ) -> Dict:
        """Simulate a complete scenario and measure token consumption.

        Args:
            scenario_name: Name for this scenario
            task_type: Task type (e.g., "api-route")
            file_paths: Files being worked on

        Returns:
            Dict with detailed token breakdown
        """
        result = {
            "scenario_name": scenario_name,
            "task_type": task_type,
            "file_paths": file_paths,
            "layers": {},
            "total_tokens": 0,
        }

        # Layer 1: Mandatory baseline
        baseline = self.baseline_profiler.profile_mandatory_core()
        result["layers"]["mandatory_core"] = {
            "tokens": baseline["total_tokens"],
            "files": len(baseline["files"]),
        }
        result["total_tokens"] += baseline["total_tokens"]

        # Layer 2: Triggered guides
        triggered_guides = self.get_triggered_guides(task_type, file_paths)
        guides_tokens = 0
        guides_info = []
        for guide_path in triggered_guides:
            file_info = self.counter.count_file(guide_path)
            guides_tokens += file_info["tokens"]
            guides_info.append(
                {
                    "path": str(guide_path.relative_to(self.project_root)),
                    "tokens": file_info["tokens"],
                    "lines": file_info["lines"],
                }
            )

        result["layers"]["triggered_guides"] = {
            "tokens": guides_tokens,
            "files": guides_info,
        }
        result["total_tokens"] += guides_tokens

        # Layer 3: Sub-agent prompt
        agent_prompt = self.get_sub_agent_prompt(task_type)
        if agent_prompt:
            file_info = self.counter.count_file(agent_prompt)
            result["layers"]["sub_agent_prompt"] = {
                "tokens": file_info["tokens"],
                "file": str(agent_prompt.relative_to(self.project_root)),
                "lines": file_info["lines"],
            }
            result["total_tokens"] += file_info["tokens"]
        else:
            result["layers"]["sub_agent_prompt"] = {"tokens": 0, "file": None}

        # Layer 4: Validator prompts
        triggered_validators = self.get_triggered_validators(file_paths)
        validators_tokens = 0
        validators_info = []

        for validator in triggered_validators:
            spec_file = validator.get("specFile")
            if spec_file:
                validator_path = self.agents_dir / "validators" / spec_file
                if validator_path.exists():
                    file_info = self.counter.count_file(validator_path)
                    validators_tokens += file_info["tokens"]
                    validators_info.append(
                        {
                            "id": validator.get("id"),
                            "name": validator.get("name"),
                            "path": str(validator_path.relative_to(self.project_root)),
                            "tokens": file_info["tokens"],
                            "lines": file_info["lines"],
                            "blocking": validator.get("blocksOnFail", False),
                        }
                    )

        result["layers"]["validators"] = {
            "tokens": validators_tokens,
            "count": len(triggered_validators),
            "files": validators_info,
        }
        result["total_tokens"] += validators_tokens

        return result

    def create_test_project_structure(self, temp_dir: Path, scenario: Dict) -> Path:
        """Create a temporary .project structure for testing CLIs.

        Args:
            temp_dir: Temporary directory
            scenario: Scenario dict with task info

        Returns:
            Path to created .project directory
        """
        project_dir = temp_dir / ".project"
        project_dir.mkdir(exist_ok=True)

        # Load state directories from config (NO hardcoded values)
        task_states = get_task_states()
        qa_states = get_qa_states()
        session_states = get_session_states()

        # Create task directories
        for state in task_states:
            (project_dir / "tasks" / state).mkdir(parents=True, exist_ok=True)

        # Create QA directories
        for state in qa_states:
            (project_dir / "qa" / state).mkdir(parents=True, exist_ok=True)

        # Create validation evidence directory
        (project_dir / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)

        # Create session directories
        for state in session_states:
            (project_dir / "sessions" / state).mkdir(parents=True, exist_ok=True)

        return project_dir

    def test_session_next_cli(
        self, session_id: str = "test-session-001"
    ) -> Optional[Dict]:
        """Test the REAL session next CLI and measure its output.

        Args:
            session_id: Session ID to test with

        Returns:
            Dict with CLI output analysis, or None if CLI failed
        """
        # Create temporary session file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Load default session state from config (NO hardcoded values)
            from tests.config import get_default_value
            default_state = get_default_value("session", "state")

            # Create minimal session structure
            sessions_dir = temp_path / ".project" / "sessions" / default_state / session_id
            sessions_dir.mkdir(parents=True, exist_ok=True)

            session_file = sessions_dir / "session.json"
            session_data = {
                "sessionId": session_id,
                "status": default_state,
                "scope": {"tasks": [], "qa": []},
                "created": "2025-11-14T00:00:00Z",
                "lastActive": "2025-11-14T00:00:00Z",
            }
            session_file.write_text(json.dumps(session_data, indent=2))

            # Try to run session next CLI
            try:
                # Note: This requires the actual .agents scripts to be importable
                # We'll invoke as a subprocess to truly test the REAL CLI
                result = run_with_timeout(
                    ["python", str(self.agents_dir / "scripts" / "session"), "next", session_id],
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    # CLI may fail in test environment - that's ok, we'll handle it
                    return {
                        "success": False,
                        "error": result.stderr,
                        "tokens": 0,
                    }

                output = result.stdout
                tokens = self.counter.count_text(output)

                return {
                    "success": True,
                    "tokens": tokens,
                    "lines": len(output.splitlines()),
                    "output_sample": output[:500] + "..." if len(output) > 500 else output,
                }

            except Exception as e:
                return {"success": False, "error": str(e), "tokens": 0}

    def run_all_scenarios(self) -> Dict:
        """Run all predefined scenarios.

        Returns:
            Dict with all scenario results
        """
        scenarios = [
            {
                "name": "UI Component (Button.tsx)",
                "task_type": "ui-component",
                "files": ["apps/example-app/src/components/Button.tsx"],
            },
            {
                "name": "API Route (leads route)",
                "task_type": "api-route",
                "files": ["apps/example-app/src/app/api/v1/resources/leads/route.ts"],
            },
            {
                "name": "Full-Stack Feature",
                "task_type": "full-stack-feature",
                "files": [
                    "apps/example-app/src/app/leads/page.tsx",
                    "apps/example-app/src/app/api/v1/resources/leads/route.ts",
                    "packages/db/prisma/schema.prisma",
                ],
            },
            {
                "name": "Database Schema",
                "task_type": "database-schema",
                "files": ["packages/db/prisma/schema.prisma"],
            },
            {
                "name": "Test Suite",
                "task_type": "test-suite",
                "files": ["apps/example-app/src/hooks/use-leads.test.ts"],
            },
        ]

        results = {"scenarios": [], "session_next_cli": None}

        for scenario in scenarios:
            result = self.simulate_scenario(
                scenario["name"], scenario["task_type"], scenario["files"]
            )
            results["scenarios"].append(result)

        # Test session next CLI
        cli_result = self.test_session_next_cli()
        results["session_next_cli"] = cli_result

        return results

    def generate_report(self, results: Dict) -> str:
        """Generate human-readable scenario report.

        Args:
            results: Results from run_all_scenarios()

        Returns:
            Markdown report
        """
        lines = [
            "# Scenario Simulation Report",
            "",
            "This report shows token consumption for realistic task scenarios,",
            "based on REAL file triggers and validator configurations.",
            "",
        ]

        for scenario in results["scenarios"]:
            name = scenario["scenario_name"]
            total = scenario["total_tokens"]

            lines.extend(
                [
                    f"## {name}",
                    f"**Total tokens**: {total:,}",
                    "",
                    "### Breakdown by Layer:",
                    "",
                ]
            )

            for layer_name, layer_data in scenario["layers"].items():
                tokens = layer_data["tokens"]
                percentage = (tokens / total * 100) if total > 0 else 0

                lines.append(
                    f"- **{layer_name.replace('_', ' ').title()}**: "
                    f"{tokens:,} tokens ({percentage:.1f}%)"
                )

                # Add file details for some layers
                if "files" in layer_data and isinstance(layer_data["files"], list):
                    for file_info in layer_data["files"][:3]:  # Top 3
                        if isinstance(file_info, dict):
                            lines.append(
                                f"  - `{file_info.get('path', 'unknown')}`: "
                                f"{file_info.get('tokens', 0):,} tokens"
                            )

            lines.extend(["", "---", ""])

        # Session next CLI analysis
        if results.get("session_next_cli"):
            cli = results["session_next_cli"]
            lines.extend(
                [
                    "## Session Next CLI Output",
                    "",
                ]
            )

            if cli.get("success"):
                lines.extend(
                    [
                        f"**Tokens**: {cli['tokens']:,}",
                        f"**Lines**: {cli['lines']:,}",
                        "",
                        "This represents the guidance output from `edison session next`,",
                        "which is loaded by orchestrators on each planning cycle.",
                        "",
                    ]
                )
            else:
                lines.extend(
                    [
                        "❌ CLI test failed (expected in isolated test environment)",
                        f"Error: {cli.get('error', 'Unknown')}",
                        "",
                    ]
                )

        return "\n".join(lines)


if __name__ == "__main__":
    simulator = ScenarioSimulator()
    results = simulator.run_all_scenarios()
    report = simulator.generate_report(results)
    print(report)

    # Save to file
    output_path = Path("/tmp/scenario-simulation-report.md")
    output_path.write_text(report)
    print(f"\n📝 Report saved to: {output_path}")