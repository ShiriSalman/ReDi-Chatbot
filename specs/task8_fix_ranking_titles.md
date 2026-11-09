# Task 8 fix – Page titles count in the ranking

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

From `docs/task8_findings.md` (runs 6–10, "Findings in retrieval"), all
`xfail` in `tests/test_real_questions.py`:

| Question | Expected page | Problem |
|---|---|---|
| q08 "How can I volunteer as a teacher in Berlin?" | `/volunteer-in-berlin`, title "Volunteer in Berlin" | The volunteer pages of other cities rank higher. |
| q09 "How can I contact ReDI?" | `/contact`, title "Contact" | Not among the top 5 chunks. |
| q10 "Does ReDI help me find a job?" | `/our-career-support`, title "Our Career Services" | FAQ and course pages rank higher. |

Checked on 2026-11-09 with a script on `data/chunks.json`:
- For q08 and q09, the most important question words are in the page
  **title** ("berlin", "volunteer"; "contact").
- For q10, none of the question words are in the title.
- "as" is not a stopword, so q08 has four content words: "as", "berlin",
  "teacher", "volunteer".

## Cause

- `retrieve()` scores only the chunk **text**. The title, which says what the
  whole page is about, is ignored. A chunk of the Berlin page that mentions
  "volunteer" once scores like any other city's chunk.
- "as" appears in most chunks. With four content words, the gate
  (`has_enough_matching_words`) needs only two, so "as" plus "volunteer" is
  enough, and chunks from every volunteer page get through and compete.

## Prototype (before deciding the numbers)

A copy of `retrieve()` in a scratch script, run on all 24 catalogue questions
(retrieval only, no model). "Passed" uses the same rule as
`tests/test_real_questions.py`.

| Title weight | Gate uses title | "as" stopword | Passed | Known issues fixed | Newly broken |
|---|---|---|---|---|---|
| 0 (now) | – | no | 21/24 | – | – |
| 0 | – | yes | 22/24 | q08 | – |
| 1 | no | no | 22/24 | q09 | – |
| 1 | no | yes | **23/24** | **q08, q09** | – |
| 1 | yes | yes | 22/24 | q08, q09 | **q17** |

- Weights 2, 3 and 5 give the same results as 1, so 1 is chosen: the smallest
  change that works.
- Counting the title in the gate breaks q17 "Who won the last World Cup?":
  it gets sources instead of the fallback. So the gate stays text-only.
- q10 is not fixed by any setting, as expected.
- Side effect on H: with weight 1, "how do i apply" and "thanks, how do I
  apply?" no longer list "Coding with AI"; "How do I apply for a course?"
  still does (where run 10 showed it is useful). This is not designed, it
  comes from the changed scores, so it is not an acceptance criterion.

## Change

Two steps, each its own commit with the tests run after it.

**Step 1: "as" is a stopword.**
- `STOPWORDS` in `src/grounding.py` gets "as".

**Step 2: the title counts in the score.**
- New setting `TITLE_WEIGHT = 1` in `src/grounding.py`: how many times the
  title's words are added to a chunk's words for scoring.
- `retrieve()` scores each chunk on its text words plus its title words
  (`TITLE_WEIGHT` times). This applies to word frequency, chunk length and
  IDF alike, so BM25 stays consistent.
- The gate `has_enough_matching_words` still looks at the **text only**.
  A chunk whose only match is its title is not returned.
- A chunk without a title is scored on its text, as before.
- Chunks are still returned unchanged, with their metadata.

## Catalogue changes (`data/task8_questions.json`)

- **q08, q09:** the `known_issue` is removed. They are fixed, and
  `xfail(strict=True)` would otherwise report them as XPASS (a failure).
- **q10:** unchanged, still `xfail`.

## Acceptance criteria

Checked by unit tests:
- **AC1:** `tokenize` drops "as".
- **AC2:** of two chunks with the same text, the one whose title contains a
  question word ranks first.
- **AC3:** a chunk that matches the question only in its title is not
  returned (the gate is text-only).
- **AC4:** a chunk without a title is still found and scored on its text.
- **AC5:** q08 and q09 pass in `tests/test_real_questions.py`; q10 is still
  `xfail`; every other question gives the same result as before.
- **AC6:** all existing tests pass.

Checked by hand (after): `python src/run_evaluation.py`.
- **AC7:** 23 of 24 passed; q08 lists `/volunteer-in-berlin` and q09 lists
  `/contact`.

## Tests

`tests/test_grounding.py`:
- `test_as_is_a_stopword` (AC1)
- `test_title_word_ranks_a_chunk_higher` (AC2)
- `test_a_title_match_alone_does_not_pass_the_gate` (AC3)
- `test_chunk_without_title_is_scored_on_its_text` (AC4)

`tests/test_real_questions.py`: no code change; AC5 follows from the
catalogue change.

## Known limitations

- **q10 stays open.** Its words are in the text but not in the title. It
  needs its own look (probably "help", "find" and "redi" appear on many
  pages), possibly synonyms ("job" → "career").
- **H is only helped by chance.** The catalogue still can't notice an
  unrelated source. That needs its own change (a field such as
  `unexpected_url`).
- The weight was chosen on 24 questions. A page with a misleading title
  would now rank higher too.

## Outcome: step 2 reverted

Run 11 (`docs/task8_findings.md`) showed a side effect the prototype did not
check: q06 "Where is ReDI School in Munich?" lost the contact chunk with the
address. The title "ReDI School Munich" contains all three question words
("munich", "redi", "school"), so every chunk of the Munich page moved up and
filled the top 5. The address chunk fell from 4th place to below 10th. q06
still passed, because the catalogue only checks that `/munich` is a source.

Prototypes on all 24 questions (retrieval only) found no simple fix:

| Idea | q06 address in top 5 | Side effect |
|---|---|---|
| At most 1 chunk per page | yes | "how do i apply" gets volunteer pages of other cities (H worse) |
| At most 2 chunks per page | no | H worse |
| "redi" and "school" as stopwords | no | q14 fails |
| Title weight 0.25–0.75 | no | at 0.25 q09 also fails |
| "where" also scores "address" | yes | the contact page fills 4 of 5 places, `/munich` drops out, q06 fails |

The owner chose that the live app must not get worse, so step 2 is reverted
(`git revert`). Step 1 ("as" as a stopword, q08 fixed) stays.

**Result:** q08 fixed; q09 is `xfail` again; q06 gets the address chunk again
(4th place).

**What this shows:** for "Where …?" questions the page about the topic
(`/munich`) and the page with the requested fact (`/contact`, the address)
are different pages. Keyword ranking can't tell what kind of answer is
wanted, because "where" is a stopword. q06/E, q09 and q10 are a reason to
look at semantic search (embeddings) later.
