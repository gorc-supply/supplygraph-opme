"""app/requirements.txt (read by Streamlit Community Cloud) must cover every third-party module the app
imports at module level - including through the `supplygraph` modules it loads - and must stay light
(no pipeline-only libraries). Static check: no network, no database."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
# import name -> distribution name (when they differ)
DIST = {"yaml": "pyyaml", "dotenv": "python-dotenv", "neo4j_viz": "neo4j-viz"}
FORBIDDEN = {"graphdatascience", "duckdb", "matplotlib", "typer", "jupyter", "pytest"}


def _module_imports(path: Path) -> list[str]:
    """Module-level imports only (imports inside functions run lazily and are not needed by the app)."""
    out: list[str] = []

    def visit(node: ast.AST, in_func: bool) -> None:
        for ch in ast.iter_child_nodes(node):
            f = in_func or isinstance(ch, ast.FunctionDef | ast.AsyncFunctionDef)
            if not f and isinstance(ch, ast.Import):
                out.extend(a.name for a in ch.names)
            elif not f and isinstance(ch, ast.ImportFrom) and ch.level == 0 and ch.module:
                out.append(ch.module)
                out.extend(f"{ch.module}.{a.name}" for a in ch.names)  # `from pkg import submodule`
            visit(ch, f)

    visit(ast.parse(path.read_text(encoding="utf-8")), False)
    return out


def _local_file(mod: str) -> Path | None:
    base = ROOT / "src" / Path(*mod.split("."))
    for p in (base.with_suffix(".py"), base / "__init__.py"):
        if p.exists():
            return p
    return None


def app_third_party_imports() -> dict[str, set[str]]:
    seen: set[Path] = set()
    found: dict[str, set[str]] = {}
    queue = sorted(APP.rglob("*.py"))
    while queue:
        f = queue.pop()
        if f in seen:
            continue
        seen.add(f)
        for mod in _module_imports(f):
            top = mod.split(".")[0]
            if top in sys.stdlib_module_names or top in ("__future__", "common"):
                continue
            if top == "supplygraph":
                parts = mod.split(".")
                queue += [p for i in range(1, len(parts) + 1) if (p := _local_file(".".join(parts[:i])))]
                continue
            found.setdefault(DIST.get(top, top), set()).add(f.relative_to(ROOT).as_posix())
    return found


def requirements() -> set[str]:
    names = set()
    for line in (APP / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            names.add(re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].lower())
    return names


def test_every_app_import_is_in_app_requirements():
    missing = {d: sorted(src) for d, src in app_third_party_imports().items() if d.lower() not in requirements()}
    assert not missing, f"add to app/requirements.txt: {missing}"


def test_app_requirements_stay_light():
    assert not (requirements() & FORBIDDEN), f"pipeline-only libraries in app/requirements.txt: {requirements() & FORBIDDEN}"


def test_no_unused_app_requirements():
    used = {d.lower() for d in app_third_party_imports()}
    assert requirements() <= used, f"listed but never imported by the app: {requirements() - used}"
