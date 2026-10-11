# Task 3 – Answer Grounding Specification

## Goal

Design how the chatbot finds relevant information from the ingested ReDI
content and uses only that information to generate an accurate answer.

The chatbot should not invent information when the available ReDI content
does not support an answer.

---

## What this feature does

- receives a user question
- finds relevant chunks from the ingested ReDI content
- uses the retrieved chunks as context for the answer
- generates an answer based only on the retrieved ReDI content
- avoids unsupported claims
- indicates when the available content is not sufficient to answer

---

## Out of scope

This change does not touch:

- content ingestion or website scraping
- audience differentiation
- how citations are displayed to the user
- conversational UI design
- deployment
- automatic content updates

---

## The interface

**Input:** A user question and the ingested ReDI content chunks.

**Output:** A grounded answer based on relevant ReDI content, or an indication
that there is not enough information to answer.

---

## Boundaries and failure modes

**Before:** Ingested ReDI content must be available.

**After:** The answer is based only on relevant retrieved ReDI content.

**What can go wrong:** No relevant content may be found, or the retrieved
content may not contain enough information to answer the question.

**What happens:** The chatbot does not invent an answer and indicates that
the available ReDI sources do not provide enough information.

---

## Scenario 1 – Find relevant content

**Given** ingested ReDI content is available  
**And** a user asks a question covered by that content  
**When** the retrieval process runs  
**Then** relevant content chunks should be selected.

---

## Scenario 2 – Ignore unrelated content

**Given** the content collection contains both relevant and unrelated chunks  
**When** a user asks a question  
**Then** unrelated chunks should not be used as supporting context.

---

## Scenario 3 – Generate an answer from retrieved content

**Given** relevant chunks have been retrieved  
**When** the chatbot generates an answer  
**Then** the answer should be based on the information in those chunks  
**And** it should not add unsupported information.

---

## Scenario 4 – No relevant content found

**Given** a user asks a question that is not covered by the ingested content  
**When** no relevant chunks are found  
**Then** the chatbot should indicate that the available ReDI content does not
provide enough information to answer.

---

## Scenario 5 – Retrieved content is insufficient

**Given** relevant content is found  
**But** the content does not contain enough information to fully answer the question  
**When** the chatbot generates a response  
**Then** it should answer only what is supported  
**And** it should not invent the missing information.

---

## Scenario 6 – Conflicting retrieved content

**Given** multiple relevant chunks contain conflicting information  
**When** the chatbot prepares an answer  
**Then** it should not silently choose unsupported information  
**And** the conflict should be indicated rather than resolved by guessing.

---

## Scenario 7 – Preserve source information

**Given** chunks are selected to support an answer  
**When** they are passed to the answer-generation step  
**Then** their source metadata should remain attached  
**So that** citations can be added later.