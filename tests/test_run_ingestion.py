# Tests for the script that runs the ingestion: read data/sources.json,
# ingest the sources and save the chunks to a JSON file.
# The tests use pytest's tmp_path, so they never touch the real data/ folder.
import json
import os
from pathlib import Path

import pytest

from run_ingestion import compare_chunks, format_changes, format_report, run

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


# Scenario 2b: Remove sources deleted from the list
def test_removes_chunks_of_a_source_deleted_from_the_list(tmp_path):
    sources_path = write_sources(tmp_path)
    chunks_path = tmp_path / "chunks.json"
    run(sources_path, chunks_path, fetch=fetch_ok)

    # Malmö is deleted from sources.json entirely (not marked "No")
    without_malmo = [s for s in SOURCES if s["url"] != "https://www.redi-school.org/redi-school-malmo"]
    write_sources(tmp_path, without_malmo)
    run(sources_path, chunks_path, fetch=fetch_ok)

    urls = {chunk["url"] for chunk in read_chunks(chunks_path)}
    assert urls == {"https://www.redi-school.org/faq"}


# specs/task8_course_list_per_city.md: city lists link to the source URL plus "?category=<city>",
# so they must not count as chunks of a deleted source
def test_keeps_the_city_lists_of_a_course_list(tmp_path):
    finder = dict(SOURCES[0], url="https://www.redi-school.org/course-finder", title="Course Finder",
                  category="Courses", reader="course-list")
    chunks_path = tmp_path / "chunks.json"
    items = [{"title": "Python", "categories": ["Munich", "Data Analytics"]}]

    run(write_sources(tmp_path, [finder]), chunks_path, fetch=fetch_ok, fetch_collection=lambda url: items)

    urls = {chunk["url"] for chunk in read_chunks(chunks_path)}
    assert urls == {
        "https://www.redi-school.org/course-finder",
        "https://www.redi-school.org/course-finder?category=Munich",
    }


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


# specs/task10_update_loop.md, "Iteration: a safe chunks.json"
# AC9
def test_a_successful_run_leaves_no_temporary_file(tmp_path):
    chunks_path = tmp_path / "chunks.json"

    run(write_sources(tmp_path), chunks_path, fetch=fetch_ok)

    assert chunks_path.exists()
    assert not (tmp_path / "chunks.json.tmp").exists()


# AC10
def test_a_failed_replace_keeps_the_old_file_and_removes_the_temporary_one(tmp_path, monkeypatch):
    chunks_path = tmp_path / "chunks.json"
    chunks_path.write_text('[{"text": "old", "url": "https://www.redi-school.org/faq"}]', encoding="utf-8")
    old_content = chunks_path.read_text(encoding="utf-8")

    def broken_replace(source, target):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", broken_replace)

    with pytest.raises(OSError, match="disk full"):
        run(write_sources(tmp_path), chunks_path, fetch=fetch_ok)

    assert chunks_path.read_text(encoding="utf-8") == old_content
    assert not (tmp_path / "chunks.json.tmp").exists()


# AC11
@pytest.mark.parametrize("content", ['[{"text": "half', '{"text": "not a list"}'], ids=["half-written", "not a list"])
def test_a_broken_saved_file_stops_the_run_with_a_clear_error(tmp_path, content):
    chunks_path = tmp_path / "chunks.json"
    chunks_path.write_text(content, encoding="utf-8")

    with pytest.raises(RuntimeError, match=r"chunks\.json.*git checkout"):
        run(write_sources(tmp_path), chunks_path, fetch=fetch_ok)

    assert chunks_path.read_text(encoding="utf-8") == content


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


# specs/task10_update_loop.md: the change summary
FAQ = "https://www.redi-school.org/faq"
MUNICH = "https://www.redi-school.org/redi-school-munich"
FINDER = "https://www.redi-school.org/course-finder"


def chunk(url, text):
    return {"url": url, "text": text}


# AC1
def test_a_source_with_chunks_only_after_the_run_is_new():
    changes = compare_chunks([], [chunk(FAQ, "a"), chunk(FAQ, "b")])

    assert changes["new"] == [{"url": FAQ, "chunks": 2}]


# AC2
def test_a_source_with_chunks_only_before_the_run_is_removed():
    changes = compare_chunks([chunk(MUNICH, "a")], [])

    assert changes["removed"] == [{"url": MUNICH, "chunks": 1}]


# AC3
def test_a_source_whose_texts_differ_is_changed():
    old = [chunk(MUNICH, "x" * 500), chunk(MUNICH, "y" * 500), chunk(MUNICH, "z" * 100)]
    new = [chunk(MUNICH, "x" * 500), chunk(MUNICH, "w" * 200)]

    changes = compare_chunks(old, new)

    assert changes["changed"] == [{"url": MUNICH, "chunks_before": 3, "chunks_after": 2, "characters": -400}]


# AC4
def test_a_source_with_the_same_texts_is_unchanged():
    chunks = [chunk(FAQ, "a"), chunk(MUNICH, "b")]

    changes = compare_chunks(chunks, [dict(c) for c in chunks])

    assert changes["unchanged"] == 2
    assert changes["new"] == changes["removed"] == changes["changed"] == []


# AC5
def test_city_lists_count_as_part_of_their_source():
    old = [chunk(FINDER, "overview"), chunk(FINDER + "?category=Munich", "Python")]
    new = [chunk(FINDER, "overview"), chunk(FINDER + "?category=Munich", "Python, Java")]

    changes = compare_chunks(old, new)

    assert [change["url"] for change in changes["changed"]] == [FINDER]
    assert changes["new"] == []


# AC6
def test_format_changes_shows_every_group():
    changes = {
        "new": [{"url": FAQ, "chunks": 3}],
        "removed": [{"url": "https://www.redi-school.org/old-page", "chunks": 5}],
        "changed": [{"url": MUNICH, "chunks_before": 12, "chunks_after": 9, "characters": -4400}],
        "unchanged": 23,
    }

    text = format_changes(changes)

    assert text.splitlines() == [
        "Changes since the last run:",
        f"  new: {FAQ} (3 chunks)",
        "  removed: https://www.redi-school.org/old-page (5 chunks)",
        f"  changed: {MUNICH} (12 -> 9 chunks, -4,400 characters)",
        "  unchanged: 23 sources",
    ]


def test_format_changes_shows_a_gain_with_a_plus_and_one_chunk_in_the_singular():
    changes = {
        "new": [{"url": FAQ, "chunks": 1}],
        "removed": [],
        "changed": [{"url": MUNICH, "chunks_before": 1, "chunks_after": 2, "characters": 1500}],
        "unchanged": 1,
    }

    text = format_changes(changes)

    assert f"  new: {FAQ} (1 chunk)" in text
    assert f"  changed: {MUNICH} (1 -> 2 chunks, +1,500 characters)" in text
    assert "  unchanged: 1 source" in text.splitlines()


def test_format_changes_says_when_nothing_changed():
    text = format_changes({"new": [], "removed": [], "changed": [], "unchanged": 26})

    assert text.splitlines() == ["No changes since the last run.", "  unchanged: 26 sources"]


# AC7
def test_run_returns_the_changes_and_a_first_run_lists_every_source_as_new(tmp_path):
    sources_path = write_sources(tmp_path)
    chunks_path = tmp_path / "chunks.json"

    first = run(sources_path, chunks_path, fetch=fetch_ok)
    second = run(sources_path, chunks_path, fetch=fetch_ok)

    assert {change["url"] for change in first.changes["new"]} == {
        "https://www.redi-school.org/faq",
        "https://www.redi-school.org/redi-school-malmo",
    }
    assert second.changes["unchanged"] == 2
    assert second.changes["new"] == second.changes["changed"] == []


# AC8
def test_the_update_guide_exists_and_the_readme_links_to_it():
    project_dir = Path(__file__).parent.parent

    assert (project_dir / "docs" / "update_content.md").exists()
    assert "docs/update_content.md" in (project_dir / "README.md").read_text(encoding="utf-8")
