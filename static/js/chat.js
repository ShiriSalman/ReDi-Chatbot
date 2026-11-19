// Chat page: sends questions to /api/chat and shows the answers with their source links.
// All text from the server is shown with textContent and never parsed as HTML, so it cannot run as code.

const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const sendButton = document.getElementById("send");
const conversation = document.getElementById("conversation");
const chatLog = document.getElementById("chat-log");
const loading = document.getElementById("loading");
const formError = document.getElementById("form-error");

const EMPTY_QUESTION = "Please enter a question.";
const GENERIC_ERROR = "Something went wrong while answering your question. Please try again.";
const NETWORK_ERROR = "The chatbot could not be reached. Please check your connection and try again.";
const CONTACT_FALLBACK_TITLE = "ReDI contact page";
const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

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

  const sender = document.createElement("div");
  sender.className = "sender";
  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = "ReDI";
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

function setLoading(isLoading) {
  loading.hidden = !isLoading;
  sendButton.disabled = isLoading;
  input.disabled = isLoading;
  chatLog.setAttribute("aria-busy", String(isLoading));
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = input.value.trim();
  if (!question) {
    formError.textContent = EMPTY_QUESTION;
    input.focus();
    return;
  }
  formError.textContent = "";

  addMessage("user", question);
  input.value = "";
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
    input.focus();
  }
});
