# UI redesign – a clearer, friendlier chat page

**Project:** ReDI School Chatbot  
**Status:** Specification

## Goal

A modern, clean, professional chat page with a friendly welcome screen,
clickable categories with suggested questions, a clearer chat layout with
visible source links, a responsive design for phones, and a simple flow.

## Constraints

- **Same stack:** Flask, one template (`templates/chat.html`), one stylesheet
  (`static/css/chat.css`), one script (`static/js/chat.js`). No framework, no
  build step, no external fonts, scripts or CDNs.
- **Same behaviour:** `POST /api/chat` and its JSON are unchanged. Answers,
  titles and errors are shown with `textContent`, never `innerHTML`
  (`test_chat_script_does_not_use_inner_html`); links are checked with
  `isSafeUrl` and open in a new tab with `rel="noopener noreferrer"`; the
  question is put back after an error; an empty question shows "Please enter
  a question."
- **Same colours:** the ReDI tokens in `chat.css`, with text contrast of at
  least 4.5:1. Checked against the website's theme on 2026-11-19:
  `--accent` #f9d6c9, `--darkAccent` #58adc4 and `--lightAccent` #f3f9fb
  match exactly.
- **ReDI's font fallback:** redi-school.org uses Clarkson (licensed) with the
  fallback `"Helvetica Neue", Helvetica, Arial, sans-serif`. The chatbot uses
  that fallback, so it looks like the website without an external font.

## Review of the current page (2026-11-18)

Kept: ReDI colours with contrast rules, safe rendering, `role="log"` with
`aria-live`, a hidden label for the input, visible focus outlines, the
friendly error handling.

Improved:

| Today | Problem |
|---|---|
| Empty area under the header | Visitors don't know what to ask |
| The whole page scrolls; `min-height: 100vh` | The header scrolls away; on phones the input can hide behind the browser bar |
| Small bubbles, plain bullet list of sources | Plain; sources easy to miss |
| Contact link as one text line | Doesn't read as "what to do next" |
| "Looking for an answer…" outside the conversation | Feels disconnected |
| One-line input, invisible 500-character limit | Long questions are cramped |
| No privacy note | Visitors aren't told questions go to Google Gemini (follow-up from 2026-11-02) |

A clickable mockup was reviewed by the owner (scratchpad,
`redi-chatbot-mockup.html`).

## Design

### Layout
- **App shell:** a compact header and the composer stay in place; only the
  conversation scrolls. Height `100dvh`, with safe-area padding for phones.
- **Header:** "ReDI" mark, "ReDI School Chatbot", tagline "Answers from
  official ReDI pages, with links", and a **New chat** button (shown once a
  conversation has started).

### Welcome screen
Shown before the first question and after **New chat**:
- "Hi! What would you like to know about ReDI School?" and one sentence on
  what the bot does.
- **Six category cards with suggested questions.** Clicking a question
  **sends it immediately**, through the same code as typing it.
- A line "Can't find your question here? **Contact ReDI** ↗" (link to the
  contact page).
- "English only. I can't see personal information such as your application
  status."

**Suggested questions** (each checked with the real retrieval on 2026-11-19;
each finds the page it needs):

| Category | Questions |
|---|---|
| Applying | How do I apply for a course? · Can I apply if I'm under 18? |
| Courses | Which courses are there in Berlin? · Which courses are there in Munich? · Will I get a certificate? |
| Costs & who can join | Are ReDI courses free? · Do I need to speak German? · Are there courses only for women? |
| Locations | Where is ReDI School in Munich? |
| Career support | Does ReDI help me find a job? |
| Get involved | How can I become a volunteer at ReDI? · How can my company support ReDI? |

### Conversation
- **Visitor's question:** peach bubble on the right.
- **Answer:** "ReDI Chatbot" label with a small avatar, a white card with the
  teal edge, paragraphs kept (`pre-wrap`).
- **Sources:** "Sources" heading and **chips** (rounded links with an arrow
  icon). A source without a valid link: "<title> (no link available)", as
  today.
- **Contact:** when the server sends `contact`, a separate callout below the
  answer: "Need more help? You can ask ReDI directly." with a **Contact ReDI**
  button.
- **Error:** a red card, as today.
- **Waiting:** a typing indicator (three dots) inside the conversation; the
  `role="status"` text "Looking for an answer…" stays for screen readers.
  No animation with `prefers-reduced-motion`.
- **Scrolling:** after an answer, the visitor's question is scrolled to the
  top, so long answers are read from their first line.

### Composer
- A `<textarea>` that grows with the text (up to about 6 lines); **Enter**
  sends, **Shift+Enter** adds a line.
- A counter "42/500", highlighted from 450 characters.
- **Privacy note** below: "Please don't enter personal information. Your
  question is sent to Google Gemini, an AI service, to write the answer."
- The **Send** button keeps its text on wider screens and shows only the
  icon on phones (with an accessible label "Send").

### Responsive and accessible
- Category cards: 3 columns on desktop, 2 on tablets, 1 on phones.
- Touch targets at least 44 px; inputs 16 px so iOS doesn't zoom.
- Keyboard: every suggestion, link and button is reachable with Tab and
  shows the focus outline.

## Acceptance criteria

Checked by tests:
- **AC1** (`tests/test_app.py`): the page has the welcome screen, the six
  categories and 12 suggestion buttons, the privacy note, a `<textarea>` with
  `maxlength="500"`, and a button with the accessible name "Send".
- **AC2** (`tests/test_real_questions.py`): every suggested question on the
  page gets at least one source on the real content (no fallback, no small
  talk), so a suggestion never leads to "I can only answer…".
- **AC3:** the existing tests pass, including
  `test_chat_script_does_not_use_inner_html`.

Checked by hand (screenshots at 390 px and 1280 px, and with the keyboard):
- **AC4:** clicking a suggestion sends it; the welcome screen hides; New chat
  brings it back.
- **AC5:** an answer shows label, card, source chips and, with `contact`, the
  callout; an error shows the red card and the question is back in the box.
- **AC6:** Enter sends, Shift+Enter adds a line, the counter counts.
- **AC7:** no horizontal scrolling at 390 px; the composer stays visible.

## Steps

Each step is one commit; the full test suite runs after each.

1. App shell and design tokens (CSS, header markup).
2. Messages, source chips, contact callout (CSS, `addMessage`, `addSources`,
   `addContact`).
3. Typing indicator (`setLoading`).
4. Welcome screen, categories, New chat (+ AC1, AC2 tests first).
5. Composer: textarea, Enter/Shift+Enter, counter.
6. Responsive and accessibility pass (screenshots).
7. Privacy note (+ its test first).

## Iteration: category tabs (2026-11-19)

The six cards with all 12 questions filled the whole desktop screen and about
three phone screens before the input. The owner asked for a shorter welcome,
compact tabs, suggestions per tab, a cleaner input, and the chat as the main
focus.

**Constraint:** the backend, the API and the existing tests don't change. The
tabs only change what is *visible*: every category stays a `.category` with
an `<h3>` and its `button.suggestion` buttons in the HTML.

**Decisions (owner chose the recommended options):**
- Default tab: **Applying**.
- After the first message: a **Suggestions** button next to the input opens
  the tabs above it, without leaving the conversation.
- **SVG icons**, no emoji (emoji look different on every device).
- Own PR on top of the first redesign.

**Design:**
- **Welcome:** "Hi! What would you like to know about ReDI School?" and one
  line "Answers come from official ReDI pages, with links." (The question
  stays, because an existing test checks it.)
- **Tabs:** six compact category buttons in a grid — Applying, Courses,
  Costs, Locations, Careers, Get involved: one row on wide screens, 3 × 2 on
  phones (owner's follow-up: a grid, not a row that scrolls). The selected one
  is in the ReDI orange (the dark shade, for readable white text). Each
  category has at most three questions.
- **Panels:** only the active tab's questions show, as wrapping chips. Each
  panel keeps its full category name as a visually hidden `<h3>`.
- **Accessibility:** `role="tablist"`, `role="tab"` with `aria-selected` and
  `aria-controls`, `role="tabpanel"`; Left/Right/Home/End move between tabs;
  only the active tab is in the Tab order.
- **Input:** one rounded container with the Suggestions button, the text box
  and a round Send button inside. The counter is only visible from 400
  characters (it stays in the HTML). The privacy note gets a lock icon; its
  text doesn't change.
- **Send** is not disabled when the box is empty, so an empty question still
  shows "Please enter a question."

**Acceptance criteria:**
- **AC8:** six tabs, each pointing to a panel with `aria-controls`; only
  Applying is selected and visible at the start (unit test).
- **AC9:** the Suggestions button exists, starts hidden and collapsed
  (`aria-expanded="false"`) (unit test).
- **AC10:** all existing tests pass unchanged.
- **AC11** (by hand, 390 and 1280 px): switching tabs shows that tab's
  questions; arrow keys move between tabs; after the first answer the
  Suggestions button opens and closes the tabs above the input; a suggestion
  from there is sent; New chat brings the welcome back; no horizontal
  scrolling of the page.

## Iteration: final touches (2026-11-19)

Requested by the owner after the tabs:
- **Less empty space:** the welcome block is centred in the free space between
  header and input instead of sitting at the top.
- **Welcome text:** "Hi! How can I help you? 👋" and "Ask me anything about
  ReDI School or choose a topic below." `test_has_a_welcome_screen` checks the
  new wording (the old question was replaced on request).
- **Contact ReDI:** a small underlined text link instead of a highlighted
  button; its touch area stays 44 px.
- **Click feedback:** a clicked suggestion is pressed in and turns orange; the
  welcome fades out over 180 ms, then the question is sent. A second click in
  that moment is ignored.
- **Waiting logo:** 24 px, without a card frame; the dot pulses (60–115 %)
  and the arrow moves 10 of the mark's 100 units (3 units were about one
  screen pixel).
- **Reduced motion:** with Windows "Animation effects" off (the owner's
  setting), the browser reports `prefers-reduced-motion: reduce` and the logo
  stood still, so waiting wasn't visible. Now the dot fades slowly in and out
  (opacity 0.25–1, 1.6 s) without moving; the arrow stays still.
- Unchanged: the welcome hides after the first question, and the input stays
  at the bottom.

## Iteration: readable answers (2026-11-19)

Requested by the owner: long answers should be easier to read, lists should
look like lists, and the sources should take less space.

**Constraint:** the Flask API, Gemini, the sources and the retrieval don't
change in this step. The prompt still asks for plain paragraphs; allowing
lists in the prompt is a **separate step** (its own PR and Task 8 evaluation
run), so a change in the evaluation can be traced to the prompt or to the
page.

**Decisions (owner):** lists are clearer for visitors, so lists are wanted
(prompt in the next step); show three sources at first; this PR starts after
the final touches were merged.

**Design:**
- **Paragraphs:** the answer is split at empty lines into real paragraphs
  with space between them; line height 1.6; at most about 65 characters per
  line on wide screens.
- **Lists:** a line starting with `- `, `* ` or `• ` is a bullet point; a
  line starting with a number and `.` or `)` (for example `1. `) is a
  numbered step. Following lines of the same kind form one list; a numbered
  list starts at its first number. A line indented under a list item belongs
  to that item.
- **Nothing else is interpreted:** no bold, links or headings. `**`, `<b>`
  or `<script>` stay visible as text. The parser (`static/js/format.js`)
  returns plain data; `chat.js` builds `<p>`, `<ul>`, `<ol>` and `<li>` with
  `createElement` and fills them with `textContent`, so no text from the
  server is ever parsed as HTML.
- **Sources:** smaller chips. With up to four sources all are shown; with
  five or more, the first three are shown and a **"+ N more"** button shows
  the rest (`aria-expanded`, `aria-controls`); after that it reads **"Show
  less"**. The hidden chips stay in the HTML with `hidden`. The order is the
  server's.
- Unchanged: questions on the right, answers on the left; the contact
  callout; errors.

**Acceptance criteria:**
- **AC12** (`tests/js/format.test.cjs`, Node's built-in test runner, run by
  `tests/test_format_js.py`): paragraphs, bullet and numbered lists, a list
  right after a sentence, mixed text, the numbered start, indented
  continuation lines, `\r\n`, empty answers, and `<script>` kept as text;
  the number of sources shown at first (all up to 4, else 3).
- **AC13:** the `innerHTML` guard also covers `format.js`; all existing tests
  pass.
- **AC14** (by hand, 390 and 1280 px): a long answer with a list is readable;
  "+ N more" and "Show less" work with mouse and keyboard; no horizontal
  scrolling.

## Known limitations

- The suggested questions are fixed in the template. When the content
  changes, AC2 shows if one stops working.
- Apart from the answer parser (AC12), the page has no JavaScript unit tests;
  the behaviour is checked by hand (AC4–AC7, AC11, AC14), as in Task 6.
