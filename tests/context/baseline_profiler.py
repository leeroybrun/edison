#!/usr/bin/env python3
"""Baseline context profiler that measures mandatory file loading costs.

This profiles the ACTUAL mandatory files loaded during session startup,
matching the real behavior defined in .agents/manifest.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .token_counter import TokenCounter
except ImportError:
    from token_counter import TokenCounter


class BaselineProfiler:
    """Profile baseline context consumption from mandatory files."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize profiler.

        Args:
            repo_root: Repository root path (auto-detected if None)
        """
        if repo_root is None:
            # Auto-detect from this file's location
            repo_root = Path(__file__).resolve().parents[4]

        self.repo_root = Path(repo_root)
        self.agents_dir = self.repo_root / ".agents"
        self.counter = TokenCounter()

        # Load manifest to get REAL mandatory files
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict:
        """Load .agents/manifest.json.

        Returns:
            Manifest dict
        """
        manifest_path = self.agents_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        return json.loads(manifest_path.read_text())

    def get_mandatory_files(self) -> List[Path]:
        """Get list of mandatory files from manifest.

        Returns:
            List of absolute paths to mandatory files
        """
        mandatory = self.manifest.get("mandatory", [])
        files = []

        for rel_path in mandatory:
            abs_path = self.repo_root / rel_path
            if abs_path.exists():
                files.append(abs_path)
            else:
                print(f"⚠️  Mandatory file not found: {rel_path}")

        return files

    def profile_mandatory_core(self) -> Dict:
        """Profile all mandatory core files.

        Returns:
            Dict with detailed breakdown
        """
        mandatory_files = self.get_mandatory_files()

        results = {
            "total_files": len(mandatory_files),
            "total_tokens": 0,
            "total_lines": 0,
            "files": [],
            "categories": {
                "guidelines": {"files": [], "tokens": 0},
                "configs": {"files": [], "tokens": 0},
                "workflows": {"files": [], "tokens": 0},
                "rules": {"files": [], "tokens": 0},
                "validators": {"files": [], "tokens": 0},
                "delegation": {"files": [], "tokens": 0},
                "other": {"files": [], "tokens": 0},
            },
        }

        for file_path in mandatory_files:
            file_info = self.counter.count_file(file_path)

            # Categorize
            rel_path = file_path.relative_to(self.repo_root)
            category = self._categorize_file(rel_path)

            results["files"].append(
                {
                    "path": str(rel_path),
                    "tokens": file_info["tokens"],
                    "lines": file_info["lines"],
                    "category": category,
                }
            )

            results["total_tokens"] += file_info["tokens"]
            results["total_lines"] += file_info["lines"]

            # Add to category
            results["categories"][category]["files"].append(str(rel_path))
            results["categories"][category]["tokens"] += file_info["tokens"]

        # Sort files by token count (descending)
        results["files"].sort(key=lambda x: x["tokens"], reverse=True)

        return results

    def _categorize_file(self, rel_path: Path) -> str:
        """Categorize a file based on its path.

        Args:
            rel_path: Relative path from repo root

        Returns:
            Category name
        """
        path_str = str(rel_path)

        if "guidelines/" in path_str:
            return "guidelines"
        elif "delegation/" in path_str and path_str.endswith(".json"):
            return "delegation"
        elif "validators/" in path_str and path_str.endswith(".json"):
            return "validators"
        elif path_str.endswith("config.json") or path_str.endswith(".json"):
            return "configs"
        elif "workflow" in path_str.lower() or "WORKFLOW" in path_str:
            return "workflows"
        elif "rules/" in path_str:
            return "rules"
        else:
            return "other"

    def profile_config_files_detailed(self) -> Dict:
        """Profile config files with structural breakdown.

        Returns:
            Dict with detailed config file analysis
        """
        config_files = {
            "delegation": self.agents_dir / "delegation" / "config.json",
            "validators": self.agents_dir / "validators" / "config.json",
            "manifest": self.agents_dir / "manifest.json",
            "session-workflow": self.agents_dir / "session-workflow.json",
        }

        results = {}

        for name, path in config_files.items():
            if not path.exists():
                results[name] = {"exists": False}
                continue

            breakdown = self.counter.count_json_structure(path)
            results[name] = breakdown

        return results

    def estimate_context_budget_usage(self) -> Dict:
        """Estimate context budget usage with different LLM context windows.

        Returns:
            Dict with budget usage percentages
        """
        baseline = self.profile_mandatory_core()
        total_tokens = baseline["total_tokens"]

        context_windows = {
            "claude-sonnet-3.5": 200_000,
            "claude-opus": 200_000,
            "gpt-4-turbo": 128_000,
            "gpt-4": 8_192,
            "gemini-1.5-pro": 1_000_000,
        }

        usage = {}
        for model, window_size in context_windows.items():
            percentage = (total_tokens / window_size) * 100
            usage[model] = {
                "context_window": window_size,
                "baseline_tokens": total_tokens,
                "percentage_used": percentage,
                "remaining_tokens": window_size - total_tokens,
            }

        return usage

    def generate_report(self) -> str:
        """Generate human-readable baseline report.

        Returns:
            Markdown report
        """
        baseline = self.profile_mandatory_core()
        configs = self.profile_config_files_detailed()
        budget = self.estimate_context_budget_usage()

        lines = [
            "# Baseline Context Profile",
            "",
            "## Mandatory Core Files",
            f"- **Total files**: {baseline['total_files']}",
            f"- **Total tokens**: {baseline['total_tokens']:,}",
            f"- **Total lines**: {baseline['total_lines']:,}",
            "",
            "### Top 10 Largest Mandatory Files",
            "",
        ]

        for i, file_info in enumerate(baseline["files"][:10], 1):
            lines.append(
                f"{i}. `{file_info['path']}` - {file_info['tokens']:,} tokens "
                f"({file_info['lines']:,} lines) [{file_info['category']}]"
            )

        lines.extend(
            [
                "",
                "### Breakdown by Category",
                "",
            ]
        )

        # Sort categories by token count
        sorted_cats = sorted(
            baseline["categories"].items(), key=lambda x: x[1]["tokens"], reverse=True
        )

        for cat_name, cat_data in sorted_cats:
            if cat_data["tokens"] == 0:
                continue

            percentage = (cat_data["tokens"] / baseline["total_tokens"]) * 100
            lines.append(
                f"- **{cat_name.title()}**: {cat_data['tokens']:,} tokens "
                f"({percentage:.1f}%) - {len(cat_data['files'])} files"
            )

        lines.extend(
            [
                "",
                "## Config File Breakdown",
                "",
            ]
        )

        for name, data in configs.items():
            if not data.get("exists", True):
                lines.append(f"### {name.title()} (not found)")
                continue

            lines.append(f"### {name.title()}")
            lines.append(f"- **Total tokens**: {data['total_tokens']:,}")
            lines.append(f"- **Lines**: {data['lines']:,}")

            if "breakdown" in data and data["breakdown"]:
                lines.append("- **Top sections**:")
                sorted_sections = sorted(
                    data["breakdown"].items(),
                    key=lambda x: x[1]["tokens"],
                    reverse=True,
                )
                for key, info in sorted_sections[:5]:
                    lines.append(
                        f"  - `{key}`: {info['tokens']:,} tokens ({info['percentage']:.1f}%)"
                    )

            lines.append("")

        lines.extend(
            [
                "## Context Budget Usage",
                "",
                f"Baseline mandatory files consume: **{baseline['total_tokens']:,} tokens**",
                "",
            ]
        )

        for model, info in budget.items():
            emoji = "✅" if info["percentage_used"] < 20 else "⚠️" if info["percentage_used"] < 40 else "🚨"
            lines.append(
                f"- **{model}**: {info['percentage_used']:.1f}% of {info['context_window']:,} tokens {emoji}"
            )

        return "\n".join(lines)


if __name__ == "__main__":
    profiler = BaselineProfiler()
    report = profiler.generate_report()
    print(report)

    # Also save to file
    output_path = Path("/tmp/baseline-context-profile.md")
    output_path.write_text(report)
    print(f"\n📝 Report saved to: {output_path}")
