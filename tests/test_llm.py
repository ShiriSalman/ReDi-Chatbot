# Tests for the Gemini connection, written from specs/gemini_error_handling.md.
# src/llm.py does not exist yet, so every test fails until it is written.
# A fake client stands in for Gemini, so the tests never call the network and need no API key.
# The errors are real SDK classes, built without a request, so the tests check the exact
# exceptions Gemini raises.
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import errors

from app import SERVER_ERROR, create_app, demo_generate
from llm import MODEL, RETRY_ATTEMPTS, TIMEOUT_MS, choose_generate, make_gemini_generate

FREE_CHUNK = {
    "text": "All our courses are free of charge for every learner.",
    "url": "https://www.redi-school.org/faq",
    "title": "FAQ",
    "category": "Applications",
    "language": "en",
    "last_updated": "unavailable",
}
QUESTION = "Are the courses free?"
SRC_DIR = Path(__file__).parent.parent / "src"


def fake_client(text="Yes, all courses are free.", error=None):
    """A stand-in for genai.Client: records each generate_content call, then answers or raises."""
    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        if error:
            raise error
        return SimpleNamespace(text=text)

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    client.calls = calls
    return client


def gemini_error(error_class, code, status, message):
    return error_class(code, {"error": {"code": code, "message": message, "status": status}})


def ask(generate):
    app = create_app(chunks=[FREE_CHUNK], generate=generate)
    app.config["TESTING"] = True
    return app.test_client().post("/api/chat", json={"question": QUESTION})


# AC1 and AC2: the request and the answer
class TestGenerate:
    def test_sends_the_prompt_to_the_model(self):
        client = fake_client()

        make_gemini_generate(client)("the prompt")

        assert client.calls == [{"model": MODEL, "contents": "the prompt"}]

    def test_returns_the_text_from_gemini(self):
        generate = make_gemini_generate(fake_client("Yes, all courses are free."))

        assert generate("the prompt") == "Yes, all courses are free."

    # AC3: blocked or empty answers are errors, not an empty chat message
    @pytest.mark.parametrize("text", [None, "", "   "], ids=["blocked", "empty", "blank"])
    def test_raises_when_gemini_returns_no_text(self, text):
        generate = make_gemini_generate(fake_client(text))

        with pytest.raises(ValueError):
            generate("the prompt")


# AC4 to AC6: Gemini errors reach the visitor as the existing friendly 500
GEMINI_ERRORS = {
    "invalid API key": gemini_error(
        errors.ClientError, 401, "UNAUTHENTICATED", "API key not valid. Please pass a valid API key."
    ),
    "invalid model name": gemini_error(
        errors.ClientError, 404, "NOT_FOUND", "models/gemini-unknown is not found."
    ),
    "Gemini server error": gemini_error(
        errors.ServerError, 503, "UNAVAILABLE", "The model is overloaded."
    ),
}


class TestErrors:
    @pytest.mark.parametrize("error", GEMINI_ERRORS.values(), ids=GEMINI_ERRORS.keys())
    def test_gemini_errors_give_a_friendly_error(self, error):
        response = ask(make_gemini_generate(fake_client(error=error)))

        assert response.status_code == 500
        assert response.get_json() == {"error": SERVER_ERROR}
        body = response.get_data(as_text=True)
        assert error.message not in body
        assert "key" not in body.lower()

    def test_a_blocked_answer_gives_a_friendly_error(self):
        response = ask(make_gemini_generate(fake_client(text=None)))

        assert response.status_code == 500
        assert response.get_json() == {"error": SERVER_ERROR}


# AC7: Gemini only with GEMINI_API_KEY, demo mode otherwise
class TestChooseGenerate:
    @pytest.mark.parametrize(
        "environ",
        [{}, {"GEMINI_API_KEY": "   "}, {"GOOGLE_API_KEY": "google-key"}],
        ids=["no key", "blank key", "only GOOGLE_API_KEY"],
    )
    def test_uses_demo_mode_without_an_api_key(self, environ):
        assert choose_generate(demo_generate, environ=environ) is demo_generate

    def test_uses_gemini_with_the_key_from_gemini_api_key(self, monkeypatch):
        created = record_client_creation(monkeypatch)

        generate = choose_generate(
            demo_generate, environ={"GEMINI_API_KEY": "test-key", "GOOGLE_API_KEY": "google-key"}
        )

        assert len(created) == 1
        assert created[0]["api_key"] == "test-key"
        assert generate("the prompt") == "Answer from Gemini."

    # AC11: on 2026-10-25 a network error and a 503 "high demand" each failed a question at once
    def test_client_gets_a_timeout_and_retries(self, monkeypatch):
        created = record_client_creation(monkeypatch)

        choose_generate(demo_generate, environ={"GEMINI_API_KEY": "test-key"})

        http_options = created[0]["http_options"]
        assert http_options.timeout == TIMEOUT_MS
        assert http_options.retry_options.attempts == RETRY_ATTEMPTS


def record_client_creation(monkeypatch):
    """Replace genai.Client with a fake and return the list of arguments it was created with."""
    created = []

    def fake_genai_client(**kwargs):
        created.append(kwargs)
        return fake_client("Answer from Gemini.")

    monkeypatch.setattr("google.genai.Client", fake_genai_client)
    return created


# Security: no Gemini key is ever written in the code (Google API keys start with "AIza")
def test_no_api_key_is_hardcoded():
    for path in SRC_DIR.glob("*.py"):
        assert "AIza" not in path.read_text(encoding="utf-8"), path.name
