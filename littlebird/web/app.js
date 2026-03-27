const state = {
  pollingHandle: null,
};

const elements = {
  statusBadge: document.getElementById("status-badge"),
  threadState: document.getElementById("thread-state"),
  lastCapture: document.getElementById("last-capture"),
  eventCount: document.getElementById("event-count"),
  memoryCount: document.getElementById("memory-count"),
  chatLog: document.getElementById("chat-log"),
  chatForm: document.getElementById("chat-form"),
  questionInput: document.getElementById("question-input"),
  startButton: document.getElementById("start-btn"),
  pauseButton: document.getElementById("pause-btn"),
  stopButton: document.getElementById("stop-btn"),
  messageTemplate: document.getElementById("chat-message-template"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

function appendMessage(role, body) {
  const node = elements.messageTemplate.content.firstElementChild.cloneNode(true);
  node.querySelector(".message-role").textContent = role;
  node.querySelector(".message-body").textContent = body;
  elements.chatLog.append(node);
  elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

function renderStatus(status) {
  const { running, paused, thread_alive, last_capture_at, captured_event_count, recent_memory_count } = status;
  elements.threadState.textContent = thread_alive ? "Alive" : "Stopped";
  elements.lastCapture.textContent = last_capture_at || "None";
  elements.eventCount.textContent = String(captured_event_count ?? 0);
  elements.memoryCount.textContent = String(recent_memory_count ?? 0);

  if (running) {
    elements.statusBadge.textContent = "Running";
    elements.statusBadge.className = "badge badge-running";
  } else if (paused && thread_alive) {
    elements.statusBadge.textContent = "Paused";
    elements.statusBadge.className = "badge badge-paused";
  } else {
    elements.statusBadge.textContent = "Idle";
    elements.statusBadge.className = "badge badge-idle";
  }
}

async function refreshStatus() {
  const status = await api("/api/status");
  renderStatus(status);
}

async function handleCaptureAction(path, successLabel) {
  const status = await api(path, { method: "POST", body: "{}" });
  renderStatus(status);
  appendMessage("System", successLabel);
}

async function submitQuestion(event) {
  event.preventDefault();
  const question = elements.questionInput.value.trim();
  if (!question) {
    return;
  }

  appendMessage("You", question);
  elements.questionInput.value = "";

  try {
    const payload = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ question }),
    });
    appendMessage("MemChat", payload.answer || "No answer returned.");
    await refreshStatus();
  } catch (error) {
    appendMessage("System", `Chat failed: ${error.message}`);
  }
}

function wireEvents() {
  elements.chatForm.addEventListener("submit", submitQuestion);
  elements.startButton.addEventListener("click", () => handleCaptureAction("/api/capture/start", "Capture started.").catch(reportError));
  elements.pauseButton.addEventListener("click", () => handleCaptureAction("/api/capture/pause", "Capture paused.").catch(reportError));
  elements.stopButton.addEventListener("click", () => handleCaptureAction("/api/capture/stop", "Capture stopped.").catch(reportError));
}

function reportError(error) {
  appendMessage("System", error.message || String(error));
}

async function boot() {
  wireEvents();
  appendMessage("System", "Desktop ready. Start capture when you want MemChat to observe your screen.");
  await refreshStatus();
  state.pollingHandle = window.setInterval(() => {
    refreshStatus().catch(reportError);
  }, 4000);
}

boot().catch(reportError);

