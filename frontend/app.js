// Enterprise Task Agent — chat UI logic (vanilla JS, no build step).

const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const roleSelect = document.getElementById("role");
const statusDot = document.getElementById("status-dot");

const authState = { authEnabled: false, authenticated: false, user: null };

const STATUS_ICON = { completed: "✓", failed: "✕", denied: "⛔" };

function scrollToBottom() {
  chat.scrollTop = chat.scrollHeight;
}

function el(tag, className, html) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (html !== undefined) node.innerHTML = html;
  return node;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function addUserMessage(text) {
  const msg = el("div", "message user");
  msg.append(el("div", "avatar", "🧑"));
  const bubble = el("div", "bubble");
  bubble.append(el("p", null, escapeHtml(text)));
  msg.append(bubble);
  chat.append(msg);
  scrollToBottom();
}

// Creates an agent message shell and returns helper handles for live updates.
function addAgentMessage() {
  const msg = el("div", "message agent");
  msg.append(el("div", "avatar", "⚡"));
  const bubble = el("div", "bubble");
  const intro = el("p", null, "On it — planning your request…");
  const steps = el("div", "steps");
  bubble.append(intro, steps);
  msg.append(bubble);
  chat.append(msg);
  scrollToBottom();

  const stepNodes = {};

  return {
    setIntro(text) {
      intro.textContent = text;
    },
    startStep(tool, rationale) {
      const step = el("div", "step running");
      step.append(el("div", "spinner"));
      const label = el("span", null, `<span class="tool-name">${escapeHtml(tool)}</span> — ${escapeHtml(rationale || "working…")}`);
      step.append(label);
      steps.append(step);
      stepNodes[tool] = step;
      scrollToBottom();
    },
    finishStep(result) {
      const step = stepNodes[result.tool] || el("div", "step");
      if (!stepNodes[result.tool]) steps.append(step);
      step.className = `step ${result.status}`;
      step.innerHTML = "";
      step.append(el("span", "icon", STATUS_ICON[result.status] || "•"));
      step.append(
        el(
          "span",
          "step-summary",
          `<span class="tool-name">${escapeHtml(result.tool)}</span> ${escapeHtml(result.summary)}`
        )
      );
      step.append(el("span", `badge ${result.status}`, result.status));
      scrollToBottom();
    },
    info(text) {
      intro.textContent = text;
    },
    done(task) {
      if (task.status === "empty") return;
      const labels = {
        completed: "All steps completed.",
        partial: "Some steps need attention.",
        failed: "I couldn't complete this request.",
      };
      this.setIntro(labels[task.status] || "Done.");
      const line = el("div", "summary-line", `Task ${escapeHtml(task.id)} · ${task.steps.length} step(s) · status: ${escapeHtml(task.status)}`);
      steps.after(line);
      scrollToBottom();
    },
  };
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  input.disabled = busy;
  statusDot.classList.toggle("busy", busy);
  if (!busy) input.focus();
}

function sendMessage(text) {
  const message = text.trim();
  if (!message) return;

  addUserMessage(message);
  input.value = "";
  setBusy(true);

  const view = addAgentMessage();
  const role = authState.authEnabled ? (authState.user && authState.user.role) || "employee" : roleSelect.value;
  const params = new URLSearchParams({ message, role });
  const source = new EventSource(`/api/chat/stream?${params.toString()}`, { withCredentials: true });

  source.addEventListener("plan", (e) => {
    const data = JSON.parse(e.data);
    view.setIntro(
      data.count > 0
        ? `Planned ${data.count} step${data.count > 1 ? "s" : ""}. Executing…`
        : "Thinking…"
    );
  });

  source.addEventListener("step_started", (e) => {
    const data = JSON.parse(e.data);
    view.startStep(data.tool, data.rationale);
  });

  source.addEventListener("step_finished", (e) => {
    view.finishStep(JSON.parse(e.data));
  });

  source.addEventListener("info", (e) => {
    view.info(JSON.parse(e.data).message);
  });

  source.addEventListener("done", (e) => {
    view.done(JSON.parse(e.data));
    source.close();
    setBusy(false);
  });

  source.onerror = () => {
    view.setIntro("Connection interrupted. Please try again.");
    source.close();
    setBusy(false);
  };
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(input.value);
});

document.getElementById("suggestions").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) sendMessage(chip.dataset.prompt);
});

// ── Authentication bootstrap ──────────────────────────────────────────
function setGated(gated) {
  input.disabled = gated;
  sendBtn.disabled = gated;
  if (!gated) input.focus();
}

function applyAuthState() {
  const roleWrap = document.getElementById("role-wrap");
  const userChip = document.getElementById("user-chip");
  const loginBtn = document.getElementById("login-btn");
  const gate = document.getElementById("auth-gate");
  const modeNote = document.getElementById("mode-note");

  if (!authState.authEnabled) {
    roleWrap && roleWrap.classList.remove("hidden");
    userChip && userChip.classList.add("hidden");
    loginBtn && loginBtn.classList.add("hidden");
    gate && gate.classList.add("hidden");
    if (modeNote) modeNote.textContent = "Dev mode — mock actions (no sign-in configured).";
    setGated(false);
    return;
  }

  roleWrap && roleWrap.classList.add("hidden");
  if (authState.authenticated && authState.user) {
    const name = authState.user.name || "User";
    document.getElementById("user-name").textContent = name;
    document.getElementById("user-role").textContent = authState.user.role || "employee";
    document.getElementById("user-initial").textContent = (name[0] || "U").toUpperCase();
    userChip && userChip.classList.remove("hidden");
    loginBtn && loginBtn.classList.add("hidden");
    gate && gate.classList.add("hidden");
    if (modeNote) modeNote.textContent = "Signed in — real Microsoft 365 actions enabled.";
    setGated(false);
  } else {
    userChip && userChip.classList.add("hidden");
    loginBtn && loginBtn.classList.remove("hidden");
    gate && gate.classList.remove("hidden");
    if (modeNote) modeNote.textContent = "Sign in required.";
    setGated(true);
  }
}

async function bootstrapAuth() {
  try {
    const res = await fetch("/auth/status", { credentials: "same-origin" });
    const data = await res.json();
    authState.authEnabled = !!data.auth_enabled;
    authState.authenticated = !!data.authenticated;
    authState.user = data.user || null;
  } catch (err) {
    // If status can't be loaded, fall back to offline dev behavior.
    authState.authEnabled = false;
  }
  applyAuthState();
}

bootstrapAuth();
