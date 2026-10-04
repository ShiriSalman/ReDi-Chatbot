# Tests for the script that runs the ingestion: read data/sources.json,
# ingest the sources and save the chunks to a JSON file.
# src/run_ingestion.py does not exist yet, so every test fails until it is written.
# The tests use pytest's tmp_path, so they never touch the real data/ folder.
import json

from run_ingestion import format_report, run

PAGE_HTML = "<html><body><main><p>All our courses are free.</p></main></body></html>"

SOURCES = [
    {
        "url": "https://www.redi-school.org/faq",
        "title": "FAQ",
        "category": "Applications",
        "language": "en",
        "audience": "All",
        "include": "Yes",
        "notes": "",
    },
    {
        "url": "https://www.redi-school.org/redi-school-malmo",
        "title": "ReDI School Malmö",
        "category": "Locations",
        "language": "en",
        "audience": "All",
        "include": "Yes",
        "notes": "",
    },
    {
        "url": "https://www.redi-school.org/blog",
        "title": "Blog",
        "category": None,
        "language": None,
        "audience": None,
        "include": "No",
        "notes": "News that goes out of date quickly.",
    },
]


def write_sources(tmp_path, sources=SOURCES):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(sources), encoding="utf-8")
    return path


def read_chunks(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_ok(url):
    return {"html": PAGE_HTML, "last_updated": None}


def test_saves_the_chunks_of_the_included_sources(tmp_path):
    sources_path = write_sources(tmp_path)
    chunks_path = tmp_path / "chunks.json"

    run(sources_path, chunks_path, fetch=fetch_ok)

    chunks = read_chunks(chunks_path)
    assert {chunk["url"] for chunk in chunks} == {
        "https://www.redi-school.org/faq",
        "https://www.redi-school.org/redi-school-malmo",
    }


def test_keeps_non_english_characters_readable(tmp_path):
    chunks_path = tmp_path / "chunks.json"

    run(write_sources(tmp_path), chunks_path, fetch=fetch_ok)

    assert "ReDI School Malmö" in chunks_path.read_text(encoding="utf-8")


def test_returns_the_report(tmp_path):
    result = run(write_sources(tmp_path), tmp_path / "chunks.json", fetch=fetch_ok)

    assert result.report["skipped"] == ["https://www.redi-school.org/blog"]
    assert len(result.report["ingested"]) == 2


# Scenario 7: Re-ingest an existing source
def test_a_second_run_creates_no_duplicates(tmp_path):
    sources_path = write_sources(tmp_path)
    chunks_path = tmp_path / "chunks.json"

    run(sources_path, chunks_path, fetch=fetch_ok)
    first = read_chunks(chunks_path)
    run(sources_path, chunks_path, fetch=fetch_ok)
    second = read_chunks(chunks_path)

    assert len(second) == len(first)


# Scenario 8: Handle an unavailable source
def test_keeps_the_saved_chunks_of_a_source_that_fails_on_the_next_run(tmp_path):
    sources_path = write_sources(tmp_path)
    chunks_path = tmp_path / "chunks.json"
    run(sources_path, chunks_path, fetch=fetch_ok)

    def fetch_faq_down(url):
        if url == "https://www.redi-school.org/faq":
            raise ConnectionError("Timeout")
        return fetch_ok(url)

    run(sources_path, chunks_path, fetch=fetch_faq_down)

    urls = {chunk["url"] for chunk in read_chunks(chunks_path)}
    assert "https://www.redi-school.org/faq" in urls


# Scenario 10: Produce an ingestion report
def test_format_report_shows_the_counts_and_the_failure_reasons():
    report = {
        "ingested": ["https://www.redi-school.org/faq"],
        "skipped": ["https://www.redi-school.org/blog"],
        "failed": [{"url": "https://www.redi-school.org/broken", "reason": "ConnectionError: 404"}],
        "no_content": [],
    }

    text = format_report(report)

    assert "Ingested: 1" in text
    assert "Skipped: 1" in text
    assert "Failed: 1" in text
    assert "No content: 0" in text
    assert "https://www.redi-school.org/broken" in text
    assert "ConnectionError: 404" in text
