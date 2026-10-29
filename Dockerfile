# Image for running the chatbot on Render. See specs/task9_deploy_render.md.
# The Gemini key is set as an environment variable in Render's dashboard and never belongs here.
# Pinned to the venv's version, so every build on Render uses the same Python
FROM python:3.14.7-slim

# No .pyc files, logs appear immediately, and "from grounding import ..." works like in pytest.ini.
# PORT is only a default for a local "docker run"; Render sets its own.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=10000

WORKDIR /app

# Installed first, so this layer is reused when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only what the app needs at runtime
COPY src/ src/
COPY templates/ templates/
COPY static/ static/
COPY data/chunks.json data/chunks.json

# Don't run the web server as root
RUN useradd --create-home appuser
USER appuser

EXPOSE 10000

# gunicorn binds to 0.0.0.0:$PORT by itself. One worker with threads: the threads serve other
# visitors while one answer waits for Gemini, and a second worker would only load everything
# twice. With threads, --timeout doesn't limit a request; --graceful-timeout is what cuts off
# answers still running when Render restarts the service, so it is above the Gemini client's
# worst case (3 attempts x 60 seconds plus pauses) instead of the default 30 seconds.
CMD ["gunicorn", "app:app", "--workers", "1", "--threads", "4", "--graceful-timeout", "200"]
