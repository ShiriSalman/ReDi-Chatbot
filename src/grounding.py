"""Answer grounding: finds the ReDI chunks that match a question and answers only from them.

See specs/task3_answer_grounding.md for the expected behavior and
tests/test_grounding.py for the tests.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass

# Shown when the ingested content does not cover a question
NOT_ENOUGH_INFO = "The available ReDI sources do not provide enough information to answer this question."

# The rules the model gets with every question. Edit the wording here.
INSTRUCTIONS = """You answer questions about ReDI School of Digital Integration for the general public.

Use only the ReDI sources below. Do not use general knowledge and do not guess.

- If the sources answer the question, answer it clearly and briefly in English.
- If the sources cover only part of the question, answer that part and say which part the sources do not cover.
- If the sources do not contain enough information to answer, say so. Do not make up an answer.
- If the sources contain conflicting information, point out the conflict and name both sources instead of choosing one."""

# BM25 settings, the usual defaults:
# K1 controls how quickly repeated words stop adding points,
# B controls how much long chunks are scaled down
K1 = 1.5
B = 0.75

# A chunk counts as relevant only if it contains at least this share of the question's words,
# so one shared word ("tomorrow") is not enough. At most TOP_K chunks are returned.
# Both are first guesses to tune with real questions in Task 8.
MIN_WORD_SHARE = 0.5
TOP_K = 5

# Common words that say nothing about what a question is about
STOPWORDS = {
    "a", "about", "an", "and", "are", "at", "be", "can", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "like", "me", "my", "of", "on", "or", "the", "there",
    "to", "what", "when", "where", "which", "who", "will", "with", "you", "your",
}


def stem(word):
    """Reduce a plural to its singular form, so "courses" matches "course".

    Short words ("bus") and words ending in "ss" ("class") are kept as they are.
    """
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokenize(text):
    """Split text into lowercase words, without stopwords, with plurals reduced to the singular.

    Single letters and digits are dropped: they say nothing about a topic and matched
    by accident, for example the "b" of "<b>" with the "B." of "z. B.".
    """
    return [
        stem(word)
        for word in re.findall(r"\w+", text.lower())
        if len(word) > 1 and word not in STOPWORDS
    ]


def retrieve(question, chunks, top_k=TOP_K):
    """Return the chunks that best match the question, most relevant first.

    Chunks are scored with BM25 and returned unchanged, so their source metadata stays attached.
    Returns an empty list when no chunk contains at least MIN_WORD_SHARE of the question's words.
    """
    question_words = set(tokenize(question))
    if not question_words or not chunks:
        return []

    chunk_words = [tokenize(chunk["text"]) for chunk in chunks]
    average_length = sum(len(words) for words in chunk_words) / len(chunks)

    # In how many chunks each question word appears; rare words get a higher weight (IDF)
    chunk_counts = {
        word: sum(1 for words in chunk_words if word in words) for word in question_words
    }
    idf = {
        word: math.log((len(chunks) - count + 0.5) / (count + 0.5) + 1)
        for word, count in chunk_counts.items()
    }

    scored = []
    for chunk, words in zip(chunks, chunk_words):
        frequencies = Counter(words)
        matched = sum(1 for word in question_words if frequencies[word])
        if matched / len(question_words) < MIN_WORD_SHARE:
            continue

        length_factor = 1 - B + B * len(words) / average_length if average_length else 1
        score = 0.0
        for word in question_words:
            frequency = frequencies[word]
            if frequency:
                # Each extra mention adds less, so repeated text does not win on its own
                score += idf[word] * frequency * (K1 + 1) / (frequency + K1 * length_factor)
        scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def build_prompt(question, chunks):
    """Build the prompt that asks the model to answer only from the given chunks.

    Every source is numbered and shows its title and URL, so the model can tell
    the sources apart and name them when they conflict.
    """
    sources = "\n\n".join(
        f"[{number}] {chunk['title']} ({chunk['url']})\n{chunk['text']}"
        for number, chunk in enumerate(chunks, start=1)
    )
    return f"{INSTRUCTIONS}\n\nSources:\n\n{sources}\n\nQuestion: {question}"


@dataclass
class AnswerResult:
    text: str
    # False when the ingested content did not cover the question
    enough_information: bool
    # The chunks the answer is based on, with their source metadata, for citations later
    sources: list


def answer_question(question, chunks, generate):
    """Answer a question using only relevant ReDI chunks.

    generate(prompt) calls the model and returns its answer as text.
    Raises ValueError when there is no ingested content at all.
    """
    if not chunks:
        raise ValueError("No ingested ReDI content available.")

    relevant_chunks = retrieve(question, chunks)

    if not relevant_chunks:
        # Nothing to ground an answer on, so the model is not asked at all
        return AnswerResult(
            text=NOT_ENOUGH_INFO,
            enough_information=False,
            sources=[]
        )

    prompt = build_prompt(question, relevant_chunks)
    answer = generate(prompt)

    return AnswerResult(
        text=answer,
        enough_information=True,
        sources=relevant_chunks
    )
