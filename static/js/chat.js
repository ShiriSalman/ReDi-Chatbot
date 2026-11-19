// Chat page: sends questions to /api/chat and shows the answers with their source links.
// All text from the server is shown with textContent and never parsed as HTML, so it cannot run as code.

const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const sendButton = document.getElementById("send");
const conversation = document.getElementById("conversation");
const chatLog = document.getElementById("chat-log");
const loading = document.getElementById("loading");
const formError = document.getElementById("form-error");
const welcome = document.getElementById("welcome");
const newChatButton = document.getElementById("new-chat");
const counter = document.getElementById("counter");
const topics = document.getElementById("topics");
const tabList = topics.querySelector('[role="tablist"]');
const tabs = [...tabList.querySelectorAll('[role="tab"]')];
const drawer = document.getElementById("suggestion-drawer");
const suggestionsToggle = document.getElementById("suggestions-toggle");
// Where the topics go back to when the drawer closes: right after the welcome's lead line
const welcomeTopicsPlace = welcome.querySelector(".lead");

const EMPTY_QUESTION = "Please enter a question.";
const GENERIC_ERROR = "Something went wrong while answering your question. Please try again.";
const NETWORK_ERROR = "The chatbot could not be reached. Please check your connection and try again.";
const CONTACT_FALLBACK_TITLE = "ReDI contact page";
const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
// The ReDI logo mark; the header image gives its address, so it's set in one place (the template)
const LOGO_URL = document.querySelector(".brand-mark").getAttribute("src");

// The visitor's last question; after an answer it is scrolled to the top, so long answers
// are read from their first line (specs/ui_redesign.md)
let lastQuestion = null;

// A small "opens elsewhere" arrow, built with DOM methods like everything else on the page
function arrowIcon() {
  const svg = document.createElementNS(SVG_NAMESPACE, "svg");
  const attributes = {
    width: 14, height: 14, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
    "stroke-width": 2.2, "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true",
  };
  for (const [name, value] of Object.entries(attributes)) {
    svg.setAttribute(name, value);
  }
  for (const d of ["M7 17L17 7", "M8 7h9v9"]) {
    const path = document.createElementNS(SVG_NAMESPACE, "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
  }
  return svg;
}

function scrollToEnd() {
  conversation.scrollTop = conversation.scrollHeight;
}

function scrollToQuestion() {
  if (lastQuestion) {
    conversation.scrollTop = lastQuestion.offsetTop - conversation.offsetTop - 16;
  }
}

// A question is a bubble; an answer or error is a card under the "ReDI Chatbot" label.
// Returns the element that sources are added to.
function addMessage(role, text) {
  const message = document.createElement("div");
  message.className = `message message-${role}`;

  const paragraph = document.createElement("p");
  paragraph.textContent = text;

  if (role === "user") {
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.appendChild(paragraph);
    message.appendChild(bubble);
    chatLog.appendChild(message);
    lastQuestion = message;
    scrollToEnd();
    return message;
  }

  // The answer replaces the dots, so it doesn't appear below them
  hideTyping();

  const sender = document.createElement("div");
  sender.className = "sender";
  // Decorative: "ReDI Chatbot" next to it is the name
  const avatar = document.createElement("img");
  avatar.className = "avatar";
  avatar.src = LOGO_URL;
  avatar.alt = "";
  sender.append(avatar, "ReDI Chatbot");

  const card = document.createElement("div");
  card.className = "card";
  card.appendChild(paragraph);

  message.append(sender, card);
  chatLog.appendChild(message);
  scrollToQuestion();
  return message;
}

// The server already validates URLs; checking again here means a link can only ever be http(s)
function isSafeUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function addSources(message, sources) {
  // Like Task 5: the Sources section only appears when at least one link is valid
  if (!sources.some((source) => isSafeUrl(source.url))) {
    return;
  }

  const section = document.createElement("div");
  section.className = "sources";

  const title = document.createElement("p");
  title.className = "sources-title";
  title.textContent = "Sources";
  section.appendChild(title);

  // Each source is a chip: a rounded link with an arrow
  const list = document.createElement("ul");
  list.className = "chips";
  for (const source of sources) {
    const item = document.createElement("li");
    if (isSafeUrl(source.url)) {
      const link = document.createElement("a");
      link.className = "chip";
      link.href = source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.append(arrowIcon(), source.title);
      item.appendChild(link);
    } else {
      const plain = document.createElement("span");
      plain.className = "chip chip-plain";
      plain.textContent = `${source.title} (no link available)`;
      item.appendChild(plain);
    }
    list.appendChild(item);
  }
  section.appendChild(list);
  message.querySelector(".card").appendChild(section);
  scrollToQuestion();
}

// The server decides when to offer the contact page; the page only checks the link is safe.
// It is a callout below the answer, so it reads as "what to do next".
function addContact(message, contact) {
  if (!contact || !isSafeUrl(contact.url)) {
    return;
  }

  const callout = document.createElement("div");
  callout.className = "contact-callout";

  const text = document.createElement("span");
  text.textContent = "Need more help? You can ask ReDI directly.";

  const link = document.createElement("a");
  link.href = contact.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.append(contact.title || CONTACT_FALLBACK_TITLE, " ", arrowIcon());

  callout.append(text, link);
  message.appendChild(callout);
  scrollToQuestion();
}

// The ReDI logo mark built from its shapes (same as static/img/redi-mark.svg), so its orange
// dot and arrow can move on their own while waiting (CSS: .waiting-mark)
function waitingMark() {
  const svg = document.createElementNS(SVG_NAMESPACE, "svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("class", "waiting-mark");
  const shapes = [
    ["rect", { width: 100, height: 100, fill: "#58adc4" }],
    ["polygon", { points: "6,50 56,0 100,50 56,100", fill: "#ffffff" }],
    ["polygon", { points: "57,8 97,50 57,92", fill: "#f15a22", class: "mark-arrow" }],
    ["circle", { cx: 34, cy: 50, r: 14, fill: "#f15a22", class: "mark-dot" }],
  ];
  for (const [name, attributes] of shapes) {
    const shape = document.createElementNS(SVG_NAMESPACE, name);
    for (const [key, value] of Object.entries(attributes)) {
      shape.setAttribute(key, value);
    }
    svg.appendChild(shape);
  }
  return svg;
}

// The animated logo in the conversation while waiting; screen readers get the role="status" text
let typingIndicator = null;

function showTyping() {
  typingIndicator = document.createElement("div");
  typingIndicator.className = "message message-assistant typing";
  typingIndicator.setAttribute("aria-hidden", "true");
  const card = document.createElement("div");
  card.className = "card";
  card.appendChild(waitingMark());
  typingIndicator.appendChild(card);
  chatLog.appendChild(typingIndicator);
  scrollToEnd();
}

function hideTyping() {
  if (typingIndicator) {
    typingIndicator.remove();
    typingIndicator = null;
  }
}

function setLoading(isLoading) {
  loading.hidden = !isLoading;
  sendButton.disabled = isLoading;
  input.disabled = isLoading;
  chatLog.setAttribute("aria-busy", String(isLoading));
  if (isLoading) {
    showTyping();
  } else {
    hideTyping();
  }
}

async function askQuestion(question) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  // An error page that is not JSON still gets a friendly message
  const data = await response.json().catch(() => ({}));
  return { ok: response.ok, data };
}

// The welcome screen is shown until the first question and again after "New chat".
// During a conversation the topics are reached with the Suggestions button instead.
function showWelcome(visible) {
  welcome.hidden = !visible;
  newChatButton.hidden = visible;
  suggestionsToggle.hidden = visible;
  closeDrawer();
}

// The topics (tabs and questions) live in the welcome screen; the Suggestions button moves
// them into the drawer above the input, so there is one copy with its listeners
function openDrawer() {
  drawer.appendChild(topics);
  drawer.hidden = false;
  suggestionsToggle.setAttribute("aria-expanded", "true");
}

function closeDrawer() {
  welcomeTopicsPlace.after(topics);
  drawer.hidden = true;
  suggestionsToggle.setAttribute("aria-expanded", "false");
}

// Tabs: one is selected and shows its panel; only the selected tab is in the Tab order
function selectTab(tab) {
  for (const other of tabs) {
    const selected = other === tab;
    other.setAttribute("aria-selected", String(selected));
    other.tabIndex = selected ? 0 : -1;
    document.getElementById(other.getAttribute("aria-controls")).hidden = !selected;
  }
  tab.scrollIntoView({ block: "nearest", inline: "nearest" });
}

// Typed questions and suggested questions go through here, so both behave the same
async function send(question) {
  formError.textContent = "";
  showWelcome(false);
  addMessage("user", question);
  input.value = "";
  updateComposer();
  setLoading(true);

  try {
    const { ok, data } = await askQuestion(question);
    if (ok) {
      const message = addMessage("assistant", data.answer);
      addSources(message, data.sources || []);
      addContact(message, data.contact);
    } else {
      addMessage("error", data.error || GENERIC_ERROR);
      // Give the question back so the visitor can try again without retyping it
      input.value = question;
    }
  } catch {
    addMessage("error", NETWORK_ERROR);
    input.value = question;
  } finally {
    setLoading(false);
    // After an error the question is back in the box, so the counter and height follow it
    updateComposer();
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const question = input.value.trim();
  if (!question) {
    formError.textContent = EMPTY_QUESTION;
    input.focus();
    return;
  }
  send(question);
});

// The box grows with the text (up to its CSS max-height). The counter shows the 500 limit,
// visible from 400 characters and red from 450; Send looks quieter while the box is empty.
const MAX_LENGTH = Number(input.getAttribute("maxlength"));
const SHOW_COUNTER = MAX_LENGTH - 100;
const NEAR_LIMIT = MAX_LENGTH - 50;

function updateComposer() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
  counter.textContent = `${input.value.length}/${MAX_LENGTH}`;
  counter.classList.toggle("visible", input.value.length >= SHOW_COUNTER);
  counter.classList.toggle("near-limit", input.value.length >= NEAR_LIMIT);
  form.classList.toggle("has-text", input.value.trim() !== "");
}

input.addEventListener("input", updateComposer);

// Enter sends, Shift+Enter adds a line; not while an input method is composing a word
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});

// A suggested question is sent right away, exactly as written on the button
for (const button of document.querySelectorAll(".suggestion")) {
  button.addEventListener("click", () => {
    closeDrawer();
    send(button.textContent.trim());
  });
}

for (const tab of tabs) {
  tab.addEventListener("click", () => selectTab(tab));
}

// Arrow keys, Home and End move between tabs (the usual keyboard pattern for tabs)
tabList.addEventListener("keydown", (event) => {
  const index = tabs.indexOf(document.activeElement);
  const targets = {
    ArrowRight: (index + 1) % tabs.length,
    ArrowLeft: (index - 1 + tabs.length) % tabs.length,
    Home: 0,
    End: tabs.length - 1,
  };
  if (index === -1 || !(event.key in targets)) {
    return;
  }
  event.preventDefault();
  const tab = tabs[targets[event.key]];
  selectTab(tab);
  tab.focus();
});

suggestionsToggle.addEventListener("click", () => {
  if (drawer.hidden) {
    openDrawer();
  } else {
    closeDrawer();
  }
});

newChatButton.addEventListener("click", () => {
  chatLog.replaceChildren();
  lastQuestion = null;
  formError.textContent = "";
  showWelcome(true);
  conversation.scrollTop = 0;
  input.focus();
});
