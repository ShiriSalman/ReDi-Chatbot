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

## Not in scope

- Automatic or scheduled updates (after the MVP)
- A PDF reader for staff documents
- Collecting user feedback (after the MVP)
