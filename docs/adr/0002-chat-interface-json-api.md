# ADR 0002: Build the chat interface as a JSON API with a JavaScript page

**Status:** Accepted
**Date:** 2026-10-15

## Context

Task 6 adds the web page where visitors ask questions about ReDI School and
read answers with links to the ReDI pages they come from
(`specs/task6_chat_interface.md`).

The answer logic already exists and must not be redesigned:

- `answer_question(question, chunks, generate)` in `src/grounding.py`
  (Task 3) returns an `AnswerResult` with `text`, `enough_information` and
  `sources`.
- `collect_citations(sources)` in `src/citations.py` (Task 5) turns the
  sources into unique `{"title", "url"}` entries with validated URLs.

The spec asks for a chat-like experience: a loading state while waiting
(AC7), the conversation staying visible in order (AC8), and answers and
titles that cannot inject HTML or JavaScript (AC9). The stack is Flask with
plain HTML, CSS and JavaScript, and no frontend framework.

## Options considered

1. **JSON API + JavaScript.** Flask serves one HTML page. JavaScript sends
   each question with `fetch()` to `POST /api/chat` and adds the answer and
   source links to the page without reloading.
2. **Server-rendered form.** A plain HTML form posts the question to Flask,
   which renders the answer into the template with Jinja. The whole page
   reloads for every question.

| | 1: JSON API + JS | 2: Server-rendered form |
|---|---|---|
| Chat feel | smooth, no reload | page reloads on every question |
| Amount of code | more (Python and JavaScript) | less (mostly Python) |
| Safe rendering | our own rule (`textContent`) | automatic (Jinja escaping) |
| Automated tests | API fully; browser behaviour by hand | almost everything in Python |
| Chat history (AC8) | stays on the page | needs a session or hidden fields |
| Reuse elsewhere | the API is ready | a separate API would be needed |

## Decision

We chose option 1.

`src/app.py` provides `create_app(chunks, generate)` with two routes:

- `GET /` serves `templates/chat.html`.
- `POST /api/chat` takes `{"question": "..."}` and returns
  `{"answer", "enough_information", "sources"}`, using `answer_question()`
  and `collect_citations()` unchanged. Invalid input returns 400, missing
  content 503, and any other failure a friendly 500 without internal
  details.

`static/js/chat.js` shows all text with `textContent` and creates source
links as `<a>` elements only for `http`/`https` URLs.

Option 2 would have needed extra work for exactly the parts the spec stresses
most: the loading state and the visible conversation history.

## Consequences

**Positive**

- The page feels like a chat: no reloads, a loading indicator, and the
  history stays visible.
- The API returns structured data, so it is tested directly with Flask's test
  client (28 tests in `tests/test_app.py`) without a browser.
- The same API can later serve a real language model, a contact-page link,
  or another platform without changing the page.

**Negative / trade-offs**

- Safe rendering is our own responsibility instead of the template's. The
  rule "never parse server text as HTML" must hold in `chat.js`;
  `test_chat_script_does_not_use_inner_html` guards it.
- URLs are validated twice, on the server (`collect_citations`) and again in
  the browser, so a change on one side cannot create `javascript:` links.
- Browser behaviour (Enter to send, loading indicator, history order, mobile
  layout, keyboard use) has no automated tests yet and is checked by hand
  with the list in the spec, section 11.
- The page does not work without JavaScript.

**Verification**

- `tests/test_app.py`: 28 passed. Full suite: 119 passed.
- A real server run with `data/chunks.json` returned the page, the static
  files, a grounded answer with source links, the fallback message for an
  unrelated question, and a 400 for a blank question.
- Manual browser checks: see the list in the spec, section 11.
