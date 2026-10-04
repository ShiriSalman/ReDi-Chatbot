"""Downloads one source page for the ingestion pipeline (see src/ingestion.py)."""
from email.utils import parsedate_to_datetime

import requests

# Seconds to wait for a page before giving up, so one slow page can't block the run
TIMEOUT_SECONDS = 15


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


def parse_last_modified(value):
    """Turn a Last-Modified header like "Sun, 15 Mar 2026 10:00:00 GMT" into "2026-03-15"."""
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None
