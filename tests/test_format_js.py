"""Runs the JavaScript tests for the answer formatting (specs/ui_redesign.md, AC12).

The tests themselves are in tests/js/ and use Node's built-in test runner, so no
packages are needed. Without Node they are skipped (Render only runs the app).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

JS_TESTS = Path(__file__).parent / "js"
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is not installed")
def test_answer_formatting_javascript_tests_pass():
    result = subprocess.run(
        [NODE, "--test", *sorted(str(path) for path in JS_TESTS.glob("*.test.cjs"))],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
