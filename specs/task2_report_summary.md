# Task 2 iteration – Ingestion Report Summary Specification

## Goal

Give the chatbot maintainer a quick overview of an ingestion run: how many
ReDI sources were ingested, skipped, failed or had no usable content.

The detailed report lists stay as they are. The summary is calculated from
them, so the two always agree.

---

## What this feature does

- receives an ingestion report
- counts the sources in each report category
- adds the total number of sources in the run
- leaves the report itself unchanged

---

## Out of scope

This change does not touch:

- fetching, HTML cleaning or chunking
- how chunks are stored
- the shape of `IngestionResult` and its report
- answer generation
- the chatbot UI

---

## The interface

**Input:** An ingestion report with four lists: `ingested`, `skipped`,
`failed` and `no_content`.

**Output:** The number of sources in each category, plus the total:

```python
{"ingested": 2, "skipped": 1, "failed": 1, "no_content": 0, "total": 4}
```

---

## Boundaries and failure modes

**Before:** An ingestion report with the four lists is available.

**After:** The summary is returned and the report is unchanged.

**What can go wrong:** The counts could stop matching the report lists, or
calculating the summary could change the report that other code reads.

**What happens:** The counts are always calculated from the report lists, and
the report is only read, never changed.

---

## Scenario 1 – Count the sources in each category

**Given** an ingestion report with ingested, skipped and failed sources  
**When** the report is summarized  
**Then** the summary should show the number of sources in each category  
**And** the total number of sources.

---

## Scenario 2 – Summarize an empty report

**Given** an ingestion report where every list is empty  
**When** the report is summarized  
**Then** every count should be 0  
**And** no error should occur.

---

## Scenario 3 – The summary matches a real ingestion run

**Given** an ingestion run has processed approved, excluded and unavailable sources  
**When** its report is summarized  
**Then** each count should equal the number of sources in the matching report list  
**And** the total should equal the number of sources in the run.

---

## Scenario 4 – The report is not changed

**Given** an ingestion report  
**When** the report is summarized  
**Then** the report should keep its keys, lists and values.

---

## Scenario 5 – The printed report keeps working

**Given** an ingestion run has finished  
**When** the report is printed for the maintainer  
**Then** the printed counts should come from the summary  
**And** the printed output should stay the same as before this change.

---

The decision to keep the summary separate from the report is recorded in
`docs/adr/0001-ingestion-report-summary.md`.
