# ReDi-Chatbot
Chatbot that allows users to ask questions about ReDI School and receive clear answers based on official ReDI information with links to the relevant sources.
This repository contains the ReDI Chatbot project.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

## Update the content

Fetches the approved sources in `data/sources.json` and saves the chunks to `data/chunks.json`:

```powershell
python src/run_ingestion.py
```

## Run the chat page

```powershell
python src/app.py
```

Then open http://127.0.0.1:5000 in your browser.

No language model is connected yet, so the app runs in **demo mode**: retrieval and source links are real,
but the answer text is a placeholder that says it is not a real answer.
If `data/chunks.json` is missing, the chat answers with a "temporarily unavailable" message; run the ingestion first.

## Run the tests

```powershell
python -m pytest
```
