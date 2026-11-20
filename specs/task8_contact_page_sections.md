# Task 8 fix – Read the contact page by its sections

**Project:** ReDI School Chatbot  
**Status:** Specification

## Problem

Finding **E** in `docs/task8_findings.md`: "Where is ReDI School in Munich?"
gets only half of the address. `chunk_text()` cuts every page every 500
characters, wherever that falls. On the contact page the cut lands inside the
Munich address:

- chunk 36 ends: "Munich … Visiting address: ReDI School of Digital
  Integration Munich c/o Media Design Hochschule (EG / B)"
- chunk 37 starts: "Neumarkter Str. 22 81673 München Germany …"

Chunk 37 doesn't contain "Munich", so it is never retrieved.

The contact page has a heading per location (`<h2>Berlin</h2>`,
`<h2>Munich</h2>`, …, each followed by an `<h3>` with the contact person),
and each section is only 170–300 characters long.

## Measured before deciding (2026-11-19, retrieval only)

All approved pages were fetched once and chunked both ways, with a fake
model, through `run_evaluation.evaluate()`:

| Chunking | Chunks | Task 8 retrieval | Munich street retrieved |
|---|---|---|---|
| today, every 500 characters | 385 | 26 of 28 (q09, q26 fail) | no |
| by sections, **all pages** | 450–463 | 24 of 28 (loses q10, q14) | yes |
| by sections, **contact page only** | 387 | **27 of 28** (q09 passes) | yes |

On all pages, the new boundaries move q10's and q14's question words into
different chunks, so the gate rejects them. On the contact page alone,
nothing is lost, and q09 ("How can I contact ReDI?") passes for the first
time, because the first contact chunk is shorter and more focused.

**Decision (owner):** sections for the contact page only.

## Change

- **New reader** `"reader": "sections"` in `data/sources.json`, the same
  mechanism as `"course-list"`. Only the contact page gets it. Other pages
  can be switched later, each with its own measurement.
- **`sections(html)`** in `src/ingestion.py`: the page's text (same cleaning
  as `clean_html`: no nav, header, footer, aside, scripts; `<main>` if
  present), split at every `h1`, `h2` and `h3`. A section that has only its
  heading and no text of its own is joined with the next one, so
  "Munich" goes with "Birgit Köbl … Neumarkter Str. 22 …", not with Berlin.
- **`section_chunks(html)`**: whole sections are packed into chunks of at
  most `MAX_CHUNK_CHARS` (500), in page order. A section is only cut if it
  alone is longer than that, and then with `chunk_text()`.
- Everything else is unchanged: other pages, the course lists, BM25, the
  gate, spelling correction, the prompt, Gemini.

## Acceptance criteria

Checked by unit tests (`tests/test_ingestion.py`, `TestSections`):
- **AC1:** a heading and the text under it are in the same chunk, and a
  heading-only section goes with the next section: with a contact-page-like
  fixture, "Munich" and "Neumarkter Str. 22" are in the same chunk, and the
  Berlin chunk doesn't contain "Munich".
- **AC2:** small sections are packed together up to 500 characters; no chunk
  is longer than 500 characters.
- **AC3:** a section longer than 500 characters is split, and the next
  section starts a new chunk.
- **AC4:** nav, header, footer and scripts are left out, as in `clean_html`.
- **AC5:** `ingest()` uses the section reader only for a source with
  `"reader": "sections"`; other sources are chunked as before.

Checked on the real content:
- **AC6** (`tests/test_real_questions.py`): q09 passes. Its `known_issue` is
  removed from `data/task8_questions.json` (the xfail is strict).
- **AC7:** "Where is ReDI School in Munich?" retrieves a chunk with
  "Neumarkter Str. 22" (new test in `tests/test_real_questions.py`).
- **AC8 (by hand, owner):** a Task 8 run with Gemini: at least 27 of 28, and
  the Munich answer gives the full address.

## Known limitations

- Only the contact page uses sections. Other pages keep the 500-character
  cuts, including the career page (q10 answer quality).
- A page whose headings are not `h1`–`h3` (for example styled `<p>` or
  `<div>`) has no sections for this reader; it would be one long section,
  cut as today.
