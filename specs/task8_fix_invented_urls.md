# Task 8 fix – No URLs in the model's answer

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

Finding F in `docs/task8_findings.md`, run 3 on 2026-10-25 with
`gemini-3.5-flash-lite`. q01 "Are ReDI courses free?" ended with:

> Sources: - ReDI School (https://www.redi-school.org/) - Course Finder (…) -
> ReDI School Hamburg (https://www.redi-school.org/hamburg) - Coding with AI …
> (https://www.redi-school.org/munich-courses/coding-with-ai-real-world-development-workflows) - …

Two of these URLs don't exist. The real ones are `/redi-school-hamburg` and
`/web-development/munich/dcp/coding-with-ai`. q06 also ended with a URL.

## Cause

- The prompt has no URLs since `specs/task8_fix_answer_format.md`
  ("Iteration: no URLs and numbers in the prompt").
- When the model ignores the rule "Do not list sources, links or URLs", it
  guesses URLs from the title and the domain.
- Prompt rules are only followed most of the time, and the results vary
  between runs. "Never invent links" (Task 5) must always hold, so the code
  has to enforce it (see Task 3, "Who decides what").

## Change

`src/grounding.py`:
- A new function `remove_urls(text)` removes every web address from the
  answer text:
  - `http://…` and `https://…`
  - `www.…`
  - a URL in brackets together with its brackets, so `Contact (https://…)`
    becomes `Contact`
  - afterwards, spaces are tidied so no double spaces or space before
    punctuation remain
- `answer_question()` applies it to the model's answer: `remove_urls(generate(prompt))`.

The real links are not affected:
- They come from the chunks' metadata (`result.sources` →
  `collect_citations()`) and are shown below the answer as before.
- `NOT_ENOUGH_INFO` and the demo answer contain no URLs, so they don't change.

## Acceptance criteria

Checked by unit tests:
- **AC1:** `remove_urls` removes `https://` and `http://` URLs, `www.`
  addresses, and URLs in brackets together with their brackets.
- **AC2:** Text without URLs is returned unchanged.
- **AC3:** `answer_question()` returns the model's answer without URLs, while
  `result.sources` still has the chunks' URLs.
- **AC4:** All existing tests pass. In particular,
  `test_urls_written_in_the_answer_do_not_become_sources` (Task 6) still
  holds.

Checked by hand (after): `python src/run_evaluation.py`.
- **AC5:** No answer in `docs/task8_results.md` contains a URL.

## Tests (`tests/test_grounding.py`)

- `test_removes_urls_from_the_text` (AC1, parametrized)
- `test_text_without_urls_is_unchanged` (AC2)
- `test_the_answer_has_no_urls_but_the_sources_keep_theirs` (AC3)

## Known limitation

- A list of titles such as "Sources: - FAQ" can remain as plain text. It has
  no links, so nothing is invented. It is only redundant.
- Email addresses such as `takuya@redi-school.org` (from the sources) stay,
  because they are not web addresses.
