"""Task 8 evaluation: sends every question of the question set through POST /api/chat
and writes the evidence table.

See specs/task8_test_against_real_user_questions.md for the expected behavior and
tests/test_run_evaluation.py for the tests.

Usage: .venv/Scripts/python.exe src/run_evaluation.py
With GEMINI_API_KEY set the answers come from Gemini (one call per answered question),
otherwise from demo mode, where only retrieval, sources and the fallback can be judged.
"""
import json
from datetime import date
from pathlib import Path

from app import create_app, demo_generate, load_chunks
from llm import MODEL, choose_generate

PROJECT_DIR = Path(__file__).parent.parent
QUESTIONS_PATH = PROJECT_DIR / "data" / "task8_questions.json"
RESULTS_PATH = PROJECT_DIR / "docs" / "task8_results.md"


def load_questions(path=QUESTIONS_PATH):
    """Return the question set from the JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def passes(case, data):
    """Check one response against the expected behaviour of its case."""
    source_urls = [source["url"] for source in data.get("sources", [])]
    if case["expected"] == "fallback":
        return data.get("enough_information") is False and not source_urls and "contact" in data
    # An answer may be marked as not fully covered (contact link) and still be right:
    # what counts here is that retrieval found the expected page
    if not source_urls:
        return False
    return case["expected_url"] is None or case["expected_url"] in source_urls


def evaluate(questions, chunks, generate):
    """Ask every question through the chat API and record the evidence for each one.

    Going through the API, not answer_question(), means the results show exactly what
    a visitor gets, including the contact link and the error responses.
    """
    app = create_app(chunks, generate)
    app.config["TESTING"] = True
    client = app.test_client()

    results = []
    for case in questions:
        data = client.post("/api/chat", json={"question": case["question"]}).get_json() or {}
        results.append({
            "id": case["id"],
            "question": case["question"],
            "expected": case["expected"],
            # A failed request has an error message instead of an answer
            "answer": data.get("answer", data.get("error", "")),
            "sources": [source["url"] for source in data.get("sources", [])],
            "contact": "contact" in data,
            "passed": passes(case, data),
            "notes": case["known_issue"] or "",
        })
    return results


def table_cell(text):
    """Keep a value in one Markdown table cell: no line breaks, and "|" escaped."""
    return " ".join(str(text).split()).replace("|", "\\|")


def format_results(results):
    """Return the evidence table as Markdown, with a count of passed questions."""
    lines = [
        "| question | expected | actual answer | sources | pass/fail | notes |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        sources = ", ".join(result["sources"])
        if result["contact"]:
            sources = (sources + ", " if sources else "") + "contact link"
        cells = [
            result["question"],
            result["expected"],
            result["answer"],
            sources,
            "pass" if result["passed"] else "fail",
            result["notes"],
        ]
        lines.append("| " + " | ".join(table_cell(cell) for cell in cells) + " |")

    passed = sum(1 for result in results if result["passed"])
    lines.append("")
    lines.append(f"{passed} of {len(results)} passed")
    return "\n".join(lines)


def run(output_path=RESULTS_PATH):
    """Evaluate the question set with the app's real setup and save the table."""
    generate = choose_generate(demo_generate)
    mode = "demo mode" if generate is demo_generate else f"Gemini ({MODEL})"
    results = evaluate(load_questions(), load_chunks(), generate)

    report = (
        "# Task 8 results\n\n"
        f"Run on {date.today().isoformat()} in {mode}. "
        "Created by `src/run_evaluation.py` from `data/task8_questions.json`.\n\n"
        + format_results(results)
        + "\n"
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report, encoding="utf-8")
    return results


if __name__ == "__main__":
    results = run()
    passed = sum(1 for result in results if result["passed"])
    print(f"{passed} of {len(results)} passed. Saved to {RESULTS_PATH}")
