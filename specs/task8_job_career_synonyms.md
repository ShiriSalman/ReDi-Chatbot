# Task 8 fix – "job" also finds "career"

**Project:** ReDI School Chatbot  
**Status:** Specification

## Evidence (before)

q10 "Does ReDI help me find a job?" (`xfail`; run 15, 2026-11-19):

- The answer is correct but thin: "ReDI connects you to companies … career
  coaches".
- The career page "Our Career Services" (mentoring, career workshops, company
  visits, ReDI Talent Pool, ReDI for Ausbildung) is not among the sources.
- Checked with the real retrieval: the career page says "career",
  "mentoring", "entry-level positions" and only twice "job" in 10 chunks.
  The FAQ says "job" more often and fills the top 5.
- A search engine's AI overview answered the same question with the career
  page's content, because it searches by meaning.

## Alternatives checked (2026-11-19, retrieval only)

**Embeddings** (`gemini-embedding-001`, 768 dimensions): the gate stays, the
chunks that pass it are ordered by meaning instead of BM25.

| Ranking | Failing catalogue questions |
|---|---|
| BM25 (today) | q09, q10, q26 |
| Embeddings, chunk text | q01, q06, q07, q08, q09, q10, q25, q26, q27, q28 |
| Embeddings, title + text | q01, q06, q07, q08, q10, q25, q26, q27 |

Embeddings fix q09 in one variant but not q10, and make 6–7 questions worse,
for example "Which courses are there in Berlin?" gets volunteer pages. Likely
cause: the chunks are 500-character pieces cut mid-sentence, often with menu
or card text; an embedding of such a piece carries little meaning. Decision:
**not now**. Worth testing again only with chunks split by section or heading.

**A small synonym list** (scoring only):

| Synonyms | Failing catalogue questions | q10 top 5 |
|---|---|---|
| none | q09, q10, q26 | FAQ ×3, Volunteer in Copenhagen, Volunteer in Munich |
| job → career | q09, q26 | … **Our Career Services** (3rd) … |

## Change (`src/grounding.py`)

- A new setting `SYNONYMS = {"job": ["career"]}`.
- In `retrieve()`, the synonyms of the question's words are added **for
  scoring only**: they get an IDF and count in the BM25 score like the
  question's own words.
- **The gate is unchanged:** `has_enough_matching_words` still counts only
  the question's own words, so a synonym can't turn a fallback into an
  answer.
- More synonyms are added only with a catalogue question that needs them.

## Catalogue (`data/task8_questions.json`)

- q10: `known_issue` removed (it passes).

## Acceptance criteria

Checked by unit tests (`tests/test_grounding.py`):
- **AC1:** a chunk with the synonym ranks above a similar chunk without it.
- **AC2:** a chunk that matches only through a synonym doesn't pass the gate.
- **AC3:** a question without a word in `SYNONYMS` is scored as before.

Checked on the real content:
- **AC4:** q10 passes; no other catalogue question changes.

Checked by hand (after): `python src/run_evaluation.py`.
- **AC5:** the q10 answer uses the career page (for example mentoring,
  career workshops or the Talent Pool).

## Known limitations

- The list is maintained by hand and only covers what the catalogue showed.
- q09 "How can I contact ReDI?" stays open: neither synonyms nor embeddings
  fixed it without side effects.
