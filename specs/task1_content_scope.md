# Task 1 – Define Initial Content Scope

## Source of truth

The approved sources are listed in `data/sources.json`, one object per source
with the fields `url`, `title`, `category`, `language`, `audience`, `include`
and `notes`. The ingestion pipeline (Task 2) reads this file.

`sources.md` holds the rules: topics to cover, inclusion rules, documents to
request, gaps and the done checklist. `tests/test_sources.py` checks
`data/sources.json` against these rules.

In the MVP, sources are **https web pages only**. Documents from ReDI staff
are tracked in `sources.md` section 4 ("Documents to request") until a format
for them is agreed.

---

## Scenario 1: Add a source to the content scope

**Given** an official ReDI web page is available  
**When** the source is added to the content scope  
**Then** its URL, title, category, language, target audience, include
decision and notes should be recorded in `data/sources.json`.

The last-updated date is not recorded here. It is captured during ingestion
(Task 2, Scenario 6).

---

## Scenario 2: Decide whether a source is included

**Given** a candidate source has been reviewed  
**When** the decision is recorded  
**Then** `include` should be `Yes`, `No` or `Maybe`  
**And** only sources marked `Yes` are used by the chatbot  
**And** a source marked `No` or `Maybe` should have a reason in `notes`.

`Maybe` means "still being reviewed" and is treated like `No`.

---

## Scenario 3: Follow the inclusion rules

**Given** the source list has been created  
**When** it is checked  
**Then** between 10 and 25 sources should be marked `Yes`  
**And** every included source should have `language: "en"`  
**And** every URL should use https  
**And** no URL should be listed twice.

---

## Scenario 4: Cover the required categories

**Given** the source list has been created  
**When** the content scope is reviewed  
**Then** it should cover About ReDI, Courses, Applications, Locations,
Volunteering, Career Support, Support ReDI, and Contact  
**And** every category should have at least one included source.

---

## Scenario 5: Record the target audience

**Given** the source list has been created  
**When** the content scope is reviewed  
**Then** every source should record its audience (for example "All",
"Prospective students", "Current students", "Volunteers")  
**And** at least one included source should be for prospective students and
one for current students.

In the MVP the audience is informational only: the chatbot answers everyone
the same way (audience: the general public). Telling audiences apart is
Task 4, after the MVP. This scenario has no automated test yet.

---

## Scenario 6: Handle topics without a reliable source

**Given** no official ReDI source is available for a topic  
**When** the content scope is reviewed  
**Then** the topic should be listed under "Gaps" in `sources.md` section 5  
**And** each gap should later be used as an unanswerable test question
(Task 8). The expected reply is the `NOT_ENOUGH_INFO` fallback with the link
to ReDI's contact page.

This scenario has no automated test yet.

---

## Checked by

- `tests/test_sources.py`: Scenarios 1 (fields), 2, 3 and 4.
- Scenarios 5 and 6 are checked by review, using the done checklist in
  `sources.md` section 6.
