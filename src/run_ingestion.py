"""Runs the ingestion: reads data/sources.json, ingests the sources and saves data/chunks.json.

Usage: .venv/Scripts/python.exe src/run_ingestion.py
Running it again refreshes the saved chunks, so this is also how the content gets updated.
"""
import json
from pathlib import Path

from fetching import fetch_page
from ingestion import ingest

DATA_DIR = Path(__file__).parent.parent / "data"
SOURCES_PATH = DATA_DIR / "sources.json"
CHUNKS_PATH = DATA_DIR / "chunks.json"


def run(sources_path, chunks_path, fetch=fetch_page):
    """Ingest the sources and save the chunks, keeping chunks from earlier runs."""
    sources = json.loads(Path(sources_path).read_text(encoding="utf-8"))

    chunks_path = Path(chunks_path)
    existing_chunks = []
    if chunks_path.exists():
        existing_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    result = ingest(sources, fetch=fetch, existing_chunks=existing_chunks)

    # ensure_ascii=False keeps characters like "ö" readable in the file
    chunks_path.write_text(json.dumps(result.chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def format_report(report):
    """Return a short, readable summary of an ingestion report."""
    lines = [
        f"Ingested: {len(report['ingested'])}",
        f"Skipped: {len(report['skipped'])}",
        f"Failed: {len(report['failed'])}",
        f"No content: {len(report['no_content'])}",
    ]
    for failure in report["failed"]:
        lines.append(f"  failed: {failure['url']} ({failure['reason']})")
    for url in report["no_content"]:
        lines.append(f"  no content: {url}")
    return "\n".join(lines)


if __name__ == "__main__":
    result = run(SOURCES_PATH, CHUNKS_PATH)
    print(format_report(result.report))
    print(f"Saved {len(result.chunks)} chunks to {CHUNKS_PATH}")
