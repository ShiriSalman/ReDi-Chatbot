# Task 9 – Deploy to Render with Docker

**Project:** ReDI School Chatbot  
**Status:** Specification

## Goal

Run the chatbot as a Docker web service on Render. The whole Flask app (the
chat page and `POST /api/chat`) runs in one container. The app's code and
behaviour don't change.

The owner decided on Render as the only hosting platform (2026-10-27).

## Facts from the docs (checked 2026-10-29)

- **Render** (`render.com/docs/docker`, `render.com/docs/web-services`):
  - Render builds the image from the repo's `Dockerfile` and starts its
    `CMD`.
  - A web service must bind to `0.0.0.0`, on the port in the `PORT`
    environment variable. The default is `10000`.
  - Environment variables are available at runtime. They are also passed as
    build arguments, so sensitive values must not be referenced in the
    `Dockerfile`.
- **gunicorn** (`gunicorn.org/reference/settings/`):
  - If `PORT` is set, the default bind is `0.0.0.0:$PORT`.
  - The default `timeout` is 30 seconds. Workers that are silent for longer
    are killed and restarted.

## Change

### New `Dockerfile`

- Based on `python:3.14-slim`, the same Python version as the venv.
- Installs `requirements.txt`.
- Copies only what the app needs at runtime: `src/`, `templates/`,
  `static/` and `data/chunks.json`.
- `PYTHONPATH=/app/src`, the same as `pythonpath = src` in `pytest.ini`, so
  `from grounding import …` works.
- `PORT=10000` as a default for a local `docker run`. Render sets `PORT`
  itself.
- Runs as a user without root rights.
- Starts with `gunicorn app:app --workers 2 --threads 4 --timeout 200`.
  - gunicorn binds to `0.0.0.0:$PORT` by itself.
  - `--timeout 200` covers the worst case of the Gemini client: 3 attempts ×
    60 seconds plus the pauses between them (`specs/gemini_error_handling.md`).
    The default of 30 seconds would kill a slow answer.
  - The threads let other visitors be served while one answer waits for
    Gemini.

### New `.dockerignore`

Keeps these out of the build context and the image:
- `.git`, `.venv`
- caches
- `tests/`, `docs/`, `specs/`
- `.playwright-mcp/`
- `data/raw/`
- `.env*` files

### `requirements.txt`

- Add `gunicorn==26.2.0`.

### Not changed

- `src/`, `templates/`, `static/`
- the JSON API (ADR 0002)

### Settings on Render (by hand)

- A new **Web Service** from the GitHub repo, with **Language: Docker**.
- **Environment:** `GEMINI_API_KEY` = the key. It is set in the dashboard
  only, never in the repo or the `Dockerfile`. Without it, the app runs in
  demo mode.
- **Health check path:** `/`.
- After re-running the ingestion, commit `data/chunks.json`. Render then
  builds a new image.

## Acceptance criteria

Checked by unit tests (`tests/test_deploy.py`):
- **AC1:** The `Dockerfile` copies `data/chunks.json`, `src/`, `templates/`
  and `static/`.
- **AC2:** The `Dockerfile` starts gunicorn with `app:app` and a timeout
  above the Gemini client's worst case
  (`RETRY_ATTEMPTS × TIMEOUT_MS / 1000`).
- **AC3:** The `Dockerfile` contains no API key or `GEMINI_API_KEY` value.
  `.dockerignore` excludes `.env`, `.venv` and `.git`.
- **AC4:** `gunicorn` is pinned in `requirements.txt`.
- **AC5:** All existing tests pass.

Checked by hand:
- **AC6:** The first build on Render succeeds and `/` shows the chat page.
- **AC7:** With `GEMINI_API_KEY` set on Render, "Are ReDI courses free?" gets
  a real answer with sources. Without it, it gets the demo answer.

## Iteration: fixes from the code review (2026-10-29)

A code review of the first version found these problems before the branch
was pushed. The gunicorn behaviour was checked in its settings reference.

1. **The timeout was wrong.** With `--threads`, gunicorn uses the `gthread`
   worker. For non-sync workers, `--timeout` "is not tied to the length of
   time required to handle a single request". What cuts off a slow answer
   is `--graceful-timeout` (default 30 s). On every redeploy, answers still
   running are killed after it runs out.
   - **Change:** `--graceful-timeout 200`, above the Gemini client's worst
     case. `--timeout` goes back to its default.
2. **Two workers loaded everything twice** (chunks and Gemini client). The
   threads already give concurrency, and the work is waiting for Gemini.
   - **Change:** `--workers 1 --threads 4`.
3. **The base image wasn't pinned.**
   - **Change:** `python:3.14.7-slim`, the venv's version (the tag exists
     on Docker Hub).
4. **Wrong configuration went unnoticed on a server.** Without
   `GEMINI_API_KEY`, the app quietly answered in demo mode. Without
   `data/chunks.json`, every question got 503. Neither showed up in the log.
   - **Change:** `log_startup(app, chunks, generate)` in `src/app.py` logs
     once when the module loads:
     - an **error** "No ReDI content loaded …" when there are no chunks
     - a **warning** "Demo mode: GEMINI_API_KEY is not set …" in demo mode
     - otherwise **info** "Answering with Gemini (<model>) from <n> chunks."
   - `app.logger` is set to `INFO`, so the info line shows in Render's log.
5. **An outdated comment.** The comment on the module-level `app` in
   `src/app.py` named an earlier host. It now says that gunicorn loads it
   (`app:app`).

**Changed acceptance criterion:**
- **AC2:** gunicorn uses one worker and a `--graceful-timeout` above
  `RETRY_ATTEMPTS × TIMEOUT_MS / 1000`.

**New acceptance criteria:**
- **AC8:** `log_startup` logs an error with no chunks, a warning in demo
  mode, and an info line with the model and number of chunks otherwise.
- **AC9:** The base image is pinned to a patch version (`python:3.X.Y-slim`).

**Out of scope:** limiting parallel Gemini calls for the free tier (review
point 3). It changes what visitors see when the limit is hit, so the owner
decides it separately.

## Known limitations

- **Docker is not installed on the development machine.** The image is
  first built on Render, so AC6 and AC7 are the real check.
- **gunicorn doesn't run on Windows.** `python src/app.py` stays the way to
  run the app locally.
- **Free-plan limits** (for example sleeping when idle) were not checked in
  the docs and should be read on Render's pricing page.
