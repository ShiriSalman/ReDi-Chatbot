# Checks data/sources.json against the rules in sources.md (sections 2 and 6).
# data/sources.json is the list of sources the ingestion pipeline reads.
import json
from pathlib import Path

import pytest

SOURCES_FILE = Path(__file__).parent.parent / "data" / "sources.json"

CATEGORIES = [
    "About ReDI",
    "Courses",
    "Applications",
    "Locations",
    "Volunteering",
    "Career Support",
    "Support ReDI",
    "Contact",
]
REQUIRED_FIELDS = ["url", "title", "category", "language", "audience", "include", "notes"]


@pytest.fixture(scope="module")
def sources():
    with open(SOURCES_FILE, encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture(scope="module")
def included(sources):
    return [source for source in sources if source["include"] == "Yes"]


def test_every_source_has_all_fields(sources):
    for source in sources:
        missing = [field for field in REQUIRED_FIELDS if field not in source]
        assert missing == [], f"{source.get('url')} is missing {missing}"


def test_include_is_yes_no_or_maybe(sources):
    for source in sources:
        assert source["include"] in ("Yes", "No", "Maybe"), source["url"]


def test_no_url_is_listed_twice(sources):
    urls = [source["url"] for source in sources]
    duplicates = {url for url in urls if urls.count(url) > 1}
    assert duplicates == set()


def test_every_url_uses_https(sources):
    for source in sources:
        assert source["url"].startswith("https://"), source["url"]


def test_between_10_and_25_sources_are_included(included):
    assert 10 <= len(included) <= 25


def test_included_sources_are_in_english(included):
    for source in included:
        assert source["language"] == "en", source["url"]


def test_included_sources_have_a_known_category(included):
    for source in included:
        assert source["category"] in CATEGORIES, source["url"]


def test_every_category_has_at_least_one_included_source(included):
    used = {source["category"] for source in included}
    assert [category for category in CATEGORIES if category not in used] == []


def test_excluded_sources_have_a_reason(sources):
    for source in sources:
        if source["include"] != "Yes":
            assert source["notes"].strip() != "", source["url"]
