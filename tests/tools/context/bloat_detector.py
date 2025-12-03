#!/usr/bin/env python3
"""Bloat detector that identifies context optimization opportunities.

This analyzes REAL files to find:
- Oversized files
- Duplicate/similar content
- Rarely-used mandatory files
- Heavy config sections
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from .token_counter import TokenCounter
except ImportError:
    from token_counter import TokenCounter


class BloatDetector:
    """Detect context bloat and optimization opportunities."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize detector.

        Args:
            repo_root: Repository root path
        """
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[4]

        self.project_root = Path(repo_root)
        self.agents_dir = self.project_root / ".agents"
        self.counter = TokenCounter()

    def detect_oversized_files(
        self, threshold_tokens: int = 3000, threshold_lines: int = 800
    ) -> List[Dict]:
        """Find files that exceed size thresholds.

        Args:
            threshold_tokens: Token count threshold
            threshold_lines: Line count threshold

        Returns:
            List of oversized file info dicts
        """
        oversized = []

        # Scan all markdown and JSON files in .agents/
        for file_path in self.agents_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix not in [".md", ".json"]:
                continue

            # Skip certain directories
            if any(
                skip in str(file_path)
                for skip in ["__pycache__", "node_modules", ".git"]
            ):
                continue

            file_info = self.counter.count_file(file_path)

            if (
                file_info["tokens"] > threshold_tokens
                or file_info["lines"] > threshold_lines
            ):
                rel_path = file_path.relative_to(self.project_root)
                oversized.append(
                    {
                        "path": str(rel_path),
                        "tokens": file_info["tokens"],
                        "lines": file_info["lines"],
                        "chars": file_info["chars"],
                        "size_kb": file_info.get("size_kb", 0),
                        "exceeds_tokens": file_info["tokens"] > threshold_tokens,
                        "exceeds_lines": file_info["lines"] > threshold_lines,
                        "recommendation": self._recommend_size_reduction(
                            rel_path, file_info
                        ),
                    }
                )

        # Sort by token count
        oversized.sort(key=lambda x: x["tokens"], reverse=True)

        return oversized

    def _recommend_size_reduction(self, rel_path: Path, file_info: Dict) -> str:
        """Generate recommendation for reducing file size.

        Args:
            rel_path: Relative path
            file_info: File info dict

        Returns:
            Recommendation string
        """
        path_str = str(rel_path)

        if "TDD_GUIDE" in path_str:
            return "Create condensed TDD_CHECKLIST.md (200 lines) for quick reference"
        elif "VALIDATION_GUIDE" in path_str:
            return "Extract validator checklists to separate files, keep core flow only"
        elif "TESTING_GUIDE" in path_str:
            return "Split into multiple focused guides (unit, integration, e2e)"
        elif "delegation/config.json" in path_str:
            return "Split into modules: file-patterns.json, task-types.json, sub-agents.json"
        elif "validators/config.json" in path_str:
            return "Move validator specs to separate directory, keep only metadata"
        elif path_str.endswith(".md") and file_info["lines"] > 800:
            return "Consider splitting into multiple focused documents"
        elif path_str.endswith(".json") and file_info["lines"] > 500:
            return "Consider modular JSON structure with $ref imports"
        else:
            return "Review for condensation opportunities"

    def detect_duplicate_content(
        self, similarity_threshold: float = 0.7
    ) -> List[Dict]:
        """Find files with similar/duplicate content.

        Args:
            similarity_threshold: Similarity ratio threshold (0.0-1.0)

        Returns:
            List of duplicate pairs
        """
        duplicates = []

        # Focus on specific file categories
        categories = {
            "validators": list((self.agents_dir / "validators").rglob("*.md")),
            "agents": list((self.agents_dir / "agents").rglob("*.md")),
            "guides": list((self.agents_dir / "guides").rglob("*.md")),
        }

        for category, files in categories.items():
            # Compare each pair
            for i, file1 in enumerate(files):
                for file2 in files[i + 1 :]:
                    similarity = self._calculate_similarity(file1, file2)

                    if similarity >= similarity_threshold:
                        duplicates.append(
                            {
                                "category": category,
                                "file1": str(file1.relative_to(self.project_root)),
                                "file2": str(file2.relative_to(self.project_root)),
                                "similarity": similarity,
                                "recommendation": self._recommend_dedup(
                                    file1, file2, similarity
                                ),
                            }
                        )

        # Sort by similarity
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)

        return duplicates

    def _calculate_similarity(self, file1: Path, file2: Path) -> float:
        """Calculate content similarity between two files.

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            Similarity ratio (0.0-1.0)
        """
        try:
            content1 = file1.read_text(encoding="utf-8")
            content2 = file2.read_text(encoding="utf-8")

            # Use difflib's SequenceMatcher
            matcher = difflib.SequenceMatcher(None, content1, content2)
            return matcher.ratio()

        except Exception:
            return 0.0

    def _recommend_dedup(self, file1: Path, file2: Path, similarity: float) -> str:
        """Generate recommendation for deduplication.

        Args:
            file1: First file
            file2: Second file
            similarity: Similarity ratio

        Returns:
            Recommendation string
        """
        name1 = file1.name
        name2 = file2.name

        if "global" in name1 and "global" in name2:
            return "Extract common global checklist to shared template, specialize per model"
        elif similarity > 0.9:
            return "Near-identical content - consider using single file with parameters"
        elif similarity > 0.8:
            return "Extract common sections to shared include/template file"
        else:
            return "Review overlapping sections for potential consolidation"

    def analyze_config_bloat(self) -> List[Dict]:
        """Analyze config files for bloat opportunities.

        Returns:
            List of config bloat issues
        """
        issues = []

        config_files = {
            "delegation": self.agents_dir / "delegation" / "config.json",
            "validators": self.agents_dir / "validators" / "config.json",
            "manifest": self.agents_dir / "manifest.json",
        }

        for name, path in config_files.items():
            if not path.exists():
                continue

            breakdown = self.counter.count_json_structure(path)
            total_tokens = breakdown["total_tokens"]

            # Find heavy sections
            if "breakdown" in breakdown:
                for key, info in breakdown["breakdown"].items():
                    if info["tokens"] > 1000:  # Heavy section threshold
                        issues.append(
                            {
                                "config": name,
                                "section": key,
                                "tokens": info["tokens"],
                                "percentage": info["percentage"],
                                "recommendation": self._recommend_config_split(
                                    name, key, info
                                ),
                            }
                        )

        return issues

    def _recommend_config_split(self, config_name: str, section: str, info: Dict) -> str:
        """Recommend config splitting strategy.

        Args:
            config_name: Config file name
            section: Section name
            info: Section info

        Returns:
            Recommendation
        """
        if config_name == "delegation":
            if section == "filePatternRules":
                return "Extract to delegation/file-patterns.json with lazy loading"
            elif section == "taskTypeRules":
                return "Extract to delegation/task-types.json with lazy loading"
            elif section == "zenMcpIntegration":
                return "Extract to delegation/zen-mcp.json (only load when delegating)"

        elif config_name == "validators":
            if section == "validators":
                return "Move validator specs to individual files, keep metadata only"
            elif section == "postTrainingPackages":
                return "Extract to validators/post-training-packages.json"

        return "Consider extracting to separate file with lazy loading"

    def detect_unused_mandatory_files(self, usage_data: Optional[Dict] = None) -> List[Dict]:
        """Detect mandatory files that are rarely used.

        Note: This requires usage tracking data to be accurate.
        For now, we'll identify candidates based on file characteristics.

        Args:
            usage_data: Optional usage statistics

        Returns:
            List of potentially unused mandatory files
        """
        candidates = []

        # Load manifest
        manifest_path = self.agents_dir / "manifest.json"
        if not manifest_path.exists():
            return candidates

        manifest = json.loads(manifest_path.read_text())
        mandatory = manifest.get("mandatory", [])

        # Analyze each mandatory file
        for rel_path in mandatory:
            abs_path = self.project_root / rel_path

            if not abs_path.exists():
                continue

            file_info = self.counter.count_file(abs_path)

            # Check if it's referenced in other files (heuristic for usage)
            references = self._count_file_references(abs_path)

            # Files with few references might be candidates for conditional loading
            if references < 3 and file_info["tokens"] > 500:
                candidates.append(
                    {
                        "path": rel_path,
                        "tokens": file_info["tokens"],
                        "lines": file_info["lines"],
                        "references": references,
                        "recommendation": "Consider moving to conditional/triggered loading",
                    }
                )

        return candidates

    def _count_file_references(self, file_path: Path) -> int:
        """Count how many other files reference this file.

        Args:
            file_path: File to check

        Returns:
            Reference count
        """
        references = 0
        file_name = file_path.name
        rel_path = str(file_path.relative_to(self.project_root))

        # Search in all .agents/ markdown and JSON files
        for search_file in self.agents_dir.rglob("*"):
            if not search_file.is_file():
                continue

            if search_file.suffix not in [".md", ".json"]:
                continue

            if search_file == file_path:
                continue

            try:
                content = search_file.read_text(encoding="utf-8")
                # Simple string search for file references
                if file_name in content or rel_path in content:
                    references += 1
            except Exception:
                continue

        return references

    def generate_report(self) -> str:
        """Generate comprehensive bloat detection report.

        Returns:
            Markdown report
        """
        lines = [
            "# Context Bloat Detection Report",
            "",
            "This report identifies optimization opportunities in the .agents/ structure.",
            "",
        ]

        # Oversized files
        oversized = self.detect_oversized_files()
        lines.extend(
            [
                f"## 🚨 Oversized Files ({len(oversized)} found)",
                "",
                "Files exceeding recommended size thresholds:",
                "",
            ]
        )

        for i, file_info in enumerate(oversized[:10], 1):
            lines.extend(
                [
                    f"### {i}. `{file_info['path']}`",
                    f"- **Tokens**: {file_info['tokens']:,}",
                    f"- **Lines**: {file_info['lines']:,}",
                    f"- **Size**: {file_info['size_kb']:.2f} KB",
                    f"- **Recommendation**: {file_info['recommendation']}",
                    "",
                ]
            )

        # Duplicate content
        duplicates = self.detect_duplicate_content()
        lines.extend(
            [
                f"## 🔄 Duplicate/Similar Content ({len(duplicates)} pairs found)",
                "",
                "Files with high content similarity:",
                "",
            ]
        )

        for i, dup in enumerate(duplicates[:5], 1):
            lines.extend(
                [
                    f"### {i}. {dup['similarity']:.0%} similar",
                    f"- **File 1**: `{dup['file1']}`",
                    f"- **File 2**: `{dup['file2']}`",
                    f"- **Category**: {dup['category']}",
                    f"- **Recommendation**: {dup['recommendation']}",
                    "",
                ]
            )

        # Config bloat
        config_issues = self.analyze_config_bloat()
        lines.extend(
            [
                f"## ⚙️ Config File Bloat ({len(config_issues)} sections)",
                "",
                "Heavy config sections that could be modularized:",
                "",
            ]
        )

        for issue in config_issues:
            lines.extend(
                [
                    f"### {issue['config']}.{issue['section']}",
                    f"- **Tokens**: {issue['tokens']:,} ({issue['percentage']:.1f}%)",
                    f"- **Recommendation**: {issue['recommendation']}",
                    "",
                ]
            )

        # Unused mandatory files
        unused = self.detect_unused_mandatory_files()
        if unused:
            lines.extend(
                [
                    f"## 📋 Potentially Unused Mandatory Files ({len(unused)} found)",
                    "",
                    "Files marked mandatory but with low usage indicators:",
                    "",
                ]
            )

            for file_info in unused:
                lines.extend(
                    [
                        f"### `{file_info['path']}`",
                        f"- **Tokens**: {file_info['tokens']:,}",
                        f"- **References**: {file_info['references']}",
                        f"- **Recommendation**: {file_info['recommendation']}",
                        "",
                    ]
                )

        return "\n".join(lines)


if __name__ == "__main__":
    detector = BloatDetector()
    report = detector.generate_report()
    print(report)

    # Save to file
    output_path = Path("/tmp/bloat-detection-report.md")
    output_path.write_text(report)
    print(f"\n📝 Report saved to: {output_path}")
