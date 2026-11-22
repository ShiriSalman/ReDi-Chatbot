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
6. **Otherwise, if the word has at least 8 letters (`MIN_TWO_TYPO_LENGTH`) and
   chunk words are two typos away, it becomes the one of those in the most
   chunks** (`voulenteer` → `volunteer`). Two typos = one typo of a word that
   is one typo away (Norvig's "edits2").
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
