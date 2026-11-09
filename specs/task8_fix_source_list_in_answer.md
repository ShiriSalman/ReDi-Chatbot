# Task 8 fix – No source list in the model's answer

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

Seen in the live app on Render on 2026-11-09. "how can i apply" got:

> To apply as a student, go to the ReDI homepage and click on the Sign up for
> our Info day button.
>
> Sources:
> - FAQ

followed by the real Sources section with the links. The same leftover is in
`docs/task8_findings.md`: runs 3, 4 and 6 (q01, q05, q10, q15 end with
"Source: FAQ" or similar).

## Cause

- The model sometimes ignores the rule "Do not list sources, links or URLs in
  the answer".
- `specs/task8_fix_invented_urls.md` removes the URLs in code, but leaves the
  titles ("Known limitation"). The sources are then shown twice: as plain text
  from the model, and as links from `collect_citations()`.
- As with the URLs, a prompt rule is not enough, so the code removes it.

## Change

`src/grounding.py`:
- A new function `remove_source_list(text)` removes a source list at the end
  of the answer:
  - it starts with "Source:" or "Sources:" (any letter case)
  - at the start of a line, or after the end of a sentence (". Source: FAQ")
  - everything from there to the end of the answer is removed, including
    list lines such as "- FAQ"
- "source" inside a sentence ("the main source: the FAQ") is kept, as is
  "The sources do not say …" (no colon).
- `answer_question()` applies it after the marker is handled, so a marker at
  the end of a source list is still found. An answer that is only a source
  list becomes `NOT_ENOUGH_INFO`.

The real links below the answer are not affected: they come from
`result.sources`.

## Acceptance criteria

Checked by unit tests:
- **AC1:** `remove_source_list` removes "Source:"/"Sources:" lists at the end,
  on their own lines or after a sentence, in any letter case.
- **AC2:** Text without a source list is returned unchanged, including
  "source" inside a sentence.
- **AC3:** `answer_question()` returns the answer without the source list,
  still detects a `[NOT COVERED]` marker, and keeps `result.sources`.
- **AC4:** All existing tests pass. The expected text of
  `test_the_answer_has_no_urls_but_the_sources_keep_theirs` changes on purpose
  from "Yes, they are free. Sources: - FAQ" to "Yes, they are free."

Checked by hand (after): `python src/run_evaluation.py`.
- **AC5:** No answer in `docs/task8_results.md` ends with a source list.

## Tests (`tests/test_grounding.py`)

- `test_removes_the_source_list` (AC1, parametrized)
- `test_text_without_a_source_list_is_unchanged` (AC2, parametrized)
- `test_the_answer_has_no_source_list_but_keeps_marker_and_sources` (AC3)

## Known limitation

- If the model writes "Sources:" in the middle of the answer with more answer
  text after it, that text is removed too. It has not been seen so far.

## Iteration: more labels (run 9)

**Evidence:** in run 9, q02 still ended with "Links to sources: - FAQ - Coding
with AI: …". The code only knew "Source:" and "Sources:", so AC5 was not met.

All labels the model has used in `docs/task8_results.md` across all runs
(`git log -p`): "Sources:", "Source:", "Links to sources:",
"Links to the sources:" and "Links:". All of them were followed by a list of
source titles.

**Change:** `remove_source_list` also removes lists that start with "Links:",
"Links to sources:" or "Links to the sources:", with the same rules as before
(start of a line or after the end of a sentence, any letter case).

**Acceptance criteria:**
- **AC6:** the three new labels are removed (unit tests, including the exact
  q02 text from run 9).
- **AC7:** "links" inside a sentence is kept ("The FAQ has links: one for each
  city.").
- **AC5** is checked again with `python src/run_evaluation.py`.

**Still a limitation:** a label the model has never used, such as
"References:", is not removed.
