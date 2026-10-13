"""Citations: turns the sources of an answer into a list of ReDI pages the user can open.

See specs/task5_citation_sourcing.md for the expected behavior and
tests/test_citations.py for the tests.
"""
from urllib.parse import urlparse

# Used when a source has no title, instead of inventing one
NEUTRAL_TITLE = "ReDI source"


def is_valid_url(url):
    """Return True only for http:// and https:// URLs with a host."""
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def collect_citations(sources):
    """Return one citation per page, in the order the pages first appear.

    Each citation is {"title": ..., "url": ...}. The URL comes only from the source
    metadata and is None when it is missing or invalid, so no link is ever guessed.
    Pages are compared without a trailing slash, but the original URL is kept.
    """
    citations = []
    seen = set()

    for chunk in sources:
        title = chunk.get("title") or NEUTRAL_TITLE
        url = chunk.get("url")

        if is_valid_url(url):
            key = url.rstrip("/")
        else:
            # Without a usable URL, sources can only be told apart by their title
            url = None
            key = ("no url", title)

        if key in seen:
            continue
        seen.add(key)
        citations.append({"title": title, "url": url})

    return citations


def format_answer(result):
    """Return the answer text followed by a Sources section with links to the ReDI pages.

    The Sources section is only shown when at least one source has a valid URL.
    Sources without a valid URL are listed as plain text, never as a link.
    """
    citations = collect_citations(result.sources)
    if not any(citation["url"] for citation in citations):
        return result.text

    lines = [result.text, "", "**Sources**"]
    for citation in citations:
        # Titles are data: square brackets are removed so a title can never form its own link
        title = citation["title"].replace("[", "").replace("]", "")
        if citation["url"]:
            lines.append(f"- [{title}]({citation['url']})")
        else:
            lines.append(f"- {title} (no link available)")
    return "\n".join(lines)
