# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This is the ReDI Chatbot, a chatbot that answers questions about ReDI School using official ReDI information and links to the relevant sources. It's a solo learning project: the owner decides how each task gets built. Propose options and explain tradeoffs rather than picking a stack or architecture on your own.

**Status:** the MVP is complete (2026-11-23). It runs publicly at https://redi-chatbot.onrender.com. In the last Task 8 run (2026-11-23), 27 of 28 automated evaluation checks passed; the one failure (q26, a follow-up question) needs conversation memory, which is after the MVP. q29 "What is ReDI?" was added on 2026-11-26 as a known retrieval failure, so the next run is expected to give 27 of 29. The checks cover retrieval and fallback only (expected page among the sources, fallback with contact link, small-talk reply); whether the answers are factually correct needs a manual review of the answers.

**Stack:** Python 3.14 and Flask, keyword retrieval (BM25, no embeddings), Google Gemini (`gemini-3.5-flash-lite`, free tier) for the answer text, plain HTML/CSS/JavaScript for the page, Docker on Render. The owner chose Gemini for free testing; a Claude API connection is specified but parked (`specs/claude_api_connection.md`).

## MVP scope (agreed)

- **Sources:** the ReDI website plus documents from ReDI staff, and nothing else. `sources.md` describes the rules; `data/sources.json` is the list the ingestion reads (only `"include": "Yes"` entries are used).
- **Audience:** the general public.
- **Interface:** a simple web page.
- **Language:** English only.
- **When the sources don't cover a question:** say so and link to ReDI's contact page. Never guess or answer from general knowledge.
- **Every answer** includes links to the sources it used.
- **Deferred to after the MVP:** differentiating by audience, collecting user feedback, other languages, conversation memory, automatic re-crawling, and embedding on other platforms.

## How it works

`docs/how_it_works.md` has diagrams. In short:

- **Ingestion** (`src/run_ingestion.py`, `src/ingestion.py`, `src/fetching.py`): fetches the `Yes` sources, cleans the HTML and saves chunks of about 500 characters, each with its source URL, to `data/chunks.json`. A source can set `"reader"`: `"course-list"` (the Course Finder, one list per city) or `"sections"` (the contact page, chunked by headings). It ends with a change summary per source. There is no PDF reader yet.
- **Answering** (`src/grounding.py`): small talk gets a fixed reply; otherwise BM25 retrieval with a gate (`MIN_WORD_SHARE`, `MIN_MATCHED_WORDS`), spelling correction, and `SYNONYMS`. No matching chunk means the fallback answer without a model call. Otherwise the prompt (`INSTRUCTIONS`) and the chunks go to the model, which answers only from them or returns a "not covered" marker.
- **Web app** (`src/app.py`): the chat page and `POST /api/chat`. The chunks are read once at start. The served app limits each visitor to 5 Gemini questions per minute (`src/rate_limit.py`); Gemini's used-up quota gives a 429 wait message. `src/citations.py` builds the source links; `static/js/format.js` turns the answer into paragraphs and lists (DOM only, never `innerHTML`).
- **Evaluation** (`src/run_evaluation.py`): checks the entries of `data/task8_questions.json` (29 questions), sends them through the API and writes `docs/task8_results.md`. Each run is summarised in `docs/task8_findings.md`.

## Task order

The owner reviewed and approved this order. All MVP tasks are done.

1. ~~Define scope and content boundaries~~ (`sources.md`, `specs/task1_content_scope.md`)
2. ~~Build the content ingestion pipeline~~ (`specs/task2_content_ingestion.md`; web pages only, no PDFs yet)
3. ~~Design the answer-grounding approach~~ (`specs/task3_answer_grounding.md`)
4. *(after MVP)* Handle audience differentiation: tell prospective and current students apart and give each the right information
5. ~~Define citation and sourcing behavior~~ (`specs/task5_citation_sourcing.md`)
6. ~~Build the conversational interface~~ (`specs/task6_chat_interface.md`, `specs/ui_redesign.md`)
7. ~~Handle out-of-scope and edge-case questions~~ (`specs/task7_out_of_scope_edge_cases.md`)
8. ~~Test against real user questions~~ (`specs/task8_test_against_real_user_questions.md` and the `task8_*` fix specs)
9. ~~Deploy and make accessible~~ (`specs/task9_deploy_render.md`, `specs/rate_limit_per_visitor.md`)
10. ~~Set up an update loop~~ (`specs/task10_update_loop.md`, `docs/update_content.md`). *(after MVP: collecting user feedback)*

Task 8, testing against real user questions, is the main measure of correctness for the whole project: its automated checks for retrieval and fallback, plus a manual review of the answers for factual correctness. Open items and the suggested order of fixes are at the end of `docs/task8_findings.md`.

## How the owner works

- **Spec first:** each task or fix gets a spec in `specs/` (or an "Iteration" section in an existing one) with numbered acceptance criteria, then failing tests, then the implementation. Commit the spec and tests first, then the code.
- **Check retrieval changes on the real content:** before and after a change to `grounding.py`, compare what the Task 8 questions and a set of unrelated questions retrieve. They should retrieve the same pages unless the change is meant to fix one.
- **The owner runs the evaluation** with their own `GEMINI_API_KEY`. Never ask for the key or write it in a file.
- **Explain before editing** when the owner asks for it, and keep solutions simple, without new dependencies.

## Commands

Run from the project folder with the virtual environment active (`.venv\Scripts\Activate.ps1`). Without it, `python` is the system Python and imports such as `requests` fail.

- `pip install -r requirements-dev.txt`: installs the dependencies.
- `python -m pytest`: runs all Python tests (`pytest.ini` puts `src` on the path). It also runs the JavaScript tests in `tests/js/` with Node's built-in runner (`tests/test_format_js.py`, skipped without Node).
- `python -m pytest tests/test_grounding.py -k "Spelling"`: runs some of the tests.
- `python src/app.py`: runs the chat page at http://127.0.0.1:5000. Without `GEMINI_API_KEY` it runs in demo mode (real sources, placeholder answer).
- `python src/run_ingestion.py`: refreshes `data/chunks.json` from the live pages (see `docs/update_content.md`).
- `python src/run_evaluation.py`: the Task 8 evaluation; with `GEMINI_API_KEY` it pauses 4.5 s between questions for the free tier.

`tests/test_real_questions.py` runs real questions against the committed `data/chunks.json`, so a content update can change its results.

The JavaScript tests need only Node, no npm packages: `node --test tests/js/` runs them directly. (A Jest setup from practicing was removed on 2026-11-23.)

## Things to know

- **Windows and PowerShell:** quote git arguments with braces (`'stash@{0}'`); `;` runs the next command even after an error. A local `python src/app.py` keeps running after its task is stopped, so stop old servers before checking the page in a browser.
- **The app reads `data/chunks.json` once at start:** restart it after an ingestion. On Render, a merged `chunks.json` triggers a new build.
- **The rate limit is only in the served app:** tests and the evaluation create the app without it.
- **Spelling correction has an upper word length** (`MAX_TWO_TYPO_LENGTH`): two-typo candidates grow with the square of the word's length, and one long word filled the memory without it.

## Git

Changes go on a feature branch and are merged into `main` through a PR, which is how the owner practiced the workflow in PR #7. The owner merges the PRs. Don't add Claude attribution lines to commits or PRs.
