# Task 10 – Update loop

**Project:** ReDI School Chatbot  
**Status:** Specification

## Goal

The chatbot's content only changes when someone runs the ingestion again
(automatic re-crawling is after the MVP). Task 10 makes that update a
repeatable routine:

1. **A guide,** `docs/update_content.md`: when to update, the steps from
   editing the sources to checking the live page, and how to tell whether an
   update made the answers worse.
2. **A change summary** at the end of `python src/run_ingestion.py`: which
   sources changed since the last run, so surprises are visible before the
   new chunks are committed.

The owner chose the guide plus the change summary (2026-11-23).

## Why a change summary

When the Applicant Hub was added (2026-11-18), the first ingestion showed that
7 website pages had changed since the run before; the Munich page had lost
4,400 characters. Today the script only prints counts ("Ingested: 26,
Failed: 0 …"); what changed is only visible in a large `git diff` of
`data/chunks.json`.

## Change summary

`compare_chunks(old_chunks, new_chunks)` in `src/run_ingestion.py` compares
the saved chunks from before the run with the chunks after it, grouped by
source. A chunk belongs to the source URL before any `?` (the Course Finder's
city lists link to `…/course-finder?category=Munich`, see `belongs_to`).

Each source is in exactly one group:

- **new:** chunks now, none before
- **removed:** chunks before, none now (marked `No` or deleted from
  `sources.json`)
- **changed:** chunks before and now, but their texts differ (in content or
  order). Shown with the number of chunks before and after and the change in
  characters.
- **unchanged:** the same texts as before

A source whose fetch failed keeps its old chunks, so it shows as unchanged;
the report above the summary already lists it as failed.

`format_changes(changes)` turns this into lines, printed after the report:

```
Changes since the last run:
  new: https://www.redi-school.org/new-page (3 chunks)
  removed: https://www.redi-school.org/old-page (5 chunks)
  changed: https://www.redi-school.org/redi-school-munich (12 -> 9 chunks, -4,400 characters)
  unchanged: 23 sources
```

With no new, removed or changed source, the first line is "No changes since
the last run." The summary only reads; it never changes which chunks are
saved.

## The guide (`docs/update_content.md`)

Written for the owner or whoever maintains the chatbot later, as a checklist:

- **When to update:** at the start of each semester (course lists and
  application dates change), when ReDI staff announce a change, and when a
  source is added or removed.
- **Steps:** edit `data/sources.json` (and `sources.md` if a topic or rule
  changes), run the tests, run the ingestion, read the report and the change
  summary, check the questions that depend on a changed page, run the Task 8
  evaluation and compare with the last run, commit on a branch, merge the PR,
  wait for Render, check the live page.
- **When something goes wrong:** a failed source, a page that lost its
  content, a worse evaluation; how to go back (`git checkout
  data/chunks.json`).
- **Limits:** no PDF reader yet, so documents from ReDI staff can't be
  ingested; the app reads the chunks once at start, so a local app must be
  restarted.

The README's "Update the content" step links to the guide. Outdated lines in
the README's "What it does not do yet" are corrected at the same time.

## Acceptance criteria

`tests/test_run_ingestion.py`:

- **AC1:** a source with chunks only after the run is listed as new, with its
  number of chunks.
- **AC2:** a source with chunks only before the run is listed as removed.
- **AC3:** a source whose texts differ is listed as changed, with the chunk
  counts before and after and the difference in characters.
- **AC4:** a source with the same texts is counted as unchanged.
- **AC5:** the city lists (`…?category=Munich`) count as part of their source.
- **AC6:** `format_changes` shows the groups as above, and "No changes since
  the last run." when nothing changed.
- **AC7:** `run()` returns the changes; a first run (no saved chunks) lists
  every ingested source as new.

- **AC8:** `docs/update_content.md` exists and the README links to it.

## Iteration: a safe `chunks.json` (MVP stabilization, 2026-11-25)

### Problem

- **An interrupted run can break the file.** `run()` writes `data/chunks.json`
  directly. If the run is stopped while writing (Ctrl+C, a crash, a full
  disk), the file is left half-written.
- **A broken file stops the app with an unclear error.** Checked on
  2026-11-24: `load_chunks()` with a half-written file raises
  `JSONDecodeError` while the app is loaded, so it doesn't start, and the clear
  log message in `log_startup()` is never written. The next ingestion run
  stops with the same `JSONDecodeError`.

### Change

1. **`run()` writes `chunks.json.tmp` first and then replaces `chunks.json`
   with it** (`os.replace`, standard library). The replacement happens as a
   whole, so `chunks.json` is always either the old or the new file. If
   writing or replacing fails, the `.tmp` file is removed and the old file
   stays. `*.tmp` is already in `.gitignore`.
2. **A broken file gives a clear error.** When `chunks.json` exists but is not
   valid JSON or not a list, `load_chunks()` (app) and `run()` (ingestion)
   raise an error that names the file and says what to do: re-run the
   ingestion, or restore the file with `git checkout data/chunks.json`. `run()`
   doesn't overwrite the broken file.
3. **The app still doesn't start with a broken file** (owner's decision D4,
   2026-11-25). A missing file still gives an empty list and the
   "temporarily unavailable" message, as before.

### Why the app doesn't start (D4)

On Render, an app that starts with no content would pass the health check
(`/` still loads) and replace the working version with one that answers
nothing. An app that doesn't start can't pass the health check.

**Not verified:** what Render does when the app crashes at startup. Render's
documentation says that when a new deploy doesn't pass its health checks
within 15 minutes, Render "cancels the deploy" and "continues routing traffic
to your service's existing instances"
(https://render.com/docs/health-checks, read 2026-11-25). It doesn't say
this explicitly for an app that crashes at startup. That the previous version
stays live in this case is an inference, not a tested fact.

### Assumptions

- `os.replace` replaces the file as a whole on Windows and on Linux (Render),
  when both files are in the same folder.
- A valid `chunks.json` is always a JSON list. The checks don't look inside
  the chunks.

### Acceptance criteria

`tests/test_run_ingestion.py`:
- **AC9:** a successful run leaves no `chunks.json.tmp` behind.
- **AC10:** when replacing the file fails, `chunks.json` keeps its old
  content, the `.tmp` file is removed, and the error is raised.
- **AC11:** when the saved `chunks.json` is not valid JSON or not a list,
  `run()` raises an error that names the file and `git checkout`, and doesn't
  change the file.

`tests/test_app.py`, `TestUnavailableContent`:
- **AC12:** `load_chunks()` with a file that is not valid JSON or not a list
  raises an error that names the file and `git checkout`.
- **AC13:** a missing file still gives `[]`; all existing tests pass.

## Not in scope

- Automatic or scheduled updates (after the MVP)
- A PDF reader for staff documents
- Collecting user feedback (after the MVP)
