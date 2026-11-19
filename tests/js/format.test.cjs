// Tests for static/js/format.js (specs/ui_redesign.md, "Iteration: readable answers", AC12).
// Run with Node's built-in test runner: node --test tests/js/
// Jest (the leftover practice setup) skips tests/js/ (package.json, testPathIgnorePatterns).
const test = require("node:test");
const assert = require("node:assert/strict");
const { answerBlocks, initialSourceCount } = require("../../static/js/format.js");

test("one line is one paragraph", () => {
  assert.deepEqual(answerBlocks("ReDI courses are free."), [
    { type: "p", text: "ReDI courses are free." },
  ]);
});

test("an empty line separates paragraphs", () => {
  assert.deepEqual(answerBlocks("First paragraph.\n\nSecond paragraph."), [
    { type: "p", text: "First paragraph." },
    { type: "p", text: "Second paragraph." },
  ]);
});

test("a single line break stays inside the paragraph", () => {
  assert.deepEqual(answerBlocks("Line one\nline two"), [
    { type: "p", text: "Line one\nline two" },
  ]);
});

test("several empty lines and surrounding spaces don't create empty paragraphs", () => {
  assert.deepEqual(answerBlocks("\n\n  First.  \n\n\n\nSecond.\n\n"), [
    { type: "p", text: "First." },
    { type: "p", text: "Second." },
  ]);
});

test("Windows line endings are handled", () => {
  assert.deepEqual(answerBlocks("First.\r\n\r\n- a\r\n- b"), [
    { type: "p", text: "First." },
    { type: "ul", items: ["a", "b"] },
  ]);
});

test("lines starting with -, * or • form one bullet list", () => {
  assert.deepEqual(answerBlocks("- Python\n* Data Analytics\n• Cloud Computing"), [
    { type: "ul", items: ["Python", "Data Analytics", "Cloud Computing"] },
  ]);
});

test("numbered lines form a numbered list", () => {
  assert.deepEqual(answerBlocks("1. Fill in the form.\n2. Do the test.\n3) Wait for the answer."), [
    { type: "ol", items: ["Fill in the form.", "Do the test.", "Wait for the answer."], start: 1 },
  ]);
});

test("a numbered list starts at its first number", () => {
  assert.deepEqual(answerBlocks("3. Third step\n4. Fourth step"), [
    { type: "ol", items: ["Third step", "Fourth step"], start: 3 },
  ]);
});

test("a list right after a sentence, without an empty line, is still a list", () => {
  assert.deepEqual(answerBlocks("Courses in Munich:\n- Python\n- Java\nApply on the website."), [
    { type: "p", text: "Courses in Munich:" },
    { type: "ul", items: ["Python", "Java"] },
    { type: "p", text: "Apply on the website." },
  ]);
});

test("a bullet list followed by a numbered list are two lists", () => {
  assert.deepEqual(answerBlocks("- a\n- b\n1. c\n2. d"), [
    { type: "ul", items: ["a", "b"] },
    { type: "ol", items: ["c", "d"], start: 1 },
  ]);
});

test("an indented line continues the list item above it", () => {
  assert.deepEqual(answerBlocks("- Python\n  for beginners\n- Java"), [
    { type: "ul", items: ["Python for beginners", "Java"] },
  ]);
});

test("an empty line between items doesn't split the list", () => {
  assert.deepEqual(answerBlocks("- a\n\n- b"), [
    { type: "ul", items: ["a", "b"] },
  ]);
});

test("a dash without a space, or a number without a dot, is ordinary text", () => {
  assert.deepEqual(answerBlocks("-5 degrees\n2024 was a good year"), [
    { type: "p", text: "-5 degrees\n2024 was a good year" },
  ]);
});

test("an empty bullet is left out", () => {
  assert.deepEqual(answerBlocks("- a\n- \n- b"), [
    { type: "ul", items: ["a", "b"] },
  ]);
});

test("an empty answer has no blocks", () => {
  assert.deepEqual(answerBlocks(""), []);
  assert.deepEqual(answerBlocks("  \n \n"), []);
  assert.deepEqual(answerBlocks(undefined), []);
});

test("markup stays text: nothing is interpreted as HTML or Markdown", () => {
  assert.deepEqual(answerBlocks("<script>alert('x')</script>\n- **bold** <b>tag</b>"), [
    { type: "p", text: "<script>alert('x')</script>" },
    { type: "ul", items: ["**bold** <b>tag</b>"] },
  ]);
});

test("up to four sources are all shown at first", () => {
  for (const count of [0, 1, 2, 3, 4]) {
    assert.equal(initialSourceCount(count), count);
  }
});

test("with five or more sources, three are shown at first", () => {
  for (const count of [5, 6, 9]) {
    assert.equal(initialSourceCount(count), 3);
  }
});
