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

## Known limitations

- The excerpt format is written by hand on the website and can differ
  between courses; lines then have fewer details.
- Some course titles are in German, Swedish or Danish because the course is
  taught in that language. They are kept, so visitors can recognise them on
  the website.
- The lists are as current as the last ingestion run (Task 10, update loop).
- A question without a city ("which courses are there") gets the overview,
  not every course; the answer can then ask which city.
