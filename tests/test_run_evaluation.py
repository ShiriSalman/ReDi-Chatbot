# Tests for the Task 8 evaluation runner, written from specs/task8_test_against_real_user_questions.md.
# The runner sends each question through POST /api/chat and records the evidence the spec asks for:
# question | expected | actual answer | sources | pass/fail | notes.
# Small fake chunks and a fake model are used, so the tests don't depend on the real content.
import json

import pytest

import run_evaluation
from app import demo_generate
from run_evaluation import PAUSE_SECONDS, evaluate, format_results, load_questions, paced

FAQ_URL = "https://www.redi-school.org/faq"
MALMO_URL = "https://www.redi-school.org/redi-school-malmo"
FAKE_ANSWER = "Yes, all courses are free."


def make_chunk(text, **overrides):
    chunk = {
        "text": text,
        "url": FAQ_URL,
        "title": "FAQ",
        "category": "Applications",
        "language": "en",
        "last_updated": "unavailable",
    }
    chunk.update(overrides)
    return chunk


CHUNKS = [
    make_chunk("All our courses are free of charge for every learner."),
    make_chunk(
        "The ReDI office in Malmö is located close to the central station.",
        url=MALMO_URL,
        title="ReDI School Malmö",
    ),
]


def fake_generate(prompt):
    return FAKE_ANSWER


def make_case(question, expected="answer", expected_url=None, known_issue=None, case_id="q01"):
    return {
        "id": case_id,
        "question": question,
        "topic": "Costs",
        "case": "straightforward",
        "expected": expected,
        "expected_url": expected_url,
        "known_issue": known_issue,
    }


COVERED = "Are the courses free?"
UNRELATED = "What will the weather be like in Tokyo tomorrow?"


def run_one(case):
    [result] = evaluate([case], CHUNKS, fake_generate)
    return result


def test_load_questions_reads_the_file(tmp_path):
    questions = [make_case(COVERED)]
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(questions), encoding="utf-8")

    assert load_questions(path) == questions


# specs/task8_test_against_real_user_questions.md, "Iteration: what the checks measure,
# a checked question file"
class TestQuestionFileCheck:
    def run_with(self, monkeypatch, tmp_path, cases):
        calls = []
        monkeypatch.setattr(run_evaluation, "choose_generate", lambda fallback: lambda p: calls.append(p) or "x")
        monkeypatch.setattr(run_evaluation.time, "sleep", lambda seconds: None)
        monkeypatch.setattr(run_evaluation, "load_questions", lambda: cases)
        monkeypatch.setattr(run_evaluation, "load_chunks", lambda: CHUNKS)
        return calls, (lambda: run_evaluation.run(output_path=tmp_path / "results.md"))

    # AC-V1
    def test_a_bad_entry_stops_the_run_before_any_model_call(self, monkeypatch, tmp_path):
        no_known_issue = make_case(COVERED, case_id="q02")
        del no_known_issue["known_issue"]
        cases = [
            make_case(COVERED, case_id="q01"),
            no_known_issue,
            make_case("  ", case_id="q03"),
            make_case(COVERED, expected="fallbak", case_id="q04"),
        ]
        calls, run = self.run_with(monkeypatch, tmp_path, cases)

        with pytest.raises(ValueError) as error:
            run()

        message = str(error.value)
        assert "q02" in message and "known_issue" in message
        assert "q03" in message and "question" in message
        assert "q04" in message and "fallbak" in message
        assert "q01" not in message
        assert calls == []
        assert not (tmp_path / "results.md").exists()

    # AC-V2
    def test_the_real_question_file_is_valid(self):
        assert run_evaluation.validate_questions(load_questions()) == []

    # AC-V3
    def test_the_results_file_says_what_the_checks_cover(self, monkeypatch, tmp_path):
        _, run = self.run_with(monkeypatch, tmp_path, [make_case(COVERED, expected_url=FAQ_URL)])

        run()

        report = (tmp_path / "results.md").read_text(encoding="utf-8")
        assert "1 of 1 automated evaluation checks passed" in report
        assert "does not check whether the answer text is factually correct" in report
        assert "manual review" in report


# Pass/fail rules
class TestPassFail:
    def test_fallback_case_passes_when_retrieval_finds_nothing(self):
        assert run_one(make_case(UNRELATED, expected="fallback"))["passed"] is True

    def test_fallback_case_fails_when_sources_are_returned(self):
        assert run_one(make_case(COVERED, expected="fallback"))["passed"] is False

    def test_answer_case_passes_when_the_expected_page_is_cited(self):
        assert run_one(make_case(COVERED, expected_url=FAQ_URL))["passed"] is True

    def test_answer_case_fails_when_the_expected_page_is_missing(self):
        assert run_one(make_case(COVERED, expected_url=MALMO_URL))["passed"] is False

    def test_answer_case_fails_when_the_fallback_is_returned(self):
        assert run_one(make_case(UNRELATED))["passed"] is False

    def test_answer_case_without_expected_url_only_needs_an_answer(self):
        assert run_one(make_case(COVERED))["passed"] is True

    # specs/task8_fix_small_talk.md, AC4
    def test_small_talk_case_passes_with_its_reply(self):
        assert run_one(make_case("thanks", expected="small_talk"))["passed"] is True

    def test_small_talk_case_fails_with_sources(self):
        # "Are the courses free?" is a real question, so it gets sources, not a small-talk reply
        assert run_one(make_case(COVERED, expected="small_talk"))["passed"] is False

    # specs/task8_fix_contact_link_not_covered.md, AC7: an honest "not covered" answer with
    # the right sources and the contact link is what we want, not a failure
    def test_answer_case_with_contact_link_still_passes(self):
        def generate(prompt):
            return "[NOT COVERED] The sources do not say how long each course is."

        [result] = evaluate([make_case(COVERED, expected_url=FAQ_URL)], CHUNKS, generate)

        assert result["passed"] is True
        assert result["contact"] is True


# Evidence recorded for each question
class TestRecordedEvidence:
    def test_result_records_answer_sources_and_contact(self):
        result = run_one(make_case(COVERED, expected_url=FAQ_URL))

        assert result["question"] == COVERED
        assert result["expected"] == "answer"
        assert result["answer"] == FAKE_ANSWER
        assert result["sources"] == [FAQ_URL]
        assert result["contact"] is False

    def test_fallback_result_records_the_contact_link(self):
        result = run_one(make_case(UNRELATED, expected="fallback"))

        assert result["sources"] == []
        assert result["contact"] is True

    def test_known_issue_is_shown_in_notes(self):
        issue = "Retrieval misses the FAQ page"

        result = run_one(make_case(COVERED, known_issue=issue))

        assert issue in result["notes"]

    def test_keeps_the_order_of_the_question_set(self):
        cases = [make_case(UNRELATED, case_id="q01"), make_case(COVERED, case_id="q02")]

        results = evaluate(cases, CHUNKS, fake_generate)

        assert [result["id"] for result in results] == ["q01", "q02"]


# The Markdown evidence table
class TestFormatResults:
    def test_format_results_has_the_evidence_columns(self):
        results = evaluate([make_case(COVERED)], CHUNKS, fake_generate)

        table = format_results(results)

        assert "| question | expected | actual answer | sources | pass/fail | notes |" in table
        assert COVERED in table
        assert FAQ_URL in table

    def test_format_results_counts_passes(self):
        cases = [
            make_case(COVERED, expected_url=FAQ_URL, case_id="q01"),
            make_case(COVERED, expected="fallback", case_id="q02"),
        ]

        table = format_results(evaluate(cases, CHUNKS, fake_generate))

        assert table.endswith("1 of 2 automated evaluation checks passed")

    def test_answers_with_line_breaks_or_pipes_stay_in_one_table_row(self):
        # A real model may answer with several lines or a "|"; neither may break the table
        def generate(prompt):
            return "Yes | free.\nSee the FAQ."

        results = evaluate([make_case(COVERED)], CHUNKS, generate)

        rows = [line for line in format_results(results).splitlines() if COVERED in line]
        assert len(rows) == 1
        assert rows[0].count(" | ") == 5


# Iteration "stay under Gemini's free-tier limit": 15 requests per minute. A fake sleep records
# the pauses instead of waiting, so these tests stay fast.
class TestPacing:
    def test_the_pause_keeps_a_run_under_15_calls_per_minute(self):
        assert 60 / PAUSE_SECONDS < 15

    # AC-P1
    def test_the_first_call_does_not_wait_and_every_later_call_does(self):
        pauses = []
        prompts = []

        def generate(prompt):
            prompts.append(prompt)
            return f"answer to {prompt}"

        paced_generate = paced(generate, sleep=pauses.append)

        assert paced_generate("first") == "answer to first"
        assert pauses == []
        assert paced_generate("second") == "answer to second"
        assert paced_generate("third") == "answer to third"
        assert pauses == [PAUSE_SECONDS, PAUSE_SECONDS]
        assert prompts == ["first", "second", "third"]

    # AC-P2
    def test_run_paces_gemini_calls(self, monkeypatch, tmp_path):
        pauses = []
        monkeypatch.setattr(run_evaluation, "choose_generate", lambda fallback: fake_generate)
        monkeypatch.setattr(run_evaluation.time, "sleep", pauses.append)
        cases = [make_case(COVERED, case_id="q01"), make_case(COVERED, case_id="q02")]
        monkeypatch.setattr(run_evaluation, "load_questions", lambda: cases)
        monkeypatch.setattr(run_evaluation, "load_chunks", lambda: CHUNKS)

        run_evaluation.run(output_path=tmp_path / "results.md")

        assert pauses == [PAUSE_SECONDS]

    def test_run_does_not_pace_demo_mode(self, monkeypatch, tmp_path):
        pauses = []
        monkeypatch.setattr(run_evaluation, "choose_generate", lambda fallback: demo_generate)
        monkeypatch.setattr(run_evaluation.time, "sleep", pauses.append)
        cases = [make_case(COVERED, case_id="q01"), make_case(COVERED, case_id="q02")]
        monkeypatch.setattr(run_evaluation, "load_questions", lambda: cases)
        monkeypatch.setattr(run_evaluation, "load_chunks", lambda: CHUNKS)

        run_evaluation.run(output_path=tmp_path / "results.md")

        assert pauses == []
