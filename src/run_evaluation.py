"""Task 8 evaluation: sends every question of the question set through POST /api/chat
and writes the evidence table.

See specs/task8_test_against_real_user_questions.md for the expected behavior and
tests/test_run_evaluation.py for the tests.

Usage: .venv/Scripts/python.exe src/run_evaluation.py
With GEMINI_API_KEY set the answers come from Gemini (one call per answered question),
otherwise from demo mode, where only retrieval, sources and the fallback can be judged.
"""
import json
import time
from datetime import date
from pathlib import Path

from app import create_app, demo_generate, load_chunks
from grounding import GOODBYE_REPLY, GREETING_REPLY, THANKS_REPLY
from llm import MODEL, choose_generate

SMALL_TALK_REPLIES = {GREETING_REPLY, THANKS_REPLY, GOODBYE_REPLY}

PROJECT_DIR = Path(__file__).parent.parent
QUESTIONS_PATH = PROJECT_DIR / "data" / "task8_questions.json"
RESULTS_PATH = PROJECT_DIR / "docs" / "task8_results.md"

# Gemini's free tier allows 15 requests per minute; without a pause the last questions of a run
# got 429 RESOURCE_EXHAUSTED (specs/task8_test_against_real_user_questions.md). 4.5 seconds
# between calls means at most about 13 per minute.
PAUSE_SECONDS = 4.5


def paced(generate, seconds=PAUSE_SECONDS, sleep=None):
    """Return a generate function that waits `seconds` before every call except the first.

    sleep is looked up at call time (time.sleep), so tests can replace it and not wait.
    """
    calls = 0

    def paced_generate(prompt):
        nonlocal calls
        if calls:
            (sleep or time.sleep)(seconds)
        calls += 1
        return generate(prompt)

    return paced_generate


def load_questions(path=QUESTIONS_PATH):
    """Return the question set from the JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


# The keys evaluate() and passes() read, and the behaviours passes() knows
REQUIRED_KEYS = ["id", "question", "expected", "expected_url", "known_issue"]
EXPECTED_VALUES = {"answer", "fallback", "small_talk"}

# Pass/fail only checks retrieval and fallback, never the answer text
# (specs/task8_test_against_real_user_questions.md, "Iteration: what the checks measure")
CHECKS_EXPLAINED = (
    "Pass/fail is an automated check of retrieval and fallback behaviour: for \"answer\" the "
    "expected ReDI page is among the sources, for \"fallback\" there are no sources and the "
    "contact link is shown, and for \"small_talk\" the fixed reply is given. It does not check "
    "whether the answer text is factually correct; that needs a manual review of the answers below."
)


def validate_questions(questions):
    """Return a list of problems in the question set, empty when every entry is usable.

    Run before the first question, so a bad entry can't stop a run after it used Gemini's quota.
    """
    problems = []
    for position, case in enumerate(questions, start=1):
        name = case.get("id") or f"entry {position}"
        missing = [key for key in REQUIRED_KEYS if key not in case]
        if missing:
            problems.append(f"{name}: missing {', '.join(missing)}")
        question = case.get("question")
        if not isinstance(question, str) or not question.strip():
            problems.append(f"{name}: the question is empty")
        if "expected" in case and case["expected"] not in EXPECTED_VALUES:
            problems.append(f"{name}: unknown expected value {case['expected']!r}")
    return problems


def passes(case, data):
    """Check one response against the expected behaviour of its case.

    Only retrieval and fallback are checked (sources, contact link, small-talk reply), never
    whether the answer text is correct (see CHECKS_EXPLAINED).
    """
    source_urls = [source["url"] for source in data.get("sources", [])]
    if case["expected"] == "fallback":
        return data.get("enough_information") is False and not source_urls and "contact" in data
    if case["expected"] == "small_talk":
        return data.get("answer") in SMALL_TALK_REPLIES and not source_urls and "contact" not in data
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
    lines.append(f"{passed} of {len(results)} automated evaluation checks passed")
    return "\n".join(lines)


def run(output_path=RESULTS_PATH):
    """Evaluate the question set with the app's real setup and save the table.

    Raises ValueError before any question is asked when the question set has a bad entry.
    """
    questions = load_questions()
    problems = validate_questions(questions)
    if problems:
        raise ValueError("data/task8_questions.json has problems:\n- " + "\n- ".join(problems))

    generate = choose_generate(demo_generate)
    mode = "demo mode" if generate is demo_generate else f"Gemini ({MODEL})"
    if generate is not demo_generate:
        generate = paced(generate)
    results = evaluate(questions, load_chunks(), generate)

    report = (
        "# Task 8 results\n\n"
        f"Run on {date.today().isoformat()} in {mode}. "
        "Created by `src/run_evaluation.py` from `data/task8_questions.json`.\n\n"
        + CHECKS_EXPLAINED + "\n\n"
        + format_results(results)
        + "\n"
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report, encoding="utf-8")
    return results


if __name__ == "__main__":
    results = run()
    passed = sum(1 for result in results if result["passed"])
    print(f"{passed} of {len(results)} automated evaluation checks passed. Saved to {RESULTS_PATH}")
    print("They check retrieval and fallback, not whether the answers are correct: read the answers too.")
