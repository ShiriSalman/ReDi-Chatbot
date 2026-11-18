# Task 8 fix – Add the DCP Munich Applicant Hub as a source

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

- **Finding I** (`docs/task8_findings.md`): course questions don't find a
  course list. q25 "Which courses does ReDI offer?" and q26 "which courses are
  they" are `xfail`.
- **Weak answers** in run 12: q05 "Do I need to speak German?" ("the sources
  do not state whether you generally need to speak German"), q11 "Is there a
  certificate after the course?" (not covered).
- The website's application process pages (`/application-process-cyberspace`,
  `/application-process-hamburg`) have one sentence per step and are marked
  No. ReDI staff (Luciana) pointed to the Applicant Hub instead.

## The source

The **DCP MUC Applicant Hub**, https://redi-school-1.gitbook.io/dcp-muc-applicant-hub:

- Run by ReDI staff (contact luciana@redi-school.org), public, in English,
  updated regularly ("Last updated 21 hours ago" on 2026-11-18).
- Start page: semester dates, application status, course levels, and the
  list of courses in five tracks.
- FAQ: 26 questions (minimum age 18, courses in English, certificate, laptop,
  hours per week, free, hybrid format, Munich area only, selection).
- One page per course: level, content, requirements, schedule, start date,
  how to apply, certificate conditions.

## Decisions (owner, 2026-11-18)

- **Allowed:** it is on gitbook.io, not redi-school.org, but it is a
  document from ReDI staff, which `CLAUDE.md` allows.
- **All course pages**, not only the start page and FAQ.
- **Titles say "DCP Munich"**, so the model doesn't apply Munich rules to
  other locations.
- **It goes out of date each semester** (start dates, "applications are
  closed"), so it belongs in the update loop (Task 10).
- **The general hub** (`redi-school-1.gitbook.io/applicant-hub`, no location
  named) is not added before asking ReDI which locations it is for.

## Change

### 1. Ingestion: remove `<aside>` (`src/ingestion.py`)

Checked on 2026-11-18 with the real pages: GitBook puts the "GitBook
Assistant" controls and the table of contents (every course name) in
`<aside>`. `clean_html` keeps them, so every hub page would start with the
whole course list and match every course question, the same pattern as
finding H.

- `UNWANTED_TAGS` gets `"aside"`.
- Checked on the 24 existing sources: removing `<aside>` loses 0 characters
  on every page.
- The start page still lists the courses in its main text.

### 2. Sources (`data/sources.json`)

11 new sources, all `include: Yes`, language `en`, audience
`Prospective students`:

| Title | Path (after the hub URL) | Category |
|---|---|---|
| Applicant Hub – DCP Munich | (start page) | Courses |
| Applicant Hub FAQ – DCP Munich | `/frequently-asked-questions-faq` | Applications |
| Intro to Code, Data, and Design – DCP Munich | `/backend-development-track/intro-to-code-data-and-design` | Courses |
| Python – DCP Munich | `/backend-development-track/python` | Courses |
| Coding with AI – DCP Munich | `/backend-development-track/coding-with-ai` | Courses |
| Data Analytics – DCP Munich | `/data-ai-track/data-analytics` | Courses |
| Machine Learning – DCP Munich | `/data-ai-track/machine-learning` | Courses |
| Web Development Advanced – DCP Munich | `/web-development-track/web-development-advanced` | Courses |
| UX/UI Design Fundamentals – DCP Munich | `/ux-ui-design-track/ux-ui-design-fundamentals` | Courses |
| UX/UI Design Project-Based Learning – DCP Munich | `/ux-ui-design-track/ux-ui-design-project-based-learning` | Courses |
| Cybersecurity – DCP Munich | `/cybersecurity/cybersecurity` | Courses |

Not added, because they repeat a listed page:
- "Intro to Code, Data, and Design" in the Data / AI, Web Development and
  UX/UI tracks: the backend version has the same text plus a schedule table
  and the Orientation Quiz.
- "Coding with AI" in the Web Development track: identical to the backend
  version.

The website's "Coding with AI" page (`/web-development/munich/dcp/coding-with-ai`)
stays: its text is different (3 % similar). It describes the older process
with an Open Day; the hub page has the 2027 dates and the placement test. If
they conflict, the model's rule is to name both sources.

### 3. Rules (`sources.md`, `tests/test_sources.py`)

- The limit goes from **10–25** to **10–40** included sources (35 after this
  change).
- Section 1: "How to apply" and "Courses offered" also point to the hub.
- Section 4: the Applicant Hub question to Luciana is answered.

### 4. Content (`data/chunks.json`)

`python src/run_ingestion.py` is run again with the new sources.

## Acceptance criteria

Checked by unit tests:
- **AC1:** `clean_html` removes `<aside>` content and keeps the main text.
- **AC2:** `test_sources.py` passes with 35 included sources and the limit 40.

Checked on the real content (`tests/test_real_questions.py`, no model):
- **AC3:** every question that passed before still passes.
- **AC4:** q25 and q26 are checked again. If they pass (XPASS), their
  `known_issue` is removed; if not, the reason is recorded.
- **AC5:** no chunk from the hub contains "GitBook Assistant".

Checked by hand (after): `python src/run_evaluation.py`.
- **AC6:** q05 (German) and q11 (certificate) are compared with run 12.

## Known limitations

- A few lines of GitBook text stay on each page ("Skip to content", "This
  page is also available as Markdown", "Was this helpful?"). They are short
  and have no ReDI content words.
- The hub only covers Munich. Questions about other locations still depend
  on the website pages.
- The content changes each semester; until Task 10, the ingestion has to be
  run again by hand.
