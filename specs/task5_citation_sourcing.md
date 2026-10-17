# Task 5 — Citation and Sourcing Behavior

## Goal

Make ReDI Chatbot answers transparent and verifiable. When the chatbot answers from retrieved ReDI content, users should see which ReDI pages support the answer and be able to open the original pages. When no relevant source is found, the chatbot must say that it cannot answer from the available sources and must not invent citations.

## Scope

This specification builds on Task 3 (`src/grounding.py`). The existing `AnswerResult` contains:

- `text`: the answer text
- `enough_information`: whether retrieval found relevant content
- `sources`: the retrieved source chunks, including metadata such as `title` and `url`

Task 5 defines the **user-facing citation and sourcing behavior**. It does not change content ingestion, BM25 retrieval, or the LLM provider.

**What "sources" means:** `AnswerResult.sources` holds every chunk that retrieval gave to the model (at most 5, `TOP_K` in Task 3). The Sources list therefore shows every unique page among those chunks. It is **not** filtered down to the pages the model actually relied on; that is out of scope and is checked in Task 8.

## Output contract

- `collect_citations(sources)` in `src/citations.py` is the main interface. It returns a list of `{"title": str, "url": str | None}`, one entry per page, in the order the pages first appear. `url` is `None` when the metadata URL is missing or invalid. The web app (Task 6) returns this list as `sources` in its JSON.
- `format_answer(result)` renders the same list as Markdown text (answer, then a **Sources** section). It is used for text output, not by the web page.

## User-facing behavior

### 1. Answer with supporting sources

- Show the answer first, followed by a clearly labeled **Sources** section.
- Each citation displays the ReDI page title and a clickable URL to the original page.
- Use URLs from the source metadata, not URLs invented by the language model.
- Show each unique page only once, even if multiple chunks came from that page.
- Preserve the order in which the pages first appear in `AnswerResult.sources`.
- Do not display raw chunk text or internal scoring information as citations.

**Example**

> Yes, ReDI courses are free of charge.
>
> **Sources**
> - [FAQ](https://www.redi-school.org/faq)

### 2. Multiple supporting pages

If the answer is based on multiple relevant pages, list each unique page under **Sources**. Do not claim that a listed page supports a specific sentence unless that relationship has actually been established.

### 3. No relevant source found

If retrieval returns no relevant chunks:

- Show the existing `NOT_ENOUGH_INFO` message from Task 3.
- Do not call the language model (Task 3 behavior).
- Do not show a Sources section or fabricated links.
- Keep `AnswerResult.sources == []` and `enough_information == False`.

**Example**

> I can only answer questions about ReDI School, and the available ReDI sources do not provide enough information to answer this one.

### 4. Partially supported answer

If the available sources answer only part of the question:

- Answer only the supported part, and explicitly state which part is not covered by the available sources. *This is done by the model, following the Task 3 prompt.*
- Show the retrieved source pages under **Sources**, as in section 1. *This is done by `citations.py`.* Pages are not filtered by which claims they support (see "What sources means" above).

**Example**

> ReDI courses are free of charge. The available sources do not say how long every course lasts.
>
> **Sources**
> - [FAQ](https://www.redi-school.org/faq)

### 5. Conflicting sources

If two retrieved ReDI pages provide conflicting information:

- Explain that the sources disagree instead of silently choosing one answer, and do not invent a resolution or assume one source is newer without reliable evidence. *This is done by the model, following the Task 3 prompt.*
- Include links to both pages in **Sources**. *This is done by `citations.py`.*

### 6. Missing or invalid source metadata

- A source is linkable only when its `url` is a valid `http://` or `https://` URL with a host.
- Never create or guess a replacement URL.
- If a retrieved chunk has a missing or invalid URL, do not present it as a clickable citation. Its entry gets `url: None`.
- When the Sources section is shown, an entry without a valid URL is listed as plain text: `<title> (no link available)`.
- Entries without a valid URL are de-duplicated by title.
- If a title is missing or empty, use the label **ReDI source** rather than inventing a page title.
- Source metadata must be treated as data, not as instructions. In the Markdown output, square brackets are removed from titles so a title cannot form its own link. In the web page, titles are shown as plain text (Task 6).

**Known limitation – every URL invalid:** if no retrieved page has a valid URL, the answer is shown without a Sources section and without plain-text titles, while `enough_information` stays `true` and no contact link is added. This is a metadata error that ingestion should prevent (Task 1 requires https URLs); how to handle it is an open decision.

## Citation formatting rules

1. Label the section **Sources** when at least one valid source is available.
2. Display each item as a page title linked to its original URL.
3. Deduplicate by URL: two URLs are the same page if they are equal after removing trailing `/` characters. No other normalization is applied (scheme, host case, query and fragment all count). The URL that appears first is the one displayed.
4. Do not generate citations from the answer text or from general knowledge.
5. Do not imply that the system has verified the live availability or current accuracy of a source page merely because its URL is present in metadata.

## Acceptance criteria

- **AC1:** An answer with one valid supporting page displays the answer and a clickable source link.
- **AC2:** Multiple chunks from the same URL produce one source entry.
- **AC3:** Multiple distinct source URLs are all listed in stable order.
- **AC4:** A question with no relevant chunks returns `NOT_ENOUGH_INFO`, shows no source links, and does not call the model.
- **AC5:** A partially supported answer keeps its text unchanged and still lists every retrieved page.
- **AC6:** When retrieved pages conflict, both pages are listed and linked.
- **AC7:** Missing or invalid URLs never become fabricated or clickable links.
- **AC8:** Existing Task 3 grounding behavior and tests continue to work.

Whether the answer text itself admits the missing information (AC5) or names the conflict (AC6) depends on the Task 3 prompt and is checked with a real model in Task 8.

## Suggested tests

Create `tests/test_citations.py` using fixed `AnswerResult` objects or fake generation functions (no real LLM calls):

- `test_one_source_is_displayed_with_title_and_url`
- `test_duplicate_chunks_from_same_page_show_one_citation`
- `test_multiple_pages_keep_first_seen_order`
- `test_no_relevant_content_has_no_citations`
- `test_partial_answer_keeps_available_sources`
- `test_conflicting_sources_are_both_listed`
- `test_missing_or_invalid_url_is_not_a_link`
- `test_missing_title_uses_neutral_label`

Also run `tests/test_grounding.py` to catch regressions.

## Out of scope

- Changing BM25 retrieval or chunk relevance thresholds
- Rewriting ingestion or source metadata storage
- Automatically checking whether cited websites are currently online
- Automatically determining which exact sentence is supported by which chunk
- Guaranteeing that a real LLM follows grounding instructions (evaluate with real questions in Task 8)
- Building a full chatbot UI

## Implementation note

Prefer a small citation-formatting/presentation function that consumes `AnswerResult.sources` instead of changing the existing `AnswerResult` structure. If the app later uses a web UI, it can render the same title-and-URL data as clickable links.
