# Task 2 – Content Ingestion Pipeline Specification

## Goal

Build a reliable ingestion pipeline that processes the approved ReDI sources
defined in Task 1 and converts their content into clean, structured chunks
that can later be used for retrieval and answer generation.

The pipeline must preserve the source information for every chunk so that
answers can be cited later.

---

## Scenario 1 – Ingest an approved web source

**Given** an approved ReDI webpage is listed in the content scope  
**When** the ingestion pipeline processes the webpage  
**Then** the relevant textual content should be extracted  
**And** the content should be stored in a structured form  
**And** the source URL should be preserved.

---

## Scenario 2 – Do not ingest sources outside the approved scope

**Given** a webpage is not included in the approved content scope  
**When** the ingestion pipeline receives the webpage  
**Then** the webpage should not be ingested  
**And** the pipeline should record that the source was skipped.

---

## Scenario 3 – Clean extracted website content

**Given** an approved webpage contains relevant content and unnecessary
website elements  
**When** the content is processed  
**Then** unnecessary elements such as navigation, footer text and repeated
page elements should be removed  
**And** the relevant textual content should remain.

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

**Given** an approved source provides a last-updated date  
**When** the source is ingested  
**Then** the last-updated date should be stored with its metadata.

**Given** an approved source does not provide a last-updated date  
**When** the source is ingested  
**Then** the metadata should indicate that the last-updated date is unavailable.

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
**And** the failure reason should be logged.

---

## Scenario 9 – Handle a source with no usable content

**Given** an approved source is accessible but contains no usable textual content  
**When** the ingestion pipeline processes the source  
**Then** no empty content chunks should be stored  
**And** the source should be reported as having no usable content.

---

## Scenario 10 – Produce an ingestion report

**Given** multiple approved sources are processed  
**When** the ingestion run is complete  
**Then** a report should show which sources were successfully ingested  
**And** which sources were skipped  
**And** which sources failed.