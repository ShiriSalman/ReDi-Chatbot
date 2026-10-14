# Task 6 — Conversational Interface (Flask + HTML/CSS/JavaScript)

**Project:** ReDI School Chatbot  
**Status:** Specification — not yet implemented  
**Suggested file:** `specs/task6_chat_interface.md`

## 1. Goal

Build a simple, accessible web chat page where visitors can ask questions about ReDI School and read answers with links to the ReDI pages used as sources. Connect the interface to the existing content ingestion, answer grounding, and citation formatting features. Do not redesign those features.

## 2. User story

As a visitor interested in ReDI School, I want to type a question in a chat interface and receive a clear answer with source links, so I can find reliable information and open the original ReDI pages.

## 3. Scope

### In scope
- A Flask application that serves the chat page and exposes a JSON chat endpoint.
- A responsive HTML/CSS/JavaScript chat interface.
- A question input, Send button, chat messages, loading state, and visible error feedback.
- Display of answer text and source links from the existing citation feature.
- Conversation history within the current browser page session (no persistent storage required).
- Automated tests for the Flask endpoint and core UI behavior where practical.

### Out of scope
- User accounts, authentication, and saved conversations.
- A database or persistent chat history.
- Rewriting BM25 retrieval, ingestion, or citation rules.
- Streaming responses, voice chat, file uploads, or multilingual chat.
- A new LLM provider integration if one has not already been configured; use an injectable generation function for tests.

## 4. Existing features and dependencies

- **Task 2:** Ingestion produces and stores ReDI text chunks with source metadata.
- **Task 3:** `grounding.answer_question(question, chunks, generate)` returns an `AnswerResult` containing `text`, `enough_information`, and `sources`. It raises `ValueError` if no ingested chunks are available.
- **Task 5:** `citations.format_answer(result)` returns answer text followed, when applicable, by a Markdown `**Sources**` section with source links. `citations.collect_citations(result.sources)` provides structured title/URL pairs.

**Integration decision:** The Flask endpoint should return **structured JSON** with the answer text and a structured citations array. The browser should render text safely and create links from validated citation metadata. `format_answer()` may be reused for a Markdown-compatible display or regression check, but do not inject its output as untrusted raw HTML. Avoid showing duplicate source sections.

## 5. Proposed structure

```text
src/
  app.py                 # Flask app and chat endpoint
  grounding.py           # existing Task 3
  citations.py           # existing Task 5
templates/
  chat.html              # chat page
static/
  css/chat.css           # styling
  js/chat.js             # browser interaction
tests/
  test_app.py            # Flask endpoint tests
  # optional: browser/UI tests if tooling is available
specs/
  task6_conversational_interface.md
```

The final paths may follow the project's existing layout and `pytest.ini` import configuration.

## 6. User experience

1. A visitor opens `/` and sees a page titled **ReDI School Chatbot**.
2. The page contains a short introduction, an initially empty chat area, a text input, and a **Send** button.
3. The visitor types a question and submits it with the button or Enter.
4. The question appears in the conversation as a user message.
5. The interface shows a loading indicator and temporarily prevents duplicate submissions.
6. The browser sends the question to the Flask chat endpoint.
7. The assistant's answer appears below the question. If supporting citations exist, they appear under the answer as clickable source titles.
8. The input is cleared and becomes usable for another question. Previous messages remain visible until the page is refreshed.
9. If an error occurs, the interface displays a friendly message and allows the visitor to try again.

## 7. Flask routes and API contract

### `GET /`

- Returns the HTML chat page.
- Does not need to contact the language model.

### `POST /api/chat`

**Request** (`Content-Type: application/json`):

```json
{"question": "Are ReDI courses free?"}
```

**Successful response** (`200 OK`):

```json
{
  "answer": "Yes, ReDI courses are free of charge.",
  "enough_information": true,
  "sources": [
    {"title": "FAQ", "url": "https://www.redi-school.org/faq"}
  ]
}
```

**No relevant source** (`200 OK`):

```json
{
  "answer": "The available ReDI sources do not provide enough information to answer this question.",
  "enough_information": false,
  "sources": []
}
```

**Invalid request** (`400 Bad Request`):

```json
{"error": "Please enter a question."}
```

**Unavailable ingested content** (`503 Service Unavailable`):

```json
{"error": "ReDI information is temporarily unavailable. Please try again later."}
```

**Unexpected server/generation failure** (`500 Internal Server Error`):

```json
{"error": "Something went wrong while answering your question. Please try again."}
```

Do not include stack traces, API keys, raw prompts, or internal file paths in JSON responses.

## 8. Backend behavior

- Load the approved, previously ingested chunks from the project's actual storage format. Verify that format before implementation; do not assume a file path or schema not present in the project.
- Use the existing `answer_question(question, chunks, generate)` for retrieval and grounded answering.
- Use `collect_citations(result.sources)` to produce unique source entries with metadata-derived URLs.
- Return only citations with valid HTTP(S) URLs as clickable links. If sources lack valid URLs, do not invent links.
- If no relevant chunks are found, return the existing `NOT_ENOUGH_INFO` message with an empty sources array, without calling the model.
- If no ingested chunks are available at all, catch the `ValueError` from Task 3 and return a service-unavailable error.
- The generation function should be supplied through configuration or dependency injection so tests can use a fake model. Do not hard-code API credentials or claim that a real model is connected before it is configured.
- Treat source content and generated text as untrusted display data.

## 9. Frontend behavior

- Use plain HTML, CSS, and JavaScript; avoid requiring a frontend framework.
- Show user and assistant messages with distinct, readable styling.
- Use `fetch()` to send a JSON request to `/api/chat`.
- Disable the Send button during a request and show a visible loading state.
- Restore the input and button after success or failure.
- Trim whitespace and reject empty questions before sending.
- Display the answer using safe text rendering (for example, `textContent`), not `innerHTML` with raw model output.
- Render source links as real `<a>` elements, with the URL set only from the validated structured API response. Do not parse arbitrary URLs from the generated answer text.
- Do not display raw chunk text as a citation.
- Keep the conversation in memory on the current page; refresh may clear it.
- Support narrow/mobile screens, keyboard use, visible focus, and readable contrast.
- Provide accessible labels for the input and send button; announce new responses and errors where practical.

## 10. Acceptance criteria

**AC1 — Chat page loads:** `GET /` returns the chat interface with a question input and Send button.

**AC2 — Send a question:** A non-empty question submitted through the page reaches `POST /api/chat` and appears in the chat history.

**AC3 — Grounded answer:** The endpoint calls the existing Task 3 answer flow and returns its answer text, information flag, and Task 5 citations.

**AC4 — Citation links:** The interface displays valid source titles as clickable links below the answer, without duplicates or invented URLs.

**AC5 — No relevant content:** The existing fallback text is displayed with no sources; the generation function is not called.

**AC6 — Empty question:** Blank or whitespace-only questions are rejected with a clear message and do not invoke the model.

**AC7 — Loading and error feedback:** The visitor sees a loading state while waiting, a useful error message on failure, and can submit another question afterward.

**AC8 — Conversation flow:** Multiple questions and answers remain visible in order during the current page session.

**AC9 — Safe rendering:** Model-generated text and source titles cannot inject executable HTML or JavaScript into the chat page.

**AC10 — Regression:** Existing ingestion, grounding, and citation tests still pass unchanged.

## 11. Suggested automated tests

Create `tests/test_app.py` using Flask's test client and an injected fake generator / controlled chunk fixture:

1. `GET /` returns status 200 and includes the chat page.
2. `POST /api/chat` with a supported question returns the expected answer and source metadata.
3. Duplicate chunks from one page produce only one citation.
4. An unrelated question returns `NOT_ENOUGH_INFO`, `enough_information: false`, and `sources: []`; the fake generator records no calls.
5. Empty or whitespace-only questions return 400.
6. Missing JSON, malformed JSON, or a non-string `question` returns 400.
7. Missing ingested chunks return a user-friendly 503 response.
8. A generator exception returns a user-friendly 500 response without exposing internal details.
9. Invalid source URLs are not returned as clickable citation URLs.
10. Run the full existing test suite to check for regressions.

For browser interaction, manually verify Enter submission, loading indicator, repeated messages, mobile layout, keyboard navigation, and safe handling of text containing HTML-like characters. Add automated browser tests later if the course tooling supports them.

## 12. Definition of done

- [ ] Flask app serves the chat page and JSON endpoint.
- [ ] The chat page supports sending questions and displaying answers.
- [ ] Backend uses the existing grounding and citation functions.
- [ ] Sources appear as safe, clickable links when available.
- [ ] Missing information, invalid input, and server errors have appropriate behavior.
- [ ] Frontend is responsive and keyboard accessible.
- [ ] New Task 6 tests pass.
- [ ] Existing tests pass without regressions.
- [ ] Setup/run instructions document required configuration and how to start Flask locally.

## 13. Implementation order

1. Confirm the actual saved-chunks format and how the model `generate` function will be provided.
2. Write failing Flask endpoint tests from the acceptance criteria.
3. Implement the minimal Flask app and JSON endpoint.
4. Add the HTML template, CSS, and JavaScript chat interaction.
5. Test manually in the browser and run the complete pytest suite.

**Reminder:** This is a behavior specification, not evidence that the interface or live LLM integration already exists.
