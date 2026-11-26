**English** | [Deutsch](README.de.md)

# 🤖 ReDi-Chatbot

## 💬 What this is

A chatbot that answers questions about ReDI School with clear answers based on official ReDI
information, and links to the sources it used.

- **Who it is for:** the general public, for example people who are interested in a course,
  or want to volunteer or contact ReDI.
- **What it uses:** only the ReDI website and documents from ReDI staff. The allowed sources
  are listed in `sources.md` (`data/sources.json` is the list the ingestion reads).
- **When the sources don't cover a question,** it says so and links to ReDI's contact page
  instead of guessing.
- **Language:** English only.

How it works step by step, with diagrams: [docs/how_it_works.md](docs/how_it_works.md).

## 📋 Before you start

You need:

- **Python 3.14** (the `Dockerfile` uses `python:3.14.7-slim`; use the same version locally)
- the packages in `requirements-dev.txt` (installed in the next step)
- optional: a **Google Gemini API key** for real answers. Without it, the app runs in demo
  mode (see below).

## 🚀 How to run it

### ⚙️ 1. Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

### 🔄 2. Update the content

Fetches the approved sources in `data/sources.json` and saves the chunks to `data/chunks.json`:

```powershell
python src/run_ingestion.py
```

At the end it prints which sources changed since the last run. The full routine for keeping
the content current (when to update, checking the answers, deploying) is in
[docs/update_content.md](docs/update_content.md).

### ▶️ 3. Run the chat page

```powershell
python src/app.py
```

To get real answers from Google Gemini, set your API key in the same terminal first
(never write it in a file that is committed):

```powershell
$env:GEMINI_API_KEY = "your-key"
python src/app.py
```

Without `GEMINI_API_KEY` the app runs in **demo mode**: retrieval and source links are real,
but the answer text is a placeholder that says it is not a real answer.

## ✅ How to know it worked

1. Open http://127.0.0.1:5000 in your browser.
2. You see the page **"ReDI School Chatbot"** with the welcome message **"Hi! How can I help
   you?"**, topic tabs with suggested questions, and a text field ("Ask about ReDI School…").
3. Ask **"How do I apply?"**. You should get:
   - an answer (with `GEMINI_API_KEY`) or the demo-mode placeholder (without it)
   - a **Sources** section below the answer with links to ReDI pages, for example the FAQ
4. Ask something unrelated, for example **"What is the weather tomorrow?"**. The chatbot says
   it can't answer this from its sources and shows a link to ReDI's contact page.

If every question gets a "temporarily unavailable" message, `data/chunks.json` is missing:
run the ingestion (step 2) first.

## 🚧 What it does not do yet

- **Demo mode** without `GEMINI_API_KEY`: no real answer text.
- **Keyword search, not semantic search:** small spelling mistakes are corrected, but a
  question that uses different words than the pages can still miss them. Known cases:
  "which courses are they" doesn't find the course list, and "What is ReDI?" doesn't find
  the "Our impact" page. Details in `docs/task8_findings.md`.
- **No conversation memory:** each question is answered on its own, so a follow-up such as
  "which courses are they" doesn't know what was asked before.
- **No automatic updates:** the content only changes when you re-run the ingestion
  ([docs/update_content.md](docs/update_content.md)).
- **No PDF reader:** documents from ReDI staff can't be ingested yet, only web pages.
- **Deferred until after the MVP:** different answers for prospective and current students,
  user feedback, other languages, conversation memory, and embedding on other platforms.
- **Public Render URL:** each visitor can ask 5 questions per minute, and Gemini's free tier
  allows 15 per minute for everyone together; after that the page asks visitors to wait.

The technical limitations are listed in
[docs/mvp_review.md](docs/mvp_review.md#known-limitations).

## 🧪 Evaluate real user questions (Task 8)

Sends every question in `data/task8_questions.json` through the chat API and writes the
results table to `docs/task8_results.md`:

```powershell
python src/run_evaluation.py
```

With `GEMINI_API_KEY` set, the answers come from Gemini (one call per answered question);
without it, only retrieval, sources and the fallback can be judged.

The result shows how many **automated evaluation checks passed**; the last run had "27 of 29".
These checks only look at whether the right ReDI pages were found and whether unrelated
questions got the fallback. Whether an answer is factually correct isn't checked
automatically: read the answers in the results table for that.
The findings from each run are summarised in `docs/task8_findings.md`.

## ☁️ Deploy to Render

The `Dockerfile` runs the app with gunicorn (see `specs/task9_deploy_render.md`). On Render:

1. Create a **Web Service** from this GitHub repo and choose **Docker** as the language.
2. Under **Environment**, add `GEMINI_API_KEY` with your key. Without it the app runs in demo mode.
   Never put the key in the repo or the `Dockerfile`.
3. Set the **health check path** to `/`.

After re-running the ingestion, commit `data/chunks.json`; Render then builds a new image.

## 🔬 Run the tests

```powershell
python -m pytest
```

## 🗂️ Where the decisions live

- **`CLAUDE.md`:** the agreed MVP scope and the task order.
- **`docs/how_it_works.md`:** diagrams of the structure, the ingestion and the answering flow.
- **`sources.md`:** which sources are allowed, and which were checked and excluded.
- **`specs/`:** one spec per task or fix, named after the task, for example
  `specs/task3_answer_grounding.md` (how answers are grounded in the sources),
  `specs/task5_citation_sourcing.md` (how source links are shown) and
  `specs/task9_deploy_render.md` (deployment).
- **`docs/adr/`:** Architecture Decision Records for decisions with tradeoffs:
  - `0001-ingestion-report-summary.md`
  - `0002-chat-interface-json-api.md`
- **`docs/task8_findings.md`:** what the evaluation found, and the order of the next fixes.
- **`docs/update_content.md`:** how to keep the content current (Task 10).
- **`docs/mvp_review.md`:** what the reviews after Task 10 found and changed, and the known
  limitations.

## 🤝 AI Collaboration & My Contribution

I developed this project using Claude Code, Anthropic's AI coding assistant, as a development partner. I was responsible for the project direction, requirements, technical decisions, quality assurance and final results, while AI supported the implementation.

### What I did

- **Defined the project scope and requirements:** target audience, approved sources, language and grounding rules.
- **Made technical decisions:** evaluated different approaches, compared their trade-offs and selected suitable solutions based on test results.
- **Established the development workflow:** specification first, numbered acceptance criteria, test-driven development and separate pull requests.
- **Managed the GitHub workflow:** reviewed, approved and merged every pull request.
- **Tested and evaluated the chatbot:** ran evaluations, tested the deployed application, identified issues and prioritized improvements.
- **Managed the MVP scope:** decided which findings to address and which to document as known limitations.

### What AI did

- Proposed technical approaches and explained their trade-offs.
- Drafted most of the implementation code, tests, specifications and documentation for my review.
- Supported debugging, code reviews and performance optimization.
- Ran approved tests and measurements and reported the results, including failures.

### Transparency & Traceability

Technical decisions, acceptance criteria and evaluation findings are documented in `specs/`, `docs/adr/` and `docs/task8_findings.md`. All changes are traceable through the GitHub pull requests.

This project demonstrates my approach to AI-assisted software development: combining human decision-making, critical evaluation and structured development practices with AI-supported implementation.
