# Tests for citation and sourcing behavior, written from specs/task5_citation_sourcing.md.
# They call collect_citations, which builds the source list the web app returns as "sources";
# the page displays it (static/js/chat.js). A fake generate function stands in for the model.
import pytest

from citations import collect_citations
from grounding import NOT_COVERED_MARKER, answer_question

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


def fake_generate(answer):
    """A stand-in for the model that records its prompts and always gives the same answer."""
    def generate(prompt):
        generate.prompts.append(prompt)
        return answer

    generate.prompts = []
    return generate


# AC1: Answer with one supporting source
class TestOneSource:
    def test_one_source_gives_its_title_and_url(self):
        assert collect_citations([make_chunk()]) == [{"title": "FAQ", "url": FAQ_URL}]

    def test_chunk_text_is_not_part_of_a_citation(self):
        chunk = make_chunk(text="All our courses are free of charge for every learner.")

        citation = collect_citations([chunk])[0]

        assert set(citation) == {"title", "url"}
        assert chunk["text"] not in citation.values()

    def test_citations_come_from_metadata_not_from_the_answer_text(self):
        # Even if the model writes a URL into its answer, only metadata URLs become citations
        chunks = [make_chunk(text="All our courses are free of charge for every learner.")]
        generate = fake_generate("See https://made-up.example/courses for details.")

        result = answer_question("Are ReDI courses free?", chunks, generate)

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


# AC4: No relevant content means no citations
class TestNoRelevantContent:
    def test_no_sources_give_no_citations(self):
        assert collect_citations([]) == []

    def test_end_to_end_the_model_is_not_called_and_no_links_are_given(self):
        generate = fake_generate("Invented answer with https://made-up.example")
        chunks = [make_chunk(text="All our courses are free of charge for every learner.")]

        result = answer_question("What will the weather be like in Tokyo tomorrow?", chunks, generate)

        assert generate.prompts == []
        assert collect_citations(result.sources) == []


# AC5: Partly supported answers keep their sources
class TestPartialAnswer:
    def test_partial_answer_keeps_available_sources(self):
        chunks = [make_chunk(text="All our courses are free of charge for every learner.")]
        generate = fake_generate(
            f"{NOT_COVERED_MARKER} ReDI courses are free of charge. "
            "The available sources do not say how long every course lasts."
        )

        # 2 of the 4 question words are in the chunk, so it passes the gate and the model is asked
        result = answer_question("Are ReDI courses free, and how long?", chunks, generate)

        assert len(generate.prompts) == 1
        assert result.enough_information is False
        assert collect_citations(result.sources) == [{"title": "FAQ", "url": FAQ_URL}]


# AC6: Conflicting pages are both listed
class TestConflictingSources:
    def test_conflicting_sources_are_both_listed(self):
        sources = [
            make_chunk(text="The deadline is 1 March.", url=FAQ_URL, title="FAQ"),
            make_chunk(text="The deadline is 15 February.", url=APPLY_URL, title="Apply"),
        ]

        citations = collect_citations(sources)

        assert citations == [{"title": "FAQ", "url": FAQ_URL}, {"title": "Apply", "url": APPLY_URL}]


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

        citations = collect_citations(sources)

        # The valid page keeps its link; the invalid one gets no URL, and none is guessed for it
        assert citations == [{"title": "FAQ", "url": FAQ_URL}, {"title": "Old page", "url": None}]

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


# Missing titles
class TestTitles:
    @pytest.mark.parametrize("missing_title", [None, ""])
    def test_missing_title_uses_neutral_label(self, missing_title):
        citations = collect_citations([make_chunk(title=missing_title)])

        assert citations == [{"title": "ReDI source", "url": FAQ_URL}]
