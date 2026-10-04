# Tests for fetch_page, which downloads one source for the ingestion pipeline.
# src/fetching.py does not exist yet, so every test fails until it is written.
# The get function is passed in, so the tests never touch the network.
import pytest

from fetching import FetchError, fetch_page


class FakeResponse:
    def __init__(self, text="<html><body><p>Hello</p></body></html>", status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}


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
