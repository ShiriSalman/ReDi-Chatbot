# Task 8 fix – Give the model a city's whole course list

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

Run 14 (`docs/task8_findings.md`, 2026-11-19):

- q27 "Which courses are there in Berlin?" lists 8 of 22 courses.
- q28 "Which courses are there in Munich?" lists topics as courses ("Back-end
  Development, Web Development … Foundation Courses") and misses Python,
  Machine Learning and UX/UI.
- Both pass, because the catalogue only checks that the city list is among
  the sources.

Checked with the real retrieval: each city list has up to 3 parts
(`specs/task8_course_list_per_city.md`), but only one part reaches the top 5,
always the shortest (part 3). The other places go to website pages with
course-card text ("Berlin , User-Centered Design UX/UI Design Basics"), where
city, topic and title run together, which is where the model's mix-up comes
from.

## Change

### 1. Mark list parts (`src/ingestion.py`)

City list chunks get a new field `"list_part": true`. It means: this chunk is
one part of a list that is only useful complete. Other chunks don't have the
field. The overview chunk doesn't have it either (it is one complete text).

### 2. Bring the other parts along (`src/grounding.py`)

After `retrieve()` has chosen the top chunks:

- for every chosen chunk with `list_part`, all chunks with the same URL and
  `list_part` are added, in their original order (part 1, 2, 3);
- the parts of one list are kept together, at the place of the best-ranked
  part, so the model reads the list in order;
- chunks without `list_part` are unchanged, so this can't add FAQ chunks or
  other page parts.

A list has at most 3 parts, so a question about one city gets at most 2 more
chunks. The gate still decides whether anything is returned at all, so the
fallback behaviour doesn't change.

### 3. A stricter catalogue check (`tests/test_real_questions.py`)

For a question whose `expected_url` is a city list (`?category=`), every
chunk of that list must be among the retrieved chunks, not just one.

## Acceptance criteria

Checked by unit tests (`tests/test_grounding.py`, `tests/test_ingestion.py`):
- **AC1:** city list chunks have `list_part: true`; the overview and normal
  page chunks don't.
- **AC2:** when one part of a list is retrieved, all parts are returned, in
  part order, next to each other.
- **AC3:** chunks without `list_part` never pull in other chunks of the same
  URL.
- **AC4:** a question that gets the fallback today still gets it.

Checked on the real content:
- **AC5:** q27 and q28 retrieve all parts of their city's list (new check).
- **AC6:** no other catalogue question changes.

Checked by hand (after): `python src/run_evaluation.py`.
- **AC7:** the answers to q27 and q28 list the city's courses by name, not
  topics.

## Known limitations

- A question about several cities ("courses in Berlin and Munich") can get up
  to 6 list parts plus other chunks. That's still a small prompt.
- The chunk field `list_part` is new; old `data/chunks.json` files without it
  behave as before until the ingestion runs again.
