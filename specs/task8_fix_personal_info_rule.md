# Task 8 fix – Personal-information note only for personal questions

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

From `docs/task8_findings.md`, item 5 of the fix list:

- **Live app on Render, 2026-11-02, "how do i apply":** a correct answer
  (the "Sign up for our Info day" button), followed by an unrequested second
  paragraph: "For questions about your own application status or course
  enrolment, we have no access to personal information, so we suggest
  contacting ReDI directly."
- **Run 5, q15 "Sind die Kurse kostenlos?":** a general question about cost
  ended with "If you have questions about your own situation or course
  enrollment, we have no access to personal information …".

## Cause

The rule in `INSTRUCTIONS` is worded as a general statement:

> You have no access to personal information such as application status or
> course enrolment. For questions about a person's own situation, say so and
> suggest contacting ReDI directly.

The first sentence has no condition, so the model treats it as something to
say. Words like "apply" or "courses" remind it of "application status" and
"enrolment".

## Change

The rule in `src/grounding.py` is reworded so the note only applies to
personal questions:

- *Only if the question is about the visitor's own situation, such as their
  own application status, enrolment or results, say that you have no access
  to personal information and suggest contacting ReDI directly. Do not add
  this to answers to general questions.*

Nothing else changes. Retrieval decides as before which personal questions
reach the model. For example, "What is my application status?" gets the
fallback since `specs/task8_fix_retrieval_min_words.md`.

## Catalogue additions (`data/task8_questions.json`)

| ID | Question | Case | Expected | Why |
|---|---|---|---|---|
| q20 | "Did I pass the course?" | personal | answer | A personal question that still reaches the model (1 chunk). It should get the note. |
| q21 | "how do i apply" | straightforward | answer, `/faq` | The live-app finding, written as visitors type it. It should not get the note. |

## Acceptance criteria

Checked by unit tests:
- **AC1:** The prompt still mentions "personal information" (Task 7, AC4).
- **AC2:** The rule is limited to the visitor's own situation. The prompt
  contains "only if the question is about the visitor's own situation" and
  "do not add this to answers to general questions".
- **AC3:** The catalogue tests pass with q20 and q21.
- **AC4:** All existing tests pass.

Checked by hand (after): `python src/run_evaluation.py`.
- **AC5:** q02, q15 and q21 don't mention personal information.
- **AC6:** q20 says the chatbot has no access to personal information and
  suggests contacting ReDI.

## Tests

- `tests/test_grounding.py`:
  `test_personal_information_note_is_limited_to_personal_questions` (AC2)
- `tests/test_real_questions.py`: unchanged; the catalogue additions cover
  AC3.

## Known limitation

Like every prompt rule, this one is only followed most of the time. If the
note still appears in general answers, the alternative is a code check, as
for URLs (`specs/task8_fix_invented_urls.md`). Detecting "personal" reliably
is harder than detecting URLs, though.
