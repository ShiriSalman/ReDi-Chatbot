# Image for running the chatbot on Render. See specs/task9_deploy_render.md.
# The Gemini key is set as an environment variable in Render's dashboard and never belongs here.
FROM python:3.14-slim

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

# gunicorn binds to 0.0.0.0:$PORT by itself. --timeout is above the Gemini client's worst case
# (3 attempts x 60 seconds plus pauses); the default of 30 seconds would kill slow answers.
# Threads keep other visitors served while one answer waits for Gemini.
CMD ["gunicorn", "app:app", "--workers", "2", "--threads", "4", "--timeout", "200"]
