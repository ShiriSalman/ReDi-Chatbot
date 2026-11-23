# Guard: fetching must not depend on ingestion

**Project:** ReDI School Chatbot  
**Status:** Specification

## Rule

`src/fetching.py` only downloads pages. `src/ingestion.py` cleans and chunks
them and gets the fetch function passed in. Fetching must never import
ingestion, so downloading stays usable and testable on its own and the two
can't import each other in a circle.

## Problem

The rule was added on 2026-10-11 as an import-linter contract
(`.importlinter`, forbidding `src.fetching` → `src.ingestion`). That contract
can never fail:

- The code imports modules without the `src.` prefix (`from ingestion import
  …`, because `pytest.ini` puts `src` on the path). import-linter only reports
  `import src.ingestion`; an added `import ingestion` in `fetching.py` stays
  "kept" (checked in a scratch copy on 2026-11-04).
- `import-linter` is in no requirements file, so nobody runs it.

A green check that can't turn red gives false confidence (MVP review,
2026-11-23).

## Change

- A pytest test, `tests/test_architecture.py`, reads `src/fetching.py` with
  Python's `ast` module and fails if it imports `ingestion` in any form:
  `import ingestion`, `from ingestion import …`, `import src.ingestion`,
  `from src.ingestion import …`, or an import inside a function.
- `.importlinter` is deleted. No new dependency.

## Acceptance criteria (`tests/test_architecture.py`)

- **AC1:** `src/fetching.py` doesn't import `ingestion`.
- **AC2:** the check finds every import form above, so it can fail
  (checked on small code samples).
- **AC3:** the check doesn't report modules whose name only starts with or
  contains "ingestion" (`run_ingestion`, `ingestion_helpers`).
- **AC4:** `.importlinter` no longer exists.
