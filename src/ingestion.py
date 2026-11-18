"""Content ingestion pipeline: turns approved ReDI sources into clean, cited text chunks.

See specs/task2_content_ingestion.md for the expected behavior and
tests/test_ingestion.py for the tests.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import quote

from bs4 import BeautifulSoup

# Page parts that repeat on every page or aren't readable text. "aside" is GitBook's assistant
# and table of contents (specs/task8_add_applicant_hub_source.md); the ReDI website has none.
UNWANTED_TAGS = ["nav", "header", "footer", "aside", "script", "style", "noscript"]

MAX_CHUNK_CHARS = 500

# The Course Finder's categories mix locations and topics; these are the locations
# (specs/task8_course_list_per_city.md). A new location must be added here.
LOCATIONS = ["Berlin", "Munich", "NRW", "Hamburg", "Copenhagen", "Aarhus", "Malmö", "Gothenburg"]

# Course details come from the excerpt, which is written by hand; long ones are cut
MAX_DETAILS_CHARS = 150


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


def summarize_report(report):
    """Return the number of sources in each report category, plus the total.

    The report itself is not changed. Every source ends up in exactly one
    category, so the total is the number of sources in the run.
    """
    summary = {key: len(report[key]) for key in ["ingested", "skipped", "failed", "no_content"]}
    summary["total"] = sum(summary.values())
    return summary


def clean_html(html):
    """Return the relevant text of a page: its <main> content if it has one, without nav, header,
    footer, sidebars, scripts and styles."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(UNWANTED_TAGS):
        tag.decompose()

    # Use only the main content when the page marks it, otherwise the body, so the <title> in
    # <head> isn't counted as page text. GitBook adds the page outline after <main>, and the
    # ReDI website a "0" before it (specs/task8_add_applicant_hub_source.md)
    content = soup.find("main") or soup.body or soup
    lines = (line.strip() for line in content.get_text(separator="\n").splitlines())
    return "\n".join(line for line in lines if line)


def chunk_text(text, max_chars=MAX_CHUNK_CHARS):
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


def belongs_to(chunk, url):
    """Return True if the chunk comes from the source with this URL.

    A course list's city chunks link to the source URL plus "?category=<city>".
    """
    return chunk["url"] == url or chunk["url"].startswith(url + "?")


def make_chunk(text, source, url=None, title=None, last_updated="unavailable"):
    return {
        "text": text,
        "url": url or source["url"],
        "title": title or source["title"],
        "category": source["category"],
        "language": source["language"],
        "last_updated": last_updated,
    }


def page_intro(html):
    """Return the course list page's own text, without its course cards (<article>)."""
    soup = BeautifulSoup(html, "html.parser")
    for card in soup("article"):
        card.decompose()
    return " ".join(clean_html(str(soup)).split())


def excerpt_text(html):
    """Return a course excerpt as one line of plain text.

    Squarespace puts a <p> inside each <li>, so the lines are taken once, from the <li>s.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    parts = [tag.get_text(" ", strip=True) for tag in soup.find_all("li") or soup.find_all("p")]
    details = "; ".join(dict.fromkeys(part for part in parts if part))
    if len(details) > MAX_DETAILS_CHARS:
        details = details[:MAX_DETAILS_CHARS].rsplit(" ", 1)[0] + " …"
    return details


def course_line(item):
    """Return "- <title> (<topics>; <details>)" for one course."""
    topics = ", ".join(c for c in item.get("categories") or [] if c not in LOCATIONS)
    extras = "; ".join(part for part in [topics, excerpt_text(item.get("excerpt"))] if part)
    return f"- {item['title']} ({extras})" if extras else f"- {item['title']}"


def newest_update(items):
    times = [item["updatedOn"] for item in items if item.get("updatedOn")]
    if not times:
        return "unavailable"
    return datetime.fromtimestamp(max(times) / 1000, timezone.utc).date().isoformat()


def plural(count, word):
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def split_lines(lines, budget):
    """Group lines into parts of at most budget characters, never cutting a line."""
    parts, current = [], []
    for line in lines:
        if current and len("\n".join(current + [line])) > budget:
            parts.append(current)
            current = []
        current.append(line)
    if current:
        parts.append(current)
    return parts


def course_list_chunks(source, html, items):
    """Turn the Course Finder's items into an overview chunk and one list per city.

    Every part of a city's list starts with a header naming the city and "courses", so each
    part is found by questions like "Which courses are there in Munich?"
    (specs/task8_course_list_per_city.md).
    """
    by_city = {city: [i for i in items if city in (i.get("categories") or [])] for city in LOCATIONS}
    by_city = {city: city_items for city, city_items in by_city.items() if city_items}

    topics = {}
    for item in items:
        for category in item.get("categories") or []:
            if category not in LOCATIONS:
                topics[category] = topics.get(category, 0) + 1
    overview = (
        f"{page_intro(html)} ReDI School offers courses in {plural(len(by_city), 'location')}: "
        + ", ".join(f"{city} ({plural(len(city_items), 'course')})" for city, city_items in by_city.items())
        + ". Topics: " + ", ".join(sorted(topics, key=lambda topic: -topics[topic])) + "."
    )
    chunks = [make_chunk(piece, source, last_updated=newest_update(items)) for piece in chunk_text(overview)]

    for city, city_items in by_city.items():
        def header(part, parts):
            numbering = f", part {part} of {parts}" if parts > 1 else ""
            return f"Courses in {city} (ReDI Course Finder, {plural(len(city_items), 'course')}{numbering}):"

        # The longest header possible, so every part stays within the chunk size
        budget = MAX_CHUNK_CHARS - len(header(99, 99)) - 1
        parts = split_lines([course_line(item) for item in city_items], budget)
        for number, lines in enumerate(parts, start=1):
            chunks.append(make_chunk(
                "\n".join([header(number, len(parts))] + lines),
                source,
                url=f"{source['url']}?category={quote(city)}",
                title=f"{source['title']} – {city}",
                last_updated=newest_update(city_items),
            ))
    return chunks


def ingest(sources, fetch, existing_chunks=None, fetch_collection=None):
    """Fetch, clean and chunk every source whose include is "Yes".

    fetch(url) returns {"html": ..., "last_updated": ...} or raises an error.
    A source with "reader": "course-list" is also read with fetch_collection(url), which
    returns its items (see course_list_chunks).
    Chunks in existing_chunks are kept, except those of a source that is ingested again.
    """
    result = IngestionResult()
    stored = list(existing_chunks or [])

    for source in sources:
        url = source["url"]

        if source.get("include") != "Yes":
            # Drop chunks from earlier runs, so a source marked "No" is no longer used
            stored = [chunk for chunk in stored if not belongs_to(chunk, url)]
            result.report["skipped"].append(url)
            continue

        try:
            page = fetch(url)
            if source.get("reader") == "course-list":
                if fetch_collection is None:
                    raise ValueError("a course list needs fetch_collection")
                new_chunks = course_list_chunks(source, page["html"], fetch_collection(url))
            else:
                last_updated = page.get("last_updated") or "unavailable"
                new_chunks = [
                    make_chunk(piece, source, last_updated=last_updated)
                    for piece in chunk_text(clean_html(page["html"]))
                ]
        except Exception as error:
            # Old chunks of this source stay, so a temporary outage loses nothing
            result.report["failed"].append({"url": url, "reason": f"{type(error).__name__}: {error}"})
            continue

        if not new_chunks:
            result.report["no_content"].append(url)
            continue

        # Replace this source's old chunks so re-ingesting creates no duplicates
        stored = [chunk for chunk in stored if not belongs_to(chunk, url)]
        stored.extend(new_chunks)
        result.report["ingested"].append(url)

    result.chunks = stored
    return result
