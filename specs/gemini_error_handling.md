# Gemini Connection and Error Handling

**Project:** ReDI School Chatbot  
**Status:** Specification

## Goal

Replace demo mode with real answers from Google Gemini, which is free for
testing. When a Gemini call fails, the visitor gets an understandable message
instead of a technical traceback. An invalid API key and an invalid model
name are tested.

Sources, read on 2026-10-23:

- `ai.google.dev/gemini-api/docs/api-errors`
- `/troubleshooting`
- `/api-key`
- the installed SDK `google-genai` 2.32.0 (`google/genai/errors.py`,
  `types.py`, `_api_client.py`)

## Current behaviour (inspected)

- `src/app.py` builds the app with `create_app(load_chunks(), demo_generate)`.
  No model is connected.
- `src/grounding.py` `answer_question()` calls `generate(prompt)` only when
  retrieval finds chunks. Otherwise it returns `NOT_ENOUGH_INFO` and does
  not call the model.
- `src/app.py:86-91` already catches every exception from
  `answer_question()`. It logs the exception with `app.logger.exception` and
  returns 500 `SERVER_ERROR` ("Something went wrong while answering your
  question. Please try again."). No details reach the visitor
  (ADR 0002).

So the error handling for the visitor already exists. This spec adds the
Gemini call and makes sure every Gemini failure ends in that existing path.

---

## Request

`client.models.generate_content(model=MODEL, contents=prompt)`

- `prompt` is the unchanged output of `build_prompt()`.
- No other parameters are sent. `temperature`, `top_p` and `top_k` are left
  out: the troubleshooting page says newer models ignore them and will
  return 400 in a future release.
- The key comes only from the environment variable `GEMINI_API_KEY` and is
  passed to `genai.Client(api_key=...)` explicitly. On its own, the SDK
  would also read `GOOGLE_API_KEY` and prefer it over `GEMINI_API_KEY`, so
  passing the key explicitly keeps `GEMINI_API_KEY` the only setting. The
  key is never written in code.

## Response

- `response.text` is the answer. The SDK joins the text parts of the first
  candidate.
- `response.text` is `Optional[str]`. It is `None` when there is no text,
  for example when generation was blocked (safety, recitation and similar
  codes). Blocked generation is **not** raised as an exception, so
  `generate()` must check for it.

## Errors

Every case ends as 500 `SERVER_ERROR` for the visitor, with the details in
the server log only. No new `except` in `app.py` is needed.

| Case | Gemini code (HTTP) | Raised as | Visitor sees |
|---|---|---|---|
| Invalid, missing or expired API key | `authentication` (401) | `errors.ClientError` | 500 `SERVER_ERROR` |
| Invalid model name | `model_not_found` (404) | `errors.ClientError` | same |
| Invalid request or unknown parameter | `invalid_request`, `parameter_unknown` (400) | `errors.ClientError` | same |
| Permission or billing | `permission_denied` (403), `payment_required` (402) | `errors.ClientError` | same |
| Rate limit or daily quota (free tier) | `rate_limit_exceeded`, `quota_exceeded` (429) | `errors.ClientError` | same |
| Gemini server error or overload | `api_error` (500), `service_unavailable` (503), `deadline_exceeded` (504) | `errors.ServerError` | same |
| No network | – | an `httpx` exception | same |
| Blocked or empty answer (`response.text` is `None` or blank) | – | `generate()` raises `ValueError` | same |
| No `GEMINI_API_KEY` set (or blank) at app start | – | no client is created (`genai.Client()` would raise `ValueError`) | **demo mode**, as today; the app still starts |

- `ClientError` (4xx) and `ServerError` (5xx) are subclasses of
  `errors.APIError`. They have `code` (HTTP status), `status` and `message`.
- The log contains the exception (`app.logger.exception`). It never
  contains the API key. The SDK does not put the key in error messages, and
  the code never logs it.

---

## Changes

### New `src/llm.py`

- Constant `MODEL = "gemini-3.8-flash"`, the model in
  `test_gemini_connection.py`. The models page lists it as stable
  (checked on 2026-10-24). The owner can change it.
- `make_gemini_generate(client, model=MODEL)` returns a `generate(prompt)`
  that sends the request above and returns `response.text`. If the text is
  `None` or blank, it raises `ValueError("Gemini returned no text")`.
- The client is passed in (dependency injection, like `generate` itself), so
  tests use a fake client and never call the network.

- `choose_generate(fallback, environ=os.environ)`: if `GEMINI_API_KEY` is
  set and not blank, create `genai.Client(api_key=...)` and return
  `make_gemini_generate(client)`. Otherwise return `fallback`.
- `from google import genai` happens only in that branch, so demo mode and
  the tests work without the SDK call or a key.

### `src/app.py`

- At the end of the file: `create_app(load_chunks(), choose_generate(demo_generate))`.
- Update the module docstring, which says no model is connected.

### `requirements.txt`

- Add `google-genai==2.32.0` (the version installed in the venv).

### Not changed

- `grounding.py`, `citations.py`, `templates/`, `static/`
- the JSON API and the 400, 503 and 500 messages (ADR 0002)

---

## Acceptance criteria

Checked by unit tests (fake client, no network, no key):

- **AC1:** `generate(prompt)` calls `generate_content` once, with
  `model=MODEL` and `contents=prompt`, and with no other arguments.
- **AC2:** The text from `response.text` is returned unchanged.
- **AC3:** `response.text` that is `None`, `""` or only spaces raises
  `ValueError`.
- **AC4:** An invalid API key (fake `ClientError(401)`) reaches
  `POST /api/chat` as 500 with `SERVER_ERROR`. The response contains neither
  the error message nor the word "key".
- **AC5:** An invalid model name (fake `ClientError(404)`) gives the same
  500 response.
- **AC6:** A Gemini server error (fake `ServerError(503)`) gives the same 500
  response.
- **AC7:** Without `GEMINI_API_KEY`, or with a blank one, the app uses demo
  mode, also when `GOOGLE_API_KEY` is set. With `GEMINI_API_KEY` set, the
  Gemini client gets that key.
- **AC8:** All existing tests pass unchanged.

Checked by hand:

- **AC9:** With a real key, three ReDI questions get real answers with
  sources. The Tokyo question gets the fallback without a Gemini call.
- **AC10:** With a wrong key, and then with a wrong model name, the page
  shows the friendly message. The server log shows `ClientError` with 401,
  and then with 404.

## Tests (`tests/test_llm.py`)

- `test_sends_the_prompt_to_the_model` (AC1)
- `test_returns_the_text_from_gemini` (AC2)
- `test_raises_when_gemini_returns_no_text` (AC3, parametrized: `None`, `""`, `"   "`)
- `test_invalid_api_key_gives_a_friendly_error` (AC4)
- `test_invalid_model_name_gives_a_friendly_error` (AC5)
- `test_gemini_server_error_gives_a_friendly_error` (AC6)
- `test_uses_demo_mode_without_an_api_key` (AC7, parametrized: no key, a
  blank key, only `GOOGLE_API_KEY`)
- `test_uses_gemini_with_the_key_from_gemini_api_key` (AC7, with a
  monkeypatched `genai.Client`)

The fake client is a `SimpleNamespace` whose `models.generate_content`
records its arguments and either returns an object with `text` or raises.
The errors are real SDK classes built without network, for example
`errors.ClientError(401, {"error": {"code": 401, "message": "API key not valid", "status": "UNAUTHENTICATED"}})`.

---

## Security

- The key lives only in an environment variable: the shell locally, and the
  Vercel project settings when deployed. It never goes into code, commits,
  logs or chat (Gemini docs: "Treat your Gemini API key like a password").
- `test_gemini_connection.py` stays out of the test suite. `pytest.ini`
  collects only `tests/`, so a normal test run never calls Gemini.

## Iteration: timeout and retry

**Evidence:** on 2026-10-25, with a real key, every answer in the chat page
failed for a while with the friendly 500, for two reasons:
- **19:52:** `httpx.ConnectError: getaddrinfo failed`. The network was
  briefly unavailable.
- **19:57:** `ServerError: 503 UNAVAILABLE` ("This model is currently
  experiencing high demand. Spikes in demand are usually temporary.").

An answer to "thanks" also took 56 seconds. The SDK does **not** retry by
default (no `retry_options` means one attempt), and it sets no timeout of its
own.

**Change (`src/llm.py`):**
- `choose_generate()` creates the client as
  `genai.Client(api_key=..., http_options=types.HttpOptions(timeout=TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=RETRY_ATTEMPTS)))`.
- `TIMEOUT_MS = 60_000` applies to each attempt and is in milliseconds. It is
  above the 56 seconds measured for a long answer.
- `RETRY_ATTEMPTS = 3` counts the first try.
- With `retry_options` set, the SDK retries on its own. It retries HTTP 408,
  429, 500, 502, 503 and 504, and also `httpx.TimeoutException` and
  `httpx.ConnectError` (checked in `google/genai/_api_client.py`). It waits
  with exponential backoff between attempts, starting at 1 second.
- 400, 401, 403 and 404 are not retried, because another attempt cannot fix a
  wrong key or model.
- When all attempts fail, the error reaches `app.py` as before, and the
  visitor sees 500 `SERVER_ERROR`.

**Acceptance criteria:**
- **AC11:** The Gemini client is created with `timeout=TIMEOUT_MS` and
  `retry_options.attempts=RETRY_ATTEMPTS`. Checked by a unit test with a
  monkeypatched `genai.Client`.
- **AC12:** The SDK's own retry rules are not tested again; that would test
  the SDK, not our code. Checked by hand: during a short 503 spike, a
  question still gets an answer.

**Known limitation:** the worst case is about 3 × 60 seconds plus the waits
between attempts. If the Vercel function time limit is shorter, it ends the
request first. Check this in Task 9.

**Tests (`tests/test_llm.py`):**
- `test_client_gets_a_timeout_and_retries` (AC11)
- `test_uses_gemini_with_the_key_from_gemini_api_key` now checks only the
  `api_key` argument, because the client also receives `http_options`.

## Later (not in this spec)

- **Response validation beyond empty text**, for example checking the finish
  reason or handling a cut-off answer.
- **A separate message for 429** ("The chatbot is busy, please try again in
  a minute"). This would be a new visitor message, so it is the owner's
  decision.

## To verify before implementing

- The model ID on the Gemini models page. It must be a model available on
  the free tier.
- The free-tier rate limits, which decide how often 429 can occur during
  Task 8.

## Out of scope

- Claude API (`specs/claude_api_connection.md` is parked).
- Streaming, conversation memory, system instructions and safety settings.
- Task 3's known limitation (`enough_information` stays `True` when the
  model says the sources don't cover the question). It is checked in
  Task 8.
