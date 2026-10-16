// Chat page: sends questions to /api/chat and shows the answers with their source links.
// All text from the server is shown with textContent and never parsed as HTML, so it cannot run as code.

const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const sendButton = document.getElementById("send");
const chatLog = document.getElementById("chat-log");
const loading = document.getElementById("loading");
const formError = document.getElementById("form-error");

const EMPTY_QUESTION = "Please enter a question.";
const GENERIC_ERROR = "Something went wrong while answering your question. Please try again.";
const NETWORK_ERROR = "The chatbot could not be reached. Please check your connection and try again.";
const CONTACT_FALLBACK_TITLE = "ReDI contact page";

function addMessage(role, text) {
  const message = document.createElement("div");
  message.className = `message message-${role}`;

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  message.appendChild(paragraph);

  chatLog.appendChild(message);
  message.scrollIntoView({ block: "end", behavior: "smooth" });
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

  const list = document.createElement("ul");
  for (const source of sources) {
    const item = document.createElement("li");
    if (isSafeUrl(source.url)) {
      const link = document.createElement("a");
      link.href = source.url;
      link.textContent = source.title;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      item.appendChild(link);
    } else {
      item.textContent = `${source.title} (no link available)`;
    }
    list.appendChild(item);
  }
  section.appendChild(list);
  message.appendChild(section);
}

// The server decides when to offer the contact page; the page only checks the link is safe
function addContact(message, contact) {
  if (!contact || !isSafeUrl(contact.url)) {
    return;
  }

  const line = document.createElement("p");
  line.className = "contact";
  line.append("You can ask ReDI directly: ");

  const link = document.createElement("a");
  link.href = contact.url;
  link.textContent = contact.title || CONTACT_FALLBACK_TITLE;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  line.appendChild(link);

  message.appendChild(line);
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
