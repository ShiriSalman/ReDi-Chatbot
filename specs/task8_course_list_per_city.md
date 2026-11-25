# Task 8 fix – A complete course list per city from the Course Finder

**Project:** ReDI School Chatbot  
**Status:** Specification  
**Depends on:** `specs/task8_add_applicant_hub_source.md` (same files: `src/ingestion.py`,
`data/chunks.json`). Implement after that PR is merged.

## Evidence (before)

- **Finding I** (`docs/task8_findings.md`): "which courses are there" and "Which
  courses does ReDI offer?" get no course list (q25, q26 `xfail`). Seen on
  Render twice: the answer says the sources "do not provide a complete list".
- **The ingestion reads only 20 of 74 courses.** The Course Finder shows 20
  entries and loads the rest while scrolling or filtering. `fetch_page` gets
  the first 20 only. Checked on 2026-11-18: the owner counted 16 courses for
  Munich in the browser's location filter; the ingested page has 4 of them.
- **The list is split over 13 chunks** in 500-character pieces, and most of
  them don't contain the word "course" ("Coding with AI … Munich … Tue & Thu,
  19:00 - 21:00"), so the gate drops them. Even if found, retrieval gives the
  model 5 chunks, not 13.

## The data

Squarespace returns the Course Finder as JSON:
`https://www.redi-school.org/course-finder?format=json`

- 20 items per page; `pagination.nextPage` and `pagination.nextPageOffset`
  give the next page (`?format=json&offset=…`). 74 items on 2026-11-18.
- Each item has `title`, `fullUrl` (its own course page), `categories` (city
  and topics, e.g. `["Munich", "Data Analytics"]`), `excerpt` (HTML list:
  format, audience, dates, language), `publishOn`, `updatedOn`.

Courses per city on 2026-11-18: Berlin 22, Munich 16, NRW 15, Hamburg 10,
Aarhus 10, Malmö 9, Copenhagen 9, Gothenburg 3.

**No age filter.** Most courses were *created* in 2020–2022 (Munich: 12 of
16 in 2020) but are current: 45 of 74 were *updated* in 2026. A filter on the
creation date would remove the current Munich courses. The chatbot shows the
same courses as the website; ReDI keeps that list up to date.

## Change

### 1. Read the whole Course Finder (`src/fetching.py`)

A new function reads all pages of a Squarespace collection as JSON and
returns the items. It follows `nextPageOffset` until there is no next page,
with the same timeout as `fetch_page`, and raises `FetchError` on an error
status.

### 2. Build the course lists (`src/ingestion.py`)

For the Course Finder, the ingestion builds text from the items instead of
cleaning the HTML:

- **One overview chunk** (URL: the Course Finder): "ReDI School offers free
  courses in 8 locations: Berlin (22 courses), Munich (16), …" plus the topics
  (Web Development, Data Analytics, …). It keeps "All our courses are free!"
  from the page, so q01 still finds the Course Finder.
- **One list per city** (URL: `/course-finder?category=<city>`, which opens
  the website with that filter), one line per course:
  `- <title> (<topics>; <format and language from the excerpt>)`.
- A city list longer than one chunk is split between courses, never inside a
  line, and **every piece starts with the same header**, e.g. "Courses in
  Munich (ReDI Course Finder, 16 courses, part 2 of 2):", so each piece
  contains "course" and the city name.
- Titles: "Course Finder – Munich" etc.

Which source uses this reader is set in `data/sources.json` with an optional
field `"reader": "course-list"` on the Course Finder entry. Other sources are
unchanged.

### 3. Links (`src/citations.py`, tests)

City URLs are the approved Course Finder URL plus `?category=<city>`. The
link checks (`test_no_invented_links`, `test_expected_urls_are_approved_sources`)
accept exactly that form. The URL is built by the code, never by the model.

## Acceptance criteria

Checked by unit tests (fake JSON, no network):
- **AC1:** all pages are read, following `nextPageOffset`; an error status
  raises `FetchError`.
- **AC2:** courses are grouped by city; a course in two cities appears in
  both lists; topics are kept.
- **AC3:** a long city list is split between lines, and every piece starts
  with the header naming the city and "courses".
- **AC4:** the overview chunk names every city with its number of courses.
- **AC5:** text from the excerpt is plain text (no HTML).

Checked on the real content (`tests/test_real_questions.py`):
- **AC6:** new questions pass: q27 "Which courses are there in Berlin?",
  q28 "Which courses are there in Munich?" (expected: the city's list).
- **AC7:** q25 and q26 are checked again; if they pass, their `known_issue`
  is removed.
- **AC8:** no other question gets worse.

Checked by hand (after): `python src/run_evaluation.py`.
- **AC9:** the answers to q25–q28 list courses by name.

## Iteration: shorter lines, the city named twice (2026-11-18)

The first ingestion with the real data showed three problems the unit tests
didn't catch:

- **The lists were too long.** With the excerpt details (dates, times, age),
  Berlin's list needed 11 chunks and Munich's 9, but the model gets 5.
  Measured: details cut to 150 characters → up to 11 chunks per city, 60 → up
  to 6, **none → at most 3**. So a line is now only `- <title> (<topics>)`;
  dates and times are left out (known limitation below).
- **The intro was missing.** On the real page the intro and the course cards
  are in one outer `<article class="sections">`; the cards have the class
  `blog-item`. Only `article.blog-item` is removed now. The test page has the
  same structure.
- **HTML codes in titles** ("Machine Learning &amp; AI"): titles are unescaped.

**The city named once wasn't enough.** The city lists passed the gate but
ranked below the city's own pages ("ReDI School Munich", "Volunteer in
Munich"), which mention the city 3–5 times per chunk. Prototype on the whole
catalogue:

| City in the list | Catalogue | q27, q28 | q06 address chunk |
|---|---|---|---|
| Header only | 23/28 | fail | kept |
| On every line | 25/28 | pass | kept |
| **Twice in the header** | **25/28** | **pass** | **kept** |

The header now reads "Courses in Munich (ReDI Course Finder, 16 courses at
ReDI Munich):" — the smaller change.

**Result:** q25, q27 and q28 pass; q26 stays `xfail` ("they" has no city and
no course word in common with the lists).

## Known limitations

- The lists have no dates, times or teaching language (see Iteration).
  Questions about one course's schedule need its own course page, which is
  not a source yet.
- Some course titles are in German, Swedish or Danish because the course is
  taught in that language. They are kept, so visitors can recognise them on
  the website.
- The lists are as current as the last ingestion run (Task 10, update loop).
- A question without a city ("which courses are there") gets the overview,
  not every course; the answer can then ask which city.

## Iteration: broken pagination and empty lists (MVP stabilization, 2026-11-25)

### Problem

Checked with fake data on 2026-11-24:

- **A repeated offset is read 50 times.** If the JSON says `nextPage` with the
  same `nextPageOffset` again, `fetch_collection()` asks for the same page
  until `MAX_COLLECTION_PAGES` (50) and returns **50 copies** of its courses.
  The report says "ingested".
- **The page limit cuts the list silently.** With more than 50 pages, the
  courses after page 50 are missing, and nothing says so.
- **An empty course list replaces the good one.** If the Course Finder returns
  no items, `ingest()` reports "ingested", deletes every city list and keeps
  only an overview that says "ReDI School offers courses in 0 locations".
  The same happens when there are items, but none is in a city of
  `LOCATIONS`.

### Change

1. **`fetch_collection()` raises `FetchError`** when a `nextPageOffset` comes
   back that was already read, and when it has read `MAX_COLLECTION_PAGES`
   pages and `nextPage` is still set.
2. **`ingest()` treats a course list without any city list as "no
   content"**: no items at all, or no item in a city of `LOCATIONS`.

Both use paths that already exist: a source that fails or has no content
keeps its chunks from the last run, and the ingestion report names it.

Unchanged: a normal pagination (the Course Finder had 4 pages), the city
lists, the overview and the links.

### Assumptions

- Squarespace's offsets are never repeated in a correct pagination.
- 50 pages are enough. The Course Finder had 4 pages of 20 courses.
- A Course Finder without a single course in a known city is always an error,
  never a real state of the website.

### Acceptance criteria

`tests/test_fetching.py`, `TestFetchCollection`:
- **AC10:** a repeated `nextPageOffset` raises `FetchError`, and the page is
  not read again.
- **AC11:** `nextPage` still set after `MAX_COLLECTION_PAGES` pages raises
  `FetchError`.

`tests/test_ingestion.py`, `TestCourseList`:
- **AC12:** a course list with no items is reported as "no content", and the
  chunks from the last run stay unchanged.
- **AC13:** the same for items that are all in cities outside `LOCATIONS`.
- **AC14:** all existing tests pass, including AC1 (every page is read) and
  "a failed course list keeps the old chunks".
