# Tests for the Render deployment files, written from specs/task9_deploy_render.md.
# Dockerfile and .dockerignore don't exist yet, so these tests fail until they are written.
# Docker isn't installed on the development machine, so the image itself is first built on
# Render; these tests guard the parts that would otherwise only fail there.
import re
from pathlib import Path

import pytest

from llm import RETRY_ATTEMPTS, TIMEOUT_MS

PROJECT_DIR = Path(__file__).parent.parent
DOCKERFILE = PROJECT_DIR / "Dockerfile"
DOCKERIGNORE = PROJECT_DIR / ".dockerignore"
REQUIREMENTS = PROJECT_DIR / "requirements.txt"


def read(path):
    return path.read_text(encoding="utf-8")


# AC1: everything the app needs at runtime is in the image
@pytest.mark.parametrize("path", ["data/chunks.json", "src/", "templates/", "static/"])
def test_dockerfile_copies_what_the_app_needs(path):
    assert re.search(rf"^COPY\s+{re.escape(path)}\s", read(DOCKERFILE), re.MULTILINE)


# AC2: gunicorn serves the app and doesn't kill a slow Gemini answer
def test_dockerfile_starts_gunicorn_with_a_long_enough_timeout():
    dockerfile = read(DOCKERFILE)
    command = next(line for line in dockerfile.splitlines() if line.startswith("CMD"))

    assert "gunicorn" in command
    assert "app:app" in command
    timeout = int(re.search(r'"--timeout",\s*"(\d+)"', command).group(1))
    assert timeout > RETRY_ATTEMPTS * TIMEOUT_MS / 1000


# AC3: no secrets in the image
def test_dockerfile_contains_no_api_key():
    dockerfile = read(DOCKERFILE)

    assert "GEMINI_API_KEY" not in dockerfile
    assert "AIza" not in dockerfile


@pytest.mark.parametrize("entry", [".env", ".venv", ".git"])
def test_dockerignore_excludes_secrets_and_local_files(entry):
    assert entry in read(DOCKERIGNORE).splitlines()


# AC4
def test_gunicorn_is_pinned():
    assert re.search(r"^gunicorn==\d", read(REQUIREMENTS), re.MULTILINE)
