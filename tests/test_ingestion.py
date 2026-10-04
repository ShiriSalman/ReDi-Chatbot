# Tests for the content ingestion pipeline, written from specs/task2_content_ingestion.md.
# src/ingestion.py does not exist yet, so every test fails until it is written.
# The fetch function is passed in, so the tests never touch the network.
from ingestion import chunk_text, clean_html, ingest

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
