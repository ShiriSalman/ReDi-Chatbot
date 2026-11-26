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
address chunk, H as in run 10.

## Run 12: after reverting the title weighting

Run on 2026-11-09 with the same model and 24 questions. The only change
compared to run 10 is "as" as a stopword.

- **22 of 24 passed** (run 10: 21). q09 and q10 fail, as expected.
- **q06 has its address again:** `/contact` is a source, and the answer gives
  "c/o Media Design Hochschule (EG / B)" and says the street is missing (E,
  as in run 10).
- **q08 passes, but the answer is weaker than in run 11:** `/volunteer-in-berlin`
  is a source (5th of 5), but the answer says the sources "do not
  specifically state the online application process for Berlin" and is
  marked as not fully covered. In run 11, with the Berlin page ranked 2nd,
  the answer was about Berlin. Retrieval now finds the page, but low.
- **H as in run 10:** "how do i apply" and "thanks, how do I apply?" list
  "Coding with AI" again.
- **The earlier fixes still hold:** no source list, URL or visible marker;
  the personal-information note appears only for q20.

## Seen in the live app on Render on 2026-11-17

- **I: no course list.** "which courses are they" got an honest but unhelpful
  answer ("companies can host courses … the sources do not provide a full
  list of all available courses"), with the contact link. Sources: FAQ,
  ReDI School Denmark, NRW and Gothenburg; not the Course Finder, which lists
  the courses. Checked with the real retrieval:
  - **Side cause:** "they" is not a stopword, so the question has two content
    words, "course" and "they". The gate needs both in one chunk, and no
    Course Finder chunk contains "they".
  - **Main cause:** even "Which courses does ReDI offer?" doesn't find the
    Course Finder. Only 2 of its 13 chunks contain the word "course"; the
    others list courses by name, date and time.
  - **Not fixed with stopwords:** "they" alone gives the same sources as
    "which courses are there" (FAQ, NRW, Munich), still no Course Finder.
    Adding 28 pronouns and auxiliary verbs broke q14 and q20 (fallback
    instead of an answer). So the code is unchanged.
  - Recorded as q25 "Which courses does ReDI offer?" and q26 "which courses
    are they" (`xfail`). "they" also refers to an earlier question, and
    conversation memory is deferred until after the MVP.

## New source: the DCP Munich Applicant Hub (2026-11-18)

After `specs/task8_add_applicant_hub_source.md`. Retrieval only so far; the
evaluation run with the model is still to do (AC6).

- **Added:** the hub's start page and FAQ (26 questions). The 9 course
  pages are listed as No: with them, their "How to apply?" sections pushed
  the website FAQ out of the top 5 for q02, q21 and q24.
- **Ingestion:** `clean_html` now removes `<aside>` and uses only `<main>`
  when a page has one. Without this, GitBook's assistant, table of contents
  and page outline were in every hub chunk.
- **Retrieval now finds the Hub FAQ** for applying, minimum age, certificate,
  language ("Do I need to speak German?"), laptop and hours per week.
- **Still open, I:** no variant finds a course list. The hub start page lists
  the courses by name, without the words "course" or "Munich". q25 and q26
  stay `xfail`.
- **Website changes found:** 7 website pages changed since the last ingestion
  (Munich page −4,400 characters). Not included in this change, so the hub
  can be measured on its own; refreshing the website content is a separate
  step.

## Run 13: after adding the Applicant Hub start page and FAQ

Run on 2026-11-18 with the same model and 26 questions (q25, q26 added).

- **22 of 26 passed.** Only the known cases fail: q09, q10, q25, q26.
- **q11 (certificate) is answered now:** "Yes, you will receive a ReDI School
  certificate if you attend regularly and complete the course." Run 12 said
  the sources don't cover it.
- **q05 (German) is answered now:** courses are "held in English, but you do
  not need perfect English" (Applicant Hub FAQ). No contact link any more.
- **Apply questions (q02, q21, q24)** combine both FAQs: the Info Day from the
  website and "the application form … under the 'How to Apply' section of
  each course page" from the Hub FAQ. "Coding with AI" is no longer a source
  for them (H better).
- **New finding J (low): a wrong paraphrase.** q11 adds "For intermediate and
  advanced courses, attending them is mandatory to receive a certificate."
  The Hub FAQ says the *final projects* in those courses are mandatory, not
  attending. The rule "only attribute a statement to a source that actually
  contains it" doesn't catch a wrong paraphrase.
- **The earlier fixes still hold:** no source list, URL or visible marker;
  the personal-information note appears only for q20.

## Run 14: after the course lists per city and the website refresh

Run on 2026-11-19 with the same model and 28 questions (q27, q28 added).
Changes since run 13: `specs/task8_course_list_per_city.md` and a full
ingestion run (website refresh).

- **25 of 28 passed.** Only q09, q10 and q26 fail. (First recorded here as
  26; corrected after checking `docs/task8_results.md`.)
- **q25 "Which courses does ReDI offer?" is answered now:** eight locations
  with their numbers of courses (Berlin 22, Munich 16, …) and the topics.
- **q27, q28 pass, but the lists are incomplete.** Berlin lists 8 of 22
  courses; Munich mixes topics with courses ("Back-end Development, Web
  Development … Foundation Courses") and misses Python, Machine Learning and
  UX/UI. Cause: only one of the three parts of each city list reaches the top
  5 (always the shortest, part 3). The other places go to website pages with
  course-card text ("Berlin , User-Centered Design UX/UI Design Basics"),
  where city, topic and title run together. The catalogue only checks that
  one part is a source, so it doesn't catch this (like q06 in run 11).
- **q10 (job) is answered, but thinner than it could be:** "ReDI connects you
  to companies … career coaches". The career page ("Our Career Services":
  mentoring, career workshops, company visits, Talent Pool, ReDI for
  Ausbildung) is not a source. It says "career", "mentoring", "entry-level
  positions" and rarely "job", so the FAQ wins on the word "job". A search
  engine's AI overview answered with the career page's content, because it
  searches by meaning.
- **The earlier fixes still hold:** no source list, URL or visible marker;
  the personal-information note appears only for q20.

## Run 15: after giving the model the whole city list

Run on 2026-11-19 with the same model and 28 questions, after
`specs/task8_complete_city_lists.md`.

- **25 of 28 passed,** the same as run 14. Only q09, q10 and q26 fail.
- **The city lists are complete now (AC7):**
  - q27: "There are 22 courses available at ReDI Berlin", followed by all 22
    by name.
  - q28: "there are 16 courses available", followed by all 16 by name,
    including Python, Machine Learning and both UX/UI courses. No topics are
    listed as courses any more.
- The new catalogue check (every part of the city list retrieved) passes for
  q27 and q28; it failed before the change.

## Embeddings tested, not adopted (2026-11-19)

Tested for q09 and q10 with `gemini-embedding-001` (retrieval only): the gate
stays, the chunks that pass it are ordered by meaning instead of BM25.

- **Worse overall:** 8–10 failing catalogue questions instead of 3 (q01, q06,
  q07, q08, q25, q27, q28 get worse; "Which courses are there in Berlin?"
  gets volunteer pages).
- **q10 not fixed;** q09 fixed only when the title is embedded with the text.
- **Likely cause:** the chunks are 500-character pieces cut mid-sentence,
  often with menu or card text, so their embeddings carry little meaning.
- **Decision:** not now. Worth testing again only after the chunks are split
  by section or heading. Details: `specs/task8_job_career_synonyms.md`.

Instead, a single synonym ("job" also scores "career", ranking only) fixes
q10 without side effects.

## Run 16: after the job-career synonym

Run on 2026-11-19 with the same model and 28 questions, after
`specs/task8_job_career_synonyms.md`.

- **25 of 28 passed,** but one failure is not from the code: q02 "How do I
  apply for a course?" got the error message because Gemini answered
  `504 DEADLINE_EXCEEDED`. The app handled it as designed (logged, friendly
  message). q02 passed in every earlier run. Without the timeout: 26 of 28,
  only q09 and q26 fail.
- **q10 passes and uses the career page:** "According to Our Career
  Services, you can join the ReDI Talent Pool … tech companies can …
  offer entry-level positions to graduates or give them guidance".
- **But q10 is only partly right (low):**
  - part of it is written for companies ("offer jobs to the community and
    browse ReDI jobseekers"), because the retrieved chunk is the one about
    the Talent Pool and partners;
  - mentoring, career workshops and company visits are missing;
  - it adds "you can join as a career coach" from Volunteer in Copenhagen,
    which is about volunteering, not about help for learners.
- **The earlier fixes still hold:** no source list, URL or visible marker;
  the personal-information note appears only for q20.

## Run 17: after lists in answers, spelling correction and pacing

Run on 2026-11-19 with the same model and 28 questions, after three PRs:
lists in answers (`specs/task8_fix_answer_format.md`, "Iteration: simple
lists", #74), small spelling mistakes (`specs/task8_spelling_mistakes.md`,
#75) and pacing of evaluation runs
(`specs/task8_test_against_real_user_questions.md`, #76).

- **A run before the pacing was invalid:** 23 of 28, because the last 3
  questions got `429 RESOURCE_EXHAUSTED` (free tier: 15 requests per minute),
  not because of the list prompt. With 4.5 s between calls, this run had no
  error answers.
- **26 of 28 passed;** only the known q09 and q26 fail, as in run 16 without
  its timeout.
- **Lists:** 6 answers use them: the three course questions, q09, "Do I need
  to speak German?" and "How can my company support ReDI?". The city lists
  are complete: Berlin 22 of 22 courses, Munich 16 of 16, one per line.
- **No other Markdown:** no `*`, `**` or `#` in any answer.
- **Spelling correction:** it changes the retrieval of none of the 28
  questions (checked with and without it on the real chunks), so it can't
  explain a difference in this run. Its own checks are in its spec.
- **The earlier fixes still hold:** no source list, URL or visible marker.

## Run 18: after reading the contact page by sections

Run on 2026-11-20 with the same model and 28 questions, after
`specs/task8_contact_page_sections.md` (#77). The re-ingestion changed only
the contact page's chunks (387 instead of 385 chunks in total).

- **27 of 28 passed,** the best result so far; only q26 fails (it needs
  conversation memory, after the MVP). No error answers.
- **E is fixed:** "Where is ReDI School in Munich?" gets "c/o Media Design
  Hochschule (EG / B), Neumarkter Str. 22, 81673 München, Germany", plus the
  official address in Berlin. The Munich contact chunk is ranked first.
- **q09 passes for the first time** ("How can I contact ReDI?"): the first
  contact chunk is shorter and more focused, so the contact page reaches the
  top 5. Quality note (low): the answer lists specific contacts (partnerships,
  Tech Talks, volunteering in Berlin, Hamburg and NRW) but not the contact
  persons per location.
- **Sections on all pages were measured and not adopted:** 24 of 28 in the
  retrieval-only check (q10 and q14 lose their source). See the spec.

## Run 19: after correcting short stopword typos and two-typo words

Run on 2026-11-23 with the same model and 28 questions, after the spelling
iteration in `specs/task8_spelling_mistakes.md` (#81) and the per-visitor
limit (#80, not active in the evaluation).

- **27 of 28 passed,** the same as run 18; only q26 fails (it needs
  conversation memory, after the MVP). No error answers.
- As expected: the retrieval-only check had already shown that all 28
  questions retrieve the same pages as before. The change only helps
  misspelled questions such as "how du i apply" and "how to be a
  voulenteer", seen on the live page.

## Run 20: after the first content update with the change summary

Run on 2026-11-23 with the same model and 28 questions, on the content
update `update-content-2026-11` (the first run of the update loop from
`docs/update_content.md`). The change summary listed 6 of 26 sources as
changed, still 387 chunks; the only important change was the Course Finder's
Munich list.

- **27 of 28 passed,** the same as run 19; only q26 fails (it needs
  conversation memory, after the MVP). No error answers.
- **The new content reaches the answers:** "Which courses are there in
  Munich?" now lists Cybersecurity, which is new, and no longer lists
  Back-End Development.

## Seen in the live app on 2026-11-25: "What is ReDI?" (q29)

"what is redi" got the sources Contact, ReDI School Hamburg, Munich and
Berlin. The model said the sources don't define ReDI, gave what they mention
(locations, tech education) and marked the answer, so the contact link was
shown. The page that answers it, `/our-impact` ("ReDI School of Digital
Integration is a non-profit tech school …"), is ingested but not retrieved:

- After the stopwords only `redi` is left, and it is in 200 of 387 chunks, so
  BM25 gives it almost no weight. The contact and city pages repeat "ReDI
  School …" and rank first.
- Longer wordings don't help: "What is ReDI School?", "What does ReDI do?"
  and "what is redi school of digital integration" don't find `/our-impact`
  either.

Added as **q29** with a `known_issue` (strict `xfail`), so it counts as a
failed check until retrieval finds the page. No keyword rule was added: it
would be a special case for one question, like the reverted title weighting.
Expected in the next run: **27 of 29** automated evaluation checks pass
(checked in demo mode; q26 and q29 fail).

From now on the count is called "automated evaluation checks passed": the
checks cover retrieval and fallback only, and whether an answer is factually
right is judged by reading it, as in the runs above.

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
7. **Ranking:** ~~q08~~ done ("as" as a stopword), ~~q09~~ done (run 18,
   contact page by sections). Still open: q10,
   **I** (q25, q26: the Course Finder), q29 "What is ReDI?" (a word in half
   of all chunks), the German q15 finding only FAQ
   chunks, and **H** (the catalogue can't notice unrelated sources yet). Title weighting fixed q09 but cost q06 its
   address, so it was reverted. These cases may need semantic search
   (embeddings) instead of more keyword rules.
8. ~~**E**~~ Done (run 18): the contact page is read by its sections
   (`specs/task8_contact_page_sections.md`). The history:
   **E (known limitation, low):** the Munich address is cut between two
   contact-page chunks: chunk 0 ends with "…Integration Munich c/o Media
   Design Hochschule (EG / B)", chunk 1 starts with "Neumarkter Str. 22 81673
   München" and doesn't contain "Munich", so it isn't retrieved. Seen live on
   2026-11-19: the answer gives the partial address, says the full address
   isn't in the sources and offers the contact link, which is the intended
   behaviour.
   **Overlapping chunks tested (retrieval only, 2026-11-19), not adopted:**

   | Overlap | Chunks | Failing | q06 full address |
   |---|---|---|---|
   | none (today) | 385 | q09, q26 | no |
   | 80 characters | 446 | q09, **q14**, q26 | no |
   | 120 characters | 488 | q09, **q14**, q26 | no |
   | 160 characters | 539 | q09, **q14**, q26 | yes |

   Overlap changes every chunk of every page, and each size makes q14 lose
   its source. A real fix is chunking by section (one chunk per location on
   the contact page), which would also help the embeddings test and the q10
   answer (learners vs. companies on the career page). **D** after that.

After each fix, run `python src/run_evaluation.py` again and compare with
this run.
