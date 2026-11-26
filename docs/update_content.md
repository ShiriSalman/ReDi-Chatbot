# Updating the chatbot's content

The chatbot only knows what is in `data/chunks.json`. That file changes only
when someone runs the ingestion again; nothing updates automatically. This
guide is the routine for doing that safely.

## When to update

- **At the start of each semester:** course lists, application dates and
  deadlines change (the Course Finder and the DCP Munich Applicant Hub).
- **When ReDI staff announce a change,** for example a new location or a new
  application process.
- **When you add or remove a source** in `data/sources.json`.
- **When an answer on the live page is out of date.**

## Steps

Run every command from the project folder with the virtual environment
active (`.venv\Scripts\Activate.ps1`).

### 1. Start a branch

```powershell
git checkout main
git pull
git checkout -b update-content-2026-11
```

### 2. Edit the sources (only if a source is added, removed or excluded)

- `data/sources.json` is the list the ingestion reads. Only entries with
  `"include": "Yes"` are used. To stop using a page, set `"No"` and give the
  reason in `notes`; its chunks are removed on the next run.
- `sources.md` explains the rules (official, stable, in English, not a
  duplicate, 10–40 included sources). Update it when a topic or rule changes.
- Check the rules:

```powershell
python -m pytest tests/test_sources.py
```

### 3. Run the ingestion

```powershell
python src/run_ingestion.py
```

It prints a report and a change summary, for example:

```
Ingested: 26
Skipped: 23
Failed: 0
No content: 0

Changes since the last run:
  changed: https://www.redi-school.org/redi-school-munich (12 -> 9 chunks, -4,400 characters)
  unchanged: 25 sources

Saved 384 chunks to data/chunks.json
```

### 4. Read the report and the change summary

| What you see | What it means | What to do |
|---|---|---|
| `Failed: 1` with a reason | The page couldn't be fetched. Its **old chunks are kept**, so it shows as unchanged. | Open the URL in a browser. If it's a temporary outage, run the ingestion again later. If the page moved, update the URL in `data/sources.json`. |
| `No content: 1` | The page loaded but had no text the cleaner could use. Old chunks are kept. | Open the page; its layout may have changed. |
| `changed: … -4,400 characters` | The page lost a lot of text. | Open the page and check that the content is really gone, not hidden in a new layout. |
| `new:` / `removed:` | A source was added, or marked `No` or deleted. | Should match what you changed in step 2. |
| `No changes since the last run.` | Nothing changed. | No commit needed; you're done. |

For details, `git diff data/chunks.json` shows every changed chunk text.

### 5. Check the answers

```powershell
python -m pytest
```

`tests/test_real_questions.py` checks that real questions still find their
pages in the new chunks. Then run the Task 8 evaluation with your
`GEMINI_API_KEY` set in the terminal (it takes a few minutes, because it
waits between questions for the free tier):

```powershell
python src/run_evaluation.py
```

Compare the result with the last run in `docs/task8_findings.md` (27 of 29
automated evaluation checks passed in run 21 on 2026-11-26; q26 and q29 are
known failures). The checks cover
retrieval and fallback only, so also read the answers of the changed topics. Also ask the chat page a question about each changed page:

```powershell
python src/app.py
```

The app reads the chunks once at start, so restart it after an ingestion.

### 6. Commit, merge and deploy

```powershell
git add data/chunks.json data/sources.json sources.md docs/task8_results.md
git commit -m "Update the content: <what changed>"
git push -u origin update-content-2026-11
```

Open a pull request and merge it. Render builds a new image from `main`
(the `Dockerfile` copies `data/chunks.json`), which takes a few minutes.

Check in the Render dashboard, under **Events**, that a deploy for your merge
commit started within about a minute and ends with "Deploy live". An automatic
deploy has no "by you" next to it. If no deploy appears, Render didn't hear
about the merge: start one with **Manual Deploy → Deploy latest commit**, and
see "If something goes wrong" below.

### 7. Check the live page

Open https://redi-chatbot.onrender.com and ask one question about a changed
page. The answer should use the new content and link to the page.

## If something goes wrong

- **Undo an ingestion before committing:**
  `git checkout data/chunks.json` restores the last committed chunks.
- **The evaluation got worse:** don't merge. Look at which questions changed
  in `docs/task8_results.md` and which pages the change summary listed;
  usually a page lost text or changed its layout. Write the finding down in
  `docs/task8_findings.md`.
- **The live page still shows old answers:** check in the Render dashboard
  that the deploy for your merge finished. If merges never start a deploy,
  Render isn't connected to GitHub: until 2026-11-23 the Render GitHub app
  wasn't installed, so only manual deploys ran, and the live page stayed on
  an old version for three weeks without any error. The fix: install the app
  (Render → Account Settings → Git Deployment Credentials → GitHub, access to
  `ReDi-Chatbot`) and check that the service's **Repository** shows
  `ShiriSalman / ReDi-Chatbot`, not a public URL.
- **Which version is live?** Compare the live script with the one on `main`;
  they should be the same:
  https://redi-chatbot.onrender.com/static/js/chat.js and
  `static/js/chat.js`.

## Limits

- **No automatic updates.** Someone has to run this routine (automatic
  re-crawling is after the MVP).
- **No PDF reader.** Documents from ReDI staff can't be ingested yet; only
  web pages can. Until then, ask whether the content is on a public page
  (as with the Applicant Hub).
- **Pages are cleaned automatically.** A new website layout can make the
  cleaner keep menus or drop text; the change summary is the first place
  where that shows.
