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

## 5. Stabilization (2026-11-24 to 2026-11-26, #97–#104)

A code review of `src/` found broken behaviour and missing error handling.
Each fix got a spec iteration with numbered acceptance criteria and failing
tests first. No new features or dependencies.

| Finding | Fix | PR | Spec |
|---|---|---|---|
| F1: a question with several long unknown words took 13–26 s (spelling correction) | at most 2 words get the expensive two-typo search; about 1.4 s, normal questions unchanged | #97 | `task8_spelling_mistakes.md` AC14–AC17 |
| F3: an answer emptied by cleaning showed no text but kept sources | it becomes the fallback with the contact link and no sources | #98 | `task8_fix_contact_link_not_covered.md` AC10–AC13 |
| F4: a broken Course Finder pagination could loop or duplicate courses; an empty list replaced the old lists | repeated offsets and more than 50 pages stop the source; a list without city lists keeps the old chunks | #99 | `task8_course_list_per_city.md` AC10–AC14 |
| E1: an interrupted run could leave a half-written `chunks.json`, and a broken file was overwritten or made the app start empty | atomic write; the ingestion and the app refuse a broken file with restore advice | #100 | `task10_update_loop.md` AC9–AC13 |
| E2: a typo in `include` or `reader` silently skipped a source | reported as failed, old chunks kept | #101 | `task2_content_ingestion.md` AC1–AC5 |
| Malformed citation URLs could raise an error | not a link, no error | #101 | `task5_citation_sourcing.md` AC9–AC11 |
| F6: a bad entry in the question file stopped the evaluation after Gemini calls | checked before the first call; the result says what the checks cover | #102 | `task8_test_against_real_user_questions.md` AC-V1–AC-V5 |
| F2: a made-up `X-Forwarded-For` got past the visitor limit (checked live) | the visitor is counted from the end of the header, as measured in the Render log | #103, #104 | `rate_limit_per_visitor.md` AC10–AC17 |

The F2 fix was checked live after deploying (2026-11-26): six questions with
made-up headers got the visitor limit on the 6th, like six without.

**Result:** 445 tests pass, 2 xfailed (q26 needs conversation memory; q29
"What is ReDI?" is a known retrieval failure). The expected evaluation result
is 27 of 29 automated evaluation checks.

## Known limitations

Checked in the code on 2026-11-26 and accepted for the MVP. None of them gives
a wrong answer as if it were from the sources.

**Answers**

- **"What is ReDI?" (q29):** "redi" is in about half of all chunks, so BM25
  gives it almost no weight and `/our-impact` isn't found
  (`docs/task8_findings.md`).
- **"IT" is a stopword:** it is lowercased to "it", so "IT courses" searches
  only "course".
- **Thresholds tuned on few questions:** `MIN_WORD_SHARE`,
  `MIN_MATCHED_WORDS` and the synonyms were tuned on the Task 8 questions;
  other wordings may miss or retrieve too much.
- **Spelling correction still costs time:** about 1.5 s for a question with
  long unknown words (F1 limits it; it doesn't remove it).
- **A blocked Gemini answer** (no text) is shown as "Something went wrong…
  Please try again", although trying again gives the same result.
- **The used-up quota** is recognised by the `code` attribute (429) of the
  SDK's error. If google-genai changes it, visitors see the general error
  instead of the wait message.

**Visitor limit**

- It depends on Render's proxy chain as measured on 2026-11-26
  (`RENDER_PROXY_ENTRIES = 2`). If it changes, the limit can become too strict,
  but not bypassable. It resets when the app restarts, and visitors on one
  network share it.

**Ingestion**

- **New cities:** a city in the Course Finder gets its own list only if it is
  in `LOCATIONS` (`src/ingestion.py`); otherwise it appears as a topic.
- **Squarespace format:** `fetch_collection` expects `items` and
  `pagination.nextPage`/`nextPageOffset` in `?format=json`. A changed format
  ends the source with an error (old chunks kept) or reads too few items.
- **Redirects are followed silently:** a moved page is read from its new
  address, but its chunks keep the old URL.
- **Pages without a charset:** `requests` reads `text/html` without a charset
  as ISO-8859-1, which would garble characters such as "ö". Today's pages
  declare it.
- **The URLs in `data/sources.json` are trusted:** whatever is listed with
  `"Yes"` is fetched; there is no domain check.
- **An empty `data/sources.json`** removes every chunk. The change summary
  shows this before the commit, and the app then starts with "content
  unavailable".
- **A course line longer than the chunk size** isn't cut, so its chunk would be
  longer than 500 characters. None is today (longest chunk: 500).

**Code**

- Naming leftovers, not changed to avoid unrelated refactoring:
  `enough_information` also means "not fully covered"; the parameter `request`
  in `visitor_key` and `fetch_collection` in `ingest` have the same names as
  the module-level objects; `plural()` exists in both `ingestion.py` and
  `run_ingestion.py`.
- `from app import …` (in `run_evaluation.py` and the tests) runs `app.py`'s
  module-level code: it loads `chunks.json` and creates the served app.
- google-genai shows a `DeprecationWarning` (`_UnionGenericAlias`, to be
  removed in Python 3.17). Harmless on Python 3.14; update google-genai before
  moving to 3.17.
- What Render does when the app fails at startup (for example with a broken
  `chunks.json`) hasn't been verified (`specs/task10_update_loop.md`).

## Open after the MVP

- Conversation memory (q26) and semantic search
- A PDF reader for documents from ReDI staff
- Security headers and `pip-audit`
- Browser tests for `static/js/chat.js`
- Watch whether the 45-second limit cuts off real answers on Render
