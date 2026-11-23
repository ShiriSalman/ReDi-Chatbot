"""Content ingestion pipeline: turns approved ReDI sources into clean, cited text chunks.

See specs/task2_content_ingestion.md for the expected behavior and
tests/test_ingestion.py for the tests.
"""
import html as html_module
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import quote

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

# Page parts that repeat on every page or aren't readable text. "aside" is GitBook's assistant
# and table of contents (specs/task8_add_applicant_hub_source.md); the ReDI website has none.
UNWANTED_TAGS = ["nav", "header", "footer", "aside", "script", "style", "noscript"]

MAX_CHUNK_CHARS = 500

# The Course Finder's categories mix locations and topics; these are the locations
# (specs/task8_course_list_per_city.md). A new location must be added here.
LOCATIONS = ["Berlin", "Munich", "NRW", "Hamburg", "Copenhagen", "Aarhus", "Malmö", "Gothenburg"]


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
    # Filled by run_ingestion.run(): which sources changed since the last run
    changes: dict = field(default_factory=dict)


def summarize_report(report):
    """Return the number of sources in each report category, plus the total.

    The report itself is not changed. Every source ends up in exactly one
    category, so the total is the number of sources in the run.
    """
    summary = {key: len(report[key]) for key in ["ingested", "skipped", "failed", "no_content"]}
    summary["total"] = sum(summary.values())
    return summary


def main_content(html):
    """Return the part of a page with its relevant content, without nav, header, footer,
    sidebars, scripts and styles."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(UNWANTED_TAGS):
        tag.decompose()

    # Use only the main content when the page marks it, otherwise the body, so the <title> in
    # <head> isn't counted as page text. GitBook adds the page outline after <main>, and the
    # ReDI website a "0" before it (specs/task8_add_applicant_hub_source.md)
    return soup.find("main") or soup.body or soup


def clean_html(html):
    """Return the relevant text of a page: its <main> content if it has one, without nav, header,
    footer, sidebars, scripts and styles."""
    content = main_content(html)
    lines = (line.strip() for line in content.get_text(separator="\n").splitlines())
    return "\n".join(line for line in lines if line)


# Where a page with "reader": "sections" is divided (specs/task8_contact_page_sections.md)
SECTION_HEADINGS = ["h1", "h2", "h3"]


def sections(html):
    """Return the page's text split at its headings, one text per section.

    A section that has only its heading and no text of its own (the contact page's
    "<h2>Munich</h2>" before "<h3>Birgit Köbl</h3>") goes with the next section, because
    a heading belongs to the text after it.
    """
    result = []
    waiting_heading = ""
    for heading, body in heading_and_body_parts(main_content(html)):
        if heading and not body:
            waiting_heading = f"{waiting_heading} {heading}".strip()
            continue
        text = " ".join(part for part in (waiting_heading, heading, body) if part)
        if text:
            result.append(text)
        waiting_heading = ""
    if waiting_heading:
        result.append(waiting_heading)
    return result


def heading_and_body_parts(content):
    """Walk through the content in page order and return (heading text, body text) pairs:
    one pair per heading, plus one for any text before the first heading."""
    parts = [{"heading": [], "body": []}]
    current_heading = None
    for element in content.descendants:
        if isinstance(element, Tag) and element.name in SECTION_HEADINGS:
            parts.append({"heading": [], "body": []})
            current_heading = element
        elif isinstance(element, NavigableString) and not isinstance(element, Comment):
            text = element.strip()
            if text:
                in_heading = current_heading is not None and current_heading in element.parents
                parts[-1]["heading" if in_heading else "body"].append(text)
    return [(" ".join(" ".join(part["heading"]).split()), " ".join(" ".join(part["body"]).split()))
            for part in parts]


def section_chunks(html, max_chars=MAX_CHUNK_CHARS):
    """Pack the page's whole sections into chunks of at most max_chars, in page order.

    A section is only cut (with chunk_text) when it alone is longer than max_chars; the next
    section then starts a new chunk.
    """
    chunks = []
    current = ""
    for text in sections(html):
        if len(text) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(chunk_text(text, max_chars))
            continue
        candidate = f"{current} {text}" if current else text
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = text
    if current:
        chunks.append(current)
    return chunks


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
    """Return the course list page's own text, without its course cards.

    Squarespace puts the intro and the cards (class "blog-item") in one outer <article>.
    """
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.select("article.blog-item"):
        card.decompose()
    return " ".join(clean_html(str(soup)).split())


def course_line(item):
    """Return "- <title> (<topics>)" for one course.

    Details such as dates and times are left out: with them, Berlin's list needed 11 chunks,
    without them 3, so a city's whole list fits into the chunks the model gets.
    """
    title = html_module.unescape(item["title"])
    topics = ", ".join(c for c in item.get("categories") or [] if c not in LOCATIONS)
    return f"- {title} ({topics})" if topics else f"- {title}"


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
        # The city is named twice: named once, the list ranked below the city's own pages for
        # "Which courses are there in Munich?" (specs/task8_course_list_per_city.md, Iteration)
        def header(part, parts):
            numbering = f", part {part} of {parts}" if parts > 1 else ""
            return (f"Courses in {city} (ReDI Course Finder, {plural(len(city_items), 'course')} "
                    f"at ReDI {city}{numbering}):")

        # The longest header possible, so every part stays within the chunk size
        budget = MAX_CHUNK_CHARS - len(header(99, 99)) - 1
        parts = split_lines([course_line(item) for item in city_items], budget)
        for number, lines in enumerate(parts, start=1):
            chunk = make_chunk(
                "\n".join([header(number, len(parts))] + lines),
                source,
                url=f"{source['url']}?category={quote(city)}",
                title=f"{source['title']} – {city}",
                last_updated=newest_update(city_items),
            )
            # Only useful complete: retrieval brings the other parts along
            # (specs/task8_complete_city_lists.md)
            chunk["list_part"] = True
            chunks.append(chunk)
    return chunks


def ingest(sources, fetch, existing_chunks=None, fetch_collection=None):
    """Fetch, clean and chunk every source whose include is "Yes".

    fetch(url) returns {"html": ..., "last_updated": ...} or raises an error.
    A source with "reader": "course-list" is also read with fetch_collection(url), which
    returns its items (see course_list_chunks). A source with "reader": "sections" is
    chunked by its headings (see section_chunks).
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
                # "reader": "sections" keeps a heading and its text together
                # (specs/task8_contact_page_sections.md); other pages are cut every 500 characters
                if source.get("reader") == "sections":
                    pieces = section_chunks(page["html"])
                else:
                    pieces = chunk_text(clean_html(page["html"]))
                new_chunks = [make_chunk(piece, source, last_updated=last_updated) for piece in pieces]
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
