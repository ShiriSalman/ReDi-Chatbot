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
    Fetch -->|ok| Clean["clean the HTML<br/>remove nav, header, footer, scripts"]
    Clean --> Chunk["split into pieces<br/>of max. 500 characters"]
    Chunk --> Empty{"any text?"}
    Empty -->|No| NoContent["report: no content"]
    Empty -->|Yes| Save["replace its old chunks<br/>each chunk keeps url, title,<br/>category, language, last_updated"]
    Save --> Out[("data/chunks.json")]
```

A failed fetch keeps the old chunks, so a short outage of the ReDI website loses nothing.

## 3. Answering a question

```mermaid
flowchart TD
    Q["Visitor asks a question"] --> Check{"empty or over<br/>500 characters?"}
    Check -->|Yes| Err["error message"]
    Check -->|No| Talk{"small talk?<br/>hi, thanks, bye"}
    Talk -->|Yes| Fixed["fixed friendly reply<br/>no sources, no model call"]
    Talk -->|No| Retrieve["find matching chunks<br/>BM25 keyword search, top 5"]
    Retrieve --> Found{"enough matching<br/>words found?"}
    Found -->|No| Fallback["'not enough information'<br/>+ link to ReDI contact page<br/>no model call"]
    Found -->|Yes| Prompt["build the prompt:<br/>rules + chunks + question"]
    Prompt --> Model["Gemini writes the answer<br/>demo text without API key"]
    Model --> Clean["clean the answer:<br/>remove URLs and source lists"]
    Clean --> Covered{"model wrote<br/>[NOT COVERED]?"}
    Covered -->|No| Answer["answer + source links"]
    Covered -->|Yes| Partial["answer + source links<br/>+ link to ReDI contact page"]
```

The source links below the answer always come from the chunks' metadata, never from the
model. That is why the code removes every URL the model writes: it could be invented.

## Where each step lives

| Step | File |
|---|---|
| Run the ingestion | `src/run_ingestion.py` |
| Fetch a page | `src/fetching.py` |
| Clean and chunk | `src/ingestion.py` |
| Web page and API | `src/app.py`, `templates/chat.html`, `static/js/chat.js` |
| Search, prompt, cleaning the answer | `src/grounding.py` |
| Gemini connection, demo mode | `src/llm.py` |
| Source links | `src/citations.py` |
