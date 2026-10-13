# Tests for answer grounding, written from specs/task3_answer_grounding.md.
# src/grounding.py does not exist yet, so every test fails until it is written.
# The generate function (the LLM call) is passed in, so the tests never call a real model.
# Whether the model really follows the rules is checked with real questions in Task 8;
# these tests check that our code gives it the right context and instructions.
import pytest

from grounding import NOT_ENOUGH_INFO, answer_question, build_prompt, retrieve


def make_chunk(text, **overrides):
    chunk = {
        "text": text,
        "url": "https://www.redi-school.org/faq",
        "title": "FAQ",
        "category": "Applications",
        "language": "en",
        "last_updated": "unavailable",
    }
    chunk.update(overrides)
    return chunk


FREE_CHUNK = make_chunk("All our courses are free of charge for every learner.")
SCHEDULE_CHUNK = make_chunk(
    "Courses take place on Tuesday and Thursday evenings from 19:00 to 21:00.",
    url="https://www.redi-school.org/course-finder",
    title="Course Finder",
    category="Courses",
)
MALMO_CHUNK = make_chunk(
    "The ReDI office in Malmö is located close to the central station.",
    url="https://www.redi-school.org/redi-school-malmo",
    title="ReDI School Malmö",
    category="Locations",
)
VOLUNTEER_CHUNK = make_chunk(
    "Volunteers can support learners as mentors or teachers.",
    url="https://www.redi-school.org/volunteer",
    title="Volunteer",
    category="Get involved",
)

ALL_CHUNKS = [FREE_CHUNK, SCHEDULE_CHUNK, MALMO_CHUNK, VOLUNTEER_CHUNK]


def fake_generate(answer="Yes, all courses are free."):
    """Returns a generate function that gives the same answer and records the prompts."""
    prompts = []

    def generate(prompt):
        prompts.append(prompt)
        return answer

    generate.prompts = prompts
    return generate


# Boundaries: ingested ReDI content must be available
class TestContentMustBeAvailable:
    def test_raises_an_error_when_there_is_no_ingested_content(self):
        with pytest.raises(ValueError):
            answer_question("Are the courses free?", chunks=[], generate=fake_generate())


# Scenario 1: Find relevant content
class TestFindRelevantContent:
    def test_selects_the_chunk_that_answers_the_question(self):
        selected = retrieve("Are the courses free?", ALL_CHUNKS)

        assert FREE_CHUNK in selected

    def test_selects_a_different_chunk_for_a_different_question(self):
        selected = retrieve("On which evenings do the courses take place?", ALL_CHUNKS)

        assert SCHEDULE_CHUNK in selected


# Scenario 2: Ignore unrelated content
class TestIgnoreUnrelatedContent:
    def test_does_not_select_unrelated_chunks(self):
        selected = retrieve("Are the courses free?", ALL_CHUNKS)

        assert MALMO_CHUNK not in selected
        assert VOLUNTEER_CHUNK not in selected

    def test_unrelated_chunks_are_not_passed_to_the_model(self):
        generate = fake_generate()

        answer_question("Are the courses free?", ALL_CHUNKS, generate=generate)

        prompt = generate.prompts[0]
        assert MALMO_CHUNK["text"] not in prompt
        assert VOLUNTEER_CHUNK["text"] not in prompt


# Scenario 3: Generate an answer from retrieved content
class TestAnswerFromRetrievedContent:
    def test_the_prompt_contains_the_question_and_the_retrieved_text(self):
        prompt = build_prompt("Are the courses free?", [FREE_CHUNK])

        assert "Are the courses free?" in prompt
        assert FREE_CHUNK["text"] in prompt

    def test_the_prompt_tells_the_model_to_use_only_the_given_content(self):
        prompt = build_prompt("Are the courses free?", [FREE_CHUNK])

        assert "only" in prompt.lower()

    def test_returns_the_answer_from_the_model(self):
        generate = fake_generate("Yes, all courses are free.")

        result = answer_question("Are the courses free?", ALL_CHUNKS, generate=generate)

        assert result.text == "Yes, all courses are free."
        assert result.enough_information is True


# Scenario 4: No relevant content found
class TestNoRelevantContent:
    QUESTION = "What will the weather be like in Tokyo tomorrow?"

    def test_retrieves_nothing_for_a_question_the_content_does_not_cover(self):
        assert retrieve(self.QUESTION, ALL_CHUNKS) == []

    def test_says_there_is_not_enough_information(self):
        result = answer_question(self.QUESTION, ALL_CHUNKS, generate=fake_generate())

        assert result.text == NOT_ENOUGH_INFO
        assert result.enough_information is False
        assert result.sources == []

    def test_does_not_call_the_model(self):
        # Without any content there is nothing to ground an answer on,
        # so the model gets no chance to answer from general knowledge
        generate = fake_generate()

        answer_question(self.QUESTION, ALL_CHUNKS, generate=generate)

        assert generate.prompts == []


# Scenario 5: Retrieved content is insufficient
class TestInsufficientContent:
    def test_the_prompt_tells_the_model_to_say_what_the_content_does_not_cover(self):
        prompt = build_prompt("Are the courses free and how long is each course?", [FREE_CHUNK])

        lowered = prompt.lower()
        assert "not" in lowered and ("enough" in lowered or "cover" in lowered)

    def test_returns_the_partial_answer_with_its_sources(self):
        partial = "All courses are free. The sources do not say how long each course is."
        generate = fake_generate(partial)

        result = answer_question(
            "Are the courses free and how long is each course?", ALL_CHUNKS, generate=generate
        )

        assert result.text == partial
        assert FREE_CHUNK in result.sources


# Scenario 6: Conflicting retrieved content
class TestConflictingContent:
    DEADLINE_MARCH = make_chunk(
        "The application deadline for the spring semester is 1 March.",
        url="https://www.redi-school.org/faq",
    )
    DEADLINE_FEBRUARY = make_chunk(
        "The application deadline for the spring semester is 15 February.",
        url="https://www.redi-school.org/apply",
        title="Apply",
    )

    def test_retrieves_both_conflicting_chunks(self):
        chunks = [self.DEADLINE_MARCH, self.DEADLINE_FEBRUARY, MALMO_CHUNK]

        selected = retrieve("What is the application deadline for the spring semester?", chunks)

        assert self.DEADLINE_MARCH in selected
        assert self.DEADLINE_FEBRUARY in selected

    def test_both_conflicting_chunks_reach_the_model(self):
        chunks = [self.DEADLINE_MARCH, self.DEADLINE_FEBRUARY, MALMO_CHUNK]
        generate = fake_generate()

        answer_question(
            "What is the application deadline for the spring semester?", chunks, generate=generate
        )

        prompt = generate.prompts[0]
        assert self.DEADLINE_MARCH["text"] in prompt
        assert self.DEADLINE_FEBRUARY["text"] in prompt

    def test_the_prompt_tells_the_model_to_point_out_conflicts(self):
        prompt = build_prompt(
            "What is the application deadline?", [self.DEADLINE_MARCH, self.DEADLINE_FEBRUARY]
        )

        assert "conflict" in prompt.lower()


# Scenario 7: Preserve source information
class TestPreserveSourceInformation:
    def test_retrieved_chunks_keep_all_their_metadata(self):
        selected = retrieve("Are the courses free?", ALL_CHUNKS)

        for chunk in selected:
            for key in ["url", "title", "category", "language", "last_updated"]:
                assert chunk[key] == next(c for c in ALL_CHUNKS if c["text"] == chunk["text"])[key]

    def test_the_prompt_includes_the_source_url_of_each_chunk(self):
        prompt = build_prompt("Are the courses free?", [FREE_CHUNK, SCHEDULE_CHUNK])

        assert FREE_CHUNK["url"] in prompt
        assert SCHEDULE_CHUNK["url"] in prompt

    def test_the_answer_lists_the_chunks_it_was_based_on(self):
        result = answer_question("Are the courses free?", ALL_CHUNKS, generate=fake_generate())

        assert FREE_CHUNK in result.sources
        for chunk in result.sources:
            assert chunk["url"]
