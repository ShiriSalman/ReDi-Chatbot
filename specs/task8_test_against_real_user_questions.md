Task 8 — Test Against Real User Questions
Project: ReDI School Chatbot
Status: Specification — not yet implemented

## Goal
Test the chatbot with realistic questions from prospective and current ReDI students. Find gaps in retrieval, answers, citations, and fallback behavior before changing code.

## Scope
- Prepare 10–15 realistic questions about courses, applications, eligibility, schedules, and support.
- Include straightforward, unclear, partially covered, and out-of-scope questions.
- Use the existing Flask chat endpoint and approved ReDI source content.
- Record results and fix only problems supported by test evidence.

## Out of scope:
 New features, new data sources, a retrieval rewrite, and changing the chat UI without evidence.

## Test procedure
1. Create a small question set based on actual user needs; label each question by topic and expected behavior.
2. Check the approved ReDI pages to establish what a supported answer should contain.
3. Send each question through POST /api/chat or the browser and record the answer, enough_information, sources, and contact fallback.
4. Assess relevance, factual support, citation accuracy, and clarity. Record failures and their likely causes.
5. Make one focused improvement only if results justify it, then rerun the affected cases and existing tests.

## Acceptance criteria
- At least 10 different realistic questions are tested and documented.
- No unsupported facts are presented as verified ReDI information.
- Relevant source links point to the supporting ReDI pages; no invented links.
- Unknown or unrelated questions use the existing safe fallback behavior.
- Ambiguous and partially supported questions are assessed against Task 7 expectations.
- Failures are reproducible, with before/after evidence for any fix.
- Existing automated tests continue to pass.

## Evidence to record
For each question: question | expected behavior | actual answer | sources | pass/fail | notes. Keep a short summary of recurring problems and any fixes.

## Important limitation
demo_generate() does not produce a real grounded answer. In demo mode, evaluate retrieval, source selection, fallback, and API behavior only. Evaluate answer quality and hallucinations only after a real model is connected and tested. The enough_information flag means matching chunks were retrieved, not that the generated answer is correct.

## Iteration: stay under Gemini's free-tier limit (2026-11-19)

**Evidence:** in the run for the list prompt (branch `list-answers-prompt`),
the last 3 questions got "Something went wrong" instead of an answer. The
log shows `429 RESOURCE_EXHAUSTED`: "Generate content requests per minute
limit exceeded on Free Tier", limit 15 for `gemini-3.5-flash-lite`, retry in
25–35 s. The runner sends the questions back to back, and the SDK's retries
come back within the same minute. So the run measured the quota, not the
answers.

**Change:** with Gemini, `run_evaluation.py` waits **4.5 seconds before every
model call except the first**, so a run makes at most about 13 calls per
minute. Questions that don't reach the model (small talk, fallback) don't
wait. In demo mode nothing waits. A run of 28 questions takes about two to
three minutes.

**Acceptance criteria:**
- **AC-P1:** `paced(generate)` calls `generate` with the same prompt and
  returns its answer; the first call doesn't wait, every later call first
  waits 4.5 seconds.
- **AC-P2:** `run()` paces the calls with Gemini and doesn't pace them in demo
  mode.
- **AC-P3 (by hand, owner):** a full run with Gemini shows no "Something went
  wrong" answers.

The tests replace the waiting with a fake, so they stay fast.

## Iteration: what the checks measure, a checked question file (MVP stabilization, 2026-11-26)

### Problem

- **The count was read as "correct answers".** `docs/task8_results.md` ends
  with "27 of 28 passed", and `CLAUDE.md` says the evaluation "passes 27 of 28
  questions". But `passes()` only checks retrieval and fallback: for an
  "answer" case, that the expected page is among the sources; for a
  "fallback" case, no sources and the contact link; for "small_talk", the
  fixed reply. It never reads the answer text. Whether an answer is factually
  right is only known from reading it (Run 1–12 in `docs/task8_findings.md`).
- **A bad entry is found after the Gemini calls.** `evaluate()` reads
  `case["known_issue"]` and `case["expected_url"]` while it runs, and the
  results file is written only at the end. An entry without one of these keys
  stops the run with `KeyError` after the earlier questions have used
  Gemini's quota, and their answers are lost. An unknown `expected` value is
  silently checked like "answer".
- **"What is ReDI?" finds the wrong pages** (seen in the live app on
  2026-11-25). `/our-impact` answers it ("ReDI School of Digital Integration
  is a non-profit tech school …"), but "redi" is in 200 of 387 chunks, so BM25
  gives it almost no weight; the contact and city pages, which repeat "ReDI
  School …", rank above it. The catalogue had no question for it.

### Change

1. **`validate_questions()`** checks every entry before the first model call:
   the keys the runner reads (`id`, `question`, `expected`, `expected_url`,
   `known_issue`), a non-empty question, and an `expected` of `answer`,
   `fallback` or `small_talk`. If anything is wrong, `run()` raises
   `ValueError` listing every problem with the entry's id (or position), and
   no question is asked.
2. **The results file says what the checks cover.** The count reads "27 of 28
   automated evaluation checks passed", and the header explains what is
   checked and that factual answer correctness needs a manual review. The
   README, `CLAUDE.md` and `docs/update_content.md` use the same wording.
3. **q29 "What is ReDI?"** is added with `expected_url`
   `https://www.redi-school.org/our-impact` and a `known_issue`, so it is a
   strict `xfail` in `tests/test_real_questions.py` and is counted as a failed
   check in every run until retrieval finds the page (owner's decision,
   2026-11-25). No retrieval change: this is the keyword-search limit noted
   after Run 12 ("may need semantic search").

### Acceptance criteria

`tests/test_run_evaluation.py`:
- **AC-V1:** an entry without a required key, with an empty question, or with
  an unknown `expected` makes `run()` raise `ValueError` naming every problem,
  and the model is never called.
- **AC-V2:** the real `data/task8_questions.json` passes `validate_questions()`.
- **AC-V3:** `format_results()` ends with "N of M automated evaluation checks
  passed", and the file written by `run()` says that factual answer
  correctness is not checked and needs a manual review.

`tests/test_real_questions.py`:
- **AC-V4:** q29 retrieves no `/our-impact` chunk (strict `xfail` from its
  `known_issue`).

- **AC-V5:** all existing tests pass.

Expected after this change, checked in demo mode (pass/fail doesn't depend on
the answer text): **27 of 29** checks pass; q26 and q29 fail.

## Definition of done
- [ ] Question set and expected outcomes documented.
- [ ] At least 10 cases run and results recorded.
- [ ] Failures categorized and prioritized.
- [ ] Any justified fix verified with regression tests.
- [ ] Remaining limitations clearly documented.
