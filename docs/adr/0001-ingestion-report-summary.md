# ADR 0001: Calculate the ingestion report summary separately from the report

**Status:** Accepted
**Date:** 2026-10-13

## Context

After an ingestion run, the maintainer needs to see quickly how many ReDI
sources were ingested, skipped, failed or had no usable content.

`ingest()` in `src/ingestion.py` returns an `IngestionResult`. Its `report`
holds four lists: `ingested`, `skipped` and `no_content` (lists of URLs) and
`failed` (a list of `{"url": ..., "reason": ...}`). The detailed lists already
work and are covered by tests.

The counts already appeared as printed text in `format_report()` in
`src/run_ingestion.py`, but no code or test could read them as data, and the
counting happened inside the formatting code.

Other code reads the report as it is: `format_report()` and the tests in
`tests/test_ingestion.py` and `tests/test_run_ingestion.py`. If the report's
keys or types change, that code can break without warning.

## Options considered

1. **Add a separate `summarize_report(report)` function and have
   `format_report()` use it.** The report stays unchanged, and the counting
   happens in one place.
2. **Add `summarize_report(report)` and leave `format_report()` as it is.**
   This is the smallest change, but the counts would be calculated in two
   places that could drift apart.
3. **Store the summary in `IngestionResult`, filled in by `ingest()`.** It's
   convenient for callers, but it changes the result's shape and the
   ingestion logic, which this iteration meant to leave alone.

## Decision

We chose option 1.

`summarize_report(report)` in `src/ingestion.py` returns a new dictionary with
the number of sources in each category plus `total`:

```python
{"ingested": 2, "skipped": 1, "failed": 1, "no_content": 0, "total": 4}
```

It only reads the report and never changes it. `format_report()` builds its
count lines from this summary, and its printed output stays exactly the same.

## Consequences

**Positive**

- The report's keys and types are unchanged, so existing code and tests keep
  working.
- The counts are calculated in one place and can be tested directly.
- The summary can be reused later, for example in a chatbot admin page,
  without parsing printed text.

**Negative / trade-offs**

- Callers have to call `summarize_report()` themselves. The summary is not
  stored in `IngestionResult`.
- `total` relies on every source ending up in exactly one report list. If
  `ingest()` ever records a source in two lists, `total` will be wrong. The
  test `test_counts_match_the_lists_of_a_real_run` checks this assumption.

**Verification**

- Four tests in `TestSummarizeReport` (`tests/test_ingestion.py`): counts for
  each category, an empty report, a match with a real `ingest()` run, and an
  unchanged report.
- The existing `format_report` test passes without changes, which shows the
  printed output is unchanged.
- Full suite: 46 passed.
