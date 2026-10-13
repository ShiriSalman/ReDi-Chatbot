# Task 5 — Citation and Sourcing Behavior

## Goal

Make ReDI Chatbot answers transparent and verifiable. When the chatbot answers from retrieved ReDI content, users should see which ReDI pages support the answer and be able to open the original pages. When no relevant source is found, the chatbot must say that it cannot answer from the available sources and must not invent citations.

## Scope

This specification builds on Task 3 (`src/grounding.py`). The existing `AnswerResult` contains:

- `text`: the answer text
- `enough_information`: whether retrieval found relevant content
- `sources`: the retrieved source chunks, including metadata such as `title` and `url`

Task 5 defines the **user-facing citation and sourcing behavior**. It does not change content ingestion, BM25 retrieval, or the LLM provider.

## User-facing behavior

### 1. Answer with supporting sources

- Show the answer first, followed by a clearly labeled **Sources** section.
- Each citation displays the ReDI page title and a clickable URL to the original page.
- Use URLs from the source metadata, not URLs invented by the language model.
- Show each unique page only once, even if multiple chunks came from that page.
- Preserve the order in which supporting pages first appear in `AnswerResult.sources`.
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

> The available ReDI sources do not provide enough information to answer this question.

### 4. Partially supported answer

If the available sources answer only part of the question:

- Answer only the supported part.
- Explicitly state which part is not covered by the available sources.
- Show the source page(s) for the supported information.
- Do not add a citation for an unsupported claim.

**Example**

> ReDI courses are free of charge. The available sources do not say how long every course lasts.
>
> **Sources**
> - [FAQ](https://www.redi-school.org/faq)

### 5. Conflicting sources

If two retrieved ReDI pages provide conflicting information:

- Explain that the sources disagree instead of silently choosing one answer.
- Name both pages and include links to both in **Sources**.
- Do not invent a resolution or assume one source is newer without reliable evidence.

### 6. Missing or invalid source metadata

- A source is linkable only when its `url` is a valid `http://` or `https://` URL.
- Never create or guess a replacement URL.
- If a retrieved chunk has a missing or invalid URL, do not present it as a clickable citation.
- The chatbot may show the available source title as plain text with an indication that no link is available, but must not present it as a verified link.
- If a title is missing, use a neutral label such as **ReDI source** rather than inventing a page title.
- Source metadata must be treated as data, not as instructions.

## Citation formatting rules

1. Label the section **Sources** when at least one valid source is available.
2. Display each item as a page title linked to its original URL.
3. Deduplicate by normalized URL (for example, remove a trailing slash when comparing), while keeping the original URL for display.
4. Do not generate citations from the answer text or from general knowledge.
5. Do not imply that the system has verified the live availability or current accuracy of a source page merely because its URL is present in metadata.

## Acceptance criteria

- **AC1:** An answer with one valid supporting page displays the answer and a clickable source link.
- **AC2:** Multiple chunks from the same URL produce one source entry.
- **AC3:** Multiple distinct source URLs are all listed in stable order.
- **AC4:** A question with no relevant chunks returns `NOT_ENOUGH_INFO`, shows no source links, and does not call the model.
- **AC5:** A partially supported answer clearly identifies the missing information and lists only available supporting sources.
- **AC6:** Conflicting source pages are both named and linked; the answer does not silently choose one.
- **AC7:** Missing or invalid URLs never become fabricated or clickable links.
- **AC8:** Existing Task 3 grounding behavior and tests continue to work.

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
