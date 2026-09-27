# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This is the ReDI Chatbot, a chatbot that answers questions about ReDI School using official ReDI information and links to the relevant sources. It's a solo learning project: the owner decides how each task gets built. Propose options and explain tradeoffs rather than picking a stack or architecture on your own.

**Status:** planning only. There is no application code yet. The tech stack is undecided. `package.json` has Jest as a dev dependency, and there's also an empty Python `.venv` with only pip installed, so neither Node nor Python has been chosen.

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

1. Define the content scope (`sources.md`)
2. Collect real user questions, including ones that should get "I don't know"
3. Define citation behavior
4. Ingest the content (a one-off collection is fine)
5. Retrieve the relevant passages for a question
6. Ground answers in the retrieved passages
7. Handle out-of-scope questions
8. Build the web interface
9. Test against the Task 2 questions
10. Deploy
11. Document how to update the content

The Task 2 question set is the main measure of correctness for the whole project.

## Commands

- `npm install`: installs the dev dependencies (Jest).
- `npx jest`: runs the tests. `npm test` is still the npm placeholder and always fails.
- `npx jest path/to/file.test.js -t "test name"`: runs a single test.

There are no tests yet.

## Git

Changes go on a feature branch and are merged into `main` through a PR, which is how the owner practiced the workflow in PR #7.
