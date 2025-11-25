"""
Edison qa audit command.

SUMMARY: Audit guidelines quality
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Audit guidelines quality"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--path",
        type=str,
        help="Specific guideline path to audit (default: all)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "matrix"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--check-duplication",
        action="store_true",
        help="Check for content duplication between guidelines",
    )
    parser.add_argument(
        "--check-purity",
        action="store_true",
        help="Check for purity violations (project terms in core/packs)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Duplication threshold (0.0-1.0, default: 0.3)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (same as --format=json)",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Audit guidelines - delegates to guideline_audit library."""
    from edison.core import guideline_audit
    from edison.core.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Force JSON format if --json flag is used
        output_format = "json" if args.json else args.format

        # Discover all guidelines
        guidelines = guideline_audit.discover_guidelines(repo_root)

        # Filter to specific path if requested
        if args.path:
            path_filter = Path(args.path).resolve()
            guidelines = [g for g in guidelines if g.path == path_filter or path_filter in g.path.parents]

        if not guidelines:
            if output_format == "json":
                print(json.dumps({"error": "No guidelines found"}))
            else:
                print("No guidelines found", file=sys.stderr)
            return 1

        results = {
            "total_guidelines": len(guidelines),
            "by_category": {},
            "issues": [],
        }

        # Count by category
        for g in guidelines:
            cat = g.category
            results["by_category"][cat] = results["by_category"].get(cat, 0) + 1

        # Check duplication if requested
        if args.check_duplication or not (args.check_purity):
            # Default to duplication check if nothing specified
            matrix = guideline_audit.duplication_matrix(guidelines, min_similarity=args.threshold)

            results["duplication"] = {
                "pairs_found": len(matrix),
                "threshold": args.threshold,
            }

            if output_format == "matrix":
                # Output detailed matrix (matrix items are dicts with 'path1', 'path2', 'similarity')
                for item in sorted(matrix, key=lambda x: x.get("similarity", 0), reverse=True):
                    path1 = item["path1"]
                    path2 = item["path2"]
                    score = item["similarity"]
                    rel1 = path1.relative_to(repo_root) if path1.is_relative_to(repo_root) else path1
                    rel2 = path2.relative_to(repo_root) if path2.is_relative_to(repo_root) else path2
                    print(f"{score:.2f}\t{rel1}\t{rel2}")
                return 0

            # Add high-duplication pairs to issues
            for item in matrix:
                path1 = item["path1"]
                path2 = item["path2"]
                score = item["similarity"]
                results["issues"].append({
                    "type": "duplication",
                    "severity": "high" if score >= 0.5 else "medium",
                    "score": round(score, 3),
                    "files": [str(path1), str(path2)],
                })

        # Check purity if requested
        if args.check_purity:
            violations_dict = guideline_audit.purity_violations(guidelines)

            # Flatten all violation categories into a single list
            all_violations = []
            for category, violations_list in violations_dict.items():
                for violation in violations_list:
                    all_violations.append({
                        "category": category,
                        **violation,
                    })

            results["purity"] = {
                "violations_found": len(all_violations),
                "by_category": {k: len(v) for k, v in violations_dict.items()},
            }

            for violation in all_violations:
                results["issues"].append({
                    "type": "purity_violation",
                    "severity": "high",
                    "file": str(violation.get("path", "unknown")),
                    "category": violation.get("category", "unknown"),
                    "terms": violation.get("terms", []),
                    "message": violation.get("message", ""),
                })

        # Output results
        if output_format == "json":
            print(json.dumps(results, indent=2))
        else:
            # Text output
            print(f"Guideline Audit Results")
            print(f"=" * 50)
            print(f"Total guidelines: {results['total_guidelines']}")
            print(f"\nBy category:")
            for cat, count in sorted(results["by_category"].items()):
                print(f"  {cat}: {count}")

            if "duplication" in results:
                dup = results["duplication"]
                print(f"\nDuplication check:")
                print(f"  Threshold: {dup['threshold']}")
                print(f"  Pairs found: {dup['pairs_found']}")

            if "purity" in results:
                purity = results["purity"]
                print(f"\nPurity check:")
                print(f"  Violations found: {purity['violations_found']}")

            if results["issues"]:
                print(f"\nIssues found: {len(results['issues'])}")
                for issue in results["issues"][:10]:  # Show first 10
                    print(f"  - [{issue['severity']}] {issue['type']}")
                    if issue["type"] == "duplication":
                        print(f"    Score: {issue['score']}")
                    elif issue["type"] == "purity_violation":
                        print(f"    File: {issue['file']}")
                        print(f"    Terms: {', '.join(issue['terms'][:5])}")
                if len(results["issues"]) > 10:
                    print(f"  ... and {len(results['issues']) - 10} more")
            else:
                print(f"\nNo issues found!")

        return 0

    except Exception as e:
        if args.json or args.format == "json":
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
