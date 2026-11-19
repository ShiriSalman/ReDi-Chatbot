// Answer formatting (specs/ui_redesign.md, "Iteration: readable answers").
// These functions only look at the *structure* of the text (paragraphs, list lines) and return
// plain data; they never create HTML. chat.js builds the elements and fills them with textContent,
// so markup in an answer, such as <script> or **bold**, stays visible as text.
// Tested in tests/js/format.test.cjs.

// "- ", "* " or "• " at the start of a line: a bullet point
const BULLET_LINE = /^\s*[-*•]\s+(.*)$/;
// A number followed by "." or ")" and a space, such as "1. " or "2) ": a numbered step
const NUMBERED_LINE = /^\s*(\d{1,3})[.)]\s+(.*)$/;
// A line that starts with spaces continues the list item above it
const INDENTED_LINE = /^\s+\S/;

// Splits an answer into blocks: {type: "p", text}, {type: "ul", items} or {type: "ol", items, start}
function answerBlocks(text) {
  const blocks = [];
  let current = null; // the block the next line may belong to
  let afterEmptyLine = false;

  for (const line of String(text ?? "").split(/\r?\n/)) {
    const trimmed = line.trim();

    // An empty line ends a paragraph; a list may go on after it ("- a", "", "- b" is one list)
    if (!trimmed) {
      if (current && current.type === "p") {
        current = null;
      }
      afterEmptyLine = true;
      continue;
    }

    const bullet = line.match(BULLET_LINE);
    const numbered = bullet ? null : line.match(NUMBERED_LINE);

    if (bullet || numbered) {
      const type = bullet ? "ul" : "ol";
      if (!current || current.type !== type) {
        current = type === "ul" ? { type, items: [] } : { type, items: [], start: Number(numbered[1]) };
        blocks.push(current);
      }
      const item = (bullet ? bullet[1] : numbered[2]).trim();
      if (item) {
        current.items.push(item);
      }
    } else if (current && current.type !== "p" && current.items.length && !afterEmptyLine && INDENTED_LINE.test(line)) {
      const last = current.items.length - 1;
      current.items[last] = `${current.items[last]} ${trimmed}`;
    } else if (current && current.type === "p") {
      current.text = `${current.text}\n${trimmed}`;
    } else {
      current = { type: "p", text: trimmed };
      blocks.push(current);
    }
    afterEmptyLine = false;
  }

  // A list made only of empty bullets ("- ") has nothing to show
  return blocks.filter((block) => block.type === "p" || block.items.length > 0);
}

// How many source chips are shown before "+ N more". A "+ 1 more" button would save almost no
// space, so up to four sources are all shown.
const SOURCES_SHOWN_AT_FIRST = 3;

function initialSourceCount(total) {
  return total <= SOURCES_SHOWN_AT_FIRST + 1 ? total : SOURCES_SHOWN_AT_FIRST;
}

// In the browser the functions above are globals for chat.js; Node's tests load them with require()
if (typeof module !== "undefined" && module.exports) {
  module.exports = { answerBlocks, initialSourceCount };
}
