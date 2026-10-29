# Tests for the chat web app, written from specs/task6_chat_interface.md.
# src/app.py does not exist yet, so every test fails until it is written.
# The app gets its chunks and generate function passed in, so no real model or data file is used.
import json
import logging
from pathlib import Path

import pytest

from app import create_app, demo_generate, load_chunks, log_startup
from grounding import NOT_ENOUGH_INFO
from llm import MODEL

FAQ_URL = "https://www.redi-school.org/faq"
APPLY_URL = "https://www.redi-school.org/apply"
CHAT_JS = Path(__file__).parent.parent / "static" / "js" / "chat.js"
SOURCES_FILE = Path(__file__).parent.parent / "data" / "sources.json"

# From specs/task6_contact_link.md
CONTACT = {"title": "ReDI contact page", "url": "https://www.redi-school.org/contact"}

SUPPORTED_QUESTION = "Are the courses free?"
UNRELATED_QUESTION = "What will the weather be like in Tokyo tomorrow?"


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


FREE_CHUNK = make_chunk("All our courses are free of charge for every learner.")
MALMO_CHUNK = make_chunk(
    "The ReDI office in Malmö is located close to the central station.",
    url="https://www.redi-school.org/redi-school-malmo",
    title="ReDI School Malmö",
)
CHUNKS = [FREE_CHUNK, MALMO_CHUNK]


def fake_generate(answer="Yes, ReDI courses are free of charge."):
    """Returns a generate function that gives the same answer and records the prompts."""
    prompts = []

    def generate(prompt):
        prompts.append(prompt)
        return answer

    generate.prompts = prompts
    return generate


def make_client(chunks=CHUNKS, generate=None):
    app = create_app(chunks=chunks, generate=generate or fake_generate())
    app.config["TESTING"] = True
    return app.test_client()


def ask(client, question):
    return client.post("/api/chat", json={"question": question})


# AC1: The chat page loads
class TestChatPage:
    def test_get_returns_the_chat_page(self):
        response = make_client().get("/")

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "ReDI School Chatbot" in html
        assert "<input" in html or "<textarea" in html
        assert "Send" in html

    def test_loading_the_page_does_not_call_the_model(self):
        generate = fake_generate()

        make_client(generate=generate).get("/")

        assert generate.prompts == []


# AC2 + AC3: A question gets a grounded answer with Task 5 citations
class TestGroundedAnswer:
    def test_supported_question_returns_answer_and_sources(self):
        response = ask(make_client(), SUPPORTED_QUESTION)

        assert response.status_code == 200
        assert response.get_json() == {
            "answer": "Yes, ReDI courses are free of charge.",
            "enough_information": True,
            "sources": [{"title": "FAQ", "url": FAQ_URL}],
        }

    def test_the_question_goes_through_the_task3_answer_flow(self):
        generate = fake_generate()

        ask(make_client(generate=generate), SUPPORTED_QUESTION)

        # The prompt is built by Task 3: it holds the question and only the relevant chunk
        assert len(generate.prompts) == 1
        assert SUPPORTED_QUESTION in generate.prompts[0]
        assert FREE_CHUNK["text"] in generate.prompts[0]
        assert MALMO_CHUNK["text"] not in generate.prompts[0]

    def test_raw_chunk_text_is_not_returned_as_a_source(self):
        response = ask(make_client(), SUPPORTED_QUESTION)

        assert FREE_CHUNK["text"] not in json.dumps(response.get_json()["sources"])


# AC4: Citation links without duplicates or invented URLs
class TestCitations:
    def test_duplicate_chunks_from_one_page_produce_one_citation(self):
        chunks = [
            make_chunk("All our courses are free of charge."),
            make_chunk("Our courses are free for every learner."),
        ]

        response = ask(make_client(chunks=chunks), SUPPORTED_QUESTION)

        assert response.get_json()["sources"] == [{"title": "FAQ", "url": FAQ_URL}]

    def test_invalid_source_urls_are_not_returned_as_links(self):
        chunks = [
            make_chunk("All our courses are free of charge.", url=APPLY_URL, title="Apply"),
            make_chunk("Courses are free for every learner.", url="javascript:alert(1)", title="Old page"),
        ]

        response = ask(make_client(chunks=chunks), SUPPORTED_QUESTION)

        sources = response.get_json()["sources"]
        for source in sources:
            assert source["url"] is None or source["url"].startswith(("http://", "https://"))
        assert "javascript:" not in response.get_data(as_text=True)
        assert {"title": "Apply", "url": APPLY_URL} in sources

    def test_urls_written_in_the_answer_do_not_become_sources(self):
        generate = fake_generate("Read more at https://made-up.example/courses")

        response = ask(make_client(generate=generate), SUPPORTED_QUESTION)

        urls = [source["url"] for source in response.get_json()["sources"]]
        assert urls == [FAQ_URL]


# AC5: No relevant content
class TestNoRelevantContent:
    def test_unrelated_question_returns_the_fallback_without_sources(self):
        # Also covers specs/task6_contact_link.md AC1 and AC4:
        # the contact link is its own field and never one of the sources
        response = ask(make_client(), UNRELATED_QUESTION)

        assert response.status_code == 200
        assert response.get_json() == {
            "answer": NOT_ENOUGH_INFO,
            "enough_information": False,
            "sources": [],
            "contact": CONTACT,
        }

    def test_the_model_is_not_called(self):
        generate = fake_generate()

        ask(make_client(generate=generate), UNRELATED_QUESTION)

        assert generate.prompts == []


# AC6: Empty questions are rejected
class TestEmptyQuestion:
    @pytest.mark.parametrize("question", ["", "   ", "\n\t "])
    def test_blank_question_returns_400(self, question):
        response = ask(make_client(), question)

        assert response.status_code == 400
        assert response.get_json() == {"error": "Please enter a question."}

    def test_blank_question_does_not_call_the_model(self):
        generate = fake_generate()

        ask(make_client(generate=generate), "   ")

        assert generate.prompts == []


# Question length (spec section 7 and 8): the server enforces the same 500-character limit as the page
class TestQuestionLength:
    def test_question_over_500_characters_returns_400(self):
        generate = fake_generate()

        response = ask(make_client(generate=generate), "a" * 501)

        assert response.status_code == 400
        assert response.get_json() == {"error": "Please keep your question under 500 characters."}
        assert generate.prompts == []

    def test_question_of_exactly_500_characters_is_accepted(self):
        question = SUPPORTED_QUESTION + " " * 10 + "x" * (500 - len(SUPPORTED_QUESTION) - 10)

        response = ask(make_client(), question)

        assert response.status_code == 200

    def test_length_is_measured_after_trimming(self):
        # Spaces around a normal question must not push it over the limit
        response = ask(make_client(), " " * 600 + SUPPORTED_QUESTION + " " * 600)

        assert response.status_code == 200


# Invalid requests (spec section 7 and suggested test 6)
class TestInvalidRequest:
    def test_missing_json_body_returns_400(self):
        response = make_client().post("/api/chat")

        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_malformed_json_returns_400(self):
        response = make_client().post(
            "/api/chat", data="{not valid json", content_type="application/json"
        )

        assert response.status_code == 400
        assert "error" in response.get_json()

    @pytest.mark.parametrize("body", [{}, {"question": 42}, {"question": None}, ["Are the courses free?"]])
    def test_missing_or_non_string_question_returns_400(self, body):
        response = make_client().post("/api/chat", json=body)

        assert response.status_code == 400
        assert "error" in response.get_json()


# Unavailable ingested content (spec section 7 and 8)
class TestUnavailableContent:
    def test_no_ingested_chunks_returns_503(self):
        response = ask(make_client(chunks=[]), SUPPORTED_QUESTION)

        assert response.status_code == 503
        assert response.get_json() == {
            "error": "ReDI information is temporarily unavailable. Please try again later."
        }

    def test_load_chunks_reads_the_saved_chunks_file(self, tmp_path):
        path = tmp_path / "chunks.json"
        path.write_text(json.dumps([FREE_CHUNK], ensure_ascii=False), encoding="utf-8")

        assert load_chunks(path) == [FREE_CHUNK]

    def test_load_chunks_returns_an_empty_list_when_the_file_is_missing(self, tmp_path):
        assert load_chunks(tmp_path / "missing.json") == []


# AC7: Server and generation errors
class TestGenerationFailure:
    def test_generator_exception_returns_a_friendly_500(self):
        def broken_generate(prompt):
            raise RuntimeError("API key sk-secret-123 rejected at C:\\Users\\internal\\llm.py")

        response = ask(make_client(generate=broken_generate), SUPPORTED_QUESTION)

        assert response.status_code == 500
        assert response.get_json() == {
            "error": "Something went wrong while answering your question. Please try again."
        }

    def test_error_responses_hide_internal_details(self):
        def broken_generate(prompt):
            raise RuntimeError("API key sk-secret-123 rejected at C:\\Users\\internal\\llm.py")

        body = ask(make_client(generate=broken_generate), SUPPORTED_QUESTION).get_data(as_text=True)

        assert "sk-secret-123" not in body
        assert "internal" not in body
        assert "Traceback" not in body
        assert "Sources:" not in body  # no raw prompt

    def test_the_app_keeps_working_after_an_error(self):
        calls = []

        def flaky_generate(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                raise RuntimeError("temporary failure")
            return "Yes, ReDI courses are free of charge."

        client = make_client(generate=flaky_generate)

        assert ask(client, SUPPORTED_QUESTION).status_code == 500
        assert ask(client, SUPPORTED_QUESTION).status_code == 200


# AC9: Safe rendering (backend side, plus a check on the browser script)
class TestSafeRendering:
    def test_html_in_the_answer_is_returned_as_plain_json_text(self):
        # The API returns text unchanged as JSON; the browser must display it as text
        generate = fake_generate("<script>alert('x')</script>")

        response = ask(make_client(generate=generate), SUPPORTED_QUESTION)

        assert response.is_json
        assert response.get_json()["answer"] == "<script>alert('x')</script>"

    def test_chat_script_does_not_use_inner_html(self):
        # A simple guard for AC9: answers and titles must be shown with textContent
        script = CHAT_JS.read_text(encoding="utf-8")

        assert "innerHTML" not in script


# Contact link for unanswered questions, written from specs/task6_contact_link.md.
# AC1, AC2 and AC4 are covered by TestNoRelevantContent above; AC6 is checked manually.
class TestContactLink:
    # AC3
    def test_answered_question_has_no_contact_link(self):
        response = ask(make_client(), SUPPORTED_QUESTION)

        assert response.status_code == 200
        assert "contact" not in response.get_json()

    # specs/task8_fix_contact_link_not_covered.md, AC6: the model says the sources don't
    # cover the question, so the visitor gets the contact link as well as the sources
    def test_marked_answer_shows_sources_and_the_contact_link(self):
        generate = fake_generate("[NOT COVERED] The sources do not say how long each course is.")

        data = ask(make_client(generate=generate), SUPPORTED_QUESTION).get_json()

        assert data == {
            "answer": "The sources do not say how long each course is.",
            "enough_information": False,
            "sources": [{"title": "FAQ", "url": FAQ_URL}],
            "contact": CONTACT,
        }

    # AC5
    def test_contact_url_is_an_approved_source(self):
        sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))

        approved_urls = [source["url"] for source in sources if source["include"] == "Yes"]
        assert CONTACT["url"] in approved_urls

    # AC7
    @pytest.mark.parametrize("case", ["blank question", "no content", "model error"])
    def test_error_responses_have_no_contact_link(self, case):
        def broken_generate(prompt):
            raise RuntimeError("model failed")

        if case == "blank question":
            response = ask(make_client(), "   ")
        elif case == "no content":
            response = ask(make_client(chunks=[]), SUPPORTED_QUESTION)
        else:
            response = ask(make_client(generate=broken_generate), SUPPORTED_QUESTION)

        assert response.status_code in (400, 503, 500)
        assert "contact" not in response.get_json()


# specs/task9_deploy_render.md, AC8: on a server nobody watches the page, so a missing key or
# missing content must show up in the log when the app starts, not only in visitors' answers
class TestStartupLog:
    def startup_messages(self, caplog, chunks, generate):
        app = create_app(chunks=chunks, generate=generate)
        with caplog.at_level(logging.INFO):
            log_startup(app, chunks, generate)
        return [(record.levelno, record.getMessage()) for record in caplog.records]

    def test_logs_an_error_when_no_content_is_loaded(self, caplog):
        messages = self.startup_messages(caplog, [], fake_generate())

        assert any(level == logging.ERROR and "No ReDI content" in text for level, text in messages)

    def test_warns_in_demo_mode(self, caplog):
        messages = self.startup_messages(caplog, CHUNKS, demo_generate)

        assert any(
            level == logging.WARNING and "Demo mode" in text and "GEMINI_API_KEY" in text
            for level, text in messages
        )

    def test_names_the_model_and_the_number_of_chunks_otherwise(self, caplog):
        messages = self.startup_messages(caplog, CHUNKS, fake_generate())

        assert (logging.INFO, f"Answering with Gemini ({MODEL}) from {len(CHUNKS)} chunks.") in messages
        assert all(level < logging.WARNING for level, _ in messages)
