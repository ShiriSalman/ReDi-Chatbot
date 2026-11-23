# Tests for the architecture rule "fetching must not depend on ingestion",
# written from specs/fetching_import_guard.md. They replace the import-linter
# contract, which couldn't fail because the code imports modules without "src.".
import ast
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent


def imported_modules(source):
    """Return the names of all modules the Python source imports, also inside functions.

    "import src.ingestion" gives "src.ingestion"; "from ingestion import x" gives "ingestion".
    """
    modules = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def imports_ingestion(source):
    """True if the source imports the ingestion module, with or without the "src." prefix."""
    return any(module.split(".")[-1] == "ingestion" for module in imported_modules(source))


# AC1
def test_fetching_does_not_import_ingestion():
    source = (PROJECT_DIR / "src" / "fetching.py").read_text(encoding="utf-8")

    assert not imports_ingestion(source)


# AC2: the check can fail
@pytest.mark.parametrize("source", [
    "import ingestion",
    "from ingestion import chunk_text",
    "import src.ingestion",
    "from src.ingestion import chunk_text",
    "import requests, ingestion",
    "def fetch():\n    from ingestion import chunk_text\n",
])
def test_every_import_form_is_found(source):
    assert imports_ingestion(source)


# AC3
@pytest.mark.parametrize("source", [
    "import run_ingestion",
    "from ingestion_helpers import x",
    "import requests",
    "from . import something",
])
def test_similar_names_are_not_reported(source):
    assert not imports_ingestion(source)


# AC4
def test_the_import_linter_config_is_gone():
    assert not (PROJECT_DIR / ".importlinter").exists()
