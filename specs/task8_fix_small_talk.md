# Task 8 fix – Friendly replies to small talk

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

Measured with `retrieve()` on the real `data/chunks.json` (2026-11-02), and
seen in the live app on Render:

| Group | Messages | What happens | Problem |
|---|---|---|---|
| A: reaches the model | "thanks", "thank you", "Thanks!", "great", "cool", "you are great" | ReDI pages contain these words ("a huge thank you to our supporters"), so sources are retrieved and Gemini is called | An odd answer ("The sources do not contain a question to answer …"), unrelated sources, and quota used |
| B: gets the fallback | "hi", "hello", "hallo", "hey", "good morning", "bye", "goodbye", "danke" | no chunk matches | "I can only answer questions about ReDI School …" sounds unfriendly as a reply to "hi" |

## Decision

A list of small-talk messages in code, decided by the owner on 2026-11-03.
The alternatives were:
- stopwords, which would leave group B with the unfriendly fallback
- a prompt rule, which doesn't reach group B, keeps the sources and uses
  quota

## Change

### `src/grounding.py`

- **Three fixed replies:**
  - `GREETING_REPLY`: "Hello! I answer questions about ReDI School, for
    example how to apply or which courses there are."
  - `THANKS_REPLY`: "You're welcome! Feel free to ask another question about
    ReDI School."
  - `GOODBYE_REPLY`: "Goodbye! Come back any time with questions about ReDI
    School."
- **`small_talk_reply(question)`** returns the matching reply, or `None`.
  - The message is compared as a whole, after lowercasing, removing
    punctuation and collapsing spaces. "Thanks!" and "  THANK YOU " match.
    "thanks, how do I apply?" does not, so it stays a normal question.
- **The lists:**
  - greetings: hi, hello, hallo, hey, hi there, hello there, good morning,
    good afternoon, good evening
  - thanks: thanks, thank you, thank you very much, thanks a lot, thx,
    danke, great, cool, you are great
  - goodbyes: bye, bye bye, goodbye, see you
- **`answer_question()`** checks for small talk after the empty-content
  check and before retrieval. A match returns
  `AnswerResult(text=<reply>, enough_information=True, sources=[])`, and the
  model is not called.
  - `enough_information=True` means no contact link.
  - `sources=[]` means no Sources section.

### `src/run_evaluation.py`

- A new expected value `small_talk` passes when the answer is one of the
  three replies, `sources` is empty and there is no contact link.

### Not changed

- `src/app.py`, `static/`, `templates/`
- the JSON API shape (ADR 0002)
- retrieval

## Catalogue additions (`data/task8_questions.json`)

| ID | Question | Case | Expected |
|---|---|---|---|
| q22 | "thanks" | small_talk | small_talk |
| q23 | "hi" | small_talk | small_talk |

`tests/test_real_questions.py` accepts `small_talk` as an expected value and
checks the reply, the empty sources and that the model is not called.

## Acceptance criteria

Checked by unit tests:
- **AC1:** Greetings, thanks and goodbyes, in any letter case and with
  punctuation, get their reply. Sources are empty and the model is not
  called.
- **AC2:** A message that only contains a small-talk word, such as "thanks,
  how do I apply?", is answered as a normal question.
- **AC3:** Through `POST /api/chat`, "hi" returns the greeting with
  `enough_information: true`, `sources: []` and no `contact` field.
- **AC4:** The runner counts a `small_talk` case as passed for the right
  reply, and as failed otherwise.
- **AC5:** All existing tests pass.

Checked by hand (after): `python src/run_evaluation.py` gives q22 and q23
their fixed reply.

## Tests

- `tests/test_grounding.py`:
  - `test_small_talk_gets_its_reply_without_the_model` (AC1, parametrized)
  - `test_small_talk_inside_a_question_is_a_normal_question` (AC2)
- `tests/test_app.py`:
  - `test_greeting_has_no_sources_and_no_contact_link` (AC3)
- `tests/test_run_evaluation.py`:
  - `test_small_talk_case_passes_with_its_reply` (AC4)
  - `test_small_talk_case_fails_with_sources` (AC4)

## Iteration: polite words inside real questions

**Evidence:** while checking this fix in the real app, "thanks, how do I
apply?" got the fallback. It is not small talk, so it goes to retrieval with
the content words `thank` and `apply`. Since
`specs/task8_fix_retrieval_min_words.md`, a chunk needs both words, and no
chunk contains both. A polite word in front of a real question hid the
question.

**Change:** polite words and filler words from requests become stopwords in
`src/grounding.py`, so retrieval ignores them:
- polite words: thanks, thank, please, hi, hello, hey, hallo, danke
- request fillers: tell, know, want, would

Small talk on its own is still caught by `small_talk_reply()` before
retrieval, so this changes only messages that contain a real question.

**Simulated on the real `chunks.json` before implementing (2026-11-03):**

| Message | Before | After |
|---|---|---|
| "thanks, how do I apply?" | fallback | `/faq` and the course page ✅ |
| "please tell me how to apply" | 2 pages | 2 pages (with "please" alone as a stopword, 0) ✅ |
| "I want to know if the courses are free" | 2 pages | 3 pages, now including `/course-finder` ✅ |
| "hello, where is ReDI in Munich?" | 4 pages | 3 pages, including `/munich` ✅ |
| the 21 earlier catalogue questions | | unchanged, except the 5th result of q12 "When does it start?". The two chunks with the semester dates stay. |

**Catalogue addition:** q24 "thanks, how do I apply?" (straightforward,
answer, `/faq`).

**Acceptance criteria:**
- **AC6:** `tokenize()` drops polite and filler words.
- **AC7:** "thanks, how do I apply?" and "please tell me how to apply" find a
  chunk about applying.
- **AC8:** The catalogue tests pass with q24.

**Tests (`tests/test_grounding.py`):**
- `test_polite_and_filler_words_are_dropped` (AC6)
- `test_polite_words_do_not_hide_the_question` (AC7, parametrized)

## Known limitations

- **The list is maintained by hand.** Other small talk ("ok", "nice", "lol")
  still goes through retrieval. "ok" and "okay" are left out on purpose,
  because none of the three replies fits them. They keep the fallback.
- **The replies are in English,** also for "danke" and "hallo" (MVP: English
  only).
