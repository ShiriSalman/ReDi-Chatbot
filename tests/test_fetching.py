# Tests for fetch_page, which downloads one source for the ingestion pipeline.
# src/fetching.py does not exist yet, so every test fails until it is written.
# The get function is passed in, so the tests never touch the network.
import pytest

from fetching import FetchError, fetch_collection, fetch_page


class FakeResponse:
    def __init__(self, text="<html><body><p>Hello</p></body></html>", status_code=200, headers=None,
                 data=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}
        self.data = data

    def json(self):
        return self.data


def fake_get(response):
    """Returns a get function that always gives this response and records how it was called."""
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return response

    get.calls = calls
    return get


def test_returns_the_html_of_the_page():
    get = fake_get(FakeResponse(text="<p>All our courses are free.</p>"))

    page = fetch_page("https://www.redi-school.org/faq", get=get)

    assert page["html"] == "<p>All our courses are free.</p>"


def test_requests_the_given_url_with_a_timeout():
    get = fake_get(FakeResponse())

    fetch_page("https://www.redi-school.org/faq", get=get)

    url, kwargs = get.calls[0]
    assert url == "https://www.redi-school.org/faq"
    # Without a timeout, one page that never answers would block the whole run
    assert kwargs.get("timeout")


# Scenario 6: Preserve freshness information
def test_reads_the_last_updated_date_from_the_last_modified_header():
    headers = {"Last-Modified": "Sun, 15 Mar 2026 10:00:00 GMT"}

    page = fetch_page("https://www.redi-school.org/faq", get=fake_get(FakeResponse(headers=headers)))

    assert page["last_updated"] == "2026-03-15"


def test_last_updated_is_none_without_a_last_modified_header():
    page = fetch_page("https://www.redi-school.org/faq", get=fake_get(FakeResponse()))

    assert page["last_updated"] is None


def test_last_updated_is_none_when_the_header_is_not_a_date():
    headers = {"Last-Modified": "yesterday"}

    page = fetch_page("https://www.redi-school.org/faq", get=fake_get(FakeResponse(headers=headers)))

    assert page["last_updated"] is None


# Scenario 8: Handle an unavailable source
def test_raises_an_error_with_the_status_code_when_the_page_is_missing():
    get = fake_get(FakeResponse(status_code=404))

    with pytest.raises(FetchError, match="404"):
        fetch_page("https://www.redi-school.org/broken", get=get)


# specs/task8_course_list_per_city.md: the Course Finder shows 20 courses per page, so the
# page's HTML had only 20 of 74. Its JSON has every page.
COURSE_FINDER = "https://www.redi-school.org/course-finder"


def paged_get(pages):
    """Returns a get function that answers with the JSON pages in order and records the params."""
    responses = iter(FakeResponse(data=page) for page in pages)
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return next(responses)

    get.calls = calls
    return get


class TestFetchCollection:
    # AC1
    def test_reads_every_page_following_the_next_page_offset(self):
        get = paged_get([
            {"items": [{"title": "Python"}], "pagination": {"nextPage": True, "nextPageOffset": 111}},
            {"items": [{"title": "Data Analytics"}], "pagination": {"nextPage": True, "nextPageOffset": 222}},
            {"items": [{"title": "Cybersecurity"}], "pagination": {"nextPage": False}},
        ])

        items = fetch_collection(COURSE_FINDER, get=get)

        assert [item["title"] for item in items] == ["Python", "Data Analytics", "Cybersecurity"]
        assert [kwargs["params"] for _, kwargs in get.calls] == [
            {"format": "json"},
            {"format": "json", "offset": 111},
            {"format": "json", "offset": 222},
        ]
        assert all(kwargs.get("timeout") for _, kwargs in get.calls)

    def test_a_single_page_without_pagination_is_read_once(self):
        get = paged_get([{"items": [{"title": "Python"}]}])

        assert fetch_collection(COURSE_FINDER, get=get) == [{"title": "Python"}]
        assert len(get.calls) == 1

    # AC1
    def test_raises_an_error_with_the_status_code(self):
        get = fake_get(FakeResponse(status_code=503))

        with pytest.raises(FetchError, match="503"):
            fetch_collection(COURSE_FINDER, get=get)
