import ast
import subprocess
import sys
from pathlib import Path

import trano_optimization

PACKAGE = Path(trano_optimization.__file__).parent


def test_the_package_imports() -> None:
    assert trano_optimization.__doc__


def test_the_package_does_not_import_trano() -> None:
    modules = [f"trano_optimization.{path.stem}" for path in PACKAGE.glob("*.py") if path.stem != "__init__"]
    code = (
        f"import importlib, sys\nfor m in {modules!r}: importlib.import_module(m)\n"
        "print(sorted(m for m in sys.modules if m == 'trano' or m.startswith('trano.')))"
    )
    loaded = subprocess.run(  # noqa: S603 - the interpreter running the tests, on code written above
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert loaded == "[]"


def test_no_module_of_the_package_imports_trano() -> None:
    imports = [
        f"{path.name}: {name}"
        for path in PACKAGE.glob("*.py")
        for node in ast.walk(ast.parse(path.read_text()))
        for name in (
            [node.module or ""]
            if isinstance(node, ast.ImportFrom)
            else [alias.name for alias in node.names]
            if isinstance(node, ast.Import)
            else []
        )
        if name.split(".")[0] == "trano"
    ]
    assert imports == []
