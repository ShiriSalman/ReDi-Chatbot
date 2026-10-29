# Task 8 fix – Two-word questions need two matching words

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

From the Task 8 catalogue and the browser on 2026-10-24/25
(`docs/task8_findings.md`, retrieval findings):

- **q18 "Write me a poem."** retrieves 5 chunks (4 pages) instead of the
  fallback. Its content words are `write` and `poem`. Only `write` appears in
  the content (5 chunks), which is 1 of 2 words.
- **"What is the weather tomorrow?"** (found with Playwright) retrieves 3
  chunks. Its content words are `weather` and `tomorrow`. Only `tomorrow`
  appears ("the leaders of tomorrow"), which is 1 of 2 words.

## Cause

`retrieve()` keeps a chunk when it contains at least `MIN_WORD_SHARE` (0.5)
of the question's content words. With two content words, one accidental
match is already 50 %. With three or more words the share works, which is
why "What will the weather be like in Tokyo tomorrow?" (1 of 3) correctly
gets the fallback.

## Change

`src/grounding.py`:
- New constant `MIN_MATCHED_WORDS = 2`.
- A chunk is kept only if it contains at least `MIN_WORD_SHARE` of the
  question's content words **and** at least
  `min(MIN_MATCHED_WORDS, number of content words)` of them.
- Questions with one content word are unchanged: one match is still enough,
  for example "When does it start?" or "Volunteering?".

Measured on the real `data/chunks.json` before implementing (simulation,
2026-10-27). Questions not listed keep exactly their results:

| Question | Before | After |
|---|---|---|
| q18 "Write me a poem." | 5 chunks | fallback ✅ |
| "What is the weather tomorrow?" | 3 chunks | fallback ✅ |
| q13 "What is my application status?" | 5 chunks; the model says it has no access to personal information | **fallback with the contact link** (decided by the owner) |
| the other 15 catalogue questions | expected page found | unchanged |

**q13:** its content words are `application` and `status`. `status` appears
in no chunk, so only 1 of 2 words matches. The owner accepted the fallback:
it still points to ReDI's contact page, which is what a personal question
needs. Its wording ("I can only answer questions about ReDI School …") fits
this question less well than the model's answer did.

## Catalogue changes (`data/task8_questions.json`)

- **q18:** the `known_issue` is removed. It is fixed, and `xfail(strict=True)`
  would otherwise report it as XPASS.
- **q13:** `expected` changes from `answer` to `fallback`.
- **New q19 "What is the weather tomorrow?":** `out_of_scope`, `fallback`.
  This is the case found in the browser.

## Acceptance criteria

Checked by unit tests:
- **AC1:** A two-word question whose chunks contain only one of the words
  retrieves nothing.
- **AC2:** A two-word question still retrieves a chunk that contains both
  words.
- **AC3:** A one-word question still retrieves a chunk that contains the
  word.
- **AC4:** The catalogue tests pass with q18, q13 and q19 as fallback, so
  only 3 xfails remain (q08, q09, q10).
- **AC5:** All other tests pass unchanged.

Checked by hand (after): `python src/run_evaluation.py` gives q13, q18 and
q19 the fallback with the contact link.

## Tests

- `tests/test_grounding.py`:
  - `test_two_word_question_needs_both_words` (AC1)
  - `test_two_word_question_finds_a_chunk_with_both_words` (AC2)
  - `test_one_word_question_needs_only_that_word` (AC3)
- `tests/test_real_questions.py`: unchanged; the catalogue changes cover AC4.

## Out of scope

- "thanks" and other one-word small talk. They still match "thank you" on
  ReDI pages. A separate small-talk fix may follow.
- The ranking problems q08, q09 and q10.
- The stemming of "status" to "statu". It changes nothing here, because both
  the question and the chunks are stemmed the same way and "status" appears
  in no chunk.
