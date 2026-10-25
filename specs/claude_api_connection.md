# Connect the Claude Messages API

**Project:** ReDI School Chatbot  
**Status:** Parked

> **Parked on 2026-10-25.** The chatbot uses Google Gemini instead, because it
> is free for testing (`specs/gemini_error_handling.md`, `src/llm.py`). This
> spec is kept in case Claude API access comes from ReDI. It was written
> before the Gemini connection, so "Current behaviour" below describes the
> old demo-only state.
>
> If it is picked up again:
> - Add a `make_claude_generate(client)` next to `make_gemini_generate` in
>   `src/llm.py`, and decide in `choose_generate()` which key wins.
> - Re-read the Claude docs first. The model IDs, parameters and SDK details
>   below were checked on 2026-10-20 and may have changed.

## Goal

Replace demo mode with real answers from Claude through the Messages API
(`POST /v1/messages`). Keep the change small: only the `generate(prompt)`
function changes. Retrieval, the prompt, citations, the JSON API and the chat
page stay as they are.

Sources, read on 2026-10-20:
- `platform.claude.com/docs/en/api/messages/create`
- `/api/overview`
- `/api/errors`
- `/cli-sdks-libraries/sdks/python`

## Current behaviour (inspected)

- `src/app.py` builds the app with `create_app(load_chunks(), demo_generate)`.
  `demo_generate` returns a fixed `DEMO_ANSWER`.
- `src/grounding.py` `answer_question()` calls `generate(build_prompt(...))`
  only when retrieval finds chunks. Otherwise it returns `NOT_ENOUGH_INFO`
  without calling the model.
- `src/app.py` catches every exception from `answer_question()`, logs it and
  returns 500 `SERVER_ERROR`. No details reach the visitor.

---

## Request

Sent through the official Python SDK (`pip install anthropic`). The SDK adds
the required headers (`x-api-key`, `anthropic-version: 2023-06-01`,
`content-type: application/json`) and reads the key from the
`ANTHROPIC_API_KEY` environment variable.

```python
client.messages.create(
    model=MODEL,
    max_tokens=MAX_TOKENS,
    messages=[{"role": "user", "content": prompt}],
)
```

- `prompt` is the unchanged output of `build_prompt()`, with the rules,
  sources and question in one user message.
- No other parameters are sent. Specifically:
  - `temperature`, `top_p` and `top_k` are not sent. The docs mark them
    deprecated: newer models reject values other than the defaults with a
    400 error.
  - `thinking` is not sent (the model's default applies).
  - `system` is not sent (see Out of scope).

## Response

A `Message` object. Only these fields are used:

| Field | Use |
|---|---|
| `content` | array of blocks; the `text` of every block with `type == "text"` is joined into the answer. Other block types (for example `thinking`) are ignored. |
| `stop_reason` | `"refusal"` raises an error. `"max_tokens"` keeps the text and logs a warning. Other values: the text is used. |
| `usage.input_tokens`, `usage.output_tokens` | logged (`info`), to watch costs |
| `_request_id` (SDK property) | logged, for support requests |

## Errors

| Case | Where it happens | Behaviour |
|---|---|---|
| 400 `invalid_request_error` (also when a spend limit is reached) | SDK raises `BadRequestError` | 500 `SERVER_ERROR`, details logged |
| 401 `authentication_error` (wrong or expired key) | `AuthenticationError` | same |
| 403 `permission_error` | `PermissionDeniedError` | same |
| 404 `not_found_error` (for example a wrong model name) | `NotFoundError` | same |
| 429 `rate_limit_error` | `RateLimitError`, retried by the SDK first | same |
| 500 / 504 / 529 | `InternalServerError`, retried by the SDK first | same |
| No connection, or client timeout | `APIConnectionError` / `APITimeoutError`, retried first | same |
| Response has no text, or the text is blank | `generate()` raises `ValueError` | same |
| `stop_reason == "refusal"` | `generate()` raises `ValueError` | same |
| `stop_reason == "max_tokens"` | `generate()` | answer is returned cut off; warning logged |
| `ANTHROPIC_API_KEY` not set | app start | demo mode (`demo_generate`), as today |

- All SDK errors are subclasses of `anthropic.APIError`. No new `except`
  branch is needed in `app.py`, because the existing `except Exception`
  already returns 500 and logs.
- The SDK retries connection errors, 408, 409, 429 and 5xx twice by default
  (`max_retries=2`). No own retry loop.
- The SDK's default timeout is 10 minutes. The client gets
  `timeout=TIMEOUT_SECONDS` so a visitor isn't left waiting.

---

## Changes

### New `src/llm.py`

- Constants: `MODEL`, `MAX_TOKENS = 1024`, `TIMEOUT_SECONDS = 30`.
- `make_claude_generate(client, model=MODEL, max_tokens=MAX_TOKENS)` returns
  a `generate(prompt)` function that does the request and response handling
  above.
- The client is passed in (dependency injection, like `generate` itself), so
  tests use a fake client and never call the network.

### `src/app.py`

- At the end of the file: if `ANTHROPIC_API_KEY` is set, create
  `anthropic.Anthropic(timeout=TIMEOUT_SECONDS)` and pass
  `make_claude_generate(client)`; otherwise pass `demo_generate`.
- `import anthropic` happens only in that branch, so demo mode and the tests
  work without the key.
- Update the module docstring (it says no model is connected).

### `requirements.txt`

- Add `anthropic` with a pinned version (the version that installs in the
  venv).

### Not changed

- `grounding.py` (prompt and retrieval)
- `citations.py`
- `templates/`, `static/`
- the JSON API (ADR 0002)

---

## Acceptance criteria

Checked by unit tests (fake client, no network):

- **AC1:** `generate(prompt)` calls `messages.create` once, with `model`,
  `max_tokens` and `messages=[{"role": "user", "content": prompt}]`, and no
  other arguments.
- **AC2:** The text of all `text` blocks is returned. `thinking` blocks are
  ignored.
- **AC3:** A response without text, or with only blank text, raises
  `ValueError`.
- **AC4:** `stop_reason == "refusal"` raises `ValueError`.
- **AC5:** `stop_reason == "max_tokens"` returns the text.
- **AC6:** An exception from the client reaches `/api/chat` as 500
  `SERVER_ERROR`. (Already covered by the existing generator-exception test
  in `tests/test_app.py`.)
- **AC7:** Without `ANTHROPIC_API_KEY`, the app uses `demo_generate`.
- **AC8:** All existing tests pass unchanged.

Checked manually with a real key:

- **AC9:** Three ReDI questions get real answers with sources. The Tokyo
  question gets the fallback, and the model is not called.
- **AC10:** A wrong key shows the friendly 500 message on the page, and the
  server log shows `AuthenticationError`.

## Tests (`tests/test_llm.py`)

- `test_sends_the_prompt_as_one_user_message` (AC1)
- `test_joins_text_blocks_and_ignores_thinking_blocks` (AC2)
- `test_raises_when_there_is_no_text` (AC3, parametrized: no blocks, blank text)
- `test_raises_on_refusal` (AC4)
- `test_returns_the_text_when_cut_off_by_max_tokens` (AC5)
- `test_app_uses_demo_mode_without_an_api_key` (AC7, monkeypatched env var,
  re-import of `app`)

The fake client is a `SimpleNamespace` with `messages.create` that records
its arguments and returns an object with `content`, `stop_reason`, `usage`
and `_request_id`.

---

## Security

- The key lives only in the environment variable (shell locally; Vercel
  project settings when deployed). It is never put in code, commits, logs or
  chat.
- Logs contain the request ID and token counts, never the key.

## Assumptions

- The owner chooses `MODEL`. Haiku 5.5 (`claude-haiku-5-5`) is suggested
  because answers are short and grounded in given sources, which keeps
  costs low.
- `max_tokens` cut-offs are rare at 1024 tokens; showing the cut-off text is
  better than an error. The owner can change this.

## To verify before implementing

- Model ID and price on the models overview and pricing pages.
- That the `anthropic` package installs under Python 3.14 (docs:
  "Python 3.10 or later").
- The SDK exception for 402 `billing_error` and 413 `request_too_large`. It
  isn't in the SDK table, but it is still an `APIError` and still ends as a
  500.
- The Vercel function time limit, which may require a lower
  `TIMEOUT_SECONDS`.

## Out of scope

- Sending `INSTRUCTIONS` as `system`: a documented parameter, but it changes
  `build_prompt` and the Task 3/7 tests. A separate decision.
- Streaming, conversation memory, prompt caching, and tools.
- Task 3's known limitation (`enough_information` stays `True` when the
  model says the sources don't cover the question). Checked in Task 8.
- Task 8 itself (testing with real questions).
