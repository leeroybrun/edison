"""
Edison qa audit command.

SUMMARY: Audit guidelines quality
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.composition import audit as guideline_audit
from edison.core.utils.io import write_json_atomic

SUMMARY = "Audit guidelines quality"
AUDIT_TASK_ID = "fix-9-guidelines-audit"


def _resolve_threshold(repo_root: Path) -> float:
    """Resolve duplication threshold from config (NO HARDCODED VALUES).

    Priority:
    1) Project-aware CompositionConfig (core + packs + project)
    2) Bundled config fallback (still config-driven)
    """
    try:
        from edison.core.config.domains.composition import CompositionConfig

        return float(CompositionConfig(repo_root=repo_root).threshold)
    except Exception:
        from edison.core.utils.io import read_yaml
        from edison.data import get_data_path

        bundled = get_data_path("config", "composition.yaml")
        data = read_yaml(Path(bundled), default={}, raise_on_error=True) or {}
        composition = data.get("composition", {}) if isinstance(data, dict) else {}
        defaults = composition.get("defaults", {}) if isinstance(composition, dict) else {}
        dedupe = defaults.get("dedupe", {}) if isinstance(defaults, dict) else {}
        threshold = dedupe.get("threshold")
        if threshold is None:
            raise ValueError("composition.defaults.dedupe.threshold is missing from bundled config")
        return float(threshold)


def _normalize_duplication_item(item: dict, repo_root: Path) -> tuple[str, str, float]:
    """Normalize duplication matrix item into (path1, path2, similarity)."""
    similarity = float(item.get("similarity", 0.0))

    # New shape (preferred): {"a": {"path": "..."}, "b": {"path": "..."}}
    if "a" in item and "b" in item:
        a = item.get("a") or {}
        b = item.get("b") or {}
        if isinstance(a, dict) and isinstance(b, dict):
            p1 = str(a.get("path") or "")
            p2 = str(b.get("path") or "")
            if not p1 or not p2:
                raise KeyError("duplication item missing a.path or b.path")
            return p1, p2, similarity

    # Legacy shape (deprecated): {"path1": Path, "path2": Path}
    if "path1" in item and "path2" in item:
        p1 = item["path1"]
        p2 = item["path2"]
        path1 = str(p1.relative_to(repo_root) if hasattr(p1, "relative_to") else p1)
        path2 = str(p2.relative_to(repo_root) if hasattr(p2, "relative_to") else p2)
        return path1, path2, similarity

    raise KeyError("Unrecognized duplication matrix item shape")


def _default_threshold() -> float:
    """Default threshold for CLI args (config-driven, no hardcoded values)."""
    try:
        from edison.core.utils.paths import PathResolver

        return _resolve_threshold(PathResolver.resolve_project_root())
    except Exception:
        # Fall back to bundled config via _resolve_threshold's own fallback path.
        from edison.data import get_data_path

        return _resolve_threshold(Path(get_data_path("")).resolve())


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
        default=_default_threshold(),
        help="Duplication threshold (0.0-1.0). Defaults to composition config.",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Audit guidelines - delegates to guideline_audit library."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        threshold = args.threshold if args.threshold is not None else _resolve_threshold(repo_root)

        # Force JSON format if --json flag is used
        output_format = "json" if formatter.json_mode else args.format

        # Discover all guidelines
        guidelines = guideline_audit.discover_guidelines(repo_root)

        # Filter to specific path if requested
        if args.path:
            path_filter = Path(args.path).resolve()
            guidelines = [g for g in guidelines if g.path == path_filter or path_filter in g.path.parents]

        if not guidelines:
            formatter.error("No guidelines found", error_code="no_guidelines")
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
            matrix = guideline_audit.duplication_matrix(guidelines, min_similarity=threshold)

            results["duplication"] = {
                "pairs_found": len(matrix),
                "threshold": threshold,
            }

            if output_format == "matrix":
                # Output detailed matrix (matrix items are dicts with 'path1', 'path2', 'similarity')
                for item in sorted(matrix, key=lambda x: x.get("similarity", 0), reverse=True):
                    path1, path2, score = _normalize_duplication_item(item, repo_root)
                    formatter.text(f"{score:.2f}\t{path1}\t{path2}")
                return 0

            # Add high-duplication pairs to issues
            for item in matrix:
                path1, path2, score = _normalize_duplication_item(item, repo_root)
                results["issues"].append({
                    "type": "duplication",
                    "severity": "high" if score >= 0.5 else "medium",
                    "score": round(score, 3),
                    "files": [path1, path2],
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
                term = violation.get("term")
                line = violation.get("line")
                text = violation.get("text")
                message_parts = []
                if term:
                    message_parts.append(f"term='{term}'")
                if line:
                    message_parts.append(f"line={line}")
                if text:
                    message_parts.append(f"text={text!r}")
                message = "; ".join(message_parts)
                results["issues"].append({
                    "type": "purity_violation",
                    "severity": "high",
                    "file": str(violation.get("path", "unknown")),
                    "category": violation.get("category", "unknown"),
                    "terms": [term] if term else [],
                    "message": message,
                })

        # Output results
        # Persist evidence under QA validation-evidence for audit traceability.
        # This is not a "task" per se, but we still store evidence in the canonical evidence root.
        try:
            from edison.core.qa._utils import get_evidence_base_path

            evidence_root = get_evidence_base_path(repo_root) / AUDIT_TASK_ID
            evidence_root.mkdir(parents=True, exist_ok=True)
            write_json_atomic(evidence_root / "summary.json", results)
        except Exception:
            # Evidence writing must never block the audit output.
            pass

        if output_format == "json":
            formatter.json_output(results)
        else:
            # Text output
            formatter.text(f"Guideline Audit Results")
            formatter.text(f"=" * 50)
            formatter.text(f"Total guidelines: {results['total_guidelines']}")
            formatter.text(f"\nBy category:")
            for cat, count in sorted(results["by_category"].items()):
                formatter.text(f"  {cat}: {count}")

            if "duplication" in results:
                dup = results["duplication"]
                formatter.text(f"\nDuplication check:")
                formatter.text(f"  Threshold: {dup['threshold']}")
                formatter.text(f"  Pairs found: {dup['pairs_found']}")

            if "purity" in results:
                purity = results["purity"]
                formatter.text(f"\nPurity check:")
                formatter.text(f"  Violations found: {purity['violations_found']}")

            if results["issues"]:
                formatter.text(f"\nIssues found: {len(results['issues'])}")
                for issue in results["issues"][:10]:  # Show first 10
                    formatter.text(f"  - [{issue['severity']}] {issue['type']}")
                    if issue["type"] == "duplication":
                        formatter.text(f"    Score: {issue['score']}")
                    elif issue["type"] == "purity_violation":
                        formatter.text(f"    File: {issue['file']}")
                        formatter.text(f"    Terms: {', '.join(issue['terms'][:5])}")
                if len(results["issues"]) > 10:
                    formatter.text(f"  ... and {len(results['issues']) - 10} more")
            else:
                formatter.text(f"\nNo issues found!")

        return 0

    except Exception as e:
        formatter.error(e, error_code="audit_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
