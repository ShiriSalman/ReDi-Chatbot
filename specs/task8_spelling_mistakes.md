# Task 8 fix – Small spelling mistakes in questions

**Project:** ReDI School Chatbot  
**Status:** Specification

## Problem

Retrieval compares the question's words with the chunks' words exactly
(BM25 plus the gate in `has_enough_matching_words`). "How can I apply for a
course?" works, but "How can I aply for a corse?" has the words `aply` and
`corse`, which appear in no chunk. The gate rejects every chunk and the
visitor gets the fallback, although the page they need exists.

## Change

In `retrieve()` in `src/grounding.py`, before the gate and the BM25 scoring,
each question word goes through `correct_spelling()`. The words of the chunks
are the dictionary.

1. A word that appears in a chunk is kept. Correctly spelled questions behave
   exactly as before.
2. A word with fewer than 4 letters, or with digits, is kept.
3. If the word is **one typo** away from a stopword (`wich` → `which`), it is
   dropped like a stopword.
4. Otherwise, if chunk words are **one typo** away, the word is replaced by
   the one that appears in the most chunks (`corse` → `course`, not `core`).
5. Otherwise the word is kept, as before.

**One typo** is one letter missing, one extra letter, one wrong letter, or two
neighbouring letters swapped (`one_typo_away()`, the "edits1" idea from Peter
Norvig's spelling corrector). No new dependency.

Unchanged: BM25 and its settings, the gate and its values, `SYNONYMS` (they
apply to the corrected words), `complete_lists`, the prompt and answer
format, Gemini. The model still gets the visitor's original question and
answers only from the retrieved sources.

## Why unrelated questions stay unrelated

- Only one typo is corrected: `weather` doesn't become `whether` (two typos).
- Short words are never corrected (`cos`, `hwo`).
- A known word is never changed, even if it is one typo from another word.
- The gate still needs at least half of the question's words and at least two
  of them in the same chunk; a correction can't let a single accidental word
  through.

## Acceptance criteria (`tests/test_grounding.py`, `TestSpellingMistakes`)

- **AC1:** a correctly spelled question finds the same chunk as before.
- **AC2:** "How can I aply for a corse?" finds the same chunk as the correctly
  spelled question; so do a swapped-letters and an extra-letter mistake.
- **AC3:** an unrelated question ("What will the weather be like in Tokyo
  tomorrow?") still finds nothing; a word two typos away is not corrected.
- **AC4:** a known word and a word under 4 letters are not changed.
- **AC5:** with several candidates, the one in the most chunks wins.
- **AC6:** a typo of a stopword is dropped.
- **AC7:** all existing tests, including `tests/test_real_questions.py`, pass
  unchanged.

## Check on the real content (2026-11-19, 385 chunks)

- All 28 Task 8 questions retrieve exactly the same pages as without the
  correction.
- 5 of 7 misspelled suggested questions ("How can I aply for a corse?", "Wich
  cuorses are tehre in Munich?", "How can I becom a volunter at ReDI?", "Do I
  need to speek Germen?", "Will I get a certifcate?") went from no sources to
  the same pages as the correct spelling. The other 2 are in the limitations
  below.
- 7 unrelated questions (weather, poem, football, capital of France, pizza,
  cake, bitcoin) still find nothing. In "How do I bake a chocolate cake?",
  `bake` and `cake` became `make`, and the gate still rejected every chunk.

## Known limitations

- Two typos in one word, or a typo in a word under 4 letters, are not
  corrected.
- A misspelling that is itself a real word in the chunks (`form` for `from`)
  is not changed. Real example: `jobb` is in 3 chunks (Swedish/Danish text on
  the volunteer pages), so "find a jobb" finds the volunteer pages, not the
  career page.
- Real example for short words: "Are ReDI corses fre?" corrects `corses` but
  not `fre` (3 letters, which is also one typo from "for", "fee" and "few").
- Only English letters a–z are tried; `Munchen` is not corrected to
  `münchen`.

## Iteration: short typos of stopwords, two typos in long words (2026-11-23)

### Problem

Three questions typed on the live page got the fallback:

- "how di i aply" and "how du i apply": `aply` was corrected, but `di`/`du`
  have fewer than 4 letters, so they stayed. They appear in no chunk, and with
  two question words the gate needs both in the same chunk.
- "how to be a voulenteer": `voulenteer` is **two** typos from `volunteer`
  (`ul`/`lu` swapped plus an extra `e`), so it wasn't corrected.

### Change

`correct_spelling()` now handles each unknown word in this order (new or
changed steps in bold):

1. A word that appears in a chunk is kept.
2. A word with digits is kept.
3. **A word one typo from a stopword is dropped, whatever its length**
   (`di`, `du` → `do`; before, only words with 4 or more letters).
4. A word with fewer than 4 letters is kept.
5. If chunk words are one typo away, the word becomes the one in the most
   chunks.
6. **Otherwise, if the word has 8 to 15 letters (`MIN_TWO_TYPO_LENGTH`,
   `MAX_TWO_TYPO_LENGTH`) and chunk words are two typos away, it becomes the
   one of those in the most chunks** (`voulenteer` → `volunteer`). Two typos =
   one typo of a word that is one typo away (Norvig's "edits2").
7. Otherwise the word is kept.

A one-typo candidate always wins over a two-typo candidate.

### Why unrelated questions stay unrelated

- Step 3 makes a misspelled question behave like its correct spelling: "how
  old ar yu" now finds the same chunks as "how old are you" already did. No
  new kind of match: a dropped word is one a correctly spelled question
  wouldn't have.
- Short words are still never *corrected* to a chunk word (`fre`, `cos`).
- Two typos only for long words: they have few neighbours two typos away.
  `weather` (7 letters) still doesn't become `whether`.

### Acceptance criteria (`TestSpellingMistakes`, `tests/test_real_questions.py`)

- **AC8:** "how di i aply" and "how du i apply" find the same chunk as "how
  do I apply"; `di` and `du` are dropped.
- **AC9:** a short unknown word that isn't one typo from a stopword is kept,
  so an unrelated question with it still finds nothing.
- **AC10:** a word with at least 8 letters is corrected across two typos
  ("how to be a voulenteer" finds the volunteer chunk); a shorter word is not.
- **AC11:** a one-typo candidate wins over a more common two-typo candidate.
- **AC12:** on the real content, the three live-page questions find the FAQ
  and the volunteer page.
- **AC13:** a word over 15 letters is not corrected across two typos, and a
  question with one 500-letter word is answered in under 2 seconds.

### Why the upper limit

The number of two-typo candidates grows with the square of the word's length:
about 170,000 for 11 letters, but hundreds of millions for one 500-letter word,
which `MAX_QUESTION_LENGTH` allows. The first full test run without the limit
filled the computer's memory. Real typos in words over 15 letters are rare, and
such a word is simply kept as it is.

### Check on the real content (2026-11-23, 387 chunks)

- All 28 Task 8 questions retrieve exactly the same pages as before.
- The three live-page questions went from no sources to the same pages as the
  correct spelling.
- 15 unrelated questions (weather, poem, football, pizza, cake, bitcoin,
  "how do i fix my tv", "recomend a restaurnt", "wht is the wether in berln",
  …) still find nothing.
- Cost: building the two-typo candidates takes about 0.3–0.4 s per unknown
  word of 8+ letters without a one-typo match. Correctly spelled questions
  never pay it.

### Known limitations (still)

- Short words are dropped or kept, never corrected: "fre" in "Are ReDI corses
  fre?" is dropped as a typo of "for", not read as "free".
- `scholarchip` stays as it is: "scholarship" appears in no chunk.

## Iteration: a limit on two-typo corrections per question (MVP stabilization, 2026-11-25)

### Problem

`MAX_TWO_TYPO_LENGTH` limits the cost of **one** word, but not of a whole
question. A 495-character question of 31 made-up 15-letter words (allowed by
`MAX_QUESTION_LENGTH`) builds the two-typo candidates 31 times: about 310,000
strings and 0.4–0.8 s per word. On the real content (387 chunks) one such
question took **13–25 s** in `retrieve()` (two measurements, 2026-11-24 and
2026-11-25; the time depends on the machine's load).

The limit per visitor (`specs/rate_limit_per_visitor.md`) doesn't help: it is
checked right before the model call, and such a question never reaches the
model. gunicorn runs 4 threads in one worker, and Python runs only one of them
at a time, so a few such questions make every visitor wait.

### Change

In `correct_spelling()`:

1. **At most `MAX_TWO_TYPO_WORDS = 2` words per question go through the
   two-typo step** (step 6), whether or not a chunk word is found for them.
   Further words that would reach it are kept as they are, like any word
   without a close chunk word (step 7).
2. **The words are handled in alphabetical order**, so which words get the two
   two-typo corrections is the same in every run. The question's words are a
   set, whose order can change between runs.

Everything else is unchanged: the steps 1–5, the one- and two-typo rules, the
length limits and which candidate wins.

### Assumptions

- A real question has at most 2 long words with two typos each. The 28 Task 8
  questions have 1 word that goes through the two-typo step at all
  (`instruction`, which has no close chunk word and stays as it is).
- About 2 × 0.4–0.8 s in the worst case is acceptable for the MVP.
- Alphabetical order is as good as any other: it only matters for questions
  with 3 or more such words.

### Acceptance criteria (`TestSpellingMistakes`)

- **AC14:** for a question with 3 or more long unknown words without a one-typo
  match, `two_typos_away()` is called at most `MAX_TWO_TYPO_WORDS` times.
  The test counts the calls; it doesn't measure time.
- **AC15:** the first two such words in alphabetical order are corrected, and
  the others are kept.
- **AC16:** a question with two long words two typos away corrects both, as
  before.
- **AC17:** all existing tests, including AC10–AC13 and
  `tests/test_real_questions.py`, pass unchanged.

### Check on the real content (2026-11-25, 387 chunks)

- **Same results:** the 28 Task 8 questions, 11 misspelled questions (the 7
  suggested ones, the 3 live-page ones and "how to be a voulenteer in the
  instrction team") and 15 unrelated questions retrieve exactly the same pages,
  with the same corrected words, as before the change.
- **Time**, measured twice in one run, alternating without and with the limit,
  so both see the same machine load:

  | | 28 Task 8 questions (total) | 495-character question |
  |---|---|---|
  | without the limit | 2.07 s, 1.68 s | 26.08 s, 22.23 s |
  | with `MAX_TWO_TYPO_WORDS = 2` | 1.90 s, 1.61 s | 1.45 s, 1.36 s |

### Known limitations (still)

- A question still costs up to about 1.5 s of computing, and the limit per
  visitor doesn't count it, because it never reaches the model. Many such
  questions at once can still slow the app down for everyone.
- A third long word with two typos in one question is not corrected.
