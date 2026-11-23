# How the ReDI Chatbot works

The chatbot works in two separate phases:

1. **Ingestion** (run by hand): fetch the approved ReDI pages and save them as small text
   pieces ("chunks"), each with its source URL.
2. **Answering** (every time a visitor asks): find the chunks that match the question and let
   the model answer only from them.

GitHub shows the diagrams below as pictures.

## 1. Overview

```mermaid
flowchart LR
    subgraph ingestion ["Phase 1: Ingestion (python src/run_ingestion.py)"]
        S["data/sources.json<br/>approved ReDI pages"] --> I["fetch, clean, chunk"]
        W["ReDI website"] --> I
        I --> C[("data/chunks.json<br/>text + URL + title")]
    end

    subgraph answering ["Phase 2: Answering (python src/app.py)"]
        V["Visitor<br/>chat page"] -->|question| A["Flask app<br/>/api/chat"]
        A -->|"matching chunks"| G["Gemini"]
        G -->|answer text| A
        A -->|"answer + source links"| V
    end

    C --> A
```

The model never sees the internet. It only sees the chunks the app gives it, which is how
answers stay grounded in ReDI's own information.

## 2. Ingestion: from a ReDI page to chunks

```mermaid
flowchart TD
    Start["data/sources.json"] --> Each["for each source"]
    Each --> Inc{"include = Yes?"}
    Inc -->|No| Drop["remove its old chunks<br/>report: skipped"]
    Inc -->|Yes| Fetch["fetch the page<br/>src/fetching.py"]
    Fetch -->|error| Keep["keep its old chunks<br/>report: failed"]
    Fetch -->|ok| Reader{"reader?"}
    Reader -->|none| Clean["clean the HTML<br/>remove nav, header, footer, scripts<br/>split into pieces of max. 500 characters"]
    Reader -->|sections| Sections["one piece per heading and its text<br/>(contact page)"]
    Reader -->|course-list| Courses["all courses as JSON<br/>one list per city (Course Finder)"]
    Clean --> Empty{"any text?"}
    Sections --> Empty
    Courses --> Empty
    Empty -->|No| NoContent["report: no content"]
    Empty -->|Yes| Save["replace its old chunks<br/>each chunk keeps url, title,<br/>category, language, last_updated"]
    Save --> Out[("data/chunks.json")]
    Out --> Changes["change summary:<br/>new, removed, changed, unchanged<br/>per source"]
```

A failed fetch keeps the old chunks, so a short outage of the ReDI website loses nothing.

Most pages are cut every 500 characters. Two pages are read differently, set by `"reader"`
in `data/sources.json`:

- **`sections`** (the contact page): each heading stays with its text, so "Munich" and the
  Munich street address end up in the same chunk.
- **`course-list`** (the Course Finder): the page only shows 20 courses, so all courses are
  fetched as JSON and saved as one list per city ("Which courses are there in Munich?").

At the end, the script prints which sources changed since the last run. How to update the
content step by step: [update_content.md](update_content.md).

## 3. Answering a question

```mermaid
flowchart TD
    Q["Visitor asks a question"] --> Check{"empty or over<br/>500 characters?"}
    Check -->|Yes| Err["error message"]
    Check -->|No| Talk{"small talk?<br/>hi, thanks, bye"}
    Talk -->|Yes| Fixed["fixed friendly reply<br/>no sources, no model call"]
    Talk -->|No| Words["question words:<br/>without stopwords, plurals to singular,<br/>small spelling mistakes corrected"]
    Words --> Retrieve["find matching chunks<br/>BM25 keyword search, top 5"]
    Retrieve --> Found{"enough matching<br/>words found?"}
    Found -->|No| Fallback["'not enough information'<br/>+ link to ReDI contact page<br/>no model call"]
    Found -->|Yes| Lists["a part of a city's course list<br/>brings the whole list along"]
    Lists --> Prompt["build the prompt:<br/>rules + chunks + question"]
    Prompt --> Limit{"visitor asked more than<br/>5 questions this minute?"}
    Limit -->|Yes| Wait["wait message (429)<br/>no model call"]
    Limit -->|No| Model["Gemini writes the answer<br/>demo text without API key"]
    Model -->|"Gemini's quota used up"| Busy["wait message (429)"]
    Model --> Clean["clean the answer:<br/>remove URLs and source lists"]
    Clean --> Covered{"model wrote<br/>[NOT COVERED]?"}
    Covered -->|No| Answer["answer + source links"]
    Covered -->|Yes| Partial["answer + source links<br/>+ link to ReDI contact page"]
```

The source links below the answer always come from the chunks' metadata, never from the
model. That is why the code removes every URL the model writes: it could be invented.

Some details of the search (`src/grounding.py`):

- **Spelling mistakes:** a word that is in no chunk is compared with the chunks' own words.
  One typo is corrected ("aply" → "apply"), two typos only in words of 8 to 15 letters
  ("voulenteer" → "volunteer"). A short typo of a stopword ("du" → "do") is dropped.
- **The gate:** a chunk must contain at least half of the question's words, and at least two
  of them, so one accidental word ("Write me a poem.") isn't enough.
- **Synonyms** (`SYNONYMS`) only change the ranking: a question about a "job" also scores
  chunks that say "career".

**Limits that protect the free Gemini quota** (15 requests per minute for everyone together):
each visitor can ask 5 questions per minute that reach Gemini (`src/rate_limit.py`); small talk
and questions without matching chunks don't count. When Gemini's quota is used up anyway, the
visitor gets a wait message instead of an error.

On the page, `static/js/format.js` splits the answer's lines into paragraphs and lists, and
`static/js/chat.js` builds the page elements from them with `textContent`, never with
`innerHTML`, so text from the model can't add HTML to the page.

## Where each step lives

| Step | File |
|---|---|
| Run the ingestion, change summary | `src/run_ingestion.py` |
| Fetch a page or the Course Finder's JSON | `src/fetching.py` |
| Clean and chunk, the readers | `src/ingestion.py` |
| Web page and API | `src/app.py`, `templates/chat.html`, `static/js/chat.js` |
| Answer as paragraphs and lists | `static/js/format.js` |
| Limit per visitor | `src/rate_limit.py` |
| Search, spelling, prompt, cleaning the answer | `src/grounding.py` |
| Gemini connection, demo mode | `src/llm.py` |
| Source links | `src/citations.py` |
| Task 8 evaluation | `src/run_evaluation.py` |
