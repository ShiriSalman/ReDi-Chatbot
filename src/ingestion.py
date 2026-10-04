"""Content ingestion pipeline: turns approved ReDI sources into clean, cited text chunks.

See specs/task2_content_ingestion.md for the expected behavior and
tests/test_ingestion.py for the tests.
"""
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

# Page parts that repeat on every page or aren't readable text
UNWANTED_TAGS = ["nav", "header", "footer", "script", "style", "noscript"]


@dataclass
class IngestionResult:
    # Every chunk is a dict with: text, url, title, category, language, last_updated
    chunks: list = field(default_factory=list)
    # Lists of URLs: "ingested", "skipped", "no_content".
    # "failed" is a list of {"url": ..., "reason": ...}
    report: dict = field(default_factory=lambda: {
        "ingested": [],
        "skipped": [],
        "failed": [],
        "no_content": [],
    })


def clean_html(html):
    """Return the relevant text of a page, without nav, header, footer, scripts and styles."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(UNWANTED_TAGS):
        tag.decompose()

    # Use only the body, so the <title> in <head> isn't counted as page text
    content = soup.body or soup
    lines = (line.strip() for line in content.get_text(separator="\n").splitlines())
    return "\n".join(line for line in lines if line)


def chunk_text(text, max_chars=500):
    """Split text into non-empty chunks of at most max_chars characters.

    Words are kept whole, so a chunk ends at a space, never in the middle of a word.
    Only a single word longer than max_chars is cut.
    """
    chunks = []
    current = ""

    for word in text.split():
        # A word that doesn't fit into any chunk is cut into pieces
        while len(word) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(word[:max_chars])
            word = word[max_chars:]
        if not word:
            continue

        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = word

    if current:
        chunks.append(current)
    return chunks


def ingest(sources, fetch, existing_chunks=None):
    """Fetch, clean and chunk every source whose include is "Yes".

    fetch(url) returns {"html": ..., "last_updated": ...} or raises an error.
    Chunks in existing_chunks are kept, except those of a source that is ingested again.
    """
    result = IngestionResult()
    stored = list(existing_chunks or [])

    for source in sources:
        url = source["url"]

        if source.get("include") != "Yes":
            # Drop chunks from earlier runs, so a source marked "No" is no longer used
            stored = [chunk for chunk in stored if chunk["url"] != url]
            result.report["skipped"].append(url)
            continue

        try:
            page = fetch(url)
        except Exception as error:
            # Old chunks of this source stay, so a temporary outage loses nothing
            result.report["failed"].append({"url": url, "reason": f"{type(error).__name__}: {error}"})
            continue

        pieces = chunk_text(clean_html(page["html"]))
        if not pieces:
            result.report["no_content"].append(url)
            continue

        last_updated = page.get("last_updated") or "unavailable"
        # Replace this source's old chunks so re-ingesting creates no duplicates
        stored = [chunk for chunk in stored if chunk["url"] != url]
        for piece in pieces:
            stored.append({
                "text": piece,
                "url": url,
                "title": source["title"],
                "category": source["category"],
                "language": source["language"],
                "last_updated": last_updated,
            })
        result.report["ingested"].append(url)

    result.chunks = stored
    return result
