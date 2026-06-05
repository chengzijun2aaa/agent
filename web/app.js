/**
 * Agent 聊天后台前端核心逻辑（多会话路由与命名隔离版）
 */

// ============================================================
// 1. DOM 节点声明
// ============================================================
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const resetButton = document.querySelector("#reset-button");
const messages = document.querySelector("#messages");

// 侧边栏及状态面板节点
const stageEl = document.querySelector("#stage");
const riskEl = document.querySelector("#risk");
const scoreEl = document.querySelector("#score");
const intentEl = document.querySelector("#intent");
const memoryEl = document.querySelector("#memory");
const candidatesEl = document.querySelector("#candidates");

// 💡 核心新增：会话命名管理器节点
const sessionSelect = document.querySelector("#session-select");
const addSessionBtn = document.querySelector("#add-session-btn");

// ============================================================
// 2. 状态渲染与核心防御层
// ============================================================

function renderState(data) {
  const relationship = data.relationship_state || {};
  const risk = data.risk || {};
  const analysis = data.analysis || {};
  const profile = data.profile || {};

  if (stageEl) {
    stageEl.textContent = `${relationship.stage || "-"} ${relationship.stage_label || ""}`.trim();
  }

  if (riskEl) {
    riskEl.textContent = risk.risk_level || "-";
    riskEl.className = risk.risk_level === "high" ? "risk-high" : risk.risk_level === "medium" ? "risk-medium" : "";
  }

  if (scoreEl) {
    const totalScore = data.ranked?.total_score || profile.warmth;
    scoreEl.textContent = totalScore !== undefined ? Number(totalScore).toFixed(1) : "-";
  }

  if (intentEl) {
    intentEl.textContent = analysis.intent || "-";
  }

  renderMemory(data.memory || {});
  renderCandidates(data.candidates || []);
}

function renderMemory(memory) {
  if (!memoryEl) return;

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
  if (!candidatesEl) return;
  candidatesEl.replaceChildren();

  for (const candidate of candidates) {
    const li = document.createElement("li");
    const textContent = typeof candidate === "string" ? candidate : candidate.text || "";

    // 【边界熔断拦截】
    if (textContent.includes("治治我") || textContent.includes("死了那条心")) {
      continue;
    }

    li.textContent = textContent;
    candidatesEl.appendChild(li);
  }
}

// ============================================================
// 3. 聊天气泡与多会话交互流控制
// ============================================================

function appendBubble(role, text, extraClass = "") {
  if (!messages) return null;
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
  if (sendButton) {
    sendButton.disabled = isBusy;
    sendButton.textContent = isBusy ? "生成中" : "发送";
  }
  if (resetButton) resetButton.disabled = isBusy;
  if (input) input.disabled = isBusy;
}

/**
 * 发送消息（动态绑定当前选中的会话 user_id）
 */
async function sendMessage(text) {
  // 💡 核心改动：获取当前在跟哪个女生聊天（把选择的值作为 user_id 发给后端）
  const currentGirlId = sessionSelect ? sessionSelect.value : "default_girl";

  appendBubble("user", text);
  const loading = appendBubble("assistant", "正在想怎么回...", "loading");
  setBusy(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        user_id: currentGirlId, // 💡 对应后端 EmotionChatAgent 接收的 user_id
      }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "请求失败");

    if (loading) loading.remove();
    appendBubble("assistant", data.reply || "我在，你慢慢说");

    // 渲染属于该女生的最新画像和侧边栏状态
    renderState(data);
  } catch (error) {
    if (loading) loading.remove();
    appendBubble("assistant", `出错了：${error.message}`);
    console.error("API 报错:", error);
  } finally {
    setBusy(false);
    if (input) input.focus();
  }
}

// ============================================================
// 4. 会话管理监听（动态切换与新建命名）
// ============================================================

// 💡 监听切换：当你从下拉框选“小林”换到“薇薇”时，自动清空屏幕并向后端拉取新人的画像
if (sessionSelect) {
  sessionSelect.addEventListener("change", async () => {
    const targetGirlId = sessionSelect.value;
    const targetGirlName = sessionSelect.options[sessionSelect.selectedIndex].text;

    if (messages) messages.replaceChildren();
    if (candidatesEl) candidatesEl.replaceChildren();

    appendBubble("assistant", `成功切入与【${targetGirlName}】的独立对话战局。`);

    try {
      // 💡 向后端新开一个获取单人静态状态的接口，用来初始化侧边栏
      const response = await fetch(`/api/session_status?user_id=${targetGirlId}`);
      if (response.ok) {
        const data = await response.json();
        renderState(data);
      }
    } catch (err) {
      console.warn("拉取新会话静态状态失败，将在发送第一条消息时自动初始化面板");
    }
  });
}

// 💡 监听新建：点击“新建战局”，弹窗让你给聊天命名，并直接插入下拉框
if (addSessionBtn && sessionSelect) {
  addSessionBtn.addEventListener("click", () => {
    const girlName = prompt("请给这段聊天命名（输入女生的名字或备注）：");
    if (!girlName || !girlName.trim()) return;

    const pinyinId = "girl_" + Date.now(); // 用时间戳生成唯一的本地 session_id
    const newOption = document.createElement("option");
    newOption.value = pinyinId;
    newOption.textContent = girlName.trim();

    sessionSelect.appendChild(newOption);
    sessionSelect.value = pinyinId; // 自动切换到新创建的人

    // 触发切换逻辑
    sessionSelect.dispatchEvent(new Event("change"));
  });
}

// ============================================================
// 5. 原有全局事件监听绑定（保持不动）
// ============================================================
if (form) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    input.style.height = "auto";
    sendMessage(text);
  });
}

if (input) {
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (form) form.requestSubmit();
    }
  });
}

if (resetButton) {
  resetButton.addEventListener("click", async () => {
    const currentGirlId = sessionSelect ? sessionSelect.value : "default_girl";
    try {
      setBusy(true);
      // 重置接口也要带上当前是谁，只清空她一个人的历史记录
      await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentGirlId }),
      });
      if (messages) messages.replaceChildren();
      appendBubble("assistant", "当前战局历史已清空，长期记忆还保留着。");
      if (candidatesEl) candidatesEl.replaceChildren();
    } catch (err) {
      console.error("重置会话失败:", err);
    } finally {
      setBusy(false);
    }
  });
}
