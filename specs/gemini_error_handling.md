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
  Render dashboard when deployed. It never goes into code, commits,
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

**Model change:** with retries, answers still took long because
`gemini-3.8-flash` is slow (the docs call it the "most intelligent Flash
model") and was overloaded. `MODEL` is now `gemini-3.5-flash-lite`, which the
models page lists as stable and as "our fastest, most cost-effective" model.
Whether it still follows the prompt rules (only the sources, plain text) is
checked by hand in the chat page.

**Known limitation:** the worst case is about 3 × 60 seconds plus the waits
between attempts (shortened to 2 × 45 seconds in "Iteration: shorter retries
and feedback during long waits" below). On Render, gunicorn's `--graceful-timeout` is set above it
(`specs/task9_deploy_render.md`).

**Tests (`tests/test_llm.py`):**
- `test_client_gets_a_timeout_and_retries` (AC11)
- `test_uses_gemini_with_the_key_from_gemini_api_key` now checks only the
  `api_key` argument, because the client also receives `http_options`.

## Iteration: a message for the used-up quota (429)

**Evidence:** in a Task 8 run on 2026-11-19, three questions got
`ClientError: 429 RESOURCE_EXHAUSTED` ("Generate content requests per minute
limit exceeded on Free Tier", limit 15 for `gemini-3.5-flash-lite`, "Please
retry in 35 s"). The SDK's 3 attempts all fell within the same minute, and
the visitor saw `SERVER_ERROR` ("Something went wrong … Please try again"),
which suggests trying again right away. The live app on Render has the same
limit, shared by all visitors.

**Decision (owner, 2026-11-20):** a separate message for 429, then a limit
per visitor (`specs/rate_limit_per_visitor.md`).

**Change (`src/app.py` only):**
- When answering fails with an error whose `code` is `429`, the app answers
  with **status 429** and `error`: *"The chatbot is getting a lot of
  questions right now. Please wait a minute and try again."*
  (`MODEL_BUSY`). The error is still logged.
- The app checks the attribute (`getattr(error, "code", None) == 429`), so it
  doesn't import Google's SDK; demo mode and the tests work without it.
  `google.genai.errors.ClientError` has `code` as an `int` (checked with the
  installed SDK, 2.32.0).
- Every other error keeps the 500 `SERVER_ERROR`.
- The page needs no change: it shows `error` in the red card and puts the
  question back in the box for any non-OK status.

**Acceptance criteria (`tests/test_app.py`, `TestModelBusy`):**
- **AC13:** an error with `code = 429` gives status 429 and `MODEL_BUSY`,
  without internal details.
- **AC14:** an error with another `code` (for example 503), or none, still
  gives 500 `SERVER_ERROR`.
- **AC15:** the 429 is logged like other errors.

## Iteration: shorter retries and feedback during long waits

**Problem (MVP review, 2026-11-23):** when Gemini is overloaded, the client
tries 3 times with up to 60 seconds each, plus pauses of about 1 and 2
seconds (`google/genai/_api_client.py`: backoff starting at 1 s, factor 2,
up to 1 s jitter). A visitor can wait about 3 minutes and sees only the typing
animation; the page has no timeout. gunicorn has 4 threads, so four such waits
block every other visitor.

**Decision (owner, 2026-11-23):** shorter retries on the server and feedback
on the page, both.

**Change on the server (`src/llm.py`):**
- `TIMEOUT_MS = 45_000` (was 60,000) and `RETRY_ATTEMPTS = 2` (was 3).
- Worst case: 2 × 45 s plus one pause of at most about 2 s, so about 92 s
  instead of about 185 s.
- Risk: an answer that needs more than 45 seconds is cut off and retried once.
  The 56 seconds in the earlier iteration were measured with the slower
  `gemini-3.8-flash`; `gemini-3.5-flash-lite`'s usual time isn't measured.
- gunicorn's `--graceful-timeout 200` stays; it is now well above the worst
  case (the deploy test compares it with `RETRY_ATTEMPTS × TIMEOUT_MS`).

**Change on the page (`static/js/chat.js`):**
- After `STILL_WORKING_MS` (15 seconds) without an answer, the typing card
  shows *"Still working on it. The chatbot is busy right now, so this can
  take up to a minute."* The hidden status text ("Looking for an answer…")
  changes to the same words, so screen readers announce it.
- After `GIVE_UP_MS` (100 seconds) the page stops waiting (`AbortController`)
  and shows the error card *"This is taking too long. Please try again in a
  moment."* The question goes back into the box, as after other errors.
- `GIVE_UP_MS` is later than the server's worst case, so the page never gives
  up on an answer the server could still deliver.

**Acceptance criteria:**
- **AC16 (`tests/test_llm.py`):** `TIMEOUT_MS` is 45,000 and
  `RETRY_ATTEMPTS` is 2.
- **AC17 (`tests/test_app.py`):** `GIVE_UP_MS` in `chat.js` is at least the
  server's worst case plus 5 seconds (`RETRY_ATTEMPTS × TIMEOUT_MS + 5000`),
  and `STILL_WORKING_MS` is 15,000.
- **AC18 (`tests/test_app.py`):** `chat.js` contains both messages and uses
  an `AbortController`.
- **AC19 (by hand, browser):** with a delayed answer, the note appears after
  15 seconds; after 100 seconds the error card appears, the question is back
  in the box and the box can be used again. A normal answer still appears
  without the note.

## Later (not in this spec)

- **Response validation beyond empty text**, for example checking the finish
  reason or handling a cut-off answer.

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
