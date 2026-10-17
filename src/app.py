"""Chat web app: serves the chat page and answers questions through a JSON API.

See specs/task6_chat_interface.md for the expected behavior and
tests/test_app.py for the tests.

Usage: .venv/Scripts/python.exe src/app.py, then open http://127.0.0.1:5000
No language model is connected yet, so the app runs in demo mode (see demo_generate).
"""
import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from citations import collect_citations
from grounding import answer_question

PROJECT_DIR = Path(__file__).parent.parent
CHUNKS_PATH = PROJECT_DIR / "data" / "chunks.json"

# Messages shown to visitors. They never contain internal details such as errors or paths.
EMPTY_QUESTION = "Please enter a question."
QUESTION_TOO_LONG = "Please keep your question under 500 characters."

# Same limit as the input field's maxlength in templates/chat.html
MAX_QUESTION_LENGTH = 500
CONTENT_UNAVAILABLE = "ReDI information is temporarily unavailable. Please try again later."
SERVER_ERROR = "Something went wrong while answering your question. Please try again."

# Offered when retrieval finds nothing, so the visitor can ask ReDI directly.
# The URL is an approved source in data/sources.json; tests/test_app.py checks that.
CONTACT_URL = "https://www.redi-school.org/contact"
CONTACT_TITLE = "ReDI contact page"

DEMO_ANSWER = (
    "Demo mode: no language model is connected yet, so this is not a real answer. "
    "The sources below are the ReDI pages that match your question."
)


def demo_generate(prompt):
    """Stand-in for the language model until a real one is configured."""
    return DEMO_ANSWER


def load_chunks(path=CHUNKS_PATH):
    """Return the saved ingestion chunks, or an empty list when the file does not exist."""
    path = Path(path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def create_app(chunks, generate):
    """Build the Flask app.

    chunks are the ingested ReDI chunks. generate(prompt) calls the model and returns
    its answer, so tests and demo mode can pass in their own function.
    """
    app = Flask(
        __name__,
        template_folder=str(PROJECT_DIR / "templates"),
        static_folder=str(PROJECT_DIR / "static"),
    )

    @app.get("/")
    def chat_page():
        return render_template("chat.html")

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

        try:
            result = answer_question(question, chunks, generate)
        except Exception:
            # The details go to the server log only, never to the visitor
            app.logger.exception("Answering a question failed")
            return jsonify(error=SERVER_ERROR), 500

        response = {
            "answer": result.text,
            "enough_information": result.enough_information,
            "sources": collect_citations(result.sources),
        }
        # Only when retrieval found nothing; the link is never one of the sources
        if not result.enough_information:
            response["contact"] = {"title": CONTACT_TITLE, "url": CONTACT_URL}
        return jsonify(response)

    return app


# Vercel looks for a module-level variable called "app"
app = create_app(load_chunks(), demo_generate)

if __name__ == "__main__":
    # Debug mode stays off: its error page can run Python code and shows stack traces
    app.run()
