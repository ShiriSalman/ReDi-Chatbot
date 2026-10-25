# Task 8 fix – Contact link when the model says the sources don't cover the question

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

Finding C in `docs/task8_findings.md`, seen in every Task 8 run on 2026-10-25
with `gemini-3.5-flash-lite`:

- **q03 "When do the courses take place?":** "The provided sources do not
  contain enough information to answer when the courses take place."
- **q11 "Is there a certificate after the course?":** "… there is no mention
  of whether a certificate is provided … The sources do not contain enough
  information to answer this question."

Neither answer shows the contact link, so the visitor hits a dead end. This
is the known limitation from Task 3 and `specs/task6_contact_link.md`:
`enough_information` is `True` whenever retrieval finds chunks, even when the
model then says they don't cover the question.

## Decision

The model gives the code a fixed signal (decided by the owner on
2026-10-25). The alternatives were:
- a contact link under every answer, which is always reliable but adds the
  link to complete answers too
- detecting phrases like "do not contain enough information", which is
  fragile because the wording changes

## Change

### `src/grounding.py`

- **New constant** `NOT_COVERED_MARKER = "[NOT COVERED]"`.
- **The two rules about missing information become one:**
  - *If the sources do not contain enough information to answer the whole
    question, start your answer with [NOT COVERED]. Then answer the part
    the sources cover, if any, and say which part they do not cover. Do not
    make up an answer.*
  - This replaces "If the sources cover only part of the question …" and
    "If the sources do not contain enough information to answer, say so …".
- **`answer_question()`**, after `remove_urls()`:
  - If the answer contains the marker (anywhere, in any letter case), every
    occurrence is removed, along with the space after it.
  - The result has `enough_information=False`. Its `sources` stay the
    retrieved chunks, because a partial answer still uses them.
  - If nothing but the marker was written, the text becomes
    `NOT_ENOUGH_INFO`.

### `src/app.py`, `static/js/chat.js`

No change. `app.py` already adds `contact` whenever `enough_information` is
`False`, and the page already shows Sources first and then the contact line
(`specs/task6_contact_link.md`).

### `src/run_evaluation.py`

- An "answer" case passes when retrieval found sources and the expected page
  (if set) is among them, whatever `enough_information` says.
- Whether the model fully covered the question shows in the "sources" column
  as "contact link".
- Without this change, q03 and q11 would count as failures exactly when the
  fix works.

## What `enough_information` means now

| Case | `enough_information` | `sources` | contact link |
|---|---|---|---|
| Retrieval finds nothing | `False` | `[]` | yes (unchanged) |
| Model answers fully | `True` | chunks | no (unchanged) |
| **Model marks the answer as not (fully) covered** | **`False`** | **chunks** | **yes (new)** |

The new row is the first case with `enough_information: false` and a
non-empty `sources`. The JSON API shape stays the same (ADR 0002).

## Acceptance criteria

Checked by unit tests:
- **AC1:** The prompt contains the marker rule, before the sources and the
  question.
- **AC2:** An answer starting with the marker returns `enough_information`
  `False`, the text without the marker, and the retrieved chunks as sources.
- **AC3:** The marker is also found in another letter case or in the middle
  of the answer.
- **AC4:** An answer that is only the marker returns `NOT_ENOUGH_INFO`.
- **AC5:** An answer without the marker is unchanged
  (`enough_information` `True`).
- **AC6:** Through `POST /api/chat`, a marked answer returns sources and the
  `contact` field, and the marker is not in the answer.
- **AC7:** The runner counts an "answer" case with sources and the expected
  page as passed, even with `enough_information` `False`.
- **AC8:** All existing tests pass.

Checked by hand (after): `python src/run_evaluation.py`.
- **AC9:** q03 and q11 show "contact link". No answer contains
  "[NOT COVERED]".

## Tests

- `tests/test_grounding.py`:
  - `test_prompt_contains_the_not_covered_rule` (AC1)
  - `test_marked_answer_is_not_enough_information_but_keeps_its_sources` (AC2)
  - `test_marker_is_found_in_any_case_and_position` (AC3)
  - `test_answer_that_is_only_the_marker_becomes_the_fallback_text` (AC4)
  - `test_answer_without_marker_is_unchanged` (AC5)
- `tests/test_app.py`:
  - `test_marked_answer_shows_sources_and_the_contact_link` (AC6)
- `tests/test_run_evaluation.py`:
  - `test_answer_case_with_contact_link_still_passes` (AC7)

## Known limitation

- Whether the model sets the marker is only likely. If it forgets the
  marker, the answer looks as it does today (no contact link).
- The keyword tests for the old rules are not affected. `"not"` and
  `"enough"` / `"cover"` still occur in the new rule (Task 3, Scenario 5).
