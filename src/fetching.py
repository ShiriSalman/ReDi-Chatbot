"""Downloads one source page, or all items of a course list, for the ingestion pipeline
(see src/ingestion.py)."""
from email.utils import parsedate_to_datetime

import requests

# Seconds to wait for a page before giving up, so one slow page can't block the run
TIMEOUT_SECONDS = 15
MAX_COLLECTION_PAGES = 50


class FetchError(Exception):
    """A page could not be downloaded."""


def fetch_page(url, get=requests.get):
    """Download a page and return {"html": ..., "last_updated": "YYYY-MM-DD" or None}.

    Raises FetchError when the server answers with an error status such as 404.
    """
    response = get(url, timeout=TIMEOUT_SECONDS)
    if response.status_code >= 400:
        raise FetchError(f"HTTP {response.status_code} for {url}")

    return {
        "html": response.text,
        "last_updated": parse_last_modified(response.headers.get("Last-Modified")),
    }


def fetch_collection(url, get=requests.get):
    """Return every item of a Squarespace collection page, such as the Course Finder.

    The page shows only 20 items and loads the rest while scrolling; its JSON version
    (?format=json) gives them page by page. Raises FetchError on an error status.
    """
    items = []
    params = {"format": "json"}
    # A limit, so a broken pagination can't loop forever (the Course Finder had 4 pages)
    for _ in range(MAX_COLLECTION_PAGES):
        response = get(url, params=dict(params), timeout=TIMEOUT_SECONDS)
        if response.status_code >= 400:
            raise FetchError(f"HTTP {response.status_code} for {url}")
        data = response.json()
        items.extend(data.get("items", []))

        pagination = data.get("pagination") or {}
        if not pagination.get("nextPage"):
            break
        params["offset"] = pagination["nextPageOffset"]
    return items


def parse_last_modified(value):
    """Turn a Last-Modified header like "Sun, 15 Mar 2026 10:00:00 GMT" into "2026-03-15"."""
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None
