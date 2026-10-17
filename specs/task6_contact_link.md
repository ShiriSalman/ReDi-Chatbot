# Task 6 iteration – Contact Link for Unanswered Questions

## Goal

When retrieval finds no relevant ReDI content for a question, the visitor
should not hit a dead end. The chatbot keeps saying that it cannot answer
from the available sources, and also offers a link to ReDI's contact page so
the visitor can ask ReDI directly.

This is the MVP rule from `CLAUDE.md` ("say so and link to ReDI's contact
page") and a next step named in `docs/adr/0002-chat-interface-json-api.md`.

This iteration covers only the case where **retrieval** finds nothing
(`enough_information` is `False`). Questions where retrieval finds content
but the model says the sources don't cover them are a known limitation (see
Out of scope).

---

## Current behaviour (inspected)

- `src/grounding.py`: `answer_question()` returns
  `AnswerResult(text=NOT_ENOUGH_INFO, enough_information=False, sources=[])`
  and does not call the model.
- `src/app.py`: `POST /api/chat` returns `{"answer", "enough_information",
  "sources"}`. For the fallback: `NOT_ENOUGH_INFO`, `false`, `[]`.
- `static/js/chat.js`: `addMessage()` shows the answer with `textContent`.
  `addSources()` adds links only for `http`/`https` URLs and only when at least
  one is valid.
- `data/sources.json`: `https://www.redi-school.org/contact`, title "Contact",
  `include: "Yes"`, note: "Also the link for 'I don't know' answers."

---

## User flow

1. A visitor asks a question for which retrieval finds no relevant ReDI
   content (for example "What will the weather be like in Tokyo tomorrow?").
2. The assistant message shows the existing fallback text (`NOT_ENOUGH_INFO`):
   "I can only answer questions about ReDI School, and the available ReDI
   sources do not provide enough information to answer this one."
3. Below it, a short line offers the contact page: "You can ask ReDI
   directly:" followed by a link **ReDI contact page** that opens
   https://www.redi-school.org/contact in a new tab.
4. No **Sources** section is shown, because nothing supports the answer.
5. Answered questions look exactly as before, with no contact link.

---

## Backend / API changes (`src/app.py`)

This iteration extends the "No relevant source" response defined in
`specs/task6_chat_interface.md`, section 7, with a `contact` field. All other
responses stay exactly as defined there.

- Add a constant `CONTACT_URL = "https://www.redi-school.org/contact"` and a
  label `CONTACT_TITLE = "ReDI contact page"`.
- When `result.enough_information` is `False`, the response gets one extra
  field:

  ```json
  {
    "answer": "I can only answer questions about ReDI School, and the available ReDI sources do not provide enough information to answer this one.",
    "enough_information": false,
    "sources": [],
    "contact": {"title": "ReDI contact page", "url": "https://www.redi-school.org/contact"}
  }
  ```

- When `enough_information` is `True`, the response is unchanged and has no
  `contact` field.
- The contact link is never added to `sources`. Sources mean "pages that
  support this answer", and Task 5 says a fallback has no sources.
- 400, 503 and 500 error responses are unchanged.

---

## Frontend changes (`static/js/chat.js`, `static/css/chat.css`)

- The server decides when the link appears: the page shows the contact line
  whenever the response contains `contact` and `isSafeUrl(data.contact.url)`
  is true. `chat.js` does not check `enough_information` itself.
- The contact line goes into the same assistant message, in this order:
  answer, then Sources (if any), then the contact line.
- The line is the text "You can ask ReDI directly: " and an `<a>` with
  `href = data.contact.url`, `target="_blank"` and
  `rel="noopener noreferrer"`. Its text is `data.contact.title`, or
  "ReDI contact page" if the title is missing or empty.
- Built with `createElement` and `textContent` only, as in the rest of
  `chat.js`.
- A small CSS class (for example `.contact`) styled like the source links
  (ReDI dark teal, underline).

---

## Data changes

None. The URL is a constant in `app.py`, not read from a file at runtime. A
test checks that it is an approved source in `data/sources.json`
(`include: "Yes"`), the same way `tests/test_sources.py` already checks that
file.

---

## Error cases

| Case | Behaviour |
|---|---|
| Retrieval finds no relevant content | `NOT_ENOUGH_INFO` + `contact` link, no sources, model not called |
| Retrieval finds content, but the model says the sources don't cover the question | no contact link (known limitation, see Out of scope) |
| Blank / invalid request (400) | unchanged, no contact link |
| No ingested content (503) | unchanged, no contact link |
| Model error (500) | unchanged, no contact link |
| `contact.url` invalid or missing in the response | the browser shows the answer without a link (no guessed URL) |
| `contact.title` missing or empty in the response | the link text is "ReDI contact page" |
| Contact page removed from `data/sources.json` later | the source-check test fails, so the link is updated on purpose |

---

## Acceptance criteria

- **AC1:** A question for which retrieval finds no relevant content returns
  `NOT_ENOUGH_INFO`, `enough_information: false`, `sources: []` and `contact`
  with the ReDI contact page URL.
- **AC2:** The model is still not called for such a question.
- **AC3:** A covered question returns no `contact` field and is otherwise
  unchanged.
- **AC4:** The contact link is never listed under sources.
- **AC5:** The contact URL is an approved source in `data/sources.json`
  (`include: "Yes"`).
- **AC6:** The page shows the contact link under the fallback answer, opening
  in a new tab, with "ReDI contact page" as the text if the title is missing.
  *Checked manually* (see Manual browser check). The existing `innerHTML`
  guard test covers only the safety part.
- **AC7:** 400, 503 and 500 responses are unchanged.
- **AC8:** All existing tests pass. The only existing test that changes is the
  fallback test in `tests/test_app.py`, which now expects the `contact` field.

---

## Tests (`tests/test_app.py`)

**New**

- `test_answered_question_has_no_contact_link`: AC3
- `test_contact_url_is_an_approved_source`: reads `data/sources.json`, AC5
- `test_error_responses_have_no_contact_link` (parametrized: 400, 503, 500): AC7

**Changed**

- `TestNoRelevantContent.test_unrelated_question_returns_the_fallback_without_sources`:
  the expected dict gains `"contact": {...}`. Because it compares the whole
  response, it covers AC1 and AC4 (the contact link is a separate field and
  `sources` stays `[]`).

**Unchanged and still guarding**

- `TestNoRelevantContent.test_the_model_is_not_called` (AC2: the request is
  the same, so no separate test is needed)
- `test_chat_script_does_not_use_inner_html` (AC6 safety)
- `tests/test_grounding.py` and `tests/test_citations.py` (the
  `NOT_ENOUGH_INFO` text and `format_answer()` don't change)

**Manual browser check (AC6):** ask the Tokyo question. The fallback text
appears, then the "ReDI contact page" link, which opens a new tab. `Tab`
reaches the link with a visible outline. An answered question ("How do I
apply?") shows no contact line.

---

## Assumptions

- The contact page link fits all visitors (the MVP has one audience, per
  `CLAUDE.md`).
- The `NOT_ENOUGH_INFO` text stays exactly as it is, so Tasks 3 and 5 and
  their tests don't change.
- The link is added in the web layer (`app.py` and `chat.js`), not in
  `grounding.py` or `citations.py`. That keeps "what the sources say"
  separate from "where to ask instead".
- `contact` is only present on fallback answers, not `null` on every answer.
- The wording "You can ask ReDI directly:" is a first draft for the owner to
  change.

---

## Out of scope

- Showing the contact link on 400/503/500 errors.
- Adding the link to Task 5's Markdown output (`format_answer()`).
- **Known limitation:** questions where retrieval finds content but the model
  says the sources don't (fully) cover them. `enough_information` is `True`
  there, so no link is shown. This becomes visible once a real model is
  connected and should be checked in Task 8.
- Different contact pages per city or programme.
- A real LLM, other languages, audience differentiation.
