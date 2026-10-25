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

## Out of scope

- Rendering Markdown on the page. It would need a library plus sanitising and
  would go against ADR 0002.
- The slow answers (56 s for "thanks"). Those are covered by the timeout in
  `specs/gemini_error_handling.md`, "Later".
- Small talk such as "thanks" reaching the model (Task 7, known). That needs
  a retrieval change, which is a separate decision.
