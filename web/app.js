const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const resetButton = document.querySelector("#reset-button");
const messages = document.querySelector("#messages");
const stageEl = document.querySelector("#stage");
const riskEl = document.querySelector("#risk");
const scoreEl = document.querySelector("#score");
const intentEl = document.querySelector("#intent");
const memoryEl = document.querySelector("#memory");
const candidatesEl = document.querySelector("#candidates");

function appendBubble(role, text, extraClass = "") {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role} ${extraClass}`.trim();
  const span = document.createElement("span");
  span.textContent = text;
  bubble.appendChild(span);
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

function setBusy(isBusy) {
  sendButton.disabled = isBusy;
  resetButton.disabled = isBusy;
  input.disabled = isBusy;
  sendButton.textContent = isBusy ? "生成中" : "发送";
}

function renderState(data) {
  const relationship = data.relationship_state || {};
  const risk = data.risk || {};
  const analysis = data.analysis || {};
  const ranked = data.ranked || {};

  stageEl.textContent = `${relationship.stage || "-"} ${relationship.stage_label || ""}`.trim();
  riskEl.textContent = risk.risk_level || "-";
  riskEl.className = risk.risk_level === "high" ? "risk-high" : risk.risk_level === "medium" ? "risk-medium" : "";
  scoreEl.textContent = ranked.total_score ? Number(ranked.total_score).toFixed(1) : "-";
  intentEl.textContent = analysis.intent || "-";

  renderMemory(data.memory || {});
  renderCandidates(data.candidates || []);
}

function renderMemory(memory) {
  const lines = [];
  if (memory.name) lines.push(`姓名：${memory.name}`);
  if (memory.city) lines.push(`城市：${memory.city}`);
  if (memory.occupation) lines.push(`职业：${memory.occupation}`);
  if (Array.isArray(memory.pets) && memory.pets.length) {
    const pet = memory.pets[0];
    lines.push(`宠物：${pet.breed || pet.species || pet.name || "已记录"}`);
  }
  if (Array.isArray(memory.interests) && memory.interests.length) {
    lines.push(`兴趣：${memory.interests.join("、")}`);
  }
  memoryEl.textContent = lines.length ? lines.join("\n") : "暂无";
}

function renderCandidates(candidates) {
  candidatesEl.replaceChildren();
  for (const candidate of candidates) {
    const li = document.createElement("li");
    li.textContent = candidate.text || "";
    candidatesEl.appendChild(li);
  }
}

async function sendMessage(text) {
  appendBubble("user", text);
  const loading = appendBubble("assistant", "正在想怎么回...", "loading");
  setBusy(true);
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "请求失败");
    loading.remove();
    appendBubble("assistant", data.reply || "我在，你慢慢说");
    renderState(data);
  } catch (error) {
    loading.remove();
    appendBubble("assistant", `出错了：${error.message}`);
  } finally {
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  input.style.height = "auto";
  sendMessage(text);
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

resetButton.addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  messages.replaceChildren();
  appendBubble("assistant", "当前对话已清空，长期记忆还保留着。");
  candidatesEl.replaceChildren();
});
