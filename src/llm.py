"""Gemini connection: turns a prompt into an answer from Google Gemini.

See specs/gemini_error_handling.md for the expected behavior and
tests/test_llm.py for the tests.

Errors from Gemini (invalid key, unknown model, server errors) are not caught here:
they reach the error handling in app.py, which logs them and shows the visitor a
friendly message.
"""
import os

# The models page lists it as stable and as the fastest, most cost-effective model
# (checked on 2026-10-24). gemini-3.8-flash was slower (56 seconds for one answer)
# and overloaded on 2026-10-25. Change it here.
MODEL = "gemini-3.5-flash-lite"

# The only setting that switches Gemini on. The key is never written in the code.
API_KEY_VARIABLE = "GEMINI_API_KEY"

# Without these the SDK tries once and waits without limit. With them it retries
# network errors, timeouts, 429 and 5xx (for example 503 "high demand") with growing
# pauses; a wrong key or model (4xx) is not retried. TIMEOUT_MS is per attempt and in
# milliseconds; a long answer took 56 seconds.
TIMEOUT_MS = 60_000
RETRY_ATTEMPTS = 3  # including the first try


def make_gemini_generate(client, model=MODEL):
    """Return a generate(prompt) function that asks Gemini through the given client.

    The client is passed in, so tests can use a fake one and never call the network.
    """

    def generate(prompt):
        response = client.models.generate_content(model=model, contents=prompt)
        # text is None when Gemini blocked the answer, which the SDK does not raise as an error
        text = response.text
        if not text or not text.strip():
            raise ValueError("Gemini returned no text")
        return text

    return generate


def choose_generate(fallback, environ=os.environ):
    """Return Gemini's generate function if GEMINI_API_KEY is set, otherwise fallback.

    The key is passed to the client explicitly: on its own the SDK would also read
    GOOGLE_API_KEY and prefer it, but GEMINI_API_KEY is meant to be the only setting.
    """
    api_key = environ.get(API_KEY_VARIABLE, "").strip()
    if not api_key:
        return fallback

    # Imported only here, so demo mode works without creating a client
    from google import genai
    from google.genai import types

    http_options = types.HttpOptions(
        timeout=TIMEOUT_MS,
        retry_options=types.HttpRetryOptions(attempts=RETRY_ATTEMPTS),
    )
    return make_gemini_generate(genai.Client(api_key=api_key, http_options=http_options))
