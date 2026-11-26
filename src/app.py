"""Chat web app: serves the chat page and answers questions through a JSON API.

See specs/task6_chat_interface.md for the expected behavior and
tests/test_app.py for the tests.

Usage: .venv/Scripts/python.exe src/app.py, then open http://127.0.0.1:5000
With GEMINI_API_KEY set, answers come from Google Gemini (see src/llm.py).
Without it, the app runs in demo mode (see demo_generate).
"""
import json
import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from citations import collect_citations
from grounding import answer_question
from llm import MODEL, choose_generate
from rate_limit import RateLimiter

PROJECT_DIR = Path(__file__).parent.parent
CHUNKS_PATH = PROJECT_DIR / "data" / "chunks.json"

# Messages shown to visitors. They never contain internal details such as errors or paths.
EMPTY_QUESTION = "Please enter a question."

# Same limit as the input field's maxlength in templates/chat.html
MAX_QUESTION_LENGTH = 500
# Exactly MAX_QUESTION_LENGTH characters are allowed, so "or fewer", not "under"
QUESTION_TOO_LONG = f"Please keep your question to {MAX_QUESTION_LENGTH} characters or fewer."
CONTENT_UNAVAILABLE = "ReDI information is temporarily unavailable. Please try again later."
SERVER_ERROR = "Something went wrong while answering your question. Please try again."
# Gemini's free tier allows 15 requests per minute for everyone together; trying again right
# away doesn't help (specs/gemini_error_handling.md, "Iteration: a message for the used-up quota")
MODEL_BUSY = "The chatbot is getting a lot of questions right now. Please wait a minute and try again."
QUOTA_EXCEEDED = 429

# One visitor may not use up the shared quota alone (specs/rate_limit_per_visitor.md).
# Only questions that reach Gemini count.
QUESTIONS_PER_MINUTE = 5
VISITOR_LIMIT = "You're asking very quickly. Please wait a moment and try again."


class VisitorLimitReached(Exception):
    """Raised instead of calling the model when a visitor has asked too often."""


def visitor_key(request):
    """Return the visitor's IP address: the first X-Forwarded-For entry, else the connection's.

    On Render every request comes through a proxy, which adds the address it sees at the end
    of X-Forwarded-For. How many proxies there are isn't documented, so the first entry is
    used: counting from the end could give a proxy address shared by many visitors.
    """
    first_forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return first_forwarded or request.remote_addr or "unknown"


# TEMPORARY (specs/rate_limit_per_visitor.md, "Iteration: the visitor's real address (F2)",
# step 1): shows how Render forwards the address. Step 2 removes it.
OTHER_FORWARDING_HEADERS = ["Forwarded", "X-Real-IP", "True-Client-IP", "CF-Connecting-IP", "CF-Ray"]
CLIENT_ADDRESS_HEADERS = ["X-Real-IP", "True-Client-IP", "CF-Connecting-IP"]


def forwarding_summary(request):
    """Describe the forwarding headers by counts, names and positions, never by their values."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    entries = [entry.strip() for entry in forwarded.split(",") if entry.strip()]
    parts = [f"X-Forwarded-For has {len(entries)} entries"]
    present = [name for name in OTHER_FORWARDING_HEADERS if name in request.headers]
    parts.append("other headers: " + (", ".join(present) or "none"))
    for name in CLIENT_ADDRESS_HEADERS:
        value = request.headers.get(name, "").strip()
        if value:
            position = entries.index(value) + 1 if value in entries else None
            parts.append(f"{name} = entry {position} of {len(entries)}" if position else f"{name} = no entry")
    return "; ".join(parts)

# Offered when retrieval finds nothing, so the visitor can ask ReDI directly.
# The URL is an approved source in data/sources.json; tests/test_app.py checks that.
CONTACT_URL = "https://www.redi-school.org/contact"
CONTACT_TITLE = "ReDI contact page"

DEMO_ANSWER = (
    "Demo mode: no language model is connected yet, so this is not a real answer. "
    "The sources below are the ReDI pages that match your question."
)


def demo_generate(prompt):
    """Stand-in for the language model when GEMINI_API_KEY is not set."""
    return DEMO_ANSWER


def load_chunks(path=CHUNKS_PATH):
    """Return the saved ingestion chunks, or an empty list when the file does not exist.

    A file that is not a JSON list raises RuntimeError, so the app doesn't start: on Render a
    started app without content would replace a working version (specs/task10_update_loop.md,
    "Iteration: a safe chunks.json").
    """
    path = Path(path)
    if not path.exists():
        return []
    try:
        chunks = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(broken_chunks_file(path, f"not valid JSON: {error}")) from error
    if not isinstance(chunks, list):
        raise RuntimeError(broken_chunks_file(path, "not a list of chunks"))
    return chunks


def broken_chunks_file(path, problem):
    # The ingestion refuses a broken file too, so restoring it comes first
    return (f"{path} is {problem}. Restore the committed version with: git checkout "
            "data/chunks.json (then re-run the ingestion if needed)")


def create_app(chunks, generate, rate_limiter=None):
    """Build the Flask app.

    chunks are the ingested ReDI chunks. generate(prompt) calls the model and returns
    its answer, so tests and demo mode can pass in their own function.
    rate_limiter (a RateLimiter) limits the model calls per visitor; without it there is
    no limit, as in the tests and the local evaluation runs.
    """
    app = Flask(
        __name__,
        template_folder=str(PROJECT_DIR / "templates"),
        static_folder=str(PROJECT_DIR / "static"),
    )

    @app.get("/")
    def chat_page():
        # The welcome screen links to the same contact page the answers offer
        return render_template("chat.html", contact_url=CONTACT_URL)

    @app.post("/api/chat")
    def chat():
        # silent=True gives None for a missing or malformed JSON body instead of raising
        body = request.get_json(silent=True)
        question = body.get("question") if isinstance(body, dict) else None
        if not isinstance(question, str) or not question.strip():
            return jsonify(error=EMPTY_QUESTION), 400
        question = question.strip()
        # The page limits the input too, but direct API calls must not cause large model calls
        if len(question) > MAX_QUESTION_LENGTH:
            return jsonify(error=QUESTION_TOO_LONG), 400

        # answer_question raises ValueError for this case too, but checking first
        # keeps a ValueError from the model from being reported as missing content
        if not chunks:
            return jsonify(error=CONTENT_UNAVAILABLE), 503

        # The limit is checked right before the model call, so small talk and questions the
        # sources don't cover never count
        def limited_generate(prompt):
            if rate_limiter is not None:
                app.logger.info(forwarding_summary(request))  # TEMPORARY, see forwarding_summary
            if rate_limiter is not None and not rate_limiter.allow(visitor_key(request)):
                raise VisitorLimitReached()
            return generate(prompt)

        try:
            result = answer_question(question, chunks, limited_generate)
        except VisitorLimitReached:
            # Logged without the address: it is personal data and stays in memory only
            app.logger.info("A visitor reached the limit of %d questions per minute", QUESTIONS_PER_MINUTE)
            return jsonify(error=VISITOR_LIMIT), 429
        except Exception as error:
            # The details go to the server log only, never to the visitor
            app.logger.exception("Answering a question failed")
            # Gemini's errors carry the HTTP status as "code"; checking the attribute means
            # this module doesn't need to import Google's SDK
            if getattr(error, "code", None) == QUOTA_EXCEEDED:
                return jsonify(error=MODEL_BUSY), QUOTA_EXCEEDED
            return jsonify(error=SERVER_ERROR), 500

        response = {
            "answer": result.text,
            "enough_information": result.enough_information,
            "sources": collect_citations(result.sources),
        }
        # When retrieval found nothing, when the model marked the answer as not (fully) covered,
        # or when nothing of its answer was left after cleaning; the link is never one of the sources
        if not result.enough_information:
            response["contact"] = {"title": CONTACT_TITLE, "url": CONTACT_URL}
        return jsonify(response)

    return app


def log_startup(app, chunks, generate):
    """Log once at startup which content and which model the app answers with.

    On a server nobody watches the page, so a missing GEMINI_API_KEY or missing content
    has to show up in the log, not only in the visitors' answers.
    """
    app.logger.setLevel(logging.INFO)
    if not chunks:
        app.logger.error(
            "No ReDI content loaded: data/chunks.json is missing or empty, "
            "so every question gets the 'temporarily unavailable' error."
        )
    if generate is demo_generate:
        app.logger.warning(
            "Demo mode: GEMINI_API_KEY is not set, so answers are placeholders, not real answers."
        )
    else:
        app.logger.info(f"Answering with Gemini ({MODEL}) from {len(chunks)} chunks.")


# gunicorn loads this module-level variable called "app" ("app:app" in the Dockerfile, on Render)
chunks = load_chunks()
generate = choose_generate(demo_generate)
rate_limiter = RateLimiter(QUESTIONS_PER_MINUTE, window_seconds=60)
app = create_app(chunks, generate, rate_limiter=rate_limiter)
log_startup(app, chunks, generate)

if __name__ == "__main__":
    # Debug mode stays off: its error page can run Python code and shows stack traces
    app.run()
