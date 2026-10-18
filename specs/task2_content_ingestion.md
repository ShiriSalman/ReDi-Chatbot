# Task 2 – Content Ingestion Pipeline Specification

## Goal

Build a reliable ingestion pipeline that processes the approved ReDI sources
defined in Task 1 and converts their content into clean, structured chunks
that can later be used for retrieval and answer generation.

The pipeline must preserve the source information for every chunk so that
answers can be cited later.

## Definitions

- **Approved source:** an entry in `data/sources.json` with `include: "Yes"`
  (see Task 1). Entries marked `No` or `Maybe` are skipped.
- **Chunk:** a dict with `text`, `url`, `title`, `category`, `language` and
  `last_updated`, saved as a JSON list in `data/chunks.json`. `title`,
  `category` and `language` come from `data/sources.json`, not from the page.
- **Run:** `python src/run_ingestion.py` reads `data/sources.json`, ingests
  the sources and saves `data/chunks.json`. Chunks from earlier runs are
  kept unless this spec says they are replaced or removed.

## Out of scope

- **German-language content:** some approved English sources also contain
  German sections (for example the German section at the bottom of the FAQ).
  Detecting and removing them is not part of Task 2, so for now these
  sections are ingested like the rest of the page.
- **Dated news items:** some approved sources show dated news next to their
  stable content (for example the news on the ReDI School Denmark page).
  Detecting and removing them is not part of Task 2, so for now these items
  are ingested like the rest of the page.
- **PDFs and staff documents:** only HTML web pages are ingested (see Task 1).
  PDFs and documents from ReDI staff are deferred.

## Known limitations

Found in the spec review. They describe what the code does today and are
open for a later decision:

- **No usable content:** when a page that had content becomes empty, its
  chunks from earlier runs are kept (see Scenario 9).
- **Non-HTML responses:** a PDF or other non-HTML URL is parsed as HTML and
  can be recorded as ingested with unreadable text. There is no content-type
  check.
- **Repeated text inside the main content** (for example carousels) is not
  removed (see Scenario 3).
- **Last-updated date:** ReDI's pages currently send no `Last-Modified`
  header, so every chunk has `last_updated: "unavailable"`.

---

## Scenario 1 – Ingest an approved web source

**Given** an approved ReDI webpage is listed in the content scope  
**When** the ingestion pipeline processes the webpage  
**Then** the relevant textual content should be extracted  
**And** the content should be stored in a structured form  
**And** the source URL should be preserved.

---

## Scenario 2 – Do not ingest sources outside the approved scope

**Given** a source in `data/sources.json` is marked `No` or `Maybe`  
**When** the ingestion pipeline runs  
**Then** the page should not be fetched or ingested  
**And** chunks saved for it in earlier runs should be removed  
**And** the pipeline should record that the source was skipped.

---

## Scenario 2b – Remove sources deleted from the list

**Given** chunks of a source were saved in an earlier run  
**And** the source has since been deleted from `data/sources.json` entirely  
**When** the ingestion runs (`run()` in `src/run_ingestion.py`)  
**Then** its chunks should be removed from `data/chunks.json`.

This rule belongs to the run, not to `ingest()`: only the run knows the
complete list in `data/sources.json`. `ingest()` can be called with part of
the list and keeps the chunks of other sources (Scenario 7).

---

## Scenario 3 – Clean extracted website content

**Given** an approved webpage contains relevant content and unnecessary
website elements  
**When** the content is processed  
**Then** only the page `<body>` should be used  
**And** the HTML elements `nav`, `header`, `footer`, `script`, `style` and
`noscript` should be removed from it  
**And** the relevant textual content should remain.

Repeated text inside the main content is not removed in this task (see
Known limitations).

---

## Scenario 4 – Split content into chunks

**Given** clean text has been extracted from an approved source  
**When** the ingestion pipeline processes the text  
**Then** the text should be divided into manageable chunks  
**And** no chunk should be empty.

---

## Scenario 5 – Preserve source information for every chunk

**Given** content from an approved source has been divided into chunks  
**When** the chunks are stored  
**Then** every chunk should contain its source URL  
**And** every chunk should contain the source title  
**And** every chunk should contain its category  
**And** every chunk should contain its language.

---

## Scenario 6 – Preserve freshness information

**Given** the server sends a `Last-Modified` header for an approved page  
**When** the source is ingested  
**Then** the date should be stored in each chunk as `last_updated` in the
format `YYYY-MM-DD`.

**Given** the header is missing or cannot be read  
**When** the source is ingested  
**Then** `last_updated` should be the string `"unavailable"`.

---

## Scenario 7 – Re-ingest an existing source

**Given** a source has already been ingested  
**When** the ingestion pipeline processes the same source again  
**Then** the existing source content should be refreshed  
**And** duplicate entries should not be created.

---

## Scenario 8 – Handle an unavailable source

**Given** an approved source cannot be accessed  
**When** the ingestion pipeline attempts to process it  
**Then** the pipeline should not crash  
**And** the source should be recorded as failed  
**And** the failure reason should be recorded in the report  
**And** chunks saved for this source in earlier runs should be kept, so a
temporary outage loses nothing.

---

## Scenario 9 – Handle a source with no usable content

**Given** an approved source is accessible but contains no usable textual content  
**When** the ingestion pipeline processes the source  
**Then** no empty content chunks should be stored  
**And** the source should be reported as having no usable content  
**And** chunks saved for this source in earlier runs are kept (see Known
limitations).

---

## Scenario 10 – Produce an ingestion report

**Given** multiple approved sources are processed  
**When** the ingestion run is complete  
**Then** a report should show which sources were successfully ingested  
**And** which sources were skipped  
**And** which sources failed.