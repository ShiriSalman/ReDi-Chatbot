# Task 8 question catalogue, written from specs/task8_test_against_real_user_questions.md.
# Unlike the other tests, these run on the real ingested content (data/chunks.json), so they are
# the recorded evidence for retrieval, sources and fallback. The model is a fake: answer quality
# can only be judged with a real model (spec, "Important limitation").
# Cases with a known_issue are expected to fail (xfail, strict): when a fix makes one pass,
# pytest reports it, and the known_issue is removed from data/task8_questions.json on purpose.
import json
from pathlib import Path

import pytest

from app import create_app, load_chunks
from grounding import NOT_ENOUGH_INFO

DATA_DIR = Path(__file__).parent.parent / "data"
QUESTIONS_FILE = DATA_DIR / "task8_questions.json"
CHUNKS_FILE = DATA_DIR / "chunks.json"
SOURCES_FILE = DATA_DIR / "sources.json"

if not CHUNKS_FILE.exists():
    pytest.skip("data/chunks.json is missing; run the ingestion first", allow_module_level=True)

QUESTIONS = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
CHUNKS = load_chunks(CHUNKS_FILE)
APPROVED_URLS = {
    source["url"]
    for source in json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    if source["include"] == "Yes"
}

FIELDS = {"id", "question", "topic", "case", "expected", "expected_url", "known_issue"}


def fake_generate(answer="Fake answer from the test."):
    """Returns a generate function that gives the same answer and records the prompts."""
    prompts = []

    def generate(prompt):
        prompts.append(prompt)
        return answer

    generate.prompts = prompts
    return generate


def ask(question, generate=None):
    app = create_app(chunks=CHUNKS, generate=generate or fake_generate())
    app.config["TESTING"] = True
    return app.test_client().post("/api/chat", json={"question": question}).get_json()


def as_param(case):
    marks = []
    if case["known_issue"]:
        marks.append(pytest.mark.xfail(strict=True, reason=case["known_issue"]))
    return pytest.param(case, id=case["id"], marks=marks)


# AC1: at least 10 realistic questions, labelled by topic and expected behaviour
class TestQuestionSet:
    def test_question_set_has_at_least_ten_labelled_questions(self):
        assert len({case["question"] for case in QUESTIONS}) >= 10
        assert len({case["id"] for case in QUESTIONS}) == len(QUESTIONS)
        for case in QUESTIONS:
            assert set(case) == FIELDS, case["id"]
            assert case["expected"] in {"answer", "fallback"}, case["id"]

    def test_covers_every_case_type(self):
        # Spec scope: straightforward, unclear, partially covered and out-of-scope questions
        cases = {case["case"] for case in QUESTIONS}

        assert {"straightforward", "unclear", "partial", "out_of_scope"} <= cases

    def test_expected_urls_are_approved_sources(self):
        for case in QUESTIONS:
            if case["expected_url"]:
                assert case["expected_url"] in APPROVED_URLS, case["id"]


# AC3 and AC4: each question through POST /api/chat, on the real content
@pytest.mark.parametrize("case", [as_param(case) for case in QUESTIONS])
def test_real_question(case):
    generate = fake_generate()

    data = ask(case["question"], generate)

    if case["expected"] == "fallback":
        assert data["answer"] == NOT_ENOUGH_INFO
        assert data["enough_information"] is False
        assert data["sources"] == []
        assert "contact" in data
        assert generate.prompts == []
    else:
        assert data["enough_information"] is True
        if case["expected_url"]:
            assert case["expected_url"] in [source["url"] for source in data["sources"]]


# AC3: no invented links, for every question in the set
def test_no_invented_links():
    for case in QUESTIONS:
        for source in ask(case["question"])["sources"]:
            assert source["url"] in APPROVED_URLS, (case["id"], source["url"])
