# Task 8 fix – Always answer in English

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

Finding B in `docs/task8_findings.md`, seen in both Task 8 runs on
2026-10-25 with `gemini-3.5-flash-lite`:

- **q15 "Sind die Kurse kostenlos?"** got a German answer: "Basierend auf den
  vorliegenden Informationen bietet die ReDI School kostenlose technische
  Bildung an."
- **In run 2** the same answer also ended with an invented URL ("Source: FAQ
  https://www.redi-school.org/faq"). No chunk contains that URL.

The MVP is English only (`CLAUDE.md`). Task 7 expects: "if chunks are found,
the model answers in English".

## Cause

- The only language rule is inside a condition: "*If the sources answer the
  question*, answer it clearly and briefly in English." It says nothing about
  partial answers or "not enough information" answers.
- The question is German, and so are the FAQ chunks it matches (the FAQ page
  contains German text). Both pull the model towards German.

## Change

One rule is added near the top of `INSTRUCTIONS` in `src/grounding.py`,
before the other rules:

- *Always answer in English, even if the question or the sources are in
  another language.*

The conditional rule loses its "in English" ("… answer it clearly and
briefly"), so the language rule is in one place only.

Nothing else changes:
- no language detection in code
- the fallback text stays the same (it is already English)
- retrieval stays the same

## Acceptance criteria

Checked by unit tests:
- **AC1:** The prompt contains "always answer in english".
- **AC2:** The rule comes before the sources and the question, also when
  both are German.
- **AC3:** All existing tests pass.

Checked by hand (after): run `python src/run_evaluation.py` again.
- **AC4:** q15 gets an English answer.
- **AC5:** q15 contains no URL.

## Tests (`tests/test_grounding.py`)

- `test_prompt_asks_to_always_answer_in_english` (AC1)
- `test_english_rule_comes_before_a_german_question_and_source` (AC2)

## Out of scope

- Answering in the visitor's language. Other languages are deferred until
  after the MVP (`CLAUDE.md`).
- Translating German chunks during ingestion.
