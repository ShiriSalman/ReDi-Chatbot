# Tests for citation and sourcing behavior, written from specs/task5_citation_sourcing.md.
# src/citations.py does not exist yet, so every test fails until it is written.
# The tests use fixed AnswerResult objects or a fake generate function, so no real model is called.
import pytest

from citations import collect_citations, format_answer
from grounding import NOT_ENOUGH_INFO, AnswerResult, answer_question

FAQ_URL = "https://www.redi-school.org/faq"
APPLY_URL = "https://www.redi-school.org/apply"
MUNICH_URL = "https://www.redi-school.org/munich"


def make_chunk(text="Some ReDI content.", **overrides):
    chunk = {
        "text": text,
        "url": FAQ_URL,
        "title": "FAQ",
        "category": "Applications",
        "language": "en",
        "last_updated": "unavailable",
    }
    chunk.update(overrides)
    return chunk


def make_result(text="Yes, ReDI courses are free of charge.", sources=None):
    return AnswerResult(text=text, enough_information=True, sources=sources or [make_chunk()])


def sources_section(output):
    """The part of the formatted answer after the Sources label."""
    assert "**Sources**" in output
    return output.split("**Sources**", 1)[1]


# AC1: Answer with one supporting source
class TestOneSource:
    def test_one_source_is_displayed_with_title_and_url(self):
        output = format_answer(make_result())

        assert "[FAQ](https://www.redi-school.org/faq)" in sources_section(output)

    def test_the_answer_comes_first_and_sources_after_it(self):
        output = format_answer(make_result(text="Yes, ReDI courses are free of charge."))

        assert output.startswith("Yes, ReDI courses are free of charge.")
        assert output.index("Yes, ReDI courses") < output.index("**Sources**")

    def test_chunk_text_is_not_shown_as_a_citation(self):
        chunk = make_chunk(text="All our courses are free of charge for every learner.")

        output = format_answer(make_result(sources=[chunk]))

        assert chunk["text"] not in output

    def test_citations_come_from_metadata_not_from_the_answer_text(self):
        # Even if the model writes a URL into its answer, only metadata URLs become citations
        result = make_result(text="See https://made-up.example/courses for details.")

        output = format_answer(result)

        assert "made-up.example" not in sources_section(output)
        assert [c["url"] for c in collect_citations(result.sources)] == [FAQ_URL]


# AC2: Several chunks from the same page give one citation
class TestDuplicates:
    def test_duplicate_chunks_from_same_page_show_one_citation(self):
        sources = [make_chunk(text="First part."), make_chunk(text="Second part.")]

        citations = collect_citations(sources)

        assert citations == [{"title": "FAQ", "url": FAQ_URL}]

    def test_a_trailing_slash_is_still_the_same_page(self):
        sources = [make_chunk(url=FAQ_URL), make_chunk(url=FAQ_URL + "/")]

        citations = collect_citations(sources)

        assert len(citations) == 1
        # The original URL of the first chunk is kept for display
        assert citations[0]["url"] == FAQ_URL

    def test_the_formatted_answer_lists_the_page_once(self):
        sources = [make_chunk(text="First part."), make_chunk(text="Second part.")]

        output = format_answer(make_result(sources=sources))

        assert sources_section(output).count(FAQ_URL) == 1


# AC3: Several pages are listed in the order they first appear
class TestMultiplePages:
    def test_multiple_pages_keep_first_seen_order(self):
        sources = [
            make_chunk(url=MUNICH_URL, title="ReDI Munich"),
            make_chunk(url=FAQ_URL, title="FAQ"),
            make_chunk(url=MUNICH_URL, title="ReDI Munich"),
            make_chunk(url=APPLY_URL, title="Apply"),
        ]

        citations = collect_citations(sources)

        assert [c["url"] for c in citations] == [MUNICH_URL, FAQ_URL, APPLY_URL]

    def test_every_page_is_linked_in_the_sources_section(self):
        sources = [make_chunk(url=MUNICH_URL, title="ReDI Munich"), make_chunk(url=FAQ_URL, title="FAQ")]

        section = sources_section(format_answer(make_result(sources=sources)))

        assert "[ReDI Munich](https://www.redi-school.org/munich)" in section
        assert "[FAQ](https://www.redi-school.org/faq)" in section
        assert section.index("ReDI Munich") < section.index("FAQ")


# AC4: No relevant content means no citations
class TestNoRelevantContent:
    def test_no_relevant_content_has_no_citations(self):
        result = AnswerResult(text=NOT_ENOUGH_INFO, enough_information=False, sources=[])

        output = format_answer(result)

        assert output == NOT_ENOUGH_INFO
        assert "Sources" not in output
        assert "http" not in output

    def test_end_to_end_the_model_is_not_called_and_no_links_are_shown(self):
        prompts = []

        def generate(prompt):
            prompts.append(prompt)
            return "Invented answer with https://made-up.example"

        chunks = [make_chunk(text="All our courses are free of charge for every learner.")]
        result = answer_question("What will the weather be like in Tokyo tomorrow?", chunks, generate)

        assert prompts == []
        assert format_answer(result) == NOT_ENOUGH_INFO


# AC5: Partly supported answers keep their sources
class TestPartialAnswer:
    def test_partial_answer_keeps_available_sources(self):
        partial = "ReDI courses are free of charge. The available sources do not say how long every course lasts."

        output = format_answer(make_result(text=partial))

        assert output.startswith(partial)
        assert "[FAQ](https://www.redi-school.org/faq)" in sources_section(output)


# AC6: Conflicting pages are both listed
class TestConflictingSources:
    def test_conflicting_sources_are_both_listed(self):
        sources = [
            make_chunk(text="The deadline is 1 March.", url=FAQ_URL, title="FAQ"),
            make_chunk(text="The deadline is 15 February.", url=APPLY_URL, title="Apply"),
        ]
        answer = "The sources disagree: the FAQ says 1 March, the Apply page says 15 February."

        section = sources_section(format_answer(make_result(text=answer, sources=sources)))

        assert "[FAQ](https://www.redi-school.org/faq)" in section
        assert "[Apply](https://www.redi-school.org/apply)" in section


# AC7: Missing or invalid URLs never become links
class TestInvalidUrls:
    @pytest.mark.parametrize("bad_url", [
        None,
        "",
        "www.redi-school.org/faq",
        "ftp://www.redi-school.org/faq",
        "javascript:alert(1)",
    ])
    def test_missing_or_invalid_url_is_not_a_link(self, bad_url):
        sources = [make_chunk(url=FAQ_URL, title="FAQ"), make_chunk(url=bad_url, title="Old page")]

        output = format_answer(make_result(sources=sources))

        # The valid page is still linked
        assert "[FAQ](https://www.redi-school.org/faq)" in output
        # The invalid one is never a clickable link and no URL is guessed for it
        assert "[Old page](" not in output
        if bad_url:
            assert f"]({bad_url})" not in output

    def test_a_chunk_without_a_url_key_has_no_url(self):
        chunk = make_chunk(title="Old page")
        del chunk["url"]

        assert collect_citations([chunk]) == [{"title": "Old page", "url": None}]

    def test_http_and_https_urls_are_both_valid(self):
        sources = [
            make_chunk(url="http://www.redi-school.org/faq", title="FAQ"),
            make_chunk(url=APPLY_URL, title="Apply"),
        ]

        urls = [c["url"] for c in collect_citations(sources)]

        assert urls == ["http://www.redi-school.org/faq", APPLY_URL]


# Missing titles and metadata treated as data
class TestTitles:
    @pytest.mark.parametrize("missing_title", [None, ""])
    def test_missing_title_uses_neutral_label(self, missing_title):
        citations = collect_citations([make_chunk(title=missing_title)])

        assert citations == [{"title": "ReDI source", "url": FAQ_URL}]

    def test_a_title_cannot_create_its_own_link(self):
        # Source metadata is data: brackets in a title must not turn into a second link
        sneaky = make_chunk(title="FAQ](https://evil.example) [Click")

        output = format_answer(make_result(sources=[sneaky]))

        assert "](https://evil.example)" not in output
        assert FAQ_URL in output
