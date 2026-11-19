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

## Definition of done
- [ ] Question set and expected outcomes documented.
- [ ] At least 10 cases run and results recorded.
- [ ] Failures categorized and prioritized.
- [ ] Any justified fix verified with regression tests.
- [ ] Remaining limitations clearly documented.
