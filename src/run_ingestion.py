"""Runs the ingestion: reads data/sources.json, ingests the sources and saves data/chunks.json.

Usage: .venv/Scripts/python.exe src/run_ingestion.py
Running it again refreshes the saved chunks, so this is also how the content gets updated
(docs/update_content.md). At the end it prints which sources changed since the last run
(specs/task10_update_loop.md).
"""
import json
from pathlib import Path

from fetching import fetch_collection, fetch_page
from ingestion import belongs_to, ingest, summarize_report

DATA_DIR = Path(__file__).parent.parent / "data"
SOURCES_PATH = DATA_DIR / "sources.json"
CHUNKS_PATH = DATA_DIR / "chunks.json"


def run(sources_path, chunks_path, fetch=fetch_page, fetch_collection=fetch_collection):
    """Ingest the sources and save the chunks, keeping chunks from earlier runs."""
    sources = json.loads(Path(sources_path).read_text(encoding="utf-8"))

    chunks_path = Path(chunks_path)
    existing_chunks = []
    if chunks_path.exists():
        existing_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    result = ingest(sources, fetch=fetch, existing_chunks=existing_chunks, fetch_collection=fetch_collection)

    # Drop chunks of sources deleted from sources.json. ingest() keeps other sources'
    # chunks on purpose, so this check needs the complete list and lives here.
    listed_urls = [source["url"] for source in sources]
    result.chunks = [
        chunk for chunk in result.chunks if any(belongs_to(chunk, url) for url in listed_urls)
    ]

    # ensure_ascii=False keeps characters like "ö" readable in the file
    chunks_path.write_text(json.dumps(result.chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    # Only reads both lists, after saving, so it can't change which chunks are saved
    result.changes = compare_chunks(existing_chunks, result.chunks)
    return result


def texts_by_source(chunks):
    """Return {source URL: [chunk texts in order]}.

    A course list's city chunks link to the source URL plus "?category=<city>", so the part
    before "?" is the source (the same rule as belongs_to in ingestion.py).
    """
    texts = {}
    for chunk in chunks:
        texts.setdefault(chunk["url"].split("?")[0], []).append(chunk["text"])
    return texts


def compare_chunks(old_chunks, new_chunks):
    """Compare the chunks from before and after a run, per source.

    Returns {"new": [...], "removed": [...], "changed": [...], "unchanged": <number>}.
    """
    before = texts_by_source(old_chunks)
    after = texts_by_source(new_chunks)
    changes = {"new": [], "removed": [], "changed": [], "unchanged": 0}

    for url in sorted(before.keys() | after.keys()):
        old_texts, new_texts = before.get(url), after.get(url)
        if old_texts is None:
            changes["new"].append({"url": url, "chunks": len(new_texts)})
        elif new_texts is None:
            changes["removed"].append({"url": url, "chunks": len(old_texts)})
        elif old_texts != new_texts:
            changes["changed"].append({
                "url": url,
                "chunks_before": len(old_texts),
                "chunks_after": len(new_texts),
                "characters": sum(map(len, new_texts)) - sum(map(len, old_texts)),
            })
        else:
            changes["unchanged"] += 1
    return changes


def plural(count, word):
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def format_changes(changes):
    """Return the change summary as readable lines (see specs/task10_update_loop.md)."""
    if changes["new"] or changes["removed"] or changes["changed"]:
        lines = ["Changes since the last run:"]
    else:
        lines = ["No changes since the last run."]
    for change in changes["new"]:
        lines.append(f"  new: {change['url']} ({plural(change['chunks'], 'chunk')})")
    for change in changes["removed"]:
        lines.append(f"  removed: {change['url']} ({plural(change['chunks'], 'chunk')})")
    for change in changes["changed"]:
        # ":+," adds a plus sign to gains and a thousands separator: +1,500 or -4,400
        lines.append(
            f"  changed: {change['url']} ({change['chunks_before']} -> {change['chunks_after']} chunks, "
            f"{change['characters']:+,} characters)"
        )
    lines.append(f"  unchanged: {plural(changes['unchanged'], 'source')}")
    return "\n".join(lines)


def format_report(report):
    """Return a short, readable summary of an ingestion report."""
    summary = summarize_report(report)
    lines = [
        f"Ingested: {summary['ingested']}",
        f"Skipped: {summary['skipped']}",
        f"Failed: {summary['failed']}",
        f"No content: {summary['no_content']}",
    ]
    for failure in report["failed"]:
        lines.append(f"  failed: {failure['url']} ({failure['reason']})")
    for url in report["no_content"]:
        lines.append(f"  no content: {url}")
    return "\n".join(lines)


if __name__ == "__main__":
    result = run(SOURCES_PATH, CHUNKS_PATH)
    print(format_report(result.report))
    print()
    print(format_changes(result.changes))
    print()
    print(f"Saved {len(result.chunks)} chunks to {CHUNKS_PATH}")
