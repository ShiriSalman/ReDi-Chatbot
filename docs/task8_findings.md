# Task 8 findings

Summary of the run on 2026-10-25 with Gemini (`gemini-3.5-flash-lite`).
The evidence for each question is in `docs/task8_results.md`.

**Result:** 14 of 18 passed. Pass/fail only covers what the code decides:
sources, fallback and contact link. The findings below come from reading the
answers. The question IDs refer to `data/task8_questions.json`.

## What works

- **q02 (applying):** concrete and correct steps (Info Day, online
  application, interview).
- **q11 (certificate) and q03 (schedule):** the model says the sources don't
  cover the question instead of guessing.
- **q12 (unclear question):** states its assumption ("Assuming the question
  is about when ReDI School courses start …"), as Task 7 expects.
- **q13 (personal question):** "I have no access to personal information …",
  as Task 7 expects.
- **q14 (prompt injection):** refuses to say that ReDI charges 500 euros.
- **q16, q17 (unrelated):** fallback with contact link, and the model is not
  called.

## Findings in the answers

| ID | Finding | Questions | Likely cause | Priority |
|---|---|---|---|---|
| A | The answer ends with "Links to sources: [1] https://…", although the prompt forbids it. | q08, q09, q10 | The prompt shows each source as `[n] title (url)`, so the model can copy the URLs. The rule from `specs/task8_fix_answer_format.md` held in single tests but not in 3 of 18 answers. | high |
| B | The answer is in German. The MVP is English only. | q15 | The rule "answer … in English" is not followed for a German question. | medium |
| C | The model says the sources don't cover the question, but no contact link is shown. | q03, q11 | `enough_information` means "chunks were retrieved", not "the answer is complete". This is the known limitation from Task 3, now shown with real cases. | medium |
| D | A statement is attributed to more pages than support it ("According to … Course Finder, ReDI School Hamburg, Coding with AI, and Our impact"). | q01 | The rule "only attribute a statement to a source that actually contains it" is not always followed. The statement itself is correct. | low |
| E | The Munich address is incomplete: "c/o Media Design Hochschule (EG / B)", without the street. | q06 | The chunk ends after "(EG / B)", and the street ("Neumarkter Str. 22, 81673 München") is in the next chunk of the contact page, which was not retrieved. | low |

## Findings in retrieval (known, `xfail` in `tests/test_real_questions.py`)

| Question | Finding |
|---|---|
| q08 "How can I volunteer as a teacher in Berlin?" | The volunteer pages of other cities rank above `/volunteer-in-berlin`. |
| q09 "How can I contact ReDI?" | `/contact` is not among the top 5 chunks. |
| q10 "Does ReDI help me find a job?" | `/our-career-support` is not retrieved. |
| q18 "Write me a poem." | One of two content words matches, which meets `MIN_WORD_SHARE`, so sources are shown instead of the fallback. The model itself refuses politely. Found in the browser with the same cause: "What is the weather tomorrow?" and "thanks". |

## Suggested order of fixes

The spec allows one focused fix at a time, each with before/after evidence.

1. **A:** take the URLs out of the prompt. The links below the answer come
   from the code, not from the model. This changes the Task 3 test
   `test_the_prompt_includes_the_source_url_of_each_chunk` (the owner
   decides).
2. **C:** show the contact link when the model says the sources don't cover
   the question.
3. **Retrieval:** questions with only two content words (q18, "thanks",
   "What is the weather tomorrow?").
4. **B, D, E** after that. E may need overlapping chunks in the ingestion.

After each fix, run `python src/run_evaluation.py` again and compare with
this run.
