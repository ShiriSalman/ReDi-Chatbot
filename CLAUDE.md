# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This is the ReDI Chatbot, a chatbot that answers questions about ReDI School using official ReDI information and links to the relevant sources. It's a solo learning project: the owner decides how each task gets built. Propose options and explain tradeoffs rather than picking a stack or architecture on your own.

**Status:** planning only. There is no application code yet.

**Stack:** Python with Flask (decided). The Node/Jest setup (`package.json`, `tests/chat.test.js`) is left over from practicing and hasn't been removed yet.

## MVP scope (agreed)

- **Sources:** the ReDI website plus documents from ReDI staff, and nothing else. `sources.md` is the list of allowed sources and is filled in by hand.
- **Audience:** the general public.
- **Interface:** a simple web page.
- **Language:** English only.
- **When the sources don't cover a question:** say so and link to ReDI's contact page. Never guess or answer from general knowledge.
- **Every answer** includes links to the sources it used.
- **Deferred to after the MVP:** differentiating by audience, collecting user feedback, other languages, conversation memory, automatic re-crawling, and embedding on other platforms.

## Task order

The owner reviewed and approved this order:

1. Define scope and content boundaries: decide which ReDI pages and topics are in or out of scope (`sources.md` plus a spec)
2. Build the content ingestion pipeline: read or scrape web pages and PDFs, clean and structure the text, and keep the source URL on every content chunk
3. Design the answer-grounding approach: retrieval (RAG) to find the content that matches a question and produce an answer backed by it
4. *(after MVP)* Handle audience differentiation: tell prospective and current students apart and give each the right information
5. Define citation and sourcing behavior: how source links are shown, and what happens when no source is found
6. Build the conversational interface: the chat page itself (Flask + HTML/CSS/JavaScript)
7. Handle out-of-scope and edge-case questions: deal with unknown, irrelevant or problematic questions instead of making up answers
8. Test against real user questions: check correctness, tone, sources and the "I don't know" behavior
9. Deploy and make accessible: put the chatbot online once it's decided where it runs
10. Set up an update loop: document how to update the content (edit `sources.md`, re-run the ingestion). *(after MVP: collecting user feedback)*

Task 8, testing against real user questions, is the main measure of correctness for the whole project.

## Commands

- `npm install`: installs the dev dependencies (Jest).
- `npm test` (or `npx jest`): runs the tests.
- `npx jest path/to/file.test.js -t "test name"`: runs a single test.

`tests/chat.test.js` only holds practice tests that check Jest works. They don't test any real application code.

## Git

Changes go on a feature branch and are merged into `main` through a PR, which is how the owner practiced the workflow in PR #7.
