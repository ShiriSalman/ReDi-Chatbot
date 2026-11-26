# Tests for the content ingestion pipeline, written from specs/task2_content_ingestion.md.
# The fetch function is passed in, so the tests never touch the network.
import copy
import json
from pathlib import Path

import pytest

import ingestion
from ingestion import (
    MAX_CHUNK_CHARS,
    chunk_text,
    clean_html,
    course_list_chunks,
    ingest,
    section_chunks,
    summarize_report,
)

PAGE_HTML = """
<html>
  <head><title>Course Finder</title><style>body { color: red; }</style></head>
  <body>
    <header>ReDI School logo</header>
    <nav>Home | Courses | Contact</nav>
    <main>
      <h1>Course Finder</h1>
      <p>All our courses are free.</p>
      <p>Classes take place on Tuesday and Thursday evenings.</p>
    </main>
    <footer>Imprint | Data Privacy Policy</footer>
    <script>trackVisitor();</script>
  </body>
</html>
"""

# A page that only has navigation and footer, no usable text
EMPTY_PAGE_HTML = """
<html><body>
  <nav>Home | Courses | Contact</nav>
  <footer>Imprint | Data Privacy Policy</footer>
</body></html>
"""


def make_source(**overrides):
    source = {
        "url": "https://www.redi-school.org/course-finder",
        "title": "Course Finder",
        "category": "Courses",
        "language": "en",
        "include": "Yes",
    }
    source.update(overrides)
    return source


def fake_fetch(html=PAGE_HTML, last_updated=None):
    """Returns a fetch function that gives the same page for every URL and records the calls."""
    calls = []

    def fetch(url):
        calls.append(url)
        return {"html": html, "last_updated": last_updated}

    fetch.calls = calls
    return fetch


def chunks_for(result, url):
    return [chunk for chunk in result.chunks if chunk["url"] == url]


# Scenario 1: Ingest an approved web source
class TestIngestApprovedSource:
    def test_extracts_the_text_and_keeps_the_url(self):
        source = make_source()

        result = ingest([source], fetch=fake_fetch())

        chunks = chunks_for(result, source["url"])
        assert len(chunks) >= 1
        all_text = " ".join(chunk["text"] for chunk in chunks)
        assert "All our courses are free." in all_text

    def test_stores_each_chunk_as_a_dictionary_with_text(self):
        result = ingest([make_source()], fetch=fake_fetch())

        for chunk in result.chunks:
            assert isinstance(chunk, dict)
            assert isinstance(chunk["text"], str)


# Scenario 2: Do not ingest sources outside the approved scope
class TestSourcesOutsideScope:
    def test_does_not_fetch_or_store_a_source_that_is_not_approved(self):
        excluded = make_source(url="https://www.redi-school.org/blog", include="No")
        fetch = fake_fetch()

        result = ingest([excluded], fetch=fetch)

        assert fetch.calls == []
        assert chunks_for(result, excluded["url"]) == []

    def test_records_the_source_as_skipped(self):
        excluded = make_source(url="https://www.redi-school.org/blog", include="No")

        result = ingest([excluded], fetch=fake_fetch())

        assert excluded["url"] in result.report["skipped"]

    def test_removes_saved_chunks_of_a_source_that_is_no_longer_approved(self):
        # The blog was ingested in an earlier run and is now marked "No"
        old_chunk = {
            "url": "https://www.redi-school.org/blog",
            "title": "Blog",
            "category": "About ReDI",
            "language": "en",
            "last_updated": "unavailable",
            "text": "Join our open house next Thursday!",
        }
        excluded = make_source(url="https://www.redi-school.org/blog", include="No")

        result = ingest([excluded], fetch=fake_fetch(), existing_chunks=[old_chunk])

        assert chunks_for(result, excluded["url"]) == []


# Scenario 3: Clean extracted website content
class TestCleanHtml:
    def test_removes_navigation_header_and_footer(self):
        text = clean_html(PAGE_HTML)

        assert "Home | Courses | Contact" not in text
        assert "ReDI School logo" not in text
        assert "Imprint | Data Privacy Policy" not in text

    def test_removes_scripts_and_styles(self):
        text = clean_html(PAGE_HTML)

        assert "trackVisitor" not in text
        assert "color: red" not in text

    def test_keeps_the_relevant_text(self):
        text = clean_html(PAGE_HTML)

        assert "All our courses are free." in text
        assert "Classes take place on Tuesday and Thursday evenings." in text

    # specs/task8_add_applicant_hub_source.md, AC1: GitBook puts its assistant and the table of
    # contents in <aside>, so every hub page started with the whole course list
    def test_removes_sidebars_and_keeps_the_main_text(self):
        html = """
        <html><body>
          <aside>GitBook Assistant | Python | Data Analytics | Cybersecurity</aside>
          <main><p>You must be at least 18 years old to join ReDI School.</p></main>
        </body></html>
        """

        text = clean_html(html)

        assert "GitBook Assistant" not in text
        assert "Data Analytics" not in text
        assert "You must be at least 18 years old to join ReDI School." in text

    # AC7: GitBook adds the page outline after <main>, and the ReDI website a "0" before it
    def test_uses_only_the_main_content_when_the_page_has_one(self):
        html = """
        <html><body>
          <div>0</div>
          <main><p>All ReDI School courses are 100% free.</p></main>
          <div><ul><li>What is the course about?</li><li>How to apply?</li></ul></div>
        </body></html>
        """

        text = clean_html(html)

        assert text == "All ReDI School courses are 100% free."


# Scenario 4: Split content into chunks
class TestChunkText:
    LONG_TEXT = " ".join(f"Sentence number {i} about ReDI courses." for i in range(200))

    def test_splits_long_text_into_several_chunks_within_the_size_limit(self):
        chunks = chunk_text(self.LONG_TEXT, max_chars=500)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 500

    def test_no_chunk_is_empty(self):
        chunks = chunk_text(self.LONG_TEXT + "\n\n\n   \n\n", max_chars=500)

        for chunk in chunks:
            assert chunk.strip() != ""

    def test_keeps_all_of_the_text(self):
        chunks = chunk_text(self.LONG_TEXT, max_chars=500)

        joined = " ".join(chunks)
        assert "Sentence number 0 about" in joined
        assert "Sentence number 199 about" in joined

    def test_short_text_stays_one_chunk(self):
        assert chunk_text("All our courses are free.", max_chars=500) == [
            "All our courses are free."
        ]


# Scenario 5: Preserve source information for every chunk
class TestSourceInformation:
    def test_every_chunk_has_url_title_category_and_language(self):
        source = make_source(language="en", category="Courses")

        result = ingest([source], fetch=fake_fetch())

        assert result.chunks
        for chunk in result.chunks:
            assert chunk["url"] == source["url"]
            assert chunk["title"] == source["title"]
            assert chunk["category"] == source["category"]
            assert chunk["language"] == source["language"]


# Scenario 6: Preserve freshness information
class TestFreshness:
    def test_stores_the_last_updated_date_when_the_source_has_one(self):
        result = ingest([make_source()], fetch=fake_fetch(last_updated="2026-03-15"))

        for chunk in result.chunks:
            assert chunk["last_updated"] == "2026-03-15"

    def test_marks_the_date_as_unavailable_when_the_source_has_none(self):
        result = ingest([make_source()], fetch=fake_fetch(last_updated=None))

        for chunk in result.chunks:
            assert chunk["last_updated"] == "unavailable"


# Scenario 7: Re-ingest an existing source

class TestReIngest:

    def test_replaces_old_content_without_creating_duplicates(self):
        source = make_source()

        # First ingestion
        old_chunks = ingest(
            [source],
            fetch=fake_fetch()
        ).chunks

        # The website content changes
        new_html = PAGE_HTML.replace(
            "All our courses are free.",
            "Courses are still free in 2027."
        )

        # Re-ingest the same source
        result = ingest(
            [source],
            fetch=fake_fetch(html=new_html),
            existing_chunks=old_chunks
        )

        chunks = chunks_for(result, source["url"])
        all_text = " ".join(chunk["text"] for chunk in chunks)

        # New content is stored
        assert "Courses are still free in 2027." in all_text

        # Old content is removed
        assert "All our courses are free." not in all_text

        # No chunk is stored twice
        texts = [chunk["text"] for chunk in chunks]
        assert len(texts) == len(set(texts))

    def test_keeps_chunks_of_other_sources(self):
        other_chunk = {
            "url": "https://www.redi-school.org/contact",
            "title": "Contact",
            "category": "Contact",
            "language": "en",
            "last_updated": "unavailable",
            "text": "Write to us.",
        }

        # Re-ingest one source while another source is already stored
        result = ingest(
            [make_source()],
            fetch=fake_fetch(),
            existing_chunks=[other_chunk]
        )

        # The other source is not lost
        assert other_chunk in result.chunks


# Scenario 8: Handle an unavailable source
class TestUnavailableSource:
    def test_records_the_failure_with_its_reason_and_continues(self):
        good = make_source(url="https://www.redi-school.org/faq")
        broken = make_source(url="https://www.redi-school.org/broken")

        def fetch(url):
            if url == broken["url"]:
                raise ConnectionError("404 Not Found")
            return {"html": PAGE_HTML, "last_updated": None}

        result = ingest([broken, good], fetch=fetch)

        failures = result.report["failed"]
        assert len(failures) == 1
        assert failures[0]["url"] == broken["url"]
        assert "404" in failures[0]["reason"]
        assert chunks_for(result, broken["url"]) == []
        assert chunks_for(result, good["url"]) != []


# Scenario 9: Handle a source with no usable content
class TestNoUsableContent:
    def test_stores_no_chunks_and_reports_no_usable_content(self):
        source = make_source()

        result = ingest([source], fetch=fake_fetch(html=EMPTY_PAGE_HTML))

        assert chunks_for(result, source["url"]) == []
        assert source["url"] in result.report["no_content"]
        assert source["url"] not in result.report["ingested"]


# Scenario 10: Produce an ingestion report
class TestReport:
    def test_lists_ingested_skipped_and_failed_sources(self):
        ingested = make_source(url="https://www.redi-school.org/faq")
        skipped = make_source(url="https://www.redi-school.org/blog", include="No")
        failed = make_source(url="https://www.redi-school.org/broken")

        def fetch(url):
            if url == failed["url"]:
                raise ConnectionError("Timeout")
            return {"html": PAGE_HTML, "last_updated": None}

        result = ingest([ingested, skipped, failed], fetch=fetch)

        assert result.report["ingested"] == [ingested["url"]]
        assert result.report["skipped"] == [skipped["url"]]
        assert [f["url"] for f in result.report["failed"]] == [failed["url"]]


# Iteration: summarize the report as counts per category
class TestSummarizeReport:
    def test_counts_the_sources_in_each_category(self):
        report = {
            "ingested": ["https://www.redi-school.org/faq", "https://www.redi-school.org/course-finder"],
            "skipped": ["https://www.redi-school.org/blog"],
            "failed": [{"url": "https://www.redi-school.org/broken", "reason": "ConnectionError: 404"}],
            "no_content": [],
        }

        assert summarize_report(report) == {
            "ingested": 2,
            "skipped": 1,
            "failed": 1,
            "no_content": 0,
            "total": 4,
        }

    def test_an_empty_report_gives_zero_counts(self):
        report = {"ingested": [], "skipped": [], "failed": [], "no_content": []}

        assert summarize_report(report) == {
            "ingested": 0,
            "skipped": 0,
            "failed": 0,
            "no_content": 0,
            "total": 0,
        }

    def test_counts_match_the_lists_of_a_real_run(self):
        ingested = make_source(url="https://www.redi-school.org/faq")
        skipped = make_source(url="https://www.redi-school.org/blog", include="No")
        failed = make_source(url="https://www.redi-school.org/broken")

        def fetch(url):
            if url == failed["url"]:
                raise ConnectionError("Timeout")
            return {"html": PAGE_HTML, "last_updated": None}

        result = ingest([ingested, skipped, failed], fetch=fetch)

        summary = summarize_report(result.report)
        for key in ["ingested", "skipped", "failed", "no_content"]:
            assert summary[key] == len(result.report[key])
        assert summary["total"] == 3

    def test_does_not_change_the_report(self):
        # Other code reads the report lists, so the summary must leave them as they are
        report = {
            "ingested": ["https://www.redi-school.org/faq"],
            "skipped": [],
            "failed": [{"url": "https://www.redi-school.org/broken", "reason": "Timeout"}],
            "no_content": ["https://www.redi-school.org/empty"],
        }
        before = copy.deepcopy(report)

        summarize_report(report)

        assert report == before


# specs/task8_course_list_per_city.md: the Course Finder lists courses by name, and the ingestion
# read only 20 of 74. Its items are turned into one list per city plus an overview.
FINDER_URL = "https://www.redi-school.org/course-finder"
# Like the real page: the intro and the course cards (class "blog-item") are in one outer <article>
FINDER_HTML = """
<html><body>
  <nav>Home | Courses</nav>
  <main>
    <article class="sections">
      <h1>Find your course!</h1>
      <p>All our courses are free!</p>
      <article class="blog-item"><h2>Robotics</h2><p>Kids and Teens</p></article>
    </article>
  </main>
</body></html>
"""


def course(title, categories, updated_ms=1789107785592):
    return {
        "title": title,
        "categories": categories,
        # Details such as dates and times are left out, so a city's list fits into few chunks
        "excerpt": "<ul><li><p>Munich - Onsite</p></li><li><p>Tue & Thu, 19:00 - 21:00</p></li></ul>",
        "updatedOn": updated_ms,
    }


def finder_source(**overrides):
    return make_source(url=FINDER_URL, reader="course-list", **overrides)


def by_url(chunks, url):
    return [chunk for chunk in chunks if chunk["url"] == url]


class TestCourseList:
    ITEMS = [
        course("Python", ["Munich", "Data Analytics"]),
        course("Data Analytics", ["Munich", "Data Analytics"]),
        course("Cybersecurity", ["Cybersecurity", "Berlin", "Hamburg"]),
        course("Job ReDI", ["Malmö"]),
    ]

    def chunks(self, items=None):
        return course_list_chunks(finder_source(), FINDER_HTML, items or self.ITEMS)

    # AC4
    def test_the_overview_names_every_city_with_its_number_of_courses(self):
        overview = " ".join(chunk["text"] for chunk in by_url(self.chunks(), FINDER_URL))

        assert "All our courses are free!" in overview
        assert "Munich (2 courses)" in overview
        assert "Berlin (1 course)" in overview
        assert "Malmö (1 course)" in overview
        # The page's own course cards are not repeated; the lists below have every course
        assert "Robotics" not in overview
        assert "Home | Courses" not in overview

    # AC2
    def test_each_city_gets_a_list_with_a_line_per_course(self):
        munich = by_url(self.chunks(), f"{FINDER_URL}?category=Munich")

        assert len(munich) == 1
        assert munich[0]["title"] == "Course Finder – Munich"
        assert munich[0]["text"] == (
            "Courses in Munich (ReDI Course Finder, 2 courses at ReDI Munich):\n"
            "- Python (Data Analytics)\n"
            "- Data Analytics (Data Analytics)"
        )

    # AC2
    def test_a_course_in_two_cities_is_in_both_lists(self):
        chunks = self.chunks()

        for city in ["Berlin", "Hamburg"]:
            text = by_url(chunks, f"{FINDER_URL}?category={city}")[0]["text"]
            assert "- Cybersecurity (Cybersecurity)" in text

    def test_city_names_are_encoded_in_the_link(self):
        chunks = self.chunks()

        assert by_url(chunks, f"{FINDER_URL}?category=Malm%C3%B6")
        assert all(" " not in chunk["url"] for chunk in chunks)

    # AC5: the JSON titles contain HTML codes such as "&amp;"
    def test_titles_are_plain_text_and_a_course_without_topics_has_no_brackets(self):
        items = [course("Machine Learning &amp; AI", ["Munich"])]

        text = by_url(self.chunks(items), f"{FINDER_URL}?category=Munich")[0]["text"]

        assert text.endswith("\n- Machine Learning & AI")
        assert "Tue & Thu" not in text

    # AC3
    def test_a_long_list_is_split_between_lines_and_every_part_has_the_header(self):
        items = [course(f"Course number {n}", ["Munich", "Web Development"]) for n in range(30)]

        munich = by_url(self.chunks(items), f"{FINDER_URL}?category=Munich")

        assert len(munich) > 1
        for number, chunk in enumerate(munich, start=1):
            header, *lines = chunk["text"].split("\n")
            # The city is named twice: once wasn't enough to rank above the city's own page (q27, q28)
            assert header == (f"Courses in Munich (ReDI Course Finder, 30 courses at ReDI Munich, "
                              f"part {number} of {len(munich)}):")
            assert lines and all(line.startswith("- Course number ") and line.endswith(")") for line in lines)
            assert len(chunk["text"]) <= 500
        assert sum(len(chunk["text"].split("\n")) - 1 for chunk in munich) == 30

    # specs/task8_complete_city_lists.md, AC1: only the parts of a city list are marked, so
    # retrieval can bring the other parts along
    def test_only_city_list_parts_are_marked(self):
        chunks = self.chunks()

        for chunk in chunks:
            if "?category=" in chunk["url"]:
                assert chunk["list_part"] is True
            else:
                assert "list_part" not in chunk
        page = ingest([make_source()], fetch=fake_fetch()).chunks
        assert all("list_part" not in chunk for chunk in page)

    def test_chunks_keep_the_source_information_and_the_newest_update(self):
        items = [course("Python", ["Munich"], updated_ms=1700000000000),
                 course("Machine Learning", ["Munich"], updated_ms=1789107785592)]

        munich = by_url(self.chunks(items), f"{FINDER_URL}?category=Munich")[0]

        assert munich["category"] == "Courses"
        assert munich["language"] == "en"
        assert munich["last_updated"] == "2026-09-11"

    def test_ingest_reads_the_course_list_with_fetch_collection(self):
        result = ingest([finder_source()], fetch=fake_fetch(FINDER_HTML),
                        fetch_collection=lambda url: self.ITEMS)

        urls = {chunk["url"] for chunk in result.chunks}
        assert FINDER_URL in urls
        assert f"{FINDER_URL}?category=Munich" in urls
        assert result.report["ingested"] == [FINDER_URL]

    def test_ingesting_again_replaces_the_city_lists(self):
        first = ingest([finder_source()], fetch=fake_fetch(FINDER_HTML), fetch_collection=lambda url: self.ITEMS)

        second = ingest([finder_source()], fetch=fake_fetch(FINDER_HTML),
                        fetch_collection=lambda url: self.ITEMS, existing_chunks=first.chunks)

        assert len(second.chunks) == len(first.chunks)

    def test_a_course_list_marked_no_loses_its_city_lists(self):
        first = ingest([finder_source()], fetch=fake_fetch(FINDER_HTML), fetch_collection=lambda url: self.ITEMS)

        result = ingest([finder_source(include="No")], fetch=fake_fetch(), existing_chunks=first.chunks)

        assert result.chunks == []

    def test_a_failed_course_list_keeps_the_old_chunks(self):
        first = ingest([finder_source()], fetch=fake_fetch(FINDER_HTML), fetch_collection=lambda url: self.ITEMS)

        def broken(url):
            raise ConnectionError("Timeout")

        result = ingest([finder_source()], fetch=fake_fetch(FINDER_HTML), fetch_collection=broken,
                        existing_chunks=first.chunks)

        assert result.chunks == first.chunks
        assert result.report["failed"][0]["url"] == FINDER_URL

    # specs/task8_course_list_per_city.md, "Iteration: broken pagination and empty lists"
    # AC12: no items; AC13: items, but none in a city of LOCATIONS
    @pytest.mark.parametrize("items", [
        [],
        [course("Python", ["Stockholm", "Data Analytics"])],
    ], ids=["no items", "no known city"])
    def test_a_course_list_without_city_lists_keeps_the_old_chunks(self, items):
        first = ingest([finder_source()], fetch=fake_fetch(FINDER_HTML), fetch_collection=lambda url: self.ITEMS)

        result = ingest([finder_source()], fetch=fake_fetch(FINDER_HTML), fetch_collection=lambda url: items,
                        existing_chunks=first.chunks)

        assert result.chunks == first.chunks
        assert result.report["no_content"] == [FINDER_URL]
        assert result.report["ingested"] == []


# specs/task2_content_ingestion.md, "Iteration: unknown include and reader values"
class TestConfigurationErrors:
    OLD_CHUNK = {
        "url": "https://www.redi-school.org/course-finder",
        "title": "Course Finder",
        "category": "Courses",
        "language": "en",
        "last_updated": "unavailable",
        "text": "Chunk from the last run.",
    }

    # AC1
    @pytest.mark.parametrize("include", ["yes", "", None], ids=["lower case", "empty", "missing"])
    def test_an_unknown_include_value_fails_and_keeps_the_old_chunks(self, include):
        source = make_source(include=include)
        fetch = fake_fetch()

        result = ingest([source], fetch=fetch, existing_chunks=[self.OLD_CHUNK])

        assert fetch.calls == []
        assert result.chunks == [self.OLD_CHUNK]
        assert result.report["skipped"] == []
        [failure] = result.report["failed"]
        assert failure["url"] == source["url"]
        assert "include" in failure["reason"] and repr(include) in failure["reason"]

    # AC2
    def test_an_unknown_reader_fails_and_keeps_the_old_chunks(self):
        source = make_source(reader="section")
        fetch = fake_fetch()

        result = ingest([source], fetch=fetch, existing_chunks=[self.OLD_CHUNK])

        assert fetch.calls == []
        assert result.chunks == [self.OLD_CHUNK]
        [failure] = result.report["failed"]
        assert "reader" in failure["reason"] and "'section'" in failure["reason"]

    # AC3
    def test_maybe_is_skipped_like_no(self):
        result = ingest([make_source(include="Maybe")], fetch=fake_fetch(), existing_chunks=[self.OLD_CHUNK])

        assert result.report["skipped"] == [self.OLD_CHUNK["url"]]
        assert result.chunks == []

    # AC4
    def test_every_real_source_has_a_valid_include_and_reader(self):
        sources = json.loads((Path(__file__).parent.parent / "data" / "sources.json").read_text(encoding="utf-8"))

        assert {source.get("include") for source in sources} <= ingestion.INCLUDE_VALUES
        assert {source.get("reader") for source in sources} <= ingestion.READERS


# Reading a page by its sections, written from specs/task8_contact_page_sections.md.
# Like the real contact page: a heading per location, then the contact person, then the text.
CONTACT_URL = "https://www.redi-school.org/contact"
VISITING_HOURS = "Please write to us before you visit, so we can plan the visit. " * 3


def contact_section(city, person, address):
    return (
        f"<h2>{city}</h2><h3>{person}</h3>"
        f"<p>{person.split()[0].lower()}@redi-school.org</p>"
        f"<p>Visiting address: {address}</p><p>{VISITING_HOURS}</p>"
    )


CONTACT_HTML = f"""
<html><body>
  <header>ReDI School logo</header>
  <nav>Home | Courses | Contact</nav>
  <main>
    <h1>Contact us!</h1>
    {contact_section("Berlin", "Henrik Schober", "Karl-Marx-Straße 71, 12043 Berlin")}
    {contact_section("Munich", "Birgit Köbl", "c/o Media Design Hochschule (EG / B) Neumarkter Str. 22 81673 München")}
    {contact_section("NRW", "Takuya Furukawa", "c/o Startplatz, Speditionstraße 15A, 40221 Düsseldorf")}
  </main>
  <footer>Imprint | Data Privacy Policy</footer>
  <script>trackVisitor();</script>
</body></html>
"""


class TestSections:
    # AC1
    def test_a_location_heading_stays_with_its_address(self):
        chunks = section_chunks(CONTACT_HTML)

        [munich] = [chunk for chunk in chunks if "Neumarkter Str. 22" in chunk]
        assert munich.startswith("Munich Birgit Köbl")
        [berlin] = [chunk for chunk in chunks if "Karl-Marx-Straße 71" in chunk]
        assert berlin.startswith("Contact us! Berlin Henrik Schober")
        assert "Munich" not in berlin

    # AC2
    def test_small_sections_are_packed_together(self):
        html = "<main><h2>Berlin</h2><p>Open on Mondays.</p><h2>Munich</h2><p>Open on Tuesdays.</p></main>"

        assert section_chunks(html) == ["Berlin Open on Mondays. Munich Open on Tuesdays."]

    def test_no_chunk_is_longer_than_the_limit(self):
        chunks = section_chunks(CONTACT_HTML)

        assert len(chunks) == 3
        assert all(len(chunk) <= MAX_CHUNK_CHARS for chunk in chunks)

    # AC3
    def test_a_section_longer_than_the_limit_is_split_and_the_next_one_starts_a_new_chunk(self):
        long_text = "word " * 150  # 750 characters
        html = f"<main><h2>Long</h2><p>{long_text}</p><h2>Next</h2><p>Short text.</p></main>"

        chunks = section_chunks(html)

        assert len(chunks) == 3
        assert chunks[0].startswith("Long word")
        assert chunks[-1] == "Next Short text."
        assert all(len(chunk) <= MAX_CHUNK_CHARS for chunk in chunks)

    # AC4
    def test_navigation_footer_and_scripts_are_left_out(self):
        text = " ".join(section_chunks(CONTACT_HTML))

        for unwanted in ("ReDI School logo", "Home | Courses", "Imprint", "trackVisitor"):
            assert unwanted not in text

    # AC5
    def test_only_a_source_with_the_sections_reader_is_read_by_sections(self):
        by_sections = ingest([make_source(url=CONTACT_URL, reader="sections")], fetch=fake_fetch(CONTACT_HTML))
        as_before = ingest([make_source(url=CONTACT_URL)], fetch=fake_fetch(CONTACT_HTML))

        assert [chunk["text"] for chunk in by_sections.chunks] == section_chunks(CONTACT_HTML)
        assert [chunk["text"] for chunk in as_before.chunks] == chunk_text(clean_html(CONTACT_HTML))
        assert by_sections.chunks[0]["url"] == CONTACT_URL
