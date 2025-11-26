from __future__ import annotations

import ast
from pathlib import Path


BANNED = (".edison", ".agents")
ALLOWLIST = {
    # Centralized helper is allowed to mention the default dir name.
    Path("src/edison/core/paths/project.py").resolve(),
}


class _PathLiteralVisitor(ast.NodeVisitor):
    def __init__(self, banned: tuple[str, ...]):
        self.banned = banned
        self.violations: list[tuple[int, str]] = []

    def _check_constant(self, node: ast.AST) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if any(item in node.value for item in self.banned):
                self.violations.append((node.lineno, node.value))

    def visit_BinOp(self, node: ast.BinOp) -> None:  # type: ignore[override]
        # Path joins use the Div operator (``/``) and occasionally Add.
        if isinstance(node.op, (ast.Div, ast.Add)):
            self._check_constant(node.left)
            self._check_constant(node.right)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # type: ignore[override]
        # Calls like Path(".edison")
        func_name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if func_name == "Path":
            for arg in node.args:
                self._check_constant(arg)
        self.generic_visit(node)


def _iter_python_files() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[2]
    return sorted((repo_root / "src" / "edison").rglob("*.py"))


def test_no_hardcoded_project_paths():
    offenders: list[tuple[Path, int, str]] = []
    for path in _iter_python_files():
        if path.resolve() in ALLOWLIST:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        visitor = _PathLiteralVisitor(BANNED)
        visitor.visit(tree)
        for line, value in visitor.violations:
            offenders.append((path, line, value))

    if offenders:
        details = "\n".join(
            f"{p}:{line} contains banned literal '{value}'" for p, line, value in offenders
        )
        raise AssertionError(
            "Hardcoded project paths detected. Use get_project_config_dir instead:\n" + details
        )
