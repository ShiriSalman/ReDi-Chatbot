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


def start_command():
    return next(line for line in read(DOCKERFILE).splitlines() if line.startswith("CMD"))


def option_value(command, option):
    return int(re.search(rf'"{option}",\s*"(\d+)"', command).group(1))


# AC2: gunicorn serves the app, and a redeploy doesn't kill a slow Gemini answer.
# With threads gunicorn uses the gthread worker, where --timeout doesn't limit a request;
# --graceful-timeout is what cuts off answers still running on a restart.
def test_dockerfile_starts_gunicorn_with_a_long_enough_graceful_timeout():
    command = start_command()

    assert "gunicorn" in command
    assert "app:app" in command
    assert option_value(command, "--graceful-timeout") > RETRY_ATTEMPTS * TIMEOUT_MS / 1000


def test_dockerfile_uses_one_worker():
    # A second worker would load the chunks and the Gemini client twice for no benefit
    assert option_value(start_command(), "--workers") == 1


# AC9: the same Python version on every build
def test_base_image_is_pinned_to_a_patch_version():
    assert re.search(r"^FROM python:\d+\.\d+\.\d+-slim$", read(DOCKERFILE), re.MULTILINE)


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
