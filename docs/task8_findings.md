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

## Run 2: after removing URLs and numbers from the prompt

Run on 2026-10-25 with the same model, after `specs/task8_fix_answer_format.md`
("Iteration: no URLs and numbers in the prompt"). Compare with
`git log -p docs/task8_results.md`.

- **A is fixed for English answers.** q08, q09 and q10 no longer end with a
  link list or `[n]` numbers.
- **One URL is left: q15, the German answer.** It ends with
  "Source: FAQ https://www.redi-school.org/faq". No chunk text contains this
  URL, so the model built it itself from the title and the ReDI domain. The
  URL happens to be correct, but it is invented. This answer also breaks the
  English rule (B), so fixing B may fix it too.
- **B, D and E are unchanged.** Still 14 of 18 passed. Pass/fail doesn't
  change, because the fix only affects the answer text.

## Run 3: after "Always answer in English"

Run on 2026-10-25 with the same model, after `specs/task8_fix_english_answers.md`.

- **B is fixed.** q15 answers in English and has no URL: "… the sources
  state that ReDI School offers free technical education." It still ends with
  "Sources: - FAQ", a list of titles without links.
- **New finding F: invented, partly wrong URLs.** q01 ends with a source list
  that has URLs. Two of them don't exist:
  - `https://www.redi-school.org/hamburg`; the real one is
    `/redi-school-hamburg`.
  - `/munich-courses/coding-with-ai-real-world-development-workflows`; the
    real one is `/web-development/munich/dcp/coding-with-ai`.

  q06 also ends with "Sources: - Contact (https://www.redi-school.org/contact)".
  Since run 2 the prompt has no URLs, so when the model ignores the rule
  "Do not list sources, links or URLs", it guesses them from the title and
  the domain. This breaks "never invent links" (Task 5). A prompt rule is not
  enough for this, so the code has to prevent it.

## Run 4: after removing URLs in code

Run on 2026-10-25 with the same model, after `specs/task8_fix_invented_urls.md`.

- **F is fixed.** None of the 18 answers contains a URL (`http`, `www.`) or a
  `[n]` number.
- **B is still fixed.** q15 answers in English: "… the courses offered by the
  ReDI School of Digital Integration are free of charge."
- **Left over (low):** q01, q05, q10 and q15 still end with a list of titles,
  for example "Source: FAQ, Course Finder". There are no links, nothing is
  invented, and the titles match the sources shown below the answer. It is
  only redundant (known limitation in the spec).
- Still 14 of 18 passed. C, D and E are unchanged.

## Run 5: after the "not covered" marker

Run with the same model, after `specs/task8_fix_contact_link_not_covered.md`.

- **C is fixed.** q03 and q11 now show the contact link. The marker
  "[NOT COVERED]" appears in none of the 18 answers.
- **The model also marked partial answers:** q05, q08 and q09. They give
  what the sources cover and offer the contact link for the rest, which is
  the intent of the rule.
- **Also marked:** q12 (unclear question), q14 (injection attempt) and q18
  ("Write me a poem."). q18 now at least offers the contact link. Its wrong
  sources are the known retrieval problem.
- **Observation (q15, German question):** retrieval finds only FAQ chunks,
  not Course Finder. The answer now says the sources "do not explicitly
  state whether the courses themselves are free". That is honest for those
  chunks, but weaker than the English question. It also adds an unrelated
  sentence about personal information.
- Still 14 of 18 passed. The runner now counts an "answer" case with the
  contact link as passed if the expected page was retrieved.

## Run 6: after the retrieval fix and the Render deployment

Run on 2026-11-02 with the same model and 19 questions. It includes the new
q19 "What is the weather tomorrow?" and `specs/task8_fix_retrieval_min_words.md`.

- **16 of 19 passed**, as expected. Only the three known ranking cases fail:
  q08 (Berlin volunteer page), q09 (contact page) and q10 (career support).
- **The two-word fix works with the real model.** q13, q18 and q19 get the
  fallback with the contact link, and the model is not called for them.
- **The earlier fixes still hold:**
  - no API errors
  - no URL in any answer
  - no visible "[NOT COVERED]" marker
- **Contact link:** shown on 13 of 19 answers. That is every fallback, plus
  every answer the model marked as not fully covered (q03, q05, q08, q09,
  q11, q12, q14, q15).
- **Left over (low):** q10 still ends with "Source: FAQ", a title without a
  link.
- **q15 (German):** the answer is in English. It stays cautious ("the
  sources do not explicitly state whether the courses are free"), because
  retrieval finds only FAQ chunks for the German question.
- **Seen in the live app on Render, not in this run:** "how do i apply"
  added an unrequested sentence about having no access to personal
  information. This is the same pattern as q15 in run 5. The
  personal-information rule may be applied too broadly.

## Run 7: after limiting the personal-information note

Run on 2026-11-02 with the same model and 21 questions. It adds q20 "Did I
pass the course?" and q21 "how do i apply", after
`specs/task8_fix_personal_info_rule.md`.

- **18 of 21 passed.** Only the known ranking cases q08, q09 and q10 fail.
- **The note now appears only where it belongs.** q20 answers "I have no
  access to personal information and suggest contacting ReDI directly." No
  other answer mentions personal information. In particular q02, q15 and
  q21 ("how do i apply", the live-app case) don't.
- **The earlier fixes still hold:** no API errors, no URLs, no visible
  marker.

## Run 8: after the small-talk replies and the polite-word stopwords

Run on 2026-11-03 with the same model and 24 questions. It adds q22
"thanks", q23 "hi" and q24 "thanks, how do I apply?", after
`specs/task8_fix_small_talk.md` and its iteration.

- **21 of 24 passed.** Only the known ranking cases q08, q09 and q10 fail.
- **Small talk gets its fixed reply,** with no sources, no contact link and
  no model call:
  - q22 "thanks": "You're welcome! …"
  - q23 "hi": "Hello! I answer questions about ReDI School …"
- **A polite word no longer hides the question.** q24 "thanks, how do I
  apply?" gets a real answer from the FAQ.
- **The earlier fixes still hold:**
  - no API errors, URLs or visible marker
  - the personal-information note appears only for q20

## Seen in the live app on Render on 2026-11-09

"how can i apply" got a correct answer from the FAQ, with two problems:

- **G: the model's own source list.** The answer ended with "Sources: - FAQ",
  and the real Sources section with links followed below it. This is the
  "Left over (low)" from runs 4 and 6, now seen by a user. Fixed in code by
  `specs/task8_fix_source_list_in_answer.md`. Still to confirm with
  `python src/run_evaluation.py`.
- **H: an unrelated source for a one-word question.** The sources were FAQ and
  "Coding with AI: Real-World Development Workflows". After the stopwords,
  "apply" is the only content word, so any chunk containing it matches. The
  course page says "Apply AI-assisted coding workflows", where "apply" means
  "use". q21 "how do i apply" has the same sources but passes, because the
  catalogue only checks that the expected page is among the sources, not that
  nothing unrelated is.

## Run 9: after removing the source list in code

Run on 2026-11-09 with the same model and 24 questions, after
`specs/task8_fix_source_list_in_answer.md`.

- **21 of 24 passed,** the same as run 8. Only the known ranking cases q08,
  q09 and q10 fail.
- **G is only partly fixed.** No answer ends with "Source:" or "Sources:" any
  more, but q02 ends with "Links to sources: - FAQ - Coding with AI: …".
  The code only knows the labels "Source:" and "Sources:", so this one stays.
  "Links to sources:" was already seen in finding A. AC5 is not met.
- **H is confirmed:** q02, q21 and q24 (all "apply" questions) list the
  "Coding with AI" course page as a source.
- **The earlier fixes still hold:**
  - no URL in any answer, no visible "[NOT COVERED]" marker
  - the personal-information note appears only for q20

## Run 10: after the extra source-list labels

Run on 2026-11-09 with the same model and 24 questions, after the iteration
"more labels (run 9)" in `specs/task8_fix_source_list_in_answer.md`.

- **21 of 24 passed,** the same as runs 8 and 9. Only the known ranking cases
  q08, q09 and q10 fail.
- **G is fixed.** No answer contains a source-list label ("Source:",
  "Sources:", "Links:", "Links to (the) sources:"). AC5 is met. One run can't
  prove the model never writes a new label, but the code would now remove
  every label seen in runs 1–9.
- **The earlier fixes still hold:**
  - no URL in any answer, no visible "[NOT COVERED]" marker
  - the personal-information note appears only for q20
- **H needs a closer look:** the "apply" questions still list "Coding with
  AI". For q02 "How do I apply for a course?" the model used that page for
  the course's application steps (Open Day, online application, orientation,
  onboarding). So the page is not always unrelated: it is unrelated to a
  general "how do i apply", but can fit "apply for a course".

## Run 11: after counting page titles in the ranking

Run on 2026-11-09 with the same model and 24 questions, after
`specs/task8_fix_ranking_titles.md` ("as" as a stopword, `TITLE_WEIGHT = 1`).

- **23 of 24 passed** (run 10: 21). Only q10 (career support) still fails.
- **q08 is fixed:** `/volunteer-in-berlin` is a source, and the answer is
  about Berlin (its programs, 500+ volunteers).
- **q09 is fixed:** `/contact` is a source. The answer lists contact people
  by city.
- **H is better:** "how do i apply" (q21) and "thanks, how do I apply?" (q24)
  no longer list "Coding with AI". q02 "How do I apply for a course?" keeps
  it, where run 10 showed it is useful.
- **Step back for q06 "Where is ReDI School in Munich?":** the sources are
  now `/munich` and `/course-finder`; `/contact` dropped out. The answer
  only says "located in Munich, Bavaria", without the address that run 10
  gave ("c/o Media Design Hochschule (EG / B)"). Likely cause: the title
  "ReDI School Munich" pushes the Munich page's chunks up, so the contact
  chunk with the address leaves the top 5. Not checked in detail yet. q06
  still passes, because the catalogue only checks that `/munich` is a
  source, not that the answer has the address. This makes E worse.
- **Model variation, not from the code:** q15 (German) has the same sources
  as in run 10, but this time the model marked it as not fully covered
  (contact link), as in run 5.
- **The earlier fixes still hold:** no source list, URL or visible marker;
  the personal-information note appears only for q20.

**After run 11: title weighting reverted.** No simple fix kept both q09 and
the q06 address (prototypes in `specs/task8_fix_ranking_titles.md`,
"Outcome"). The live app must not get worse, so step 2 is reverted. "as" as a
stopword stays. Expected now: q08 fixed, q09 `xfail` again, q06 with the
address chunk, H as in run 10. Still to confirm with an evaluation run.

## Suggested order of fixes

The spec allows one focused fix at a time, each with before/after evidence.

1. ~~**A:** take the URLs out of the prompt.~~ Done (run 2).
2. ~~**C:** show the contact link when the model says the sources don't cover
   the question.~~ Done (run 5).
3. ~~**Retrieval:** questions with only two content words (q18, "What is the
   weather tomorrow?").~~ Done (run 6). ~~One-word small talk such as
   "thanks"~~ done (run 8).
4. ~~**B**~~ Done (run 3), and ~~**F**~~ done (run 4).
5. ~~**The personal-information rule is applied too broadly** ("how do i
   apply" in the live app, q15 in run 5). Narrow its wording.~~ Done (run 7).
6. ~~**G** (source list in the answer).~~ Done (run 10).
7. **Ranking:** ~~q08~~ done ("as" as a stopword). Still open: q09, q10,
   the German q15 finding only FAQ chunks, and **H** (the catalogue can't
   notice unrelated sources yet). Title weighting fixed q09 but cost q06 its
   address, so it was reverted. These cases may need semantic search
   (embeddings) instead of more keyword rules.
8. **E:** the catalogue should check the answer content (here the Munich
   address), so a setback like run 11 is caught by a test, not only by
   reading. Then the street, which is in the next chunk (overlapping chunks
   in the ingestion). **D** after that.

After each fix, run `python src/run_evaluation.py` again and compare with
this run.
