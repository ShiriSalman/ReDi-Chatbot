# Task 8 fix – Plain-text answers without source numbers

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

Found with a real model (Gemini, `gemini-3.8-flash`) in the chat page on
2026-10-24, as Task 8 asks (`specs/task8_test_against_real_user_questions.md`):

- **"thanks"** got bullet points written as Markdown, which the page shows as
  raw text: `* **From students:** A student expresses thanks … [1].`
- **The same answer** cites `[1]`, `[3]` and `[4, 5]`, but the page lists
  only 2 sources, without numbers.
- **"Are ReDI School courses free?"** got "Source [2] explicitly states …".

## Cause

- `build_prompt()` numbers each chunk (`[n] title (url)`) so that the model
  can tell the sources apart. The model reuses these numbers in its answer.
  The numbers then point nowhere, for two reasons:
  - `collect_citations()` merges chunks from the same page, so 5 numbered
    chunks can become 2 listed pages.
  - The page lists the sources without numbers.
- `INSTRUCTIONS` doesn't say what format the answer should have, so the model
  uses Markdown.
- `chat.js` shows the answer with `textContent` on purpose (ADR 0002), so
  Markdown is shown as raw text.

## Change

Two rules are added to `INSTRUCTIONS` in `src/grounding.py`. The wording can
be refined.

- *Write the answer as plain text in short paragraphs. Do not use Markdown,
  such as asterisks, bullet points or headings.*
- *Do not refer to sources by their numbers. The links to the sources are
  shown below the answer. If you need to name a source, use its title.*

Nothing else changes:
- The numbering in `build_prompt()` stays, because it still helps the model
  tell the sources apart.
- `citations.py` stays.
- `chat.js` keeps `textContent`, so no Markdown is rendered and no
  `innerHTML` is used.
- The JSON API stays.

## Acceptance criteria

Checked by unit tests:
- **AC1:** The prompt contains the plain-text rule. The test checks that it
  mentions "plain text" and "markdown".
- **AC2:** The prompt contains the rule not to refer to sources by number and
  to use the title instead.
- **AC3:** Both rules come before the sources and the question (like Task 7,
  AC5).
- **AC4:** All existing tests pass.

Checked by hand with Gemini (after):
- **AC5:** "thanks" and "Are ReDI School courses free?" get answers without
  `*`, `**`, `#` or `[n]`.

## Tests (`tests/test_grounding.py`)

- `test_prompt_asks_for_plain_text_without_markdown` (AC1)
- `test_prompt_asks_to_name_sources_by_title_not_number` (AC2)
- `test_format_rules_come_before_the_sources` (AC3)

## Iteration: no link lists, no over-attribution

**Evidence (after the first fix):** on 2026-10-25, with
`gemini-3.5-flash-lite`, "Are ReDI School courses free?" got a plain-text
answer, but with two new problems:

- It ended with "Links to sources: [1] https://www.redi-school.org/ … [5] …".
  This repeats the source list shown below the answer and uses numbers again.
  The model copies the URLs from the prompt (`[n] title (url)`).
- It said "According to ReDI School, Course Finder, ReDI School Hamburg, Our
  impact, and ReDI School NRW, all of their courses are free". Only Course
  Finder says so ("All our courses are free!"). The other pages speak of
  "free tech education" in general.

**Change:** two more rules in `INSTRUCTIONS`.
- *Do not list sources, links or URLs in the answer. They are shown below
  it.*
- *Only attribute a statement to a source that actually contains it.*

The URLs stay in the prompt. `test_the_prompt_includes_the_source_url_of_each_chunk`
(Task 3) requires them, and they help the model tell the sources apart.

**Acceptance criteria:**
- **AC6:** The prompt contains the rule not to list sources, links or URLs.
- **AC7:** The prompt contains the rule to attribute a statement only to a
  source that actually contains it.
- **AC8 (by hand):** "Are ReDI School courses free?" gets an answer without
  a link list. If it names a source for "all courses are free", that source
  is Course Finder.

**Tests:**
- `test_prompt_forbids_listing_sources_links_or_urls` (AC6)
- `test_prompt_asks_to_attribute_statements_only_to_supporting_sources` (AC7)

## Iteration: no URLs and numbers in the prompt

**Evidence:** in the Task 8 run on 2026-10-25 (`docs/task8_results.md`,
finding A in `docs/task8_findings.md`), 3 of 18 answers still ended with
"Links to sources: [1] https://…", despite the rule against it.

**Cause:** `build_prompt()` shows each source as `[n] title (url)`. The model
can copy what it sees, and a rule only makes copying less likely.

**Change:** `build_prompt()` shows each source as `Source: <title>`, followed
by its text, with no number and no URL. What the model doesn't see, it can't
copy.
- The links below the answer don't depend on this. They come from
  `collect_citations(result.sources)`, which still has all metadata
  (Task 3, Scenario 7).
- Each title belongs to exactly one URL in `data/chunks.json` (24 titles,
  checked on 2026-10-25), so the model can still tell the sources apart and
  name both sides of a conflict by title.
- The rules stay as they are.

**Changed test (Task 3):**
- `test_the_prompt_includes_the_source_url_of_each_chunk` becomes
  `test_the_prompt_names_each_source_by_title_without_its_url`.
- Scenario 7 asks for the metadata to stay attached to the chunks. That is
  still tested by `test_retrieved_chunks_keep_all_their_metadata` and
  `test_the_answer_lists_the_chunks_it_was_based_on`.

**Acceptance criteria:**
- **AC9:** The prompt contains each source's title and text, but neither its
  URL nor a number like `[1]`.
- **AC10:** All other tests pass unchanged.
- **AC11 (by hand):** run `python src/run_evaluation.py` again. No answer
  contains a URL or a `[n]` number.

**Tests:**
- `test_the_prompt_names_each_source_by_title_without_its_url` (AC9, changed)
- `test_prompt_has_no_source_numbers` (AC9)

## Out of scope

- Rendering Markdown on the page. It would need a library plus sanitising and
  would go against ADR 0002.
- The slow answers (56 s for "thanks"). Those are covered by the timeout in
  `specs/gemini_error_handling.md`, "Later".
- Small talk such as "thanks" reaching the model (Task 7, known). That needs
  a retrieval change, which is a separate decision.
