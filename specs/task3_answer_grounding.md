# Task 3 – Answer Grounding Specification

## Goal

Design how the chatbot finds relevant information from the ingested ReDI
content and uses only that information to generate an accurate answer.

The chatbot should not invent information when the available ReDI content
does not support an answer.

---

## What this feature does

- receives a user question
- finds relevant chunks from the ingested ReDI content
- uses the retrieved chunks as context for the answer
- generates an answer based only on the retrieved ReDI content
- avoids unsupported claims
- indicates when the available content is not sufficient to answer

---

## Out of scope

This change does not touch:

- content ingestion or website scraping
- audience differentiation
- how citations are displayed to the user
- conversational UI design
- deployment
- automatic content updates

---

## The interface

`answer_question(question, chunks, generate)` in `src/grounding.py`.

**Input:**
- `question`: the user's question as text
- `chunks`: the ingested chunks (Task 2). Each chunk has at least `text`,
  `title` and `url`.
- `generate(prompt)`: the function that calls the language model and returns
  its answer as text. It is passed in, so tests use a fake model.

**Output:** an `AnswerResult` with:
- `text`: the model's answer, or `NOT_ENOUGH_INFO` ("I can only answer
  questions about ReDI School, and the available ReDI sources do not provide
  enough information to answer this one." Wording from Task 7.)
- `enough_information`: `False` only when retrieval found no relevant chunk
- `sources`: the retrieved chunks, unchanged, most relevant first (at most
  5). These are the chunks given to the model, not only the ones it used.

Helper functions: `retrieve(question, chunks)` finds the relevant chunks and
`build_prompt(question, chunks)` builds the prompt.

---

## Retrieval rules

- Question and chunk text are split into lowercase words. Stopwords (such as
  "the", "how", "is"), single letters and digits are dropped, and plurals are
  reduced to the singular ("courses" → "course").
- A chunk is **relevant** only if it contains at least half of the question's
  remaining words (`MIN_WORD_SHARE = 0.5`).
- Relevant chunks are ranked with BM25 (`K1 = 1.5`, `B = 0.75`), and at most
  5 are returned (`TOP_K = 5`).
- `MIN_WORD_SHARE` and `TOP_K` are first guesses, to be tuned with real
  questions in Task 8.

---

## Who decides what

- **Code decides** whether there is anything to answer from: if retrieval
  finds no relevant chunk, the result is `NOT_ENOUGH_INFO` and the model is
  **not called** (Scenario 4).
- **The model decides** how to answer from the retrieved chunks: using only
  them, saying what is not covered, and pointing out conflicts (Scenarios 3,
  5 and 6). It is told to do this in the prompt (`INSTRUCTIONS` in
  `src/grounding.py`).

---

## Boundaries and failure modes

**Before:** Ingested ReDI content must be available. If `chunks` is empty,
`answer_question` raises `ValueError` and the model is not called. This is
different from "no relevant chunk found", which returns `NOT_ENOUGH_INFO`.

**After:** The answer is based only on relevant retrieved ReDI content.

**What can go wrong:** No relevant content may be found, or the retrieved
content may not contain enough information to answer the question.

**What happens:** The chatbot does not invent an answer and indicates that
the available ReDI sources do not provide enough information.

### Edge cases

| Case | Behaviour |
|---|---|
| Blank question, or only stopwords ("What is it?") | no words left, so retrieval finds nothing: `NOT_ENOUGH_INFO`, model not called |
| Greeting or HTML-like input ("hallo", `<b>hallo</b>`) | usually no relevant chunk: `NOT_ENOUGH_INFO` |
| Long, multi-part question | needs half of its words in one chunk, so it often falls back to `NOT_ENOUGH_INFO` |
| Non-English question | can match German sections of English pages; the model is told to answer in English |
| `generate` raises an error | the error is not caught here; the caller handles it (Task 6 returns a 500) |
| `generate` returns empty text or says the sources don't cover the question | passed through as the answer; `enough_information` stays `True` and `sources` are listed (known limitation) |

### Known limitation

`enough_information` only reflects retrieval. If retrieval finds chunks but
the model says they don't answer the question, the result still has
`enough_information = True` and lists the retrieved chunks as sources. How
often this happens is measured in Task 8.

---

## Scenario 1 – Find relevant content

**Given** ingested ReDI content is available  
**And** a user asks a question covered by that content  
**When** the retrieval process runs  
**Then** relevant content chunks should be selected.

---

## Scenario 2 – Ignore unrelated content

**Given** the content collection contains both relevant and unrelated chunks  
**When** a user asks a question  
**Then** unrelated chunks should not be used as supporting context.

---

## Scenario 3 – Generate an answer from retrieved content

**Given** relevant chunks have been retrieved  
**When** the chatbot generates an answer  
**Then** the answer should be based on the information in those chunks  
**And** it should not add unsupported information.

---

## Scenario 4 – No relevant content found

**Given** a user asks a question that is not covered by the ingested content  
**When** no relevant chunks are found  
**Then** the chatbot should indicate that the available ReDI content does not
provide enough information to answer  
**And** the language model should not be called.

---

## Scenario 5 – Retrieved content is insufficient

**Given** relevant content is found  
**But** the content does not contain enough information to fully answer the question  
**When** the chatbot generates a response  
**Then** it should answer only what is supported  
**And** it should not invent the missing information.

---

## Scenario 6 – Conflicting retrieved content

**Given** multiple relevant chunks contain conflicting information  
**When** the chatbot prepares an answer  
**Then** it should not silently choose unsupported information  
**And** the conflict should be indicated rather than resolved by guessing.

---

## Scenario 7 – Preserve source information

**Given** chunks are selected to support an answer  
**When** they are passed to the answer-generation step  
**Then** their source metadata should remain attached  
**So that** citations can be added later.

---

## Verification

- **Unit tests** (`tests/test_grounding.py`) cover the precondition and
  Scenarios 1, 2, 4 and 7 completely, using a fake model.
- **Scenarios 3, 5 and 6** depend on the model. Unit tests only check that the
  right chunks reach the prompt and that the prompt contains the rule (use
  only the sources, say what is not covered, point out conflicts). Whether a
  real model follows these rules is checked in Task 8.
