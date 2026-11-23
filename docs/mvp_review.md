# MVP review: ReDI Chatbot after Task 10

After Task 10 (2026-11-23), the whole project was reviewed for code quality,
tests, documentation, dependencies, security and performance. The review found
no serious problems, but six spots to tidy up: outdated text, two checks that
couldn't fail, and a long wait without feedback. All six were fixed in four
PRs (#90–#93), each as spec → failing tests → code.

**Result:** 404 tests pass (1 xfailed: q26, which needs conversation memory,
after the MVP). Task 8 stays at 27 of 28.

## 1. Documentation brought up to date (#90)

- **`docs/how_it_works.md`:** the diagrams now show all steps added after the
  first version: the ingestion readers (`sections` for the contact page,
  `course-list` for the Course Finder), the change summary after the
  ingestion, spelling correction, synonyms, complete city lists, the limit
  per visitor and the 429 case.
- **README:** "How to know it worked" describes the current page (welcome
  message, topic tabs, "Ask about ReDI School…").
- **9 test files:** removed the outdated header line "…does not exist yet, so
  every test fails until it is written."

## 2. An architecture check that can really fail (#91)

- **Problem:** the import-linter rule "fetching must not import ingestion"
  could never fail: the code imports modules without the `src.` prefix, and
  import-linter wasn't installed.
- **Fix:** a small pytest test (`tests/test_architecture.py`) reads
  `src/fetching.py` with Python's `ast` module and fails on any import of
  `ingestion`. It was checked once with a real forbidden import, and the test
  turned red.
- `.importlinter` was removed. No new dependency.
- Spec: `specs/fetching_import_guard.md`.

## 3. Unused code removed (#92)

- **Problem:** `citations.format_answer()` rendered the sources as Markdown,
  but nothing used it; the web page displays the sources itself.
- **Fix:** the function was removed. The citation rules it was tested through
  (a page listed once, the order, URLs only from metadata, invalid URLs,
  partial and conflicting answers) are still tested, now through
  `collect_citations`. Only the 4 tests that checked Markdown details were
  deleted.
- Spec note: `specs/task5_citation_sourcing.md`.

## 4. Shorter waits and feedback on the page (#93)

- **Problem:** when Gemini was overloaded, a visitor could wait about 3
  minutes with only the typing animation (3 attempts × 60 s), and four such
  waits blocked all of gunicorn's threads.
- **Server (`src/llm.py`):** 2 attempts × 45 s, so the worst case is about
  1.5 minutes instead of about 3.
- **Page (`static/js/chat.js`):** after 15 s a "still working" note, visible
  and announced to screen readers; after 100 s the page gives up with "This
  is taking too long. Please try again in a moment." and puts the question
  back in the box.
- A test makes sure the page always waits longer than the server's worst
  case. Checked in the browser with an artificially delayed answer.
- Spec: iteration in `specs/gemini_error_handling.md`.

## Kept on purpose

- No test file was removed to reduce the number of files. Tests that look
  similar check different levels, for example `tests/test_rate_limit.py` (the
  counter) and `TestVisitorLimit` in `tests/test_app.py` (the HTTP response).
- The specs stay separate, because code and tests refer to them by name.

## Before the review

A few practice leftovers had already been removed: the outdated
`CLAUDE.md` status (#87), the Jest practice setup (#88) and the practice test
`tests/test_example.py` (#89).

## Open after the MVP

- Conversation memory (q26) and semantic search
- A PDF reader for documents from ReDI staff
- Security headers and `pip-audit`
- Browser tests for `static/js/chat.js`
- Watch whether the 45-second limit cuts off real answers on Render
