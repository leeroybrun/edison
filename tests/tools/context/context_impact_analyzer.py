#!/usr/bin/env python3
"""Main context impact analyzer CLI.

Comprehensive tool to measure, analyze, and optimize context consumption
across the entire AI-automated development workflow.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

try:
    from .baseline_profiler import BaselineProfiler
    from .bloat_detector import BloatDetector
    from .scenario_simulator import ScenarioSimulator
    from .token_counter import TokenCounter
except ImportError:
    # Fallback for direct script execution
    from baseline_profiler import BaselineProfiler
    from bloat_detector import BloatDetector
    from scenario_simulator import ScenarioSimulator
    from token_counter import TokenCounter


class ContextImpactAnalyzer:
    """Main analyzer orchestrating all context analysis tools."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize analyzer.

        Args:
            repo_root: Repository root path
        """
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[4]

        self.project_root = Path(repo_root)
        self.baseline_profiler = BaselineProfiler(repo_root)
        self.scenario_simulator = ScenarioSimulator(repo_root)
        self.bloat_detector = BloatDetector(repo_root)
        self.counter = TokenCounter()

    def run_full_analysis(self) -> Dict:
        """Run complete context impact analysis.

        Returns:
            Dict with all analysis results
        """
        print("🔍 Running comprehensive context impact analysis...")
        print()

        results = {}

        # 1. Baseline profiling
        print("📊 Step 1/4: Profiling baseline mandatory files...")
        baseline = self.baseline_profiler.profile_mandatory_core()
        budget = self.baseline_profiler.estimate_context_budget_usage()
        results["baseline"] = baseline
        results["budget"] = budget
        print(f"   ✓ Baseline: {baseline['total_tokens']:,} tokens")

        # 2. Scenario simulation
        print("\n🎯 Step 2/4: Simulating realistic task scenarios...")
        scenarios = self.scenario_simulator.run_all_scenarios()
        results["scenarios"] = scenarios
        print(f"   ✓ Simulated {len(scenarios['scenarios'])} scenarios")

        # 3. Bloat detection
        print("\n🚨 Step 3/4: Detecting context bloat...")
        oversized = self.bloat_detector.detect_oversized_files()
        duplicates = self.bloat_detector.detect_duplicate_content()
        config_bloat = self.bloat_detector.analyze_config_bloat()
        results["bloat"] = {
            "oversized": oversized,
            "duplicates": duplicates,
            "config_bloat": config_bloat,
        }
        print(f"   ✓ Found {len(oversized)} oversized files")
        print(f"   ✓ Found {len(duplicates)} duplicate pairs")

        # 4. Optimization recommendations
        print("\n💡 Step 4/4: Generating optimization recommendations...")
        recommendations = self._generate_recommendations(results)
        results["recommendations"] = recommendations
        print(f"   ✓ Generated {len(recommendations['immediate'])} immediate recommendations")

        print("\n✅ Analysis complete!")
        return results

    def _generate_recommendations(self, analysis_results: Dict) -> Dict:
        """Generate actionable optimization recommendations.

        Args:
            analysis_results: Combined analysis results

        Returns:
            Dict with categorized recommendations
        """
        recommendations = {
            "immediate": [],
            "medium_term": [],
            "long_term": [],
        }

        baseline = analysis_results.get("baseline", {})
        bloat = analysis_results.get("bloat", {})

        # Immediate: Quick wins from oversized files
        for file_info in bloat.get("oversized", [])[:5]:
            if file_info["tokens"] > 5000:
                recommendations["immediate"].append(
                    {
                        "priority": "high",
                        "type": "file_reduction",
                        "file": file_info["path"],
                        "current_tokens": file_info["tokens"],
                        "target_tokens": file_info["tokens"] // 2,
                        "action": file_info["recommendation"],
                        "estimated_savings": file_info["tokens"] // 2,
                    }
                )

        # Immediate: Deduplication
        for dup in bloat.get("duplicates", [])[:3]:
            if dup["similarity"] > 0.8:
                recommendations["immediate"].append(
                    {
                        "priority": "high",
                        "type": "deduplication",
                        "files": [dup["file1"], dup["file2"]],
                        "similarity": dup["similarity"],
                        "action": dup["recommendation"],
                        "estimated_savings": 1000,  # Conservative estimate
                    }
                )

        # Medium-term: Config modularization
        for issue in bloat.get("config_bloat", []):
            recommendations["medium_term"].append(
                {
                    "priority": "medium",
                    "type": "config_modularization",
                    "config": issue["config"],
                    "section": issue["section"],
                    "current_tokens": issue["tokens"],
                    "action": issue["recommendation"],
                    "estimated_savings": issue["tokens"] // 3,  # Lazy loading saves ~33%
                }
            )

        # Medium-term: Conditional guide loading
        recommendations["medium_term"].append(
            {
                "priority": "medium",
                "type": "lazy_loading",
                "action": "Implement lazy loading for extended guides (TDD_GUIDE, VALIDATION_GUIDE)",
                "estimated_savings": 3000,
            }
        )

        # Long-term: Architectural changes
        recommendations["long_term"].extend(
            [
                {
                    "priority": "low",
                    "type": "architecture",
                    "action": "Implement RAG system for guide retrieval (semantic search)",
                    "estimated_savings": 10000,
                },
                {
                    "priority": "low",
                    "type": "architecture",
                    "action": "Context budget enforcement system (fail if >50K tokens)",
                    "estimated_savings": 0,  # Prevention, not reduction
                },
                {
                    "priority": "low",
                    "type": "architecture",
                    "action": "Smart context pruning based on task relevance scores",
                    "estimated_savings": 8000,
                },
            ]
        )

        return recommendations

    def generate_comprehensive_report(self, results: Dict, format: str = "markdown") -> str:
        """Generate comprehensive analysis report.

        Args:
            results: Analysis results
            format: Output format (markdown or json)

        Returns:
            Formatted report
        """
        if format == "json":
            return json.dumps(results, indent=2)

        # Markdown report
        lines = [
            "# 🔬 Context Impact Analysis Report",
            "",
            "**Generated by**: Context Impact Analyzer",
            f"**Repository**: {self.project_root.name}",
            "",
            "---",
            "",
        ]

        # Executive Summary
        baseline = results.get("baseline", {})
        scenarios = results.get("scenarios", {}).get("scenarios", [])
        bloat = results.get("bloat", {})

        total_baseline = baseline.get("total_tokens", 0)
        max_scenario = max(s["total_tokens"] for s in scenarios) if scenarios else 0

        lines.extend(
            [
                "## 📊 Executive Summary",
                "",
                f"- **Baseline mandatory files**: {total_baseline:,} tokens",
                f"- **Maximum scenario load**: {max_scenario:,} tokens",
                f"- **Oversized files found**: {len(bloat.get('oversized', []))}",
                f"- **Duplicate pairs found**: {len(bloat.get('duplicates', []))}",
                "",
                "### Key Findings",
                "",
            ]
        )

        # Top findings
        if bloat.get("oversized"):
            top_file = bloat["oversized"][0]
            lines.append(
                f"- 🚨 Largest file: `{top_file['path']}` ({top_file['tokens']:,} tokens)"
            )

        if bloat.get("duplicates"):
            top_dup = bloat["duplicates"][0]
            lines.append(
                f"- 🔄 Highest duplication: {top_dup['similarity']:.0%} between "
                f"`{Path(top_dup['file1']).name}` and `{Path(top_dup['file2']).name}`"
            )

        lines.extend(["", "---", ""])

        # Baseline section
        if "baseline" in results:
            baseline_report = self.baseline_profiler.generate_report()
            lines.extend([baseline_report, "", "---", ""])

        # Scenario section
        if "scenarios" in results:
            scenario_report = self.scenario_simulator.generate_report(results["scenarios"])
            lines.extend([scenario_report, "", "---", ""])

        # Bloat detection section
        if "bloat" in results:
            bloat_report = self.bloat_detector.generate_report()
            lines.extend([bloat_report, "", "---", ""])

        # Recommendations section
        recommendations = results.get("recommendations", {})
        lines.extend(
            [
                "## 💡 Optimization Recommendations",
                "",
                "Prioritized action items to reduce context consumption:",
                "",
            ]
        )

        # Immediate
        immediate = recommendations.get("immediate", [])
        if immediate:
            lines.extend(
                [
                    "### 🔴 Immediate (High Impact, Low Effort)",
                    "",
                ]
            )
            for i, rec in enumerate(immediate[:5], 1):
                savings = rec.get("estimated_savings", 0)
                lines.append(f"{i}. **{rec['action']}**")
                if "file" in rec:
                    lines.append(f"   - File: `{rec['file']}`")
                    lines.append(
                        f"   - Current: {rec.get('current_tokens', 0):,} tokens"
                    )
                if savings > 0:
                    lines.append(f"   - Est. savings: ~{savings:,} tokens")
                lines.append("")

        # Medium-term
        medium = recommendations.get("medium_term", [])
        if medium:
            lines.extend(
                [
                    "### 🟡 Medium-Term (High Impact, Medium Effort)",
                    "",
                ]
            )
            for i, rec in enumerate(medium[:5], 1):
                lines.append(f"{i}. **{rec['action']}**")
                if rec.get("estimated_savings", 0) > 0:
                    lines.append(
                        f"   - Est. savings: ~{rec['estimated_savings']:,} tokens"
                    )
                lines.append("")

        # Long-term
        long_term = recommendations.get("long_term", [])
        if long_term:
            lines.extend(
                [
                    "### 🔵 Long-Term (Transformative)",
                    "",
                ]
            )
            for i, rec in enumerate(long_term, 1):
                lines.append(f"{i}. **{rec['action']}**")
                if rec.get("estimated_savings", 0) > 0:
                    lines.append(
                        f"   - Est. savings: ~{rec['estimated_savings']:,} tokens"
                    )
                lines.append("")

        # Calculate total potential savings
        total_savings = sum(
            rec.get("estimated_savings", 0)
            for rec in immediate + medium + long_term
        )

        lines.extend(
            [
                "---",
                "",
                "## 📈 Potential Impact",
                "",
                f"**Total estimated savings**: ~{total_savings:,} tokens",
                f"**Reduction percentage**: ~{(total_savings / max_scenario * 100):.1f}%",
                "",
                "This represents significant context budget freed for actual code analysis.",
                "",
            ]
        )

        return "\n".join(lines)

    def export_results(
        self, results: Dict, output_path: Path, format: str = "markdown"
    ):
        """Export analysis results to file.

        Args:
            results: Analysis results
            output_path: Output file path
            format: Output format
        """
        report = self.generate_comprehensive_report(results, format)
        output_path.write_text(report, encoding="utf-8")
        print(f"\n📝 Report saved to: {output_path}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Context Impact Analyzer - Measure and optimize AI workflow context consumption"
    )

    parser.add_argument(
        "--scenario",
        choices=[
            "all",
            "baseline",
            "scenarios",
            "bloat",
            "ui-component",
            "api-route",
            "full-stack",
        ],
        default="all",
        help="Which analysis to run (default: all)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: /tmp/context-impact-report.md)",
    )

    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root path (auto-detected if not provided)",
    )

    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="CI mode: exit with error if context budget exceeds threshold",
    )

    parser.add_argument(
        "--threshold",
        type=int,
        default=80000,
        help="Context budget threshold for CI mode (default: 80000 tokens)",
    )

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = ContextImpactAnalyzer(repo_root=args.project_root)

    # Run analysis based on scenario
    if args.scenario == "all":
        results = analyzer.run_full_analysis()
    elif args.scenario == "baseline":
        results = {"baseline": analyzer.baseline_profiler.profile_mandatory_core()}
    elif args.scenario == "bloat":
        results = {
            "bloat": {
                "oversized": analyzer.bloat_detector.detect_oversized_files(),
                "duplicates": analyzer.bloat_detector.detect_duplicate_content(),
            }
        }
    else:
        print(f"Scenario '{args.scenario}' not fully implemented yet")
        sys.exit(1)

    # Generate report
    report = analyzer.generate_comprehensive_report(results, args.format)
    print("\n" + "=" * 70)
    print(report)
    print("=" * 70)

    # Export to file
    output_path = args.output or Path("/tmp/context-impact-report.md")
    analyzer.export_results(results, output_path, args.format)

    # CI mode: check threshold
    if args.ci_mode:
        scenarios = results.get("scenarios", {}).get("scenarios", [])
        if scenarios:
            max_tokens = max(s["total_tokens"] for s in scenarios)
            if max_tokens > args.threshold:
                print(
                    f"\n❌ CI CHECK FAILED: Context budget exceeded ({max_tokens:,} > {args.threshold:,} tokens)"
                )
                sys.exit(1)
            else:
                print(
                    f"\n✅ CI CHECK PASSED: Context budget OK ({max_tokens:,} <= {args.threshold:,} tokens)"
                )

    sys.exit(0)


if __name__ == "__main__":
    main()
