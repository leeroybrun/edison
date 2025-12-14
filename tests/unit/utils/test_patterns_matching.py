from __future__ import annotations

from edison.core.utils.patterns import match_patterns, matches_any_pattern


def test_match_patterns_supports_globstar_directory_depth() -> None:
    files = ["apps/api/server.ts", "apps/api/routes/v1/health.ts"]
    assert match_patterns(files, ["apps/api/**/*"]) == files


def test_matches_any_pattern_supports_brace_expansion() -> None:
    assert matches_any_pattern(
        "apps/dashboard/app/page.tsx",
        ["apps/dashboard/**/*.{tsx,jsx}"],
    )
    assert matches_any_pattern(
        "apps/dashboard/app/page.jsx",
        ["apps/dashboard/**/*.{tsx,jsx}"],
    )


def test_bare_filename_glob_matches_anywhere() -> None:
    assert matches_any_pattern("src/components/Button.tsx", ["*.tsx"])

